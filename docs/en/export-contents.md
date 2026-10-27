# Export contents

**English** · [Français](../fr/export-contents.md)

`python3 -m strike_kits export BACKUP FOLDER` produces:

```
FOLDER/
├── kits/
│   ├── 031_WhereIs.json
│   ├── 032_CrazyInLove.json
│   └── …                       one file per kit
├── samples.json                id → name catalog of all samples
└── wav/                        user samples (absent with --no-wav or for a .fac)
    ├── Crazy in Love sample track.wav
    └── …
```

## `kits/NNN_Name.json`

`NNN` is the kit number and serves as the key on import. The part after `_` is
free: the file can be renamed.

```jsonc
{
  "format": "KITH",            // KITH (empty or factory kit) or KITC (saved on the device)
  "name": "My Kit",            // 16 characters max
  "level": 90,                 // kit volume, 0–100
  "tempo": 120.0,              // 30–280 BPM, to one decimal place
  "slots": [                   // 24 slots: 1–9 = pads P1–P9
    {
      "slot": 1,
      "_label": "P1",
      "light":  { "play_color": 16, "play_mode": 3, "play_beat": 1, "stop_color": 8, "…": 0 },
      "params": { "volume": 90, "pan": 15, "midi_note": 36, "curve": 0, "p09": 0, "…": 0 },
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

- The meaning of each field is described in [Parameters](parameters.md).
- Keys starting with `_` are informative and ignored on import.
- `sample` is a sample id or `null` (no sample). On import, it also accepts
  the exact name of a sample, including those added from `wav/`.
- The `pXX` parameters (hexadecimal id) are not identified yet; they can
  still be edited.
- Each parameter has a min/max range stored in the kit. A value changed out of
  range is rejected on import.

## `samples.json`

Catalog of all samples known to the device (about 8,000), factory and
user:

```json
{
 "7903": "Bongo Small _02",
 "8072": "Crazy in Love sample track"
}
```

The names come from the backup's name-sorted index; they are complete
(the `.had` headers truncate them to 16 characters). In the studied example, the
user samples have ids 99 and 8040 to 8072. An id is `folder × 100 + number`:
8071 corresponds to `WAV/DATA/080/71.wav` in the device's memory.

## `wav/`

The user samples, copied as is from the backup, named
`Sample name.wav`. Characters forbidden in a file name
(`/ \ : * ? " < > |`) are replaced with `_`. Factory samples are not
in the backup.

The same folder is used to [add samples](adding-a-sample.md): files
already present in the backup are ignored on import.
