<script>
  // Gestionnaire des samples utilisateur : écoute, renommage, ajout d'un WAV,
  // kits qui utilisent chaque sample (GET /api/samples/user).
  import { onMount } from "svelte";
  import { onPlaying, toggle } from "./player.js";
  import { t } from "./locale.svelte.js";

  let { load, onrename, onupload, onclose } = $props();

  let samples = $state(null);
  let query = $state("");
  let playing = $state(null);
  let renaming = $state(null); // id du sample en cours de renommage
  let newName = $state("");
  let busy = $state(false);
  let error = $state("");
  let dragging = $state(false);

  $effect(() => onPlaying((id) => (playing = id)));
  onMount(refresh);

  let filtered = $derived.by(() => {
    const q = query.trim().toLowerCase();
    return (samples ?? []).filter((s) => !q || s.name.toLowerCase().includes(q) || String(s.id) === q);
  });

  async function refresh() {
    try {
      samples = await load();
    } catch (err) {
      error = err.message;
    }
  }

  function startRename(s) {
    error = "";
    renaming = s.id;
    newName = s.name;
  }

  async function rename() {
    const id = renaming;
    const name = newName.trim();
    if (id == null) return;
    if (!name || name === samples.find((s) => s.id === id)?.name) {
      renaming = null;
      return;
    }
    try {
      await onrename(id, name);
      error = "";
      renaming = null;
      await refresh();
    } catch (err) {
      error = err.message;
    }
  }

  function renameKeydown(e) {
    if (e.key === "Enter") rename();
    else if (e.key === "Escape") renaming = null;
    else return;
    e.preventDefault();
    e.stopPropagation();
  }

  // focus et sélection du nom à l'ouverture du champ de renommage
  function selectAll(node) {
    node.focus();
    node.select();
  }

  async function upload(files) {
    error = "";
    busy = true;
    try {
      for (const file of files) await onupload(file);
    } catch (err) {
      error = err.message;
    } finally {
      busy = false;
      await refresh();
    }
  }

  function uses(s) {
    return s.uses.map((u) => `${u.kit} ${u.kit_name} · ${u.slot} ${u.wave === "wave_a" ? "A" : "B"}`).join(", ");
  }

  function onkeydown(e) {
    if (e.key === "Escape" && renaming == null) onclose();
  }
</script>

<svelte:window {onkeydown} />

<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && onclose()}>
  <div class="dialog" role="dialog" aria-modal="true" aria-label={t("sampleManager")}>
    <header>
      <h2>{t("sampleManager")}</h2>
      <button onclick={onclose} aria-label={t("close")}>✕</button>
    </header>

    <input type="search" placeholder={t("searchSample")} bind:value={query} />

    <ul class="list">
      {#each filtered as s (s.id)}
        <li>
          <span class="id">{s.id}</span>
          <div class="main">
            {#if renaming === s.id}
              <input
                class="rename"
                maxlength="127"
                aria-label={t("renameSample", { name: s.name })}
                bind:value={newName}
                onkeydown={renameKeydown}
                onblur={rename}
                use:selectAll
              />
            {:else}
              <span class="name">{s.name}</span>
            {/if}
            <span class="uses muted" title={uses(s)}>{s.uses.length ? uses(s) : t("sampleUnused")}</span>
          </div>
          <span class="size muted">{t("sizeKb", { n: Math.max(1, Math.round(s.size / 1024)) })}</span>
          <button
            class="icon"
            onclick={() => startRename(s)}
            title={t("renameSample", { name: s.name })}
            aria-label={t("renameSample", { name: s.name })}
          >
            <!-- crayon : le caractère ✎ est trop petit dans la plupart des polices -->
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path d="M4 20h4L19 9l-4-4L4 16v4z" />
              <path d="M13.5 6.5l4 4" />
            </svg>
          </button>
          <button class="icon" onclick={() => toggle(s.id)} aria-label={t("listenTo", { name: s.name })}>
            {playing === s.id ? "■" : "▶"}
          </button>
        </li>
      {:else}
        <li class="muted empty">{t(samples ? "noUserSample" : "loading")}</li>
      {/each}
    </ul>
    {#if samples}<p class="count muted">{t("sampleCount", { n: filtered.length })}</p>{/if}

    <label
      class="drop"
      class:dragging
      ondragover={(e) => {
        e.preventDefault();
        dragging = true;
      }}
      ondragleave={() => (dragging = false)}
      ondrop={(e) => {
        e.preventDefault();
        dragging = false;
        upload([...e.dataTransfer.files]);
      }}
    >
      <input type="file" accept=".wav,audio/wav" multiple hidden onchange={(e) => upload([...e.target.files])} />
      {t(busy ? "uploading" : "dropWav")}
    </label>
    {#if error}<p class="error">{error}</p>{/if}
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgb(0 0 0 / 45%);
    display: grid;
    place-items: center;
    z-index: 10;
    padding: 16px;
  }
  .dialog {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    width: min(760px, 100%);
    max-height: calc(100vh - 32px);
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 16px;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    overflow-y: auto;
    flex: 1;
    min-height: 200px;
    border: 1px solid var(--border);
    border-radius: 6px;
  }
  li {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 4px 10px;
    border-bottom: 1px solid var(--border);
  }
  li.empty {
    padding: 10px;
  }
  .id {
    color: var(--muted);
    font-variant-numeric: tabular-nums;
    width: 40px;
    flex: none;
  }
  .main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .name,
  .uses {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .uses {
    font-size: 12px;
  }
  .size {
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    flex: none;
  }
  .icon {
    border: 0;
    border-radius: 0;
    width: 40px;
    background: transparent;
    flex: none;
  }
  .icon svg {
    display: block;
    margin: auto;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .count {
    margin: 0;
    font-size: 12px;
  }
  .drop {
    border: 2px dashed var(--border);
    border-radius: 6px;
    padding: 14px;
    text-align: center;
    color: var(--muted);
    cursor: pointer;
  }
  .drop.dragging {
    border-color: var(--accent);
    color: var(--text);
  }
  .error {
    margin: 0;
    color: var(--danger);
  }
</style>
