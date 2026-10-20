// Lecteur unique : lancer un sample arrête le précédent. Le WAV est téléchargé
// avec le jeton (api.wav), puis lu depuis une URL blob:, libérée au suivant.
import { api } from "./api.js";

const audio = new Audio();
let current = null;
let blobUrl = null;
let pending = 0; // numéro du dernier chargement demandé
const listeners = new Set();

function notify() {
  for (const fn of listeners) fn(current);
}

audio.addEventListener("ended", () => {
  current = null;
  notify();
});

export async function toggle(id) {
  const request = ++pending;
  if (current === id) {
    audio.pause();
    current = null;
    notify();
    return;
  }
  audio.pause();
  current = id;
  notify();
  try {
    const blob = await api.wav(id);
    if (request !== pending) return; // un autre clic est arrivé entre-temps
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    blobUrl = URL.createObjectURL(blob);
    audio.src = blobUrl;
    await audio.play();
  } catch (err) {
    if (request !== pending) return;
    console.warn(`Lecture du sample ${id} impossible : ${err.message}`);
    current = null;
    notify();
  }
}

export function onPlaying(fn) {
  listeners.add(fn);
  fn(current);
  return () => listeners.delete(fn);
}
