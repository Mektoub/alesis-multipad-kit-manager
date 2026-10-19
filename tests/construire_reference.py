#!/usr/bin/env python3
"""Construit la sauvegarde de référence des tests, tests/ressources/Backup001.bkf.

Elle part d'une vraie sauvegarde de l'appareil (Backup003.bkf du 16/10/2026) :
  - kit 031 « WhereIs » (KITC, Control Click sur les pads 7–9) ;
  - kit 032 « CrazyInLove » (KITC, créé sur l'appareil ; Click et Aux+Phone sur P9) ;
  - kits 033–100 vides (KITH).
Pour réduire la taille (66 Mo → 5 Mo), les deux gros samples 8071 et 8072 sont
retirés puis remplacés par deux WAV courts, qui reprennent les mêmes ids : les
kits continuent donc de les référencer. Le kit d'usine 005 « Ham & Beans » du
.fac (couches de vélocité) est copié en 040.

Usage :
  python3 tests/construire_reference.py Backup003.bkf STRIKE_BACKUP_KIT.fac \\
      SnareUF.wav "Sample Stuck.wav" -o tests/ressources/Backup001.bkf
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import strike_kits as sk  # noqa: E402


def build(bkf3, fac, wav_8071, wav_8072):
    b = sk.Bkf.parse(bkf3)
    assert b.remove_last_sample() == 8072
    assert b.remove_last_sample() == 8071
    assert b.add_sample("SnareUF", wav_8071) == 8071
    assert b.add_sample("Sample Stuck", wav_8072) == 8072
    kits = {e.name: fac[e.offset : e.offset + e.size] for e in sk.kit_entries(sk.parse_fac(fac))}
    b.set_file("KIT/040.kit", kits["005.kit"])
    return b.serialize()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("backup003")
    ap.add_argument("fac")
    ap.add_argument("wav_8071")
    ap.add_argument("wav_8072")
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()
    data = build(*(Path(p).read_bytes() for p in (a.backup003, a.fac, a.wav_8071, a.wav_8072)))
    Path(a.output).write_bytes(data)
    print("%s : %d octets" % (a.output, len(data)))


if __name__ == "__main__":
    main()
