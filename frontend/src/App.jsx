import { useCallback, useEffect, useRef, useState } from "react";
import { api, clearTokens, formatApiError, getAccess, setTokens } from "./api.js";

const LABELS = {
  en: { sale: "Sale", expense: "Expense", credit_given: "Credit", credit_repaid: "Debt repayment" },
  sw: { sale: "Mauzo", expense: "Matumizi", credit_given: "Deni", credit_repaid: "Malipo ya deni" },
};

const COPY = {
  en: {
    language: "Kiswahili",
    kicker: "Kenya · voice bookkeeping",
    tagline: "Speak sales, expenses, and debts. Hustle keeps your books.",
    login: "Log in",
    register: "Register",
    name: "Name",
    phone: "Phone number",
    pin: "PIN (4–6 digits)",
    wait: "Please wait…",
    start: "Get started",
    logout: "Log out",
    stop: "Stop",
    speak: "Speak",
    listening: "Listening… speak naturally. Example: I sold tomatoes for two hundred shillings.",
    speakHint: "Tap, speak, then confirm the voice response.",
    saveVoice: "Save my voice for 30 days (optional)",
    transcript: "Transcript",
    translate: "Translate to English",
    translating: "Translating…",
    understood: "I could not understand — please say it again with the amount.",
    save: "Yes, save",
    cancel: "Cancel",
    books: "Books",
    type: "Type",
    item: "Item",
    amount: "Amount",
    person: "Person",
    date: "Date",
    empty: "No entries yet. Record your first sale.",
    loginError: "Could not log in",
    registerError: "Could not register",
    serverError: "Cannot reach the server. Is the API running?",
    audioError: "The audio was not understood. Try again.",
    micError: "Allow microphone access in your browser.",
    saveError: "Could not save.",
    translateError: "Could not translate text.",
  },
  sw: {
    language: "English",
    kicker: "Kenya · vitabu kwa sauti",
    tagline: "Sema mauzo, matumizi, na deni. Hustle inaandika vitabu.",
    login: "Ingia",
    register: "Jisajili",
    name: "Jina",
    phone: "Namba ya simu",
    pin: "PIN (tarakimu 4–6)",
    wait: "Subiri…",
    start: "Anza",
    logout: "Toka",
    stop: "Acha",
    speak: "Sema",
    listening: "Inasikiliza… sema kama kawaida. Mfano: niliuza nyanya kwa bob mia mbili.",
    speakHint: "Bofya, sema, kisha thibitisha sauti inayorudi.",
    saveVoice: "Hifadhi sauti yangu siku 30 (si lazima)",
    transcript: "Maandishi",
    translate: "Tafsiri kwa English",
    translating: "Inatafsiri…",
    understood: "Sijaelewa vizuri — sema tena na kiasi.",
    save: "Sawa, hifadhi",
    cancel: "Ghairi",
    books: "Vitabu",
    type: "Aina",
    item: "Bidhaa",
    amount: "Kiasi",
    person: "Mtu",
    date: "Tarehe",
    empty: "Bado hakuna maandishi. Sema mauzo ya kwanza.",
    loginError: "Haikuweza kuingia",
    registerError: "Haikuweza kusajili",
    serverError: "Haikuweza kuunganisha na server. API inaendesha?",
    audioError: "Sauti haikueleweka. Jaribu tena.",
    micError: "Ruhusu maikrofoni kwenye browser.",
    saveError: "Haikuweza kuhifadhi.",
    translateError: "Haikuweza kutafsiri maandishi.",
  },
};

function formatKes(value) {
  const [whole, frac = "00"] = String(value).split(".");
  return `KES ${whole}.${frac.padEnd(2, "0").slice(0, 2)}`;
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getAccess()));
  const [me, setMe] = useState(null);
  const [mode, setMode] = useState("login");
  const [language, setLanguage] = useState("sw");
  const [form, setForm] = useState({ phone_number: "", pin: "", display_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [liveDraft, setLiveDraft] = useState("");
  const [parseResult, setParseResult] = useState(null);
  const [translatedTranscript, setTranslatedTranscript] = useState("");
  const [translating, setTranslating] = useState(false);
  const [ledger, setLedger] = useState({ items: [], total: 0 });
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const recognitionRef = useRef(null);
  const audioRef = useRef(null);
  const copy = COPY[language];

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
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(formatApiError(data, mode === "login" ? copy.loginError : copy.registerError));
        return;
      }
      setTokens(data.access_token, data.refresh_token);
      setAuthed(true);
    } catch (err) {
      setError(err.message || copy.serverError);
    } finally {
      setBusy(false);
    }
  }

  async function translateTranscript() {
    if (!parseResult?.transcript || translating) return;
    setTranslating(true);
    setError("");
    const response = await api("/api/v1/voice/translate", {
      method: "POST",
      body: JSON.stringify({ text: parseResult.transcript }),
    });
    const payload = await response.json().catch(() => ({}));
    setTranslating(false);
    if (!response.ok) {
      setError(payload.detail || copy.translateError);
      return;
    }
    setTranslatedTranscript(payload.translation);
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
          setError(payload.detail || copy.audioError);
          return;
        }
        setParseResult(payload);
        setTranslatedTranscript("");
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
      setError(copy.micError);
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
      setError(copy.saveError);
      return;
    }
    setParseResult(null);
    setTranslatedTranscript("");
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
        <div className="language-switcher">
          <button className="ghost" onClick={() => setLanguage(language === "sw" ? "en" : "sw")}>
            {copy.language}
          </button>
        </div>
        <header className="hero">
          <p className="kicker">{copy.kicker}</p>
          <h1>Hustle</h1>
          <p className="lede">{copy.tagline}</p>
        </header>
        <form className="card" onSubmit={submitAuth}>
          <div className="tabs">
            <button type="button" className={mode === "login" ? "on" : ""} onClick={() => setMode("login")}>
              {copy.login}
            </button>
            <button type="button" className={mode === "register" ? "on" : ""} onClick={() => setMode("register")}>
              {copy.register}
            </button>
          </div>
          {mode === "register" && (
            <label>
              {copy.name}
              <input
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                required
              />
            </label>
          )}
          <label>
            {copy.phone}
            <input
              inputMode="tel"
              placeholder="0712 345 678"
              autoComplete="tel"
              value={form.phone_number}
              onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
              required
            />
          </label>
          <label>
            {copy.pin}
            <input
              type="password"
              inputMode="numeric"
              pattern="\d{4,6}"
              value={form.pin}
              onChange={(e) => setForm({ ...form, pin: e.target.value })}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />
          </label>
          {error && <p className="error">{String(error)}</p>}
          <button className="primary" disabled={busy} type="submit">
            {busy ? copy.wait : mode === "login" ? copy.login : copy.start}
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
        <div className="row header-actions">
          <button className="ghost" onClick={() => setLanguage(language === "sw" ? "en" : "sw")}>
            {copy.language}
          </button>
          <button
            className="ghost"
            onClick={() => {
              clearTokens();
              setAuthed(false);
            }}
          >
            {copy.logout}
          </button>
        </div>
      </header>

      <section className="mic-panel">
        <button
          type="button"
          className={`mic ${recording ? "hot" : ""}`}
          onClick={toggleMic}
          disabled={busy}
          aria-pressed={recording}
        >
          {recording ? copy.stop : copy.speak}
        </button>
        <p className="hint">
          {recording
            ? copy.listening
            : copy.speakHint}
        </p>
        <label className="optin">
          <input type="checkbox" checked={Boolean(me?.save_voice_notes)} onChange={toggleVoiceNotes} />
          {copy.saveVoice}
        </label>
      </section>

      <section className="card">
        <h2>{copy.transcript}</h2>
        <p className="transcript">{translatedTranscript || parseResult?.transcript || liveDraft || "—"}</p>
        {parseResult && (
          <>
            {!translatedTranscript && (
              <button className="ghost translate-button" disabled={translating || busy} onClick={translateTranscript}>
                {translating ? copy.translating : copy.translate}
              </button>
            )}
            <p className="confirm-text">{parseResult.confirmation_text}</p>
            <audio ref={audioRef} controls className="player" />
            <ul className="preview">
              {parseResult.entries.map((entry, index) => (
                <li key={index}>
                  <strong>{LABELS[language][entry.entry_type]}</strong> · {entry.item_description} · {formatKes(entry.amount_kes)}
                  {entry.counterparty_name ? ` · ${entry.counterparty_name}` : ""}
                </li>
              ))}
            </ul>
            {parseResult.needs_clarification && <p className="error">{copy.understood}</p>}
            <div className="row">
              <button className="primary" disabled={busy || !parseResult.entries.length} onClick={confirmBooks}>
                {copy.save}
              </button>
              <button
                className="ghost"
                onClick={() => {
                  setParseResult(null);
                  setTranslatedTranscript("");
                }}
              >
                {copy.cancel}
              </button>
            </div>
          </>
        )}
      </section>

      <section className="card">
        <h2>{copy.books} ({ledger.total})</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{copy.type}</th>
                <th>{copy.item}</th>
                <th>{copy.amount}</th>
                <th>{copy.person}</th>
                <th>{copy.date}</th>
              </tr>
            </thead>
            <tbody>
              {ledger.items.map((row) => (
                <tr key={row.id}>
                  <td>{LABELS[language][row.entry_type]}</td>
                  <td>{row.item_description}</td>
                  <td>{formatKes(row.amount_kes)}</td>
                  <td>{row.counterparty_name || "—"}</td>
                  <td>{new Date(row.created_at).toLocaleString("en-KE")}</td>
                </tr>
              ))}
              {!ledger.items.length && (
                <tr>
                  <td colSpan={5}>{copy.empty}</td>
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
