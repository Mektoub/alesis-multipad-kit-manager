<script>
  // Une couche (wave A ou B) : sample, puis sections Mode et Mix comme sur l'appareil.
  import ParamField from "./ParamField.svelte";
  import { onPlaying, toggle } from "./player.js";
  import { tooltip } from "./format.js";
  import { t } from "./locale.svelte.js";

  let { wave, title, meta, sampleIndex, defaults, onpick } = $props();

  let playing = $state(null);
  $effect(() => onPlaying((id) => (playing = id)));

  let sample = $derived(wave.sample == null ? null : sampleIndex.get(wave.sample));
  let hasHeader = $derived("sample" in wave);
  let defs = $derived(
    new Map([
      ...meta.wave_params.map((d) => [`params.${d.name}`, d]),
      ...meta.velocity_params.map((d) => [d.name, d]),
    ]),
  );
  // champs présents dans cette wave (vélocité illisible dans certains kits KITC)
  let sections = $derived(
    meta.wave_sections
      .map((s) => ({ ...s, fields: s.fields.filter(present) }))
      .filter((s) => s.fields.length),
  );
  let unknown = $derived(meta.wave_params.filter((d) => !d.known && d.name in wave.params));

  function present(field) {
    const [part, key] = field.split(".");
    return key ? key in wave[part] : hasHeader && part in wave;
  }

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
    <div class="sample" title={meta.help.sample}>
      <button class="pick" onclick={onpick} title={t("chooseSample")}>
        {#if sample}
          <span class="name">{sample.name}</span><span class="muted">#{sample.id}</span>
        {:else if wave.sample != null}
          <span class="name">Sample #{wave.sample}</span>
        {:else}
          <span class="muted">{t("noSampleChoose")}</span>
        {/if}
      </button>
      {#if sample?.user}
        <button onclick={() => toggle(sample.id)} aria-label={t("listen")}>{playing === sample.id ? "■" : "▶"}</button>
      {/if}
      {#if wave.sample != null}
        <button onclick={() => (wave.sample = null)} aria-label={t("removeSample")} title={t("removeSample")}>✕</button>
      {/if}
    </div>
  {:else}
    <p class="muted">{t("waveUnreadable")}</p>
  {/if}

  {#each sections as s (s.title)}
    <h4>{s.title}</h4>
    {#each s.fields as field (field)}
      {@const def = defs.get(field)}
      {#if field.startsWith("params.")}
        <ParamField {def} bind:value={wave.params[def.name]} defaultValue={defaults.params[def.name]} />
      {:else}
        {@const edge = def.name === "velocity_low" ? "low" : "high"}
        <label class="velocity" title={tooltip(def.description, def, defaults[def.name])}>
          <span class="muted">{def.title}</span>
          <input type="number" min={def.min} max={def.max} bind:value={wave[def.name]} onchange={() => clampVelocity(edge)} />
        </label>
      {/if}
    {/each}
  {/each}
  {#if unknown.length}
    <details>
      <summary class="muted">{t("unknownParams", { n: unknown.length })}</summary>
      {#each unknown as def (def.name)}
        <ParamField {def} bind:value={wave.params[def.name]} defaultValue={defaults.params[def.name]} />
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
  h4 {
    margin: 6px 0 0;
    font-size: 13px;
    font-weight: 600;
  }
  .velocity {
    display: grid;
    grid-template-columns: 110px 1fr;
    align-items: center;
    gap: 8px;
    min-height: 30px;
    font-size: 13px;
    cursor: help;
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
