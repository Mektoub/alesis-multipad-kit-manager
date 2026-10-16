"""Tests de strike_kits sur de vraies sauvegardes.

Chemins configurables via STRIKE_BKF, STRIKE_BKF2 et STRIKE_FAC ; les tests sont
ignorés si les fichiers sont absents. Backup002.bkf est la sauvegarde faite par
l'appareil après l'import de « Crazy in Love sample track.wav » et la création
du kit 032 « CrazyInLove » (sample sur le pad 5).
"""
import json
import os
import struct
import wave
import tempfile
import unittest
from pathlib import Path

import strike_kits as sk

ROOT = Path(__file__).resolve().parent / "Strike"
BKF = Path(os.environ.get("STRIKE_BKF", ROOT / "All User Kit And Sample Backup/Backup001.bkf"))
BKF2 = Path(os.environ.get("STRIKE_BKF2", ROOT / "All User Kit And Sample Backup/Backup002.bkf"))
# Backup003 : Control « Click On/Off » et Audio Output « Aux+Phone » sur le pad 9 du kit 032
# (Control déjà présent sur les pads 7–9 du 031).
BKF3 = Path(os.environ.get("STRIKE_BKF3", ROOT / "All User Kit And Sample Backup/Backup003.bkf"))
NEW_WAV = "Crazy in Love sample track.wav"
FAC = Path(os.environ.get("STRIKE_FAC", ROOT / "BackUp/BACKUP00000/STRIKE_BACKUP_KIT.fac"))


def files_of(data):
    return {e.full: data[e.offset:e.offset + e.size] for e in sk.parse_bkf(data)}


def kits_of(data):
    _, entries = sk.parse_container(data)
    return {e.name: data[e.offset:e.offset + e.size] for e in sk.kit_entries(entries)}


class RoundTrip(unittest.TestCase):
    def roundtrip(self, backup):
        with tempfile.TemporaryDirectory() as tmp:
            sk.cmd_export(backup, tmp)
            out = Path(tmp) / ("out" + backup.suffix)
            sk.cmd_import(backup, tmp, out)
            self.assertEqual(backup.read_bytes(), out.read_bytes())

    @unittest.skipUnless(BKF.exists(), "pas de .bkf")
    def test_bkf_identique(self):
        self.roundtrip(BKF)

    @unittest.skipUnless(FAC.exists(), "pas de .fac")
    def test_fac_identique(self):
        self.roundtrip(FAC)


@unittest.skipUnless(FAC.exists(), "pas de .fac")
class Velocite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kit = kits_of(FAC.read_bytes())["005.kit"]

    def test_sample_lu_quelle_que_soit_la_velocite(self):
        # kit d'usine 005, pad 5, wave B : sample 107, vélocité 126–127
        w = sk.decode_kit(self.kit)["slots"][4]["wave_b"]
        self.assertEqual((w["sample"], w["velocity_low"], w["velocity_high"]), (107, 126, 127))

    def test_modification_velocite(self):
        data = sk.decode_kit(self.kit)
        w = data["slots"][4]["wave_b"]
        w["velocity_low"], w["velocity_high"], w["sample"] = 10, 90, 7903
        dec = sk.decode_kit(sk.encode_kit(self.kit, data))["slots"][4]["wave_b"]
        self.assertEqual((dec["sample"], dec["velocity_low"], dec["velocity_high"]), (7903, 10, 90))

    def test_velocite_incoherente_refusee(self):
        data = sk.decode_kit(self.kit)
        for low, high in ((100, 50), (0, 128), (127, 127)):
            w = data["slots"][4]["wave_b"]
            w["velocity_low"], w["velocity_high"] = low, high
            with self.assertRaisesRegex(sk.StrikeError, "velocity"):
                sk.encode_kit(self.kit, data)


@unittest.skipUnless(BKF.exists(), "pas de .bkf")
class Bkf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = BKF.read_bytes()
        cls.tmp = tempfile.TemporaryDirectory()
        sk.cmd_export(BKF, cls.tmp.name)
        cls.dir = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def kit_json(self, num):
        (f,) = (self.dir / "kits").glob(num + "_*.json")
        return f, json.loads(f.read_text(encoding="utf-8"))

    def rebuild(self, num, data):
        f, _ = self.kit_json(num)
        original = f.read_text(encoding="utf-8")
        f.write_text(json.dumps(data), encoding="utf-8")
        try:
            out = self.dir / "out.bkf"
            sk.cmd_import(BKF, self.dir, out)
            return out.read_bytes()
        finally:
            f.write_text(original, encoding="utf-8")

    def test_checksums_kits(self):
        for name, kit in kits_of(self.data).items():
            self.assertEqual(kit[8], sk.kit_checksum(kit), name)

    def test_samples_catalogue(self):
        cat = sk.sample_catalog(self.data, sk.parse_bkf(self.data))
        self.assertEqual(cat[8071][:16], "WIMH sample trac")
        self.assertEqual(cat[7903], "Bongo Small _02")

    def test_kit_whereis_kitc(self):
        _, kit = self.kit_json("031")
        self.assertEqual((kit["format"], kit["name"], kit["tempo"]), ("KITC", "WhereIs", 116.0))
        p1 = kit["slots"][0]
        self.assertEqual(p1["wave_a"]["sample"], 8071)
        self.assertEqual(p1["params"]["midi_note"], 38)
        self.assertEqual(kit["slots"][17]["wave_a"]["sample"], 7903)

    def test_modification_kit_vide(self):
        _, kit = self.kit_json("032")
        kit["name"] = "Mon Kit"
        kit["level"] = 80
        kit["tempo"] = 98.5
        p1 = kit["slots"][0]
        p1["params"]["midi_note"] = 50
        p1["light"]["play_color"] = 9
        p1["wave_a"]["sample"] = 8071
        p1["wave_a"]["params"]["volume"] = 70
        p1["wave_b"]["sample"] = "Bongo Small _02"
        out = self.rebuild("032", kit)

        before, after = kits_of(self.data), kits_of(out)
        self.assertEqual([n for n in before if before[n] != after[n]], ["032.kit"])
        k = after["032.kit"]
        self.assertEqual(k[8], sk.kit_checksum(k))
        dec = sk.decode_kit(k)
        self.assertEqual((dec["name"], dec["level"], dec["tempo"]), ("Mon Kit", 80, 98.5))
        s = dec["slots"][0]
        self.assertEqual(s["params"]["midi_note"], 50)
        self.assertEqual(s["light"]["play_color"], 9)
        self.assertEqual((s["wave_a"]["sample"], s["wave_a"]["params"]["volume"]), (8071, 70))
        self.assertEqual(s["wave_b"]["sample"], 7903)
        self.assertEqual(len(out), len(self.data))
        sk.parse_bkf(out)  # sommes de contrôle du conteneur valides

    def test_valeur_hors_plage(self):
        _, kit = self.kit_json("032")
        kit["slots"][0]["params"]["volume"] = 101
        with self.assertRaisesRegex(sk.StrikeError, "hors plage"):
            self.rebuild("032", kit)

    def test_sample_inconnu(self):
        _, kit = self.kit_json("032")
        kit["slots"][0]["wave_a"]["sample"] = "N'existe pas"
        with self.assertRaisesRegex(sk.StrikeError, "introuvable"):
            self.rebuild("032", kit)

    def test_kitc_modification_pad_masque(self):
        _, kit = self.kit_json("031")
        kit["slots"][0]["params"]["midi_note"] = 60
        kit["slots"][0]["wave_b"]["sample"] = 7903
        out = self.rebuild("031", kit)
        before, after = kits_of(self.data)["031.kit"], kits_of(out)["031.kit"]
        changed = [i for i in range(len(before)) if before[i] != after[i]]
        p1 = sk.SLOT_BASE
        # note MIDI (valeur seule), id du sample de la wave B (2 octets), somme de contrôle
        self.assertEqual(changed, [8, p1 + 0x28 + 2 * 4 + 1, p1 + 0xE0, p1 + 0xE1])
        dec = sk.decode_kit(after)["slots"][0]
        self.assertEqual((dec["params"]["midi_note"], dec["wave_b"]["sample"]), (60, 7903))

    def test_refus_ecraser_original(self):
        with self.assertRaises(sk.StrikeError):
            sk.cmd_import(BKF, self.dir, BKF)


def make_wav(path, sampwidth=2, rate=44100, channels=1, frames=100):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(rate)
        w.writeframes(b"\x01" * frames * sampwidth * channels)


@unittest.skipUnless(BKF.exists() and BKF2.exists(), "pas de Backup001/Backup002")
class AjoutSample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = BKF.read_bytes()
        cls.data2 = BKF2.read_bytes()
        cls.wav = files_of(cls.data2)["WAV/DATA/080/72.wav"]

    def test_reconstruction_conteneur_identique(self):
        for data in (self.data, self.data2):
            self.assertEqual(sk.Bkf.parse(data).serialize(), data)

    def test_ajout_reproduit_l_appareil(self):
        bkf = sk.Bkf.parse(self.data)
        sid = bkf.add_sample("Crazy in Love sample track", self.wav)
        self.assertEqual(sid, 8072)
        out = bkf.serialize()
        got, want = files_of(out), files_of(self.data2)
        self.assertEqual(sorted(got), sorted(want))
        diff = [k for k in want if got[k] != want[k]]
        self.assertEqual(diff, ["KIT/032.kit"])  # kit créé à la main sur l'appareil
        bkf.set_file("KIT/032.kit", want["KIT/032.kit"])
        self.assertEqual(bkf.serialize(), self.data2)

    def test_kit_crazyinlove(self):
        kit = sk.decode_kit(kits_of(self.data2)["032.kit"])
        self.assertEqual((kit["format"], kit["name"]), ("KITC", "CrazyInLove"))
        p5 = kit["slots"][4]
        self.assertEqual((p5["wave_a"]["sample"], p5["params"]["midi_note"]), (8072, 41))

    def test_import_avec_dossier_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sk.cmd_export(BKF, tmp)
            (tmp / "wav").mkdir(exist_ok=True)
            (tmp / "wav" / NEW_WAV).write_bytes(self.wav)
            (f,) = (tmp / "kits").glob("033_*.json")
            kit = json.loads(f.read_text(encoding="utf-8"))
            kit["slots"][4]["wave_a"]["sample"] = "Crazy in Love sample track"
            f.write_text(json.dumps(kit), encoding="utf-8")
            out = tmp / "out.bkf"
            sk.cmd_import(BKF, tmp, out)
            data = out.read_bytes()
            files = files_of(data)
            self.assertEqual(files["WAV/DATA/080/72.wav"], self.wav)
            dec = sk.decode_kit(files["KIT/033.kit"])
            self.assertEqual(dec["slots"][4]["wave_a"]["sample"], 8072)
            # un second import du même dossier n'ajoute pas le sample une deuxième fois
            out2 = tmp / "out2.bkf"
            sk.cmd_import(out, tmp, out2)
            self.assertEqual(out2.read_bytes(), data)

    def test_export_des_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            sk.cmd_export(BKF2, tmp)
            wavs = {p.name: p.read_bytes() for p in (Path(tmp) / "wav").iterdir()}
            self.assertEqual(len(wavs), 34)
            self.assertEqual(wavs[NEW_WAV], self.wav)
            self.assertEqual(wavs["WIMH sample track.wav"], files_of(self.data2)["WAV/DATA/080/71.wav"])

    def test_export_sans_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            sk.cmd_export(BKF2, tmp, wav=False)
            self.assertFalse((Path(tmp) / "wav").exists())

    def test_wav_exporte_puis_renomme_non_reimporte(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sk.cmd_export(BKF2, tmp)
            (tmp / "wav" / NEW_WAV).rename(tmp / "wav" / "Autre nom.wav")
            out = tmp / "out.bkf"
            sk.cmd_import(BKF2, tmp, out)
            self.assertEqual(out.read_bytes(), self.data2)

    def test_nom_de_fichier_assaini(self):
        self.assertEqual(sk.wav_filename('A/B:C*"?<>|'), "A_B_C______.wav")

    def test_wav_refuse_si_pas_16_bits_44k(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kwargs in ({"sampwidth": 1}, {"rate": 48000}, {"sampwidth": 3}):
                p = Path(tmp) / "x.wav"
                make_wav(p, **kwargs)
                with self.assertRaisesRegex(sk.StrikeError, "16 bits"):
                    sk.Bkf.parse(self.data).add_sample("x", p.read_bytes())

    def test_ajout_mono_et_had(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "m.wav"
            make_wav(p, channels=1, frames=10)
            bkf = sk.Bkf.parse(self.data)
            sid = bkf.add_sample("Mon sample avec un nom long", p.read_bytes())
            files = files_of(bkf.serialize())
            had = files["WAV/HEAD/080/72.had"]
            self.assertEqual(sid, 8072)
            self.assertEqual(had[8], sk.kit_checksum(had))
            self.assertEqual((had[0x15], struct.unpack(">I", had[0x20:0x24])[0]), (1, 20))
            self.assertEqual(had[0x40:0x50], b"Mon sample avec ")
            cat = sk.sample_catalog(bkf.serialize(), sk.parse_bkf(bkf.serialize()))
            self.assertEqual(cat[8072], "Mon sample avec un nom long")

    def test_nom_deja_utilise(self):
        bkf = sk.Bkf.parse(self.data)
        with self.assertRaisesRegex(sk.StrikeError, "existe déjà"):
            bkf.add_sample("Kick (27)", self.wav)


@unittest.skipUnless(BKF3.exists(), "pas de Backup003")
class Controle(unittest.TestCase):
    def test_controle_click(self):
        kits = kits_of(BKF3.read_bytes())
        crazy, whereis = sk.decode_kit(kits["032.kit"]), sk.decode_kit(kits["031.kit"])
        self.assertEqual((crazy["tempo"], whereis["tempo"]), (99.0, 116.0))
        # dans les pads masqués des kits KITC, le champ peut être illisible (absent)
        self.assertEqual([s["params"].get("control") for s in crazy["slots"][:9]],
                         [0, 0, None, 0, 0, 0, 0, 0, 3])
        self.assertEqual([s["params"]["control"] for s in whereis["slots"][6:9]], [3, 3, 3])
        # Audio Output du pad 9 passé de Main+Phone (0) à Aux+Phone (4)
        self.assertEqual(crazy["slots"][8]["params"]["audio_output"], 4)


@unittest.skipUnless(BKF2.exists() and FAC.exists(), "pas de Backup002 / .fac")
class BackupEnMemoire(unittest.TestCase):
    def test_kits_et_lecture(self):
        b = sk.Backup.open(BKF2)
        self.assertEqual((b.kind, len(b.kit_numbers()), b.kit_numbers()[0]), ("bkf", 70, "031"))
        self.assertEqual(b.decode("032")["name"], "CrazyInLove")
        self.assertEqual(b.decode("032")["slots"][4]["wave_a"]["_sample_name"], "Crazy in Love sample track")
        self.assertFalse(b.dirty)
        self.assertEqual(b.serialize(), BKF2.read_bytes())

    def test_modification_puis_enregistrement(self):
        b = sk.Backup.open(BKF2)
        kit = b.decode("033")
        kit["name"] = "Nouveau"
        kit["slots"][0]["wave_a"]["sample"] = "Crazy in Love sample track"
        dec = b.update("033", kit)
        self.assertEqual((dec["name"], dec["slots"][0]["wave_a"]["sample"]), ("Nouveau", 8072))
        self.assertTrue(b.dirty)
        relu = sk.Backup(b.serialize())
        self.assertEqual(relu.decode("033")["name"], "Nouveau")
        with self.assertRaises(sk.StrikeError):
            b.update("033", dict(kit, level=500))
        with self.assertRaises(sk.StrikeError):
            b.decode("999")

    def test_samples(self):
        b = sk.Backup.open(BKF2)
        self.assertEqual(len(b.samples()), 8073)
        self.assertEqual(b.user_sample_ids(), sorted(b.user_sample_ids()))
        self.assertIn(8072, b.user_sample_ids())
        self.assertEqual(b.user_wav(8072), files_of(BKF2.read_bytes())["WAV/DATA/080/72.wav"])
        with self.assertRaises(sk.StrikeError):
            b.user_wav(7903)  # sample d'usine : absent de la sauvegarde
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "n.wav"
            make_wav(p)
            sid = b.add_sample("Nouveau sample", p.read_bytes())
        self.assertEqual((sid, b.samples()[sid]), (8073, "Nouveau sample"))
        self.assertIn(sid, b.user_sample_ids())
        self.assertTrue(b.dirty)

    def test_fac(self):
        b = sk.Backup.open(FAC)
        self.assertEqual((b.kind, len(b.kit_numbers())), ("fac", 100))
        self.assertEqual(b.decode("002")["name"], "Cash Money Kit")
        self.assertEqual(b.user_sample_ids(), [])
        with self.assertRaisesRegex(sk.StrikeError, ".bkf"):
            b.add_sample("x", b"")
        self.assertEqual(b.serialize(), FAC.read_bytes())


@unittest.skipUnless(BKF3.exists(), "pas de Backup003")
class RecopiePad(unittest.TestCase):
    def setUp(self):
        self.b = sk.Backup.open(BKF3)

    def test_recopie_complete_sans_note_midi(self):
        kit = self.b.decode("032")  # P5 : sample 8072 ; P9 : Click, Aux+Phone
        skipped = sk.copy_slot_settings(kit, 9, [1, 2], ["params", "light", "wave_a", "wave_b"])
        dec = sk.decode_kit(sk.encode_kit(self.b.get_raw("032"), kit))
        for i in (0, 1):
            self.assertEqual(dec["slots"][i]["params"]["control"], 3)
            self.assertEqual(dec["slots"][i]["params"]["audio_output"], 4)
        self.assertEqual([dec["slots"][i]["params"]["midi_note"] for i in (0, 1)], [36, 37])
        # champs illisibles dans les pads cibles (kit KITC) : signalés, non recopiés
        self.assertEqual(skipped, [(1, "wave_a.params.p09"), (1, "wave_a.params.p10"), (2, "params.p17")])

    def test_recopie_partielle_et_note_midi(self):
        kit = self.b.decode("032")
        sk.copy_slot_settings(kit, 5, [6], ["wave_a"], include_midi_note=True)
        p6 = kit["slots"][5]
        self.assertEqual(p6["wave_a"]["sample"], 8072)
        self.assertEqual(p6["params"]["midi_note"], 42)  # params non copiés
        sk.copy_slot_settings(kit, 5, [6], ["params"], include_midi_note=True)
        self.assertEqual(kit["slots"][5]["params"]["midi_note"], 41)

    def test_champs_illisibles_signales(self):
        kit = self.b.decode("032")  # le pad 3 n'a pas de champ control lisible
        skipped = sk.copy_slot_settings(kit, 9, [3], ["params"])
        self.assertIn((3, "params.control"), skipped)
        self.assertNotIn("control", kit["slots"][2]["params"])

    def test_emplacement_invalide(self):
        kit = self.b.decode("032")
        for src, dests, parts in ((0, [1], ["params"]), (1, [25], ["params"]), (1, [2], ["autre"])):
            with self.assertRaises(sk.StrikeError):
                sk.copy_slot_settings(kit, src, dests, parts)


if __name__ == "__main__":
    unittest.main()
