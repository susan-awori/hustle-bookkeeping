import { useCallback, useEffect, useRef, useState } from "react";
import { api, clearTokens, getAccess, setTokens } from "./api.js";

const LABELS = {
  sale: "Mauzo",
  expense: "Matumizi",
  credit_given: "Deni",
  credit_repaid: "Malipo ya deni",
};

function formatKes(value) {
  const [whole, frac = "00"] = String(value).split(".");
  return `KES ${whole}.${frac.padEnd(2, "0").slice(0, 2)}`;
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getAccess()));
  const [me, setMe] = useState(null);
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ phone_number: "", pin: "", display_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [liveDraft, setLiveDraft] = useState("");
  const [parseResult, setParseResult] = useState(null);
  const [ledger, setLedger] = useState({ items: [], total: 0 });
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const recognitionRef = useRef(null);
  const audioRef = useRef(null);

  const loadMeAndBooks = useCallback(async () => {
    const meRes = await api("/api/v1/auth/me");
    if (!meRes.ok) {
      clearTokens();
      setAuthed(false);
      return;
    }
    setMe(await meRes.json());
    const books = await api("/api/v1/ledger");
    if (books.ok) setLedger(await books.json());
  }, []);

  useEffect(() => {
    if (authed) loadMeAndBooks();
  }, [authed, loadMeAndBooks]);

  async function submitAuth(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const path = mode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
    const body =
      mode === "login"
        ? { phone_number: form.phone_number, pin: form.pin }
        : form;
    try {
      const response = await api(path, { method: "POST", body: JSON.stringify(body) });
      const responseText = await response.text();
      let data = {};
      try {
        data = responseText ? JSON.parse(responseText) : {};
      } catch {
        data = { raw: responseText };
      }
      if (!response.ok) {
        console.error("Hustle auth request failed", {
          path,
          status: response.status,
          body: data,
        });
        setError(data.detail?.[0]?.msg || data.detail || "Haikuweza kuingia");
        return;
      }
      setTokens(data.access_token, data.refresh_token);
      setAuthed(true);
    } catch (requestError) {
      console.error("Hustle auth request error", {
        path,
        message: requestError instanceof Error ? requestError.message : String(requestError),
        error: requestError,
      });
      setError("Haikuweza kuingia. Angalia console kwa maelezo.");
    } finally {
      setBusy(false);
    }
  }

  function startLiveDraft() {
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) return;
    const rec = new Speech();
    rec.lang = "sw-KE";
    rec.interimResults = true;
    rec.continuous = true;
    rec.onresult = (event) => {
      let text = "";
      for (let i = 0; i < event.results.length; i += 1) {
        text += event.results[i][0].transcript + " ";
      }
      setLiveDraft(text.trim());
    };
    rec.start();
    recognitionRef.current = rec;
  }

  async function toggleMic() {
    setError("");
    if (recording) {
      recognitionRef.current?.stop();
      mediaRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const data = new FormData();
        data.append("audio", blob, "take.webm");
        data.append("save_voice_notes", me?.save_voice_notes ? "true" : "false");
        setBusy(true);
        const response = await api("/api/v1/voice/parse", { method: "POST", body: data });
        const payload = await response.json().catch(() => ({}));
        setBusy(false);
        if (!response.ok) {
          setError(payload.detail || "Sauti haikueleweka. Jaribu tena.");
          return;
        }
        setParseResult(payload);
        if (payload.confirmation_audio_base64) {
          const src = `data:${payload.audio_mime_type};base64,${payload.confirmation_audio_base64}`;
          if (audioRef.current) {
            audioRef.current.src = src;
            audioRef.current.play().catch(() => {});
          }
        }
      };
      mediaRef.current = recorder;
      recorder.start();
      startLiveDraft();
      setParseResult(null);
      setLiveDraft("");
      setRecording(true);
    } catch {
      setError("Ruhusu maikrofoni kwenye browser.");
    }
  }

  async function confirmBooks() {
    if (!parseResult?.entries?.length) return;
    setBusy(true);
    const response = await api("/api/v1/voice/confirm", {
      method: "POST",
      body: JSON.stringify({ transcript: parseResult.transcript, entries: parseResult.entries }),
    });
    setBusy(false);
    if (!response.ok) {
      setError("Haikuweza kuhifadhi.");
      return;
    }
    setParseResult(null);
    setLiveDraft("");
    await loadMeAndBooks();
  }

  async function toggleVoiceNotes() {
    const next = !me.save_voice_notes;
    const response = await api("/api/v1/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ save_voice_notes: next }),
    });
    if (response.ok) setMe(await response.json());
  }

  if (!authed) {
    return (
      <main className="shell">
        <header className="hero">
          <p className="kicker">Kenya · vitabu kwa sauti</p>
          <h1>Hustle</h1>
          <p className="lede">Sema mauzo, matumizi, na deni. Hustle inaandika vitabu.</p>
        </header>
        <form className="card" onSubmit={submitAuth}>
          <div className="tabs">
            <button type="button" className={mode === "login" ? "on" : ""} onClick={() => setMode("login")}>
              Ingia
            </button>
            <button type="button" className={mode === "register" ? "on" : ""} onClick={() => setMode("register")}>
              Jisajili
            </button>
          </div>
          {mode === "register" && (
            <label>
              Jina
              <input
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                required
              />
            </label>
          )}
          <label>
            Namba ya simu
            <input
              inputMode="tel"
              placeholder="0712 345 678"
              value={form.phone_number}
              onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
              required
            />
          </label>
          <label>
            PIN (tarakimu 4–6)
            <input
              type="password"
              inputMode="numeric"
              pattern="\d{4,6}"
              value={form.pin}
              onChange={(e) => setForm({ ...form, pin: e.target.value })}
              required
            />
          </label>
          {error && <p className="error">{String(error)}</p>}
          <button className="primary" disabled={busy} type="submit">
            {busy ? "Subiri…" : mode === "login" ? "Ingia" : "Anza"}
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="shell">
      <header className="top">
        <div>
          <p className="kicker">Hustle</p>
          <h1>{me?.display_name || "Mfanyabiashara"}</h1>
        </div>
        <button
          className="ghost"
          onClick={() => {
            clearTokens();
            setAuthed(false);
          }}
        >
          Toka
        </button>
      </header>

      <section className="mic-panel">
        <button
          type="button"
          className={`mic ${recording ? "hot" : ""}`}
          onClick={toggleMic}
          disabled={busy}
          aria-pressed={recording}
        >
          {recording ? "Acha" : "Sema"}
        </button>
        <p className="hint">
          {recording
            ? "Inasikiliza… sema kama kawaida. Mfano: niliuza nyanya kwa bob mia mbili."
            : "Bofya, sema, kisha thibitisha sauti inayorudi."}
        </p>
        <label className="optin">
          <input type="checkbox" checked={Boolean(me?.save_voice_notes)} onChange={toggleVoiceNotes} />
          Hifadhi sauti yangu siku 30 (si lazima)
        </label>
      </section>

      <section className="card">
        <h2>Transcript</h2>
        <p className="transcript">{parseResult?.transcript || liveDraft || "—"}</p>
        {parseResult && (
          <>
            <p className="confirm-text">{parseResult.confirmation_text}</p>
            <audio ref={audioRef} controls className="player" />
            <ul className="preview">
              {parseResult.entries.map((entry, index) => (
                <li key={index}>
                  <strong>{LABELS[entry.entry_type]}</strong> · {entry.item_description} · {formatKes(entry.amount_kes)}
                  {entry.counterparty_name ? ` · ${entry.counterparty_name}` : ""}
                </li>
              ))}
            </ul>
            {parseResult.needs_clarification && <p className="error">Sijaelewa vizuri — sema tena na kiasi.</p>}
            <div className="row">
              <button className="primary" disabled={busy || !parseResult.entries.length} onClick={confirmBooks}>
                Sawa, hifadhi
              </button>
              <button className="ghost" onClick={() => setParseResult(null)}>
                Ghairi
              </button>
            </div>
          </>
        )}
      </section>

      <section className="card">
        <h2>Vitabu ({ledger.total})</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Aina</th>
                <th>Bidhaa</th>
                <th>Kiasi</th>
                <th>Mtu</th>
                <th>Tarehe</th>
              </tr>
            </thead>
            <tbody>
              {ledger.items.map((row) => (
                <tr key={row.id}>
                  <td>{LABELS[row.entry_type]}</td>
                  <td>{row.item_description}</td>
                  <td>{formatKes(row.amount_kes)}</td>
                  <td>{row.counterparty_name || "—"}</td>
                  <td>{new Date(row.created_at).toLocaleString("en-KE")}</td>
                </tr>
              ))}
              {!ledger.items.length && (
                <tr>
                  <td colSpan={5}>Bado hakuna maandishi. Sema mauzo ya kwanza.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      {error && <p className="error">{String(error)}</p>}
    </main>
  );
}
