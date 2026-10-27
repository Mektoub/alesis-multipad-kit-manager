# Editing a kit

**English** · [Français](../fr/editing-a-kit.md)

There are two ways to do it: the [web editor](web-editor.md), or the command line
described here, which goes through JSON files.

## 1. Make a backup on the device

On the Strike MultiPad: *Utility > Backup > Save All User Kits*, onto a USB stick
formatted as FAT32. The file appears in
`Strike/All User Kit And Sample Backup/BackupNNN.bkf`.

Copy this folder to the computer and **keep a copy of the original backup**.

## 2. Export

```bash
python3 -m strike_kits export "Strike/All User Kit And Sample Backup/Backup001.bkf" my_kits
```

The `my_kits/` folder contains one JSON file per kit, the sample catalog and the
WAVs of your samples (see [Export contents](export-contents.md)). The
`--no-wav` option skips copying the WAVs.

## 3. Edit the JSON files

Open `my_kits/kits/NNN_Name.json` in a text editor. Pads P1 to P9
are slots 1 to 9 of the `slots` list. A few examples:

```jsonc
// rename the kit and change the tempo
"name": "My Kit",
"tempo": 98.5,

// pad 5: MIDI note, LED color (9 = Cyan), sample referenced by name
{ "slot": 5,
  "params": { "midi_note": 41 },
  "light": { "play_color": 9 },
  "wave_a": { "sample": "Crazy in Love sample track" } }

// pad 9: start/stop the click, Aux+Phone output
{ "slot": 9, "params": { "control": 3, "audio_output": 4 } }

// two layers depending on how hard the pad is hit
"wave_a": { "sample": 7903, "velocity_low": 0,   "velocity_high": 100 },
"wave_b": { "sample": 7904, "velocity_low": 101, "velocity_high": 127 }
```

Just edit the existing values: there is no need to delete the other fields, and
those that do not change are written back unchanged. The meaning and range of
each field are described in [Parameters](parameters.md).

A sample is referenced by its id or by its exact name (see `samples.json`);
`null` removes the sample. To use a new WAV, see
[Adding a sample](adding-a-sample.md).

## 4. Produce a new backup

```bash
python3 -m strike_kits import "Strike/All User Kit And Sample Backup/Backup001.bkf" my_kits \
    -o "Strike/All User Kit And Sample Backup/Backup002.bkf"
```

- The tool starts from the original backup (which it refuses to overwrite), applies
  the JSON files and the new WAVs, then recomputes the checksums.
- Undecoded bytes are kept as they are: an export followed by an import with no
  changes gives back a byte-for-byte identical file.
- An out-of-range value, a sample that cannot be found or an unknown field stops
  the import with a message naming the file and slot concerned. Nothing is
  written in that case.

## 5. Load onto the device

Copy the new `.bkf` into `Strike/All User Kit And Sample Backup/` on the USB
stick, then load it from the device's *Utility > Backup* menu.

## Kits created on the device (`KITC`)

When a kit is saved on the device, it is written in a variant (`KITC`) where,
for pads 1 to 8, only the values are stored. All fields remain readable and
editable, as in empty kits (`KITH`). Details:
[kit format](bkf-format.md#specifics-of-the-kitc-variant).

## `.fac` backups

The `Strike/BackUp/…/STRIKE_BACKUP_KIT.fac` files contain the 100 kits, without
samples. They are exported and imported the same way, but samples cannot be
added to them.
