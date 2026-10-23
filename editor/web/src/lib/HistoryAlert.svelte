<script>
  // Alerte avant une action hors historique (déplacer, transférer ou supprimer un
  // kit) quand des modifications peuvent encore être annulées ou rétablies :
  // l'action viderait l'historique. `onchoose` reçoit "cancel", "save" ou "continue".
  let { question, onchoose } = $props();

  function onkeydown(e) {
    if (e.key === "Escape") onchoose("cancel");
  }
</script>

<svelte:window {onkeydown} />

<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && onchoose("cancel")}>
  <div class="dialog" role="alertdialog" aria-modal="true" aria-label="Historique des modifications">
    <p><strong>{question}</strong></p>
    <p class="muted">
      Cette action ne peut pas être annulée et vide l'historique des modifications : Annuler et Rétablir ne
      pourront plus revenir avant elle. Les modifications non enregistrées sont conservées.
    </p>
    <footer>
      <button onclick={() => onchoose("cancel")}>Annuler</button>
      <button onclick={() => onchoose("save")}>Enregistrer et continuer</button>
      <button class="primary" onclick={() => onchoose("continue")}>Continuer</button>
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
