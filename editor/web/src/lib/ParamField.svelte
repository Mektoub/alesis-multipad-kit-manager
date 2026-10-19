<script>
  // Un paramètre (id, valeur, min, max) : liste déroulante si ses valeurs ont
  // des libellés, curseur sinon.
  // `defaultValue` : valeur par défaut de l'emplacement affiché, pour l'infobulle.
  import { formatValue, tooltip } from "./format.js";

  let { def, value = $bindable(), defaultValue = null } = $props();
</script>

<label class="field" class:unknown={!def.known} title={tooltip(def.description, def, defaultValue)}>
  <span class="name">
    {def.title}
    {#if def.labels && !def.verified}<span class="hint" title="Libellés supposés d'après le manuel">?</span>{/if}
  </span>
  {#if def.labels}
    <select bind:value>
      {#each { length: def.max - def.min + 1 } as _, i (i)}
        <option value={def.min + i}>{def.labels[def.min + i] ?? `Valeur ${def.min + i}`}</option>
      {/each}
    </select>
  {:else}
    <input type="range" min={def.min} max={def.max} bind:value />
    <span class="value">{formatValue(def, value)}</span>
  {/if}
</label>

<style>
  .field {
    display: grid;
    grid-template-columns: 110px 1fr 40px;
    align-items: center;
    gap: 8px;
    min-height: 30px;
  }
  .field select {
    grid-column: 2 / 4;
  }
  .name {
    color: var(--muted);
    font-size: 13px;
    cursor: help;
  }
  .unknown .name {
    font-family: ui-monospace, monospace;
  }
  .value {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .hint {
    display: inline-block;
    margin-left: 2px;
    font-size: 11px;
    color: var(--muted);
    cursor: help;
  }
</style>
