import { useCallback, useEffect, useRef, useState } from "react";
import { api, clearTokens, formatApiError, getAccess, setTokens } from "./api.js";
import { echoTranscript, speakText, stopSpeaking } from "./speech.js";

const LABELS = {
  en: { sale: "Sale", expense: "Expense", credit_given: "Credit", credit_repaid: "Debt repayment" },
  sw: { sale: "Mauzo", expense: "Matumizi", credit_given: "Deni", credit_repaid: "Malipo ya deni" },
};

const PAYMENT_LABELS = {
  en: { cash: "Cash", mpesa: "M-Pesa", credit: "Credit" },
  sw: { cash: "Pesa taslimu", mpesa: "M-Pesa", credit: "Deni" },
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
    listening: "Listening… e.g. sold tomatoes 200 cash, via M-Pesa, or on credit to Amina.",
    speakHint: "Tap, speak, then Hustle will repeat back what it heard.",
    saveVoice: "Save my voice for 30 days (optional)",
    conversation: "Conversation",
    you: "You",
    hustle: "Hustle",
    editTranscript: "Edit what you said",
    continueParse: "Yes, that's right",
    replayVoice: "Hear again",
    understood: "I could not understand — please include an amount.",
    save: "Yes, save to books",
    cancel: "Start over",
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
    typeEntry: "Or type your entry",
    typePlaceholder: "e.g. sold tomatoes 200 cash / via mpesa / on credit to Amina 300",
    typeSubmit: "Send to Hustle",
    speechUnavailable: "Browser speech not available — type below, or use Chrome/Edge.",
    heardHint: "Fix anything misheard, then continue.",
    parsedHint: "Hustle understood your entry like this. Save or edit again.",
    transcriptLabel: "What you said",
    payment: "Payment",
    creditOwed: "Credit owed",
    creditEmpty: "No outstanding credit.",
    creditTotal: "Total owed",
    markPaidCash: "Paid cash",
    markPaidMpesa: "Paid M-Pesa",
    repaying: "Updating…",
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
    listening: "Inasikiliza… mf. niliuza nyanya 200 cash, kwa mpesa, au deni kwa Amina 300.",
    speakHint: "Bofya, sema, kisha Hustle itarudia ulichosema.",
    saveVoice: "Hifadhi sauti yangu siku 30 (si lazima)",
    conversation: "Mazungumzo",
    you: "Wewe",
    hustle: "Hustle",
    editTranscript: "Hariri ulichosema",
    continueParse: "Sawa, ni hivyo",
    replayVoice: "Sikia tena",
    understood: "Sijaelewa vizuri — taja kiasi pia.",
    save: "Sawa, hifadhi vitabuni",
    cancel: "Anza upya",
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
    typeEntry: "Au andika maandishi",
    typePlaceholder: "mf. niliuza nyanya 200 cash / mpesa / deni kwa Amina 300",
    typeSubmit: "Tuma kwa Hustle",
    speechUnavailable: "Sauti ya browser haipatikani — andika hapa chini, au tumia Chrome/Edge.",
    heardHint: "Rekebisha kama kuna makosa, kisha endelea.",
    parsedHint: "Hustle imeelewa hivi. Hifadhi au hariri tena.",
    transcriptLabel: "Ulichosema",
    payment: "Malipo",
    creditOwed: "Deni linalosubiri",
    creditEmpty: "Hakuna deni lililobaki.",
    creditTotal: "Jumla ya deni",
    markPaidCash: "Amelipa cash",
    markPaidMpesa: "Amelipa M-Pesa",
    repaying: "Inasasisha…",
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
  const [conversationStep, setConversationStep] = useState("idle");
  const [editableTranscript, setEditableTranscript] = useState("");
  const [parseResult, setParseResult] = useState(null);
  const [typedEntry, setTypedEntry] = useState("");
  const [speechAvailable, setSpeechAvailable] = useState(
    () => Boolean(typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition)),
  );
  const [ledger, setLedger] = useState({ items: [], total: 0 });
  const [creditOwed, setCreditOwed] = useState({ items: [], total: 0, amount_due_kes: "0.00" });
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const recognitionRef = useRef(null);
  const liveDraftRef = useRef("");
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
    const [books, credit] = await Promise.all([
      api("/api/v1/ledger"),
      api("/api/v1/ledger/credit/outstanding"),
    ]);
    if (books.ok) setLedger(await books.json());
    if (credit.ok) setCreditOwed(await credit.json());
  }, []);

  useEffect(() => {
    if (authed) loadMeAndBooks();
  }, [authed, loadMeAndBooks]);

  function resetConversation() {
    stopSpeaking();
    setConversationStep("idle");
    setEditableTranscript("");
    setParseResult(null);
    setLiveDraft("");
    liveDraftRef.current = "";
    setTypedEntry("");
  }

  async function speakConfirmation(payload) {
    if (payload.confirmation_audio_base64 && audioRef.current) {
      audioRef.current.src = `data:${payload.audio_mime_type};base64,${payload.confirmation_audio_base64}`;
      audioRef.current.play().catch(() => speakText(payload.confirmation_text, language));
      return;
    }
    await speakText(payload.confirmation_text, language);
  }

  async function beginHeard(transcript) {
    const text = transcript.trim();
    if (!text) {
      setError(copy.audioError);
      return;
    }
    setError("");
    setEditableTranscript(text);
    setParseResult(null);
    setConversationStep("heard");
    await echoTranscript(text, language);
  }

  async function continueFromTranscript() {
    const text = editableTranscript.trim();
    if (!text || busy) return;
    setError("");
    setBusy(true);
    try {
      const response = await api("/api/v1/voice/parse-text", {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(formatApiError(payload, copy.audioError));
        return;
      }
      setParseResult(payload);
      setConversationStep("parsed");
      await speakConfirmation(payload);
    } catch (err) {
      setError(err.message || copy.serverError);
    } finally {
      setBusy(false);
    }
  }

  async function submitAuth(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const path = mode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
    const body = mode === "login" ? { phone_number: form.phone_number, pin: form.pin } : form;
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

  function startLiveDraft() {
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) {
      setSpeechAvailable(false);
      return;
    }
    const rec = new Speech();
    rec.lang = "en-KE";
    rec.interimResults = true;
    rec.continuous = true;
    rec.onresult = (event) => {
      let text = "";
      for (let i = 0; i < event.results.length; i += 1) {
        text += event.results[i][0].transcript + " ";
      }
      const trimmed = text.trim();
      liveDraftRef.current = trimmed;
      setLiveDraft(trimmed);
    };
    rec.onerror = () => setSpeechAvailable(false);
    rec.start();
    recognitionRef.current = rec;
  }

  function stopLiveDraft() {
    const rec = recognitionRef.current;
    if (!rec) return Promise.resolve();
    return new Promise((resolve) => {
      const done = () => resolve();
      rec.onend = done;
      rec.stop();
      window.setTimeout(done, 400);
    });
  }

  async function toggleMic() {
    setError("");
    if (recording) {
      await stopLiveDraft();
      mediaRef.current?.stop();
      setRecording(false);
      return;
    }
    resetConversation();
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
        if (liveDraftRef.current) {
          data.append("browser_transcript", liveDraftRef.current);
        }
        setBusy(true);
        try {
          const response = await api("/api/v1/voice/transcribe", { method: "POST", body: data });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            setError(formatApiError(payload, copy.audioError));
            return;
          }
          await beginHeard(payload.transcript);
        } catch (err) {
          setError(err.message || copy.serverError);
        } finally {
          setBusy(false);
        }
      };
      mediaRef.current = recorder;
      recorder.start();
      startLiveDraft();
      setRecording(true);
    } catch {
      setError(copy.micError);
    }
  }

  async function parseTypedEntry(event) {
    event.preventDefault();
    const text = typedEntry.trim();
    if (!text || busy) return;
    resetConversation();
    await beginHeard(text);
  }

  async function confirmBooks() {
    if (!parseResult?.entries?.length) return;
    setBusy(true);
    const response = await api("/api/v1/voice/confirm", {
      method: "POST",
      body: JSON.stringify({ transcript: editableTranscript, entries: parseResult.entries }),
    });
    setBusy(false);
    if (!response.ok) {
      setError(copy.saveError);
      return;
    }
    resetConversation();
    await loadMeAndBooks();
  }

  async function repayCredit(entryId, paymentMethod) {
    setBusy(true);
    setError("");
    const response = await api(`/api/v1/ledger/${entryId}/repay`, {
      method: "POST",
      body: JSON.stringify({ payment_method: paymentMethod }),
    });
    setBusy(false);
    if (!response.ok) {
      setError(copy.saveError);
      return;
    }
    await loadMeAndBooks();
  }

  function paymentLabel(method) {
    return PAYMENT_LABELS[language][method] || method;
  }

  function entryPaymentLabel(row) {
    if (row.entry_type === "credit_given" && !row.is_settled) {
      return PAYMENT_LABELS[language].credit;
    }
    return paymentLabel(row.payment_method);
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
        <p className="hint">{recording ? copy.listening : copy.speakHint}</p>
        {recording && liveDraft && <p className="live-draft">{liveDraft}</p>}
        <label className="optin">
          <input type="checkbox" checked={Boolean(me?.save_voice_notes)} onChange={toggleVoiceNotes} />
          {copy.saveVoice}
        </label>
        {!speechAvailable && <p className="hint">{copy.speechUnavailable}</p>}
        {conversationStep === "idle" && (
          <form className="type-entry" onSubmit={parseTypedEntry}>
            <label>
              {copy.typeEntry}
              <textarea
                rows={2}
                value={typedEntry}
                onChange={(e) => setTypedEntry(e.target.value)}
                placeholder={copy.typePlaceholder}
              />
            </label>
            <button className="ghost" type="submit" disabled={busy || !typedEntry.trim()}>
              {copy.typeSubmit}
            </button>
          </form>
        )}
      </section>

      {conversationStep !== "idle" && (
        <section className="card conversation">
          <h2>{copy.conversation}</h2>

          <div className="chat-bubble you-bubble">
            <p className="bubble-label">{copy.you}</p>
            <label>
              {copy.transcriptLabel}
              <textarea
                rows={3}
                value={editableTranscript}
                onChange={(e) => setEditableTranscript(e.target.value)}
                disabled={conversationStep === "parsed"}
              />
            </label>
          </div>

          {conversationStep === "heard" && (
            <div className="chat-bubble hustle-bubble">
              <p className="bubble-label">{copy.hustle}</p>
              <p className="bubble-text">
                {language === "sw"
                  ? `Nilisikia: "${editableTranscript}". Sahihi?`
                  : `I heard: "${editableTranscript}". Is that correct?`}
              </p>
            </div>
          )}

          {conversationStep === "parsed" && parseResult && (
            <>
              <div className="chat-bubble hustle-bubble">
                <p className="bubble-label">{copy.hustle}</p>
                <p className="bubble-text">{parseResult.confirmation_text}</p>
                <audio ref={audioRef} controls className="player" />
                <ul className="preview">
                  {parseResult.entries.map((entry, index) => (
                <li key={index}>
                  <strong>{LABELS[language][entry.entry_type]}</strong> · {entry.item_description} ·{" "}
                  {formatKes(entry.amount_kes)} · {paymentLabel(entry.payment_method)}
                  {entry.counterparty_name ? ` · ${entry.counterparty_name}` : ""}
                </li>
                  ))}
                </ul>
                {parseResult.needs_clarification && <p className="error">{copy.understood}</p>}
              </div>
              <p className="hint">{copy.parsedHint}</p>
            </>
          )}

          {conversationStep === "heard" && <p className="hint">{copy.heardHint}</p>}

          <div className="row conversation-actions">
            {conversationStep === "heard" && (
              <>
                <button
                  className="ghost"
                  type="button"
                  disabled={busy}
                  onClick={() => echoTranscript(editableTranscript, language)}
                >
                  {copy.replayVoice}
                </button>
                <button
                  className="primary"
                  type="button"
                  disabled={busy || !editableTranscript.trim()}
                  onClick={continueFromTranscript}
                >
                  {copy.continueParse}
                </button>
              </>
            )}
            {conversationStep === "parsed" && (
              <>
                <button
                  className="ghost"
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setConversationStep("heard");
                    setParseResult(null);
                    echoTranscript(editableTranscript, language);
                  }}
                >
                  {copy.editTranscript}
                </button>
                <button
                  className="primary"
                  type="button"
                  disabled={busy || !parseResult?.entries?.length}
                  onClick={confirmBooks}
                >
                  {copy.save}
                </button>
              </>
            )}
            <button className="ghost" type="button" disabled={busy} onClick={resetConversation}>
              {copy.cancel}
            </button>
          </div>
        </section>
      )}

      <section className="card credit-panel">
        <h2>
          {copy.creditOwed} ({creditOwed.total})
        </h2>
        {creditOwed.total > 0 && (
          <p className="credit-total">
            {copy.creditTotal}: {formatKes(creditOwed.amount_due_kes)}
          </p>
        )}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{copy.item}</th>
                <th>{copy.person}</th>
                <th>{copy.amount}</th>
                <th>{copy.date}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {creditOwed.items.map((row) => (
                <tr key={row.id}>
                  <td>{row.item_description}</td>
                  <td>{row.counterparty_name || "—"}</td>
                  <td>{formatKes(row.amount_kes)}</td>
                  <td>{new Date(row.created_at).toLocaleDateString("en-KE")}</td>
                  <td className="repay-actions">
                    <button
                      className="ghost"
                      type="button"
                      disabled={busy}
                      onClick={() => repayCredit(row.id, "cash")}
                    >
                      {busy ? copy.repaying : copy.markPaidCash}
                    </button>
                    <button
                      className="ghost"
                      type="button"
                      disabled={busy}
                      onClick={() => repayCredit(row.id, "mpesa")}
                    >
                      {busy ? copy.repaying : copy.markPaidMpesa}
                    </button>
                  </td>
                </tr>
              ))}
              {!creditOwed.items.length && (
                <tr>
                  <td colSpan={5}>{copy.creditEmpty}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>
          {copy.books} ({ledger.total})
        </h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{copy.type}</th>
                <th>{copy.item}</th>
                <th>{copy.amount}</th>
                <th>{copy.payment}</th>
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
                  <td>{entryPaymentLabel(row)}</td>
                  <td>{row.counterparty_name || "—"}</td>
                  <td>{new Date(row.created_at).toLocaleString("en-KE")}</td>
                </tr>
              ))}
              {!ledger.items.length && (
                <tr>
                  <td colSpan={6}>{copy.empty}</td>
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
