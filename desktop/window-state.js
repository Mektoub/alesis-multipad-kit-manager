// Taille, position et état maximisé de la fenêtre, gardés d'un lancement à
// l'autre dans <userData>/window-state.json. Au premier lancement, ou si le
// fichier est illisible, la fenêtre s'ouvre maximisée (1400×900 une fois
// restaurée) ; une position hors des écrans actuels (écran débranché) est
// abandonnée, la fenêtre est alors centrée.

import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";

export const DEFAULT_STATE = { width: 1400, height: 900, maximized: true };
// partie de la barre de titre qui doit rester sur un écran
const VISIBLE = { width: 100, height: 40 };

const isInt = (v) => Number.isInteger(v);

export function readWindowState(file) {
  try {
    const s = JSON.parse(readFileSync(file, "utf8"));
    if (!isInt(s.width) || !isInt(s.height) || s.width <= 0 || s.height <= 0) return { ...DEFAULT_STATE };
    const state = { width: s.width, height: s.height, maximized: s.maximized === true };
    if (isInt(s.x) && isInt(s.y)) Object.assign(state, { x: s.x, y: s.y });
    return state;
  } catch {
    return { ...DEFAULT_STATE };
  }
}

// Options de BrowserWindow : taille, et position si le haut de la fenêtre est
// sur l'une des zones de travail `workAreas` ({ x, y, width, height }).
export function windowBounds(state, workAreas) {
  const bounds = { width: state.width, height: state.height };
  if (state.x === undefined) return bounds;
  const visible = workAreas.some((a) => {
    const w = Math.min(state.x + state.width, a.x + a.width) - Math.max(state.x, a.x);
    const h = Math.min(state.y + VISIBLE.height, a.y + a.height) - Math.max(state.y, a.y);
    return w >= VISIBLE.width && h >= VISIBLE.height;
  });
  return visible ? { ...bounds, x: state.x, y: state.y } : bounds;
}

// Écriture atomique ; un échec (dossier non accessible) est sans conséquence.
export function writeWindowState(file, { x, y, width, height }, maximized) {
  try {
    mkdirSync(path.dirname(file), { recursive: true });
    writeFileSync(`${file}.tmp`, `${JSON.stringify({ x, y, width, height, maximized }, null, 2)}\n`);
    renameSync(`${file}.tmp`, file);
  } catch {
    // la fenêtre reprendra son état par défaut
  }
}
