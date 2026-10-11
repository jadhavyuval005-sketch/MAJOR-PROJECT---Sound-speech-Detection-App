import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Recorder, micSupported } from "./recorder.js";

const FLAG_TEXT = {
  silent: "We couldn't hear anything. Check the microphone and try again.",
  too_short: "That was very short. Try saying the whole word.",
  too_long: "That recording was too long. Say just the one word.",
  mostly_silence: "Very little speech was detected. Try again a bit closer to the microphone.",
  clipped: "The recording was too loud. Move back slightly.",
};
const BLOCKING = ["silent", "too_short", "too_long", "mostly_silence"];

export default function Assessment({ child, language, onDone, onCancel }) {
  const [assessment, setAssessment] = useState(null);
  const [words, setWords] = useState([]);
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState("ready"); // ready | recording | review | saving
  const [clip, setClip] = useState(null); // {blob, url}
  const [error, setError] = useState("");
  const rec = useRef(null);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const [a, w] = await Promise.all([api.startAssessment(child.id, language), api.words(language)]);
        if (live) { setAssessment(a); setWords(w); }
      } catch (e) { if (live) setError(e.message); }
    })();
    return () => { live = false; rec.current?.cancel(); };
  }, [child.id, language]);

  useEffect(() => () => clip && URL.revokeObjectURL(clip.url), [clip]);

  if (!micSupported()) {
    return <div className="card"><p className="error">This browser can't record audio. Please use a recent Chrome, Edge, Firefox or Safari.</p>
      <button className="btn" onClick={onCancel}>Back</button></div>;
  }
  if (error && !assessment) return <div className="card"><p className="error">{error}</p><button className="btn" onClick={onCancel}>Back</button></div>;
  if (!assessment) return <p className="muted">Getting ready…</p>;

  const word = words[index];
  const progress = Math.round((index / words.length) * 100);

  async function start() {
    setError("");
    try {
      rec.current = new Recorder();
      await rec.current.start();
      setPhase("recording");
    } catch (e) {
      setError(e.name === "NotAllowedError"
        ? "Microphone access was blocked. Allow it in the browser's address bar and try again."
        : "Couldn't start the microphone: " + e.message);
    }
  }

  async function stop() {
    try {
      const blob = await rec.current.stop();
      setClip({ blob, url: URL.createObjectURL(blob) });
      setPhase("review");
    } catch {
      setError("Couldn't process that recording. Please try again.");
      setPhase("ready");
    }
  }

  async function keep() {
    setPhase("saving");
    setError("");
    try {
      const r = await api.uploadRecording(assessment.id, word.id, clip.blob);
      const blocking = r.quality_flags.filter((f) => BLOCKING.includes(f));
      if (blocking.length) {
        setError(FLAG_TEXT[blocking[0]]);
        setPhase("ready");
        return;
      }
      if (index + 1 >= words.length) {
        const done = await api.completeAssessment(assessment.id);
        onDone(done.id);
      } else {
        setIndex(index + 1);
        setClip(null);
        setPhase("ready");
      }
    } catch (e) {
      setError(e.message);
      setPhase("review");
    }
  }

  return (
    <div className="assess">
      <div className="row between">
        <p className="muted">{child.name} · word {index + 1} of {words.length}</p>
        <button className="link" onClick={onCancel}>Stop for now</button>
      </div>
      <div className="bar"><div style={{ width: `${progress}%` }} /></div>

      <div className="card word-card">
        <p className="muted small">{word.lang === "hi" ? "Hindi" : "English"} — ask your child to say this word</p>
        <div className={`word ${word.lang === "hi" ? "deva" : ""}`} lang={word.lang}>{word.text}</div>
        {word.lang === "hi" && <p className="roman">{word.roman} {word.gloss && <span className="muted">({word.gloss})</span>}</p>}

        {error && <p className="error" role="alert">{error}</p>}

        {phase === "ready" && <button className="btn primary big-btn" onClick={start}>● Record</button>}
        {phase === "recording" && (
          <>
            <p className="rec-dot">Recording… say the word now</p>
            <button className="btn danger big-btn" onClick={stop}>■ Stop</button>
          </>
        )}
        {(phase === "review" || phase === "saving") && clip && (
          <>
            <audio controls src={clip.url} />
            <div className="row center-row">
              <button className="btn" disabled={phase === "saving"} onClick={() => { setClip(null); setPhase("ready"); }}>Record again</button>
              <button className="btn primary" disabled={phase === "saving"} onClick={keep}>
                {phase === "saving" ? "Saving…" : index + 1 >= words.length ? "Save and finish" : "Save and next"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
