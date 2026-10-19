<script>
  // Donne une même valeur à un réglage de plusieurs emplacements.
  import { untrack } from "svelte";
  import { formatValue } from "./format.js";
  let { kit, meta, source, onapply, onclose } = $props();

  // même disposition que la grille de l'éditeur
  const PAD_ROWS = [[7, 8, 9], [4, 5, 6], [1, 2, 3]];

  const light = [
    { key: "play_color", title: "Couleur Play", labels: meta.colors.map((c) => c.name) },
    { key: "play_mode", title: "Mode Play", labels: meta.play_modes },
    { key: "stop_color", title: "Couleur Stop", labels: meta.colors.map((c) => c.name) },
    { key: "stop_mode", title: "Mode Stop", labels: meta.stop_modes },
  ];

  function fromParam(prefix, group, d) {
    return { field: `${prefix}.${d.name}`, group, title: d.title, min: d.min, max: d.max,
             labels: d.labels, description: d.description, known: d.known };
  }

  const FIELDS = [
    ...meta.pad_params.map((d) => fromParam("params", "Pad", d)),
    ...light.map((l) => ({ field: `light.${l.key}`, group: "Éclairage", title: l.title, min: 0,
                           max: l.labels.length - 1, labels: l.labels, description: meta.help[l.key], known: true })),
    ...["wave_a", "wave_b"].flatMap((w) => {
      const group = w === "wave_a" ? "Wave A" : "Wave B";
      return [
        { field: `${w}.velocity_low`, group, title: "Velocity Low", min: 0, max: 126,
          description: meta.help.velocity_low, known: true },
        { field: `${w}.velocity_high`, group, title: "Velocity High", min: 1, max: 127,
          description: meta.help.velocity_high, known: true },
        ...meta.wave_params.map((d) => fromParam(`${w}.params`, group, d)),
      ];
    }),
  ];
  const GROUPS = [...new Set(FIELDS.map((f) => f.group))];

  let fieldName = $state("params.sensitivity");
  let def = $derived(FIELDS.find((f) => f.field === fieldName));
  // valeurs de départ (la fenêtre est recréée à chaque ouverture)
  let value = $state(untrack(() => currentValue("params.sensitivity")));
  let targets = $state(untrack(() => new Set([source])));
  let busy = $state(false);
  let error = $state("");

  let others = $derived(kit.slots.slice(9).map((s) => s.slot));
  let valid = $derived(Number.isInteger(value) && value >= def.min && value <= def.max);
  let sourceLabel = $derived(kit.slots[source - 1]._label);
  let defaultValue = $derived(lookup(meta.defaults.slots[source - 1], fieldName));

  function lookup(node, field) {
    for (const key of field.split(".")) node = node?.[key];
    return node;
  }

  function currentValue(field) {
    return lookup(kit.slots[source - 1], field) ?? 0;
  }

  function changeField(e) {
    fieldName = e.target.value;
    value = currentValue(fieldName);
  }

  function toggle(n) {
    const next = new Set(targets);
    next.has(n) ? next.delete(n) : next.add(n);
    targets = next;
  }

  function selectPads(all) {
    targets = new Set(all ? [1, 2, 3, 4, 5, 6, 7, 8, 9] : []);
  }

  async function submit() {
    busy = true;
    error = "";
    try {
      await onapply({ targets: [...targets].sort((a, b) => a - b), field: fieldName, value, title: def.title });
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
  <div class="dialog" role="dialog" aria-modal="true" aria-label="Modifier plusieurs pads">
    <header>
      <h2>Modifier plusieurs pads</h2>
      <button onclick={onclose} aria-label="Fermer">✕</button>
    </header>

    <section>
      <label class="row">
        <span class="muted">Réglage</span>
        <select value={fieldName} onchange={changeField}>
          {#each GROUPS as g}
            <optgroup label={g}>
              {#each FIELDS.filter((f) => f.group === g) as f (f.field)}
                <option value={f.field}>{f.title}</option>
              {/each}
            </optgroup>
          {/each}
        </select>
      </label>
      <p class="muted help">
        {def.description}
        {#if defaultValue != null}<br />Par défaut sur {sourceLabel} : {formatValue({ ...def, name: fieldName.split(".").pop() }, defaultValue)}{/if}
      </p>
      <label class="row">
        <span class="muted">Valeur</span>
        {#if def.labels}
          <select bind:value>
            {#each { length: def.max - def.min + 1 } as _, i}
              <option value={def.min + i}>{def.labels[def.min + i] ?? `Valeur ${def.min + i}`}</option>
            {/each}
          </select>
        {:else}
          <span class="value">
            <input type="range" min={def.min} max={def.max} bind:value />
            <input type="number" min={def.min} max={def.max} step="1" bind:value />
          </span>
        {/if}
      </label>
      {#if !def.labels}<p class="muted help">Plage : {def.min} à {def.max}</p>{/if}
    </section>

    <section>
      <div class="head">
        <h3>Pads</h3>
        <span>
          <button class="link" onclick={() => selectPads(true)}>tous les pads</button>
          <button class="link" onclick={() => selectPads(false)}>aucun</button>
        </span>
      </div>
      <div class="pads">
        {#each PAD_ROWS as row}
          {#each row as n}
            <button class="target" class:on={targets.has(n)} aria-pressed={targets.has(n)} onclick={() => toggle(n)}>
              P{n}
            </button>
          {/each}
        {/each}
      </div>
      <details>
        <summary class="muted">Autres entrées (10 à 24)</summary>
        <div class="others">
          {#each others as n}
            <button class="target small" class:on={targets.has(n)} aria-pressed={targets.has(n)} onclick={() => toggle(n)}>
              {n}
            </button>
          {/each}
        </div>
      </details>
    </section>

    {#if error}<p class="error">{error}</p>{/if}

    <footer>
      <button onclick={onclose}>Annuler</button>
      <button class="primary" onclick={submit} disabled={busy || !targets.size || !valid}>
        Appliquer à {targets.size} emplacement(s)
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
  h2 {
    margin: 0;
    font-size: 16px;
  }
  h3 {
    margin: 0;
    font-size: 14px;
  }
  section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .row {
    display: grid;
    grid-template-columns: 70px 1fr;
    align-items: center;
    gap: 8px;
  }
  .value {
    display: grid;
    grid-template-columns: 1fr 70px;
    gap: 8px;
    align-items: center;
  }
  .help {
    margin: 0 0 0 78px;
    font-size: 12px;
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
  details summary {
    cursor: pointer;
    font-size: 13px;
  }
  .error {
    margin: 0;
    color: var(--danger);
  }
</style>
