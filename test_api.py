import io
import shutil
import wave

import numpy as np
import pytest

from app import create_app
from app.analyzer import align, score_phonemes
from app.config import TestConfig
from app.extensions import db


def make_wav(seconds=1.0, rate=16000, freq=220, amp=0.4):
    t = np.arange(int(seconds * rate)) / rate
    pcm = (amp * np.sin(2 * np.pi * freq * t) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


@pytest.fixture()
def client():
    app = create_app(TestConfig)
    with app.app_context():
        yield app.test_client()
        db.session.remove()
        db.drop_all()
    shutil.rmtree(TestConfig.LOCAL_AUDIO_DIR, ignore_errors=True)


def register(client, email="a@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "name": "Asha", "password": "password123"})
    assert r.status_code == 201, r.get_json()
    return {"Authorization": "Bearer " + r.get_json()["token"]}


def test_auth_flow(client):
    register(client)
    assert client.post("/api/auth/register", json={"email": "a@example.com", "name": "x",
                                                    "password": "password123"}).status_code == 409
    assert client.post("/api/auth/register", json={"email": "bad", "name": "x",
                                                    "password": "password123"}).status_code == 400
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "A@example.com", "password": "password123"})
    assert r.status_code == 200
    h = {"Authorization": "Bearer " + r.get_json()["token"]}
    assert client.get("/api/auth/me", headers=h).get_json()["email"] == "a@example.com"
    assert client.get("/api/children").status_code == 401


def test_full_assessment(client):
    h = register(client)
    r = client.post("/api/children", headers=h, json={"name": "Riya", "age_months": 60, "home_language": "mixed"})
    child_id = r.get_json()["id"]
    assert client.post("/api/children", headers=h, json={"name": "X", "age_months": 5}).status_code == 400

    words = client.get("/api/words?language=mixed", headers=h).get_json()
    assert {w["lang"] for w in words} == {"hi", "en"} and words[0]["lang"] == "hi" and words[1]["lang"] == "en"

    a = client.post("/api/assessments", headers=h, json={"child_id": child_id, "language": "mixed"}).get_json()
    up = lambda wid, audio: client.post(
        f"/api/assessments/{a['id']}/recordings", headers=h,
        data={"word_id": wid, "audio": (io.BytesIO(audio), "w.wav")}, content_type="multipart/form-data")

    r = up("hi_machhli", make_wav())
    assert r.status_code == 201 and r.get_json()["quality_flags"] == [] and r.get_json()["auto_score"] is None
    assert up("hi_machhli", make_wav()).status_code == 201  # re-record replaces
    assert up("en_fish", make_wav(seconds=0.1)).get_json()["quality_flags"].count("too_short") == 1
    assert up("nope", make_wav()).status_code == 400
    assert up("en_ship", b"not audio").status_code == 400

    detail = client.get(f"/api/assessments/{a['id']}", headers=h).get_json()
    assert len(detail["recordings"]) == 2 and detail["band"] == "not_scored"

    ids = {r["word_id"]: r["id"] for r in detail["recordings"]}
    client.patch(f"/api/recordings/{ids['hi_machhli']}", headers=h, json={"clinician_correct": True})
    client.patch(f"/api/recordings/{ids['en_fish']}", headers=h, json={"clinician_correct": False})
    done = client.post(f"/api/assessments/{a['id']}/complete", headers=h).get_json()
    assert done["status"] == "completed" and done["score"] == 0.5 and done["band"] == "refer"
    assert up("en_ship", make_wav()).status_code == 409

    audio = client.get(f"/api/recordings/{ids['hi_machhli']}/audio", headers=h)
    assert audio.status_code == 200 and audio.data[:4] == b"RIFF"


def test_silent_recording_flagged(client):
    h = register(client)
    cid = client.post("/api/children", headers=h, json={"name": "R", "age_months": 48}).get_json()["id"]
    a = client.post("/api/assessments", headers=h, json={"child_id": cid, "language": "en"}).get_json()
    r = client.post(f"/api/assessments/{a['id']}/recordings", headers=h,
                    data={"word_id": "en_fish", "audio": (io.BytesIO(make_wav(amp=0.0)), "w.wav")},
                    content_type="multipart/form-data")
    assert "silent" in r.get_json()["quality_flags"]


def test_users_cannot_see_each_others_data(client):
    h1, h2 = register(client, "one@example.com"), register(client, "two@example.com")
    cid = client.post("/api/children", headers=h1, json={"name": "R", "age_months": 48}).get_json()["id"]
    a = client.post("/api/assessments", headers=h1, json={"child_id": cid, "language": "hi"}).get_json()
    assert client.get("/api/children", headers=h2).get_json() == []
    assert client.get(f"/api/assessments/{a['id']}", headers=h2).status_code == 404
    assert client.post("/api/assessments", headers=h2, json={"child_id": cid}).status_code == 404
    assert client.delete(f"/api/children/{cid}", headers=h2).status_code == 404


def test_phoneme_alignment():
    assert score_phonemes(["f", "ɪ", "ʃ"], ["f", "ɪ", "ʃ"]) == (1.0, [])
    score, errors = score_phonemes(["ʃ", "ɪ", "p"], ["s", "ɪ", "p"])  # /ʃ/ fronted to /s/
    assert errors == [{"type": "substitution", "position": 0, "expected": "ʃ", "got": "s"}]
    assert score == pytest.approx(0.667, abs=0.001)
    _, errors = score_phonemes(["s", "p", "u", "n"], ["p", "u", "n"])  # cluster reduction
    assert errors[0]["type"] == "omission" and errors[0]["expected"] == "s"
    assert score_phonemes(["m", "ə", "tʃʰ"], ["m", "ə", "tʃ"])[0] == 1.0  # aspiration marks ignored
    assert align([], [])[0] == 0


def test_static_login_page_served(client):
    r = client.get("/login/")
    assert r.status_code == 200 and b"vaaniAI" in r.data
    assert client.get("/login/login.css").status_code == 200
    assert client.get("/login/login.js").status_code == 200
