# `.bkf` format ("All User Kit And Sample Backup")

**English** · [Français](../fr/bkf-format.md)

File produced by *Utility > Backup > Save All User Kits* (firmware ≥ 1.3),
in `Strike/All User Kit And Sample Backup/BackupNNN.bkf`. It contains the user
kits, the user samples and the sample index lists.

This document describes what was observed by reverse-engineering a single real
file (`Backup001.bkf`, 39 MB, 141 files). Uncertain points are flagged.

Conventions: offsets in hexadecimal; **the container is little-endian**,
but **the files it contains (kits, lists, `.had`) are big-endian**.

## Overview

```
0x00  PACKBKF header (0x40 bytes)
0x40  File record 1: FILEH | PATH | NAME | DATA | data | padding
....  File record 2
....  ...
EOF   (the last FILEH points to the end of the file)
```

Paths are those of the device's internal memory, with `S:\` as the root.

## Header (0x00–0x40)

| Offset | Size | Observed value | Meaning |
|---|---|---|---|
| 0x00 | 8 | `PACKBKF ` | signature (with trailing space) |
| 0x08 | 4 | `0x38` | unknown (version?) |
| 0x0C | 3 | 0 | — |
| 0x0F | 1 | `0xAE` | **checksum**: `sum(octets[0x10:0x40]) & 0xFF` |
| 0x10 | 4 LE | 141 | number of files (verified) |
| 0x14 | 4 LE | 33 | number of `.wav` files (verified: goes to 34 after importing a sample) |
| 0x18 | 0x28 | 0 | — |

## File record

Each file occupies a record starting at an offset `p`:

| Relative offset | Size | Content |
|---|---|---|
| +0x000 | 8 | `FILEH\0\0\0` |
| +0x008 | 3 | 0 |
| +0x00B | 1 | **checksum**: `sum(octets[p+0x10 : p+0x180]) & 0xFF` |
| +0x00C | 4 | 0 |
| +0x010 | 4 LE | absolute offset of the next record (= file size for the last one) |
| +0x014 | 0x3C | 0 |
| +0x050 | 4 + 4 LE + 8 | `PATH`, length `0x80`, 8 null bytes |
| +0x060 | 0x80 | folder path, e.g. `S:\KIT\`, zero-terminated |
| +0x0E0 | 4 + 4 LE + 8 | `NAME`, length `0x80`, 8 null bytes |
| +0x0F0 | 0x80 | file name, e.g. `031.kit` |
| +0x170 | 4 + 4 LE + 8 | `DATA`, data size, 8 null bytes |
| +0x180 | size | raw file data |
| … | variable | null padding up to the next record |

The `FILEH` checksum only covers the metadata (from +0x10 to +0x180),
not the data. Kit integrity relies on the kits' own checksum
(see below).

The null padding after the data is **`32 − (size mod 16)`** bytes, from 17 to 32
(rule verified on the 284 records of two backups).

The record order is: kits, lists, `.had`, then `.wav`. Within each
group, samples appear in their creation order.

## Contained files

| Folder | Files | Content |
|---|---|---|
| `S:\KIT\` | `031.kit` … `100.kit` | the 70 user kits, 0x2660 bytes each ([format](#kit-format-kit)) |
| `S:\WAV\LIST\` | `Wave_list.lst`, `wave_list_sort_num.lst`, `wave_list_sort_name.lst`, `wave_list_sort_group.lst`, `WaveList_User_SortSize.lst` | sample indexes (factory and user) |
| `S:\WAV\HEAD\NNN\` | `MM.had` | header of each user sample (224 bytes) |
| `S:\WAV\DATA\NNN\` | `MM.wav` | user sample (16-bit PCM WAV, 44.1 kHz) |

### Sample id

A sample is identified by an integer `id = NNN × 100 + MM`, where `NNN` is the folder
and `MM` the file number. Example: `8071` corresponds to `WAV/DATA/080/71.wav`.
Factory samples have ids below 8000 and are not included in the
backup, except in the index lists. `0xFFFF` means "no sample".

### `.had` (sample header, 0xE0 bytes, big-endian)

| Offset | Size | Content |
|---|---|---|
| 0x00 | 4 | `INTH` |
| 0x04 | 2 | `0x0010` |
| 0x08 | 1 | **checksum**: `sum(had[0x0A:]) & 0xFF` (same rule as kits, verified) |
| 0x14 | 1 | bits per sample (`0x10` = 16) |
| 0x15 | 1 | number of channels (1 or 2) |
| 0x16 | 2 | sample rate (`0xAC44` = 44,100 Hz) |
| 0x18 | 4 | offset of the audio data in the `.wav` (after the `data` chunk) |
| 0x1C | 4 | same (start point?) |
| 0x20 | 4 | audio data size (size of the `data` chunk) |
| 0x28 | 4 | audio data offset |
| 0x2C | 4 | end offset = offset + size (= size of the `.wav` if `data` is the last chunk) |
| 0x30 | 4 | audio data offset |
| 0x34 | 4 | end offset |
| 0x3F | 1 | length of the full name |
| 0x40 | 16 | sample name, truncated to 16 characters |
| 0x58 | 4 + 4 | `PATH`, path length |
| 0x60 | 0x80 | relative path, e.g. `\080\71.wav` |

The 3 (start, end) pairs probably correspond to the whole sample, the played
region (*Edit Start/End*) and the loop. In some `.had` files, the unused
bytes contain leftover audio data instead of zeros.

### `.lst` lists

All have a 0x20-byte header:

| Offset | Content |
|---|---|
| 0x00 | `WLTH` (`Wave_list.lst`) or `SLTH` (others) |
| 0x04 | `0x0020` (header size) |
| 0x08 | 1 byte that varies from one file to another. **It is not a checksum**: it does not change when the device adds a sample |
| 0x0A | u16, number of entries: 8,072 samples, 85 groups, or 33 user samples |

Samples have **dense ids from 0 to 8,071**: the id is the index in
`Wave_list.lst`. For all observed samples, `id = folder × 100 + file`.

- **`Wave_list.lst`** (fixed size 0x20000): table indexed by id, 8-byte
  entries.
  - +0: u16, id (bit `0x8000` = free entry);
  - +2: u16, location `folder << 8 | file` (e.g. `0x5047` = `080/71`);
  - +4: u16, library? (0, 1, 2, 30, 31, 32; 0 for user samples);
  - +6: u16, **rank of the sample in `sort_num`**.

  Entries beyond 8,071 are free (`0x8000 | index`). Their location
  is already filled in (e.g. `0x5048` = `080/72` for id 8072).
- **`wave_list_sort_num.lst`**: 8,072 (u16 rank, u16 id) pairs sorted by rank,
  followed by a null pair. A recent user sample is appended at the end of the list.
- **`wave_list_sort_name.lst`**: 8,072 entries of 0x90 bytes sorted by name
  (nearly alphabetical, case-insensitive; a few punctuation exceptions).
  - +0x00: u16, position counter. On insertion, the entry receives its position
    and **all following entries are incremented by 1**. The factory
    values (position modulo 256) are a legacy of this mechanism. The low
    byte always equals the position modulo 256; the high byte
    contains the rest of the position for a recently added sample (1832 for
    "Crazy in Love"), but 0 for a sample added in 2016 ("WIMH sample
    track", 102 at position 7782). The tool writes the full position.
  - +0x02: u16, **sample id**;
  - +0x04: u16, length of the original name (name of the imported file, including `.wav`);
  - +0x10: **full name**, 0x80 bytes. The device appends `_id` to duplicate names.

  This is the source of the `samples.json` catalog.
- **`wave_list_sort_group.lst`**: 85 groups (categories), one after another:
  - +0: u8, group number;
  - +1: u16, number of members;
  - +3: u8, 0;
  - +4: u32, name length;
  - +8: name, 16 bytes;
  - +0x18: members (u16 rank, u16 id).

  Groups 0 to 41 are the factory categories (*Kicks Acous*, *Loops DnB*…),
  42 to 83 the same categories on the user side (empty here), and 84 **New Sample**
  holds the 33 imported samples.
- **`WaveList_User_SortSize.lst`** (fixed size 0x4000): 33 pairs
  (u32 id, u32 size of the `.wav`) of the user samples, sorted by increasing
  size (for equal sizes, decreasing id).

### Adding a sample (observed on the device)

Rules deduced from two backups made before and after importing a single WAV
on the device. The tool applies them and reproduces the device's backup
byte for byte (test `test_ajout_reproduit_l_appareil`). With `id` = current
number of samples (8,072 in the example):

1. The `.wav` is copied **as is** to `S:\WAV\DATA\080\72.wav`, after the other `.wav` files.
2. A `.had` is created in `S:\WAV\HEAD\080\72.had`, after the other `.had` files.
3. `Wave_list.lst`: number of entries + 1; entry `id` loses the `0x8000` flag.
4. `sort_num`: the pair (rank = `id`, `id`) is added before the final null pair.
5. `sort_name`: the entry is inserted at its alphabetical position (case-insensitive).
   Its +0x04 field equals the name length + 4 (`.wav`).
6. `sort_group`: (n, `id`) is appended to the *New Sample* group, whose number
   of members becomes n + 1.
7. `SortSize`: (`id`, size of the `.wav`) is inserted by increasing size, before
   entries of the same size.
8. The `.bkf` header is updated: number of files + 2, number of `.wav` + 1,
   checksums.

Byte 0x08 of the lists does not change.

### Renaming a sample (not observed)

No device backups made before and after a rename have been compared. The tool
(`Bkf.rename_sample`) applies the rules of adding:

1. `sort_name`: the entry is removed (counter of the following entries − 1), then
   inserted again at its new alphabetical place (counter of the following ones + 1),
   with the new name at +0x10. The +0x04 field (length of the original name) is kept.
2. `.had`: name length at 0x3F, name truncated to 16 characters at 0x40, checksum.

The other lists and the `.wav` do not change. Renaming then restoring the old name
gives back an identical backup.

## Kit format (`.kit`)

Shared by the `.bkf` and [`.fac`](fac-format.md) formats. Fixed size of
**0x2660 bytes (9,824)**, big-endian.

### Variants

| Signature | Field at +0x04 | Observed in |
|---|---|---|
| `KITH` | `0x0260` | factory kits and empty kits |
| `KITC` | `0x0020` | kits created or edited on the device (e.g. 031 "WhereIs", 001, 002 of the `.fac`) |

### Header (0x000–0x260)

| Offset | Size | Content |
|---|---|---|
| 0x00 | 4 | `KITH` or `KITC` |
| 0x04 | 2 | `0x0260` (KITH) or `0x0020` (KITC) |
| 0x06 | 2 | `0x0000` or `0xFFFF` (unknown) |
| 0x08 | 1 | **checksum**: `sum(kit[0x0A:]) & 0xFF` (verified on 33 distinct kits) |
| 0x09 | 1 | `0x00` (KITH); `0x2B` (KITC) |
| 0x0A | 2 | `0x0018` / `0x1318` (KITH), other in KITC (unknown) |
| 0x0C | 1 | **kit volume** (0–100); in KITH followed by min (0x0D) and max (0x0E) |
| 0x10 | 2 | **tempo × 10** (e.g. 1200 = 120 BPM); in KITH followed by min `0x012C` (30) and max `0x0AF0` (280) |
| 0x50–0x1A0 | — | probably the kit effects (FX1–3): repeated blocks of values, not decoded |
| 0xC0 | 16 | **kit name** (ASCII, zero-terminated) |

The rest of the header is not decoded. It probably holds the time
signature and the logo settings (color, mode, beat).

### Slots (pads and triggers)

There are **24 slots** of 0x180 bytes, at `0x260 + i × 0x180` (`i` = 0…23).
Each one starts with `KITI` `0x0180`.

Based on the MIDI notes of the factory kits:

| Slots | Factory MIDI notes | Role |
|---|---|---|
| 1–9 | 36–46 | pads P1–P9 (certain) |
| 10–17 | 39–51 | external triggers: **15 = Trigger In 4/5, 16 = Trigger In 1, 17 = Trigger In HH** (verified); Trigger In 2/3 not located yet |
| 18–21 | 53–57, 124–127 | pedals: **18 = FootSwitch 1/2, 20 = FootSwitch 3/4** (verified); 19 and 21 unknown (second contact of dual inputs?) |
| 22–24 | 60–63 | unknown |

Structure of a slot (relative offsets):

| Offset | Size | Content |
|---|---|---|
| +0x00 | 4 | `KITI` |
| +0x04 | 2 | `0x0180` (block size) |
| +0x0C | 2 | `0x0001` |
| +0x10 | 1 | Play color (0 = Red … 16 = White, manual order) |
| +0x11 | 1 | Play mode (0–6) |
| +0x12 | 1 | Play Beat: 0 = 1/2, 1 = 1/4, 2 = 1/8, 3 = 1/16 (verified: 3 = 1/16) |
| +0x14 | 1 | Stop color |
| +0x15 | 1 | Stop mode |
| +0x16 | 1 | Stop Beat, same values (verified: 0 = 1/2) |
| +0x18 | 1 | unknown (0–6) |
| +0x19 | 1 | Sync Mode: Mute, Cycle, Random, Together, HiHat (verified: 4 = HiHat) |
| +0x28–0x80 | 4 × n | **pad parameters** (records, see below) |
| +0x80–0xE0 | 0x60 | **wave A** |
| +0xE0–0x140 | 0x60 | **wave B** |
| +0x140–0x180 | 0x40 | zeros |

A wave consists of:

| Offset | Size | Content |
|---|---|---|
| +0x00 | 2 | **sample id** (`0xFFFF` = none) |
| +0x02 | 1 | **Velocity Low** (0 by default) |
| +0x03 | 1 | **Velocity High** (127 by default) |
| +0x04 | 4 | zeros |
| +0x08–0x60 | 4 × n | wave parameters (records) |

### Parameter records

Each parameter takes 4 bytes: `id`, `value`, `min`, `max`. The sequence
ends with a record whose `id` is `0xFF` (padding `ff 00 00 00`).
The ranges are therefore self-describing. Exception: some observed values
exceed `max`, for example `0x28` for a 0–16 range on `0x0E`, `0x16` and
`0x17`. These may be special values.

Pad parameters (+0x28 area):

| id | Range | Probable meaning |
|---|---|---|
| 0x00 | 0–100 | volume |
| 0x02 | 0–31 | pan (15 = center) |
| 0x08 | 0–127 | MIDI note (confirmed: 36, 37, 38… on P1, P2, P3…) |
| 0x09 | 0–4 | ? (Sync Mode is at +0x19) |
| 0x0C | 0–16 | Sync Group |
| 0x0E | 0–16 | ? (17 values: a color?) |
| 0x0F | 0–5 | **Audio Output**: 0 = Main+Phone, 1–3 = FX1–3, 4 = Aux+Phone (verified), 5 = Phone Only |
| 0x10 | 0–127 | Fixed Level (0 = Off) |
| 0x11 | 1–32 | Sensitivity |
| 0x12 | 0–32 | Threshold (default 4, as in the manual) |
| 0x13 | 0–7 | **Curve**: Normal, Exp1, Exp2, Log1, Log2, Loud (verified: 5 = Loud) |
| 0x14 | 0–13 | **Control** (verified: 3 = Click On/Off). Probable order from the manual: Off, Next Kit, Previous Kit, Click On/Off, Tap Tempo, Panic, Looper Rec, Looper Play/Stop, Kit FX1–3, MST FX; 14 possible values, i.e. 2 more than in the v1.2 manual |
| 0x15 | 0–1 | **Sound**: 0 = On (default, verified), 1 = Off |
| 0x16 | 0–127 | **Kit FX Level** (verified; 40 by default) |
| 0x17 | 0–16 | ? |

Wave parameters (+0x08 area):

| id | Range | Probable meaning |
|---|---|---|
| 0x00 | 0–100 | volume |
| 0x02 | 0–32 | pan |
| 0x09 | 0–5 | **Playback Mode**: Oneshot, Alter, Loop, RoundRobin, Hi-hat, then FS1–FS4; FS4 is 9 (verified), beyond the declared max |
| 0x10 | 0–127 | ? (velocity?) |
| 0x18 | 0–255 | ? |
| 0x19 | 0–1 | **Poly/Mono**: 0 = Mono (verified), 1 = Poly |
| 0x1A | 0–100 | Fade In |
| 0x1B | 0–100 | Fade Out |
| 0x1C | 0–2 | Priority (Low/Medium/High) |

### Specifics of the `KITC` variant

`KITC` is **the format the device writes when a kit is saved**. Kit 032
"CrazyInLove", created on the device, went from `KITH` to `KITC`.

Slots 9 to 24 (from 0xE60) have a normal `KITI` structure.
In the first 8 (0x260–0xE60), **the offsets are the same as in `KITH`**,
but:

- the `KITI` signature and the `id`, `min` and `max` bytes of the records are
  replaced by `0xFF` (sometimes `0x00`), only the **value** staying in place.
  Example: `ff 5a ff ff` for a volume of 90, `ff 29 ff ff` for MIDI note 41
  of pad 5;
- the wave headers remain intact: sample id and velocities (e.g. `1f 88 00 7f`
  for sample 8072, velocity 0–127, on pad 5);
- 0x30-byte structures (`80 00 … 00 20 "Empty"`), spaced 0xB0 bytes apart
  starting at 0xD0, overwrite the `id`, `min` and `max` bytes of some
  records. **The value byte, however, stays in place**: the `"Empty"` string
  then appears with its 2nd byte replaced by the value. Example: `45 28 70 74`
  (`"E(pt"`) gives MIDI note 40 of pad 4. The overwritten positions are the
  same in all observed `KITC` kits.

In these 8 slots, the tool therefore always reads the value byte, whatever the
neighboring bytes, and only rewrites that byte (or the 2 bytes of the sample id). A
wave header is read if `low ≤ high ≤ 127`.

## How to go further

To identify an unknown parameter:

1. make a backup;
2. change a single setting on the device;
3. make another backup;
4. export both with `python3 -m strike_kits export` and compare with `diff -r`.
