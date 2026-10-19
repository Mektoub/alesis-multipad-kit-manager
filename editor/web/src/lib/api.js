// Accès à l'API FastAPI. Les erreurs remontent avec le message `detail` du serveur.

async function request(method, url, body) {
  const options = { method, headers: {} };
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
  return res.json();
}

export const api = {
  backups: () => request("GET", "/api/backups"),
  state: () => request("GET", "/api/state"),
  meta: () => request("GET", "/api/meta"),
  open: (path) => request("POST", "/api/open", { path }),
  kit: (num) => request("GET", `/api/kits/${num}`),
  saveKit: (num, kit) => request("PUT", `/api/kits/${num}`, kit),
  copySlot: (num, body) => request("POST", `/api/kits/${num}/copy`, body),
  transferKit: (num, body) => request("POST", `/api/kits/${num}/transfer`, body),
  samples: () => request("GET", "/api/samples"),
  addSample: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("POST", "/api/samples", form);
  },
  save: (path, overwrite = false) => request("POST", "/api/save", { path, overwrite }),
  wavUrl: (id) => `/api/samples/${id}/wav`,
};
