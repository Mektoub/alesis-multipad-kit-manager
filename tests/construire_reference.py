#!/usr/bin/env python3
"""Construit la sauvegarde de référence des tests, tests/ressources/Backup001.bkf.

Elle part d'une vraie sauvegarde de l'appareil (Backup003.bkf du 16/10/2026),
dont elle garde la structure écrite par l'appareil :
  - kit 031 « WhereIs » (KITC, Control Click sur les pads 7–9) ;
  - kit 032 « CrazyInLove » (KITC, créé sur l'appareil ; Click et Aux+Phone sur P9) ;
  - kits 033–100 vides (KITH).

Aucun son d'origine n'y reste : la sauvegarde est diffusable avec le code.
  - Les 34 samples utilisateur gardent leur id (les kits les référencent) et
    leur nombre de canaux, mais leur audio, métadonnées comprises, est remplacé
    par un son synthétique court (sinus amorti, bruit, clic) ; ils sont renommés
    « Sine 01 », « Noise 02 »…, sauf 8071 « SnareUF » et 8072 « Sample Stuck ».
    En-tête .had, liste par nom et liste par taille sont mis à jour en conséquence.
  - Le kit 040 « Layer Demo » est construit à partir d'un kit vide : samples
    d'usine (références par numéro, l'audio est dans l'appareil), couches de
    vélocité (P4, P6 ; P5 wave B : sample 107, vélocité 126–127).

Le script s'applique aussi bien à la sauvegarde d'origine qu'à une référence
déjà construite : le résultat est le même.

Usage :
  python3 tests/construire_reference.py Backup003.bkf -o tests/ressources/Backup001.bkf
"""

import argparse
import math
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import strike_kits as sk  # noqa: E402

RATE = 44100
KEPT_NAMES = {8071: "SnareUF", 8072: "Sample Stuck"}
KINDS = ("Sine", "Noise", "Click")

# kit 040 : wave A, wave B, vélocité (basse, haute) de la wave B, couleur des LED
LAYER_KIT = "040"
LAYER_PADS = [
    (5074, None, None, 7),  # P1 Kicker Bass
    (7345, None, None, 7),  # P2 808Rimshot
    (5520, None, None, 7),  # P3 808Cowbell
    (5326, 5329, (101, 127), 0),  # P4 Claps Dry Hard 1, Claps Dry Hard 4 au-dessus de 100
    (7896, 107, (126, 127), 0),  # P5 Bongo Large_01, iLectro au maximum
    (5522, 5521, (64, 127), 0),  # P6 808LowConga, 808HighConga au-dessus de 63
    (93, None, None, 16),  # P7 909 Ride
    (102, None, None, 16),  # P8 DirtyCrash
    (572, None, None, 16),  # P9 Abfarad HHat
]


def tone(kind, seed, frames, channels):
    """Données 16 bits entrelacées d'un son synthétique amorti (déterministe)."""
    rng = random.Random(seed)
    freq = 80 * 2 ** (seed % 24 / 6)
    out = bytearray()
    for i in range(frames):
        t = i / RATE
        if kind == "Sine":
            v = math.sin(2 * math.pi * freq * t) * math.exp(-t * 18)
        elif kind == "Noise":
            v = (rng.random() * 2 - 1) * math.exp(-t * 18)
        else:  # Click
            v = max(0.0, 1 - i / 40)
        out += struct.pack("<h", int(v * 0.8 * 32767)) * channels
    return bytes(out)


def make_wav(data, channels):
    fmt = struct.pack("<HHIIHH", 1, channels, RATE, RATE * 2 * channels, 2 * channels, 16)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


def channel_count(wav):
    """Nombre de canaux lu dans le bloc fmt (l'appareil accepte aussi des
    formats que wav_info refuse à l'ajout)."""
    fmt = wav.index(b"fmt ")
    return struct.unpack("<H", wav[fmt + 10 : fmt + 12])[0]


def wav_path(sid):
    return "WAV/DATA/%03d/%d.wav" % (sid // 100, sid % 100)


def drop_entry(b, name, size, sid_at, sid):
    """Retire de la liste `name` (entrées de `size` octets) celle du sample `sid`."""
    data, n = b._list(name)
    total = len(data)
    k = next(k for k in range(n) if struct.unpack(">H", data[sid_at + size * k : sid_at + 2 + size * k])[0] == sid)
    del data[0x20 + size * k : 0x20 + size * (k + 1)]
    if name == "wave_list_sort_name.lst":  # rang de chaque entrée suivante
        for j in range(k, n - 1):
            o = 0x20 + size * j
            data[o : o + 2] = struct.pack(">H", (struct.unpack(">H", data[o : o + 2])[0] - 1) & 0xFFFF)
    else:  # liste de taille fixe
        data += bytes(total - len(data))
    b._save_list(name, data, n - 1)


def replace_sample(b, sid, name, wav):
    """Remplace l'audio et le nom du sample utilisateur `sid`."""
    channels, data_off, data_len = sk.wav_info(wav)
    folder, fileno = sid // 100, sid % 100
    b.set_file(wav_path(sid), wav)
    rel = "\\%03d\\%d.wav" % (folder, fileno)
    b.set_file("WAV/HEAD/%03d/%d.had" % (folder, fileno), sk.make_had(name, channels, data_off, data_len, rel))
    drop_entry(b, "wave_list_sort_name.lst", 0x90, 0x22, sid)
    b._add_sort_name(sid, name)
    drop_entry(b, "WaveList_User_SortSize.lst", 8, 0x22, sid)
    b._add_sort_size(sid, len(wav))


def build(source):
    b = sk.Bkf.parse(source)
    for n, sid in enumerate(sk.Backup(source).user_sample_ids()):
        kind = KINDS[n % 3]
        frames = RATE * (3 + n % 5) // 20  # 0,15 à 0,35 s
        channels = channel_count(b.get_file(wav_path(sid)))
        wav = make_wav(tone(kind, n, frames, channels), channels)
        replace_sample(b, sid, KEPT_NAMES.get(sid) or "%s %02d" % (kind, n + 1), wav)

    backup = sk.Backup(b.serialize())
    backup.clear_kit(LAYER_KIT)
    kit = backup.decode(LAYER_KIT)
    kit.update(name="Layer Demo", level=90, tempo=120.0)
    for slot, (a, wb, vel, color) in zip(kit["slots"], LAYER_PADS, strict=False):
        slot["wave_a"]["sample"] = a
        if wb is not None:
            slot["wave_b"]["sample"] = wb
            slot["wave_b"]["velocity_low"], slot["wave_b"]["velocity_high"] = vel
            if vel[0] < 126:  # couches qui se partagent la plage
                slot["wave_a"]["velocity_high"] = vel[0] - 1
        slot["light"]["play_color"] = slot["light"]["stop_color"] = color
    backup.update(LAYER_KIT, kit)
    return backup.serialize()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="sauvegarde de l'appareil, ou référence déjà construite")
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()
    data = build(Path(a.source).read_bytes())
    Path(a.output).write_bytes(data)
    print("%s : %d octets" % (a.output, len(data)))


if __name__ == "__main__":
    main()
