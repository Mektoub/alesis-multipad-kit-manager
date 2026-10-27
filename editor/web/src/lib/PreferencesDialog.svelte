<script>
  // Fenêtre « Préférences » : chaque réglage est appliqué et enregistré dès
  // qu'il change (PATCH /api/preferences, voir editor/preferences.py).
  //
  // `prefs` : préférences actuelles ; `onchange(changes)` : les enregistre
  // (promesse, rejetée avec le message du serveur).
  import { desktop } from "./desktop.js";
  import { t } from "./locale.svelte.js";

  let { prefs, onchange, onclose } = $props();

  const HISTORY_MIN = 10;
  const HISTORY_MAX = 1000;
  const THEMES = [
    ["system", "themeSystem"],
    ["light", "themeLight"],
    ["dark", "themeDark"],
  ];
  // noms des langues dans leur propre langue
  const LANGUAGES = [
    ["system", null],
    ["en", "English"],
    ["fr", "Français"],
  ];

  let error = $state("");

  async function change(changes) {
    error = "";
    try {
      await onchange(changes);
    } catch (err) {
      error = err.message;
    }
  }

  // taille de l'historique : appliquée en quittant le champ (ou Entrée), pas à
  // chaque chiffre tapé, puisqu'une réduction oublie les étapes anciennes
  function changeLimit(e) {
    const value = Number(e.target.value);
    if (!Number.isInteger(value) || value < HISTORY_MIN || value > HISTORY_MAX) {
      error = t("historyLimitError", { min: HISTORY_MIN, max: HISTORY_MAX });
      e.target.value = prefs.history_limit;
      return;
    }
    if (value !== prefs.history_limit) change({ history_limit: value });
  }

  function onkeydown(e) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window {onkeydown} />

<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && onclose()}>
  <div class="dialog" role="dialog" aria-modal="true" aria-label={t("preferences")}>
    <header>
      <h2>{t("preferences")}</h2>
      <button onclick={onclose} aria-label={t("close")}>✕</button>
    </header>

    <fieldset>
      <legend>{t("theme")}</legend>
      <div class="row">
        {#each THEMES as [value, key] (value)}
          <label class="choice">
            <input type="radio" name="theme" {value} checked={prefs.theme === value} onchange={() => change({ theme: value })} />
            {t(key)}
          </label>
        {/each}
      </div>
    </fieldset>

    <fieldset>
      <legend>{t("language")}</legend>
      <div class="row">
        {#each LANGUAGES as [value, name] (value)}
          <label class="choice">
            <input type="radio" name="language" {value} checked={prefs.language === value}
              onchange={() => change({ language: value })} />
            {name ?? t("languageSystem")}
          </label>
        {/each}
      </div>
    </fieldset>

    <fieldset>
      <legend>{t("kitsAndFiles")}</legend>
      <label class="choice">
        <input type="checkbox" checked={prefs.hide_empty} onchange={(e) => change({ hide_empty: e.target.checked })} />
        {t("hideEmpty")}
      </label>
      <label class="choice">
        <input type="checkbox" checked={prefs.reopen_last} onchange={(e) => change({ reopen_last: e.target.checked })} />
        {t("reopenLast")}
      </label>
      <div class="row">
        <span class="muted">{t("recentCount", { n: prefs.recent_files.length })}</span>
        <button onclick={() => change({ recent_files: [] })} disabled={!prefs.recent_files.length}>{t("clearList")}</button>
      </div>
    </fieldset>

    <fieldset>
      <legend>{t("history")}</legend>
      <label class="limit">
        <input type="number" min={HISTORY_MIN} max={HISTORY_MAX} value={prefs.history_limit} onchange={changeLimit}
          onkeydown={(e) => e.key === "Enter" && e.target.blur()} aria-label={t("historySize")} />
        {t("stepsKept")}
      </label>
      <p class="muted explain">{t("historyLimitHelp", { min: HISTORY_MIN, max: HISTORY_MAX })}</p>
    </fieldset>

    {#if desktop}
      <p class="muted explain">{t("windowKept")}</p>
    {/if}

    {#if error}<p class="error" role="alert">{error}</p>{/if}

    <footer>
      <button class="primary" onclick={onclose}>{t("close")}</button>
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
  fieldset {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 0;
    padding: 10px 12px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  legend {
    padding: 0 4px;
    font-weight: 600;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .row button {
    margin-left: auto;
  }
  .choice,
  .limit {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .limit input {
    width: 80px;
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
