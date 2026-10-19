# Alesis Strike MultiPad - Kit Manager

Outils pour créer et modifier sur ordinateur les « user kits » de l'Alesis
Strike MultiPad, à partir de ses sauvegardes USB :

- `.bkf` : *Save All User Kits* (`Strike/All User Kit And Sample Backup/`) : kits et samples utilisateur ;
- `.fac` : `Strike/BackUp/…/STRIKE_BACKUP_KIT.fac` : kits seulement.

Le format n'est pas documenté par Alesis : il a été rétro-ingénié. **Garder une
copie de la sauvegarde d'origine** avant de charger un fichier produit par ces outils.

## Commandes

| Commande | Rôle |
|---|---|
| `python3 strike_kits.py export SAUVEGARDE DOSSIER [--no-wav]` | exporte les kits en JSON et les samples utilisateur en WAV |
| `python3 strike_kits.py import SAUVEGARDE DOSSIER -o NOUVELLE` | applique les JSON et les nouveaux WAV, écrit une nouvelle sauvegarde |
| `./editeur.sh [--root DOSSIER]` | lance l'éditeur web local sur http://127.0.0.1:8765/ |

`strike_kits.py` n'a besoin que de Python 3. `editeur.sh` demande en plus
Node.js : au premier lancement, il crée l'environnement virtuel `.venv`, installe
les dépendances et construit l'interface ; ensuite, il ne refait que ce qui a changé.

## Exemple

```bash
python3 strike_kits.py export Backup001.bkf mes_kits
# modifier mes_kits/kits/032_Empty.json, déposer des WAV dans mes_kits/wav/
python3 strike_kits.py import Backup001.bkf mes_kits -o Backup002.bkf
```

## Documentation

| Guide | Contenu |
|---|---|
| [Modifier un kit](docs/modifier-un-kit.md) | de la sauvegarde sur l'appareil au rechargement, en passant par les JSON |
| [Ajouter un sample](docs/ajouter-un-sample.md) | format requis, dossier `wav/`, règles et limites |
| [Éditeur web](docs/editeur-web.md) | installation, lancement, utilisation, API |
| [Contenu de l'export](docs/contenu-export.md) | `kits/*.json`, `samples.json`, `wav/` |
| [Paramètres](docs/parametres.md) | sens et plage de chaque champ, et méthode pour en identifier d'autres |
| [Limites connues](docs/limites.md) | ce qui n'est pas encore couvert ou vérifié |
| [Développement](docs/developpement.md) | organisation du code, tests, sauvegardes de référence |

Formats binaires :

- [docs/format-bkf.md](docs/format-bkf.md) : conteneur `.bkf`, samples, listes d'index et format des kits ;
- [docs/format-fac.md](docs/format-fac.md) : conteneur `.fac`.

Historique des versions : [CHANGELOG.md](CHANGELOG.md).
