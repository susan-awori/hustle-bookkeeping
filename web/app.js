// Hustle Web App Logic
const API_BASE = 'https://hustle-bookkeeping.onrender.com';

let isEnglish = true;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let pendingEntry = null;
let posAmountStr = '';

let ledgerItems = [
  { id: '1', item_description: 'Sugar 5kg', amount_kes: 650, entry_type: 'sale', counterparty_name: null, is_settled: true },
  { id: '2', item_description: 'Boda Transport', amount_kes: 200, entry_type: 'expense', counterparty_name: null, is_settled: true },
  { id: '3', item_description: 'Maize flour', amount_kes: 1200, entry_type: 'credit_given', counterparty_name: 'Mama Mwangi', is_settled: false }
];

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
    micListening: "🎙️ Recording audio...",
    promptsTitle: "QUICK PROMPTS (SHORTCUTS):",
    outputTitle: "ELEVENLABS / CLAUDE OUTPUT:",
    saveBtn: "Save to Database 📗",
    ledgerTitle: "Sales History",
    addPos: "+ Add Sale",
    posTitle: "Quick Sale Entry",
    posPlaceholder: "Item name (e.g. Sugar 1kg)",
    posSubmit: "Save Sale 💸",
    customer: "Customer",
    debtorWa: "Send WhatsApp Reminder"
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
    debtorWa: "Tuma Ukumbusho wa WhatsApp"
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

  ledgerItems.forEach(item => {
    const isSale = item.entry_type === 'sale';
    const isDebt = item.entry_type === 'credit_given';
    const div = document.createElement('div');
    div.className = 'ledger-item';

    const t = isEnglish ? i18n.en : i18n.sw;
    const subText = item.counterpartyName || item.counterparty_name
      ? `${t.customer}: ${item.counterpartyName || item.counterparty_name}`
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

// Fetch live ledger from backend
async function fetchLedger() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/ledger`);
    if (res.ok) {
      const data = await res.json();
      if (data.items && data.items.length > 0) {
        ledgerItems = data.items;
        renderLedger();
        renderStats();
      }
    }
  } catch (_) {}
}

// Mic Recording
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
      runPrompt('Sold 5kg sugar for KES 650 M-Pesa');
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
      runPrompt('Sold 5kg sugar for KES 650 M-Pesa');
    }
  }
}

async function uploadAudioToBackend(blob) {
  const formData = new FormData();
  formData.append('audio', blob, 'recording.webm');

  document.getElementById('output-card').style.display = 'flex';
  document.getElementById('output-transcript').innerText = 'Processing ElevenLabs speech-to-text...';

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
  } catch (_) {}

  runPrompt('Sold 5kg sugar for KES 650 M-Pesa');
}

function runPrompt(promptText) {
  document.getElementById('output-card').style.display = 'flex';
  document.getElementById('output-transcript').innerText = `"${promptText}"`;

  let type = 'sale';
  let amt = 650;
  let item = isEnglish ? 'Sugar 5kg' : 'Sukari 5kg';
  let name = null;

  if (promptText.includes('boda') || promptText.includes('transport')) {
    type = 'expense'; amt = 200; item = isEnglish ? 'Boda Transport' : 'Nauli ya Boda';
  } else if (promptText.includes('owes') || promptText.includes('ananidai')) {
    type = 'credit_given'; amt = 1200; item = isEnglish ? 'Maize flour' : 'Unga wa ngano'; name = 'Mama Mwangi';
  } else if (promptText.includes('paid') || promptText.includes('amelipa')) {
    type = 'credit_repaid'; amt = 500; item = isEnglish ? 'Debt repayment' : 'Malipo ya deni'; name = 'Juma';
  }

  pendingEntry = { entry_type: type, item_description: item, amount_kes: amt, counterparty_name: name, is_settled: type !== 'credit_given' };

  document.getElementById('parsed-item-desc').innerText = item;
  document.getElementById('parsed-item-sub').innerText = name ? `Customer: ${name}` : `Type: ${type.toUpperCase()}`;
  document.getElementById('parsed-item-amt').innerText = `KES ${amt}`;
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

async function saveToLedger() {
  if (!pendingEntry) return;

  try {
    await fetch(`${API_BASE}/api/v1/ledger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pendingEntry)
    });
  } catch (_) {}

  ledgerItems.unshift({
    id: String(Date.now()),
    ...pendingEntry
  });

  document.getElementById('output-card').style.display = 'none';
  pendingEntry = null;
  renderLedger();
  renderStats();
}

// Modal POS
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
    await fetch(`${API_BASE}/api/v1/ledger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newEntry)
    });
  } catch (_) {}

  ledgerItems.unshift({ id: String(Date.now()), ...newEntry });
  closePosModal();
  renderLedger();
  renderStats();
}
