# Format `.fac` (sauvegarde des kits)

[English](../en/fac-format.md) · **Français**

Fichier `Strike/BackUp/BACKUPNNNNN/STRIKE_BACKUP_KIT.fac`, produit par le menu
*Utility > Backup* de l'appareil. Il contient **uniquement les kits** (pas de
samples) : 100 kits `001` à `100` dans l'exemple étudié (992 288 octets).

Ce document décrit ce qui a été observé par rétro-ingénierie d'un seul fichier
réel. Tout est en **big-endian**.

## Vue d'ensemble

Le fichier imite un petit système de fichiers : un en-tête racine, un répertoire
`KIT`, une table d'entrées de fichiers, puis les données mises bout à bout.

```
0x000  SDRH   en-tête racine            (0x40)
0x040  SDCH   contenu de la racine      (0x40) : 1 répertoire
0x080  DIRH   répertoire « KIT »        (0x60) → contenu en 0x0E0
0x0E0  SDCH   contenu de KIT            (0x40) : 100 fichiers
0x120  FIEH   × 100                     (0x60 chacun)
0x26A0 données des 100 kits, contiguës  (0x2660 chacun)
```

`SDRH` pourrait signifier « SD Root Header » ; ce n'est qu'une supposition.

## En-têtes

### `SDRH` (0x00)

| Offset | Taille | Valeur | Sens |
|---|---|---|---|
| 0x00 | 4 | `SDRH` | signature |
| 0x04 | 2 | `0x0040` | taille de l'en-tête |
| 0x08 | 1 | `0xB0` | inconnu (version, drapeaux ?) |
| reste | — | 0 | — |

### `SDCH` (0x40 et 0xE0)

En-tête de contenu d'un répertoire, de 0x40 octets.

| Offset | Taille | Racine (0x40) | `KIT` (0xE0) | Sens probable |
|---|---|---|---|---|
| 0x04 | 2 | `0x0040` | `0x0040` | taille de l'en-tête |
| 0x0A | 2 | 1 | 0 | nombre de sous-répertoires |
| 0x0C | 2 | 0 | 100 | nombre de fichiers |

### `DIRH` (0x80) et `FIEH` (à partir de 0x120)

Les deux types d'entrée ont la même disposition, sur 0x60 octets :

| Offset | Taille | `DIRH` | `FIEH` |
|---|---|---|---|
| 0x00 | 4 | `DIRH` | `FIEH` |
| 0x04 | 4 | 3 (longueur du nom) | 3 (longueur du nom) |
| 0x08 | 0x40 | `KIT` | `001` … `100` |
| 0x48 | 4 | — | extension `kit` |
| 0x4C | 4 | — | **taille** des données (0x2660) |
| 0x50 | 4 | — | 0 |
| 0x54 | 4 | **offset** du `SDCH` de contenu (0xE0) | **offset** des données |
| 0x58 | 8 | 0 | 0 |

Les entrées ne sont pas forcément rangées par numéro : dans le fichier étudié,
la table donne 031, 033, puis 032, et les données suivent l'ordre de
la table. Les données se suivent sans bourrage : le premier kit commence à 0x26A0, soit
`0x120 + 100 × 0x60`, et le dernier se termine exactement à la fin du fichier.

## Sommes de contrôle

Aucune somme de contrôle n'a été repérée au niveau du conteneur. Chaque kit porte
sa propre somme de contrôle (octet 0x08).

## Contenu

Les données sont des kits identiques à ceux du `.bkf` : voir
[Format d'un kit](bkf-format.md#format-dun-kit-kit). Dans l'exemple étudié :

- 001–030 : kits d'usine (*Power Duel*, *Cash Money Kit*, … *Bells*) ;
- 031 : *WhereIs* (kit utilisateur, variante `KITC`), identique octet pour octet
  au `031.kit` du `.bkf` ;
- 032–100 : *Empty*.

## Lien avec le `.bkf`

| | `.fac` | `.bkf` |
|---|---|---|
| Emplacement | `Strike/BackUp/BACKUPNNNNN/` | `Strike/All User Kit And Sample Backup/` |
| Kits | 001–100 | 031–100 (kits utilisateur) |
| Samples | non | oui (WAV, `.had`, listes) |
| Endianness du conteneur | big-endian | little-endian |
| Sommes de contrôle du conteneur | aucune connue | en-tête et chaque `FILEH` |
