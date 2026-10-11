// Thin wrapper around fetch for the Flask API. The JWT lives in localStorage.
const KEY = "ssd_token";

export const getToken = () => {
  try { return localStorage.getItem(KEY); } catch { return null; }
};
export const setToken = (t) => {
  try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY); } catch { /* private mode */ }
};

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

async function request(path, { method = "GET", json, form, raw } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (json) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(`/api${path}`, { method, headers, body: json ? JSON.stringify(json) : form });
  } catch {
    throw new Error("Cannot reach the server. Check your connection and try again.");
  }
  if (res.status === 204) return null;
  if (raw && res.ok) return res.blob();
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized();
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  register: (b) => request("/auth/register", { method: "POST", json: b }),
  login: (b) => request("/auth/login", { method: "POST", json: b }),
  me: () => request("/auth/me"),
  children: () => request("/children"),
  addChild: (b) => request("/children", { method: "POST", json: b }),
  deleteChild: (id) => request(`/children/${id}`, { method: "DELETE" }),
  words: (language) => request(`/words?language=${language}`),
  assessments: (childId) => request(`/assessments${childId ? `?child_id=${childId}` : ""}`),
  startAssessment: (child_id, language) =>
    request("/assessments", { method: "POST", json: { child_id, language } }),
  assessment: (id) => request(`/assessments/${id}`),
  uploadRecording: (assessmentId, wordId, wavBlob) => {
    const form = new FormData();
    form.append("word_id", wordId);
    form.append("audio", wavBlob, `${wordId}.wav`);
    return request(`/assessments/${assessmentId}/recordings`, { method: "POST", form });
  },
  completeAssessment: (id) => request(`/assessments/${id}/complete`, { method: "POST" }),
  rateRecording: (id, clinician_correct) =>
    request(`/recordings/${id}`, { method: "PATCH", json: { clinician_correct } }),
  recordingAudio: (id) => request(`/recordings/${id}/audio`, { raw: true }),
};
