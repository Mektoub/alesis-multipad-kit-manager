<script>
  // Liste déroulante de l'historique (chevron à côté de ↶ ↷), la plus récente
  // étape en haut. Les étapes annulées, encore rétablissables, sont grisées
  // au-dessus de la position actuelle ; un clic ramène à l'étape choisie.
  //
  // `listing` : réponse de GET /api/history ; `onselect({ id, message })`, avec
  // le message de confirmation à afficher.
  import { t } from "./locale.svelte.js";

  let { listing, onselect, onclose } = $props();

  let menu;
  let start = $derived(t(listing.base === 0 ? "historyFileOpened" : "historyStart"));
  let startMessage = $derived(t(listing.base === 0 ? "backToFileOpened" : "backToStart"));
  let rows = $derived([
    ...listing.entries.toReversed(),
    { id: listing.base, label: start, detail: "", done: true, start: true },
  ]);

  // fenêtre étroite : la liste est décalée vers la droite pour ne pas sortir
  // de l'écran par la gauche
  $effect(() => {
    const left = menu.getBoundingClientRect().left;
    if (left < 8) menu.style.right = `${left - 8}px`;
  });

  // clic hors de la liste et du chevron (son parent) : fermeture
  function onpointerdown(e) {
    if (!menu?.parentElement.contains(e.target)) onclose();
  }

  function onkeydown(e) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window {onpointerdown} {onkeydown} />

<div class="menu" role="menu" aria-label={t("historyTitle")} bind:this={menu}>
  {#each rows as row (row.id)}
    {@const current = row.id === listing.position}
    <button
      role="menuitem"
      class:undone={!row.done}
      class:current
      class:start={row.start}
      disabled={current}
      onclick={() => onselect({ id: row.id, message: row.start ? startMessage : t("backTo", { label: row.label }) })}
      title={t(current ? "currentPosition" : row.done ? "undoToHere" : "redoToHere")}
    >
      <span class="label">{row.label}</span>
      {#if row.detail}<span class="detail">{row.detail}</span>{/if}
      {#if row.id === listing.saved}<span class="saved">{t("saved")}</span>{/if}
    </button>
  {/each}
</div>

<style>
  .menu {
    position: absolute;
    top: calc(100% + 6px);
    right: 0; /* bord droit sur le chevron : la liste s'étend vers la gauche */
    z-index: 12;
    width: min(420px, 90vw);
    max-height: 60vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    padding: 4px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 6px 20px rgb(0 0 0 / 25%);
  }
  button {
    display: flex;
    align-items: baseline;
    gap: 8px;
    width: 100%;
    text-align: left;
    border: 0;
    border-radius: 4px;
    background: none;
    padding: 6px 8px;
    font-size: 13px;
  }
  button:not(:disabled):hover {
    background: var(--border);
  }
  .label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .detail {
    color: var(--muted);
    white-space: nowrap;
  }
  .undone .label,
  .undone .detail {
    color: var(--muted);
    font-style: italic;
  }
  .current {
    font-weight: 600;
    box-shadow: inset 3px 0 var(--accent);
  }
  button:disabled {
    opacity: 1;
    cursor: default;
  }
  .start .label {
    color: var(--muted);
  }
  .saved {
    font-size: 11px;
    color: var(--ok);
    border: 1px solid currentcolor;
    border-radius: 3px;
    padding: 0 4px;
  }
</style>
