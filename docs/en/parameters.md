# Identified parameters

**English** · [Français](../fr/parameters.md)

Field names in the [kit JSON files](export-contents.md) and their meaning as known
so far. “Verified” means confirmed by a backup made on the device; the other
labels follow the manual's order or the observed range.

## Kit

| Key | Meaning | Range |
|---|---|---|
| `name` | kit name | 16 characters |
| `level` | Kit Level | 0–100 |
| `tempo` | Kit Tempo, in BPM (verified: 99.0 and 116.0) | 30–280 |

## Pad (a slot's `params`)

Grouped by section, as in the device's Pad menu and in the editor.

| Section | Key | Meaning | Range |
|---|---|---|---|
| Feel | `sensitivity` | Sensitivity | 1–32 |
| Feel | `curve` | Curve (verified: 5 = Loud): Normal, Exp1, Exp2, Log1, Log2, Loud | 0–7 |
| Feel | `threshold` | Threshold (4 by default) | 0–32 |
| Feel | `fixed_level` | Fixed Level, 0 = Off | 0–127 |
| Control | `control` | Mode (see below) | 0–13 |
| Control | `sound` | Sound: 0 = On (default, verified), 1 = Off | 0–1 |
| Output | `audio_output` | Audio Output (see below) | 0–5 |
| Output | `kit_fx_level` | Kit FX Level (verified; 40 by default) | 0–127 |
| Output | `midi_note` | MIDI Note Output (verified: 36, 37, 38… on P1, P2, P3…) | 0–127 |
| Output | `volume` | volume | 0–100 |
| Output | `pan` | pan: 0 = L15, **15 = center**, 30 = R15 | 0–31 |
| Group | `sync_group` | Sync Group, 0 = Off | 0–16 |
| Group | `sync_mode` | Sync Mode (verified: 4 = HiHat): Mute, Cycle, Random, Together, HiHat | 0–4 |

`sync_mode` is not a record but a byte at a fixed offset in the slot (+0x19),
like the lighting; it is stored in `params` with the rest of the Group section.

**`control`** (labeled *Mode* on the device): 0 = Off, 1 = Next Kit, 2 = Previous Kit, **3 = Click On/Off (verified)**,
4 = Tap Tempo, 5 = Panic, 6 = Looper Rec, 7 = Looper Play/Stop, 8–10 = Kit FX1–3 On/Off,
11 = MST FX On/Off. Values 12 and 13 do not appear in the v1.2 manual.

**`audio_output`**: 0 = Main+Phone, 1 = FX1, 2 = FX2, 3 = FX3, **4 = Aux+Phone (verified)**,
5 = Phone Only.

## Lighting (`light`, Light section)

| Key | Meaning | Range |
|---|---|---|
| `play_color`, `stop_color` | LED color when the pad is playing / idle | 0–16 |
| `play_mode` | Off, Trigger, Audio Meter, Audio Breath, Fill, BPM Pulse, BPM Pong | 0–6 |
| `stop_mode` | Off, Solid Dim, Solid Medium, Solid Bright, BPM Pulse, BPM Pong | 0–6 |
| `play_beat`, `stop_beat` | Play Beat / Stop Beat (verified: 0 = 1/2, 3 = 1/16): 1/2, 1/4, 1/8, 1/16 | 0–3 |

Colors, in the manual's order: 0 Red, 1 Coral, 2 Deep Pink, 3 Light Pink,
4 Magenta, 5 Purple, 6 Plum, 7 Blue, 8 Sky Blue, 9 Cyan, 10 Aquamarine, 11 Lime,
12 Green, 13 Yellow, 14 Orange, 15 Orange Red, 16 White.

## Wave (`wave_a`, `wave_b`)

| Section | Key | Meaning | Range |
|---|---|---|---|
| — | `sample` | sample id, or `null` | — |
| Mode | `params.playback_mode` | Playback Mode (see below) | 0–9 |
| Mode | `params.poly_mono` | Poly/Mono (verified: 0 = Mono, 1 = Poly) | 0–1 |
| Mix | `params.volume` | layer volume | 0–100 |
| Mix | `params.pan` | pan, 15 = center | 0–32 |
| Mix | `params.fade_in`, `params.fade_out` | fades, 0 = Off | 0–100 |
| Mix | `velocity_high`, `velocity_low` | velocity range that triggers the layer (verified: 127 and 0 by default) | 1–127, 0–126 |
| Mix | `params.priority` | Low / Medium / High | 0–2 |

**`playback_mode`**: 0 = Oneshot, 1 = Alter, 2 = Loop, 3 = RoundRobin, 4 = Hi-hat,
6–8 = FS1–FS3 (assumed), **9 = FS4 (verified)**. The record declares a 0–5
range, but the device writes 9 for FS4: the editor accepts 0–9. Value 5 is
still unknown (the device's list has only 9 choices). Setting FS1 on a pad
would tell whether FS1 is 5 or 6.

The device's Mode menu also has *Start Click* (under some conditions), not yet
located.

Factory kits use velocities to stack layers (wave A 0–100, wave B 101–127) or to
finely split multisamples (0–30, 31–35…).

## Slots

| Slots | Role |
|---|---|
| 1–9 | pads P1–P9 (certain) |
| 10–17 | external triggers: **15 = Trigger In 4/5, 16 = Trigger In 1, 17 = Trigger In HH** (verified); Trigger In 2/3 not yet located |
| 18–21 | pedals: **18 = FootSwitch 1/2, 20 = FootSwitch 3/4** (verified); 19 and 21 unknown (second contact of the dual inputs?) |
| 22–24 | unknown |

## Unidentified parameters

| Where | Key | Range | Clue |
|---|---|---|---|
| pad | `p09` | 0–4 | ? (2 on some pads of the factory kits) |
| pad | `p0e` | 0–16 | 17 values: a color? |
| pad | `p17` | 0–16 | ? |
| wave | `p10` | 0–127 | ? |
| wave | `p18` | 0–255 | ? Start Click? |

Still to be located as well: Start Click, the kit's time signature, the logo
settings and the effects (FX1–3).

## Identifying a parameter

1. Make a backup on the device.
2. Change **a single** setting.
3. Make another backup.
4. Export both and compare:

```bash
python3 -m strike_kits export --no-wav Backup_avant.bkf avant
python3 -m strike_kits export --no-wav Backup_apres.bkf apres
diff -r avant/kits apres/kits
```

This is how `control`, `audio_output` and the behavior of adding samples were
identified, then `curve`, `kit_fx_level`, `sync_mode`, the lighting beats,
`playback_mode` and `poly_mono` (nine settings on two kits, a single pair of
backups: each setting on a different pad). Once the parameter is identified, all
it takes is naming it in `PAD_PARAMS` or `WAVE_PARAMS` (`strike_kits/__init__.py`),
or in `LIGHT_FIELDS` / `PAD_FIELDS` for a byte at a fixed offset in the slot, with
a test based on the reference backup. For the web editor, it is then given
labels and a place in the sections (`PAD_SECTIONS`, `WAVE_SECTIONS`) in
`editor/meta.py`.
