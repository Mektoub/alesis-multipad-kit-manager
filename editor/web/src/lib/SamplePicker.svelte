<script>
  // Fenêtre de choix d'un sample : recherche, filtre, écoute, ajout d'un WAV.
  import { onPlaying, toggle } from "./player.js";

  let { samples, current, onselect, onclose, onupload } = $props();

  const LIMIT = 300;
  let query = $state("");
  let scope = $state("all");
  let playing = $state(null);
  let uploading = $state(false);
  let uploadError = $state("");
  let dragging = $state(false);
  let input;

  $effect(() => onPlaying((id) => (playing = id)));
  $effect(() => input?.focus());

  let filtered = $derived.by(() => {
    const q = query.trim().toLowerCase();
    return samples.filter(
      (s) =>
        (scope === "all" || (scope === "user") === s.user) &&
        (!q || s.name.toLowerCase().includes(q) || String(s.id) === q),
    );
  });

  async function upload(files) {
    uploadError = "";
    uploading = true;
    try {
      for (const file of files) {
        const added = await onupload(file);
        onselect(added.id);
      }
    } catch (err) {
      uploadError = err.message;
    } finally {
      uploading = false;
    }
  }

  function onkeydown(e) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window {onkeydown} />

<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && onclose()}>
  <div class="dialog" role="dialog" aria-modal="true" aria-label="Choisir un sample">
    <header>
      <h2>Choisir un sample</h2>
      <button onclick={onclose} aria-label="Fermer">✕</button>
    </header>

    <div class="toolbar">
      <input type="search" placeholder="Rechercher par nom ou id…" bind:value={query} bind:this={input} />
      <select bind:value={scope}>
        <option value="all">Tous</option>
        <option value="user">Mes samples</option>
        <option value="factory">Usine</option>
      </select>
    </div>

    <ul class="list">
      <li>
        <button class="row" class:active={current === null} onclick={() => onselect(null)}>
          <span class="name muted">— Aucun sample —</span>
        </button>
      </li>
      {#each filtered.slice(0, LIMIT) as s (s.id)}
        <li>
          <button class="row" class:active={current === s.id} onclick={() => onselect(s.id)}>
            <span class="id">{s.id}</span>
            <span class="name">{s.name}</span>
            {#if s.user}<span class="badge">perso</span>{/if}
          </button>
          {#if s.user}
            <button class="play" onclick={() => toggle(s.id)} aria-label="Écouter {s.name}">
              {playing === s.id ? "■" : "▶"}
            </button>
          {/if}
        </li>
      {/each}
    </ul>
    <p class="count muted">
      {filtered.length} sample(s){filtered.length > LIMIT ? `, ${LIMIT} affichés : affinez la recherche` : ""}.
      Seuls les samples perso peuvent être écoutés.
    </p>

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
      {uploading ? "Ajout en cours…" : "Ajouter un WAV : glisser-déposer ici ou cliquer (16 bits, 44,1 kHz)"}
    </label>
    {#if uploadError}<p class="error">{uploadError}</p>{/if}
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
    width: min(640px, 100%);
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
  .toolbar {
    display: flex;
    gap: 8px;
  }
  .toolbar input {
    flex: 1;
    min-width: 0;
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
    border-bottom: 1px solid var(--border);
  }
  .row {
    flex: 1;
    display: flex;
    gap: 10px;
    align-items: center;
    text-align: left;
    border: 0;
    border-radius: 0;
    background: transparent;
    min-width: 0;
  }
  .row.active {
    background: var(--panel-2);
    font-weight: 600;
  }
  .id {
    color: var(--muted);
    font-variant-numeric: tabular-nums;
    width: 40px;
    flex: none;
  }
  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .badge {
    margin-left: auto;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 10px;
    background: var(--accent);
    color: var(--accent-text);
  }
  .play {
    border: 0;
    border-radius: 0;
    width: 40px;
    background: transparent;
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
