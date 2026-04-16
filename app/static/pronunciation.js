function speakText(text) {
  if (!("speechSynthesis" in window) || !text) {
    return;
  }

  const synth = window.speechSynthesis;
  synth.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = 0.95;
  utterance.pitch = 1;

  const voices = synth.getVoices();
  const preferredVoice = voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith("en"));
  if (preferredVoice) {
    utterance.voice = preferredVoice;
  }

  synth.speak(utterance);
}

function bindPronunciationButtons() {
  document.querySelectorAll("[data-pronounce]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const text = button.getAttribute("data-pronounce");
      speakText(text);
    });
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bindPronunciationButtons);
} else {
  bindPronunciationButtons();
}
