# Format `.bkf` (sauvegarde « All User Kit And Sample Backup »)

Fichier produit par *Utility > Backup > Save All User Kits* (firmware ≥ 1.3),
dans `Strike/All User Kit And Sample Backup/BackupNNN.bkf`. Il contient les kits
utilisateur, les samples utilisateur et les listes d'index des samples.

Ce document décrit ce qui a été observé par rétro-ingénierie d'un seul fichier
réel (`Backup001.bkf`, 39 Mo, 141 fichiers). Les points incertains sont signalés.

Conventions : offsets en hexadécimal ; **le conteneur est en little-endian**,
mais **les fichiers qu'il contient (kits, listes, `.had`) sont en big-endian**.

## Vue d'ensemble

```
0x00  En-tête PACKBKF (0x40 octets)
0x40  Enregistrement fichier 1 : FILEH | PATH | NAME | DATA | données | bourrage
....  Enregistrement fichier 2
....  ...
EOF   (le dernier FILEH pointe sur la fin du fichier)
```

Les chemins sont ceux de la mémoire interne de l'appareil, avec `S:\` comme racine.

## En-tête (0x00–0x40)

| Offset | Taille | Valeur observée | Sens |
|---|---|---|---|
| 0x00 | 8 | `PACKBKF ` | signature (avec espace final) |
| 0x08 | 4 | `0x38` | inconnu (version ?) |
| 0x0C | 3 | 0 | — |
| 0x0F | 1 | `0xAE` | **somme de contrôle** : `sum(octets[0x10:0x40]) & 0xFF` |
| 0x10 | 4 LE | 141 | nombre de fichiers (vérifié) |
| 0x14 | 4 LE | 33 | nombre de fichiers `.wav` (vérifié : passe à 34 après l'import d'un sample) |
| 0x18 | 0x28 | 0 | — |

## Enregistrement fichier

Chaque fichier occupe un enregistrement qui commence à un offset `p` :

| Offset relatif | Taille | Contenu |
|---|---|---|
| +0x000 | 8 | `FILEH\0\0\0` |
| +0x008 | 3 | 0 |
| +0x00B | 1 | **somme de contrôle** : `sum(octets[p+0x10 : p+0x180]) & 0xFF` |
| +0x00C | 4 | 0 |
| +0x010 | 4 LE | offset absolu de l'enregistrement suivant (= taille du fichier pour le dernier) |
| +0x014 | 0x3C | 0 |
| +0x050 | 4 + 4 LE + 8 | `PATH`, longueur `0x80`, 8 octets nuls |
| +0x060 | 0x80 | chemin du dossier, ex. `S:\KIT\`, terminé par des zéros |
| +0x0E0 | 4 + 4 LE + 8 | `NAME`, longueur `0x80`, 8 octets nuls |
| +0x0F0 | 0x80 | nom du fichier, ex. `031.kit` |
| +0x170 | 4 + 4 LE + 8 | `DATA`, taille des données, 8 octets nuls |
| +0x180 | taille | données brutes du fichier |
| … | variable | bourrage nul jusqu'à l'enregistrement suivant |

La somme de contrôle `FILEH` ne couvre que les métadonnées (de +0x10 à +0x180),
pas les données. L'intégrité des kits repose sur leur propre somme de contrôle
(voir plus bas).

Le bourrage nul après les données vaut **`32 − (taille mod 16)`** octets, de 17 à 32
(règle vérifiée sur les 284 enregistrements de deux sauvegardes).

L'ordre des enregistrements est : kits, listes, `.had`, puis `.wav`. Dans chaque
groupe, les samples apparaissent dans leur ordre de création.

## Fichiers contenus

| Dossier | Fichiers | Contenu |
|---|---|---|
| `S:\KIT\` | `031.kit` … `100.kit` | les 70 kits utilisateur, 0x2660 octets chacun ([format](#format-dun-kit-kit)) |
| `S:\WAV\LIST\` | `Wave_list.lst`, `wave_list_sort_num.lst`, `wave_list_sort_name.lst`, `wave_list_sort_group.lst`, `WaveList_User_SortSize.lst` | index des samples (usine et utilisateur) |
| `S:\WAV\HEAD\NNN\` | `MM.had` | en-tête de chaque sample utilisateur (224 octets) |
| `S:\WAV\DATA\NNN\` | `MM.wav` | sample utilisateur (WAV PCM 16 bits, 44,1 kHz) |

### Identifiant de sample

Un sample est identifié par un entier `id = NNN × 100 + MM`, où `NNN` est le dossier
et `MM` le numéro de fichier. Exemple : `8071` correspond à `WAV/DATA/080/71.wav`.
Les samples d'usine ont des id inférieurs à 8000 et ne figurent pas dans la
sauvegarde, sauf dans les listes d'index. `0xFFFF` signifie « aucun sample ».

### `.had` (en-tête de sample, 0xE0 octets, big-endian)

| Offset | Taille | Contenu |
|---|---|---|
| 0x00 | 4 | `INTH` |
| 0x04 | 2 | `0x0010` |
| 0x08 | 1 | **somme de contrôle** : `sum(had[0x0A:]) & 0xFF` (même règle que les kits, vérifiée) |
| 0x14 | 1 | bits par échantillon (`0x10` = 16) |
| 0x15 | 1 | nombre de canaux (1 ou 2) |
| 0x16 | 2 | fréquence (`0xAC44` = 44 100 Hz) |
| 0x18 | 4 | offset des données audio dans le `.wav` (après le chunk `data`) |
| 0x1C | 4 | idem (point de départ ?) |
| 0x20 | 4 | taille des données audio (taille du chunk `data`) |
| 0x28 | 4 | offset des données audio |
| 0x2C | 4 | offset de fin = offset + taille (= taille du `.wav` si `data` est le dernier chunk) |
| 0x30 | 4 | offset des données audio |
| 0x34 | 4 | offset de fin |
| 0x3F | 1 | longueur du nom complet |
| 0x40 | 16 | nom du sample, tronqué à 16 caractères |
| 0x58 | 4 + 4 | `PATH`, longueur du chemin |
| 0x60 | 0x80 | chemin relatif, ex. `\080\71.wav` |

Les 3 paires (début, fin) correspondent probablement au sample entier, à la zone
lue (*Edit Start/End*) et à la boucle. Dans certains `.had`, les octets non
utilisés contiennent des résidus de données audio au lieu de zéros.

### Listes `.lst`

Toutes ont un en-tête de 0x20 octets :

| Offset | Contenu |
|---|---|
| 0x00 | `WLTH` (`Wave_list.lst`) ou `SLTH` (autres) |
| 0x04 | `0x0020` (taille de l'en-tête) |
| 0x08 | 1 octet qui varie d'un fichier à l'autre. **Ce n'est pas une somme de contrôle** : il ne change pas quand l'appareil ajoute un sample |
| 0x0A | u16, nombre d'entrées : 8 072 samples, 85 groupes, ou 33 samples utilisateur |

Les samples ont des id **denses de 0 à 8 071** : l'id est l'indice dans
`Wave_list.lst`. Pour tous les samples observés, `id = dossier × 100 + fichier`.

- **`Wave_list.lst`** (taille fixe 0x20000) : table indexée par id, entrées de
  8 octets.
  - +0 : u16, id (bit `0x8000` = entrée libre) ;
  - +2 : u16, emplacement `dossier << 8 | fichier` (ex. `0x5047` = `080/71`) ;
  - +4 : u16, bibliothèque ? (0, 1, 2, 30, 31, 32 ; 0 pour les samples utilisateur) ;
  - +6 : u16, **rang du sample dans `sort_num`**.

  Les entrées au-delà de 8 071 sont libres (`0x8000 | indice`). Leur emplacement
  est déjà renseigné (ex. `0x5048` = `080/72` pour l'id 8072).
- **`wave_list_sort_num.lst`** : 8 072 paires (u16 rang, u16 id) triées par rang,
  suivies d'une paire nulle. Un sample utilisateur récent est ajouté en fin de liste.
- **`wave_list_sort_name.lst`** : 8 072 entrées de 0x90 octets triées par nom
  (quasi alphabétique, insensible à la casse ; quelques exceptions de ponctuation).
  - +0x00 : u16, compteur de position. À l'insertion, l'entrée reçoit sa position
    et **toutes les entrées suivantes sont incrémentées de 1**. Les valeurs
    d'usine (position modulo 256) sont l'héritage de ce mécanisme. L'octet de
    poids faible vaut toujours la position modulo 256 ; l'octet de poids fort
    contient le reste de la position pour un sample ajouté récemment (1832 pour
    « Crazy in Love »), mais 0 pour un sample ajouté en 2016 (« WIMH sample
    track », 102 à la position 7782). L'outil écrit la position complète.
  - +0x02 : u16, **id du sample** ;
  - +0x04 : u16, longueur du nom d'origine (nom du fichier importé, `.wav` compris) ;
  - +0x10 : **nom complet**, 0x80 octets. L'appareil ajoute `_id` aux noms en double.

  C'est la source du catalogue `samples.json`.
- **`wave_list_sort_group.lst`** : 85 groupes (catégories), à la suite :
  - +0 : u8, numéro du groupe ;
  - +1 : u16, nombre de membres ;
  - +3 : u8, 0 ;
  - +4 : u32, longueur du nom ;
  - +8 : nom, 16 octets ;
  - +0x18 : membres (u16 rang, u16 id).

  Les groupes 0 à 41 sont les catégories d'usine (*Kicks Acous*, *Loops DnB*…),
  42 à 83 les mêmes catégories côté utilisateur (vides ici), et 84 **New Sample**
  regroupe les 33 samples importés.
- **`WaveList_User_SortSize.lst`** (taille fixe 0x4000) : 33 paires
  (u32 id, u32 taille du `.wav`) des samples utilisateur, triées par taille
  croissante (à taille égale, id décroissant).

### Ajout d'un sample (observé sur l'appareil)

Règles déduites de deux sauvegardes faites avant et après l'import d'un seul WAV
sur l'appareil. L'outil les applique et reproduit la sauvegarde de l'appareil
octet pour octet (test `test_ajout_reproduit_l_appareil`). Avec `id` = nombre
actuel de samples (8 072 dans l'exemple) :

1. Le `.wav` est copié **tel quel** dans `S:\WAV\DATA\080\72.wav`, à la suite des autres `.wav`.
2. Un `.had` est créé dans `S:\WAV\HEAD\080\72.had`, à la suite des autres `.had`.
3. `Wave_list.lst` : nombre d'entrées + 1 ; l'entrée `id` perd le drapeau `0x8000`.
4. `sort_num` : la paire (rang = `id`, `id`) est ajoutée avant la paire nulle finale.
5. `sort_name` : l'entrée est insérée à sa place alphabétique (insensible à la casse).
   Son champ +0x04 vaut la longueur du nom + 4 (`.wav`).
6. `sort_group` : (n, `id`) est ajouté en fin du groupe *New Sample*, dont le nombre
   de membres passe à n + 1.
7. `SortSize` : (`id`, taille du `.wav`) est inséré par taille croissante, avant les
   entrées de même taille.
8. L'en-tête `.bkf` est mis à jour : nombre de fichiers + 2, nombre de `.wav` + 1,
   sommes de contrôle.

L'octet 0x08 des listes ne change pas.

## Format d'un kit (`.kit`)

Commun aux formats `.bkf` et [`.fac`](format-fac.md). Taille fixe de
**0x2660 octets (9 824)**, en big-endian.

### Variantes

| Signature | Champ à +0x04 | Observé dans |
|---|---|---|
| `KITH` | `0x0260` | kits d'usine et kits vides |
| `KITC` | `0x0020` | kits créés ou modifiés sur l'appareil (ex. 031 « WhereIs », 001, 002 du `.fac`) |

### En-tête (0x000–0x260)

| Offset | Taille | Contenu |
|---|---|---|
| 0x00 | 4 | `KITH` ou `KITC` |
| 0x04 | 2 | `0x0260` (KITH) ou `0x0020` (KITC) |
| 0x06 | 2 | `0x0000` ou `0xFFFF` (inconnu) |
| 0x08 | 1 | **somme de contrôle** : `sum(kit[0x0A:]) & 0xFF` (vérifiée sur 33 kits distincts) |
| 0x09 | 1 | `0x00` (KITH) ; `0x2B` (KITC) |
| 0x0A | 2 | `0x0018` / `0x1318` (KITH), autre en KITC (inconnu) |
| 0x0C | 1 | **volume du kit** (0–100) ; en KITH suivi de min (0x0D) et max (0x0E) |
| 0x10 | 2 | **tempo × 10** (ex. 1200 = 120 BPM) ; en KITH suivi de min `0x012C` (30) et max `0x0AF0` (280) |
| 0x50–0x1A0 | — | probablement les effets du kit (FX1–3) : blocs répétés de valeurs, non décodés |
| 0xC0 | 16 | **nom du kit** (ASCII, terminé par des zéros) |

Le reste de l'en-tête n'est pas décodé. On y trouve probablement la signature
rythmique et les réglages de logo (couleur, mode, beat).

### Emplacements (pads et déclencheurs)

Il y a **24 emplacements** de 0x180 octets, à `0x260 + i × 0x180` (`i` = 0…23).
Chacun commence par `KITI` `0x0180`.

D'après les notes MIDI des kits d'usine :

| Emplacements | Notes MIDI usine | Rôle |
|---|---|---|
| 1–9 | 36–46 | pads P1–P9 (certain) |
| 10–17 | 39–51 | déclencheurs externes, probablement T1–T5, HH… |
| 18–21 | 53–57, 124–127 | probablement les pédales FS1–FS4 |
| 22–24 | 60–63 | inconnu |

Structure d'un emplacement (offsets relatifs) :

| Offset | Taille | Contenu |
|---|---|---|
| +0x00 | 4 | `KITI` |
| +0x04 | 2 | `0x0180` (taille du bloc) |
| +0x0C | 2 | `0x0001` |
| +0x10 | 1 | couleur Play (0 = Red … 16 = White, ordre du manuel) |
| +0x11 | 1 | mode Play (0–6) |
| +0x12 | 1 | Play Beat : 0 = 1/2, 1 = 1/4, 2 = 1/8, 3 = 1/16 (vérifié : 3 = 1/16) |
| +0x14 | 1 | couleur Stop |
| +0x15 | 1 | mode Stop |
| +0x16 | 1 | Stop Beat, mêmes valeurs (vérifié : 0 = 1/2) |
| +0x18 | 1 | inconnu (0–6) |
| +0x19 | 1 | Sync Mode : Mute, Cycle, Random, Together, HiHat (vérifié : 4 = HiHat) |
| +0x28–0x80 | 4 × n | **paramètres du pad** (enregistrements, voir ci-dessous) |
| +0x80–0xE0 | 0x60 | **wave A** |
| +0xE0–0x140 | 0x60 | **wave B** |
| +0x140–0x180 | 0x40 | zéros |

Une wave se compose de :

| Offset | Taille | Contenu |
|---|---|---|
| +0x00 | 2 | **id du sample** (`0xFFFF` = aucun) |
| +0x02 | 1 | **Velocity Low** (0 par défaut) |
| +0x03 | 1 | **Velocity High** (127 par défaut) |
| +0x04 | 4 | zéros |
| +0x08–0x60 | 4 × n | paramètres de la wave (enregistrements) |

### Enregistrements de paramètres

Chaque paramètre tient sur 4 octets : `id`, `valeur`, `min`, `max`. La suite se
termine par un enregistrement dont l'`id` vaut `0xFF` (bourrage `ff 00 00 00`).
Les plages sont donc auto-décrites. Exception : certaines valeurs observées
dépassent `max`, par exemple `0x28` pour une plage 0–16 sur `0x0E`, `0x16` et
`0x17`. Il s'agit peut-être de valeurs spéciales.

Paramètres de pad (zone +0x28) :

| id | Plage | Sens probable |
|---|---|---|
| 0x00 | 0–100 | volume |
| 0x02 | 0–31 | pan (15 = centre) |
| 0x08 | 0–127 | note MIDI (confirmé : 36, 37, 38… sur P1, P2, P3…) |
| 0x09 | 0–4 | ? (Sync Mode est à +0x19) |
| 0x0C | 0–16 | Sync Group |
| 0x0E | 0–16 | ? (17 valeurs : une couleur ?) |
| 0x0F | 0–5 | **Audio Output** : 0 = Main+Phone, 1–3 = FX1–3, 4 = Aux+Phone (vérifié), 5 = Phone Only |
| 0x10 | 0–127 | Fixed Level (0 = Off) |
| 0x11 | 1–32 | Sensitivity |
| 0x12 | 0–32 | Threshold (défaut 4, comme dans le manuel) |
| 0x13 | 0–7 | **Curve** : Normal, Exp1, Exp2, Log1, Log2, Loud (vérifié : 5 = Loud) |
| 0x14 | 0–13 | **Control** (vérifié : 3 = Click On/Off). Ordre probable du manuel : Off, Next Kit, Previous Kit, Click On/Off, Tap Tempo, Panic, Looper Rec, Looper Play/Stop, Kit FX1–3, MST FX ; 14 valeurs possibles, soit 2 de plus que dans le manuel v1.2 |
| 0x15 | 0–1 | **Sound** : 0 = Off (par défaut), 1 = On |
| 0x16 | 0–127 | **Kit FX Level** (vérifié ; 40 par défaut) |
| 0x17 | 0–16 | ? |

Paramètres de wave (zone +0x08) :

| id | Plage | Sens probable |
|---|---|---|
| 0x00 | 0–100 | volume |
| 0x02 | 0–32 | pan |
| 0x09 | 0–5 | **Playback Mode** : Oneshot, Alter, Loop, RoundRobin, Hi-hat, puis FS1–FS4 ; FS4 vaut 9 (vérifié), au-delà du max déclaré |
| 0x10 | 0–127 | ? (vélocité ?) |
| 0x18 | 0–255 | ? |
| 0x19 | 0–1 | **Poly/Mono** : 0 = Mono (vérifié), 1 = Poly |
| 0x1A | 0–100 | Fade In |
| 0x1B | 0–100 | Fade Out |
| 0x1C | 0–2 | Priority (Low/Medium/High) |

### Particularités de la variante `KITC`

`KITC` est **le format que l'appareil écrit quand on enregistre un kit**. Le kit 032
« CrazyInLove », créé sur l'appareil, est passé de `KITH` à `KITC`.

Les emplacements 9 à 24 (à partir de 0xE60) ont une structure `KITI` normale.
Dans les 8 premiers (0x260–0xE60), **les offsets sont les mêmes qu'en `KITH`**,
mais :

- la signature `KITI` et les octets `id`, `min` et `max` des enregistrements sont
  remplacés par `0xFF` (parfois `0x00`), seule la **valeur** restant à sa position.
  Exemple : `ff 5a ff ff` pour un volume de 90, `ff 29 ff ff` pour la note MIDI 41
  du pad 5 ;
- les en-têtes de wave restent intacts : id du sample et vélocités (ex. `1f 88 00 7f`
  pour le sample 8072, vélocité 0–127, sur le pad 5) ;
- des structures de 0x30 octets (`80 00 … 00 20 "Empty"`), espacées de 0xB0 octets
  à partir de 0xD0, recouvrent les octets `id`, `min` et `max` de certains
  enregistrements. **L'octet valeur, lui, reste à sa place** : la chaîne `"Empty"`
  apparaît alors avec son 2ᵉ octet remplacé par la valeur. Exemple : `45 28 70 74`
  (`"E(pt"`) donne la note MIDI 40 du pad 4. Les positions recouvertes sont les
  mêmes dans tous les kits `KITC` observés.

Dans ces 8 emplacements, l'outil lit donc toujours l'octet valeur, quels que soient
les octets voisins, et ne réécrit que lui (ou les 2 octets de l'id du sample). Un
en-tête de wave est lu si `low ≤ high ≤ 127`.

## Méthode pour aller plus loin

Pour identifier un paramètre inconnu :

1. faire une sauvegarde ;
2. modifier un seul réglage sur l'appareil ;
3. refaire une sauvegarde ;
4. exporter les deux avec `python3 -m strike_kits export` et comparer avec `diff -r`.
