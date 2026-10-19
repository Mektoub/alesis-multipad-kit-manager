<script>
  // Kit : réglages généraux, grille des 9 pads, autres entrées, emplacement choisi.
  import SlotEditor from "./SlotEditor.svelte";
  import { tooltip } from "./format.js";

  let { kit, meta, sampleIndex, selected = $bindable(), onpick, oncopy, ontransfer, onbulk } = $props();

  // Disposition de l'appareil : 7-8-9 en haut (pads deux fois moins hauts),
  // 4-5-6 au milieu, 1-2-3 en bas.
  const PAD_ORDER = [6, 7, 8, 3, 4, 5, 0, 1, 2];

  let slot = $derived(kit.slots[selected]);
  let others = $derived(kit.slots.slice(9));

  function color(s) {
    return meta.colors[s.light.play_color]?.css ?? "transparent";
  }
  const CLICK = 3;
  let controlLabels = $derived(meta.pad_params.find((d) => d.name === "control")?.labels ?? []);

  function controlBadge(s) {
    const c = s.params.control;
    if (!c) return "";
    return c === CLICK ? "Click" : (controlLabels[c] ?? `Control ${c}`);
  }
  function sampleName(id) {
    if (id == null) return "";
    return sampleIndex.get(id)?.name ?? `#${id}`;
  }
</script>

<div class="kit">
  <div class="settings">
    <label title={meta.help.name}>
      <span class="muted">Nom</span>
      <input type="text" maxlength={meta.kit_name_max} bind:value={kit.name} />
    </label>
    <label title={tooltip(meta.help.level, {}, meta.defaults.kit.level)}>
      <span class="muted">Volume du kit</span>
      <input type="range" min="0" max="100" bind:value={kit.level} />
      <span class="num">{kit.level}</span>
    </label>
    <label title={tooltip(`${meta.help.tempo} Flèches : ±1 BPM ; une décimale peut être saisie (ex. 98.5).`, {}, meta.defaults.kit.tempo)}>
      <span class="muted">Tempo (BPM)</span>
      <input type="number" min="30" max="280" step="any" bind:value={kit.tempo} />
    </label>
    <span class="format muted" title="KITC : format écrit par l'appareil quand on enregistre un kit">{kit.format}</span>
    <button onclick={ontransfer}>Déplacer / copier le kit…</button>
  </div>

  <div class="pads">
    {#each PAD_ORDER as i (i)}
      {@const s = kit.slots[i]}
      <button class="pad" class:small={i >= 6} class:selected={selected === i} onclick={() => (selected = i)} style:--led={color(s)}>
        <span class="label">{s._label}</span>
        <span class="sample">{sampleName(s.wave_a.sample)}</span>
        {#if s.wave_b.sample != null}<span class="sample b">{sampleName(s.wave_b.sample)}</span>{/if}
        {#if controlBadge(s)}
          <span class="control" class:click={s.params.control === CLICK} title="Control : {controlBadge(s)}">{controlBadge(s)}</span>
        {/if}
      </button>
    {/each}
  </div>

  <div class="others">
    <span class="muted">Autres entrées (déclencheurs, pédales… correspondance non vérifiée) :</span>
    {#each others as s, i (s.slot)}
      <button class="chip" class:selected={selected === i + 9} class:used={s.wave_a.sample != null || s.wave_b.sample != null} onclick={() => (selected = i + 9)}>
        {s.slot}
      </button>
    {/each}
  </div>

  <div class="editor">
    <div class="editor-head">
      <h2>{slot._label}</h2>
      <span class="actions">
        <button onclick={() => onbulk(selected + 1)} title="Donner une même valeur à un réglage de plusieurs pads">Modifier plusieurs pads…</button>
        <button onclick={() => oncopy(selected + 1)}>Copier vers…</button>
      </span>
    </div>
    {#key selected}
      <SlotEditor {slot} {meta} {sampleIndex} {onpick} />
    {/key}
  </div>
</div>

<style>
  .kit {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .settings {
    display: flex;
    flex-wrap: wrap;
    gap: 16px 24px;
    align-items: center;
  }
  .settings label {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .settings input[type="number"] {
    width: 80px;
  }
  .num {
    width: 28px;
    font-variant-numeric: tabular-nums;
  }
  .format {
    margin-left: auto;
    font-family: ui-monospace, monospace;
    font-size: 12px;
  }
  .pads {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    max-width: 560px;
  }
  .pad {
    position: relative;
    aspect-ratio: 1.6;
    min-width: 0;
    background: var(--pad);
    color: var(--pad-text);
    border: 2px solid transparent;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: flex-start;
    text-align: left;
    gap: 2px;
    padding: 10px;
    overflow: hidden;
    box-shadow: inset 0 -4px 0 var(--led);
  }
  .pad.small {
    aspect-ratio: 3.2;
  }
  .pad.selected {
    border-color: var(--accent);
  }
  .label {
    position: absolute;
    top: 8px;
    left: 10px;
    font-weight: 700;
  }
  .control {
    position: absolute;
    top: 7px;
    right: 8px;
    font-size: 11px;
    font-weight: 600;
    padding: 1px 7px;
    border-radius: 10px;
    background: rgb(255 255 255 / 15%);
    max-width: 60%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .control.click {
    background: var(--accent);
    color: var(--accent-text);
  }
  .editor-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .sample {
    font-size: 12px;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sample.b {
    opacity: 0.65;
  }
  .others {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .chip {
    min-width: 34px;
    padding: 3px 6px;
  }
  .chip.used {
    font-weight: 700;
  }
  .chip.selected {
    border-color: var(--accent);
    color: var(--accent);
  }
  .editor {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-shadow: var(--shadow);
  }
</style>
