import { useCallback, useEffect, useState } from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "./api.js";
import Auth from "./Auth.jsx";
import Dashboard from "./Dashboard.jsx";
import Assessment from "./Assessment.jsx";
import Results from "./Results.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(!!getToken());
  // view: {name: "dashboard"} | {name: "assess", child, language} | {name: "results", id}
  const [view, setView] = useState({ name: "dashboard" });

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setView({ name: "dashboard" });
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (getToken()) {
      api.me().then(setUser).catch(() => setToken(null)).finally(() => setBooting(false));
    }
  }, [logout]);

  const signedIn = ({ token, user }) => { setToken(token); setUser(user); };

  if (booting) return <div className="center muted">Loading…</div>;
  if (!user) return <Auth onSignedIn={signedIn} />;

  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => setView({ name: "dashboard" })}>
          <span className="logo">वा</span> vaaniAI
        </button>
        <div className="who">
          <span>{user.name}</span>
          <button className="link" onClick={logout}>Sign out</button>
        </div>
      </header>
      <main className="page">
        {view.name === "dashboard" && (
          <Dashboard
            onStart={(child, language) => setView({ name: "assess", child, language })}
            onOpen={(id) => setView({ name: "results", id })}
          />
        )}
        {view.name === "assess" && (
          <Assessment
            child={view.child}
            language={view.language}
            onDone={(id) => setView({ name: "results", id })}
            onCancel={() => setView({ name: "dashboard" })}
          />
        )}
        {view.name === "results" && (
          <Results id={view.id} onBack={() => setView({ name: "dashboard" })} />
        )}
      </main>
      <footer className="foot">
        A screening aid for parents and clinicians. It does not diagnose a speech sound disorder.
      </footer>
    </>
  );
}
