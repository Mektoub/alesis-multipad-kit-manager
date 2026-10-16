# strike_kits — éditer les kits du Strike MultiPad en JSON

Outil Python 3 (sans dépendance) pour éditer sur ordinateur les « user kits » de
l'Alesis Strike MultiPad à partir d'une sauvegarde `.bkf`
(*Save All User Kits*, dossier `Strike/All User Kit And Sample Backup/`).
Les fichiers `.fac` (`Strike/BackUp/…/STRIKE_BACKUP_KIT.fac`) sont aussi pris en charge.

Le format a été rétro-ingénié : il n'est pas documenté par Alesis. Ce qui en est
connu est décrit dans :

- [docs/format-bkf.md](docs/format-bkf.md) : conteneur `.bkf`, samples, listes et format des kits ;
- [docs/format-fac.md](docs/format-fac.md) : conteneur `.fac`.

## Utilisation

```bash
# 1. Exporter les kits en JSON et les samples utilisateur en WAV (--no-wav pour s'en passer)
python3 strike_kits.py export Backup001.bkf mes_kits

# 2. Modifier mes_kits/kits/032_Empty.json, etc.
#    Optionnel : déposer de nouveaux samples dans mes_kits/wav/

# 3. Produire une nouvelle sauvegarde (l'original n'est jamais modifié)
python3 strike_kits.py import Backup001.bkf mes_kits -o Backup002.bkf
```

Copier ensuite `Backup002.bkf` dans `Strike/All User Kit And Sample Backup/` sur
la clé USB et la charger depuis le menu *Utility > Backup* de l'appareil.
**Garder une copie de la sauvegarde d'origine.**

L'import repart du `.bkf` d'origine, réécrit les kits et ajoute les nouveaux
samples. Les octets non décodés restent intacts, et les sommes de contrôle sont
recalculées. Un export suivi d'un import sans modification redonne un fichier
identique octet pour octet.

## Ajouter des samples

Déposer les fichiers dans le dossier `wav/` de l'export (ex. `mes_kits/wav/Mon Snare.wav`),
puis y faire référence par leur nom, sans `.wav`, dans les kits :

```json
"wave_a": { "sample": "Mon Snare" }
```

- Format requis : WAV PCM **16 bits, 44,1 kHz**, mono ou stéréo. Le fichier est copié tel quel.
- Le nom du sample est celui du fichier. Un WAV est ignoré si son nom existe déjà
  parmi les samples ou si son contenu est identique à un sample utilisateur. Le
  dossier `wav/` produit par l'export peut donc rester en place, même si on renomme
  un fichier : on peut relancer l'import sans créer de doublon.
- Les samples rejoignent la catégorie *User > New Sample*, comme un import sur l'appareil.
- Les règles appliquées ont été relevées sur une sauvegarde faite par l'appareil
  avant et après un import ; l'outil reproduit ce résultat octet pour octet.

## Contenu de l'export

- `kits/NNN_Nom.json` : un fichier par kit. `NNN` est le numéro du kit et sert
  de clé à l'import ; la partie après `_` est libre.
- `samples.json` : catalogue `id → nom` de tous les samples (usine et utilisateur).
- `wav/Nom du sample.wav` : les samples utilisateur, copiés tels quels. Les
  caractères interdits dans un nom de fichier (`/ \ : * ? " < > |`) sont remplacés
  par `_`. Les samples d'usine ne figurent pas dans la sauvegarde.

Structure d'un kit :

```json
{
  "format": "KITH",
  "name": "Mon Kit",          // 16 caractères max
  "level": 90,                // 0–100
  "tempo": 120.0,             // 30–280 BPM
  "slots": [
    {
      "slot": 1, "_label": "P1",
      "light":  { "play_color": 16, "play_mode": 3, "stop_color": 8, "stop_mode": 1 },
      "params": { "volume": 90, "pan": 15, "midi_note": 36, "...": 0 },
      "wave_a": { "sample": 8071, "_sample_name": "WIMH sample track",
                  "velocity_low": 0, "velocity_high": 127, "params": { "volume": 90, "...": 0 } },
      "wave_b": { "sample": null, "velocity_low": 0, "velocity_high": 127, "params": { "...": 0 } }
    }
  ]
}
```

- Les clés qui commencent par `_` sont informatives et ignorées à l'import.
- `sample` accepte un id (voir `samples.json`), un nom exact de sample (y compris
  ceux ajoutés depuis `wav/`), ou `null` (aucun sample). Un id vaut `dossier × 100 + numéro` : `8071` = `WAV/DATA/080/71.wav`.
- Chaque paramètre a une plage min/max stockée dans le kit. Une valeur modifiée
  hors plage est refusée.

## Paramètres identifiés

| Où | Clé | Sens | Plage |
|---|---|---|---|
| kit | `level`, `tempo`, `name` | volume du kit, tempo, nom | 0–100, 30–280 |
| pad | `volume`, `pan` | volume, panoramique (15 = centre) | 0–100, 0–31 |
| pad | `midi_note` | note MIDI émise | 0–127 |
| pad | `sensitivity`, `threshold` | sensibilité, seuil | 1–32, 0–32 |
| pad | `fixed_level` | dynamique fixe (0 = Off) | 0–127 |
| pad | `sync_group` | Sync Group (0 = Off) | 0–16 |
| pad | `control` | Control : 0 = Off, 1 = Next Kit, 2 = Previous Kit, 3 = Click On/Off (vérifié), suite dans l'ordre du manuel | 0–13 |
| pad | `audio_output` | 0 = Main+Phone, 1–3 = FX1–3, 4 = Aux+Phone (vérifié), 5 = Phone Only | 0–5 |
| pad | `sound` | Sound On/Off (sens des valeurs à confirmer) | 0–1 |
| light | `play_color`, `stop_color` | couleur (0 = Red … 16 = White, ordre du manuel) | 0–16 |
| light | `play_mode`, `stop_mode` | mode d'éclairage (ordre du manuel) | 0–6 |
| wave | `velocity_low`, `velocity_high` | plage de vélocité qui déclenche la couche (couches A/B, multisamples) | 0–126, 1–127 |
| wave | `volume`, `pan` | volume, panoramique de la couche | 0–100, 0–32 |
| wave | `fade_in`, `fade_out` | fondus (0 = Off) | 0–100 |
| wave | `priority` | Low / Medium / High | 0–2 |

Les paramètres nommés `pXX` (id hexadécimal) ne sont pas encore identifiés. On
peut les modifier, mais leur sens reste à découvrir. Pour en identifier un :
faire une sauvegarde, changer un seul réglage sur l'appareil, refaire une
sauvegarde, exporter les deux, puis comparer :

```bash
diff -r export_avant/kits export_apres/kits
```

## Limites connues

- **Emplacements** : 1–9 = pads P1–P9 (certain). 10–24 = déclencheurs externes,
  pédales, etc. (correspondance exacte non vérifiée).
- **Kits `KITC`** (format écrit par l'appareil quand on enregistre un kit) : dans
  les emplacements 1 à 8, seules les valeurs sont stockées et certaines sont
  recouvertes par d'autres données. Les champs illisibles sont absents du JSON et
  ne peuvent pas être modifiés. Les kits vides (`KITH`) sont entièrement modifiables.
- Les noms de samples de plus de 16 caractères peuvent être tronqués dans les
  en-têtes `.had`. `samples.json` donne les noms complets.
- **Ajout de samples** : vérifié jusqu'à l'id 8099 (dossier `080`). Au-delà, l'outil
  refuse par prudence, la convention de nommage des dossiers suivants n'ayant pas été
  observée. Supprimer ou remplacer un sample n'est pas pris en charge.
- Les échantillons ajoutés n'ont pas encore été testés en lecture sur l'appareil.

## Tests

```bash
python3 -m unittest -v test_strike_kits
```

Les tests utilisent de vraies sauvegardes, cherchées par défaut dans le dossier
`Strike/` du projet ou indiquées par les variables `STRIKE_BKF`, `STRIKE_BKF2`
et `STRIKE_FAC`. `Backup002.bkf` est la sauvegarde faite par l'appareil après
l'import d'un sample. Elle sert de référence au test d'ajout.
