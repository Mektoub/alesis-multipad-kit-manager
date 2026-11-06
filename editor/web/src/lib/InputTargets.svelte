<script>
  // Choix des entrées 10 à 24 dans les fenêtres de copie et de réglage : entrées
  // identifiées par leur nom (déclencheurs, puis pédales), puis les autres
  // emplacements par leur numéro.
  import { t } from "./locale.svelte.js";

  let { kit, meta, targets, source = null, ontoggle } = $props();

  let unknown = $derived(kit.slots.slice(9).map((s) => s.slot).filter((n) => !meta.inputs.flat().includes(n)));
</script>

<div class="rows">
  {#each meta.inputs as row, i (i)}
    <div class="row">
      {#each row as n (n)}
        <button
          class="target small"
          class:on={targets.has(n)}
          disabled={n === source}
          aria-pressed={targets.has(n)}
          onclick={() => ontoggle(n)}
        >
          {kit.slots[n - 1]._label}
        </button>
      {/each}
    </div>
  {/each}
  {#if unknown.length}
    <div class="row">
      <span class="muted">{t("unidentifiedSlots")}</span>
      {#each unknown as n (n)}
        <button
          class="target small"
          class:on={targets.has(n)}
          disabled={n === source}
          aria-pressed={targets.has(n)}
          onclick={() => ontoggle(n)}
        >
          {n}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .rows {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 6px;
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .target {
    font-weight: 600;
    min-width: 38px;
    padding: 4px 6px;
  }
  .target.on {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-text);
  }
</style>
