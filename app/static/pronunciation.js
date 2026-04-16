let currentAudio = null;
let currentAudioUrl = null;

function cleanupCurrentAudio() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (currentAudioUrl) {
    URL.revokeObjectURL(currentAudioUrl);
    currentAudioUrl = null;
  }
}

function fallbackSpeakText(text) {
  if (!("speechSynthesis" in window) || !text) {
    return;
  }

  const synth = window.speechSynthesis;
  synth.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = 0.82;
  utterance.pitch = 0.88;
  utterance.volume = 0.9;
  synth.speak(utterance);
}

async function playGeneratedAudio(text) {
  const response = await fetch(`/api/pronounce?text=${encodeURIComponent(text)}`);
  if (!response.ok) {
    throw new Error(`Pronunciation request failed with ${response.status}`);
  }

  const blob = await response.blob();
  cleanupCurrentAudio();
  currentAudioUrl = URL.createObjectURL(blob);
  currentAudio = new Audio(currentAudioUrl);
  currentAudio.addEventListener("ended", cleanupCurrentAudio, { once: true });
  currentAudio.addEventListener("error", cleanupCurrentAudio, { once: true });
  await currentAudio.play();
}

async function speakText(text) {
  if (!text) {
    return;
  }

  try {
    await playGeneratedAudio(text);
  } catch (_error) {
    fallbackSpeakText(text);
  }
}

function bindPronunciationButtons() {
  document.querySelectorAll("[data-pronounce]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      const text = button.getAttribute("data-pronounce");
      await speakText(text);
    });
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bindPronunciationButtons);
} else {
  bindPronunciationButtons();
}
