<script>
  // Une couche (wave A ou B) : sample, plage de vélocité, mixage.
  import ParamField from "./ParamField.svelte";
  import { onPlaying, toggle } from "./player.js";

  let { wave, title, meta, sampleIndex, onpick } = $props();

  let playing = $state(null);
  $effect(() => onPlaying((id) => (playing = id)));

  let sample = $derived(wave.sample == null ? null : sampleIndex.get(wave.sample));
  let hasHeader = $derived("sample" in wave);
  let known = $derived(meta.wave_params.filter((d) => d.known && d.name in wave.params));
  let unknown = $derived(meta.wave_params.filter((d) => !d.known && d.name in wave.params));

  function clampVelocity(edited) {
    if (wave.velocity_low > wave.velocity_high) {
      if (edited === "low") wave.velocity_high = wave.velocity_low;
      else wave.velocity_low = wave.velocity_high;
    }
  }
</script>

<section class="wave">
  <h3>{title}</h3>
  {#if hasHeader}
    <div class="sample">
      <button class="pick" onclick={onpick} title="Choisir un sample">
        {#if sample}
          <span class="name">{sample.name}</span><span class="muted">#{sample.id}</span>
        {:else if wave.sample != null}
          <span class="name">Sample #{wave.sample}</span>
        {:else}
          <span class="muted">Aucun sample : choisir…</span>
        {/if}
      </button>
      {#if sample?.user}
        <button onclick={() => toggle(sample.id)} aria-label="Écouter">{playing === sample.id ? "■" : "▶"}</button>
      {/if}
      {#if wave.sample != null}
        <button onclick={() => (wave.sample = null)} aria-label="Retirer le sample" title="Retirer le sample">✕</button>
      {/if}
    </div>
    <div class="velocity">
      <span class="muted">Vélocité</span>
      <input type="number" min="0" max="126" bind:value={wave.velocity_low} onchange={() => clampVelocity("low")} />
      <span class="muted">à</span>
      <input type="number" min="1" max="127" bind:value={wave.velocity_high} onchange={() => clampVelocity("high")} />
    </div>
  {:else}
    <p class="muted">Sample et vélocité illisibles dans ce kit.</p>
  {/if}

  {#each known as def (def.name)}
    <ParamField {def} bind:value={wave.params[def.name]} />
  {/each}
  {#if unknown.length}
    <details>
      <summary class="muted">Paramètres non identifiés ({unknown.length})</summary>
      {#each unknown as def (def.name)}
        <ParamField {def} bind:value={wave.params[def.name]} />
      {/each}
    </details>
  {/if}
</section>

<style>
  .wave {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .sample {
    display: flex;
    gap: 6px;
  }
  .pick {
    flex: 1;
    display: flex;
    justify-content: space-between;
    gap: 8px;
    text-align: left;
    min-width: 0;
  }
  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .velocity {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .velocity input {
    width: 70px;
  }
  details summary {
    cursor: pointer;
    font-size: 13px;
    margin: 4px 0;
  }
  p {
    margin: 0;
  }
</style>
