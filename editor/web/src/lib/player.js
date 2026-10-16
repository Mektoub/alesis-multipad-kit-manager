// Lecteur unique : lancer un sample arrête le précédent.
import { api } from "./api.js";

const audio = new Audio();
let current = null;
const listeners = new Set();

function notify() {
  for (const fn of listeners) fn(current);
}

audio.addEventListener("ended", () => {
  current = null;
  notify();
});

export function toggle(id) {
  if (current === id) {
    audio.pause();
    current = null;
  } else {
    audio.src = api.wavUrl(id);
    audio.play();
    current = id;
  }
  notify();
}

export function onPlaying(fn) {
  listeners.add(fn);
  fn(current);
  return () => listeners.delete(fn);
}
