"""Tests de l'API de l'éditeur (FastAPI), sur la sauvegarde de référence.

Un seul mode : chaque requête /api/* porte le jeton, les fichiers sont désignés
par chemin absolu (application Electron comme lancement local par ./dev.sh serve).
"""

import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import wave
from pathlib import Path

from fastapi.testclient import TestClient

import strike_kits as sk
from editor.server import create_app, default_roots
from tests.outils import REF

TOKEN = "secret-de-test"


# les dossiers temporaires des tests sont hors de la zone par défaut (dossier personnel)
TMP_ALLOWED = (tempfile.gettempdir(),)


def client_for(open_file=None, token=TOKEN, allow=TMP_ALLOWED):
    """Client de test qui envoie le jeton dans chaque requête."""
    client = TestClient(create_app(token=token, open_file=open_file, allow=allow))
    client.headers["X-KitManager-Token"] = token
    return client


def wav_bytes(frames=100):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x01\x00" * frames)
    return buf.getvalue()


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        (cls.root / "sauvegardes").mkdir()
        shutil.copy(REF, cls.root / "sauvegardes" / "Backup001.bkf")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.file = self.root / "sauvegardes" / "Backup001.bkf"
        self.client = client_for()
        r = self.client.post("/api/open", json={"path": str(self.file)})
        self.assertEqual(r.status_code, 200, r.text)
        self.state = r.json()

    def test_ni_liste_des_sauvegardes_ni_dossier_de_travail(self):
        self.assertEqual(self.client.get("/api/backups").status_code, 404)
        self.assertEqual(self.client.post("/api/root", json={"path": str(self.root)}).status_code, 404)
        self.assertNotIn("root", self.state)

    def test_etat_apres_ouverture(self):
        self.assertEqual((self.state["kind"], self.state["dirty"], len(self.state["kits"])), ("bkf", False, 70))
        self.assertIn({"num": "032", "name": "CrazyInLove", "format": "KITC"}, self.state["kits"])

    def test_ouverture_avec_modifications_non_enregistrees(self):
        kit = self.client.get("/api/kits/033").json()
        kit["name"] = "Pas enregistre"
        self.client.put("/api/kits/033", json=kit)
        r = self.client.post("/api/open", json={"path": str(self.file)})
        self.assertEqual(r.status_code, 409)
        self.assertIn("pas enregistrées", r.json()["detail"])
        self.assertEqual(self.client.get("/api/kits/033").json()["name"], "Pas enregistre")
        r = self.client.post("/api/open", json={"path": str(self.file), "force": True})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["dirty"], self.client.get("/api/kits/033").json()["name"]), (False, "Empty"))

    def test_ouverture_refusee(self):
        for path in ("sauvegardes/Backup001.bkf", "../x.bkf", str(self.root / "inexistant.bkf")):
            r = self.client.post("/api/open", json={"path": path})
            self.assertEqual(r.status_code, 400, path)
        self.assertEqual(self.client.post("/api/open", json={"path": "/etc/passwd"}).status_code, 403)  # hors zone

    def test_lecture_et_modification_kit(self):
        kit = self.client.get("/api/kits/033").json()
        kit["name"] = "Via API"
        kit["slots"][0]["params"]["midi_note"] = 60
        r = self.client.put("/api/kits/033", json=kit)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["name"], r.json()["slots"][0]["params"]["midi_note"]), ("Via API", 60))
        state = self.client.get("/api/state").json()
        self.assertTrue(state["dirty"])
        self.assertIn({"num": "033", "name": "Via API", "format": "KITH"}, state["kits"])

    def test_modification_invalide(self):
        kit = self.client.get("/api/kits/033").json()
        kit["slots"][0]["params"]["volume"] = 500
        r = self.client.put("/api/kits/033", json=kit)
        self.assertEqual(r.status_code, 400)
        self.assertIn("hors plage", r.json()["detail"])
        self.assertEqual(self.client.get("/api/kits/999").status_code, 404)

    def test_samples_et_audio(self):
        samples = self.client.get("/api/samples").json()
        self.assertEqual(len(samples), 8073)
        self.assertIn({"id": 8072, "name": "Sample Stuck", "user": True}, samples)
        r = self.client.get("/api/samples/8072/wav")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "audio/wav"))
        self.assertEqual(len(r.content), 525602)
        self.assertEqual(self.client.get("/api/samples/7903/wav").status_code, 404)

    def test_ajout_sample(self):
        r = self.client.post("/api/samples", files={"file": ("Mon snare.wav", wav_bytes(), "audio/wav")})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"id": 8073, "name": "Mon snare", "user": True})
        r = self.client.post("/api/samples", files={"file": ("Mauvais.wav", b"pas un wav", "audio/wav")})
        self.assertEqual(r.status_code, 400)

    def test_enregistrement(self):
        kit = self.client.get("/api/kits/034").json()
        kit["name"] = "Enregistre"
        self.client.put("/api/kits/034", json=kit)
        target = self.root / "sauvegardes" / "Backup002.bkf"
        r = self.client.post("/api/save", json={"path": str(target)})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(sk.Backup.open(target).decode("034")["name"], "Enregistre")
        state = self.client.get("/api/state").json()
        self.assertEqual((state["path"], state["dirty"]), (str(target), False))
        # autre fichier existant : confirmation requise
        other = self.root / "sauvegardes" / "Autre.bkf"
        shutil.copy(REF, other)
        r = self.client.post("/api/save", json={"path": str(other)})
        self.assertEqual(r.status_code, 409)
        r = self.client.post("/api/save", json={"path": str(other), "overwrite": True})
        self.assertEqual(r.status_code, 200)

    def test_enregistrement_refuse(self):
        folder = self.root / "sauvegardes"
        for path in ("relatif.bkf", "../hors.bkf", str(folder / "x.fac"), str(folder / "x.txt")):
            r = self.client.post("/api/save", json={"path": path, "overwrite": True})
            self.assertEqual(r.status_code, 400, path)

    def test_copie_et_echange_de_kits(self):
        r = self.client.post("/api/kits/032/transfer", json={"target": "040", "mode": "copy"})
        self.assertEqual(r.status_code, 200, r.text)
        names = {k["num"]: k["name"] for k in r.json()["kits"]}
        self.assertEqual((names["032"], names["040"]), ("CrazyInLove", "CrazyInLove"))
        self.assertTrue(r.json()["dirty"])
        r = self.client.post("/api/kits/031/transfer", json={"target": "041", "mode": "swap"})
        names = {k["num"]: k["name"] for k in r.json()["kits"]}
        self.assertEqual((names["031"], names["041"]), ("Empty", "WhereIs"))
        self.assertEqual(self.client.get("/api/kits/041").json()["name"], "WhereIs")
        for body in ({"target": "032", "mode": "copy"}, {"target": "200", "mode": "swap"}):
            self.assertEqual(self.client.post("/api/kits/032/transfer", json=body).status_code, 400)
        self.assertEqual(
            self.client.post("/api/kits/032/transfer", json={"target": "040", "mode": "move"}).status_code, 422
        )

    def test_modification_multi_kits(self):
        body = {"kits": ["031", "032"], "targets": [1, 9], "field": "params.sensitivity", "value": 20}
        r = self.client.post("/api/kits/set", json=body)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["dirty"])
        self.assertEqual(r.json()["skipped"], [])
        for num in ("031", "032"):
            kit = self.client.get("/api/kits/%s" % num).json()
            self.assertEqual([kit["slots"][i]["params"]["sensitivity"] for i in (0, 8)], [20, 20], num)
        body["value"] = 99
        self.assertEqual(self.client.post("/api/kits/set", json=body).status_code, 400)

    def test_modification_groupee(self):
        body = {"targets": [1, 2, 9], "field": "params.sensitivity", "value": 20}
        r = self.client.post("/api/kits/033/set", json=body)
        self.assertEqual(r.status_code, 200, r.text)
        kit = r.json()["kit"]
        self.assertEqual([kit["slots"][i]["params"]["sensitivity"] for i in (0, 1, 2, 8)], [20, 20, 16, 20])
        self.assertEqual(r.json()["skipped"], [])
        self.assertTrue(self.client.get("/api/state").json()["dirty"])
        bad = {"targets": [1], "field": "params.sensitivity", "value": 99}
        self.assertEqual(self.client.post("/api/kits/033/set", json=bad).status_code, 400)
        bad = {"targets": [1], "field": "params.inconnu", "value": 1}
        self.assertEqual(self.client.post("/api/kits/033/set", json=bad).status_code, 400)

    def test_recopie_pad(self):
        r = self.client.post("/api/kits/032/copy", json={"source": 5, "targets": [1, 2], "parts": ["wave_a"]})
        self.assertEqual(r.status_code, 200, r.text)
        kit = r.json()["kit"]
        self.assertEqual([kit["slots"][i]["wave_a"]["sample"] for i in (0, 1)], [8072, 8072])
        self.assertEqual(r.json()["skipped"], [])  # champs recouverts des kits KITC désormais lus
        self.assertTrue(self.client.get("/api/state").json()["dirty"])
        r = self.client.post("/api/kits/032/copy", json={"source": 5, "targets": [30], "parts": ["wave_a"]})
        self.assertEqual(r.status_code, 400)

    def test_meta(self):
        meta = self.client.get("/api/meta").json()
        pad = {p["name"]: p for p in meta["pad_params"]}
        self.assertEqual((pad["volume"]["min"], pad["volume"]["max"]), (0, 100))
        self.assertEqual(pad["control"]["labels"][3], "Click On/Off")
        self.assertEqual(len(meta["colors"]), 17)
        self.assertEqual(len(meta["slots"]), 24)


class SansSauvegarde(unittest.TestCase):
    def test_etat_vide(self):
        client = client_for()
        self.assertEqual(client.get("/api/state").json()["path"], None)
        self.assertEqual(client.get("/api/kits/031").status_code, 409)

    def test_descriptions_des_parametres(self):
        meta = client_for().get("/api/meta").json()
        pad = {p["name"]: p for p in meta["pad_params"]}
        wave = {p["name"]: p for p in meta["wave_params"]}
        self.assertIn("seuil", pad["threshold"]["description"].lower())
        self.assertIn("non identifié", pad["p13"]["description"])
        for p in meta["pad_params"] + meta["wave_params"]:
            self.assertTrue(p["description"], p["name"])
        self.assertIn("fondu", wave["fade_in"]["description"].lower())
        for key in (
            "level",
            "tempo",
            "play_color",
            "play_mode",
            "stop_color",
            "stop_mode",
            "sample",
            "velocity_low",
            "velocity_high",
        ):
            self.assertTrue(meta["help"][key], key)

    def test_valeurs_par_defaut(self):
        meta = client_for().get("/api/meta").json()
        d = meta["defaults"]
        self.assertEqual((d["kit"]["level"], d["kit"]["tempo"]), (100, 120.0))
        self.assertEqual([s["params"]["sensitivity"] for s in d["slots"][:9]], [16] * 6 + [24] * 3)
        self.assertEqual([s["params"]["midi_note"] for s in d["slots"][:3]], [36, 37, 38])
        self.assertEqual(d["slots"][0]["wave_a"]["velocity_high"], 127)

    def test_valeurs_par_defaut_conformes_au_kit_vide(self):
        """La table correspond exactement à un kit vide écrit par l'appareil."""
        defaults = client_for().get("/api/meta").json()["defaults"]
        empty = sk.Backup.open(REF).decode("041")
        self.assertEqual(empty["name"], "Empty")
        self.assertEqual(defaults["kit"], {"level": empty["level"], "tempo": empty["tempo"]})
        for want, got in zip(empty["slots"], defaults["slots"], strict=True):
            self.assertEqual(got["params"], want["params"], want["slot"])
            self.assertEqual(got["light"], want["light"], want["slot"])
            for w in ("wave_a", "wave_b"):
                self.assertEqual(got[w], {k: v for k, v in want[w].items() if k != "sample"}, (want["slot"], w))


class Enregistrement(unittest.TestCase):
    """« Enregistrer » écrit dans le fichier ouvert ; au premier enregistrement de
    chaque session, l'état précédent est copié dans <fichier>.N.bak."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.file = self.root / "Backup001.bkf"
        shutil.copy(REF, self.file)
        self.client = client_for()
        self.open()

    def open(self, force=False):
        r = self.client.post("/api/open", json={"path": str(self.file), "force": force})
        self.assertEqual(r.status_code, 200, r.text)

    def rename(self, name):
        kit = self.client.get("/api/kits/033").json()
        kit["name"] = name
        self.assertEqual(self.client.put("/api/kits/033", json=kit).status_code, 200)

    def test_enregistrer_dans_le_fichier_ouvert(self):
        original = self.file.read_bytes()
        self.rename("Premier")
        r = self.client.post("/api/save", json={})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["path"], r.json()["dirty"]), (str(self.file), False))
        self.assertEqual(sk.Backup.open(self.file).decode("033")["name"], "Premier")
        self.assertEqual((self.root / "Backup001.bkf.1.bak").read_bytes(), original)
        # deuxième enregistrement de la même session : pas de nouvelle copie
        self.rename("Second")
        self.client.post("/api/save", json={})
        self.assertEqual(sorted(p.name for p in self.root.glob("*.bak")), ["Backup001.bkf.1.bak"])
        # nouvelle session : nouvelle copie numérotée, avec l'état précédent
        before = self.file.read_bytes()
        self.open()
        self.rename("Troisieme")
        self.client.post("/api/save", json={})
        self.assertEqual((self.root / "Backup001.bkf.2.bak").read_bytes(), before)
        self.assertEqual((self.root / "Backup001.bkf.1.bak").read_bytes(), original)

    def test_enregistrer_sous_le_meme_nom_equivaut_a_enregistrer(self):
        self.rename("Meme nom")
        r = self.client.post("/api/save", json={"path": str(self.file)})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue((self.root / "Backup001.bkf.1.bak").exists())

    def test_enregistrer_sous_puis_enregistrer(self):
        self.rename("Copie")
        copy = self.root / "Backup002.bkf"
        r = self.client.post("/api/save", json={"path": str(copy)})
        self.assertEqual((r.status_code, r.json()["path"]), (200, str(copy)))
        self.assertEqual(list(self.root.glob("*.bak")), [])
        # « Enregistrer » écrit désormais dans la copie ; elle vient de l'éditeur,
        # ce n'est pas un fichier d'origine : pas de .bak
        self.rename("Copie modifiee")
        self.client.post("/api/save", json={})
        self.assertEqual(sk.Backup.open(self.root / "Backup002.bkf").decode("033")["name"], "Copie modifiee")
        self.assertEqual(sk.Backup.open(self.file).decode("033")["name"], "Empty")
        self.assertEqual(list(self.root.glob("*.bak")), [])

    def test_enregistrer_sans_sauvegarde_ouverte(self):
        self.assertEqual(client_for().post("/api/save", json={}).status_code, 409)


class JetonEtChemins(unittest.TestCase):
    """API réservée au porteur du jeton ; fichiers ouverts et enregistrés par
    chemin absolu, n'importe où."""

    TOKEN = TOKEN

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.a, self.b = base / "a", base / "b"
        self.a.mkdir()
        self.b.mkdir()
        self.file = self.b / "Ma sauvegarde.bkf"
        shutil.copy(REF, self.file)
        self.client = client_for()

    def open(self, path, **kw):
        return self.client.post("/api/open", json=dict(path=str(path), **kw))

    def test_jeton_exige(self):
        anonymous = TestClient(create_app(token=self.TOKEN))
        for headers in ({}, {"X-KitManager-Token": "faux"}):
            r = anonymous.get("/api/state", headers=headers)
            self.assertEqual(r.status_code, 403, headers)
        self.assertEqual(self.client.get("/api/state").status_code, 200)

    def test_ouvrir_par_chemin_absolu(self):
        r = self.open(self.file)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["path"], r.json()["kind"]), (str(self.file), "bkf"))
        for path in ("Ma sauvegarde.bkf", self.b / "inexistant.bkf", self.b):
            self.assertEqual(self.open(path).status_code, 400, path)

    def test_jeton_obligatoire_a_la_creation(self):
        for token in (None, ""):
            with self.assertRaises(ValueError):
                create_app(token=token)

    def test_fichier_ouvert_au_demarrage(self):
        r = client_for(open_file=self.file).get("/api/state")
        self.assertEqual((r.json()["path"], r.json()["dirty"], len(r.json()["kits"])), (str(self.file), False, 70))
        for bad in (self.b / "inexistant.bkf", self.b, Path("relatif.bkf")):
            with self.assertRaises(sk.StrikeError, msg=bad):
                create_app(token=TOKEN, open_file=bad, allow=TMP_ALLOWED)

    def test_enregistrer_et_enregistrer_sous(self):
        self.open(self.file)
        kit = self.client.get("/api/kits/033").json()
        kit["name"] = "Bureau"
        self.client.put("/api/kits/033", json=kit)
        # « Enregistrer sous » un autre fichier existant : confirmation requise
        existing = self.a / "Existant.bkf"
        shutil.copy(REF, existing)
        self.assertEqual(self.client.post("/api/save", json={"path": str(existing)}).status_code, 409)
        # « Enregistrer sous » ailleurs
        target = self.a / "Copie.bkf"
        r = self.client.post("/api/save", json={"path": str(target)})
        self.assertEqual((r.status_code, r.json()["path"]), (200, str(target)))
        r = self.client.post("/api/save", json={"path": str(existing), "overwrite": True})
        self.assertEqual((r.status_code, r.json()["path"]), (200, str(existing)))
        r = self.client.post("/api/save", json={"path": str(target), "overwrite": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.post("/api/save", json={"path": "relatif.bkf"}).status_code, 400)
        # « Enregistrer » : écrit dans la copie (pas de .bak : ce n'est pas un original)
        r = self.client.post("/api/save", json={})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(list(self.a.glob("*.bak")), [])
        self.assertEqual(sk.Backup.open(target).decode("033")["name"], "Bureau")
        # « Enregistrer » sur le fichier d'origine ouvert : .bak dans son dossier
        self.open(self.file, force=True)
        self.client.put("/api/kits/033", json=kit)
        self.client.post("/api/save", json={})
        self.assertTrue((self.b / "Ma sauvegarde.bkf.1.bak").exists())

    def test_ouvrir_avec_modifications_non_enregistrees(self):
        self.open(self.file)
        kit = self.client.get("/api/kits/033").json()
        kit["name"] = "Pas enregistre"
        self.client.put("/api/kits/033", json=kit)
        self.assertEqual(self.open(self.file).status_code, 409)
        self.assertEqual(self.open(self.file, force=True).status_code, 200)


class DossiersAutorises(unittest.TestCase):
    """Le serveur n'ouvre et n'écrit que dans le dossier personnel, les supports
    amovibles de l'utilisateur (/media/<utilisateur>, /run/media/<utilisateur>) et
    les dossiers ajoutés (--allow), chemins résolus (liens symboliques compris)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        self.inside, self.outside = base / "autorise", base / "interdit"
        self.inside.mkdir()
        self.outside.mkdir()
        self.file = self.inside / "B.bkf"
        shutil.copy(REF, self.file)
        shutil.copy(REF, self.outside / "B.bkf")
        self.client = client_for(allow=(self.inside,))

    def post(self, url, path, **kw):
        return self.client.post(url, json=dict(path=str(path), **kw))

    def test_zone_par_defaut(self):
        import getpass

        user = getpass.getuser()
        self.assertEqual(default_roots(), [Path.home(), Path("/media") / user, Path("/run/media") / user])

    def test_ouvrir_hors_zone_refuse(self):
        r = self.post("/api/open", self.outside / "B.bkf")
        self.assertEqual(r.status_code, 403, r.text)
        self.assertIn("hors des dossiers autorisés", r.json()["detail"])
        self.assertEqual(self.post("/api/open", self.file).status_code, 200)

    def test_dossier_personnel_autorise_par_defaut(self):
        self.assertEqual(self.post("/api/open", REF).status_code, 200)  # le dépôt est dans le dossier personnel

    def test_enregistrer_sous_hors_zone_refuse(self):
        self.post("/api/open", self.file)
        target = self.outside / "Nouveau.bkf"
        r = self.post("/api/save", target)
        self.assertEqual(r.status_code, 403, r.text)
        self.assertFalse(target.exists())
        self.assertEqual(self.post("/api/save", self.inside / "Nouveau.bkf").status_code, 200)

    def test_lien_symbolique_vers_l_exterieur_refuse(self):
        link = self.inside / "lien"
        link.symlink_to(self.outside, target_is_directory=True)
        self.assertEqual(self.post("/api/open", link / "B.bkf").status_code, 403)
        self.post("/api/open", self.file)
        self.assertEqual(self.post("/api/save", link / "Nouveau.bkf").status_code, 403)
        self.assertFalse((self.outside / "Nouveau.bkf").exists())

    def test_prefixe_proche_refuse(self):
        """/…/autorise-bis n'est pas dans /…/autorise."""
        twin = self.inside.with_name("autorise-bis")
        twin.mkdir()
        shutil.copy(REF, twin / "B.bkf")
        self.assertEqual(self.post("/api/open", twin / "B.bkf").status_code, 403)

    def test_fichier_au_demarrage_hors_zone(self):
        with self.assertRaises(sk.StrikeError) as ctx:
            create_app(token=TOKEN, open_file=self.outside / "B.bkf", allow=(self.inside,))
        self.assertIn("hors des dossiers autorisés", str(ctx.exception))


class Lancement(unittest.TestCase):
    def test_interface_absente_avertissement_sur_stderr(self):
        """Sans interface construite (cas de la CI), l'avertissement part sur la sortie
        d'erreur : la sortie standard ne contient que les lignes utiles."""
        import contextlib
        from unittest import mock

        import editor.__main__ as launcher

        out, err = io.StringIO(), io.StringIO()
        fake_run = lambda app, host, port, on_ready: on_ready(None, 4321)  # noqa: E731
        argv = ["editor", "--port", "0", "--no-browser", "--open", str(REF)]
        with (
            mock.patch.object(launcher, "WEB_DIST", Path(REF.parent) / "absent"),
            mock.patch.object(launcher, "run", fake_run),
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(os.environ, {}, clear=False),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            os.environ.pop("KITMANAGER_TOKEN", None)
            launcher.main()
        self.assertIn("Interface non construite", err.getvalue())
        self.assertTrue(
            out.getvalue().startswith("Éditeur disponible sur http://127.0.0.1:4321/#token="), out.getvalue()
        )
        self.assertNotIn("Interface non construite", out.getvalue())

    def start_local(self, *args):
        """Lancement local (sans KITMANAGER_TOKEN), comme ./dev.sh serve."""
        project = Path(__file__).resolve().parent.parent
        env = {k: v for k, v in os.environ.items() if k != "KITMANAGER_TOKEN"}
        return subprocess.Popen(
            [sys.executable, "-m", "editor", "--port", "0", "--no-browser", *args],
            cwd=project,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_mode_local_jeton_dans_l_adresse(self):
        """En local, un jeton est créé et donné dans l'adresse ; le fichier est déjà ouvert."""
        p = self.start_local("--open", str(REF))
        try:
            line = p.stdout.readline()
            # jeton de secrets.token_urlsafe : lettres, chiffres, « - » et « _ »
            m = re.match(r"Éditeur disponible sur (http://127\.0\.0\.1:\d+/)#token=([\w-]+)$", line)
            self.assertTrue(m, line)
            base, token = m.groups()
            req = urllib.request.Request(base + "api/state", headers={"X-KitManager-Token": token})
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(json.load(resp)["path"], str(REF))
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(base + "api/state", timeout=5)
            self.assertEqual(ctx.exception.code, 403)
        finally:
            p.terminate()
            p.communicate(timeout=15)

    def test_fichier_introuvable_au_lancement(self):
        p = self.start_local("--open", str(REF.parent / "inexistant.bkf"))
        out, err = p.communicate(timeout=15)
        self.assertEqual(p.returncode, 2, err)
        self.assertIn("inexistant.bkf", err)
        self.assertNotIn("Traceback", err)

    def test_option_allow(self):
        """--allow DOSSIER ajoute un dossier à la zone autorisée ; sans lui, une
        sauvegarde hors zone est refusée dès le lancement."""
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "B.bkf"
            shutil.copy(REF, file)
            p = self.start_local("--open", str(file))
            out, err = p.communicate(timeout=15)
            self.assertEqual(p.returncode, 2, err)
            self.assertIn("hors des dossiers autorisés", err)
            p = self.start_local("--open", str(file), "--allow", tmp)
            try:
                self.assertIn("Éditeur disponible", p.stdout.readline())
            finally:
                p.terminate()
                p.communicate(timeout=15)

    def test_arret_propre_par_ctrl_c(self):
        """Ctrl+C (SIGINT) arrête l'éditeur sans trace d'erreur, avec le code 0."""
        p = self.start_local("--open", str(REF))
        try:
            self.assertIn("Éditeur disponible", p.stdout.readline())
            p.send_signal(signal.SIGINT)
            out, err = p.communicate(timeout=15)
        finally:
            if p.poll() is None:
                p.kill()
        self.assertNotIn("Traceback", err)
        self.assertEqual(p.returncode, 0, err)
        self.assertIn("arrêté", out)

    def test_port_libre_annonce_quand_pret(self):
        from editor.__main__ import ready_line, run

        app = create_app(token="t")
        ready, servers = threading.Event(), []
        announced = {}

        def on_ready(server, port):
            servers.append(server)
            announced.update(json.loads(ready_line(port)))
            ready.set()

        thread = threading.Thread(target=run, args=(app, "127.0.0.1", 0, on_ready), daemon=True)
        thread.start()
        self.assertTrue(ready.wait(10), "serveur non prêt")
        try:
            self.assertTrue(announced["ready"])
            self.assertGreater(announced["port"], 0)
            req = urllib.request.Request(
                "http://127.0.0.1:%d/api/state" % announced["port"], headers={"X-KitManager-Token": "t"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(json.load(resp)["path"], None)
        finally:
            servers[0].should_exit = True
            thread.join(10)

    def test_arret_quand_l_entree_standard_se_ferme(self):
        """--watch-stdin : le serveur s'arrête quand l'application qui l'a lancé
        ferme son entrée standard, ou disparaît (plantage compris)."""
        project = Path(__file__).resolve().parent.parent
        p = subprocess.Popen(
            [sys.executable, "-m", "editor", "--port", "0", "--watch-stdin"],
            cwd=project,
            env={**os.environ, "KITMANAGER_TOKEN": "t"},
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            self.assertTrue(json.loads(p.stdout.readline())["ready"])
            p.stdin.close()
            out, err = p.communicate(timeout=15)
        finally:
            if p.poll() is None:
                p.kill()
        self.assertEqual(p.returncode, 0, err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
