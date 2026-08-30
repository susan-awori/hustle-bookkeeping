let speaking = false;

export function stopSpeaking() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  speaking = false;
}

export function speakText(text, language = "sw") {
  if (typeof window === "undefined" || !window.speechSynthesis || !text?.trim()) {
    return Promise.resolve();
  }
  stopSpeaking();
  const utterance = new SpeechSynthesisUtterance(text.trim());
  utterance.lang = language === "sw" ? "sw-KE" : "en-KE";
  utterance.rate = 0.95;
  return new Promise((resolve) => {
    utterance.onend = () => {
      speaking = false;
      resolve();
    };
    utterance.onerror = () => {
      speaking = false;
      resolve();
    };
    speaking = true;
    window.speechSynthesis.speak(utterance);
  });
}

export function echoTranscript(transcript, language = "sw") {
  const text =
    language === "sw"
      ? `Nilisikia: ${transcript}. Sahihi? Unaweza kuhariri hapa chini.`
      : `I heard: ${transcript}. Is that correct? You can edit it below.`;
  return speakText(text, language);
}
