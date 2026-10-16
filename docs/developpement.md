# Développement

## Organisation du code

| Chemin | Rôle |
|---|---|
| `strike_kits.py` | lecture et écriture des formats, commandes `export` / `import` (bibliothèque standard uniquement) |
| `editor/server.py` | API FastAPI de l'éditeur |
| `editor/meta.py` | description des paramètres pour l'interface (libellés, couleurs) |
| `editor/__main__.py` | lancement (`python -m editor`) |
| `editeur.sh` | lancement avec préparation automatique du venv et de l'interface |
| `editor/web/` | interface Svelte (Vite) |
| `test_strike_kits.py` | tests du format et de la ligne de commande |
| `test_editor.py` | tests de l'API |
| `docs/format-*.md` | ce que l'on sait des formats binaires |

Dans `strike_kits.py` :

- `decode_kit` / `encode_kit` : kit binaire ↔ JSON ;
- `Bkf` : conteneur `.bkf` décomposé en enregistrements, reconstructible à
  l'identique, avec `add_sample` ;
- `Backup` : sauvegarde `.bkf` ou `.fac` ouverte en mémoire, utilisée par l'éditeur
  et par les commandes.

## Tests

```bash
python3 -m unittest -v test_strike_kits      # sans dépendance
.venv/bin/python -m unittest -v test_editor  # nécessite requirements.txt
```

Les tests s'appuient sur de vraies sauvegardes, cherchées dans le dossier
`Strike/` du projet ; ceux dont la sauvegarde manque sont ignorés. On peut les
indiquer par des variables d'environnement :

| Variable | Sauvegarde | Sert à vérifier |
|---|---|---|
| `STRIKE_BKF` | `Backup001.bkf` | aller-retour, modifications, kit `KITC` « WhereIs » |
| `STRIKE_BKF2` | `Backup002.bkf` : après l'import de « Crazy in Love sample track.wav » et la création du kit 032 | l'ajout de sample reproduit l'appareil octet pour octet |
| `STRIKE_BKF3` | `Backup003.bkf` : Control « Click On/Off » et Audio Output « Aux+Phone » sur le pad 9 du kit 032 | identification de `control` et `audio_output` |
| `STRIKE_FAC` | `STRIKE_BACKUP_KIT.fac` | conteneur `.fac`, vélocités des kits d'usine |

Avant de corriger un bug, écrire un test qui le met en évidence et vérifier qu'il
échoue, puis corriger.

## Interface

```bash
cd editor/web
npm install
npm run dev     # développement, avec le serveur lancé à côté
npm run build   # production, dans editor/web/dist
```

Les versions des paquets sont figées dans `package.json` et `requirements.txt`.
