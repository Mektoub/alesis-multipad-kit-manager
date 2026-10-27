<script>
  // Fenêtre « Préférences » : chaque réglage est appliqué et enregistré dès
  // qu'il change (PATCH /api/preferences, voir editor/preferences.py).
  //
  // `prefs` : préférences actuelles ; `onchange(changes)` : les enregistre
  // (promesse, rejetée avec le message du serveur).
  import { desktop } from "./desktop.js";

  let { prefs, onchange, onclose } = $props();

  const HISTORY_MIN = 10;
  const HISTORY_MAX = 1000;
  const THEMES = [
    ["system", "Système"],
    ["light", "Clair"],
    ["dark", "Sombre"],
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
      error = `Taille de l'historique : un nombre entier de ${HISTORY_MIN} à ${HISTORY_MAX}.`;
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
  <div class="dialog" role="dialog" aria-modal="true" aria-label="Préférences">
    <header>
      <h2>Préférences</h2>
      <button onclick={onclose} aria-label="Fermer">✕</button>
    </header>

    <fieldset>
      <legend>Thème</legend>
      <div class="row">
        {#each THEMES as [value, label] (value)}
          <label class="choice">
            <input type="radio" name="theme" {value} checked={prefs.theme === value} onchange={() => change({ theme: value })} />
            {label}
          </label>
        {/each}
      </div>
    </fieldset>

    <fieldset>
      <legend>Kits et fichiers</legend>
      <label class="choice">
        <input type="checkbox" checked={prefs.hide_empty} onchange={(e) => change({ hide_empty: e.target.checked })} />
        Masquer les kits vides dans la liste
      </label>
      <label class="choice">
        <input type="checkbox" checked={prefs.reopen_last} onchange={(e) => change({ reopen_last: e.target.checked })} />
        Rouvrir la dernière sauvegarde au lancement
      </label>
      <div class="row">
        <span class="muted">{prefs.recent_files.length} fichier(s) récent(s)</span>
        <button onclick={() => change({ recent_files: [] })} disabled={!prefs.recent_files.length}>Effacer la liste</button>
      </div>
    </fieldset>

    <fieldset>
      <legend>Historique</legend>
      <label class="limit">
        <input type="number" min={HISTORY_MIN} max={HISTORY_MAX} value={prefs.history_limit} onchange={changeLimit}
          onkeydown={(e) => e.key === "Enter" && e.target.blur()} aria-label="Taille de l'historique" />
        étapes gardées pour Annuler / Rétablir
      </label>
      <p class="muted explain">De {HISTORY_MIN} à {HISTORY_MAX}. Une réduction oublie tout de suite les étapes les plus anciennes.</p>
    </fieldset>

    {#if desktop}
      <p class="muted explain">La taille et la position de la fenêtre sont retenues d'un lancement à l'autre.</p>
    {/if}

    {#if error}<p class="error" role="alert">{error}</p>{/if}

    <footer>
      <button class="primary" onclick={onclose}>Fermer</button>
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
