<script>
  // Question posée au premier lancement de l'application installée : rechercher
  // les mises à jour au démarrage (préférence `check_updates`, désactivée tant
  // qu'il n'y a pas de réponse). `onchoose` reçoit true ou false ; Échap : non.
  import { t } from "./locale.svelte.js";

  let { onchoose } = $props();

  function onkeydown(e) {
    if (e.key === "Escape") onchoose(false);
  }
</script>

<svelte:window {onkeydown} />

<div class="backdrop" role="presentation">
  <div class="dialog" role="alertdialog" aria-modal="true" aria-label={t("updateQuestionTitle")}>
    <p><strong>{t("updateQuestion")}</strong></p>
    <p class="muted">{t("updateQuestionDetail")}</p>
    <footer>
      <button onclick={() => onchoose(false)}>{t("updateQuestionNo")}</button>
      <button class="primary" onclick={() => onchoose(true)}>{t("updateQuestionYes")}</button>
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
    z-index: 15;
    padding: 16px;
  }
  .dialog {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    width: min(460px, 100%);
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 16px;
  }
  p {
    margin: 0;
  }
  .muted {
    font-size: 13px;
  }
  footer {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 4px;
  }
</style>
