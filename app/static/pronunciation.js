let currentAudio = null;
let currentAudioUrl = null;
let pronunciationNotice = null;

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

function ensurePronunciationNotice() {
  if (pronunciationNotice) {
    return pronunciationNotice;
  }
  pronunciationNotice = document.createElement("div");
  pronunciationNotice.className = "pronunciation-notice";
  pronunciationNotice.hidden = true;
  document.body.appendChild(pronunciationNotice);
  return pronunciationNotice;
}

function showPronunciationNotice(message) {
  const notice = ensurePronunciationNotice();
  notice.textContent = message;
  notice.hidden = false;
  window.clearTimeout(showPronunciationNotice.timeoutId);
  showPronunciationNotice.timeoutId = window.setTimeout(() => {
    notice.hidden = true;
  }, 2600);
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
    cleanupCurrentAudio();
    showPronunciationNotice("Pronunciation is temporarily unavailable.");
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
