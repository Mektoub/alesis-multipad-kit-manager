<script>
  import { onMount, untrack } from "svelte";
  import { fly } from "svelte/transition";
  import { api } from "./lib/api.js";
  import { desktop } from "./lib/desktop.js";
  import KitEditor from "./lib/KitEditor.svelte";
  import CopyDialog from "./lib/CopyDialog.svelte";
  import ResetDialog from "./lib/ResetDialog.svelte";
  import KitTransferDialog from "./lib/KitTransferDialog.svelte";
  import BulkEditDialog from "./lib/BulkEditDialog.svelte";
  import SamplePicker from "./lib/SamplePicker.svelte";
  import SampleManager from "./lib/SampleManager.svelte";
  import HistoryAlert from "./lib/HistoryAlert.svelte";
  import HistoryMenu from "./lib/HistoryMenu.svelte";
  import PreferencesDialog from "./lib/PreferencesDialog.svelte";
  import RecentMenu from "./lib/RecentMenu.svelte";
  import { applyTheme } from "./lib/theme.js";
  import { resolveLanguage } from "./lib/i18n.js";
  import { language, setLanguage, t } from "./lib/locale.svelte.js";
  import { SHORTCUTS, isMac, isTextField, shortcut } from "./lib/shortcuts.js";

  let meta = $state(null);
  let session = $state(null); // état renvoyé par /api/state
  let samples = $state([]);
  let currentNum = $state(null);
  let kit = $state(null);
  let selected = $state(0);
  let prefs = $state(null); // préférences de l'utilisateur (GET /api/preferences)
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
  let historyList = $state(null); // liste déroulante de l'historique (GET /api/history), ouverte
  let historyAlert = $state(null); // { question, resolve } : alerte avant une action hors historique
  let prefsOpen = $state(false); // fenêtre Préférences
  let samplesOpen = $state(false); // gestionnaire des samples utilisateur
  let recentOpen = $state(false); // liste déroulante des fichiers récents

  let fileName = $derived(session?.path?.split(/[\\/]/).pop() ?? "");
  // libellés des dernières étapes à annuler et à rétablir (editor/history.py)
  let canUndo = $derived(Boolean(session?.history?.undo));
  let canRedo = $derived(Boolean(session?.history?.redo));
  let sampleIndex = $derived(new Map(samples.map((s) => [s.id, s])));
  // kits vides masqués par défaut (le kit affiché reste visible)
  let hideEmpty = $derived(prefs?.hide_empty ?? true);
  let recentFiles = $derived(prefs?.recent_files ?? []);
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

  $effect(() => applyTheme(prefs?.theme ?? "system"));

  // Langue (préférence) : textes de l'interface, menus de l'application de
  // bureau ; les textes venus du serveur (infobulles, historique) sont relus.
  $effect(() => {
    if (!prefs) return;
    const lang = resolveLanguage(prefs.language);
    desktop?.setLanguage(lang);
    if (lang === untrack(language)) return;
    setLanguage(lang);
    untrack(reloadTexts);
  });

  async function reloadTexts() {
    try {
      [meta, session] = await Promise.all([api.meta(), api.state()]);
    } catch (err) {
      error = err.message;
    }
  }

  // Mode bureau : menu Fichier › Ouvrir récent
  $effect(() => {
    desktop?.setRecent(recentFiles);
  });

  // Enregistre des préférences ; l'erreur remonte à l'appelant.
  async function setPrefs(changes) {
    prefs = await api.setPreferences(changes);
  }

  // Après une ouverture ou un enregistrement : fichiers récents mis à jour par le serveur.
  async function refreshPrefs() {
    try {
      prefs = await api.preferences();
    } catch {
      // sans conséquence : la liste sera relue plus tard
    }
  }

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
      edited();
      const entry = session.kits.find((k) => k.num === num);
      if (entry) entry.name = saved.name;
    } catch (err) {
      error = t("changeRefused", { message: err.message });
      if (num === currentNum) await loadKit(num, false);
    } finally {
      syncing = false;
    }
  }

  // Après une modification de paramètres faite par l'éditeur (PUT, qui ne
  // renvoie que le kit) : une étape de plus à annuler, plus rien à rétablir.
  function edited(history = { undo: t("lastChange"), redo: null }) {
    session.dirty = true;
    session.history = history;
  }

  // Envoie tout de suite une modification encore en attente.
  async function flush() {
    clearTimeout(timer);
    const snapshot = JSON.stringify(kit);
    if (kit && snapshot !== lastSynced) await push(currentNum, snapshot);
  }

  async function copySlot(request) {
    await flush();
    const { kit: updated, skipped, history } = await api.copySlot(currentNum, request);
    lastSynced = JSON.stringify(updated);
    kit = updated;
    edited(history);
    copyFrom = null;
    const dest = request.targets.map((n) => updated.slots[n - 1]._label).join(", ");
    notice = t("copied", { source: updated.slots[request.source - 1]._label, dest });
    if (skipped.length) {
      const list = skipped.map((s) => `${updated.slots[s.slot - 1]._label} ${s.field}`).join(", ");
      notice += t("copySkipped", { list });
    }
  }

  async function resetSlots(request) {
    await flush();
    const { kit: updated, skipped, history } = await api.resetSlots(currentNum, request);
    lastSynced = JSON.stringify(updated);
    kit = updated;
    edited(history);
    resetFrom = null;
    const dest = request.targets.map((n) => updated.slots[n - 1]._label).join(", ");
    notice = t("resetDone", { dest });
    if (skipped.length) {
      const list = skipped.map((s) => `${updated.slots[s.slot - 1]._label} ${s.field}`).join(", ");
      notice += t("resetSkipped", { list });
    }
  }

  async function bulkSet({ kits, targets, field, value, title }) {
    await flush();
    const { skipped, ...state } = await api.setSlotsInKits({ kits, targets, field, value });
    session = state;
    bulkFrom = null;
    await loadKit(currentNum, false);
    const dest = targets.map((n) => kit.slots[n - 1]._label).join(", ");
    const where = kits.length === 1 ? t("bulkOneKit", { kit: kits[0] }) : t("bulkKits", { n: kits.length });
    notice = t("bulkDone", { title, value, dest, where });
    if (skipped.length) {
      const list = skipped.map((s) => `kit ${s.kit} ${kit.slots[s.slot - 1]._label}`).join(", ");
      notice += t("bulkSkipped", { list });
    }
  }

  async function transferKit({ target, mode }) {
    await flush();
    const source = currentNum;
    const before = session.kits.find((k) => k.num === target)?.name;
    let question = t("askMove", { source, target });
    if (mode === "copy") question = t("askCopy", { source, target });
    else if (before !== "Empty") question = t("askSwap", { source, target });
    if (!(await outsideHistory(question))) return; // la fenêtre reste ouverte
    session = await api.transferKit(source, { target, mode });
    transferring = false;
    if (mode === "copy") notice = t("kitCopied", { source, target });
    else if (before === "Empty") notice = t("kitMoved", { source, target });
    else notice = t("kitsSwapped", { source, target });
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
    if (!(await outsideHistory(t("askMove", { source, target })))) return;
    session = await api.moveKit(source, { target });
    notice = t("kitMoved", { source, target });
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
    const question = t("askClear", { num, name: kit.name });
    await flush();
    if (canUndo || canRedo ? !(await outsideHistory(question)) : !confirm(question)) return;
    session = await api.clearKit(num);
    notice = t("kitCleared", { num });
    await loadKit(num);
  }

  // Déplacer, transférer ou supprimer un kit vide l'historique : s'il reste des
  // modifications à annuler ou à rétablir, l'utilisateur choisit d'abandonner
  // l'action, d'enregistrer avant, ou de continuer. Vrai si l'action peut se faire.
  async function outsideHistory(question) {
    if (!canUndo && !canRedo) return true;
    const choice = await new Promise((resolve) => (historyAlert = { question, resolve }));
    historyAlert = null;
    if (choice === "save") {
      await save();
      return !session.dirty;
    }
    return choice === "continue";
  }

  // Annuler / Rétablir : `name` = "undo" | "redo". Le kit affiché est relu ;
  // si l'étape ne concerne qu'un autre kit, celui-ci est affiché.
  async function step(name) {
    if (!session?.path || saving) return;
    error = "";
    try {
      await flush(); // la modification en attente devient une étape
      const { done, detail, changed, ...state } = await api[name]();
      await applied(state, changed);
      notice = t(name === "undo" ? "undone" : "redone", { label: `${done}${detail ? ` (${detail})` : ""}` });
    } catch (err) {
      if (err.status !== 409) error = err.message;
      session = await api.state(); // rien à annuler : l'interface se remet à jour
    }
  }

  // Après annuler / rétablir : nouvel état, kit affiché relu ; si seul un autre
  // kit a changé, c'est lui qui est affiché.
  async function applied(state, changed) {
    session = state;
    const num = changed.length === 1 && !changed.includes(currentNum) ? changed[0] : currentNum;
    await loadKit(num, num !== currentNum);
  }

  async function toggleHistory() {
    if (historyList) {
      historyList = null;
      return;
    }
    try {
      await flush(); // la modification en attente figure dans la liste
      historyList = await api.history();
    } catch (err) {
      error = err.message;
    }
  }

  // Liste de l'historique : revenir à une étape (annuler ou rétablir celles
  // d'entre les deux), `message` : confirmation à afficher.
  async function gotoStep({ id, message }) {
    historyList = null;
    error = "";
    try {
      await flush();
      const { changed, ...state } = await api.historyGoto(id);
      await applied(state, changed);
      notice = message;
    } catch (err) {
      error = err.message;
      session = await api.state();
    }
  }

  // Raccourcis clavier, hors champs de saisie (qui gardent leur propre annulation)
  // et hors fenêtres de dialogue. Sous macOS, le menu de l'application de bureau
  // reçoit lui-même ⌘Z et ⌘⇧Z (commandes undo / redo).
  function keydown(e) {
    const name = shortcut(e);
    if (!name || isTextField(document.activeElement)) return;
    if (desktop && e.metaKey && e.key.toLowerCase() === "z") return;
    if (copyFrom || resetFrom || bulkFrom || transferring || picking || historyAlert || historyList) return;
    if (prefsOpen || recentOpen || samplesOpen) return;
    e.preventDefault();
    step(name);
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
    recentOpen = false;
    try {
      if (!force) await flush(); // la dernière modification compte pour le serveur
      session = await api.open(path, force);
      await refreshPrefs();
      openPath = session.path;
      samples = await api.samples();
      savePath = nextName(session.path);
      const first = session.kits.find((k) => k.name !== "Empty") ?? session.kits[0];
      await loadKit(first.num);
    } catch (err) {
      // le serveur refuse d'abandonner des modifications non enregistrées sans confirmation
      if (err.status === 409 && confirm(t("askOpenUnsaved"))) {
        return openBackup(path, true);
      }
      error = err.message;
    }
  }

  // Recharger : relit le fichier ouvert et abandonne les modifications non
  // enregistrées (après confirmation) ; le kit affiché reste le même.
  async function reload() {
    if (session.dirty && !confirm(t("askReload"))) return;
    clearTimeout(timer); // une modification en attente ne doit pas être renvoyée
    error = notice = "";
    try {
      const num = currentNum;
      session = await api.open(session.path, true);
      samples = await api.samples();
      await loadKit(session.kits.some((k) => k.num === num) ? num : session.kits[0].num, false);
      notice = t("reloaded");
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
      if (path != null) await refreshPrefs(); // « Enregistrer sous » : nouveau fichier récent
      openPath = session.path; // « Enregistrer sous » : le nouveau fichier devient le fichier ouvert
      notice = t("savedTo", { path: session.path });
      savePath = nextName(session.path);
    } catch (err) {
      if (err.status === 409 && confirm(t("askOverwrite", { message: err.message }))) return save(path, true);
      error = err.message;
    } finally {
      saving = false;
    }
  }

  // Mode bureau : boîtes de dialogue natives.
  async function openDialog() {
    const path = await desktop.openFile(prefs?.last_dir);
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
      case "undo":
      case "redo":
        // menu Édition : dans un champ de saisie, annulation de la frappe
        if (isTextField(document.activeElement)) document.execCommand(command);
        else await step(command);
        return null;
      case "preferences":
        prefsOpen = true;
        return null;
      case "samples":
        openSamples();
        return null;
      case "clear-recent":
        await setPrefs({ recent_files: [] }).catch((err) => (error = err.message));
        return null;
      case "prepare-close":
        await flush();
        return { dirty: Boolean(session?.dirty) };
      case "save-before-close":
        await save();
        return { saved: !session?.dirty };
      default:
        return { error: t("unknownCommand", { command }) };
    }
  }

  function openSamples() {
    if (session?.kind === "bkf") samplesOpen = true;
    else if (session?.path) error = t("samplesBkfOnly");
  }

  async function uploadSample(file) {
    const added = await api.addSample(file);
    samples = await api.samples();
    session = await api.state(); // ajout hors historique (editor/history.py)
    return added;
  }

  async function renameSample(id, name) {
    await api.renameSample(id, name);
    samples = await api.samples();
    session = await api.state(); // renommage hors historique (editor/history.py)
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
      // langue d'abord : les textes du serveur en dépendent
      prefs = await api.preferences();
      setLanguage(resolveLanguage(prefs.language));
      [meta, session] = await Promise.all([api.meta(), api.state()]);
      // navigateur : chemin proposé, la dernière sauvegarde ouverte
      openPath = recentFiles[0] ?? "";
      if (session.path) {
        openPath = session.path;
        samples = await api.samples();
        savePath = nextName(session.path);
        const first = session.kits.find((k) => k.name !== "Empty") ?? session.kits[0];
        await loadKit(first.num);
      }
    } catch (err) {
      error = err.status === 403
        ? t(desktop ? "tokenRefusedDesktop" : "tokenRefusedBrowser")
        : t("serverUnreachable", { message: err.message });
    }
    // après le chargement initial, pour qu'un fichier transmis au lancement ne
    // soit pas remplacé par l'état lu ci-dessus
    desktop?.onCommand(handleCommand);
  });
</script>

<svelte:window onbeforeunload={beforeunload} onkeydown={keydown} />

<header class="top">
  <h1>{__APP_NAMES__.long} <span class="version">v{__APP_NAMES__.version}</span></h1>
  <div class="open">
    {#if desktop}
      <button onclick={openDialog}>{t("openDialog")}</button>
    {:else}
      <input type="text" bind:value={openPath} placeholder={t("openPlaceholder")} aria-label={t("openLabel")} />
      <button onclick={() => openBackup(openPath.trim())} disabled={!openPath.trim()}>{t("open")}</button>
    {/if}
    <span class="recent">
      <button class="icon chevron" onclick={() => (recentOpen = !recentOpen)} disabled={!recentFiles.length}
        aria-label={t("recentFiles")} aria-expanded={recentOpen} title={t("recentFiles")}>▾</button>
      {#if recentOpen}
        <RecentMenu files={recentFiles} onselect={(path) => openBackup(path)} onclose={() => (recentOpen = false)} />
      {/if}
    </span>
    {#if desktop && session?.path}<span class="file" title={session.path}>{fileName}</span>{/if}
  </div>
  {#if session?.path}
    <div class="save">
      <span class="status" class:dirty={session.dirty}>
        {t(syncing ? "syncing" : session.dirty ? "unsaved" : "upToDate")}
      </span>
      <button class="icon" onclick={() => step("undo")} disabled={saving || !canUndo} aria-label={t("undo")}
        title={t(canUndo ? "undoTitleLabel" : "undoTitle", { label: session.history.undo, keys: SHORTCUTS.undo })}>↶</button>
      <button class="icon" onclick={() => step("redo")} disabled={saving || !canRedo} aria-label={t("redo")}
        title={t(canRedo ? "redoTitleLabel" : "redoTitle", { label: session.history.redo, keys: t(isMac ? "redoKeysMac" : "redoKeys") })}>↷</button>
      <span class="history">
        <button class="icon chevron" onclick={toggleHistory} disabled={saving || (!canUndo && !canRedo)}
          aria-label={t("history")} aria-expanded={Boolean(historyList)} title={t("historyTitle")}>▾</button>
        {#if historyList}
          <HistoryMenu listing={historyList} onselect={gotoStep} onclose={() => (historyList = null)} />
        {/if}
      </span>
      {#if session.kind === "bkf"}
        <button onclick={openSamples} title={t("samplesTitle")}>{t("samplesButton")}</button>
      {/if}
      <button onclick={reload} disabled={saving} title={t("reloadTitle")}>{t("reload")}</button>
      {#if !desktop}<input type="text" bind:value={savePath} aria-label={t("destination")} />{/if}
      <button class="primary" onclick={() => save()} disabled={saving} title={t("saveTitle")}>{t("save")}</button>
      {#if desktop}
        <button onclick={saveAsDialog} disabled={saving}>{t("saveAsDialog")}</button>
      {:else}
        <button onclick={() => save(savePath)} disabled={saving}>{t("saveAs")}</button>
      {/if}
    </div>
  {/if}
  <button class="icon prefs" class:alone={!session?.path} onclick={() => (prefsOpen = true)} aria-label={t("preferences")}
    title={t("preferences")}>⚙</button>
</header>

<!-- Messages en toasts (en haut, au milieu, au-dessus des fenêtres) : les erreurs
     restent jusqu'à leur fermeture, les confirmations disparaissent seules. -->
<div class="toasts">
  {#if error}
    <div class="toast error" role="alert" transition:fly={{ y: -16, duration: 150 }}>
      <span>{error}</span><button onclick={() => (error = "")} aria-label={t("close")}>✕</button>
    </div>
  {/if}
  {#if notice}
    <div class="toast ok" role="status" transition:fly={{ y: -16, duration: 150 }}>
      <span>{notice}</span><button onclick={() => (notice = "")} aria-label={t("close")}>✕</button>
    </div>
  {/if}
</div>

{#if session?.path && meta}
  <main class="layout">
    <aside>
      <div class="aside-head">
        <h2>{t("kits")}</h2>
        <label class="muted"><input type="checkbox" checked={hideEmpty}
          onchange={(e) => setPrefs({ hide_empty: e.target.checked }).catch((err) => (error = err.message))} /> {t("hideEmptyShort")}</label>
      </div>
      <p class="muted info">{t("fileInfo", { path: session.path, kind: session.kind, n: session.user_samples })}</p>
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
                title={t("dragKitTitle")}
                aria-label={t("dragKitLabel", { num: k.num })}
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
      <!-- eslint-disable-next-line svelte/no-at-html-tags -- texte fixe de messages.js -->
      <p>{@html t("welcomeDesktop")}</p>
    {:else}
      <!-- eslint-disable-next-line svelte/no-at-html-tags -- texte fixe de messages.js -->
      <p>{@html t("welcomeBrowser")}</p>
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

{#if prefsOpen && prefs}
  <PreferencesDialog {prefs} onchange={setPrefs} onclose={() => (prefsOpen = false)} />
{/if}

{#if historyAlert}
  <HistoryAlert question={historyAlert.question} onchoose={historyAlert.resolve} />
{/if}

{#if samplesOpen}
  <SampleManager
    load={api.userSamples}
    onrename={renameSample}
    onupload={uploadSample}
    onclose={() => (samplesOpen = false)}
  />
{/if}

{#if picking && kit}
  <SamplePicker
    {samples}
    current={kit.slots[selected][picking].sample}
    onselect={selectSample}
    onclose={() => (picking = null)}
    onupload={uploadSample}
    onrename={renameSample}
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
  .history,
  .recent {
    position: relative;
  }
  .prefs.alone {
    margin-left: auto;
  }
  .chevron {
    margin-left: -6px;
    padding-inline: 4px;
  }
  .icon {
    font-size: 16px;
    line-height: 1;
    padding-inline: 8px;
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
