<script>
  // Réglages d'un emplacement (pad ou entrée externe), par sections comme sur
  // l'appareil (Feel, Control, Output, Light, Group), puis les deux waves.
  import ColorSwatches from "./ColorSwatches.svelte";
  import ParamField from "./ParamField.svelte";
  import WaveEditor from "./WaveEditor.svelte";
  import { tooltip } from "./format.js";

  let { slot, meta, sampleIndex, onpick } = $props();

  let defaults = $derived(meta.defaults.slots[slot.slot - 1]);
  // « params.x » / « light.x » -> définition
  let defs = $derived(
    new Map([
      ...meta.pad_params.map((d) => [`params.${d.name}`, d]),
      ...meta.light_params.map((d) => [`light.${d.name}`, d]),
    ]),
  );
  // champs présents dans cet emplacement (illisibles dans certains kits KITC)
  let sections = $derived(
    meta.pad_sections
      .map((s) => ({ ...s, fields: s.fields.map(split).filter(([part, key]) => key in slot[part]) }))
      .filter((s) => s.fields.length),
  );
  let unknown = $derived(meta.pad_params.filter((d) => !d.known && d.name in slot.params));

  function split(field) {
    const [part, key] = field.split(".");
    return [part, key];
  }
  const isColor = (key) => key.endsWith("_color");
</script>

<div class="slot">
  {#each sections as s (s.title)}
    <section>
      <h3>{s.title}</h3>
      {#each s.fields as [part, key] (`${part}.${key}`)}
        {@const def = defs.get(`${part}.${key}`)}
        {#if isColor(key)}
          <div class="color-row" title={tooltip(def.description, def, defaults[part][key])}>
            <span class="muted">{def.title}</span>
            <ColorSwatches colors={meta.colors} bind:value={slot[part][key]} label={def.title} />
          </div>
        {:else}
          <ParamField {def} bind:value={slot[part][key]} defaultValue={defaults[part][key]} />
        {/if}
      {/each}
    </section>
  {/each}

  {#if unknown.length}
    <section>
      <details>
        <summary class="muted">Paramètres non identifiés ({unknown.length})</summary>
        {#each unknown as def (def.name)}
          <ParamField {def} bind:value={slot.params[def.name]} defaultValue={defaults.params[def.name]} />
        {/each}
      </details>
    </section>
  {/if}
</div>

<div class="waves">
  <WaveEditor wave={slot.wave_a} title="Wave A" {meta} {sampleIndex} defaults={defaults.wave_a} onpick={() => onpick("wave_a")} />
  <WaveEditor wave={slot.wave_b} title="Wave B" {meta} {sampleIndex} defaults={defaults.wave_b} onpick={() => onpick("wave_b")} />
</div>

<style>
  .slot,
  .waves {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
  }
  .waves {
    margin-top: 20px;
  }
  section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .color-row {
    display: grid;
    grid-template-columns: 110px 1fr;
    gap: 8px;
    align-items: center;
    font-size: 13px;
    cursor: help;
  }
  details summary {
    cursor: pointer;
    font-size: 13px;
    margin: 4px 0;
  }
</style>
