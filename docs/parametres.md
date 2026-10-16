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

| Clé | Sens | Plage |
|---|---|---|
| `volume` | volume | 0–100 |
| `pan` | panoramique : 0 = L15, **15 = centre**, 30 = R15 | 0–31 |
| `midi_note` | MIDI Note Output (vérifié : 36, 37, 38… sur P1, P2, P3…) | 0–127 |
| `sensitivity` | Sensitivity | 1–32 |
| `threshold` | Threshold (4 par défaut) | 0–32 |
| `fixed_level` | Fixed Level, 0 = Off | 0–127 |
| `sync_group` | Sync Group, 0 = Off | 0–16 |
| `control` | Control (voir ci-dessous) | 0–13 |
| `audio_output` | Audio Output (voir ci-dessous) | 0–5 |
| `sound` | Sound On/Off (sens des valeurs à confirmer) | 0–1 |

**`control`** : 0 = Off, 1 = Next Kit, 2 = Previous Kit, **3 = Click On/Off (vérifié)**,
4 = Tap Tempo, 5 = Panic, 6 = Looper Rec, 7 = Looper Play/Stop, 8–10 = Kit FX1–3 On/Off,
11 = MST FX On/Off. Les valeurs 12 et 13 n'apparaissent pas dans le manuel v1.2.

**`audio_output`** : 0 = Main+Phone, 1 = FX1, 2 = FX2, 3 = FX3, **4 = Aux+Phone (vérifié)**,
5 = Phone Only.

## Éclairage (`light`)

| Clé | Sens | Plage |
|---|---|---|
| `play_color`, `stop_color` | couleur de la LED quand le pad joue / au repos | 0–16 |
| `play_mode` | Off, Trigger, Audio Meter, Audio Breath, Fill, BPM Pulse, BPM Pong | 0–6 |
| `stop_mode` | Off, Solid Dim, Solid Medium, Solid Bright, BPM Pulse, BPM Pong | 0–6 |

Couleurs, dans l'ordre du manuel : 0 Red, 1 Coral, 2 Deep Pink, 3 Light Pink,
4 Magenta, 5 Purple, 6 Plum, 7 Blue, 8 Sky Blue, 9 Cyan, 10 Aquamarine, 11 Lime,
12 Green, 13 Yellow, 14 Orange, 15 Orange Red, 16 White.

## Wave (`wave_a`, `wave_b`)

| Clé | Sens | Plage |
|---|---|---|
| `sample` | id du sample, ou `null` | — |
| `velocity_low`, `velocity_high` | plage de vélocité qui déclenche la couche (vérifié : 0 et 127 par défaut) | 0–126, 1–127 |
| `params.volume` | volume de la couche | 0–100 |
| `params.pan` | panoramique, 15 = centre | 0–32 |
| `params.fade_in`, `params.fade_out` | fondus, 0 = Off | 0–100 |
| `params.priority` | Low / Medium / High | 0–2 |

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
| pad | `p09` | 0–4 | 5 valeurs : Sync Mode ? |
| pad | `p0e` | 0–16 | 17 valeurs : une couleur ? |
| pad | `p13` | 0–7 | ? |
| pad | `p16` | 0–127 | Kit FX Level ? |
| pad | `p17` | 0–16 | ? |
| wave | `p09` | 0–5 | Playback Mode ? |
| wave | `p10` | 0–127 | ? |
| wave | `p18` | 0–255 | ? |
| wave | `p19` | 0–1 | Poly/Mono ? |

Restent aussi à localiser : Curve, la signature rythmique du kit, les réglages du
logo et les effets (FX1–3).

## Identifier un paramètre

1. Faire une sauvegarde sur l'appareil.
2. Changer **un seul** réglage.
3. Refaire une sauvegarde.
4. Exporter les deux et comparer :

```bash
python3 strike_kits.py export --no-wav Backup_avant.bkf avant
python3 strike_kits.py export --no-wav Backup_apres.bkf apres
diff -r avant/kits apres/kits
```

C'est ainsi qu'ont été identifiés `control`, `audio_output` et le comportement de
l'ajout de samples. Une fois le paramètre identifié, il suffit de le nommer dans
`PAD_PARAMS` ou `WAVE_PARAMS` (`strike_kits.py`), avec un test qui s'appuie sur
la sauvegarde de référence. Pour l'éditeur web, on peut aussi lui donner des
libellés dans `editor/meta.py`.
