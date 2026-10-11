import { useEffect, useState } from "react";
import { api } from "./api.js";
import { BAND } from "./Dashboard.jsx";

const MESSAGE = {
  typical: "Most words were produced as expected.",
  monitor: "Some sounds were not produced as expected. Repeat the screening in a few weeks and talk to your child's teacher or paediatrician if it continues.",
  refer: "Many sounds were not produced as expected. We suggest booking an assessment with a speech-language pathologist.",
  not_scored: "Listen to each recording below and mark it correct or incorrect to get an overview.",
};

function Play({ id }) {
  const [url, setUrl] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => () => url && URL.revokeObjectURL(url), [url]);
  async function load() {
    try { setUrl(URL.createObjectURL(await api.recordingAudio(id))); } catch (e) { setErr(e.message); }
  }
  if (err) return <span className="error small">{err}</span>;
  return url ? <audio controls autoPlay src={url} /> : <button className="btn small-btn" onClick={load}>▶ Play</button>;
}

export default function Results({ id, onBack }) {
  const [data, setData] = useState(null);
  const [words, setWords] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const a = await api.assessment(id);
        const w = await api.words(a.language);
        setWords(Object.fromEntries(w.map((x) => [x.id, x])));
        setData(a);
      } catch (e) { setError(e.message); }
    })();
  }, [id]);

  async function rate(rec, value) {
    try {
      await api.rateRecording(rec.id, rec.clinician_correct === value ? null : value);
      setData(await api.assessment(id));
    } catch (e) { setError(e.message); }
  }

  if (error && !data) return <div className="card"><p className="error">{error}</p><button className="btn" onClick={onBack}>Back</button></div>;
  if (!data) return <p className="muted">Loading…</p>;

  const band = BAND[data.band];
  return (
    <>
      <button className="link" onClick={onBack}>← Back</button>
      <div className="card summary">
        <span className={`pill ${band.cls}`}>{band.label}</span>
        {data.score !== null && <div className="score">{Math.round(data.score * 100)}%<span>of words correct</span></div>}
        <p>{MESSAGE[data.band]}</p>
        <p className="muted small">
          {data.recording_count} words recorded · {data.scored} marked.
          {data.analyzer === "quality" && " Automatic phoneme scoring is off, so scores come from your own marking."}
          {" "}This screening cannot diagnose a speech sound disorder.
        </p>
      </div>
      {error && <p className="error" role="alert">{error}</p>}

      <div className="card">
        <table>
          <thead><tr><th>Word</th><th>Recording</th><th>Heard</th><th>Marked</th></tr></thead>
          <tbody>
            {data.recordings.map((r) => {
              const w = words[r.word_id];
              return (
                <tr key={r.id}>
                  <td>
                    <span className={w?.lang === "hi" ? "deva" : ""}>{w?.text}</span>
                    <div className="muted small">{w?.target}</div>
                  </td>
                  <td><Play id={r.id} /></td>
                  <td className="small">
                    {r.recognized ? <>/{r.recognized}/ <span className="muted">({Math.round(r.auto_score * 100)}%)</span>
                      {r.errors.map((e, i) => (
                        <div key={i} className="muted">{e.type}: {e.expected ?? "–"} → {e.got ?? "–"}</div>
                      ))}</> : <span className="muted">—</span>}
                  </td>
                  <td>
                    <div className="row">
                      <button className={`chip ${r.clinician_correct === true ? "on good" : ""}`} onClick={() => rate(r, true)}>✓ Correct</button>
                      <button className={`chip ${r.clinician_correct === false ? "on bad" : ""}`} onClick={() => rate(r, false)}>✗ Not quite</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
