<script>
  // Kit : réglages généraux, grille des 9 pads, autres entrées, emplacement choisi.
  import SlotEditor from "./SlotEditor.svelte";

  let { kit, meta, sampleIndex, selected = $bindable(), onpick } = $props();

  let slot = $derived(kit.slots[selected]);
  let others = $derived(kit.slots.slice(9));

  function color(s) {
    return meta.colors[s.light.play_color]?.css ?? "transparent";
  }
  function sampleName(id) {
    if (id == null) return "";
    return sampleIndex.get(id)?.name ?? `#${id}`;
  }
</script>

<div class="kit">
  <div class="settings">
    <label>
      <span class="muted">Nom</span>
      <input type="text" maxlength={meta.kit_name_max} bind:value={kit.name} />
    </label>
    <label>
      <span class="muted">Volume du kit</span>
      <input type="range" min="0" max="100" bind:value={kit.level} />
      <span class="num">{kit.level}</span>
    </label>
    <label>
      <span class="muted">Tempo (BPM)</span>
      <input type="number" min="30" max="280" step="0.1" bind:value={kit.tempo} />
    </label>
    <span class="format muted" title="KITC : format écrit par l'appareil ; certains champs peuvent être illisibles">{kit.format}</span>
  </div>

  <div class="pads">
    {#each kit.slots.slice(0, 9) as s, i}
      <button class="pad" class:selected={selected === i} onclick={() => (selected = i)} style:--led={color(s)}>
        <span class="label">{s._label}</span>
        <span class="sample">{sampleName(s.wave_a.sample)}</span>
        {#if s.wave_b.sample != null}<span class="sample b">{sampleName(s.wave_b.sample)}</span>{/if}
        {#if s.params.midi_note != null}<span class="note">♪ {s.params.midi_note}</span>{/if}
      </button>
    {/each}
  </div>

  <div class="others">
    <span class="muted">Autres entrées (déclencheurs, pédales… correspondance non vérifiée) :</span>
    {#each others as s, i}
      <button class="chip" class:selected={selected === i + 9} class:used={s.wave_a.sample != null || s.wave_b.sample != null} onclick={() => (selected = i + 9)}>
        {s.slot}
      </button>
    {/each}
  </div>

  <div class="editor">
    <h2>{slot._label}</h2>
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
  .pad.selected {
    border-color: var(--accent);
  }
  .label {
    position: absolute;
    top: 8px;
    left: 10px;
    font-weight: 700;
  }
  .note {
    position: absolute;
    top: 8px;
    right: 10px;
    font-size: 12px;
    opacity: 0.7;
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
