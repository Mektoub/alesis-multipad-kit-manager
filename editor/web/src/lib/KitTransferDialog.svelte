<script>
  // Copie d'un kit vers un autre numéro, ou échange de deux kits (déplacement
  // quand la cible est vide), comme le menu Copy de l'appareil.
  import { untrack } from "svelte";
  import { t } from "./locale.svelte.js";

  let { kits, source, ontransfer, onclose } = $props();

  let sourceKit = $derived(kits.find((k) => k.num === source));
  let candidates = $derived(kits.filter((k) => k.num !== source));
  // cible proposée à l'ouverture : premier kit vide
  let target = $state(untrack(() => kits.find((k) => k.num !== source && k.name === "Empty")?.num ?? ""));
  let mode = $state("swap");
  let busy = $state(false);
  let error = $state("");

  let targetKit = $derived(kits.find((k) => k.num === target));
  let targetEmpty = $derived(targetKit?.name === "Empty");

  async function submit() {
    if (mode === "copy" && !targetEmpty
        && !confirm(t("askReplace", { target, name: targetKit.name }))) return;
    busy = true;
    error = "";
    try {
      await ontransfer({ target, mode });
    } catch (err) {
      error = err.message;
    } finally {
      busy = false; // transfert abandonné (alerte de l'historique) ou refusé
    }
  }

  function onkeydown(e) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window {onkeydown} />

<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && onclose()}>
  <div class="dialog" role="dialog" aria-modal="true" aria-label={t("transferTitle")}>
    <header>
      <h2>{t("kitHeader", { num: source, name: sourceKit?.name })}</h2>
      <button onclick={onclose} aria-label={t("close")}>✕</button>
    </header>

    <section>
      <label class="choice"><input type="radio" bind:group={mode} value="swap" /> {t("moveSwap")}</label>
      <label class="choice"><input type="radio" bind:group={mode} value="copy" /> {t("copyDuplicate")}</label>
    </section>

    <section>
      <label>
        <span class="muted">{t("toKit")}</span>
        <select bind:value={target}>
          {#each candidates as k (k.num)}<option value={k.num}>{k.num} — {k.name}</option>{/each}
        </select>
      </label>
      <p class="muted explain">
        {#if !targetKit}
          {t("chooseKit")}
        {:else if mode === "swap" && targetEmpty}
          {t("explainMove", { target, source })}
        {:else if mode === "swap"}
          {t("explainSwap", { source, target, name: targetKit.name })}
        {:else if targetEmpty}
          {t("explainCopy", { target })}
        {:else}
          <strong>{t("explainReplace", { target, name: targetKit.name })}</strong>{t("explainReplaceEnd")}
        {/if}
      </p>
    </section>

    {#if error}<p class="error">{error}</p>{/if}

    <footer>
      <button onclick={onclose}>{t("cancel")}</button>
      <button class="primary" onclick={submit} disabled={busy || !targetKit}>
        {t(mode === "copy" ? "copy" : targetEmpty ? "move" : "swap")}
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
    width: min(420px, 100%);
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 16px;
  }
  header,
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
  section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  label:not(.choice) {
    display: grid;
    grid-template-columns: 90px 1fr;
    align-items: center;
    gap: 8px;
  }
  .explain {
    margin: 0;
    font-size: 13px;
  }
  .error {
    color: var(--danger);
    margin: 0;
  }
</style>
