"""Tests des textes du serveur en anglais et en français : catalogues, langue
de la requête, préférence `language`."""

import re
import unittest

from fastapi.testclient import TestClient

from editor import meta
from editor.i18n import LANGUAGES, MESSAGES, Msg, from_header, set_language, system_language, tr
from editor.preferences import Preferences
from editor.server import create_app
from tests.outils import REF

TOKEN = "secret-de-test"


def placeholders(text):
    return set(re.findall(r"{(\w+)}", text))


class Catalogues(unittest.TestCase):
    def tearDown(self):
        set_language("en")

    def test_memes_cles_et_memes_parametres(self):
        en, fr = MESSAGES["en"], MESSAGES["fr"]
        self.assertEqual(set(en), set(fr))
        for key in en:
            self.assertEqual(placeholders(en[key]), placeholders(fr[key]), key)

    def test_infobulles_dans_les_deux_langues(self):
        for table in (meta.PAD_DESCRIPTIONS, meta.WAVE_DESCRIPTIONS, meta.HELP):
            self.assertEqual(set(table), set(LANGUAGES))
            self.assertEqual(set(table["en"]), set(table["fr"]))

    def test_langue_de_la_requete(self):
        for value, lang in [("fr", "fr"), ("fr-CA", "fr"), ("en-US", "en"), ("de", "en"), (None, "en"), ("", "en")]:
            self.assertEqual(from_header(value), lang, value)

    def test_langue_du_systeme(self):
        self.assertEqual(system_language({"LANG": "fr_FR.UTF-8"}), "fr")
        self.assertEqual(system_language({"LC_ALL": "en_GB.UTF-8", "LANG": "fr_FR.UTF-8"}), "en")
        self.assertEqual(system_language({"LANG": "de_DE.UTF-8"}), "en")

    def test_msg_traduit_a_l_affichage(self):
        msg = Msg("kit_step", kit="001", text=Msg("kit_name"))
        set_language("fr")
        self.assertEqual(str(msg), "Kit 001 · Nom du kit")
        set_language("en")
        self.assertEqual(str(msg), "Kit 001 · Kit name")
        set_language("xx")
        self.assertEqual(tr("no_backup"), "no backup open")


class Api(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(token=TOKEN, open_file=REF, allow=(str(REF.parent),)))
        self.client.headers["X-KitManager-Token"] = TOKEN

    def tearDown(self):
        set_language("en")

    def test_erreurs_et_historique_selon_l_en_tete(self):
        r = self.client.get("/api/kits/999", headers={"X-KitManager-Language": "fr"})
        self.assertEqual(r.json()["detail"], "kit 999 inexistant")
        r = self.client.get("/api/kits/999")  # sans en-tête : anglais
        self.assertEqual(r.json()["detail"], "kit 999 does not exist")
        self.client.post("/api/kits/032/copy", json={"source": 5, "targets": [1, 2], "parts": ["wave_a"]})
        undo = {
            lang: self.client.get("/api/state", headers={"X-KitManager-Language": lang}).json()["history"]["undo"]
            for lang in LANGUAGES
        }
        self.assertEqual(undo, {"en": "Kit 032 · Copy settings from P5", "fr": "Kit 032 · Copie des réglages de P5"})

    def test_infobulles_selon_l_en_tete(self):
        help_ = {
            lang: self.client.get("/api/meta", headers={"X-KitManager-Language": lang}).json()["help"]["name"]
            for lang in LANGUAGES
        }
        self.assertEqual(help_, {"en": meta.HELP["en"]["name"], "fr": meta.HELP["fr"]["name"]})
        # noms des paramètres : en anglais dans les deux langues
        titles = {
            lang: self.client.get("/api/meta", headers={"X-KitManager-Language": lang}).json()["pad_params"][0]["title"]
            for lang in LANGUAGES
        }
        self.assertEqual(titles["en"], titles["fr"])

    def test_preference_language(self):
        self.assertEqual(self.client.get("/api/preferences").json()["language"], "system")
        for value in ("en", "fr", "system"):
            r = self.client.patch("/api/preferences", json={"language": value})
            self.assertEqual((r.status_code, r.json()["language"]), (200, value))
        r = self.client.patch("/api/preferences", json={"language": "de"}, headers={"X-KitManager-Language": "fr"})
        self.assertEqual((r.status_code, r.json()["detail"]), (400, "valeur invalide pour language : 'de'"))

    def test_langue_du_lancement_selon_la_preference(self):
        prefs = Preferences()
        prefs.update({"language": "fr"})
        create_app(token=TOKEN, preferences=prefs)
        self.assertEqual(tr("no_backup"), "aucune sauvegarde ouverte")
