"""Tests de l'historique des modifications (annuler / rétablir), sur la
sauvegarde de référence."""

import unittest

import strike_kits as sk
from editor.history import LIMIT, History, changes
from editor.i18n import set_language
from tests.outils import REF


class Horloge:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def edit(backup, num, fn):
    """Fonction qui applique `fn` au kit décodé puis l'enregistre (comme un PUT)."""

    def run():
        kit = backup.decode(num)
        fn(kit)
        return backup.update(num, kit)

    return run


def set_volume(value, slot=0):
    def fn(kit):
        kit["slots"][slot]["params"]["volume"] = value

    return fn


class Differences(unittest.TestCase):
    def test_champs_modifies(self):
        b = sk.Backup.open(REF)
        before = b.decode("032")
        after = b.decode("032")
        after["name"] = "Autre"
        after["slots"][2]["wave_a"]["params"]["volume"] = 12
        self.assertEqual(
            changes(before, after),
            [(("name",), "CrazyInLove", "Autre"), (("slots", 2, "wave_a", "params", "volume"), 90, 12)],
        )
        self.assertEqual(changes(before, before), [])


class Historique(unittest.TestCase):
    def setUp(self):
        set_language("fr")
        self.addCleanup(set_language, "en")
        self.b = sk.Backup.open(REF)
        self.clock = Horloge()
        self.h = History(clock=self.clock)
        self.raw = {n: self.b.get_raw(n) for n in ("031", "032", "033")}

    def put(self, num, fn):
        return self.h.track(self.b, [num], edit(self.b, num, fn), merge=True)

    def volume(self, num="032", slot=0):
        return self.b.decode(num)["slots"][slot]["params"]["volume"]

    def test_annuler_retablir(self):
        self.put("032", set_volume(50))
        self.assertEqual(self.h.summary(), {"undo": "Kit 032 · P1 · Volume", "redo": None})
        entry = self.h.undo(self.b)
        self.assertEqual((entry.label, entry.kits), ("Kit 032 · P1 · Volume", ["032"]))
        self.assertEqual(self.b.get_raw("032"), self.raw["032"])  # octets d'origine, à l'identique
        self.assertEqual(self.h.summary(), {"undo": None, "redo": "Kit 032 · P1 · Volume"})
        self.h.redo(self.b)
        self.assertEqual(self.volume(), 50)

    def test_rien_a_annuler(self):
        self.assertIsNone(self.h.undo(self.b))
        self.assertIsNone(self.h.redo(self.b))
        self.put("032", set_volume(self.volume()))  # aucune différence : pas d'étape
        self.assertEqual(self.h.summary(), {"undo": None, "redo": None})

    def test_ordre_inverse(self):
        self.put("032", set_volume(50))
        self.clock.t = 10
        self.put("033", set_volume(60))
        self.h.undo(self.b)
        self.assertEqual((self.volume("032"), self.b.get_raw("033")), (50, self.raw["033"]))
        self.h.undo(self.b)
        self.assertEqual(self.b.get_raw("032"), self.raw["032"])

    def test_nouvelle_modification_vide_retablir(self):
        self.put("032", set_volume(50))
        self.h.undo(self.b)
        self.put("032", set_volume(70))
        self.assertIsNone(self.h.summary()["redo"])

    def test_envois_rapproches_fusionnes(self):
        for t, v in ((0, 10), (0.4, 20), (0.8, 30)):
            self.clock.t = t
            self.put("032", set_volume(v))
        self.h.undo(self.b)
        self.assertEqual(self.b.get_raw("032"), self.raw["032"])  # une seule étape
        self.assertIsNone(self.h.summary()["undo"])

    def test_pas_de_fusion_apres_une_pause_ni_sur_un_autre_champ(self):
        self.put("032", set_volume(10))
        self.clock.t = 5
        self.put("032", set_volume(20))  # pause
        self.clock.t = 5.2
        self.put("032", set_volume(30, slot=1))  # autre champ
        self.h.undo(self.b)
        self.h.undo(self.b)
        self.assertEqual(self.volume(), 10)

    def test_fusion_revenue_a_l_origine(self):
        old = self.volume()
        self.put("032", set_volume(10))
        self.put("032", set_volume(old))
        self.assertIsNone(self.h.summary()["undo"])

    def test_action_sur_plusieurs_kits_une_etape(self):
        nums = ["031", "032", "033"]
        self.h.track(
            self.b,
            nums,
            lambda: self.b.set_slots_in_kits(nums, [1, 2], "params.sensitivity", 20),
            label="Sensitivity",
        )
        self.assertEqual(self.h.summary()["undo"], "Sensitivity · 3 kits")
        entry = self.h.undo(self.b)
        self.assertEqual(entry.kits, nums)
        self.assertEqual({n: self.b.get_raw(n) for n in nums}, self.raw)

    def test_libelles(self):
        self.h.track(self.b, ["032"], lambda: self.b.set_slots("032", [1, 2], "params.sensitivity", 20), label="X")
        self.assertEqual(self.h.summary()["undo"], "Kit 032 · X")
        self.clock.t = 10
        self.put("032", lambda k: k.update(name="Nom"))
        self.assertEqual(self.h.summary()["undo"], "Kit 032 · Nom du kit")
        self.clock.t = 20
        self.put("032", lambda k: k["slots"][3]["light"].update(play_color=2))
        self.assertEqual(self.h.summary()["undo"], "Kit 032 · P4 · Play Color")
        self.clock.t = 30
        self.put("032", lambda k: k["slots"][0]["wave_b"]["params"].update(volume=3, pan=2))
        self.assertEqual(self.h.summary()["undo"], "Kit 032 · 2 paramètres")

    def test_libelles_dans_la_langue_de_lecture(self):
        """Une étape faite en français se lit en anglais après changement de langue."""
        self.put("032", lambda k: k.update(name="Nom"))
        self.clock.t = 10
        self.h.track(self.b, ["031", "032"], lambda: self.b.set_slots_in_kits(["031", "032"], [1], "params.volume", 5))
        set_language("en")
        rows = self.h.entries()["entries"]
        self.assertEqual([r["label"] for r in rows], ["Kit 032 · Kit name", "2 parameters · 2 kits"])
        self.assertEqual(rows[0]["detail"], "“CrazyInLove” → “Nom”")

    def test_limite(self):
        for i in range(LIMIT + 5):
            self.clock.t = 10 * i
            self.put("032", set_volume(i % 2))
        n = 0
        while self.h.undo(self.b):
            n += 1
        self.assertEqual(n, LIMIT)

    def test_etat_enregistre(self):
        self.assertFalse(self.h.dirty)
        self.put("032", set_volume(50))
        self.assertTrue(self.h.dirty)
        self.h.mark_saved()
        self.assertFalse(self.h.dirty)
        self.h.undo(self.b)
        self.assertTrue(self.h.dirty)
        self.h.redo(self.b)
        self.assertFalse(self.h.dirty)

    def test_pas_de_fusion_avec_l_etape_enregistree(self):
        self.put("032", set_volume(50))
        self.h.mark_saved()
        self.put("032", set_volume(60))
        self.h.undo(self.b)
        self.assertEqual((self.volume(), self.h.dirty), (50, False))

    def test_vider(self):
        self.put("032", set_volume(50))
        self.h.clear()
        self.assertEqual(self.h.summary(), {"undo": None, "redo": None})
        self.assertTrue(self.h.dirty)  # les modifications restent, non enregistrées

    def test_modification_hors_historique(self):
        self.put("032", set_volume(50))
        self.h.mark_saved()
        self.h.untracked()  # ajout de sample : le fichier diffère, l'historique reste
        self.assertEqual(self.h.summary()["undo"], "Kit 032 · P1 · Volume")
        self.assertTrue(self.h.dirty)
        self.h.undo(self.b)
        self.h.redo(self.b)
        self.assertTrue(self.h.dirty)

    def test_valeurs_avant_apres(self):
        self.put("032", set_volume(50))
        self.clock.t = 10
        self.put("032", lambda k: k["slots"][0]["params"].update(curve=2))
        self.clock.t = 20
        self.put("032", lambda k: k["slots"][0]["wave_a"].update(sample=8071))
        self.clock.t = 30
        self.put("032", lambda k: k.update(name="Nom"))
        self.clock.t = 40
        self.put("032", lambda k: k["slots"][0]["wave_b"]["params"].update(volume=3, pan=2))
        details = [e["detail"] for e in self.h.entries()["entries"]]
        self.assertEqual(details, ["90 → 50", "Normal → Exp2", "— → SnareUF", "« CrazyInLove » → « Nom »", ""])

    def test_liste(self):
        self.assertEqual(self.h.entries(), {"entries": [], "base": 0, "position": 0, "saved": 0})
        for t, v in ((0, 10), (10, 20), (20, 30)):
            self.clock.t = t
            self.put("032", set_volume(v))
        self.h.mark_saved()
        self.h.undo(self.b)
        listing = self.h.entries()
        self.assertEqual([e["done"] for e in listing["entries"]], [True, True, False])
        ids = [e["id"] for e in listing["entries"]]
        self.assertEqual((listing["position"], listing["saved"]), (ids[1], ids[2]))
        self.assertEqual(listing["entries"][0]["label"], "Kit 032 · P1 · Volume")

    def test_aller_a_une_etape(self):
        for t, (num, v) in enumerate((("032", 10), ("033", 20), ("032", 30))):
            self.clock.t = 10 * t
            self.put(num, set_volume(v))
        ids = [e["id"] for e in self.h.entries()["entries"]]
        self.assertEqual(self.h.goto(self.b, ids[0]), ["032", "033"])  # deux étapes annulées
        self.assertEqual((self.volume("032"), self.b.get_raw("033")), (10, self.raw["033"]))
        self.assertEqual(self.h.goto(self.b, self.h.entries()["base"]), ["032"])
        self.assertEqual(self.b.get_raw("032"), self.raw["032"])
        self.assertEqual(self.h.goto(self.b, ids[2]), ["032", "033"])
        self.assertEqual((self.volume("032"), self.volume("033")), (30, 20))
        self.assertEqual(self.h.goto(self.b, ids[2]), [])  # déjà à cette étape
        with self.assertRaises(KeyError):
            self.h.goto(self.b, 999)

    def test_echec_sans_etape(self):
        with self.assertRaises(sk.StrikeError):
            self.h.track(self.b, ["032"], lambda: self.b.set_slots("032", [1], "params.volume", 999))
        self.assertIsNone(self.h.summary()["undo"])


if __name__ == "__main__":
    unittest.main()
