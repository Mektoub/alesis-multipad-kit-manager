<script>
  // Recopie des réglages d'un emplacement vers d'autres.
  let { kit, source, oncopy, onclose } = $props();

  const PARTS = [
    { key: "params", label: "Pad (volume, pan, Control, sortie…)" },
    { key: "light", label: "Éclairage" },
    { key: "wave_a", label: "Wave A (sample, vélocité, mixage)" },
    { key: "wave_b", label: "Wave B (sample, vélocité, mixage)" },
  ];
  // même disposition que la grille de l'éditeur
  const PAD_ROWS = [[7, 8, 9], [4, 5, 6], [1, 2, 3]];

  let targets = $state(new Set());
  let parts = $state(new Set(PARTS.map((p) => p.key)));
  let includeMidi = $state(false);
  let busy = $state(false);
  let error = $state("");

  let others = $derived(kit.slots.slice(9).map((s) => s.slot));

  function toggle(set, value) {
    const next = new Set(set);
    next.has(value) ? next.delete(value) : next.add(value);
    return next;
  }

  function selectPads(all) {
    targets = new Set(all ? [1, 2, 3, 4, 5, 6, 7, 8, 9].filter((n) => n !== source) : []);
  }

  async function submit() {
    busy = true;
    error = "";
    try {
      await oncopy({
        source,
        targets: [...targets].sort((a, b) => a - b),
        parts: PARTS.map((p) => p.key).filter((k) => parts.has(k)),
        include_midi_note: includeMidi,
      });
    } catch (err) {
      error = err.message;
      busy = false;
    }
  }

  function onkeydown(e) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window {onkeydown} />

<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && onclose()}>
  <div class="dialog" role="dialog" aria-modal="true" aria-label="Copier les réglages">
    <header>
      <h2>Copier les réglages de {kit.slots[source - 1]._label}</h2>
      <button onclick={onclose} aria-label="Fermer">✕</button>
    </header>

    <section>
      <div class="head">
        <h3>Vers</h3>
        <span>
          <button class="link" onclick={() => selectPads(true)}>tous les pads</button>
          <button class="link" onclick={() => selectPads(false)}>aucun</button>
        </span>
      </div>
      <div class="pads">
        {#each PAD_ROWS as row}
          {#each row as n}
            <button
              class="target"
              class:on={targets.has(n)}
              disabled={n === source}
              aria-pressed={targets.has(n)}
              onclick={() => (targets = toggle(targets, n))}
            >
              P{n}
            </button>
          {/each}
        {/each}
      </div>
      <details>
        <summary class="muted">Autres entrées (10 à 24)</summary>
        <div class="others">
          {#each others as n}
            <button
              class="target small"
              class:on={targets.has(n)}
              disabled={n === source}
              aria-pressed={targets.has(n)}
              onclick={() => (targets = toggle(targets, n))}
            >
              {n}
            </button>
          {/each}
        </div>
      </details>
    </section>

    <section>
      <h3>Quoi</h3>
      {#each PARTS as p}
        <label><input type="checkbox" checked={parts.has(p.key)} onchange={() => (parts = toggle(parts, p.key))} /> {p.label}</label>
      {/each}
      <label class="midi">
        <input type="checkbox" bind:checked={includeMidi} disabled={!parts.has("params")} />
        Inclure la note MIDI (sinon chaque pad garde la sienne)
      </label>
    </section>

    {#if error}<p class="error">{error}</p>{/if}

    <footer>
      <button onclick={onclose}>Annuler</button>
      <button class="primary" onclick={submit} disabled={busy || !targets.size || !parts.size}>
        Copier vers {targets.size} emplacement(s)
      </button>
    </footer>
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
    width: min(460px, 100%);
    max-height: calc(100vh - 32px);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 16px;
  }
  header,
  .head,
  footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }
  footer {
    justify-content: flex-end;
  }
  section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .pads {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }
  .others {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
  }
  .target {
    padding: 8px 0;
    font-weight: 600;
  }
  .target.small {
    min-width: 38px;
    padding: 4px 6px;
  }
  .target.on {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-text);
  }
  .link {
    border: 0;
    background: transparent;
    color: var(--accent);
    padding: 2px 4px;
  }
  .midi {
    margin-top: 4px;
  }
  details summary {
    cursor: pointer;
    font-size: 13px;
  }
  .error {
    margin: 0;
    color: var(--danger);
  }
</style>
