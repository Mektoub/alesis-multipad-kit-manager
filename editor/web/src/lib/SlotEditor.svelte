<script>
  // Réglages d'un emplacement (pad ou entrée externe) : pad, éclairage, waves.
  import ColorSwatches from "./ColorSwatches.svelte";
  import ParamField from "./ParamField.svelte";
  import WaveEditor from "./WaveEditor.svelte";

  let { slot, meta, sampleIndex, onpick } = $props();

  let known = $derived(meta.pad_params.filter((d) => d.known && d.name in slot.params));
  let unknown = $derived(meta.pad_params.filter((d) => !d.known && d.name in slot.params));
</script>

<div class="slot">
  <section>
    <h3>Pad</h3>
    {#each known as def (def.name)}
      <ParamField {def} bind:value={slot.params[def.name]} />
    {/each}
    {#if unknown.length}
      <details>
        <summary class="muted">Paramètres non identifiés ({unknown.length})</summary>
        {#each unknown as def (def.name)}
          <ParamField {def} bind:value={slot.params[def.name]} />
        {/each}
      </details>
    {/if}
  </section>

  <section>
    <h3>Éclairage</h3>
    {#if "play_color" in slot.light}
      <div class="light-row"><span class="muted">Play</span><ColorSwatches colors={meta.colors} bind:value={slot.light.play_color} label="Couleur Play" /></div>
    {/if}
    {#if "play_mode" in slot.light}
      <label class="light-row"><span class="muted">Mode Play</span>
        <select bind:value={slot.light.play_mode}>
          {#each meta.play_modes as m, i}<option value={i}>{m}</option>{/each}
        </select>
      </label>
    {/if}
    {#if "stop_color" in slot.light}
      <div class="light-row"><span class="muted">Stop</span><ColorSwatches colors={meta.colors} bind:value={slot.light.stop_color} label="Couleur Stop" /></div>
    {/if}
    {#if "stop_mode" in slot.light}
      <label class="light-row"><span class="muted">Mode Stop</span>
        <select bind:value={slot.light.stop_mode}>
          {#each meta.stop_modes as m, i}<option value={i}>{m}</option>{/each}
          {#if slot.light.stop_mode >= meta.stop_modes.length}<option value={slot.light.stop_mode}>Valeur {slot.light.stop_mode}</option>{/if}
        </select>
      </label>
    {/if}
  </section>

  <WaveEditor wave={slot.wave_a} title="Wave A" {meta} {sampleIndex} onpick={() => onpick("wave_a")} />
  <WaveEditor wave={slot.wave_b} title="Wave B" {meta} {sampleIndex} onpick={() => onpick("wave_b")} />
</div>

<style>
  .slot {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
  }
  section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .light-row {
    display: grid;
    grid-template-columns: 80px 1fr;
    gap: 8px;
    align-items: center;
  }
  details summary {
    cursor: pointer;
    font-size: 13px;
    margin: 4px 0;
  }
</style>
