# Changelog

## 0.2.0 — 2026-10-16

- Éditeur web local (`python -m editor`) : FastAPI + Svelte, édition des kits, choix et écoute des samples, ajout de WAV, enregistrement sous un nouveau fichier.
- Classe `Backup` : sauvegarde `.bkf` / `.fac` éditable en mémoire, utilisée par l'éditeur et par `import` / `export`.
- Éditeur web : grille des pads disposée comme sur l'appareil (7-8-9 en haut, deux fois moins hauts, puis 4-5-6 et 1-2-3).
- Éditeur web : recopie des réglages d'un pad vers d'autres (sections au choix, note MIDI conservée par défaut) ; badge du Control (« Click ») sur les pads à la place de la note MIDI.
- Fonction `copy_slot_settings` et route `POST /api/kits/{num}/copy`.
- Éditeur web : déplacer, échanger ou dupliquer un kit vers un autre numéro (`Backup.copy_kit`, `Backup.swap_kits`, route `POST /api/kits/{num}/transfer`).
- Éditeur web : les flèches du champ tempo avancent de 1 BPM (au lieu de 0,1) ; une valeur décimale reste saisissable.
- Éditeur web : les infobulles indiquent la valeur par défaut du réglage pour le pad affiché (relevée dans un kit vide de l'appareil ; `/api/meta` expose `defaults`).
- Éditeur web : « Modifier plusieurs pads… » donne une même valeur à un réglage sur une sélection de pads (`set_slots_value`, `Backup.set_slots`, route `POST /api/kits/{num}/set`).
- Tests : une seule sauvegarde de référence, `tests/ressources/Backup001.bkf` (5 Mo, construite par `tests/construire_reference.py`), indépendante des sauvegardes de travail de `Strike/` ; tests déplacés dans `tests/`, `.fac` construit en mémoire. `Bkf.remove_last_sample` (inverse de `add_sample`, réservé aux tests).
- Éditeur web : infobulle décrivant chaque réglage (paramètres de pad et de wave, kit, éclairage, sample, vélocité), d'après le manuel ; `/api/meta` expose `description` et `help`.
- Script `editeur.sh` : lance l'éditeur en créant ou mettant à jour le venv, les dépendances et l'interface au besoin.
- Correction : dans les pads 1 à 8 des kits `KITC`, les champs dont l'en-tête est recouvert par d'autres données étaient omis ; leur octet valeur est désormais lu et modifiable, et tous les pads affichent les mêmes champs.
- Documentation réorganisée : README réduit aux commandes, un guide par cas d'usage dans `docs/` (modifier un kit, ajouter un sample, éditeur web, contenu de l'export, paramètres, limites, développement).

## 0.1.0 — 2026-10-16

- Export des kits `.bkf` / `.fac` en JSON et import vers une nouvelle sauvegarde (round-trip à l'identique).
- Recalcul des sommes de contrôle (kit, en-têtes `PACKBKF` / `FILEH`) ; validation des plages de valeurs.
- Catalogue des samples (`samples.json`) ; samples désignables par id ou par nom.
- Documentation des formats `.bkf`, `.fac` et `.kit` dans `docs/`, dont `.had` et les listes de samples.
- Ajout de samples WAV depuis le dossier `wav/` de l'export (reproduit à l'identique l'import fait par l'appareil).
- Kits `KITC` : lecture et modification des valeurs des emplacements 1 à 8.
- Paramètres de pad identifiés : `control` (`p14`, 3 = Click On/Off) et `audio_output` (`p0f`, 4 = Aux+Phone).
- Vélocités de wave (`velocity_low`, `velocity_high`) ; correction : le sample d'une wave dont la vélocité n'est pas 0–127 n'était ni exporté ni modifiable.
- Export des WAV des samples utilisateur dans `wav/` (option `--no-wav`) ; l'import ignore les WAV déjà présents (par nom ou par contenu).
