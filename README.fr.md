# Alesis Strike MultiPad - Kit Manager

[English](README.md) · **Français**

Outils pour créer et modifier sur ordinateur les « user kits » de l'Alesis
Strike MultiPad, à partir de ses sauvegardes USB :

- `.bkf` : *Save All User Kits* (`Strike/All User Kit And Sample Backup/`) : kits et samples utilisateur ;
- `.fac` : `Strike/BackUp/…/STRIKE_BACKUP_KIT.fac` : kits seulement.

Le format n'est pas documenté par Alesis : il a été rétro-ingénié. **Garder une
copie de la sauvegarde d'origine** avant de charger un fichier produit par ces outils.

![Éditeur web : liste des kits, grille des 9 pads et réglages du pad choisi](docs/images/overview.png)

## Commandes

| Commande | Rôle |
|---|---|
| `python3 -m strike_kits export SAUVEGARDE DOSSIER [--no-wav]` | exporte les kits en JSON et les samples utilisateur en WAV |
| `python3 -m strike_kits import SAUVEGARDE DOSSIER -o NOUVELLE` | applique les JSON et les nouveaux WAV, écrit une nouvelle sauvegarde |
| `./dev.sh serve SAUVEGARDE` | lance l'éditeur dans le navigateur sur cette sauvegarde (lancement rapide) |
| `./dev.sh start [--frozen] [SAUVEGARDE]` | lance l'application de bureau (Electron), en développement |
| `./dev.sh package` | construit le paquet .deb de l'application de bureau (`sudo apt install ./desktop/dist/alesis-kit-manager_*.deb`) |
| `./dev.sh release X.Y.Z` | nouvelle version : versions mises à jour, commit et tag `vX.Y.Z` (non poussé) |

`strike_kits` n'a besoin que de Python 3. `./dev.sh serve` et `./dev.sh start`
demandent en plus Node.js : au premier lancement, ils créent l'environnement
virtuel `.venv`, installent les dépendances et construisent l'interface ;
ensuite, ils ne refont que ce qui a changé.

## Exemple

```bash
python3 -m strike_kits export Backup001.bkf mes_kits
# modifier mes_kits/kits/032_Empty.json, déposer des WAV dans mes_kits/wav/
python3 -m strike_kits import Backup001.bkf mes_kits -o Backup002.bkf
```

## Documentation

| Guide | Contenu |
|---|---|
| [Modifier un kit](docs/fr/editing-a-kit.md) | de la sauvegarde sur l'appareil au rechargement, en passant par les JSON |
| [Ajouter un sample](docs/fr/adding-a-sample.md) | format requis, dossier `wav/`, règles et limites |
| [Éditeur web](docs/fr/web-editor.md) | installation, lancement, utilisation, API |
| [Application de bureau](docs/fr/desktop-app.md) | lancement, fonctionnement, dépannage |
| [Contenu de l'export](docs/fr/export-contents.md) | `kits/*.json`, `samples.json`, `wav/` |
| [Paramètres](docs/fr/parameters.md) | sens et plage de chaque champ, et méthode pour en identifier d'autres |
| [Limites connues](docs/fr/limitations.md) | ce qui n'est pas encore couvert ou vérifié |
| [Développement](docs/fr/development.md) | organisation du code, tests, sauvegardes de référence |

Formats binaires :

- [docs/fr/bkf-format.md](docs/fr/bkf-format.md) : conteneur `.bkf`, samples, listes d'index et format des kits ;
- [docs/fr/fac-format.md](docs/fr/fac-format.md) : conteneur `.fac`.

Historique des versions : [CHANGELOG.md](CHANGELOG.md).
