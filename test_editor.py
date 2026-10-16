"""Tests de l'API de l'éditeur web (FastAPI)."""
import io
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

from fastapi.testclient import TestClient

import strike_kits as sk
from editor.server import create_app

BKF2 = Path(__file__).resolve().parent / "Strike/All User Kit And Sample Backup/Backup002.bkf"


def wav_bytes(frames=100):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x01\x00" * frames)
    return buf.getvalue()


@unittest.skipUnless(BKF2.exists(), "pas de Backup002")
class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        (cls.root / "sauvegardes").mkdir()
        shutil.copy(BKF2, cls.root / "sauvegardes" / "Backup002.bkf")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.client = TestClient(create_app(self.root))
        r = self.client.post("/api/open", json={"path": "sauvegardes/Backup002.bkf"})
        self.assertEqual(r.status_code, 200, r.text)
        self.state = r.json()

    def test_liste_des_sauvegardes(self):
        r = self.client.get("/api/backups")
        self.assertIn({"path": "sauvegardes/Backup002.bkf", "size": BKF2.stat().st_size}, r.json())

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
        self.assertIn({"id": 8072, "name": "Crazy in Love sample track", "user": True}, samples)
        r = self.client.get("/api/samples/8072/wav")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "audio/wav"))
        self.assertEqual(len(r.content), 27128422)
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
        r = self.client.post("/api/save", json={"path": "sauvegardes/Backup003.bkf"})
        self.assertEqual(r.status_code, 200, r.text)
        saved = sk.Backup.open(self.root / "sauvegardes" / "Backup003.bkf")
        self.assertEqual(saved.decode("034")["name"], "Enregistre")
        state = self.client.get("/api/state").json()
        self.assertEqual((state["path"], state["dirty"]), ("sauvegardes/Backup003.bkf", False))
        # fichier existant : confirmation requise
        r = self.client.post("/api/save", json={"path": "sauvegardes/Backup003.bkf"})
        self.assertEqual(r.status_code, 409)
        r = self.client.post("/api/save", json={"path": "sauvegardes/Backup003.bkf", "overwrite": True})
        self.assertEqual(r.status_code, 200)

    def test_enregistrement_refuse(self):
        for path in ("sauvegardes/Backup002.bkf", "../hors.bkf", "sauvegardes/x.fac", "sauvegardes/x.txt"):
            r = self.client.post("/api/save", json={"path": path, "overwrite": True})
            self.assertEqual(r.status_code, 400, path)

    def test_recopie_pad(self):
        r = self.client.post("/api/kits/032/copy", json={"source": 5, "targets": [1, 2], "parts": ["wave_a"]})
        self.assertEqual(r.status_code, 200, r.text)
        kit = r.json()["kit"]
        self.assertEqual([kit["slots"][i]["wave_a"]["sample"] for i in (0, 1)], [8072, 8072])
        self.assertEqual(r.json()["skipped"], [{"slot": 1, "field": "wave_a.params.p09"},
                                               {"slot": 1, "field": "wave_a.params.p10"}])
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


if __name__ == "__main__":
    unittest.main()
