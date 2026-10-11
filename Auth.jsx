import { useState } from "react";
import { api } from "./api.js";

// Decorative letters drifting in the hero: Devanagari + English sounds children practise.
const FLOATERS = [
  { t: "अ", x: 8, y: 12, d: 0 }, { t: "ch", x: 78, y: 8, d: 1.2 }, { t: "क", x: 88, y: 40, d: 2.1 },
  { t: "θ", x: 6, y: 58, d: .6 }, { t: "ट", x: 70, y: 70, d: 1.7 }, { t: "sh", x: 22, y: 84, d: 2.6 },
  { t: "ळ", x: 90, y: 88, d: .9 },
];
function Hero() {
  return (
    <section className="hero" aria-hidden="false">
      {FLOATERS.map((f) => (
        <span key={f.t} className="floater" style={{ left: `${f.x}%`, top: `${f.y}%`, animationDelay: `${f.d}s` }} aria-hidden="true">{f.t}</span>
      ))}
      <div className="hero-inner">
        <div className="brandmark"><span className="logo">वा</span><b>vaaniAI</b></div>
        <h1>Every child's voice,<br /><em>heard clearly</em> in Hindi, English, and both.</h1>
        <p className="lede">A friendly speech-sound screening you can do at home in five minutes. No special equipment, just a microphone.</p>

        <ul className="points">
          <li><b>हिन्दी + English</b> word lists that match how children really talk</li>
          <li><b>Hear it back</b> and mark each word yourself</li>
          <li><b>Share</b> a clear summary with a speech therapist</li>
        </ul>
      </div>
    </section>
  );
}

export default function Auth({ onSignedIn }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "parent" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const login = mode === "login";

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onSignedIn(await (login ? api.login(form) : api.register(form)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <Hero />
      <section className="auth-side">
        <form className="auth-form" onSubmit={submit}>
          <p className="namaste">नमस्ते 👋</p>
          <h2>{login ? "Welcome back" : "Create your account"}</h2>
          <p className="muted sub">{login ? "Sign in to continue your child's screening." : "It takes less than a minute."}</p>

          {!login && (
            <>
              <label>Your name<input value={form.name} onChange={set("name")} required autoComplete="name" /></label>
              <label>I am a
                <select value={form.role} onChange={set("role")}>
                  <option value="parent">Parent or caregiver</option>
                  <option value="clinician">Clinician or teacher</option>
                </select>
              </label>
            </>
          )}
          <label>Email<input type="email" value={form.email} onChange={set("email")} required autoComplete="email" placeholder="you@example.com" /></label>
          <label>Password
            <span className="pw">
              <input type={show ? "text" : "password"} value={form.password} onChange={set("password")} required minLength={8}
                autoComplete={login ? "current-password" : "new-password"} placeholder={login ? "" : "At least 8 characters"} />
              <button type="button" className="eye" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}>{show ? "Hide" : "Show"}</button>
            </span>
          </label>
          {error && <p className="error" role="alert">{error}</p>}
          <button className="btn primary wide" disabled={busy}>
            {busy ? "Please wait…" : login ? "Sign in" : "Create account"}
          </button>
          <p className="switch">
            {login ? "New to vaaniAI?" : "Already have an account?"}{" "}
            <button type="button" className="link" onClick={() => { setMode(login ? "register" : "login"); setError(""); }}>
              {login ? "Create an account" : "Sign in"}
            </button>
          </p>
          <p className="fine">A screening aid, not a diagnosis. Recordings stay private to your account.</p>
        </form>
      </section>
    </div>
  );
}
