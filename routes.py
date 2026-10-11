import io
import re
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from . import analyzer
from .extensions import bcrypt, db
from .models import Assessment, Child, Recording, User
from .words import get_word, words_for

api = Blueprint("api", __name__, url_prefix="/api")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LANGS = ("hi", "en", "mixed")


def err(message, status=400):
    return jsonify({"error": message}), status


def uid():
    return int(get_jwt_identity())


def owned_child(child_id):
    return Child.query.filter_by(id=child_id, user_id=uid()).first()


def owned_assessment(assessment_id):
    return (Assessment.query.join(Child)
            .filter(Assessment.id == assessment_id, Child.user_id == uid()).first())


@api.get("/health")
def health():
    return {"status": "ok"}


# ---------- auth ----------
@api.post("/auth/register")
def register():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    name = (body.get("name") or "").strip()
    password = body.get("password") or ""
    if not EMAIL_RE.match(email):
        return err("Enter a valid email address")
    if not name:
        return err("Name is required")
    if len(password) < 8:
        return err("Password must be at least 8 characters")
    if User.query.filter_by(email=email).first():
        return err("An account with this email already exists", 409)
    role = body.get("role") if body.get("role") in ("parent", "clinician") else "parent"
    user = User(email=email, name=name, role=role,
                password_hash=bcrypt.generate_password_hash(password).decode())
    db.session.add(user)
    db.session.commit()
    return jsonify(token=create_access_token(identity=str(user.id)), user=user.to_dict()), 201


@api.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    user = User.query.filter_by(email=(body.get("email") or "").strip().lower()).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, body.get("password") or ""):
        return err("Incorrect email or password", 401)
    return jsonify(token=create_access_token(identity=str(user.id)), user=user.to_dict())


@api.get("/auth/me")
@jwt_required()
def me():
    user = db.session.get(User, uid())
    return jsonify(user.to_dict()) if user else err("User not found", 404)


# ---------- children ----------
@api.get("/children")
@jwt_required()
def list_children():
    kids = Child.query.filter_by(user_id=uid()).order_by(Child.id).all()
    return jsonify([k.to_dict() for k in kids])


@api.post("/children")
@jwt_required()
def add_child():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    try:
        age = int(body.get("age_months"))
    except (TypeError, ValueError):
        return err("Age in months must be a number")
    lang = body.get("home_language", "mixed")
    if not name:
        return err("Child's name is required")
    if not 24 <= age <= 144:
        return err("Age must be between 24 and 144 months (2 to 12 years)")
    if lang not in LANGS:
        return err("Invalid home language")
    child = Child(user_id=uid(), name=name, age_months=age, home_language=lang)
    db.session.add(child)
    db.session.commit()
    return jsonify(child.to_dict()), 201


@api.delete("/children/<int:child_id>")
@jwt_required()
def delete_child(child_id):
    child = owned_child(child_id)
    if not child:
        return err("Child not found", 404)
    storage = current_app.extensions["audio_storage"]
    for a in child.assessments:
        for r in a.recordings:
            storage.delete(r.audio_key)
    db.session.delete(child)
    db.session.commit()
    return "", 204


# ---------- words ----------
@api.get("/words")
@jwt_required()
def words():
    lang = request.args.get("language", "mixed")
    if lang not in LANGS:
        return err("Invalid language")
    return jsonify(words_for(lang))


# ---------- assessments ----------
@api.get("/assessments")
@jwt_required()
def list_assessments():
    q = Assessment.query.join(Child).filter(Child.user_id == uid())
    if request.args.get("child_id"):
        q = q.filter(Assessment.child_id == int(request.args["child_id"]))
    return jsonify([a.to_dict() for a in q.order_by(Assessment.id.desc()).all()])


@api.post("/assessments")
@jwt_required()
def start_assessment():
    body = request.get_json(silent=True) or {}
    child = owned_child(body.get("child_id"))
    if not child:
        return err("Child not found", 404)
    lang = body.get("language", child.home_language)
    if lang not in LANGS:
        return err("Invalid language")
    a = Assessment(child_id=child.id, language=lang, analyzer=current_app.config["ANALYZER"])
    db.session.add(a)
    db.session.commit()
    return jsonify(a.to_dict(with_recordings=True)), 201


@api.get("/assessments/<int:assessment_id>")
@jwt_required()
def get_assessment(assessment_id):
    a = owned_assessment(assessment_id)
    if not a:
        return err("Assessment not found", 404)
    return jsonify(a.to_dict(with_recordings=True))


@api.post("/assessments/<int:assessment_id>/recordings")
@jwt_required()
def upload_recording(assessment_id):
    a = owned_assessment(assessment_id)
    if not a:
        return err("Assessment not found", 404)
    if a.status == "completed":
        return err("Assessment is already completed", 409)
    word = get_word(request.form.get("word_id", ""))
    if not word:
        return err("Unknown word")
    file = request.files.get("audio")
    if not file:
        return err("Audio file is required")
    data = file.read()
    cfg = current_app.config
    try:
        result = analyzer.analyze(data, word, cfg["ANALYZER"], cfg["MAX_AUDIO_SECONDS"], cfg["WAV2VEC2_MODEL"])
    except analyzer.AudioError as exc:
        return err(str(exc))

    storage = current_app.extensions["audio_storage"]
    for old in [r for r in a.recordings if r.word_id == word["id"]]:  # re-recording replaces
        storage.delete(old.audio_key)
        db.session.delete(old)
    key = f"assessments/{a.id}/{word['id']}-{uuid.uuid4().hex[:8]}.wav"
    storage.put(key, data)
    rec = Recording(assessment_id=a.id, word_id=word["id"], audio_key=key, **result)
    db.session.add(rec)
    db.session.commit()
    return jsonify(rec.to_dict()), 201


@api.post("/assessments/<int:assessment_id>/complete")
@jwt_required()
def complete_assessment(assessment_id):
    a = owned_assessment(assessment_id)
    if not a:
        return err("Assessment not found", 404)
    a.status = "completed"
    a.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()
    return jsonify(a.to_dict(with_recordings=True))


# ---------- recordings ----------
def owned_recording(rec_id):
    return (Recording.query.join(Assessment).join(Child)
            .filter(Recording.id == rec_id, Child.user_id == uid()).first())


@api.patch("/recordings/<int:rec_id>")
@jwt_required()
def rate_recording(rec_id):
    rec = owned_recording(rec_id)
    if not rec:
        return err("Recording not found", 404)
    value = (request.get_json(silent=True) or {}).get("clinician_correct")
    if value is not None and not isinstance(value, bool):
        return err("clinician_correct must be true, false or null")
    rec.clinician_correct = value
    db.session.commit()
    return jsonify(rec.to_dict())


@api.get("/recordings/<int:rec_id>/audio")
@jwt_required()
def recording_audio(rec_id):
    rec = owned_recording(rec_id)
    if not rec:
        return err("Recording not found", 404)
    data = current_app.extensions["audio_storage"].get(rec.audio_key)
    return send_file(io.BytesIO(data), mimetype="audio/wav")
