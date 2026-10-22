<script>
  // Donne une même valeur à un réglage de plusieurs emplacements, dans le kit
  // courant ou dans plusieurs kits (mêmes emplacements dans chacun).
  import { untrack } from "svelte";
  import { SvelteSet } from "svelte/reactivity";
  import { formatValue } from "./format.js";
  let { kit, meta, source, kits, currentNum, onapply, onclose } = $props();

  // même disposition que la grille de l'éditeur
  const PAD_ROWS = [[7, 8, 9], [4, 5, 6], [1, 2, 3]];

  // Réglages proposés, construits une fois à l'ouverture (`meta` ne change pas).
  // Groupés par sections, comme dans l'éditeur ; les paramètres non identifiés à la fin.
  function buildFields(meta) {
    const fromDef = (field, group, d) => ({
      field, group, title: d.title, min: d.min, max: d.max,
      labels: d.labels, description: d.description, known: d.known,
    });
    const pad = new Map([
      ...meta.pad_params.map((d) => [`params.${d.name}`, d]),
      ...meta.light_params.map((d) => [`light.${d.name}`, d]),
    ]);
    const wave = new Map([
      ...meta.wave_params.map((d) => [`params.${d.name}`, d]),
      ...meta.velocity_params.map((d) => [d.name, d]),
    ]);
    const unknown = (params) => params.filter((d) => !d.known);
    return [
      ...meta.pad_sections.flatMap((s) => s.fields.map((f) => fromDef(f, `Pad · ${s.title}`, pad.get(f)))),
      ...unknown(meta.pad_params).map((d) => fromDef(`params.${d.name}`, "Pad · non identifiés", d)),
      ...["wave_a", "wave_b"].flatMap((w) => {
        const title = w === "wave_a" ? "Wave A" : "Wave B";
        return [
          ...meta.wave_sections.flatMap((s) =>
            s.fields.map((f) => fromDef(`${w}.${f}`, `${title} · ${s.title}`, wave.get(f))),
          ),
          ...unknown(meta.wave_params).map((d) => fromDef(`${w}.params.${d.name}`, `${title} · non identifiés`, d)),
        ];
      }),
    ];
  }

  const FIELDS = untrack(() => buildFields(meta));
  const GROUPS = [...new Set(FIELDS.map((f) => f.group))];

  let fieldName = $state("params.sensitivity");
  let def = $derived(FIELDS.find((f) => f.field === fieldName));
  // valeurs de départ (la fenêtre est recréée à chaque ouverture)
  let value = $state(untrack(() => currentValue("params.sensitivity")));
  // sélections réactives, modifiées en place
  const targets = untrack(() => new SvelteSet([source]));
  const chosenKits = untrack(() => new SvelteSet([currentNum]));
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

  function toggle(set, value) {
    if (set.has(value)) set.delete(value);
    else set.add(value);
  }

  function replace(set, values) {
    set.clear();
    for (const v of values) set.add(v);
  }

  function selectKits(which) {
    if (which === "current") replace(chosenKits, [currentNum]);
    else if (which === "used") replace(chosenKits, kits.filter((k) => k.name !== "Empty").map((k) => k.num));
    else chosenKits.clear();
  }

  function selectPads(all) {
    replace(targets, all ? [1, 2, 3, 4, 5, 6, 7, 8, 9] : []);
  }

  async function submit() {
    busy = true;
    error = "";
    try {
      await onapply({
        kits: kits.map((k) => k.num).filter((n) => chosenKits.has(n)),
        targets: [...targets].sort((a, b) => a - b),
        field: fieldName,
        value,
        title: def.title,
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
  <div class="dialog" role="dialog" aria-modal="true" aria-label="Modifier plusieurs pads">
    <header>
      <h2>Modifier plusieurs pads</h2>
      <button onclick={onclose} aria-label="Fermer">✕</button>
    </header>

    <section>
      <label class="row">
        <span class="muted">Réglage</span>
        <select value={fieldName} onchange={changeField}>
          {#each GROUPS as g (g)}
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
            {#each { length: def.max - def.min + 1 } as _, i (i)}
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
        {#each PAD_ROWS as row, r (r)}
          {#each row as n (n)}
            <button class="target" class:on={targets.has(n)} aria-pressed={targets.has(n)} onclick={() => toggle(targets, n)}>
              P{n}
            </button>
          {/each}
        {/each}
      </div>
      <details>
        <summary class="muted">Autres entrées (10 à 24)</summary>
        <div class="others">
          {#each others as n (n)}
            <button class="target small" class:on={targets.has(n)} aria-pressed={targets.has(n)} onclick={() => toggle(targets, n)}>
              {n}
            </button>
          {/each}
        </div>
      </details>
    </section>

    <section>
      <div class="head">
        <h3>Kits ({chosenKits.size})</h3>
        <span>
          <button class="link" onclick={() => selectKits("current")}>kit courant</button>
          <button class="link" onclick={() => selectKits("used")}>kits non vides</button>
          <button class="link" onclick={() => selectKits("none")}>aucun</button>
        </span>
      </div>
      <p class="muted help kits-help">Les mêmes pads sont modifiés dans chaque kit coché.</p>
      <ul class="kits">
        {#each kits as k (k.num)}
          <li>
            <label class:empty={k.name === "Empty"}>
              <input type="checkbox" checked={chosenKits.has(k.num)} onchange={() => toggle(chosenKits, k.num)} />
              <span class="num">{k.num}</span> {k.name}{k.num === currentNum ? " (courant)" : ""}
            </label>
          </li>
        {/each}
      </ul>
    </section>

    {#if error}<p class="error">{error}</p>{/if}

    <footer>
      <button onclick={onclose}>Annuler</button>
      <button class="primary" onclick={submit} disabled={busy || !targets.size || !chosenKits.size || !valid}>
        Appliquer à {targets.size} pad(s){chosenKits.size > 1 ? ` × ${chosenKits.size} kits` : ""}
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
  .kits {
    list-style: none;
    margin: 0;
    padding: 4px 8px;
    max-height: 180px;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  .kits label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    padding: 2px 0;
  }
  .kits .empty {
    color: var(--muted);
    font-style: italic;
  }
  .kits .num {
    font-variant-numeric: tabular-nums;
    color: var(--muted);
  }
  .kits-help {
    margin: 0;
  }
  .error {
    margin: 0;
    color: var(--danger);
  }
</style>
