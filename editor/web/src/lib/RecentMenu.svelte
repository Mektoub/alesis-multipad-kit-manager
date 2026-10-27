<script>
  // Liste déroulante des fichiers récents (chevron à côté de « Ouvrir »), le plus
  // récent en haut. `files` : chemins absolus (préférences) ; `onselect(chemin)`.
  import { t } from "./locale.svelte.js";

  let { files, onselect, onclose } = $props();

  let menu;
  const split = (file) => {
    const i = Math.max(file.lastIndexOf("/"), file.lastIndexOf("\\"));
    return [file.slice(i + 1), file.slice(0, i)];
  };

  // fenêtre étroite : la liste est décalée vers la gauche pour ne pas sortir
  // de l'écran par la droite
  $effect(() => {
    const overflow = menu.getBoundingClientRect().right - (document.documentElement.clientWidth - 8);
    if (overflow > 0) menu.style.left = `${-overflow}px`;
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

<div class="menu" role="menu" aria-label={t("recentFiles")} bind:this={menu}>
  {#each files as file (file)}
    {@const [name, dir] = split(file)}
    <button role="menuitem" onclick={() => onselect(file)} title={file}>
      <span class="name">{name}</span>
      <span class="dir">{dir}</span>
    </button>
  {/each}
</div>

<style>
  .menu {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    z-index: 12;
    width: min(460px, 90vw);
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
  button:hover {
    background: var(--border);
  }
  .name {
    font-weight: 600;
    white-space: nowrap;
  }
  .dir {
    flex: 1;
    min-width: 0;
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
