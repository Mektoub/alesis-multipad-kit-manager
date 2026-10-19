"""Tests de l'API de l'éditeur web (FastAPI), sur la sauvegarde de référence."""
import io
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

from fastapi.testclient import TestClient

import strike_kits as sk
from editor.server import create_app
from tests.outils import REF


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
        self.client = TestClient(create_app(self.root))
        r = self.client.post("/api/open", json={"path": "sauvegardes/Backup001.bkf"})
        self.assertEqual(r.status_code, 200, r.text)
        self.state = r.json()

    def test_liste_des_sauvegardes(self):
        r = self.client.get("/api/backups")
        self.assertIn({"path": "sauvegardes/Backup001.bkf", "size": REF.stat().st_size}, r.json())

    def test_etat_apres_ouverture(self):
        self.assertEqual((self.state["kind"], self.state["dirty"], len(self.state["kits"])), ("bkf", False, 70))
        self.assertIn({"num": "032", "name": "CrazyInLove", "format": "KITC"}, self.state["kits"])

    def test_ouverture_hors_racine_refusee(self):
        for path in ("../x.bkf", "/etc/passwd", "inexistant.bkf"):
            r = self.client.post("/api/open", json={"path": path})
            self.assertEqual(r.status_code, 400, path)

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
        r = self.client.post("/api/save", json={"path": "sauvegardes/Backup002.bkf"})
        self.assertEqual(r.status_code, 200, r.text)
        saved = sk.Backup.open(self.root / "sauvegardes" / "Backup002.bkf")
        self.assertEqual(saved.decode("034")["name"], "Enregistre")
        state = self.client.get("/api/state").json()
        self.assertEqual((state["path"], state["dirty"]), ("sauvegardes/Backup002.bkf", False))
        # fichier existant : confirmation requise
        r = self.client.post("/api/save", json={"path": "sauvegardes/Backup002.bkf"})
        self.assertEqual(r.status_code, 409)
        r = self.client.post("/api/save", json={"path": "sauvegardes/Backup002.bkf", "overwrite": True})
        self.assertEqual(r.status_code, 200)

    def test_enregistrement_refuse(self):
        for path in ("sauvegardes/Backup001.bkf", "../hors.bkf", "sauvegardes/x.fac", "sauvegardes/x.txt"):
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
        self.assertEqual(self.client.post("/api/kits/032/transfer",
                                          json={"target": "040", "mode": "move"}).status_code, 422)

    def test_modification_groupee(self):
        r = self.client.post("/api/kits/033/set", json={"targets": [1, 2, 9], "field": "params.sensitivity", "value": 20})
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
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(Path(tmp)))
            self.assertEqual(client.get("/api/state").json()["path"], None)
            self.assertEqual(client.get("/api/kits/031").status_code, 409)

    def test_descriptions_des_parametres(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = TestClient(create_app(Path(tmp))).get("/api/meta").json()
        pad = {p["name"]: p for p in meta["pad_params"]}
        wave = {p["name"]: p for p in meta["wave_params"]}
        self.assertIn("seuil", pad["threshold"]["description"].lower())
        self.assertIn("non identifié", pad["p13"]["description"])
        for p in meta["pad_params"] + meta["wave_params"]:
            self.assertTrue(p["description"], p["name"])
        self.assertIn("fondu", wave["fade_in"]["description"].lower())
        for key in ("level", "tempo", "play_color", "play_mode", "stop_color", "stop_mode",
                    "sample", "velocity_low", "velocity_high"):
            self.assertTrue(meta["help"][key], key)


    def test_valeurs_par_defaut(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = TestClient(create_app(Path(tmp))).get("/api/meta").json()
        d = meta["defaults"]
        self.assertEqual((d["kit"]["level"], d["kit"]["tempo"]), (100, 120.0))
        self.assertEqual([s["params"]["sensitivity"] for s in d["slots"][:9]], [16] * 6 + [24] * 3)
        self.assertEqual([s["params"]["midi_note"] for s in d["slots"][:3]], [36, 37, 38])
        self.assertEqual(d["slots"][0]["wave_a"]["velocity_high"], 127)

    def test_valeurs_par_defaut_conformes_au_kit_vide(self):
        """La table correspond exactement à un kit vide écrit par l'appareil."""
        with tempfile.TemporaryDirectory() as tmp:
            defaults = TestClient(create_app(Path(tmp))).get("/api/meta").json()["defaults"]
        empty = sk.Backup.open(REF).decode("041")
        self.assertEqual(empty["name"], "Empty")
        self.assertEqual(defaults["kit"], {"level": empty["level"], "tempo": empty["tempo"]})
        for want, got in zip(empty["slots"], defaults["slots"]):
            self.assertEqual(got["params"], want["params"], want["slot"])
            self.assertEqual(got["light"], want["light"], want["slot"])
            for w in ("wave_a", "wave_b"):
                self.assertEqual(got[w], {k: v for k, v in want[w].items() if k != "sample"}, (want["slot"], w))


if __name__ == "__main__":
    unittest.main()
