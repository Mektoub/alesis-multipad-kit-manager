<script>
  import { onMount } from "svelte";
  import { api } from "./lib/api.js";
  import KitEditor from "./lib/KitEditor.svelte";
  import SamplePicker from "./lib/SamplePicker.svelte";

  let meta = $state(null);
  let backups = $state([]);
  let session = $state(null); // état renvoyé par /api/state
  let samples = $state([]);
  let currentNum = $state(null);
  let kit = $state(null);
  let selected = $state(0);
  let hideEmpty = $state(false);
  let error = $state("");
  let notice = $state("");
  let picking = $state(null); // "wave_a" | "wave_b" | null
  let savePath = $state("");
  let saving = $state(false);
  let syncing = $state(false);
  let chosenBackup = $state("");

  let sampleIndex = $derived(new Map(samples.map((s) => [s.id, s])));
  let visibleKits = $derived(
    (session?.kits ?? []).filter((k) => !hideEmpty || k.name !== "Empty" || k.num === currentNum),
  );

  // Synchronisation : chaque modification du kit est envoyée au serveur après
  // un court délai ; la réponse (kit relu) remplace la copie locale.
  let lastSynced = "";
  let timer;
  $effect(() => {
    if (!kit) return;
    const snapshot = JSON.stringify(kit);
    if (snapshot === lastSynced) return;
    clearTimeout(timer);
    timer = setTimeout(() => push(currentNum, snapshot), 350);
  });

  async function push(num, snapshot) {
    syncing = true;
    try {
      const saved = await api.saveKit(num, JSON.parse(snapshot));
      error = "";
      if (num !== currentNum) return;
      lastSynced = JSON.stringify(saved);
      if (JSON.stringify(kit) === snapshot) kit = saved;
      session.dirty = true;
      const entry = session.kits.find((k) => k.num === num);
      if (entry) entry.name = saved.name;
    } catch (err) {
      error = `Modification refusée : ${err.message}`;
      if (num === currentNum) await loadKit(num, false);
    } finally {
      syncing = false;
    }
  }

  async function loadKit(num, resetSlot = true) {
    const data = await api.kit(num);
    lastSynced = JSON.stringify(data);
    currentNum = num;
    kit = data;
    if (resetSlot) selected = 0;
  }

  function nextName(path) {
    const existing = new Set(backups.map((b) => b.path));
    const m = path.match(/^(.*?)(\d+)(\.\w+)$/);
    if (!m) return path.replace(/(\.\w+)$/, "_modifie$1");
    let n = Number(m[2]);
    let candidate;
    do {
      n += 1;
      candidate = `${m[1]}${String(n).padStart(m[2].length, "0")}${m[3]}`;
    } while (existing.has(candidate));
    return candidate;
  }

  async function openBackup(path) {
    if (session?.dirty && !confirm("Des modifications ne sont pas enregistrées. Ouvrir quand même ?")) return;
    error = notice = "";
    try {
      session = await api.open(path);
      samples = await api.samples();
      savePath = nextName(session.path);
      const first = session.kits.find((k) => k.name !== "Empty") ?? session.kits[0];
      await loadKit(first.num);
    } catch (err) {
      error = err.message;
    }
  }

  async function save(overwrite = false) {
    saving = true;
    error = notice = "";
    try {
      await new Promise((r) => setTimeout(r, 400)); // laisse partir la dernière modification
      session = await api.save(savePath, overwrite);
      notice = `Enregistré dans ${session.path}`;
      backups = await api.backups();
      savePath = nextName(session.path);
    } catch (err) {
      if (err.status === 409 && confirm(`${err.message}\nL'écraser ?`)) return save(true);
      error = err.message;
    } finally {
      saving = false;
    }
  }

  async function uploadSample(file) {
    const added = await api.addSample(file);
    samples = await api.samples();
    session.dirty = true;
    session.user_samples += 1;
    return added;
  }

  function selectSample(id) {
    kit.slots[selected][picking].sample = id;
    picking = null;
  }

  function beforeunload(e) {
    if (session?.dirty) e.preventDefault();
  }

  onMount(async () => {
    try {
      [meta, backups, session] = await Promise.all([api.meta(), api.backups(), api.state()]);
      chosenBackup = backups[0]?.path ?? "";
      if (session.path) {
        samples = await api.samples();
        savePath = nextName(session.path);
        const first = session.kits.find((k) => k.name !== "Empty") ?? session.kits[0];
        await loadKit(first.num);
      }
    } catch (err) {
      error = `Serveur injoignable : ${err.message}`;
    }
  });
</script>

<svelte:window onbeforeunload={beforeunload} />

<header class="top">
  <h1>Strike Kit Editor</h1>
  <div class="open">
    <select bind:value={chosenBackup} aria-label="Sauvegarde à ouvrir">
      {#each backups as b}<option value={b.path}>{b.path}</option>{/each}
      {#if !backups.length}<option value="">Aucune sauvegarde .bkf/.fac trouvée</option>{/if}
    </select>
    <button onclick={() => openBackup(chosenBackup)} disabled={!chosenBackup}>Ouvrir</button>
  </div>
  {#if session?.path}
    <div class="save">
      <span class="status" class:dirty={session.dirty}>
        {syncing ? "Synchronisation…" : session.dirty ? "Modifications non enregistrées" : "À jour"}
      </span>
      <input type="text" bind:value={savePath} aria-label="Fichier de destination" />
      <button class="primary" onclick={() => save()} disabled={saving}>Enregistrer sous</button>
    </div>
  {/if}
</header>

{#if error}<div class="banner error" role="alert">{error}<button onclick={() => (error = "")} aria-label="Fermer">✕</button></div>{/if}
{#if notice}<div class="banner ok" role="status">{notice}<button onclick={() => (notice = "")} aria-label="Fermer">✕</button></div>{/if}

{#if session?.path && meta}
  <main class="layout">
    <aside>
      <div class="aside-head">
        <h2>Kits</h2>
        <label class="muted"><input type="checkbox" bind:checked={hideEmpty} /> masquer les vides</label>
      </div>
      <p class="muted info">{session.path} · {session.kind} · {session.user_samples} sample(s) perso</p>
      <ul>
        {#each visibleKits as k (k.num)}
          <li>
            <button class:active={k.num === currentNum} onclick={() => loadKit(k.num)}>
              <span class="num">{k.num}</span>
              <span class="kname" class:empty={k.name === "Empty"}>{k.name}</span>
            </button>
          </li>
        {/each}
      </ul>
    </aside>
    <section class="content">
      {#if kit}
        <KitEditor {kit} {meta} {sampleIndex} bind:selected onpick={(w) => (picking = w)} />
      {/if}
    </section>
  </main>
{:else if meta}
  <main class="welcome">
    <p>Choisissez une sauvegarde <code>.bkf</code> (kits et samples utilisateur) ou <code>.fac</code> puis cliquez sur <strong>Ouvrir</strong>.</p>
    <p class="muted">Les sauvegardes sont recherchées dans le dossier de travail : {session?.root}</p>
  </main>
{/if}

{#if picking && kit}
  <SamplePicker
    {samples}
    current={kit.slots[selected][picking].sample}
    onselect={selectSample}
    onclose={() => (picking = null)}
    onupload={uploadSample}
  />
{/if}

<style>
  .top {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 20px;
    padding: 10px 16px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
  }
  h1 {
    margin: 0;
    font-size: 17px;
  }
  .open,
  .save {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
  }
  .open select {
    max-width: 380px;
  }
  .save {
    margin-left: auto;
  }
  .save input {
    width: 300px;
    max-width: 50vw;
  }
  .status {
    font-size: 12px;
    color: var(--ok);
  }
  .status.dirty {
    color: var(--accent);
  }
  .banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
  }
  .banner button {
    border: 0;
    background: transparent;
  }
  .banner.error {
    background: var(--danger-bg);
    color: var(--danger);
  }
  .banner.ok {
    background: var(--panel-2);
    color: var(--ok);
  }
  .layout {
    display: grid;
    grid-template-columns: 260px 1fr;
    min-height: calc(100vh - 56px);
  }
  aside {
    border-right: 1px solid var(--border);
    background: var(--panel);
    padding: 12px;
    overflow-y: auto;
    max-height: calc(100vh - 56px);
    position: sticky;
    top: 0;
  }
  .aside-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .aside-head label {
    font-size: 12px;
  }
  .info {
    font-size: 12px;
    margin: 6px 0 10px;
    word-break: break-all;
  }
  aside ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  aside li button {
    width: 100%;
    display: flex;
    gap: 10px;
    border: 0;
    background: transparent;
    text-align: left;
  }
  aside li button.active {
    background: var(--panel-2);
    font-weight: 600;
  }
  .num {
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .kname.empty {
    color: var(--muted);
    font-style: italic;
  }
  .content {
    padding: 16px;
    min-width: 0;
  }
  .welcome {
    padding: 40px 16px;
    text-align: center;
  }
  @media (max-width: 760px) {
    .layout {
      grid-template-columns: 1fr;
    }
    aside {
      position: static;
      max-height: 240px;
      border-right: 0;
      border-bottom: 1px solid var(--border);
    }
    .save {
      margin-left: 0;
      flex-wrap: wrap;
    }
  }
</style>
