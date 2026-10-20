# Modifier un kit

Deux façons de faire : l'[éditeur web](editeur-web.md), ou la ligne de commande
décrite ici, qui passe par des fichiers JSON.

## 1. Faire une sauvegarde sur l'appareil

Sur le Strike MultiPad : *Utility > Backup > Save All User Kits*, sur une clé USB
formatée en FAT32. Le fichier apparaît dans
`Strike/All User Kit And Sample Backup/BackupNNN.bkf`.

Copier ce dossier sur l'ordinateur et **garder une copie de la sauvegarde d'origine**.

## 2. Exporter

```bash
python3 -m strike_kits export "Strike/All User Kit And Sample Backup/Backup001.bkf" mes_kits
```

Le dossier `mes_kits/` contient un JSON par kit, le catalogue des samples et les
WAV de tes samples (voir [Contenu de l'export](contenu-export.md)). L'option
`--no-wav` évite de copier les WAV.

## 3. Modifier les JSON

Ouvrir `mes_kits/kits/NNN_Nom.json` dans un éditeur de texte. Les pads P1 à P9
sont les emplacements 1 à 9 de la liste `slots`. Quelques exemples :

```jsonc
// renommer le kit et changer le tempo
"name": "Mon Kit",
"tempo": 98.5,

// pad 5 : note MIDI, couleur de LED (9 = Cyan), sample désigné par son nom
{ "slot": 5,
  "params": { "midi_note": 41 },
  "light": { "play_color": 9 },
  "wave_a": { "sample": "Crazy in Love sample track" } }

// pad 9 : démarrer/arrêter le click, sortie Aux+Phone
{ "slot": 9, "params": { "control": 3, "audio_output": 4 } }

// deux couches selon la force de frappe
"wave_a": { "sample": 7903, "velocity_low": 0,   "velocity_high": 100 },
"wave_b": { "sample": 7904, "velocity_low": 101, "velocity_high": 127 }
```

Il suffit de modifier les valeurs existantes : on n'a pas besoin de supprimer les
autres champs, et ceux qui ne changent pas sont réécrits à l'identique. Le sens
et la plage de chaque champ sont décrits dans [Paramètres](parametres.md).

Un sample se désigne par son id ou par son nom exact (voir `samples.json`) ;
`null` retire le sample. Pour utiliser un nouveau WAV, voir
[Ajouter un sample](ajouter-un-sample.md).

## 4. Produire une nouvelle sauvegarde

```bash
python3 -m strike_kits import "Strike/All User Kit And Sample Backup/Backup001.bkf" mes_kits \
    -o "Strike/All User Kit And Sample Backup/Backup002.bkf"
```

- L'outil repart de la sauvegarde d'origine (qu'il refuse d'écraser), applique les
  JSON et les nouveaux WAV, puis recalcule les sommes de contrôle.
- Les octets non décodés sont conservés tels quels : un export suivi d'un import
  sans modification redonne un fichier identique octet pour octet.
- Une valeur hors plage, un sample introuvable ou un champ inconnu arrête l'import
  avec un message qui indique le fichier et l'emplacement concernés. Rien n'est
  écrit dans ce cas.

## 5. Charger sur l'appareil

Copier le nouveau `.bkf` dans `Strike/All User Kit And Sample Backup/` sur la clé
USB, puis le charger depuis le menu *Utility > Backup* de l'appareil.

## Kits créés sur l'appareil (`KITC`)

Quand on enregistre un kit sur l'appareil, il est écrit dans une variante (`KITC`)
où, pour les pads 1 à 8, seules les valeurs sont stockées. Tous les champs restent
lisibles et modifiables, comme dans les kits vides (`KITH`). Détails :
[format des kits](format-bkf.md#particularités-de-la-variante-kitc).

## Sauvegardes `.fac`

Les fichiers `Strike/BackUp/…/STRIKE_BACKUP_KIT.fac` contiennent les 100 kits,
sans samples. Ils s'exportent et s'importent de la même façon, mais on ne peut pas
y ajouter de samples.
