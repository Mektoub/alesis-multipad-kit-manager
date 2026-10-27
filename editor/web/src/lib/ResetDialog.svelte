<script>
  // Remet des réglages d'emplacements aux valeurs par défaut (celles du kit vide
  // de l'appareil, propres à chaque emplacement), par sections.
  import { untrack } from "svelte";
  import { SvelteSet } from "svelte/reactivity";
  import { t } from "./locale.svelte.js";

  let { kit, meta, source, onreset, onclose } = $props();

  // même disposition que la grille de l'éditeur
  const PAD_ROWS = [[7, 8, 9], [4, 5, 6], [1, 2, 3]];

  // Sections proposées : celles du pad, puis Mode et Mix de chaque wave, et le
  // retrait du sample de chaque wave. Aucune n'est cochée au départ ; « toutes les
  // sections » coche tout sauf le retrait des samples.
  function buildSections(meta) {
    const pad = meta.pad_sections.map((s) => ({ key: `pad.${s.title}`, label: s.title, fields: s.fields, all: true }));
    const waves = ["wave_a", "wave_b"].map((w) => ({
      title: w === "wave_a" ? "Wave A" : "Wave B",
      sections: [
        ...meta.wave_sections.map((s) => ({
          key: `${w}.${s.title}`, label: s.title, fields: s.fields.map((f) => `${w}.${f}`), all: true,
        })),
        { key: `${w}.sample`, label: t("removeSampleSection"), fields: [`${w}.sample`], all: false },
      ],
    }));
    return [{ title: "Pad", sections: pad }, ...waves];
  }

  const GROUPS = untrack(() => buildSections(meta));
  const SECTIONS = GROUPS.flatMap((g) => g.sections);

  // sélections réactives, modifiées en place
  const targets = untrack(() => new SvelteSet([source]));
  const chosen = new SvelteSet();
  let busy = $state(false);
  let error = $state("");

  let others = $derived(kit.slots.slice(9).map((s) => s.slot));

  function toggle(set, value) {
    if (set.has(value)) set.delete(value);
    else set.add(value);
  }

  function selectSections(all) {
    chosen.clear();
    if (all) for (const s of SECTIONS) if (s.all) chosen.add(s.key);
  }

  function selectPads(all) {
    targets.clear();
    if (all) for (const n of [1, 2, 3, 4, 5, 6, 7, 8, 9]) targets.add(n);
  }

  async function submit() {
    busy = true;
    error = "";
    try {
      await onreset({
        targets: [...targets].sort((a, b) => a - b),
        fields: SECTIONS.filter((s) => chosen.has(s.key)).flatMap((s) => s.fields),
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
  <div class="dialog" role="dialog" aria-modal="true" aria-label={t("resetLabel")}>
    <header>
      <h2>{t("defaults")}</h2>
      <button onclick={onclose} aria-label={t("close")}>✕</button>
    </header>

    <section>
      <div class="head">
        <h3>{t("slots")}</h3>
        <span>
          <button class="link" onclick={() => selectPads(true)}>{t("allPads")}</button>
          <button class="link" onclick={() => selectPads(false)}>{t("none")}</button>
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
        <summary class="muted">{t("otherInputs")}</summary>
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
        <h3>{t("sections")}</h3>
        <span>
          <button class="link" onclick={() => selectSections(true)}>{t("allSections")}</button>
          <button class="link" onclick={() => selectSections(false)}>{t("noneSections")}</button>
        </span>
      </div>
      {#each GROUPS as g (g.title)}
        <div class="group">
          <strong>{g.title}</strong>
          {#each g.sections as s (s.key)}
            <label><input type="checkbox" checked={chosen.has(s.key)} onchange={() => toggle(chosen, s.key)} /> {s.label}</label>
          {/each}
        </div>
      {/each}
      <p class="muted help">{t("resetHelp")}</p>
    </section>

    {#if error}<p class="error">{error}</p>{/if}

    <footer>
      <button onclick={onclose}>{t("cancel")}</button>
      <button class="primary" onclick={submit} disabled={busy || !targets.size || !chosen.size}>
        {t("resetSlots", { n: targets.size })}
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
  section {
    display: flex;
    flex-direction: column;
    gap: 6px;
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
  .group {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    align-items: center;
  }
  .group strong {
    width: 100%;
    font-size: 13px;
  }
  details summary {
    cursor: pointer;
    font-size: 13px;
  }
  .help {
    margin: 4px 0 0;
    font-size: 13px;
  }
  .error {
    margin: 0;
    color: var(--danger);
  }
</style>
