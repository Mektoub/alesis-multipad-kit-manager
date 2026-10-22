# Paramètres identifiés

Noms des champs des [JSON de kit](contenu-export.md) et sens connu à ce jour.
« Vérifié » signifie confirmé par une sauvegarde faite sur l'appareil ; les autres
libellés suivent l'ordre du manuel ou la plage observée.

## Kit

| Clé | Sens | Plage |
|---|---|---|
| `name` | nom du kit | 16 caractères |
| `level` | Kit Level | 0–100 |
| `tempo` | Kit Tempo, en BPM (vérifié : 99,0 et 116,0) | 30–280 |

## Pad (`params` d'un emplacement)

Rangés par sections, comme dans le menu Pad de l'appareil et dans l'éditeur.

| Section | Clé | Sens | Plage |
|---|---|---|---|
| Feel | `sensitivity` | Sensitivity | 1–32 |
| Feel | `curve` | Curve (vérifié : 5 = Loud) : Normal, Exp1, Exp2, Log1, Log2, Loud | 0–7 |
| Feel | `threshold` | Threshold (4 par défaut) | 0–32 |
| Feel | `fixed_level` | Fixed Level, 0 = Off | 0–127 |
| Control | `control` | Mode (voir ci-dessous) | 0–13 |
| Control | `sound` | Sound On/Off (sens des valeurs à confirmer) | 0–1 |
| Output | `audio_output` | Audio Output (voir ci-dessous) | 0–5 |
| Output | `kit_fx_level` | Kit FX Level (vérifié ; 40 par défaut) | 0–127 |
| Output | `midi_note` | MIDI Note Output (vérifié : 36, 37, 38… sur P1, P2, P3…) | 0–127 |
| Output | `volume` | volume | 0–100 |
| Output | `pan` | panoramique : 0 = L15, **15 = centre**, 30 = R15 | 0–31 |
| Group | `sync_group` | Sync Group, 0 = Off | 0–16 |
| Group | `sync_mode` | Sync Mode (vérifié : 4 = HiHat) : Mute, Cycle, Random, Together, HiHat | 0–4 |

`sync_mode` n'est pas un enregistrement mais un octet à offset fixe de
l'emplacement (+0x19), comme l'éclairage ; il est rangé dans `params` avec le
reste de la section Group.

**`control`** (libellé *Mode* sur l'appareil) : 0 = Off, 1 = Next Kit, 2 = Previous Kit, **3 = Click On/Off (vérifié)**,
4 = Tap Tempo, 5 = Panic, 6 = Looper Rec, 7 = Looper Play/Stop, 8–10 = Kit FX1–3 On/Off,
11 = MST FX On/Off. Les valeurs 12 et 13 n'apparaissent pas dans le manuel v1.2.

**`audio_output`** : 0 = Main+Phone, 1 = FX1, 2 = FX2, 3 = FX3, **4 = Aux+Phone (vérifié)**,
5 = Phone Only.

## Éclairage (`light`, section Light)

| Clé | Sens | Plage |
|---|---|---|
| `play_color`, `stop_color` | couleur de la LED quand le pad joue / au repos | 0–16 |
| `play_mode` | Off, Trigger, Audio Meter, Audio Breath, Fill, BPM Pulse, BPM Pong | 0–6 |
| `stop_mode` | Off, Solid Dim, Solid Medium, Solid Bright, BPM Pulse, BPM Pong | 0–6 |
| `play_beat`, `stop_beat` | Play Beat / Stop Beat (vérifié : 0 = 1/2, 3 = 1/16) : 1/2, 1/4, 1/8, 1/16 | 0–3 |

Couleurs, dans l'ordre du manuel : 0 Red, 1 Coral, 2 Deep Pink, 3 Light Pink,
4 Magenta, 5 Purple, 6 Plum, 7 Blue, 8 Sky Blue, 9 Cyan, 10 Aquamarine, 11 Lime,
12 Green, 13 Yellow, 14 Orange, 15 Orange Red, 16 White.

## Wave (`wave_a`, `wave_b`)

| Section | Clé | Sens | Plage |
|---|---|---|---|
| — | `sample` | id du sample, ou `null` | — |
| Mode | `params.playback_mode` | Playback Mode (voir ci-dessous) | 0–9 |
| Mode | `params.poly_mono` | Poly/Mono (vérifié : 0 = Mono, 1 = Poly) | 0–1 |
| Mix | `params.volume` | volume de la couche | 0–100 |
| Mix | `params.pan` | panoramique, 15 = centre | 0–32 |
| Mix | `params.fade_in`, `params.fade_out` | fondus, 0 = Off | 0–100 |
| Mix | `velocity_high`, `velocity_low` | plage de vélocité qui déclenche la couche (vérifié : 127 et 0 par défaut) | 1–127, 0–126 |
| Mix | `params.priority` | Low / Medium / High | 0–2 |

**`playback_mode`** : 0 = Oneshot, 1 = Alter, 2 = Loop, 3 = RoundRobin, 4 = Hi-hat,
6–8 = FS1–FS3 (supposés), **9 = FS4 (vérifié)**. L'enregistrement annonce une
plage 0–5, mais l'appareil écrit 9 pour FS4 : l'éditeur accepte 0–9. La valeur 5
reste inconnue (la liste de l'appareil n'a que 9 choix). Régler FS1 sur un pad
dirait si FS1 vaut 5 ou 6.

Le menu Mode de l'appareil a aussi *Start Click* (sous conditions), pas encore
localisé.

Les kits d'usine utilisent les vélocités pour superposer des couches (wave A
0–100, wave B 101–127) ou découper finement des multisamples (0–30, 31–35…).

## Emplacements

| Emplacements | Rôle |
|---|---|
| 1–9 | pads P1–P9 (certain) |
| 10–17 | déclencheurs externes, probablement T1–T5, HH… |
| 18–21 | probablement les pédales FS1–FS4 |
| 22–24 | inconnu |

## Paramètres non identifiés

| Où | Clé | Plage | Indice |
|---|---|---|---|
| pad | `p09` | 0–4 | ? (2 sur certains pads des kits d'usine) |
| pad | `p0e` | 0–16 | 17 valeurs : une couleur ? |
| pad | `p17` | 0–16 | ? |
| wave | `p10` | 0–127 | ? |
| wave | `p18` | 0–255 | ? Start Click ? |

Restent aussi à localiser : Start Click, la signature rythmique du kit, les
réglages du logo et les effets (FX1–3).

## Identifier un paramètre

1. Faire une sauvegarde sur l'appareil.
2. Changer **un seul** réglage.
3. Refaire une sauvegarde.
4. Exporter les deux et comparer :

```bash
python3 -m strike_kits export --no-wav Backup_avant.bkf avant
python3 -m strike_kits export --no-wav Backup_apres.bkf apres
diff -r avant/kits apres/kits
```

C'est ainsi qu'ont été identifiés `control`, `audio_output`, le comportement de
l'ajout de samples, puis `curve`, `kit_fx_level`, `sync_mode`, les beats de
l'éclairage, `playback_mode` et `poly_mono` (neuf réglages sur deux kits, une seule
paire de sauvegardes : chaque réglage sur un pad différent). Une fois le paramètre identifié, il suffit de le nommer dans
`PAD_PARAMS` ou `WAVE_PARAMS` (`strike_kits/__init__.py`), ou dans `LIGHT_FIELDS` /
`PAD_FIELDS` pour un octet à offset fixe de l'emplacement, avec un test qui s'appuie sur
la sauvegarde de référence. Pour l'éditeur web, on lui donne ensuite des
libellés et une place dans les sections (`PAD_SECTIONS`, `WAVE_SECTIONS`) dans
`editor/meta.py`.
