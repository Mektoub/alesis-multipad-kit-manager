<script>
  import { onMount } from "svelte";
  import { fly } from "svelte/transition";
  import { api } from "./lib/api.js";
  import { desktop } from "./lib/desktop.js";
  import KitEditor from "./lib/KitEditor.svelte";
  import CopyDialog from "./lib/CopyDialog.svelte";
  import ResetDialog from "./lib/ResetDialog.svelte";
  import KitTransferDialog from "./lib/KitTransferDialog.svelte";
  import BulkEditDialog from "./lib/BulkEditDialog.svelte";
  import SamplePicker from "./lib/SamplePicker.svelte";

  let meta = $state(null);
  let session = $state(null); // état renvoyé par /api/state
  let samples = $state([]);
  let currentNum = $state(null);
  let kit = $state(null);
  let selected = $state(0);
  let hideEmpty = $state(true); // kits vides masqués par défaut (le kit affiché reste visible)
  let error = $state("");
  let notice = $state("");
  let picking = $state(null); // "wave_a" | "wave_b" | null
  let copyFrom = $state(null); // emplacement source de la recopie
  let resetFrom = $state(null); // emplacement présélectionné pour « Valeurs par défaut »
  let dragKit = $state(null); // kit glissé par sa poignée dans la liste
  let dropKit = $state(null); // kit survolé pendant le glisser
  let transferring = $state(false); // fenêtre « Déplacer / copier le kit »
  let bulkFrom = $state(null); // emplacement d'où part la modification groupée
  let savePath = $state("");
  let saving = $state(false);
  let syncing = $state(false);
  let openPath = $state(""); // chemin absolu de la sauvegarde à ouvrir

  let fileName = $derived(session?.path?.split(/[\\/]/).pop() ?? "");
  let sampleIndex = $derived(new Map(samples.map((s) => [s.id, s])));
  let visibleKits = $derived(
    (session?.kits ?? []).filter((k) => !hideEmpty || k.name !== "Empty" || k.num === currentNum),
  );

  // Les confirmations (toasts verts) disparaissent seules ; les erreurs restent.
  const NOTICE_MS = 6000;
  $effect(() => {
    if (!notice) return;
    const t = setTimeout(() => (notice = ""), NOTICE_MS);
    return () => clearTimeout(t);
  });

  // Mode bureau : l'application est tenue informée des modifications non
  // enregistrées, pour confirmer la fermeture de la fenêtre.
  $effect(() => {
    desktop?.setDirty(Boolean(session?.dirty));
  });

  // Synchronisation : chaque modification du kit est envoyée au serveur après
  // un court délai ; la réponse (kit relu) remplace la copie locale.
  let lastSynced = "";
  let timer;
  $effect(() => {
    if (!kit) return;
    const snapshot = JSON.stringify(kit);
    if (snapshot === lastSynced) return;
    clearTimeout(timer);
    timer = setTimeout(() => push(currentNum, snapshot), 350);
  });

  async function push(num, snapshot) {
    syncing = true;
    try {
      const saved = await api.saveKit(num, JSON.parse(snapshot));
      error = "";
      if (num !== currentNum) return;
      lastSynced = JSON.stringify(saved);
      if (JSON.stringify(kit) === snapshot) kit = saved;
      session.dirty = true;
      const entry = session.kits.find((k) => k.num === num);
      if (entry) entry.name = saved.name;
    } catch (err) {
      error = `Modification refusée : ${err.message}`;
      if (num === currentNum) await loadKit(num, false);
    } finally {
      syncing = false;
    }
  }

  // Envoie tout de suite une modification encore en attente.
  async function flush() {
    clearTimeout(timer);
    const snapshot = JSON.stringify(kit);
    if (kit && snapshot !== lastSynced) await push(currentNum, snapshot);
  }

  async function copySlot(request) {
    await flush();
    const { kit: updated, skipped } = await api.copySlot(currentNum, request);
    lastSynced = JSON.stringify(updated);
    kit = updated;
    session.dirty = true;
    copyFrom = null;
    const dest = request.targets.map((n) => updated.slots[n - 1]._label).join(", ");
    notice = `Réglages de ${updated.slots[request.source - 1]._label} copiés vers ${dest}.`;
    if (skipped.length) {
      const list = skipped.map((s) => `${updated.slots[s.slot - 1]._label} ${s.field}`).join(", ");
      notice += ` Champs illisibles dans ce kit, non copiés : ${list}.`;
    }
  }

  async function resetSlots(request) {
    await flush();
    const { kit: updated, skipped } = await api.resetSlots(currentNum, request);
    lastSynced = JSON.stringify(updated);
    kit = updated;
    session.dirty = true;
    resetFrom = null;
    const dest = request.targets.map((n) => updated.slots[n - 1]._label).join(", ");
    notice = `Valeurs par défaut remises sur ${dest}.`;
    if (skipped.length) {
      const list = skipped.map((s) => `${updated.slots[s.slot - 1]._label} ${s.field}`).join(", ");
      notice += ` Champs illisibles dans ce kit, non modifiés : ${list}.`;
    }
  }

  async function bulkSet({ kits, targets, field, value, title }) {
    await flush();
    const { skipped, ...state } = await api.setSlotsInKits({ kits, targets, field, value });
    session = state;
    bulkFrom = null;
    await loadKit(currentNum, false);
    const dest = targets.map((n) => kit.slots[n - 1]._label).join(", ");
    const where = kits.length === 1 ? `du kit ${kits[0]}` : `de ${kits.length} kits`;
    notice = `${title} = ${value} appliqué à ${dest} ${where}.`;
    if (skipped.length) {
      notice += ` Champ absent, non modifié : ${skipped.map((s) => `kit ${s.kit} ${kit.slots[s.slot - 1]._label}`).join(", ")}.`;
    }
  }

  async function transferKit({ target, mode }) {
    await flush();
    const source = currentNum;
    const before = session.kits.find((k) => k.num === target)?.name;
    session = await api.transferKit(source, { target, mode });
    transferring = false;
    if (mode === "copy") notice = `Kit ${source} copié en ${target}.`;
    else if (before === "Empty") notice = `Kit ${source} déplacé en ${target}.`;
    else notice = `Kits ${source} et ${target} échangés.`;
    await loadKit(target);
  }

  // Glisser-déposer dans la liste : le kit prend la place du kit visé, ceux
  // d'entre les deux se décalent d'un cran ; le kit affiché suit son numéro.
  async function moveKit(source, target) {
    if (source === target) return;
    await flush();
    const nums = session.kits.map((k) => k.num);
    const [i, j, c] = [source, target, currentNum].map((n) => nums.indexOf(n));
    let shown = c;
    if (c === i) shown = j;
    else if (j < i && j <= c && c < i) shown = c + 1;
    else if (i < j && i < c && c <= j) shown = c - 1;
    session = await api.moveKit(source, { target });
    notice = `Kit ${source} déplacé en ${target}.`;
    await loadKit(nums[shown], false);
  }

  function dragStart(e, num) {
    dragKit = num;
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", num);
  }

  function dragOver(e, num) {
    if (dragKit == null) return; // fichier ou autre contenu glissé
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    dropKit = num;
  }

  function drop(e, num) {
    if (dragKit == null) return;
    e.preventDefault();
    const source = dragKit;
    dragEnd();
    moveKit(source, num).catch((err) => (error = err.message));
  }

  function dragEnd() {
    dragKit = dropKit = null;
  }

  // Supprimer = remplacer par le kit vide de l'appareil, après confirmation.
  async function clearKit() {
    const num = currentNum;
    if (!confirm(`Supprimer le kit ${num} « ${kit.name} » ? Il sera remplacé par un kit vide.`)) return;
    await flush();
    session = await api.clearKit(num);
    notice = `Kit ${num} supprimé.`;
    await loadKit(num);
  }

  async function loadKit(num, resetSlot = true) {
    const data = await api.kit(num);
    lastSynced = JSON.stringify(data);
    currentNum = num;
    kit = data;
    if (resetSlot) selected = 0;
  }

  // Nom proposé pour « Enregistrer sous » : numéro suivant (Backup002.bkf après
  // Backup001.bkf). Si le fichier existe, le serveur demande confirmation.
  function nextName(path) {
    const m = path.match(/^(.*?)(\d+)(\.\w+)$/);
    if (!m) return path.replace(/(\.\w+)$/, "_modifie$1");
    return `${m[1]}${String(Number(m[2]) + 1).padStart(m[2].length, "0")}${m[3]}`;
  }

  async function openBackup(path, force = false) {
    error = notice = "";
    try {
      if (!force) await flush(); // la dernière modification compte pour le serveur
      session = await api.open(path, force);
      openPath = session.path;
      samples = await api.samples();
      savePath = nextName(session.path);
      const first = session.kits.find((k) => k.name !== "Empty") ?? session.kits[0];
      await loadKit(first.num);
    } catch (err) {
      // le serveur refuse d'abandonner des modifications non enregistrées sans confirmation
      if (err.status === 409 && confirm("Des modifications ne sont pas enregistrées. Ouvrir quand même ?")) {
        return openBackup(path, true);
      }
      error = err.message;
    }
  }

  // Recharger : relit le fichier ouvert et abandonne les modifications non
  // enregistrées (après confirmation) ; le kit affiché reste le même.
  async function reload() {
    if (session.dirty && !confirm("Abandonner toutes les modifications non enregistrées et relire le fichier ?")) return;
    clearTimeout(timer); // une modification en attente ne doit pas être renvoyée
    error = notice = "";
    try {
      const num = currentNum;
      session = await api.open(session.path, true);
      samples = await api.samples();
      await loadKit(session.kits.some((k) => k.num === num) ? num : session.kits[0].num, false);
      notice = "Fichier rechargé : modifications non enregistrées abandonnées.";
    } catch (err) {
      error = err.message;
    }
  }

  // `path` null : « Enregistrer » dans le fichier ouvert (copie .bak du fichier
  // d'origine faite par le serveur) ; sinon « Enregistrer sous ».
  async function save(path = null, overwrite = false) {
    saving = true;
    error = notice = "";
    try {
      await flush(); // la dernière modification compte
      session = await api.save(path, overwrite);
      openPath = session.path; // « Enregistrer sous » : le nouveau fichier devient le fichier ouvert
      notice = `Enregistré dans ${session.path}`;
      savePath = nextName(session.path);
    } catch (err) {
      if (err.status === 409 && confirm(`${err.message}\nL'écraser ?`)) return save(path, true);
      error = err.message;
    } finally {
      saving = false;
    }
  }

  // Mode bureau : boîtes de dialogue natives.
  async function openDialog() {
    const path = await desktop.openFile();
    if (path) await openBackup(path);
  }

  async function saveAsDialog() {
    const path = await desktop.saveFile(nextName(session.path));
    if (path) await save(path, true); // la boîte native a déjà confirmé l'écrasement
  }

  // Commandes de l'application de bureau : menu Fichier, fichier passé au
  // lancement, fermeture de la fenêtre.
  async function handleCommand({ command, path }) {
    switch (command) {
      case "open":
        return openDialog();
      case "open-file":
        return openBackup(path);
      case "save":
        if (session?.path) await save();
        return null;
      case "save-as":
        if (session?.path) await saveAsDialog();
        return null;
      case "prepare-close":
        await flush();
        return { dirty: Boolean(session?.dirty) };
      case "save-before-close":
        await save();
        return { saved: !session?.dirty };
      default:
        return { error: `commande inconnue : ${command}` };
    }
  }

  async function uploadSample(file) {
    const added = await api.addSample(file);
    samples = await api.samples();
    session.dirty = true;
    session.user_samples += 1;
    return added;
  }

  function selectSample(id) {
    kit.slots[selected][picking].sample = id;
    picking = null;
  }

  // Dans le navigateur seulement : en mode bureau, l'application confirme
  // elle-même la fermeture (setDirty), et preventDefault la bloquerait.
  function beforeunload(e) {
    if (!desktop && session?.dirty) e.preventDefault();
  }

  onMount(async () => {
    try {
      [meta, session] = await Promise.all([api.meta(), api.state()]);
      if (session.path) {
        openPath = session.path;
        samples = await api.samples();
        savePath = nextName(session.path);
        const first = session.kits.find((k) => k.name !== "Empty") ?? session.kits[0];
        await loadKit(first.num);
      }
    } catch (err) {
      error = err.status === 403
        ? desktop
          ? "Accès refusé : jeton de l'application refusé par le serveur."
          : "Accès refusé : ouvrir l'éditeur par l'adresse affichée au lancement (avec #token=…)."
        : `Serveur injoignable : ${err.message}`;
    }
    // après le chargement initial, pour qu'un fichier transmis au lancement ne
    // soit pas remplacé par l'état lu ci-dessus
    desktop?.onCommand(handleCommand);
  });
</script>

<svelte:window onbeforeunload={beforeunload} />

<header class="top">
  <h1>{__APP_NAMES__.long} <span class="version">v{__APP_NAMES__.version}</span></h1>
  <div class="open">
    {#if desktop}
      <button onclick={openDialog}>Ouvrir…</button>
      {#if session?.path}<span class="file" title={session.path}>{fileName}</span>{/if}
    {:else}
      <input type="text" bind:value={openPath} placeholder="/chemin/vers/Backup001.bkf" aria-label="Sauvegarde à ouvrir (chemin absolu)" />
      <button onclick={() => openBackup(openPath.trim())} disabled={!openPath.trim()}>Ouvrir</button>
    {/if}
  </div>
  {#if session?.path}
    <div class="save">
      <span class="status" class:dirty={session.dirty}>
        {syncing ? "Synchronisation…" : session.dirty ? "Modifications non enregistrées" : "À jour"}
      </span>
      <button onclick={reload} disabled={saving} title="Relire le fichier ouvert et annuler toutes les modifications non enregistrées">Recharger</button>
      {#if !desktop}<input type="text" bind:value={savePath} aria-label="Fichier de destination" />{/if}
      <button class="primary" onclick={() => save()} disabled={saving} title="Écrit dans le fichier ouvert ; au premier enregistrement, une copie .bak de l'original est conservée">Enregistrer</button>
      {#if desktop}
        <button onclick={saveAsDialog} disabled={saving}>Enregistrer sous…</button>
      {:else}
        <button onclick={() => save(savePath)} disabled={saving}>Enregistrer sous</button>
      {/if}
    </div>
  {/if}
</header>

<!-- Messages en toasts (en haut, au milieu, au-dessus des fenêtres) : les erreurs
     restent jusqu'à leur fermeture, les confirmations disparaissent seules. -->
<div class="toasts">
  {#if error}
    <div class="toast error" role="alert" transition:fly={{ y: -16, duration: 150 }}>
      <span>{error}</span><button onclick={() => (error = "")} aria-label="Fermer">✕</button>
    </div>
  {/if}
  {#if notice}
    <div class="toast ok" role="status" transition:fly={{ y: -16, duration: 150 }}>
      <span>{notice}</span><button onclick={() => (notice = "")} aria-label="Fermer">✕</button>
    </div>
  {/if}
</div>

{#if session?.path && meta}
  <main class="layout">
    <aside>
      <div class="aside-head">
        <h2>Kits</h2>
        <label class="muted"><input type="checkbox" bind:checked={hideEmpty} /> masquer les vides</label>
      </div>
      <p class="muted info">{session.path} · {session.kind} · {session.user_samples} sample(s) perso</p>
      <ul>
        {#each visibleKits as k (k.num)}
          <li
            class:dragged={dragKit === k.num}
            class:drop-before={dropKit === k.num && dragKit !== k.num && k.num < dragKit}
            class:drop-after={dropKit === k.num && dragKit !== k.num && k.num > dragKit}
            ondragover={(e) => dragOver(e, k.num)}
            ondragleave={() => dropKit === k.num && (dropKit = null)}
            ondrop={(e) => drop(e, k.num)}
          >
            <button class:active={k.num === currentNum} onclick={() => loadKit(k.num)}>
              <span class="num">{k.num}</span>
              <span class="kname" class:empty={k.name === "Empty"}>{k.name}</span>
            </button>
            {#if !k.empty}
              <span
                class="grip"
                role="button"
                tabindex="-1"
                draggable="true"
                title="Glisser pour déplacer le kit (les kits suivants se décalent)"
                aria-label="Déplacer le kit {k.num}"
                ondragstart={(e) => dragStart(e, k.num)}
                ondragend={dragEnd}
              >⠿</span>
            {/if}
          </li>
        {/each}
      </ul>
    </aside>
    <section class="content">
      {#if kit}
        <KitEditor {kit} {meta} {sampleIndex} bind:selected onpick={(w) => (picking = w)} oncopy={(n) => (copyFrom = n)} onreset={(n) => (resetFrom = n)} ontransfer={() => (transferring = true)} onclear={clearKit} empty={session.kits.find((k) => k.num === currentNum)?.empty} onbulk={(n) => (bulkFrom = n)} />
      {/if}
    </section>
  </main>
{:else if meta}
  <main class="welcome">
    {#if desktop}
      <p>Ouvrez une sauvegarde <code>.bkf</code> (kits et samples utilisateur) ou <code>.fac</code> avec <strong>Ouvrir…</strong>.</p>
    {:else}
      <p>Indiquez le chemin complet d'une sauvegarde <code>.bkf</code> (kits et samples utilisateur) ou <code>.fac</code>, puis cliquez sur <strong>Ouvrir</strong>.</p>
    {/if}
  </main>
{/if}

{#if resetFrom && kit}
  <ResetDialog {kit} {meta} source={resetFrom} onreset={resetSlots} onclose={() => (resetFrom = null)} />
{/if}
{#if copyFrom && kit}
  <CopyDialog {kit} source={copyFrom} oncopy={copySlot} onclose={() => (copyFrom = null)} />
{/if}

{#if bulkFrom && kit}
  <BulkEditDialog {kit} {meta} source={bulkFrom} kits={session.kits} {currentNum} onapply={bulkSet} onclose={() => (bulkFrom = null)} />
{/if}

{#if transferring && kit}
  <KitTransferDialog kits={session.kits} source={currentNum} ontransfer={transferKit} onclose={() => (transferring = false)} />
{/if}

{#if picking && kit}
  <SamplePicker
    {samples}
    current={kit.slots[selected][picking].sample}
    onselect={selectSample}
    onclose={() => (picking = null)}
    onupload={uploadSample}
  />
{/if}

<style>
  .top {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 20px;
    padding: 10px 16px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
  }
  h1 {
    margin: 0;
    font-size: 17px;
  }
  .version {
    font-size: 12px;
    font-weight: normal;
    color: var(--muted);
  }
  .open,
  .save {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
  }
  .open input {
    width: 380px;
    max-width: 40vw;
  }
  .save {
    margin-left: auto;
  }
  .file {
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .save input {
    width: 300px;
    max-width: 50vw;
  }
  .status {
    font-size: 12px;
    color: var(--ok);
  }
  .status.dirty {
    color: var(--accent);
  }
  .toasts {
    position: fixed;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 20;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    max-width: min(440px, calc(100vw - 32px));
    pointer-events: none;
  }
  .toast {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 12px 10px 14px;
    border: 1px solid var(--border);
    border-left-width: 4px;
    border-radius: var(--radius);
    background: var(--panel);
    color: var(--text);
    box-shadow: 0 4px 16px rgb(0 0 0 / 18%);
    pointer-events: auto;
  }
  .toast span {
    flex: 1;
    overflow-wrap: anywhere;
  }
  .toast button {
    border: 0;
    background: transparent;
    padding: 0 2px;
    color: var(--muted);
  }
  .toast.error {
    border-left-color: var(--danger);
    background: var(--danger-bg);
    color: var(--danger);
  }
  .toast.ok {
    border-left-color: var(--ok);
  }
  .layout {
    display: grid;
    grid-template-columns: 260px 1fr;
    min-height: calc(100vh - 56px);
  }
  aside {
    border-right: 1px solid var(--border);
    background: var(--panel);
    padding: 12px;
    overflow-y: auto;
    max-height: calc(100vh - 56px);
    position: sticky;
    top: 0;
  }
  .aside-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .aside-head label {
    font-size: 12px;
  }
  .info {
    font-size: 12px;
    margin: 6px 0 10px;
    word-break: break-all;
  }
  aside ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  aside li {
    display: flex;
    align-items: center;
    border-block: 2px solid transparent;
  }
  aside li.drop-before {
    border-top-color: var(--accent);
  }
  aside li.drop-after {
    border-bottom-color: var(--accent);
  }
  aside li.dragged {
    opacity: 0.5;
  }
  .grip {
    padding: 0 6px;
    color: var(--muted);
    cursor: grab;
    user-select: none;
    opacity: 0;
  }
  aside li:hover .grip,
  aside li.dragged .grip {
    opacity: 1;
  }
  .grip:active {
    cursor: grabbing;
  }
  aside li button {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 10px;
    border: 0;
    background: transparent;
    text-align: left;
  }
  aside li button.active {
    background: var(--panel-2);
    font-weight: 600;
  }
  .num {
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .kname.empty {
    color: var(--muted);
    font-style: italic;
  }
  .content {
    padding: 16px;
    min-width: 0;
  }
  .welcome {
    padding: 40px 16px;
    text-align: center;
  }
  @media (max-width: 760px) {
    .layout {
      grid-template-columns: 1fr;
    }
    aside {
      position: static;
      max-height: 240px;
      border-right: 0;
      border-bottom: 1px solid var(--border);
    }
    .save {
      margin-left: 0;
      flex-wrap: wrap;
    }
  }
</style>
