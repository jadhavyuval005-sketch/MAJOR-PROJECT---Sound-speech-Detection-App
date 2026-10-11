import { useEffect, useState } from "react";
import { api } from "./api.js";

export const LANG_LABEL = { hi: "Hindi", en: "English", mixed: "Hindi + English" };
export const BAND = {
  typical: { label: "Typical range", cls: "good" },
  monitor: { label: "Keep an eye on it", cls: "warn" },
  refer: { label: "Consider a specialist", cls: "bad" },
  not_scored: { label: "Not scored yet", cls: "muted-pill" },
};

export const ageText = (m) => `${Math.floor(m / 12)}y ${m % 12}m`;

export default function Dashboard({ onStart, onOpen }) {
  const [children, setChildren] = useState([]);
  const [assessments, setAssessments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", years: "", months: "0", home_language: "mixed" });
  const [adding, setAdding] = useState(false);

  const load = () =>
    Promise.all([api.children(), api.assessments()])
      .then(([c, a]) => { setChildren(c); setAssessments(a); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  async function addChild(e) {
    e.preventDefault();
    setError("");
    try {
      await api.addChild({
        name: form.name,
        age_months: Number(form.years) * 12 + Number(form.months),
        home_language: form.home_language,
      });
      setForm({ name: "", years: "", months: "0", home_language: "mixed" });
      setAdding(false);
      load();
    } catch (err) { setError(err.message); }
  }

  async function remove(child) {
    if (!confirm(`Delete ${child.name} and all their recordings? This cannot be undone.`)) return;
    try { await api.deleteChild(child.id); load(); } catch (err) { setError(err.message); }
  }

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <>
      <div className="row between">
        <h2>Children</h2>
        <button className="btn" onClick={() => setAdding(!adding)}>{adding ? "Close" : "Add a child"}</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}

      {adding && (
        <form className="card grid-form" onSubmit={addChild}>
          <label>Child's name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <label>Age (years)
            <input type="number" min="2" max="12" value={form.years} required
              onChange={(e) => setForm({ ...form, years: e.target.value })} />
          </label>
          <label>Months
            <input type="number" min="0" max="11" value={form.months}
              onChange={(e) => setForm({ ...form, months: e.target.value })} />
          </label>
          <label>Language at home
            <select value={form.home_language} onChange={(e) => setForm({ ...form, home_language: e.target.value })}>
              {Object.entries(LANG_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <button className="btn primary">Save</button>
        </form>
      )}

      {children.length === 0 && !adding && (
        <div className="card empty">
          <p>No children yet. Add a child to start a screening.</p>
        </div>
      )}

      <div className="cards">
        {children.map((c) => (
          <div className="card" key={c.id}>
            <h3>{c.name}</h3>
            <p className="muted">{ageText(c.age_months)} · {LANG_LABEL[c.home_language]}</p>
            <div className="row">
              <button className="btn primary" onClick={() => onStart(c, c.home_language)}>Start screening</button>
              <button className="link danger" onClick={() => remove(c)}>Delete</button>
            </div>
          </div>
        ))}
      </div>

      {assessments.length > 0 && (
        <>
          <h2>Past screenings</h2>
          <div className="card list">
            {assessments.map((a) => {
              const child = children.find((c) => c.id === a.child_id);
              const band = BAND[a.band];
              return (
                <button className="list-row" key={a.id} onClick={() => onOpen(a.id)}>
                  <span><strong>{child?.name}</strong> · {LANG_LABEL[a.language]}</span>
                  <span className="muted">{new Date(a.created_at).toLocaleDateString()}</span>
                  <span className={`pill ${band.cls}`}>
                    {a.status === "in_progress" ? "In progress" : band.label}
                  </span>
                </button>
              );
            })}
          </div>
        </>
      )}
    </>
  );
}
