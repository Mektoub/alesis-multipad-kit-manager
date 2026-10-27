"""Tests des préférences de l'utilisateur : fichier, validation, API, effets
sur l'éditeur (fichiers récents, réouverture, taille de l'historique)."""

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from editor.history import History
from editor.preferences import DEFAULTS, FILE_NAME, RECENT_MAX, Preferences, config_dir
from editor.server import create_app
from tests.outils import REF

TOKEN = "secret-de-test"


class Fichier(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.file = Path(tmp.name) / "config" / FILE_NAME

    def test_valeurs_par_defaut_sans_fichier(self):
        self.assertEqual(Preferences(self.file).get(), DEFAULTS)
        self.assertFalse(self.file.exists())  # rien n'est écrit tant que rien ne change

    def test_ecriture_puis_relecture(self):
        Preferences(self.file).update({"theme": "dark", "history_limit": 50})
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8"))["theme"], "dark")
        prefs = Preferences(self.file)
        self.assertEqual((prefs["theme"], prefs["history_limit"], prefs["hide_empty"]), ("dark", 50, True))

    def test_fichier_abime_ou_valeurs_invalides_ignores(self):
        self.file.parent.mkdir()
        self.file.write_text("{pas du json", encoding="utf-8")
        self.assertEqual(Preferences(self.file).get(), DEFAULTS)
        self.file.write_text(json.dumps({"theme": "rose", "hide_empty": False, "inconnue": 1}), encoding="utf-8")
        self.assertEqual(Preferences(self.file).get(), dict(DEFAULTS, hide_empty=False))
        self.file.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(Preferences(self.file).get(), DEFAULTS)

    def test_modification_refusee_en_entier(self):
        prefs = Preferences(self.file)
        for changes in (
            {"theme": "dark", "history_limit": 5},  # sous la borne
            {"history_limit": True},
            {"hide_empty": "oui"},
            {"recent_files": ["relatif.bkf"]},
            {"last_dir": 3},
            {"inconnue": 1},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                prefs.update(changes)
        self.assertEqual(prefs.get(), DEFAULTS)

    def test_fichiers_recents(self):
        prefs = Preferences(self.file)
        files = ["/s/B%02d.bkf" % i for i in range(RECENT_MAX + 2)]
        for f in files:
            prefs.opened(f)
        prefs.opened(files[3])  # déjà présent : remonte en tête, sans doublon
        recent = prefs["recent_files"]
        self.assertEqual(len(recent), RECENT_MAX)
        self.assertEqual(recent[:2], [files[3], files[-1]])
        self.assertEqual(prefs["last_dir"], "/s")

    def test_dossier_non_inscriptible_preferences_en_memoire(self):
        self.file.parent.write_text("un fichier, pas un dossier", encoding="utf-8")
        prefs = Preferences(self.file)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(prefs.update({"theme": "light"})["theme"], "light")
        self.assertIn("Préférences non enregistrées", err.getvalue())


class DossierDeConfiguration(unittest.TestCase):
    def test_par_systeme(self):
        home = Path.home()
        self.assertEqual(config_dir("App", "linux", {}), home / ".config" / "App")
        self.assertEqual(config_dir("App", "linux", {"XDG_CONFIG_HOME": "/x"}), Path("/x/App"))
        self.assertEqual(config_dir("App", "darwin", {}), home / "Library" / "Application Support" / "App")
        self.assertEqual(config_dir("App", "win32", {"APPDATA": "/r"}), Path("/r/App"))
        self.assertEqual(config_dir("App", "linux", {"KITMANAGER_CONFIG": "/c"}), Path("/c"))


class TailleHistorique(unittest.TestCase):
    def test_reduction_oublie_les_plus_anciennes(self):
        h = History(limit=100)
        h.done = [type("E", (), {"id": i})() for i in range(1, 21)]
        h.set_limit(10)
        self.assertEqual([e.id for e in h.done], list(range(11, 21)))
        self.assertEqual((h.base, h.limit), (10, 10))


class Api(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.file = self.root / "Backup001.bkf"
        shutil.copy(REF, self.file)
        self.prefs_file = self.root / "config" / FILE_NAME

    def client(self, **kw):
        app = create_app(token=TOKEN, allow=(str(self.root),), preferences=Preferences(self.prefs_file), **kw)
        client = TestClient(app)
        client.headers["X-KitManager-Token"] = TOKEN
        return client

    def test_lecture_et_modification(self):
        c = self.client()
        self.assertEqual(c.get("/api/preferences").json(), DEFAULTS)
        r = c.patch("/api/preferences", json={"theme": "light", "hide_empty": False})
        self.assertEqual((r.status_code, r.json()["theme"], r.json()["hide_empty"]), (200, "light", False))
        self.assertEqual(self.client().get("/api/preferences").json()["theme"], "light")  # relancement

    def test_valeur_invalide_400(self):
        r = self.client().patch("/api/preferences", json={"theme": "rose"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("theme", r.json()["detail"])

    def test_jeton_exige(self):
        app = create_app(token=TOKEN, preferences=Preferences(self.prefs_file))
        self.assertEqual(TestClient(app).get("/api/preferences").status_code, 403)

    def test_ouverture_et_enregistrer_sous_dans_les_recents(self):
        c = self.client()
        c.post("/api/open", json={"path": str(self.file)})
        copy = self.root / "Backup002.bkf"
        c.post("/api/save", json={"path": str(copy)})
        prefs = c.get("/api/preferences").json()
        self.assertEqual(prefs["recent_files"], [str(copy), str(self.file)])
        self.assertEqual(prefs["last_dir"], str(self.root))

    def test_reouverture_de_la_derniere_sauvegarde(self):
        c = self.client()
        c.post("/api/open", json={"path": str(self.file)})
        self.assertIsNone(self.client().get("/api/state").json()["path"])  # préférence désactivée
        c.patch("/api/preferences", json={"reopen_last": True})
        self.assertEqual(self.client().get("/api/state").json()["path"], str(self.file))
        self.file.unlink()  # fichier disparu : démarrage sans sauvegarde
        self.assertIsNone(self.client().get("/api/state").json()["path"])

    def test_fichier_au_lancement_prioritaire(self):
        other = self.root / "Autre.bkf"
        shutil.copy(REF, other)
        Preferences(self.prefs_file).update({"reopen_last": True, "recent_files": [str(self.file)]})
        state = self.client(open_file=other).get("/api/state").json()
        self.assertEqual(state["path"], str(other))

    def test_taille_de_l_historique(self):
        Preferences(self.prefs_file).update({"history_limit": 10})
        c = self.client()
        c.post("/api/open", json={"path": str(self.file)})

        def edits(n, start):
            for i in range(n):
                kit = c.get("/api/kits/032").json()
                kit["slots"][i % 9]["params"]["volume"] = start + i
                self.assertEqual(c.put("/api/kits/032", json=kit).status_code, 200)

        edits(15, 0)  # emplacements différents d'un envoi à l'autre : pas de fusion
        self.assertEqual(len(c.get("/api/history").json()["entries"]), 10)
        c.patch("/api/preferences", json={"history_limit": 20})
        edits(15, 30)
        self.assertEqual(len(c.get("/api/history").json()["entries"]), 20)
        c.patch("/api/preferences", json={"history_limit": 10})  # réduite : étapes anciennes oubliées
        self.assertEqual(len(c.get("/api/history").json()["entries"]), 10)


if __name__ == "__main__":
    unittest.main()
