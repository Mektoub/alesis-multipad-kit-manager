"""Outils communs aux tests : sauvegarde de référence, WAV et .fac synthétiques.

Tous les tests reposent sur une seule sauvegarde, tests/ressources/Backup001.bkf
(voir construire_reference.py pour son contenu et sa construction).
"""

import struct
import wave
from pathlib import Path

import strike_kits as sk

REF = Path(__file__).resolve().parent / "ressources" / "Backup001.bkf"


def files_of(data):
    return {e.full: data[e.offset : e.offset + e.size] for e in sk.parse_bkf(data)}


def kits_of(data):
    _, entries = sk.parse_container(data)
    return {e.name: data[e.offset : e.offset + e.size] for e in sk.kit_entries(entries)}


def make_wav(path, sampwidth=2, rate=44100, channels=1, frames=100):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(rate)
        w.writeframes(b"\x01" * frames * sampwidth * channels)


def make_fac(kits):
    """Conteneur .fac (SDRH) contenant `kits` : liste de (numéro, octets du kit),
    dans l'ordre de la table (l'appareil ne les range pas forcément par numéro).

    Disposition relevée sur un vrai STRIKE_BACKUP_KIT.fac (docs/fr/fac-format.md) :
    SDRH, SDCH racine, DIRH « KIT », SDCH du répertoire, une entrée FIEH de 0x60
    octets par kit, puis les données mises bout à bout.
    """

    def name_entry(tag, name):
        e = bytearray(0x60)
        e[0:4] = tag
        e[4:8] = struct.pack(">I", len(name))
        e[8 : 8 + len(name)] = name.encode("ascii")
        return e

    head = bytearray(0x120)
    head[0:4], head[4:6], head[8] = b"SDRH", b"\x00\x40", 0xB0
    head[0x40:0x44], head[0x44:0x46], head[0x4A:0x4C] = b"SDCH", b"\x00\x40", b"\x00\x01"
    head[0x80:0xE0] = name_entry(b"DIRH", "KIT")
    head[0xD4:0xD8] = struct.pack(">I", 0xE0)
    head[0xE0:0xE4], head[0xE4:0xE6] = b"SDCH", b"\x00\x40"
    head[0xEC:0xEE] = struct.pack(">H", len(kits))
    table = bytearray()
    offset = 0x120 + 0x60 * len(kits)
    for num, kit in kits:
        e = name_entry(b"FIEH", num)
        e[0x48:0x4B] = b"kit"
        e[0x4C:0x50] = struct.pack(">I", len(kit))
        e[0x54:0x58] = struct.pack(">I", offset)
        table += e
        offset += len(kit)
    return bytes(head + table + b"".join(kit for _, kit in kits))


def ref_fac():
    """.fac contenant les 70 kits de la référence : 001 = WhereIs, 002 = CrazyInLove,
    010 = Layer Demo (couches de vélocité), les autres vides."""
    kits = kits_of(REF.read_bytes())
    return make_fac([("%03d" % (i + 1), kits[n]) for i, n in enumerate(sorted(kits))])
