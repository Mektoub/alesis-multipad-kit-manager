# `.fac` format (kit backup)

**English** · [Français](../fr/fac-format.md)

File `Strike/BackUp/BACKUPNNNNN/STRIKE_BACKUP_KIT.fac`, produced by the device's
*Utility > Backup* menu. It contains **only the kits** (no
samples): 100 kits `001` to `100` in the studied example (992,288 bytes).

This document describes what was observed by reverse-engineering a single real
file. Everything is **big-endian**.

## Overview

The file mimics a small file system: a root header, a `KIT`
directory, a table of file entries, then the data laid end to end.

```
0x000  SDRH   root header               (0x40)
0x040  SDCH   root contents             (0x40): 1 directory
0x080  DIRH   "KIT" directory           (0x60) → contents at 0x0E0
0x0E0  SDCH   KIT contents              (0x40): 100 files
0x120  FIEH   × 100                     (0x60 each)
0x26A0 data of the 100 kits, contiguous (0x2660 each)
```

`SDRH` might stand for "SD Root Header"; this is only a guess.

## Headers

### `SDRH` (0x00)

| Offset | Size | Value | Meaning |
|---|---|---|---|
| 0x00 | 4 | `SDRH` | signature |
| 0x04 | 2 | `0x0040` | header size |
| 0x08 | 1 | `0xB0` | unknown (version, flags?) |
| rest | — | 0 | — |

### `SDCH` (0x40 and 0xE0)

Directory contents header, 0x40 bytes.

| Offset | Size | Root (0x40) | `KIT` (0xE0) | Probable meaning |
|---|---|---|---|---|
| 0x04 | 2 | `0x0040` | `0x0040` | header size |
| 0x0A | 2 | 1 | 0 | number of subdirectories |
| 0x0C | 2 | 0 | 100 | number of files |

### `DIRH` (0x80) and `FIEH` (from 0x120)

Both entry types have the same layout, over 0x60 bytes:

| Offset | Size | `DIRH` | `FIEH` |
|---|---|---|---|
| 0x00 | 4 | `DIRH` | `FIEH` |
| 0x04 | 4 | 3 (name length) | 3 (name length) |
| 0x08 | 0x40 | `KIT` | `001` … `100` |
| 0x48 | 4 | — | extension `kit` |
| 0x4C | 4 | — | data **size** (0x2660) |
| 0x50 | 4 | — | 0 |
| 0x54 | 4 | **offset** of the contents `SDCH` (0xE0) | data **offset** |
| 0x58 | 8 | 0 | 0 |

Entries are not necessarily sorted by number: in the studied file,
the table lists 031, 033, then 032, and the data follow the order of
the table. The data follow one another without padding: the first kit starts at 0x26A0, i.e.
`0x120 + 100 × 0x60`, and the last one ends exactly at the end of the file.

## Checksums

No checksum was found at the container level. Each kit carries
its own checksum (byte 0x08).

## Contents

The data are kits identical to those of the `.bkf`: see
[Kit format](bkf-format.md#kit-format-kit). In the studied example:

- 001–030: factory kits (*Power Duel*, *Cash Money Kit*, … *Bells*);
- 031: *WhereIs* (user kit, `KITC` variant), identical byte for byte
  to the `031.kit` of the `.bkf`;
- 032–100: *Empty*.

## Relation to the `.bkf`

| | `.fac` | `.bkf` |
|---|---|---|
| Location | `Strike/BackUp/BACKUPNNNNN/` | `Strike/All User Kit And Sample Backup/` |
| Kits | 001–100 | 031–100 (user kits) |
| Samples | no | yes (WAV, `.had`, lists) |
| Container endianness | big-endian | little-endian |
| Container checksums | none known | header and each `FILEH` |
