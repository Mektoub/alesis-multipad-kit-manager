"""Tests de strike_kits sur la sauvegarde de référence tests/ressources/Backup001.bkf.

Contenu de la référence (voir construire_reference.py) :
  - 031 « WhereIs » (KITC) : P1 sample 8071, note 38 ; Control Click sur P7–P9 ;
  - 032 « CrazyInLove » (KITC, créé sur l'appareil) : P5 sample 8072 ; P9 Click, Aux+Phone ;
  - 040 « Ham & Beans » (kit d'usine) : P5 wave B sample 107, vélocité 126–127 ;
  - autres kits vides (KITH) ; samples utilisateur 8071 « SnareUF » et 8072 « Sample Stuck ».
"""

import json
import struct
import tempfile
import unittest
from pathlib import Path

import strike_kits as sk
from tests.outils import REF, files_of, kits_of, make_wav, ref_fac


class RoundTrip(unittest.TestCase):
    def roundtrip(self, backup):
        with tempfile.TemporaryDirectory() as tmp:
            sk.cmd_export(backup, tmp)
            out = Path(tmp) / ("out" + backup.suffix)
            sk.cmd_import(backup, tmp, out)
            self.assertEqual(backup.read_bytes(), out.read_bytes())

    def test_bkf_identique(self):
        self.roundtrip(REF)

    def test_fac_identique(self):
        with tempfile.TemporaryDirectory() as tmp:
            fac = Path(tmp) / "STRIKE_BACKUP_KIT.fac"
            fac.write_bytes(ref_fac())
            self.roundtrip(fac)


class Velocite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kit = kits_of(REF.read_bytes())["040.kit"]

    def test_sample_lu_quelle_que_soit_la_velocite(self):
        # kit d'usine « Ham & Beans », pad 5, wave B : sample 107, vélocité 126–127
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


class Bkf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = REF.read_bytes()
        cls.tmp = tempfile.TemporaryDirectory()
        sk.cmd_export(REF, cls.tmp.name)
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
            sk.cmd_import(REF, self.dir, out)
            return out.read_bytes()
        finally:
            f.write_text(original, encoding="utf-8")

    def test_checksums_kits(self):
        for name, kit in kits_of(self.data).items():
            self.assertEqual(kit[8], sk.kit_checksum(kit), name)

    def test_samples_catalogue(self):
        cat = sk.sample_catalog(self.data, sk.parse_bkf(self.data))
        self.assertEqual((cat[8071], cat[8072]), ("SnareUF", "Sample Stuck"))
        self.assertEqual(cat[7903], "Bongo Small _02")

    def test_kit_whereis_kitc(self):
        _, kit = self.kit_json("031")
        self.assertEqual((kit["format"], kit["name"], kit["tempo"]), ("KITC", "WhereIs", 116.0))
        p1 = kit["slots"][0]
        self.assertEqual(p1["wave_a"]["sample"], 8071)
        self.assertEqual(p1["params"]["midi_note"], 38)
        self.assertEqual(kit["slots"][17]["wave_a"]["sample"], 7903)

    def test_modification_kit_vide(self):
        _, kit = self.kit_json("033")
        kit["name"] = "Mon Kit"
        kit["level"] = 80
        kit["tempo"] = 98.5
        p1 = kit["slots"][0]
        p1["params"]["midi_note"] = 50
        p1["light"]["play_color"] = 9
        p1["wave_a"]["sample"] = 8071
        p1["wave_a"]["params"]["volume"] = 70
        p1["wave_b"]["sample"] = "Bongo Small _02"
        out = self.rebuild("033", kit)

        before, after = kits_of(self.data), kits_of(out)
        self.assertEqual([n for n in before if before[n] != after[n]], ["033.kit"])
        k = after["033.kit"]
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
        _, kit = self.kit_json("033")
        kit["slots"][0]["params"]["volume"] = 101
        with self.assertRaisesRegex(sk.StrikeError, "hors plage"):
            self.rebuild("033", kit)

    def test_sample_inconnu(self):
        _, kit = self.kit_json("033")
        kit["slots"][0]["wave_a"]["sample"] = "N'existe pas"
        with self.assertRaisesRegex(sk.StrikeError, "introuvable"):
            self.rebuild("033", kit)

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
            sk.cmd_import(REF, self.dir, REF)


class AjoutSample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = REF.read_bytes()
        cls.wav = files_of(cls.data)["WAV/DATA/080/72.wav"]

    def new_wav(self, tmp, name="Nouveau son.wav", **kwargs):
        p = Path(tmp) / name
        make_wav(p, **kwargs)
        return p

    def test_reconstruction_conteneur_identique(self):
        self.assertEqual(sk.Bkf.parse(self.data).serialize(), self.data)

    def test_retrait_puis_ajout_identique(self):
        # le dernier sample de la référence (8072) a été écrit par add_sample ;
        # le retirer puis le rajouter redonne la sauvegarde à l'identique
        bkf = sk.Bkf.parse(self.data)
        self.assertEqual(bkf.remove_last_sample(), 8072)
        self.assertNotIn("WAV/DATA/080/72.wav", [r.full for r in bkf.records])
        self.assertEqual(bkf.add_sample("Sample Stuck", self.wav), 8072)
        self.assertEqual(bkf.serialize(), self.data)

    def test_regles_de_l_ajout(self):
        """Règles relevées en comparant deux sauvegardes faites par l'appareil avant
        et après l'import d'un WAV (docs/format-bkf.md, « Ajout d'un sample »)."""

        def lst(files, name):
            data = files["WAV/LIST/" + name]
            return data, struct.unpack(">H", data[0x0A:0x0C])[0]

        with tempfile.TemporaryDirectory() as tmp:
            wav = self.new_wav(tmp).read_bytes()
        bkf = sk.Bkf.parse(self.data)
        before = files_of(self.data)
        sid = bkf.add_sample("Nouveau son", wav)
        out = bkf.serialize()
        after = files_of(out)
        self.assertEqual(sid, 8073)
        # en-tête : nombre de fichiers + 2, nombre de WAV + 1
        self.assertEqual(
            struct.unpack("<2I", out[0x10:0x18]),
            (struct.unpack("<I", self.data[0x10:0x14])[0] + 2, struct.unpack("<I", self.data[0x14:0x18])[0] + 1),
        )
        # .wav copié tel quel, .had et .wav à la suite des autres
        self.assertEqual(after["WAV/DATA/080/73.wav"], wav)
        names = [r.full for r in bkf.records]
        self.assertEqual(names[-1], "WAV/DATA/080/73.wav")
        self.assertEqual(names[names.index("WAV/HEAD/080/73.had") - 1], "WAV/HEAD/080/72.had")
        # Wave_list : entrée 8073 libérée du drapeau 0x8000
        wl, n = lst(after, "Wave_list.lst")
        self.assertEqual((n, struct.unpack(">H", wl[0x20 + 8 * sid : 0x22 + 8 * sid])[0]), (8074, sid))
        # sort_num : (rang, id) ajouté avant la paire nulle finale
        num, n = lst(after, "wave_list_sort_num.lst")
        self.assertEqual(struct.unpack(">4H", num[0x20 + 4 * (n - 1) : 0x28 + 4 * (n - 1)]), (8073, sid, 0, 0))
        # sort_name : insertion alphabétique, compteur des entrées suivantes + 1
        old, _ = lst(before, "wave_list_sort_name.lst")
        new, n = lst(after, "wave_list_sort_name.lst")
        pos = next(k for k in range(n) if struct.unpack(">H", new[0x22 + 0x90 * k : 0x24 + 0x90 * k])[0] == sid)
        o = 0x20 + 0x90 * pos
        self.assertEqual(struct.unpack(">3H", new[o : o + 6]), (pos, sid, len("Nouveau son") + 4))
        self.assertEqual(new[o + 0x10 : o + 0x1B], b"Nouveau son")
        self.assertLess(new[o - 0x80 : o].split(b"\0")[0].lower(), b"nouveau son")
        follow = struct.unpack(">H", new[o + 0x90 : o + 0x92])[0]
        self.assertEqual(follow, struct.unpack(">H", old[o : o + 2])[0] + 1)
        # groupe New Sample : (n, id) ajouté en fin
        grp, _ = lst(after, "wave_list_sort_group.lst")
        i = grp.index(b"New Sample") - 8
        members = struct.unpack(">H", grp[i + 1 : i + 3])[0]
        end = i + 0x18 + 4 * members
        self.assertEqual(struct.unpack(">2H", grp[end - 4 : end]), (members - 1, sid))
        # SortSize : (id, taille) inséré par taille croissante, en tête car le plus petit
        size, n = lst(after, "WaveList_User_SortSize.lst")
        self.assertEqual((n, struct.unpack(">2I", size[0x20:0x28])), (35, (sid, len(wav))))
        self.assertEqual(len(size), len(before["WAV/LIST/WaveList_User_SortSize.lst"]))

    def test_kit_crazyinlove(self):
        kit = sk.decode_kit(kits_of(self.data)["032.kit"])
        self.assertEqual((kit["format"], kit["name"]), ("KITC", "CrazyInLove"))
        p5 = kit["slots"][4]
        self.assertEqual((p5["wave_a"]["sample"], p5["params"]["midi_note"]), (8072, 41))

    def test_import_avec_dossier_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sk.cmd_export(REF, tmp)
            wav = self.new_wav(tmp / "wav")
            (f,) = (tmp / "kits").glob("033_*.json")
            kit = json.loads(f.read_text(encoding="utf-8"))
            kit["slots"][4]["wave_a"]["sample"] = "Nouveau son"
            f.write_text(json.dumps(kit), encoding="utf-8")
            out = tmp / "out.bkf"
            sk.cmd_import(REF, tmp, out)
            data = out.read_bytes()
            files = files_of(data)
            self.assertEqual(files["WAV/DATA/080/73.wav"], wav.read_bytes())
            dec = sk.decode_kit(files["KIT/033.kit"])
            self.assertEqual(dec["slots"][4]["wave_a"]["sample"], 8073)
            # un second import du même dossier n'ajoute pas le sample une deuxième fois
            out2 = tmp / "out2.bkf"
            sk.cmd_import(out, tmp, out2)
            self.assertEqual(out2.read_bytes(), data)

    def test_export_des_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            sk.cmd_export(REF, tmp)
            wavs = {p.name: p.read_bytes() for p in (Path(tmp) / "wav").iterdir()}
            self.assertEqual(len(wavs), 34)
            self.assertEqual(wavs["Sample Stuck.wav"], self.wav)
            self.assertEqual(wavs["SnareUF.wav"], files_of(self.data)["WAV/DATA/080/71.wav"])

    def test_export_sans_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            sk.cmd_export(REF, tmp, wav=False)
            self.assertFalse((Path(tmp) / "wav").exists())

    def test_wav_exporte_puis_renomme_non_reimporte(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sk.cmd_export(REF, tmp)
            (tmp / "wav" / "Sample Stuck.wav").rename(tmp / "wav" / "Autre nom.wav")
            out = tmp / "out.bkf"
            sk.cmd_import(REF, tmp, out)
            self.assertEqual(out.read_bytes(), self.data)

    def test_nom_de_fichier_assaini(self):
        self.assertEqual(sk.wav_filename('A/B:C*"?<>|'), "A_B_C______.wav")

    def test_wav_refuse_si_pas_16_bits_44k(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kwargs in ({"sampwidth": 1}, {"rate": 48000}, {"sampwidth": 3}):
                p = self.new_wav(tmp, "x.wav", **kwargs)
                with self.assertRaisesRegex(sk.StrikeError, "16 bits"):
                    sk.Bkf.parse(self.data).add_sample("x", p.read_bytes())

    def test_ajout_mono_et_had(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.new_wav(tmp, "m.wav", channels=1, frames=10)
            bkf = sk.Bkf.parse(self.data)
            sid = bkf.add_sample("Mon sample avec un nom long", p.read_bytes())
            files = files_of(bkf.serialize())
            had = files["WAV/HEAD/080/73.had"]
            self.assertEqual(sid, 8073)
            self.assertEqual(had[8], sk.kit_checksum(had))
            self.assertEqual((had[0x15], struct.unpack(">I", had[0x20:0x24])[0]), (1, 20))
            self.assertEqual(had[0x40:0x50], b"Mon sample avec ")
            cat = sk.sample_catalog(bkf.serialize(), sk.parse_bkf(bkf.serialize()))
            self.assertEqual(cat[8073], "Mon sample avec un nom long")

    def test_nom_deja_utilise(self):
        bkf = sk.Bkf.parse(self.data)
        with self.assertRaisesRegex(sk.StrikeError, "existe déjà"):
            bkf.add_sample("Kick (27)", self.wav)

    def test_retrait_impossible_si_aucun_sample(self):
        bkf = sk.Bkf.parse(self.data)
        wl = bytearray(bkf.get_file("WAV/LIST/Wave_list.lst"))
        wl[0x0A:0x0C] = b"\x00\x00"
        bkf.set_file("WAV/LIST/Wave_list.lst", wl)
        with self.assertRaises(sk.StrikeError):
            bkf.remove_last_sample()


class KitcChampsRecouverts(unittest.TestCase):
    """Dans les pads 1–8 des kits KITC, des structures recouvrent id/min/max de
    certains enregistrements, mais l'octet valeur reste à sa place."""

    @classmethod
    def setUpClass(cls):
        cls.kits = kits_of(REF.read_bytes())

    def test_tous_les_champs_sur_tous_les_pads(self):
        pad = [sk.param_name(sk.PAD_PARAMS, r) for r, _, _ in sk.PAD_LAYOUT] + list(sk.PAD_FIELDS)
        wave = [sk.param_name(sk.WAVE_PARAMS, r) for r, _, _ in sk.WAVE_LAYOUT]
        for name in ("031.kit", "032.kit"):
            for s in sk.decode_kit(self.kits[name])["slots"]:
                self.assertEqual(list(s["params"]), pad, (name, s["slot"]))
                for w in ("wave_a", "wave_b"):
                    self.assertEqual(list(s[w]["params"]), wave, (name, s["slot"], w))

    def test_valeurs_recouvertes(self):
        p4 = sk.decode_kit(self.kits["032.kit"])["slots"][3]["params"]
        self.assertEqual((p4["pan"], p4["midi_note"]), (15, 40))

    def test_modification_valeur_recouverte(self):
        raw = self.kits["032.kit"]
        data = sk.decode_kit(raw)
        data["slots"][3]["params"]["midi_note"] = 52
        new = sk.encode_kit(raw, data)
        changed = [i for i in range(len(raw)) if raw[i] != new[i]]
        off = sk.SLOT_BASE + 3 * sk.SLOT_SIZE + sk.PAD_RECORDS + 2 * 4 + 1
        self.assertEqual(changed, [8, off])
        self.assertEqual(sk.decode_kit(new)["slots"][3]["params"]["midi_note"], 52)


class Controle(unittest.TestCase):
    def test_controle_click(self):
        kits = kits_of(REF.read_bytes())
        crazy, whereis = sk.decode_kit(kits["032.kit"]), sk.decode_kit(kits["031.kit"])
        self.assertEqual((crazy["tempo"], whereis["tempo"]), (99.0, 116.0))
        self.assertEqual([s["params"].get("control") for s in crazy["slots"][:9]], [0] * 8 + [3])
        self.assertEqual([s["params"]["control"] for s in whereis["slots"][6:9]], [3, 3, 3])
        # Audio Output du pad 9 passé de Main+Phone (0) à Aux+Phone (4)
        self.assertEqual(crazy["slots"][8]["params"]["audio_output"], 4)


class ParametresIdentifies(unittest.TestCase):
    """Réglages faits sur l'appareil à partir des kits 031 et 032 de la référence
    (identiques à ceux de la sauvegarde de départ) : octets changés dans la
    sauvegarde écrite par l'appareil, somme de contrôle (0x08) comprise."""

    DEVICE = {
        "031.kit": {0x08: 95, 0x276: 0, 0x3F9: 4, 0x731: 5, 0x8BD: 50, 0x9F2: 3},
        "032.kit": {0x08: 88, 0x2E2: 50, 0x771: 9, 0x7D1: 9, 0x8FD: 0, 0xA63: 100},
    }

    @classmethod
    def setUpClass(cls):
        cls.kits = kits_of(REF.read_bytes())

    def changed(self, name, edit):
        raw = self.kits[name]
        data = sk.decode_kit(raw)
        edit(data["slots"])
        new = sk.encode_kit(raw, data)
        return {i: new[i] for i in range(len(raw)) if raw[i] != new[i]}

    def test_kit_1_comme_l_appareil(self):
        def edit(s):
            s[3]["params"]["curve"] = 5  # Loud
            s[4]["params"]["kit_fx_level"] = 50
            s[5]["light"]["play_beat"] = 3  # 1/16
            s[0]["light"]["stop_beat"] = 0  # 1/2
            s[1]["params"]["sync_mode"] = 4  # HiHat

        self.assertEqual(self.changed("031.kit", edit), self.DEVICE["031.kit"])

    def test_kit_2_comme_l_appareil(self):
        def edit(s):
            for w in ("wave_a", "wave_b"):
                s[3][w]["params"]["playback_mode"] = 9  # FS4
            s[4]["wave_a"]["params"]["poly_mono"] = 0  # Mono
            s[5]["wave_a"]["velocity_high"] = 100
            s[0]["wave_a"]["velocity_low"] = 50

        self.assertEqual(self.changed("032.kit", edit), self.DEVICE["032.kit"])

    def test_valeurs_lues(self):
        s = sk.decode_kit(self.kits["031.kit"])["slots"]
        self.assertEqual((s[4]["params"]["kit_fx_level"], s[3]["params"]["curve"]), (40, 0))
        self.assertEqual((s[0]["light"]["play_beat"], s[0]["light"]["stop_beat"]), (1, 1))
        self.assertEqual(s[1]["params"]["sync_mode"], 0)
        w = sk.decode_kit(self.kits["032.kit"])["slots"][4]["wave_a"]["params"]
        self.assertEqual((w["playback_mode"], w["poly_mono"]), (0, 1))

    def test_plages(self):
        # Playback Mode : l'enregistrement annonce 0–5, l'appareil écrit 9 (FS4)
        for name, edit in (
            ("playback_mode", lambda s: s[0]["wave_a"]["params"].update(playback_mode=10)),
            ("sync_mode", lambda s: s[0]["params"].update(sync_mode=5)),
            ("play_beat", lambda s: s[0]["light"].update(play_beat=4)),
        ):
            with self.assertRaisesRegex(sk.StrikeError, "hors plage", msg=name):
                self.changed("033.kit", edit)

    def test_modification_groupee(self):
        b = sk.Backup.open(REF)
        for field in ("params.sync_mode", "light.play_beat", "light.stop_beat", "wave_a.params.playback_mode"):
            kit, skipped = b.set_slots("033", [1, 2], field, 3)
            self.assertEqual(skipped, [], field)
            node = kit["slots"][1]
            for key in field.split("."):
                node = node[key]
            self.assertEqual(node, 3, field)


class BackupEnMemoire(unittest.TestCase):
    def test_kits_et_lecture(self):
        b = sk.Backup.open(REF)
        self.assertEqual((b.kind, len(b.kit_numbers()), b.kit_numbers()[0]), ("bkf", 70, "031"))
        self.assertEqual(b.decode("032")["name"], "CrazyInLove")
        self.assertEqual(b.decode("032")["slots"][4]["wave_a"]["_sample_name"], "Sample Stuck")
        self.assertFalse(b.dirty)
        self.assertEqual(b.serialize(), REF.read_bytes())

    def test_modification_puis_enregistrement(self):
        b = sk.Backup.open(REF)
        kit = b.decode("033")
        kit["name"] = "Nouveau"
        kit["slots"][0]["wave_a"]["sample"] = "Sample Stuck"
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
        b = sk.Backup.open(REF)
        self.assertEqual(len(b.samples()), 8073)
        self.assertEqual(b.user_sample_ids(), sorted(b.user_sample_ids()))
        self.assertIn(8072, b.user_sample_ids())
        self.assertEqual(b.user_wav(8072), files_of(REF.read_bytes())["WAV/DATA/080/72.wav"])
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
        fac = ref_fac()
        b = sk.Backup(fac)
        self.assertEqual((b.kind, len(b.kit_numbers())), ("fac", 70))
        self.assertEqual((b.decode("001")["name"], b.decode("010")["name"]), ("WhereIs", "Ham & Beans"))
        self.assertEqual(b.user_sample_ids(), [])
        with self.assertRaisesRegex(sk.StrikeError, ".bkf"):
            b.add_sample("x", b"")
        self.assertEqual(b.serialize(), fac)


class RecopiePad(unittest.TestCase):
    def setUp(self):
        self.b = sk.Backup.open(REF)

    def test_recopie_complete_sans_note_midi(self):
        kit = self.b.decode("032")  # P5 : sample 8072 ; P9 : Click, Aux+Phone
        skipped = sk.copy_slot_settings(kit, 9, [1, 2], ["params", "light", "wave_a", "wave_b"])
        dec = sk.decode_kit(sk.encode_kit(self.b.get_raw("032"), kit))
        for i in (0, 1):
            self.assertEqual(dec["slots"][i]["params"]["control"], 3)
            self.assertEqual(dec["slots"][i]["params"]["audio_output"], 4)
        self.assertEqual([dec["slots"][i]["params"]["midi_note"] for i in (0, 1)], [36, 37])
        # tous les champs sont lisibles, y compris dans les pads masqués du kit KITC
        self.assertEqual(skipped, [])

    def test_recopie_partielle_et_note_midi(self):
        kit = self.b.decode("032")
        sk.copy_slot_settings(kit, 5, [6], ["wave_a"], include_midi_note=True)
        p6 = kit["slots"][5]
        self.assertEqual(p6["wave_a"]["sample"], 8072)
        self.assertEqual(p6["params"]["midi_note"], 42)  # params non copiés
        sk.copy_slot_settings(kit, 5, [6], ["params"], include_midi_note=True)
        self.assertEqual(kit["slots"][5]["params"]["midi_note"], 41)

    def test_recopie_vers_champ_recouvert(self):
        kit = self.b.decode("032")  # pad 3 : control recouvert par une autre structure
        skipped = sk.copy_slot_settings(kit, 9, [3], ["params"])
        self.assertEqual(skipped, [])
        dec = sk.decode_kit(sk.encode_kit(self.b.get_raw("032"), kit))
        self.assertEqual(dec["slots"][2]["params"]["control"], 3)

    def test_champ_absent_signale(self):
        kit = self.b.decode("032")
        del kit["slots"][2]["params"]["control"]
        self.assertEqual(sk.copy_slot_settings(kit, 9, [3], ["params"]), [(3, "params.control")])

    def test_emplacement_invalide(self):
        kit = self.b.decode("032")
        for src, dests, parts in ((0, [1], ["params"]), (1, [25], ["params"]), (1, [2], ["autre"])):
            with self.assertRaises(sk.StrikeError):
                sk.copy_slot_settings(kit, src, dests, parts)


class ModificationGroupee(unittest.TestCase):
    def setUp(self):
        self.b = sk.Backup.open(REF)

    def values(self, kit, field):
        out = []
        for s in kit["slots"]:
            node = s
            for key in field.split("."):
                node = node[key]
            out.append(node)
        return out

    def test_sensitivity_sur_une_selection(self):
        before = self.values(self.b.decode("033"), "params.sensitivity")
        kit, skipped = self.b.set_slots("033", [1, 3, 5, 9], "params.sensitivity", 20)
        self.assertEqual(skipped, [])
        expected = [20 if n in (1, 3, 5, 9) else v for n, v in enumerate(before, 1)]
        self.assertEqual(self.values(kit, "params.sensitivity"), expected)
        self.assertEqual(self.values(self.b.decode("033"), "params.sensitivity"), expected)
        self.assertTrue(self.b.dirty)

    def test_sections_et_kit_kitc(self):
        targets = list(range(1, 10))
        for field, value in (
            ("wave_b.params.volume", 70),
            ("light.play_color", 9),
            ("wave_a.velocity_high", 100),
            ("params.control", 3),
        ):
            kit, _ = self.b.set_slots("032", targets, field, value)
            self.assertEqual(self.values(kit, field)[:9], [value] * 9, field)
        before = self.values(self.b.decode("032"), "wave_a.sample")
        kit, _ = self.b.set_slots("032", [2, 4], "wave_a.sample", "Sample Stuck")
        self.assertEqual(
            self.values(kit, "wave_a.sample"), [8072 if n in (2, 4) else v for n, v in enumerate(before, 1)]
        )

    def test_valeur_hors_plage_sans_effet(self):
        raw = self.b.get_raw("033")
        with self.assertRaisesRegex(sk.StrikeError, "hors plage"):
            self.b.set_slots("033", [1, 2], "params.sensitivity", 40)
        self.assertEqual(self.b.get_raw("033"), raw)
        self.assertFalse(self.b.dirty)

    def test_champ_ou_emplacement_invalide(self):
        for targets, field in (
            ([1], "params.inconnu"),
            ([1], "autre.volume"),
            ([1], "light.couleur"),
            ([1], "wave_c.params.volume"),
            ([1], "params"),
            ([25], "params.volume"),
            ([], "params.volume"),
        ):
            with self.assertRaises(sk.StrikeError, msg=(targets, field)):
                self.b.set_slots("033", targets, field, 1)


class ModificationMultiKits(unittest.TestCase):
    def setUp(self):
        self.b = sk.Backup.open(REF)

    def sensitivity(self, num):
        return [s["params"]["sensitivity"] for s in self.b.decode(num)["slots"][:9]]

    def test_memes_pads_dans_plusieurs_kits(self):
        before = {n: self.sensitivity(n) for n in ("031", "032", "033", "034")}
        skipped = self.b.set_slots_in_kits(["031", "032", "033"], [1, 3, 9], "params.sensitivity", 20)
        self.assertEqual(skipped, [])
        for n in ("031", "032", "033"):
            self.assertEqual(self.sensitivity(n), [20 if p in (1, 3, 9) else v for p, v in enumerate(before[n], 1)], n)
        self.assertEqual(self.sensitivity("034"), before["034"])
        self.assertTrue(self.b.dirty)

    def test_atomique(self):
        raws = {n: self.b.get_raw(n) for n in ("031", "032")}
        for kits, value in ((["031", "032"], 40), (["031", "999"], 20), ([], 20)):
            with self.assertRaises(sk.StrikeError, msg=(kits, value)):
                self.b.set_slots_in_kits(kits, [1], "params.sensitivity", value)
        self.assertEqual({n: self.b.get_raw(n) for n in raws}, raws)
        self.assertFalse(self.b.dirty)

    def test_doublons_ignores(self):
        self.b.set_slots_in_kits(["033", "033"], [1], "params.sensitivity", 20)
        self.assertEqual(self.sensitivity("033")[0], 20)


class CopieKit(unittest.TestCase):
    def setUp(self):
        self.b = sk.Backup.open(REF)
        self.raw = {n: self.b.get_raw(n) for n in ("031", "032", "040")}

    def test_copie(self):
        self.b.copy_kit("032", "040")
        self.assertEqual(self.b.get_raw("040"), self.raw["032"])
        self.assertEqual(self.b.get_raw("032"), self.raw["032"])
        self.assertTrue(self.b.dirty)
        out = sk.Backup(self.b.serialize())  # conteneur valide
        self.assertEqual(out.decode("040")["name"], "CrazyInLove")

    def test_echange(self):
        self.b.swap_kits("031", "040")
        self.assertEqual((self.b.get_raw("031"), self.b.get_raw("040")), (self.raw["040"], self.raw["031"]))
        self.assertEqual(sk.Backup(self.b.serialize()).decode("040")["name"], "WhereIs")

    def test_fac(self):
        b = sk.Backup(ref_fac())
        source = b.get_raw("010")
        b.copy_kit("010", "050")
        b.swap_kits("001", "002")
        out = sk.Backup(b.serialize())
        self.assertEqual(out.get_raw("050"), source)
        self.assertEqual((out.decode("001")["name"], out.decode("002")["name"]), ("CrazyInLove", "WhereIs"))

    def test_kits_invalides(self):
        for a, b in (("032", "032"), ("032", "101"), ("999", "040")):
            for op in (self.b.copy_kit, self.b.swap_kits):
                with self.assertRaises(sk.StrikeError):
                    op(a, b)
        self.assertFalse(self.b.dirty)


class SuppressionKit(unittest.TestCase):
    """Supprimer un kit : le remplacer par le kit vide écrit par l'appareil."""

    def setUp(self):
        self.b = sk.Backup.open(REF)

    def test_kit_vide_de_l_appareil(self):
        # identique aux kits vides de la référence (.bkf et .fac)
        self.assertEqual(sk.EMPTY_KIT, self.b.get_raw("041"))
        self.assertEqual(sk.EMPTY_KIT, sk.Backup(ref_fac()).get_raw("070"))
        kit = sk.decode_kit(sk.EMPTY_KIT)
        self.assertEqual((kit["format"], kit["name"], kit["level"], kit["tempo"]), ("KITH", "Empty", 100, 120.0))
        self.assertTrue(sk.is_empty_kit(self.b.get_raw("041")))
        self.assertFalse(sk.is_empty_kit(self.b.get_raw("031")))

    def test_suppression(self):
        others = {n: self.b.get_raw(n) for n in self.b.kit_numbers() if n != "031"}
        self.b.clear_kit("031")
        self.assertEqual(self.b.get_raw("031"), sk.EMPTY_KIT)
        self.assertEqual({n: self.b.get_raw(n) for n in others}, others)
        self.assertTrue(self.b.dirty)
        out = sk.Backup(self.b.serialize())  # conteneur valide
        self.assertEqual(out.decode("031")["name"], "Empty")
        self.assertIn(8071, out.user_sample_ids())  # les samples restent dans la sauvegarde

    def test_kit_deja_vide(self):
        self.b.clear_kit("041")
        self.assertFalse(self.b.dirty)

    def test_fac(self):
        b = sk.Backup(ref_fac())
        b.clear_kit("001")
        self.assertEqual(sk.Backup(b.serialize()).get_raw("001"), sk.EMPTY_KIT)

    def test_kit_inexistant(self):
        with self.assertRaises(sk.StrikeError):
            self.b.clear_kit("999")
        self.assertFalse(self.b.dirty)


if __name__ == "__main__":
    unittest.main()
