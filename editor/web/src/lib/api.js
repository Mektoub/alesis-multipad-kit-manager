// Accès à l'API FastAPI. Les erreurs remontent avec le message `detail` du serveur.
//
// Chaque requête porte le jeton exigé par le serveur (en-tête X-KitManager-Token) :
// fourni par l'application Electron (window.kitManagerDesktop), ou, en lancement
// local, lu dans l'adresse (#token=…). Il est alors conservé pour l'onglet
// (sessionStorage), afin qu'un rechargement de la page fonctionne, et retiré
// de l'adresse affichée.

import { desktop } from "./desktop.js";

function readToken() {
  if (desktop?.token) return desktop.token;
  const fromHash = new URLSearchParams(location.hash.slice(1)).get("token");
  try {
    if (fromHash) {
      sessionStorage.setItem("kitmanager-token", fromHash);
      history.replaceState(null, "", location.pathname + location.search);
      return fromHash;
    }
    return sessionStorage.getItem("kitmanager-token") ?? "";
  } catch {
    return fromHash ?? "";
  }
}

const TOKEN = readToken();

// `blob` : réponse binaire (WAV) au lieu de JSON.
async function request(method, url, body, { blob = false } = {}) {
  const options = { method, headers: { "X-KitManager-Token": TOKEN } };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // réponse non JSON : on garde le statut HTTP
    }
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    err.status = res.status;
    throw err;
  }
  return blob ? res.blob() : res.json();
}

export const api = {
  state: () => request("GET", "/api/state"),
  meta: () => request("GET", "/api/meta"),
  open: (path, force = false) => request("POST", "/api/open", { path, force }),
  kit: (num) => request("GET", `/api/kits/${num}`),
  saveKit: (num, kit) => request("PUT", `/api/kits/${num}`, kit),
  copySlot: (num, body) => request("POST", `/api/kits/${num}/copy`, body),
  resetSlots: (num, body) => request("POST", `/api/kits/${num}/reset`, body),
  setSlots: (num, body) => request("POST", `/api/kits/${num}/set`, body),
  setSlotsInKits: (body) => request("POST", "/api/kits/set", body),
  transferKit: (num, body) => request("POST", `/api/kits/${num}/transfer`, body),
  clearKit: (num) => request("POST", `/api/kits/${num}/clear`),
  samples: () => request("GET", "/api/samples"),
  addSample: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("POST", "/api/samples", form);
  },
  // sans chemin : « Enregistrer » dans le fichier ouvert ; avec : « Enregistrer sous »
  save: (path = null, overwrite = false) => request("POST", "/api/save", path == null ? {} : { path, overwrite }),
  // WAV d'un sample utilisateur, en Blob : une balise audio ne pourrait pas
  // envoyer le jeton, l'interface le télécharge donc elle-même.
  wav: (id) => request("GET", `/api/samples/${id}/wav`, undefined, { blob: true }),
};
