# Contenu de l'export

`python3 strike_kits.py export SAUVEGARDE DOSSIER` produit :

```
DOSSIER/
├── kits/
│   ├── 031_WhereIs.json
│   ├── 032_CrazyInLove.json
│   └── …                       un fichier par kit
├── samples.json                catalogue id → nom de tous les samples
└── wav/                        samples utilisateur (absent avec --no-wav ou pour un .fac)
    ├── Crazy in Love sample track.wav
    └── …
```

## `kits/NNN_Nom.json`

`NNN` est le numéro du kit et sert de clé à l'import. La partie après `_` est
libre : on peut renommer le fichier.

```jsonc
{
  "format": "KITH",            // KITH (kit vide ou d'usine) ou KITC (enregistré sur l'appareil)
  "name": "Mon Kit",           // 16 caractères max
  "level": 90,                 // volume du kit, 0–100
  "tempo": 120.0,              // 30–280 BPM, au dixième
  "slots": [                   // 24 emplacements : 1–9 = pads P1–P9
    {
      "slot": 1,
      "_label": "P1",
      "light":  { "play_color": 16, "play_mode": 3, "stop_color": 8, "stop_mode": 1 },
      "params": { "volume": 90, "pan": 15, "midi_note": 36, "control": 0, "p09": 0, "…": 0 },
      "wave_a": {
        "sample": 8071,
        "_sample_name": "WIMH sample track",
        "velocity_low": 0,
        "velocity_high": 127,
        "params": { "volume": 90, "pan": 15, "fade_in": 0, "…": 0 }
      },
      "wave_b": { "sample": null, "velocity_low": 0, "velocity_high": 127, "params": { "…": 0 } }
    }
  ]
}
```

- Le sens de chaque champ est décrit dans [Paramètres](parametres.md).
- Les clés qui commencent par `_` sont informatives et ignorées à l'import.
- `sample` vaut un id de sample ou `null` (aucun sample). À l'import, il accepte aussi
  le nom exact d'un sample, y compris ceux ajoutés depuis `wav/`.
- Les paramètres `pXX` (id hexadécimal) ne sont pas encore identifiés ; ils sont
  modifiables quand même.
- Dans les kits `KITC`, certains champs des pads 1 à 8 peuvent être absents : ils
  sont illisibles et ne peuvent pas être modifiés.
- Chaque paramètre a une plage min/max stockée dans le kit. Une valeur modifiée hors
  plage est refusée à l'import.

## `samples.json`

Catalogue de tous les samples connus de l'appareil (8 000 environ), usine et
utilisateur :

```json
{
 "7903": "Bongo Small _02",
 "8072": "Crazy in Love sample track"
}
```

Les noms viennent de l'index trié par nom de la sauvegarde ; ils sont complets
(les en-têtes `.had` les tronquent à 16 caractères). Dans l'exemple étudié, les
samples utilisateur ont les id 99 et 8040 à 8072. Un id vaut `dossier × 100 + numéro` :
8071 correspond à `WAV/DATA/080/71.wav` dans la mémoire de l'appareil.

## `wav/`

Les samples utilisateur, copiés tels quels depuis la sauvegarde, nommés
`Nom du sample.wav`. Les caractères interdits dans un nom de fichier
(`/ \ : * ? " < > |`) sont remplacés par `_`. Les samples d'usine ne sont pas
dans la sauvegarde.

Le même dossier sert à [ajouter des samples](ajouter-un-sample.md) : les fichiers
déjà présents dans la sauvegarde sont ignorés à l'import.
