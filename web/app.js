// Hustle Web App Logic - 100% Real Live Backend Data
const API_BASE = 'https://hustle-bookkeeping.onrender.com';

let isEnglish = true;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let pendingEntry = null;
let posAmountStr = '';

// Start with empty ledger items array (NO dummy data)
let ledgerItems = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  fetchLedger();
  updateUI();
});

// Localization Translations
const i18n = {
  en: {
    salesToday: "Today Sales",
    debtsOwed: "Debts Owed",
    micTap: "Tap Microphone to Record Voice",
    micListening: "🎙️ Recording live microphone...",
    promptsTitle: "QUICK PROMPTS (SHORTCUTS):",
    outputTitle: "ELEVENLABS / CLAUDE OUTPUT:",
    saveBtn: "Save to Real Database 📗",
    ledgerTitle: "Sales History",
    addPos: "+ Add Sale",
    posTitle: "Quick Sale Entry",
    posPlaceholder: "Item name (e.g. Sugar 1kg)",
    posSubmit: "Save Sale 💸",
    customer: "Customer",
    debtorWa: "Send WhatsApp Reminder",
    emptyState: "No transactions recorded yet. Tap the microphone or Add Sale button."
  },
  sw: {
    salesToday: "Mauzo Leo",
    debtsOwed: "Madeni",
    micTap: "Bofya Maikrofoni Kurekodi",
    micListening: "🎙️ Inasikiliza sauti...",
    promptsTitle: "MIFANO YA HARAKA:",
    outputTitle: "ELEVENLABS / CLAUDE HESABU:",
    saveBtn: "Hifadhi kwa Database 📗",
    ledgerTitle: "Orodha ya Mauzo",
    addPos: "+ Ongeza Mauzo",
    posTitle: "Weka Mauzo ya Haraka",
    posPlaceholder: "Jina la bidhaa (e.g. Sukari 1kg)",
    posSubmit: "Hifadhi Mauzo 💸",
    customer: "Mteja",
    debtorWa: "Tuma Ukumbusho wa WhatsApp",
    emptyState: "Bado hakuna hesabu. Bofya maikrofoni kuanza kurekodi."
  }
};

function toggleLanguage() {
  isEnglish = !isEnglish;
  document.getElementById('lang-btn').innerText = isEnglish ? '🇬🇧 ENG' : '🇰🇪 SWA';
  updateUI();
}

function updateUI() {
  const t = isEnglish ? i18n.en : i18n.sw;
  document.getElementById('lbl-sales-today').innerText = t.salesToday;
  document.getElementById('lbl-debts-owed').innerText = t.debtsOwed;
  if (!isRecording) {
    document.getElementById('mic-status').innerText = t.micTap;
  }
  document.getElementById('lbl-prompts-title').innerText = t.promptsTitle;
  document.getElementById('lbl-output-title').innerText = t.outputTitle;
  document.getElementById('btn-save-ledger').innerText = t.saveBtn;
  document.getElementById('lbl-ledger-title').innerText = t.ledgerTitle;
  document.getElementById('btn-add-pos').innerText = t.addPos;
  document.getElementById('lbl-pos-title').innerText = t.posTitle;
  document.getElementById('pos-desc').placeholder = t.posPlaceholder;
  document.getElementById('btn-submit-pos').innerText = t.posSubmit;

  renderLedger();
  renderStats();
}

function renderStats() {
  let sales = 0;
  let debts = 0;
  ledgerItems.forEach(i => {
    if (i.entry_type === 'sale') sales += Number(i.amount_kes);
    if (i.entry_type === 'credit_given' && !i.is_settled) debts += Number(i.amount_kes);
  });
  document.getElementById('val-sales').innerText = `KES ${sales.toLocaleString()}`;
  document.getElementById('val-debts').innerText = `KES ${debts.toLocaleString()}`;
}

function renderLedger() {
  const listEl = document.getElementById('ledger-list');
  listEl.innerHTML = '';

  const t = isEnglish ? i18n.en : i18n.sw;

  if (ledgerItems.length === 0) {
    listEl.innerHTML = `
      <div style="text-align:center; padding:32px 16px; color:var(--text-muted); font-size:16px;">
        ${t.emptyState}
      </div>
    `;
    return;
  }

  ledgerItems.forEach(item => {
    const isSale = item.entry_type === 'sale';
    const isDebt = item.entry_type === 'credit_given';
    const div = document.createElement('div');
    div.className = 'ledger-item';

    const subText = item.counterparty_name || item.counterpartyName
      ? `${t.customer}: ${item.counterparty_name || item.counterpartyName}`
      : 'M-Pesa · Cash';

    let actionBtn = '';
    if (isDebt && !item.is_settled) {
      const waText = encodeURIComponent(
        isEnglish
          ? `Hello ${item.counterparty_name || "Customer"}, friendly reminder for debt of KES ${item.amount_kes} (${item.item_description}). Thank you!`
          : `Hujambo ${item.counterparty_name || "Mteja"}, huu ni ukumbusho wa deni ya KES ${item.amount_kes} (${item.item_description}). Asante!`
      );
      actionBtn = `<a href="https://wa.me/?text=${waText}" target="_blank" class="wa-btn">${t.debtorWa}</a>`;
    }

    div.innerHTML = `
      <div>
        <div class="ledger-title">${item.item_description}</div>
        <div class="ledger-sub">${subText}</div>
      </div>
      <div style="display:flex; align-items:center; gap:12px;">
        <div class="ledger-amount" style="color: ${isSale ? 'var(--primary-green)' : isDebt ? 'var(--accent-gold)' : 'var(--danger-red)'}">
          KES ${Number(item.amount_kes).toLocaleString()}
        </div>
        ${actionBtn}
      </div>
    `;
    listEl.appendChild(div);
  });
}

// Fetch 100% live ledger entries from real backend database
async function fetchLedger() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/ledger`);
    if (res.ok) {
      const data = await res.json();
      ledgerItems = data.items || [];
      renderLedger();
      renderStats();
    }
  } catch (err) {
    console.error('Fetch ledger error:', err);
  }
}

// Mic Recording via Web Audio API
async function toggleMicRecording() {
  const micBtn = document.getElementById('mic-btn');
  const micStatus = document.getElementById('mic-status');
  const t = isEnglish ? i18n.en : i18n.sw;

  if (isRecording) {
    isRecording = false;
    micBtn.classList.remove('recording');
    micStatus.innerText = t.micTap;
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  } else {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert(isEnglish ? "Microphone access is not supported on this browser." : "Maikrofoni haitumiki kwenye browser hii.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        uploadAudioToBackend(audioBlob);
      };
      mediaRecorder.start();
      isRecording = true;
      micBtn.classList.add('recording');
      micStatus.innerText = t.micListening;
    } catch (err) {
      alert(isEnglish ? "Please allow microphone permissions." : "Tafadhali ruhusu maikrofoni.");
    }
  }
}

// Upload live audio recording to FastAPI -> ElevenLabs -> Claude
async function uploadAudioToBackend(blob) {
  const formData = new FormData();
  formData.append('audio', blob, 'recording.webm');

  document.getElementById('output-card').style.display = 'flex';
  document.getElementById('output-transcript').innerText = isEnglish ? 'Processing voice audio with ElevenLabs & Claude...' : 'Inachambua sauti na ElevenLabs...';

  try {
    const res = await fetch(`${API_BASE}/api/v1/voice/parse`, {
      method: 'POST',
      body: formData
    });
    if (res.ok) {
      const data = await res.json();
      displayParsedResult(data.transcript, data.entries);
      return;
    }
  } catch (err) {
    console.error('API Voice parse error:', err);
  }
}

function displayParsedResult(transcript, entries) {
  document.getElementById('output-transcript').innerText = `"${transcript}"`;
  if (entries && entries.length > 0) {
    const e = entries[0];
    pendingEntry = e;
    document.getElementById('parsed-item-desc').innerText = e.item_description;
    document.getElementById('parsed-item-sub').innerText = e.counterparty_name ? `Customer: ${e.counterparty_name}` : `Type: ${e.entry_type.toUpperCase()}`;
    document.getElementById('parsed-item-amt').innerText = `KES ${e.amount_kes}`;
  }
}

// Save parsed entry to real backend database
async function saveToLedger() {
  if (!pendingEntry) return;

  try {
    const res = await fetch(`${API_BASE}/api/v1/ledger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pendingEntry)
    });

    if (res.ok) {
      document.getElementById('output-card').style.display = 'none';
      pendingEntry = null;
      await fetchLedger(); // Re-fetch live items from real DB
    }
  } catch (err) {
    console.error('Save entry error:', err);
  }
}

// Modal POS Quick Entry
function openPosModal() {
  document.getElementById('pos-modal').classList.add('active');
  posAmountStr = '';
  document.getElementById('pos-amount').innerText = 'KES 0';
  document.getElementById('pos-desc').value = '';
}

function closePosModal() {
  document.getElementById('pos-modal').classList.remove('active');
}

function keypadPress(key) {
  if (key === 'C') posAmountStr = '';
  else if (key === '⌫') posAmountStr = posAmountStr.slice(0, -1);
  else posAmountStr += key;

  document.getElementById('pos-amount').innerText = posAmountStr.length > 0 ? `KES ${posAmountStr}` : 'KES 0';
}

async function submitPosSale() {
  const desc = document.getElementById('pos-desc').value.trim();
  if (!desc || !posAmountStr) return;

  const newEntry = {
    entry_type: 'sale',
    item_description: desc,
    amount_kes: Number(posAmountStr),
    counterparty_name: null,
    is_settled: true
  };

  try {
    const res = await fetch(`${API_BASE}/api/v1/ledger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newEntry)
    });

    if (res.ok) {
      closePosModal();
      await fetchLedger(); // Re-fetch live items from real DB
    }
  } catch (err) {
    console.error('Submit POS sale error:', err);
  }
}
