"""Textes du serveur affichés par l'interface (erreurs, libellés de
l'historique, infobulles des paramètres), en anglais et en français.

La langue est celle de la requête en cours : l'interface envoie la sienne dans
l'en-tête X-KitManager-Language (voir editor/server.py), anglais par défaut.
Hors requête (lancement du serveur), c'est celle des préférences (`startup`).
Les noms des paramètres des pads et leurs valeurs restent en anglais, comme
sur l'appareil ; les erreurs de la bibliothèque strike_kits restent en français.

`Msg` garde un texte à traduire plus tard : les libellés de l'historique sont
ainsi affichés dans la langue de la requête qui les lit, pas dans celle de la
modification.
"""

import locale
import os
from contextvars import ContextVar

LANGUAGES = ("en", "fr")
DEFAULT = "en"

MESSAGES = {
    "en": {
        "absolute_path": "absolute path expected: {path}",
        "outside_roots": "outside the allowed folders ({roots}): {path}",
        "backup_not_found": "backup not found: {path}",
        "unsaved": "some changes are not saved",
        "no_backup": "no backup open",
        "token": "missing or invalid token",
        "kit_missing": "kit {num} does not exist",
        "user_samples_only": "only user samples are stored in the backup",
        "extension": "the extension must be .{kind}",
        "file_exists": "the file already exists: {path}",
        "nothing_undo": "nothing to undo",
        "nothing_redo": "nothing to redo",
        "step_missing": "step {id} is not in the history",
        "unknown_preference": "unknown preference: {key}",
        "invalid_preference": "invalid value for {key}: {value}",
        # historique
        "copy_from": "Copy settings from {slot}",
        "defaults": "Default values",
        "kit_name": "Kit name",
        "kit_level": "Kit volume",
        "tempo": "Tempo",
        "n_params": "{n} parameters",
        "kit_step": "Kit {kit} · {text}",
        "kits_step": "{text} · {n} kits",
        "quoted": "“{text}”",
        # infobulles
        "unknown_param": "Unidentified parameter (range {lo} to {hi}).",
    },
    "fr": {
        "absolute_path": "chemin absolu attendu : {path}",
        "outside_roots": "hors des dossiers autorisés ({roots}) : {path}",
        "backup_not_found": "sauvegarde introuvable : {path}",
        "unsaved": "des modifications ne sont pas enregistrées",
        "no_backup": "aucune sauvegarde ouverte",
        "token": "jeton absent ou invalide",
        "kit_missing": "kit {num} inexistant",
        "user_samples_only": "seuls les samples utilisateur sont dans la sauvegarde",
        "extension": "l'extension doit être .{kind}",
        "file_exists": "le fichier existe déjà : {path}",
        "nothing_undo": "rien à annuler",
        "nothing_redo": "rien à rétablir",
        "step_missing": "étape {id} absente de l'historique",
        "unknown_preference": "préférence inconnue : {key}",
        "invalid_preference": "valeur invalide pour {key} : {value}",
        "copy_from": "Copie des réglages de {slot}",
        "defaults": "Valeurs par défaut",
        "kit_name": "Nom du kit",
        "kit_level": "Volume du kit",
        "tempo": "Tempo",
        "n_params": "{n} paramètres",
        "kit_step": "Kit {kit} · {text}",
        "kits_step": "{text} · {n} kits",
        "quoted": "« {text} »",
        "unknown_param": "Paramètre non identifié (plage {lo} à {hi}).",
    },
}

_language = ContextVar("language", default=DEFAULT)


def language():
    return _language.get()


def set_language(lang):
    """Langue de la requête en cours ; une langue inconnue donne l'anglais."""
    _language.set(lang if lang in LANGUAGES else DEFAULT)


def from_header(value):
    """« fr », « fr-FR », « fr_FR.UTF-8 », « French_France »… → langue prise
    en charge, sinon anglais."""
    lang = (value or "").strip()[:2].lower()
    return lang if lang in LANGUAGES else DEFAULT


def system_language(env=os.environ):
    """Langue du système : variables LC_ALL, LC_MESSAGES, LANG, sinon locale."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if env.get(var):
            return from_header(env[var])
    return from_header(locale.getlocale()[0])


def startup(preference):
    """Langue hors requête : préférence `language` ("system", "en" ou "fr")."""
    set_language(system_language() if preference == "system" else preference)


def tr(key, /, **params):
    """Texte `key` dans la langue en cours, `params` insérés (Msg traduits)."""
    return MESSAGES[language()][key].format(**{k: str(v) for k, v in params.items()})


class Msg:
    """Texte traduit à l'affichage : str(Msg("kit_step", kit="001", text=…))."""

    def __init__(self, key, /, **params):
        self.key, self.params = key, params

    def __str__(self):
        return tr(self.key, **self.params)
