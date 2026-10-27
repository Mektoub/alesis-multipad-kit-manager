"""Préférences de l'utilisateur, gardées d'un lancement à l'autre dans
<dossier de configuration>/preferences.json (voir `config_dir`).

Les mêmes pour le navigateur et l'application de bureau : c'est le serveur qui
les lit et les écrit (GET / PATCH /api/preferences). Chaque clé a une valeur
par défaut et une règle de validation ; à la lecture, une clé inconnue ou une
valeur invalide (fichier abîmé, d'une autre version) est ignorée.

`recent_files` et `last_dir` sont tenus à jour par le serveur à chaque ouverture
ou enregistrement (`opened`).
"""

import json
import os
import sys
from pathlib import Path

FILE_NAME = "preferences.json"
RECENT_MAX = 10  # fichiers récents gardés
HISTORY_MIN, HISTORY_MAX = 10, 1000  # bornes de la taille de l'historique

DEFAULTS = {
    "theme": "system",  # "system" | "light" | "dark"
    "hide_empty": True,  # kits vides masqués dans la liste
    "reopen_last": False,  # rouvrir la dernière sauvegarde au lancement
    "history_limit": 100,  # étapes gardées pour annuler / rétablir
    "recent_files": [],  # chemins absolus, le plus récent en tête
    "last_dir": None,  # dossier du dernier fichier ouvert ou enregistré
}


def _valid(key, value):
    if key == "theme":
        return value in ("system", "light", "dark")
    if key in ("hide_empty", "reopen_last"):
        return isinstance(value, bool)
    if key == "history_limit":
        return isinstance(value, int) and not isinstance(value, bool) and HISTORY_MIN <= value <= HISTORY_MAX
    if key == "recent_files":
        return (
            isinstance(value, list)
            and len(value) <= RECENT_MAX
            and all(isinstance(p, str) and Path(p).is_absolute() for p in value)
        )
    if key == "last_dir":
        return value is None or (isinstance(value, str) and Path(value).is_absolute())
    return False


def config_dir(app_dir, platform=sys.platform, env=os.environ):
    """Dossier de configuration de l'application, celui d'Electron (userData) :
    KITMANAGER_CONFIG s'il est donné, sinon ~/.config/<app_dir> (XDG) sous
    Linux, ~/Library/Application Support/<app_dir> sous macOS,
    %APPDATA%\\<app_dir> sous Windows."""
    if env.get("KITMANAGER_CONFIG"):
        return Path(env["KITMANAGER_CONFIG"])
    if platform == "win32":
        return Path(env.get("APPDATA") or Path.home() / "AppData" / "Roaming") / app_dir
    if platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_dir
    return Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config") / app_dir


class Preferences:
    """`file` : fichier JSON des préférences ; None : en mémoire seulement (tests)."""

    def __init__(self, file=None):
        self.file = Path(file) if file is not None else None
        self.values = dict(DEFAULTS)
        if self.file is not None:
            try:
                data = json.loads(self.file.read_text(encoding="utf-8"))
            except OSError, ValueError:
                data = {}
            if isinstance(data, dict):
                self.values.update({k: v for k, v in data.items() if k in DEFAULTS and _valid(k, v)})

    def __getitem__(self, key):
        return self.values[key]

    def get(self):
        return dict(self.values)

    def update(self, changes):
        """Modifie les clés données, toutes valides, ou aucune (ValueError)."""
        for key, value in changes.items():
            if key not in DEFAULTS:
                raise ValueError("préférence inconnue : %s" % key)
            if not _valid(key, value):
                raise ValueError("valeur invalide pour %s : %r" % (key, value))
        self.values.update(changes)
        self._write()
        return self.get()

    def opened(self, path):
        """Fichier ouvert ou enregistré : en tête des récents, son dossier retenu."""
        path = str(path)
        recent = [path, *(p for p in self.values["recent_files"] if p != path)][:RECENT_MAX]
        return self.update({"recent_files": recent, "last_dir": str(Path(path).parent)})

    def _write(self):
        """Écriture atomique : fichier temporaire, puis remplacement. En cas
        d'échec (dossier non accessible), les préférences restent en mémoire."""
        if self.file is None:
            return
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.file.with_name(self.file.name + ".tmp")
            tmp.write_text(json.dumps(self.values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, self.file)
        except OSError as exc:
            print("Préférences non enregistrées : %s" % exc, file=sys.stderr)
