import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const TOKEN = "jeton-de-test";

// Le jeton est lu au chargement d'api.js : chaque test recharge les modules
// après avoir placé le jeton dans l'adresse, comme au lancement local.
async function loadPlayer() {
  vi.resetModules();
  history.replaceState(null, "", `/#token=${TOKEN}`);
  return import("./player.js");
}

describe("lecteur de samples", () => {
  let played;

  beforeEach(() => {
    sessionStorage.clear();
    played = [];
    vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(function () {
      played.push(this.src);
      return Promise.resolve();
    });
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
    let n = 0;
    URL.createObjectURL = vi.fn(() => `blob:sample-${++n}`);
    URL.revokeObjectURL = vi.fn();
    globalThis.fetch = vi.fn(async () => new Response(new Blob(["RIFF"], { type: "audio/wav" })));
  });

  afterEach(() => vi.restoreAllMocks());

  it("demande le WAV avec le jeton et le lit depuis un blob", async () => {
    const { toggle } = await loadPlayer();
    await toggle(8072);
    expect(fetch).toHaveBeenCalledWith("/api/samples/8072/wav", expect.objectContaining({
      headers: expect.objectContaining({ "X-KitManager-Token": TOKEN }),
    }));
    expect(played).toEqual(["blob:sample-1"]);
  });

  it("libère le blob du sample précédent", async () => {
    const { toggle } = await loadPlayer();
    await toggle(8071);
    await toggle(8072);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:sample-1");
    expect(played).toEqual(["blob:sample-1", "blob:sample-2"]);
  });

  it("un second clic sur le sample en cours l'arrête", async () => {
    const { toggle, onPlaying } = await loadPlayer();
    const states = [];
    onPlaying((id) => states.push(id));
    await toggle(8072);
    await toggle(8072);
    expect(states).toEqual([null, 8072, null]);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("si le chargement échoue, rien n'est marqué en lecture", async () => {
    fetch.mockResolvedValue(new Response("{}", { status: 404 }));
    const { toggle, onPlaying } = await loadPlayer();
    const states = [];
    onPlaying((id) => states.push(id));
    await toggle(7903);
    expect(states.at(-1)).toBeNull();
    expect(played).toEqual([]);
  });
});
