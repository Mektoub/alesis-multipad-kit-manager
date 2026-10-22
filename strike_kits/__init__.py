"""Édition des kits de l'Alesis Strike MultiPad via JSON.

Formats pris en charge (rétro-ingénierie, non officiels) :
  - .bkf  « All User Kit And Sample Backup » (en-tête PACKBKF)
  - .fac  « BackUp/STRIKE_BACKUP_KIT.fac »   (en-tête SDRH)

Principe : `export` décode chaque kit en JSON ; `import` repart du fichier de
sauvegarde d'origine, réécrit les kits avec les valeurs du JSON, ajoute les WAV
du dossier `wav/` (.bkf uniquement) et recalcule les sommes de contrôle. Les
octets non décodés sont conservés tels quels, si bien qu'un dossier non modifié
redonne un fichier identique octet pour octet.

Ligne de commande : python3 -m strike_kits export|import … (strike_kits/__main__.py).
"""

import argparse
import base64
import json
import re
import struct
import sys
import zlib
from pathlib import Path

KIT_SIZE = 0x2660
SLOT_COUNT = 24
SLOT_BASE = 0x260
SLOT_SIZE = 0x180

NAME_OFF, NAME_LEN = 0xC0, 16
LEVEL_OFF = 0x0C
TEMPO_OFF = 0x10

# Kit vide écrit par l'appareil (« Empty », KITH, volume 100, 120 BPM, réglages
# par défaut, aucun sample), identique dans les .bkf et le .fac : sert à
# supprimer un kit. Compressé (zlib) et encodé en base64.
EMPTY_KIT = zlib.decompress(
    base64.b64decode(
        "eNrt1stKw0AUBuB/YmynonZqvcQLmIW1UVvxggsfQDB025UrF9kqLtwI6vhIPppvEI8QMQsjWCEHyz8whEly/pDvhCSjdHwZXOf5"
        "LbpRhgzhqxnMvRlMNuquw+zFzd39w28q5gE7U7pe+JlUWpti/bFtFPsbf73D4YSVffznMUrHqXn5arMTe2u+UbxCFrSxbXfgW9IF"
        "aZNbTODa0gkH+I4z8VKIuAs0l4GFFUlbTeDX5JxcyitnDl/Kj1tFXiSH1g3MBpBtytwCgh9zlPJr9+/RX9V/l/6q/gn9Vf336K/q"
        "v09/Vf9BhX9E/1r8h/RX9T+kv6r/Ad///P5Or78tZqV/n/6q/kf0V/U/pr+q/wn9Vf1P6a/qz/9PXf/HCn9L/1r8n+iv6v9Mf1V/"
        "T39V/zP6q/qf05/P//T4vwOOdeep"
    )
)
assert len(EMPTY_KIT) == KIT_SIZE

# Enregistrements (id, valeur, min, max), dans l'ordre fixe où ils apparaissent
# dans tous les kits. Dans les 8 premiers emplacements des kits KITC, seuls les
# octets « valeur » font foi : id/min/max sont remplacés par 0xFF, 0x00 ou par
# des structures qui recouvrent la zone (l'octet valeur restant à sa place).
KITC_MASKED_SLOTS = 8
PAD_LAYOUT = [
    (0x00, 0, 100),
    (0x02, 0, 31),
    (0x08, 0, 127),
    (0x09, 0, 4),
    (0x0C, 0, 16),
    (0x0E, 0, 16),
    (0x0F, 0, 5),
    (0x10, 0, 127),
    (0x11, 1, 32),
    (0x12, 0, 32),
    (0x13, 0, 7),
    (0x14, 0, 13),
    (0x15, 0, 1),
    (0x16, 0, 127),
    (0x17, 0, 16),
]
WAVE_LAYOUT = [
    (0x00, 0, 100),
    (0x02, 0, 32),
    (0x09, 0, 5),
    (0x10, 0, 127),
    (0x18, 0, 255),
    (0x19, 0, 1),
    (0x1A, 0, 100),
    (0x1B, 0, 100),
    (0x1C, 0, 2),
]
PAD_PARAMS = {
    0x00: "volume",
    0x02: "pan",
    0x08: "midi_note",
    0x0C: "sync_group",
    0x0F: "audio_output",
    0x10: "fixed_level",
    0x11: "sensitivity",
    0x12: "threshold",
    0x13: "curve",
    0x14: "control",
    0x15: "sound",
    0x16: "kit_fx_level",
}
WAVE_PARAMS = {
    0x00: "volume",
    0x02: "pan",
    0x09: "playback_mode",
    0x19: "poly_mono",
    0x1A: "fade_in",
    0x1B: "fade_out",
    0x1C: "priority",
}
# Maximum réel quand l'appareil écrit plus que le max de l'enregistrement :
# Playback Mode annonce 0–5, mais FS4 vaut 9 (vérifié).
VALUE_MAX = {"playback_mode": 9}
# Champs à offset fixe dans l'emplacement : nom -> (offset, valeur max).
# Éclairage (`light`) ; Sync Mode, rangé avec les paramètres du pad (`params`).
LIGHT_FIELDS = {
    "play_color": (0x10, 16),
    "play_mode": (0x11, 6),
    "play_beat": (0x12, 3),
    "stop_color": (0x14, 16),
    "stop_mode": (0x15, 6),
    "stop_beat": (0x16, 3),
}
PAD_FIELDS = {"sync_mode": (0x19, 4)}

PAD_RECORDS = 0x28
WAVES = {"wave_a": 0x80, "wave_b": 0xE0}
WAVE_RECORDS = 0x08
# En-tête d'une wave : u16 id du sample, u8 Velocity Low, u8 Velocity High.
NO_SAMPLE = 0xFFFF


class StrikeError(Exception):
    pass


# --------------------------------------------------------------------------
# Kits
# --------------------------------------------------------------------------


def kit_checksum(kit):
    """Somme de contrôle des kits et des .had (octet 0x08)."""
    return sum(kit[10:]) & 0xFF


def param_name(table, rid):
    return table.get(rid, "p%02x" % rid)


def layout_index(layout, table, name):
    for k, (rid, _, _) in enumerate(layout):
        if param_name(table, rid) == name:
            return k
    raise StrikeError("paramètre inconnu : %s" % name)


def record_readable(kit, off, rid, lo, hi, masked):
    """Vrai si l'octet valeur de l'enregistrement à `off` est exploitable."""
    if masked:
        return True
    return kit[off] in (rid, 0xFF, 0x00) and (kit[off + 2], kit[off + 3]) in ((lo, hi), (0xFF, 0xFF), (0, 0))


def is_masked(kit, index):
    return kit[:4] == b"KITC" and index < KITC_MASKED_SLOTS


def decode_params(kit, start, layout, table, masked=False):
    out = {}
    for k, (rid, lo, hi) in enumerate(layout):
        off = start + 4 * k
        if record_readable(kit, off, rid, lo, hi, masked):
            out[param_name(table, rid)] = kit[off + 1]
    return out


def encode_params(kit, start, layout, table, params, where, masked=False):
    for name, value in params.items():
        if name.startswith("_"):
            continue
        k = layout_index(layout, table, name)
        rid, lo, hi = layout[k]
        off = start + 4 * k
        if not record_readable(kit, off, rid, lo, hi, masked):
            raise StrikeError("%s : %s non modifiable dans ce kit" % (where, name))
        if kit[off + 1] == value:
            continue
        hi = VALUE_MAX.get(name, hi)
        if not isinstance(value, int) or not lo <= value <= hi:
            raise StrikeError("%s : %s=%r hors plage [%d, %d]" % (where, name, value, lo, hi))
        kit[off + 1] = value


def decode_fixed(kit, base, fields):
    """Champs à offset fixe lisibles (valeur dans la plage) de l'emplacement `base`."""
    return {k: kit[base + o] for k, (o, hi) in fields.items() if kit[base + o] <= hi}


def encode_fixed(kit, base, fields, values, where, section):
    for key, value in values.items():
        off, limit = fields[key]
        if kit[base + off] == value:
            continue
        if kit[base + off] > limit:
            raise StrikeError("%s : %s.%s non modifiable dans ce kit" % (where, section, key))
        if not isinstance(value, int) or not 0 <= value <= limit:
            raise StrikeError("%s : %s.%s=%r hors plage [0, %d]" % (where, section, key, value, limit))
        kit[base + off] = value


def wave_header_readable(kit, w):
    return kit[w + 2] <= kit[w + 3] <= 127


def slot_label(index):
    return "P%d" % (index + 1) if index < 9 else "slot %d" % (index + 1)


def is_empty_kit(kit):
    """Vrai si `kit` est exactement le kit vide de l'appareil."""
    return bytes(kit) == EMPTY_KIT


def kit_format(kit):
    kind = bytes(kit[:4]).decode("ascii", "replace")
    if kind not in ("KITH", "KITC"):
        raise StrikeError("kit inconnu : %r" % kind)
    return kind


def decode_kit(kit, samples=None):
    samples = samples or {}
    out = {
        "format": kit_format(kit),
        "name": bytes(kit[NAME_OFF : NAME_OFF + NAME_LEN]).split(b"\0")[0].decode("latin-1"),
        "level": kit[LEVEL_OFF],
        "tempo": struct.unpack(">H", kit[TEMPO_OFF : TEMPO_OFF + 2])[0] / 10,
        "slots": [],
    }
    for i in range(SLOT_COUNT):
        base = SLOT_BASE + i * SLOT_SIZE
        slot = {"slot": i + 1, "_label": slot_label(i)}
        slot["light"] = decode_fixed(kit, base, LIGHT_FIELDS)
        masked = is_masked(kit, i)
        slot["params"] = decode_params(kit, base + PAD_RECORDS, PAD_LAYOUT, PAD_PARAMS, masked)
        slot["params"].update(decode_fixed(kit, base, PAD_FIELDS))
        for wave, woff in WAVES.items():
            w = base + woff
            entry = {}
            if wave_header_readable(kit, w):
                sid = struct.unpack(">H", kit[w : w + 2])[0]
                entry["sample"] = None if sid == NO_SAMPLE else sid
                if sid in samples:
                    entry["_sample_name"] = samples[sid]
                entry["velocity_low"], entry["velocity_high"] = kit[w + 2], kit[w + 3]
            entry["params"] = decode_params(kit, w + WAVE_RECORDS, WAVE_LAYOUT, WAVE_PARAMS, masked)
            slot[wave] = entry
        out["slots"].append(slot)
    return out


def resolve_sample(value, samples, where):
    if value is None:
        return NO_SAMPLE
    if isinstance(value, int):
        if not 0 <= value < NO_SAMPLE:
            raise StrikeError("%s : id de sample invalide %r" % (where, value))
        return value
    if isinstance(value, str):
        ids = [sid for sid, name in samples.items() if name == value]
        if len(ids) == 1:
            return ids[0]
        if not ids:
            raise StrikeError("%s : sample introuvable %r (voir samples.json)" % (where, value))
        raise StrikeError(
            "%s : nom de sample ambigu %r (ids %s), utiliser l'id" % (where, value, ", ".join(map(str, sorted(ids))))
        )
    raise StrikeError("%s : sample doit être un id, un nom ou null" % where)


def encode_kit(raw, data, samples=None):
    """Applique le JSON `data` sur une copie du kit binaire `raw`."""
    kit = bytearray(raw)
    samples = samples or {}
    if data.get("format", kit_format(kit)) != kit_format(kit):
        raise StrikeError("le format du JSON ne correspond pas au kit d'origine")

    name = data["name"].encode("latin-1")
    if len(name) > NAME_LEN:
        raise StrikeError("nom de kit trop long (%d caractères max) : %r" % (NAME_LEN, data["name"]))
    if name != bytes(kit[NAME_OFF : NAME_OFF + NAME_LEN]).split(b"\0")[0]:
        kit[NAME_OFF : NAME_OFF + NAME_LEN] = name.ljust(NAME_LEN, b"\0")

    if data["level"] != kit[LEVEL_OFF]:
        if not 0 <= data["level"] <= 100:
            raise StrikeError("level hors plage [0, 100]")
        kit[LEVEL_OFF] = data["level"]
    tempo = round(data["tempo"] * 10)
    if tempo != struct.unpack(">H", kit[TEMPO_OFF : TEMPO_OFF + 2])[0]:
        if not 300 <= tempo <= 2800:
            raise StrikeError("tempo hors plage [30, 280]")
        kit[TEMPO_OFF : TEMPO_OFF + 2] = struct.pack(">H", tempo)

    for slot in data["slots"]:
        i = slot["slot"] - 1
        where = "emplacement %d" % slot["slot"]
        if not 0 <= i < SLOT_COUNT:
            raise StrikeError("%s inexistant" % where)
        base = SLOT_BASE + i * SLOT_SIZE
        light = slot.get("light", {})
        for key in light:
            if key not in LIGHT_FIELDS:
                raise StrikeError("%s : champ light inconnu %s" % (where, key))
        encode_fixed(kit, base, LIGHT_FIELDS, light, where, "light")
        params = slot.get("params", {})
        encode_fixed(kit, base, PAD_FIELDS, {k: v for k, v in params.items() if k in PAD_FIELDS}, where, "params")
        records = {k: v for k, v in params.items() if k not in PAD_FIELDS}
        masked = is_masked(kit, i)
        encode_params(kit, base + PAD_RECORDS, PAD_LAYOUT, PAD_PARAMS, records, where, masked)
        for wave, woff in WAVES.items():
            if wave not in slot:
                continue
            w = base + woff
            label = "%s %s" % (where, wave)
            header = {k: slot[wave][k] for k in ("sample", "velocity_low", "velocity_high") if k in slot[wave]}
            if header:
                if not wave_header_readable(kit, w):
                    raise StrikeError("%s : sample et vélocité non modifiables dans ce kit" % label)
                if "sample" in header:
                    kit[w : w + 2] = struct.pack(">H", resolve_sample(header["sample"], samples, label))
                low = header.get("velocity_low", kit[w + 2])
                high = header.get("velocity_high", kit[w + 3])
                if (low, high) != (kit[w + 2], kit[w + 3]):
                    if not (
                        isinstance(low, int)
                        and isinstance(high, int)
                        and 0 <= low <= 126
                        and 1 <= high <= 127
                        and low <= high
                    ):
                        raise StrikeError(
                            "%s : velocity_low=%r / velocity_high=%r invalides "
                            "(0–126, 1–127, low ≤ high)" % (label, low, high)
                        )
                    kit[w + 2], kit[w + 3] = low, high
            encode_params(kit, w + WAVE_RECORDS, WAVE_LAYOUT, WAVE_PARAMS, slot[wave].get("params", {}), label, masked)

    kit[8] = kit_checksum(kit)
    return bytes(kit)


COPY_PARTS = ("params", "light", "wave_a", "wave_b")
WAVE_HEADER_KEYS = ("sample", "velocity_low", "velocity_high")


def copy_slot_settings(kit, source, targets, parts, include_midi_note=False):
    """Recopie, dans le JSON `kit`, les réglages de l'emplacement `source` vers `targets`.

    `parts` choisit les sections parmi COPY_PARTS. La note MIDI n'est recopiée que
    si `include_midi_note` est vrai. Retourne les champs non recopiés car illisibles
    dans l'emplacement cible (kits KITC) : [(emplacement, "section.champ")].
    """
    for n in [source, *targets]:
        if not isinstance(n, int) or not 1 <= n <= SLOT_COUNT:
            raise StrikeError("emplacement %r inexistant (1 à %d)" % (n, SLOT_COUNT))
    unknown = set(parts) - set(COPY_PARTS)
    if unknown:
        raise StrikeError("sections inconnues : %s" % ", ".join(sorted(unknown)))
    src = kit["slots"][source - 1]
    skipped = []

    def copy(fields, dest, keys, label, target):
        for key in keys:
            if key == "midi_note" and not include_midi_note:
                continue
            if key in dest:
                dest[key] = fields[key]
            else:
                skipped.append((target, "%s.%s" % (label, key)))

    for target in targets:
        if target == source:
            continue
        dst = kit["slots"][target - 1]
        for part in parts:
            if part in ("params", "light"):
                copy(src[part], dst[part], list(src[part]), part, target)
            else:
                copy(src[part], dst[part], [k for k in WAVE_HEADER_KEYS if k in src[part]], part, target)
                copy(src[part]["params"], dst[part]["params"], list(src[part]["params"]), part + ".params", target)
    return skipped


def slot_field_names():
    """Champs modifiables en groupe, au format « section.clé »."""
    pad = [param_name(PAD_PARAMS, r) for r, _, _ in PAD_LAYOUT] + list(PAD_FIELDS)
    wave = [param_name(WAVE_PARAMS, r) for r, _, _ in WAVE_LAYOUT]
    names = ["params." + n for n in pad] + ["light." + n for n in LIGHT_FIELDS]
    for w in WAVES:
        names += ["%s.%s" % (w, k) for k in WAVE_HEADER_KEYS] + ["%s.params.%s" % (w, n) for n in wave]
    return names


def set_slots_value(kit, targets, field, value):
    """Donne la valeur `value` au champ `field` (ex. « params.sensitivity »,
    « wave_a.params.volume ») des emplacements `targets`, dans le JSON `kit`.

    La valeur est validée à l'encodage du kit. Retourne les emplacements où le
    champ est absent, donc non modifié : [(emplacement, champ)].
    """
    if field not in slot_field_names():
        raise StrikeError("champ inconnu : %s" % field)
    if not targets:
        raise StrikeError("aucun emplacement choisi")
    for n in targets:
        if not isinstance(n, int) or not 1 <= n <= SLOT_COUNT:
            raise StrikeError("emplacement %r inexistant (1 à %d)" % (n, SLOT_COUNT))
    *path, key = field.split(".")
    skipped = []
    for n in targets:
        node = kit["slots"][n - 1]
        for part in path:
            node = node[part]
        if key in node:
            node[key] = value
        else:
            skipped.append((n, field))
    return skipped


def reset_slot_settings(kit, targets, fields):
    """Remet les champs `fields` (« section.clé », voir slot_field_names) des
    emplacements `targets` du JSON `kit` aux valeurs du kit vide de l'appareil,
    propres à chaque emplacement (note MIDI, Sensitivity, éclairage…).

    Retourne les champs absents, donc non modifiés : [(emplacement, champ)].
    """
    unknown = sorted(set(fields) - set(slot_field_names()))
    if unknown:
        raise StrikeError("champs inconnus : %s" % ", ".join(unknown))
    if not fields:
        raise StrikeError("aucun champ choisi")
    if not targets:
        raise StrikeError("aucun emplacement choisi")
    for n in targets:
        if not isinstance(n, int) or not 1 <= n <= SLOT_COUNT:
            raise StrikeError("emplacement %r inexistant (1 à %d)" % (n, SLOT_COUNT))
    empty = decode_kit(EMPTY_KIT)["slots"]
    skipped = []
    for n in targets:
        for field in fields:
            *path, key = field.split(".")
            src, dst = empty[n - 1], kit["slots"][n - 1]
            for part in path:
                src, dst = src[part], dst[part]
            if key in dst and key in src:
                dst[key] = src[key]
            else:
                skipped.append((n, field))
    return skipped


# --------------------------------------------------------------------------
# WAV
# --------------------------------------------------------------------------


def wav_info(data):
    """(canaux, offset des données, taille des données) d'un WAV PCM 16 bits 44,1 kHz."""
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise StrikeError("ce n'est pas un fichier WAV")
    fmt, chunk, o = None, None, 12
    while o + 8 <= len(data):
        cid, size = data[o : o + 4], struct.unpack("<I", data[o + 4 : o + 8])[0]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", data[o + 8 : o + 24])
        elif cid == b"data":
            chunk = (o + 8, size)
        o += 8 + size + (size & 1)
    if fmt is None or chunk is None:
        raise StrikeError("WAV sans chunk fmt ou data")
    tag, channels, rate, _, _, bits = fmt
    if tag != 1 or bits != 16 or rate != 44100 or channels not in (1, 2):
        raise StrikeError(
            "WAV PCM 16 bits, 44,1 kHz, mono ou stéréo requis "
            "(reçu : format %d, %d bits, %d Hz, %d canaux)" % (tag, bits, rate, channels)
        )
    if chunk[0] + chunk[1] > len(data):
        raise StrikeError("WAV tronqué")
    return channels, chunk[0], chunk[1]


def make_had(name, channels, data_off, data_len, path):
    had = bytearray(0xE0)
    had[0:4] = b"INTH"
    had[4:6] = b"\x00\x10"
    had[0x14:0x18] = bytes([16, channels]) + struct.pack(">H", 44100)
    end = data_off + data_len
    had[0x18:0x38] = struct.pack(">8I", data_off, data_off, data_len, 0, data_off, end, data_off, end)
    raw = name.encode("latin-1")
    had[0x3F] = len(raw)
    had[0x40:0x50] = raw[:16].ljust(16, b"\0")
    had[0x58:0x60] = b"PATH" + struct.pack(">I", len(path))
    had[0x60 : 0x60 + len(path)] = path.encode("latin-1")
    had[8] = kit_checksum(had)
    return bytes(had)


# --------------------------------------------------------------------------
# Conteneur .bkf
# --------------------------------------------------------------------------


class Entry:
    def __init__(self, path, name, offset, size):
        self.path, self.name, self.offset, self.size = path, name, offset, size

    @property
    def full(self):
        return self.path + self.name


def norm_path(path):
    return path.replace("S:\\", "").replace("\\", "/")


class Record:
    def __init__(self, path, name, data, pad=None):
        self.path, self.name, self.data, self.pad = path, name, data, pad

    @property
    def full(self):
        return norm_path(self.path) + self.name


def default_pad(size):
    return 32 - size % 16


class Bkf:
    """Sauvegarde .bkf décomposée en enregistrements, reconstructible à l'identique."""

    def __init__(self, header, records):
        self.header, self.records = bytearray(header), records

    @classmethod
    def parse(cls, data):
        if data[:8] != b"PACKBKF ":
            raise StrikeError("ce n'est pas un fichier .bkf (PACKBKF)")
        if sum(data[0x10:0x40]) & 0xFF != data[0x0F]:
            raise StrikeError("somme de contrôle de l'en-tête .bkf invalide")
        records, p = [], 0x40
        while p < len(data):
            if data[p : p + 8] != b"FILEH\0\0\0":
                raise StrikeError("enregistrement FILEH attendu à 0x%x" % p)
            if sum(data[p + 0x10 : p + 0x180]) & 0xFF != data[p + 0x0B]:
                raise StrikeError("somme de contrôle FILEH invalide à 0x%x" % p)
            nxt = struct.unpack("<I", data[p + 0x10 : p + 0x14])[0]
            path = data[p + 0x60 : p + 0xE0].split(b"\0")[0].decode("latin-1")
            name = data[p + 0xF0 : p + 0x170].split(b"\0")[0].decode("latin-1")
            size = struct.unpack("<I", data[p + 0x174 : p + 0x178])[0]
            end = p + 0x180 + size
            if nxt < end or nxt > len(data):
                raise StrikeError("chaînage FILEH invalide à 0x%x" % p)
            records.append(Record(path, name, data[p + 0x180 : end], nxt - end))
            p = nxt
        count = struct.unpack("<I", data[0x10:0x14])[0]
        if count != len(records):
            raise StrikeError("nombre de fichiers incohérent (%d annoncés, %d lus)" % (count, len(records)))
        return cls(data[:0x40], records)

    def serialize(self):
        head = bytearray(self.header)
        head[0x10:0x14] = struct.pack("<I", len(self.records))
        head[0x14:0x18] = struct.pack("<I", sum(1 for r in self.records if r.path.startswith("S:\\WAV\\DATA\\")))
        head[0x0F] = sum(head[0x10:0x40]) & 0xFF
        out = bytearray(head)
        for r in self.records:
            pad = default_pad(len(r.data)) if r.pad is None else r.pad
            meta = bytearray(0x180)
            meta[0:8] = b"FILEH\0\0\0"
            meta[0x10:0x14] = struct.pack("<I", len(out) + 0x180 + len(r.data) + pad)
            meta[0x50:0x58] = b"PATH" + struct.pack("<I", 0x80)
            meta[0x60:0xE0] = r.path.encode("latin-1").ljust(0x80, b"\0")
            meta[0xE0:0xE8] = b"NAME" + struct.pack("<I", 0x80)
            meta[0xF0:0x170] = r.name.encode("latin-1").ljust(0x80, b"\0")
            meta[0x170:0x178] = b"DATA" + struct.pack("<I", len(r.data))
            meta[0x0B] = sum(meta[0x10:0x180]) & 0xFF
            out += meta + r.data + bytes(pad)
        return bytes(out)

    def find(self, full):
        for r in self.records:
            if r.full == full:
                return r
        raise StrikeError("fichier %s absent de la sauvegarde" % full)

    def get_file(self, full):
        return self.find(full).data

    def set_file(self, full, data):
        r = self.find(full)
        if len(data) != len(r.data):
            r.pad = None
        r.data = bytes(data)

    def insert_after_last(self, prefix, record):
        last = max(i for i, r in enumerate(self.records) if r.path.startswith(prefix))
        self.records.insert(last + 1, record)

    # -- samples -----------------------------------------------------------

    def sample_names(self):
        return set(sample_catalog_from_list(self.get_file("WAV/LIST/wave_list_sort_name.lst")).values())

    def add_sample(self, name, wav):
        """Ajoute un sample utilisateur comme le fait l'appareil ; retourne son id."""
        channels, data_off, data_len = wav_info(wav)
        raw = name.encode("latin-1", "strict") if name else b""
        if not raw or len(raw) > 0x7F or b"\0" in raw:
            raise StrikeError("nom de sample invalide : %r" % name)
        if name in self.sample_names():
            raise StrikeError("un sample nommé %r existe déjà" % name)

        wl = bytearray(self.get_file("WAV/LIST/Wave_list.lst"))
        count = struct.unpack(">H", wl[0x0A:0x0C])[0]
        o = 0x20 + 8 * count
        if o + 8 > len(wl):
            raise StrikeError("table des samples pleine")
        flag_id, loc = struct.unpack(">2H", wl[o : o + 4])
        if flag_id != 0x8000 | count:
            raise StrikeError("table des samples non contiguë : cas non pris en charge")
        sid, folder, fileno = count, loc >> 8, loc & 0xFF
        if folder != sid // 100 or fileno != sid % 100 or fileno < 10:
            raise StrikeError("emplacement de sample %03d/%d non vérifié : cas non pris en charge" % (folder, fileno))
        rank = count
        wl[o : o + 2] = struct.pack(">H", sid)
        wl[o + 6 : o + 8] = struct.pack(">H", rank)
        wl[0x0A:0x0C] = struct.pack(">H", count + 1)
        self.set_file("WAV/LIST/Wave_list.lst", wl)

        self._add_sort_num(rank, sid)
        self._add_sort_name(sid, name)
        self._add_group_member("New Sample", sid)
        self._add_sort_size(sid, len(wav))

        rel = "\\%03d\\%d" % (folder, fileno)
        self.insert_after_last(
            "S:\\WAV\\HEAD\\",
            Record(
                "S:\\WAV\\HEAD\\%03d\\" % folder,
                "%d.had" % fileno,
                make_had(name, channels, data_off, data_len, rel + ".wav"),
            ),
        )
        self.insert_after_last(
            "S:\\WAV\\DATA\\", Record("S:\\WAV\\DATA\\%03d\\" % folder, "%d.wav" % fileno, bytes(wav))
        )
        return sid

    def _list(self, name):
        data = bytearray(self.get_file("WAV/LIST/" + name))
        return data, struct.unpack(">H", data[0x0A:0x0C])[0]

    def _save_list(self, name, data, count):
        data[0x0A:0x0C] = struct.pack(">H", count)
        self.set_file("WAV/LIST/" + name, data)

    def _add_sort_num(self, rank, sid):
        data, count = self._list("wave_list_sort_num.lst")
        o = 0x20 + 4 * count
        data[o:o] = struct.pack(">2H", rank, sid)
        self._save_list("wave_list_sort_num.lst", data, count + 1)

    def _add_sort_name(self, sid, name):
        data, count = self._list("wave_list_sort_name.lst")
        key = name.lower()
        pos = count
        for k in range(count):
            o = 0x20 + 0x90 * k
            if data[o + 0x10 : o + 0x90].split(b"\0")[0].decode("latin-1").lower() > key:
                pos = k
                break
        for k in range(pos, count):
            o = 0x20 + 0x90 * k
            data[o : o + 2] = struct.pack(">H", (struct.unpack(">H", data[o : o + 2])[0] + 1) & 0xFFFF)
        entry = bytearray(0x90)
        entry[0:6] = struct.pack(">3H", pos, sid, len(name) + 4)
        entry[0x10:0x90] = name.encode("latin-1").ljust(0x80, b"\0")
        o = 0x20 + 0x90 * pos
        data[o:o] = entry
        self._save_list("wave_list_sort_name.lst", data, count + 1)

    def _add_group_member(self, group, sid):
        data, groups = self._list("wave_list_sort_group.lst")
        o = 0x20
        for _ in range(groups):
            members = struct.unpack(">H", data[o + 1 : o + 3])[0]
            if data[o + 8 : o + 0x18].split(b"\0")[0].decode("latin-1") == group:
                end = o + 0x18 + 4 * members
                data[end:end] = struct.pack(">2H", members, sid)
                data[o + 1 : o + 3] = struct.pack(">H", members + 1)
                self._save_list("wave_list_sort_group.lst", data, groups)
                return
            o += 0x18 + 4 * members
        raise StrikeError("groupe %r introuvable" % group)

    def _add_sort_size(self, sid, size):
        data, count = self._list("WaveList_User_SortSize.lst")
        size_total = len(data)
        pos = count
        for k in range(count):
            if struct.unpack(">I", data[0x24 + 8 * k : 0x28 + 8 * k])[0] >= size:
                pos = k
                break
        o = 0x20 + 8 * pos
        data[o:o] = struct.pack(">2I", sid, size)
        if any(data[size_total:]):
            raise StrikeError("liste des samples utilisateur pleine")
        del data[size_total:]
        self._save_list("WaveList_User_SortSize.lst", data, count + 1)

    def remove_last_sample(self):
        """Annule `add_sample` pour le dernier sample ajouté ; retourne son id.

        Sert à construire la sauvegarde de référence des tests. Le comportement de
        l'appareil lors d'une suppression n'a pas été observé : cette opération
        n'est pas proposée à l'utilisateur. Le rang mémorisé dans Wave_list.lst
        (préréglé par l'appareil sur les entrées libres) est laissé en place.
        """
        wl = bytearray(self.get_file("WAV/LIST/Wave_list.lst"))
        count = struct.unpack(">H", wl[0x0A:0x0C])[0]
        sid = count - 1
        o = 0x20 + 8 * sid
        flag_id, loc = struct.unpack(">2H", wl[o : o + 4])
        if sid < 0 or flag_id != sid:
            raise StrikeError("aucun sample à retirer")
        folder, fileno = loc >> 8, loc & 0xFF

        data, n = self._list("wave_list_sort_num.lst")
        last = 0x20 + 4 * (n - 1)
        if struct.unpack(">H", data[last + 2 : last + 4])[0] != sid:
            raise StrikeError("le sample %d n'est pas le dernier ajouté" % sid)
        del data[last : last + 4]
        self._save_list("wave_list_sort_num.lst", data, n - 1)

        data, n = self._list("wave_list_sort_name.lst")
        pos = next(k for k in range(n) if struct.unpack(">H", data[0x22 + 0x90 * k : 0x24 + 0x90 * k])[0] == sid)
        del data[0x20 + 0x90 * pos : 0x20 + 0x90 * (pos + 1)]
        for k in range(pos, n - 1):
            p = 0x20 + 0x90 * k
            data[p : p + 2] = struct.pack(">H", (struct.unpack(">H", data[p : p + 2])[0] - 1) & 0xFFFF)
        self._save_list("wave_list_sort_name.lst", data, n - 1)

        data, groups = self._list("wave_list_sort_group.lst")
        p = 0x20
        for _ in range(groups):
            members = struct.unpack(">H", data[p + 1 : p + 3])[0]
            if data[p + 8 : p + 0x18].split(b"\0")[0] == b"New Sample":
                end = p + 0x18 + 4 * members
                if members == 0 or struct.unpack(">H", data[end - 2 : end])[0] != sid:
                    raise StrikeError("le sample %d n'est pas le dernier du groupe New Sample" % sid)
                del data[end - 4 : end]
                data[p + 1 : p + 3] = struct.pack(">H", members - 1)
                break
            p += 0x18 + 4 * members
        self._save_list("wave_list_sort_group.lst", data, groups)

        data, n = self._list("WaveList_User_SortSize.lst")
        size_total = len(data)
        k = next(k for k in range(n) if struct.unpack(">I", data[0x20 + 8 * k : 0x24 + 8 * k])[0] == sid)
        del data[0x20 + 8 * k : 0x28 + 8 * k]
        data += bytes(size_total - len(data))
        self._save_list("WaveList_User_SortSize.lst", data, n - 1)

        wl[o : o + 2] = struct.pack(">H", 0x8000 | sid)
        wl[0x0A:0x0C] = struct.pack(">H", count - 1)
        self.set_file("WAV/LIST/Wave_list.lst", wl)
        for kind, ext in (("HEAD", "had"), ("DATA", "wav")):
            self.records.remove(self.find("WAV/%s/%03d/%d.%s" % (kind, folder, fileno, ext)))
        return sid


def parse_bkf(data):
    bkf = Bkf.parse(data)
    entries, p = [], 0x40
    for r in bkf.records:
        entries.append(Entry(norm_path(r.path), r.name, p + 0x180, len(r.data)))
        p += 0x180 + len(r.data) + r.pad
    return entries


def parse_fac(data):
    if data[:4] != b"SDRH":
        raise StrikeError("ce n'est pas un fichier .fac (SDRH)")
    entries, p = [], 0x120
    while data[p : p + 4] == b"FIEH":
        name = data[p + 8 : p + 0x48].split(b"\0")[0].decode("latin-1")
        ext = data[p + 0x48 : p + 0x4C].split(b"\0")[0].decode("latin-1")
        size, off = struct.unpack(">I", data[p + 0x4C : p + 0x50])[0], struct.unpack(">I", data[p + 0x54 : p + 0x58])[0]
        entries.append(Entry("KIT/", "%s.%s" % (name, ext), off, size))
        p += 0x60
    return entries


def parse_container(data):
    if data[:8] == b"PACKBKF ":
        return "bkf", parse_bkf(data)
    if data[:4] == b"SDRH":
        return "fac", parse_fac(data)
    raise StrikeError("format de sauvegarde non reconnu")


def kit_entries(entries):
    return [e for e in entries if e.path.rstrip("/").endswith("KIT") and e.name.endswith(".kit")]


def sample_catalog_from_list(lst):
    catalog = {}
    for p in range(0x20, len(lst) - 0x8F, 0x90):
        sid = struct.unpack(">H", lst[p + 2 : p + 4])[0]
        name = lst[p + 0x10 : p + 0x90].split(b"\0")[0].decode("latin-1")
        if name:
            catalog[sid] = name
    return catalog


def build_catalog(files):
    """id -> nom, à partir de [(chemin normalisé, nom, contenu)] : liste triée par nom et .had."""
    catalog = {}
    for _path, name, content in files:
        if name.lower() == "wave_list_sort_name.lst":
            catalog.update(sample_catalog_from_list(content))
    for path, name, content in files:
        m = re.search(r"HEAD/(\d+)/$", path)
        if m and name.endswith(".had"):
            sid = int(m.group(1)) * 100 + int(name[:-4])
            catalog.setdefault(sid, content[0x40:0x50].split(b"\0")[0].decode("latin-1"))
    return catalog


def sample_catalog(data, entries):
    return build_catalog([(e.path, e.name, data[e.offset : e.offset + e.size]) for e in entries])


def wav_sample_id(path, name):
    m = re.search(r"WAV/DATA/(\d+)/$", path)
    if m and name.lower().endswith(".wav"):
        return int(m.group(1)) * 100 + int(name[:-4])
    return None


class Backup:
    """Sauvegarde .bkf ou .fac chargée en mémoire, modifiable kit par kit."""

    def __init__(self, data):
        self.kind, entries = parse_container(data)
        self.dirty = False
        self._catalog = None
        if self.kind == "bkf":
            self.bkf, self.fac = Bkf.parse(data), None
        else:
            self.bkf, self.fac = None, bytearray(data)
            self._fac_kits = {e.name[:-4]: e for e in kit_entries(entries)}

    @classmethod
    def open(cls, path):
        return cls(Path(path).read_bytes())

    def kit_numbers(self):
        if self.fac is not None:
            return sorted(self._fac_kits)
        return sorted(r.name[:-4] for r in self.bkf.records if norm_path(r.path) == "KIT/" and r.name.endswith(".kit"))

    def get_raw(self, num):
        if num not in self.kit_numbers():
            raise StrikeError("kit %s absent de la sauvegarde" % num)
        if self.fac is not None:
            e = self._fac_kits[num]
            return bytes(self.fac[e.offset : e.offset + e.size])
        return self.bkf.get_file("KIT/%s.kit" % num)

    def _set_raw(self, num, kit):
        if self.fac is not None:
            e = self._fac_kits[num]
            self.fac[e.offset : e.offset + e.size] = kit
        else:
            self.bkf.set_file("KIT/%s.kit" % num, kit)

    def samples(self):
        if self._catalog is None:
            self._catalog = (
                {}
                if self.bkf is None
                else build_catalog([(norm_path(r.path), r.name, r.data) for r in self.bkf.records])
            )
        return self._catalog

    def user_sample_ids(self):
        if self.bkf is None:
            return []
        return sorted(i for i in (wav_sample_id(norm_path(r.path), r.name) for r in self.bkf.records) if i is not None)

    def user_wav(self, sid):
        if self.bkf is not None:
            for r in self.bkf.records:
                if wav_sample_id(norm_path(r.path), r.name) == sid:
                    return r.data
        raise StrikeError("sample %r absent de la sauvegarde (seuls les samples utilisateur y sont)" % sid)

    def decode(self, num):
        return decode_kit(self.get_raw(num), self.samples())

    def _encode(self, num, data):
        """(octets d'origine, octets encodés) du kit `num` modifié selon `data`."""
        raw = self.get_raw(num)
        try:
            return raw, encode_kit(raw, data, self.samples())
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise StrikeError("JSON de kit invalide : %r" % exc) from exc

    def update(self, num, data):
        raw, kit = self._encode(num, data)
        if kit != raw:
            self._set_raw(num, kit)
            self.dirty = True
        return self.decode(num)

    def _two_kits(self, a, b):
        if a == b:
            raise StrikeError("le kit source et le kit cible sont identiques (%s)" % a)
        return self.get_raw(a), self.get_raw(b)

    def copy_kit(self, source, target):
        """Remplace le kit `target` par une copie du kit `source`.

        Un kit ne contient pas son propre numéro : copier ses octets suffit.
        """
        raw, _ = self._two_kits(source, target)
        self._set_raw(target, raw)
        self.dirty = True

    def swap_kits(self, a, b):
        """Échange deux kits (déplacer un kit = l'échanger avec un kit vide)."""
        raw_a, raw_b = self._two_kits(a, b)
        self._set_raw(a, raw_b)
        self._set_raw(b, raw_a)
        self.dirty = True

    def clear_kit(self, num):
        """Supprime le kit `num` : le remplace par le kit vide de l'appareil. Les
        samples utilisateur qu'il référençait restent dans la sauvegarde."""
        if is_empty_kit(self.get_raw(num)):
            return
        self._set_raw(num, EMPTY_KIT)
        self.dirty = True

    def set_slots(self, num, targets, field, value):
        kit = self.decode(num)
        skipped = set_slots_value(kit, targets, field, value)
        return self.update(num, kit), skipped

    def set_slots_in_kits(self, nums, targets, field, value):
        """`set_slots` sur plusieurs kits, mêmes emplacements dans chacun.

        Tout ou rien : chaque kit est validé avant qu'aucun ne soit modifié.
        Retourne les champs absents : [(kit, emplacement, champ)].
        """
        nums = list(dict.fromkeys(nums))
        if not nums:
            raise StrikeError("aucun kit choisi")
        encoded, skipped = [], []
        for num in nums:
            kit = self.decode(num)
            try:
                skipped += [(num, n, f) for n, f in set_slots_value(kit, targets, field, value)]
                encoded.append((num,) + self._encode(num, kit))
            except StrikeError as exc:
                raise StrikeError("kit %s : %s" % (num, exc)) from exc
        for num, raw, kit in encoded:
            if kit != raw:
                self._set_raw(num, kit)
                self.dirty = True
        return skipped

    def reset_slots(self, num, targets, fields):
        kit = self.decode(num)
        skipped = reset_slot_settings(kit, targets, fields)
        return self.update(num, kit), skipped

    def copy_slot(self, num, source, targets, parts, include_midi_note=False):
        kit = self.decode(num)
        skipped = copy_slot_settings(kit, source, targets, parts, include_midi_note)
        return self.update(num, kit), skipped

    def add_sample(self, name, wav):
        if self.bkf is None:
            raise StrikeError("l'ajout de samples n'est possible qu'avec un .bkf")
        sid = self.bkf.add_sample(name, wav)
        self._catalog = None
        self.dirty = True
        return sid

    def serialize(self):
        return bytes(self.fac) if self.fac is not None else self.bkf.serialize()


# --------------------------------------------------------------------------
# Commandes
# --------------------------------------------------------------------------


def safe_filename(text):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "kit"


def wav_filename(name):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name) + ".wav"


def cmd_export(backup, outdir, wav=True):
    b = Backup.open(backup)
    samples = b.samples()
    out = Path(outdir)
    (out / "kits").mkdir(parents=True, exist_ok=True)
    for num in b.kit_numbers():
        kit = b.decode(num)
        path = out / "kits" / ("%s_%s.json" % (num, safe_filename(kit["name"])))
        path.write_text(json.dumps(kit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    wavs = b.user_sample_ids() if wav else []
    if wavs:
        (out / "wav").mkdir(exist_ok=True)
        for sid in wavs:
            (out / "wav" / wav_filename(samples.get(sid, str(sid)))).write_bytes(b.user_wav(sid))
    if samples:
        (out / "samples.json").write_text(
            json.dumps({str(k): v for k, v in sorted(samples.items())}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
    print(
        "%d kits et %d WAV exportés dans %s (%s, %d samples référencés)"
        % (len(b.kit_numbers()), len(wavs), out, b.kind, len(samples))
    )


def kit_jsons(indir):
    files = sorted((Path(indir) / "kits").glob("*.json"))
    if not files:
        raise StrikeError("aucun JSON dans %s/kits" % indir)
    for f in files:
        try:
            yield f, f.name.split("_")[0].split(".")[0], json.loads(f.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise StrikeError("%s : JSON invalide (%s)" % (f.name, exc)) from exc


def import_dir(data, indir):
    b = Backup(data)
    wavs = sorted((Path(indir) / "wav").glob("*.wav")) + sorted((Path(indir) / "wav").glob("*.WAV"))
    if wavs and b.kind != "bkf":
        raise StrikeError("l'ajout de samples n'est possible qu'avec un .bkf")
    known = set(b.samples().values())
    contents = {b.user_wav(i) for i in b.user_sample_ids()}
    for wav in wavs:
        name, content = wav.stem, wav.read_bytes()
        if name in known or content in contents:
            continue
        try:
            sid = b.add_sample(name, content)
        except StrikeError as exc:
            raise StrikeError("%s : %s" % (wav.name, exc)) from exc
        known.add(name)
        contents.add(content)
        print("sample %r ajouté (id %d)" % (name, sid))
    changed = 0
    for f, num, kit in kit_jsons(indir):
        try:
            before = b.get_raw(num)
            b.update(num, kit)
        except StrikeError as exc:
            raise StrikeError("%s : %s" % (f.name, exc)) from exc
        changed += b.get_raw(num) != before
    return b.serialize(), changed


def cmd_import(backup, indir, output):
    if Path(output).resolve() == Path(backup).resolve():
        raise StrikeError("refus d'écraser la sauvegarde d'origine")
    data = Path(backup).read_bytes()
    out, changed = import_dir(data, indir)
    parse_container(out)  # revalide le résultat
    Path(output).write_bytes(out)
    print("%d kit(s) modifié(s), écrit dans %s" % (changed, output))


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="python3 -m strike_kits", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="sauvegarde -> dossier de JSON")
    ex.add_argument("backup")
    ex.add_argument("outdir")
    ex.add_argument("--no-wav", action="store_true", help="ne pas exporter les WAV des samples utilisateur")
    im = sub.add_parser("import", help="dossier de JSON (+ wav/) -> nouvelle sauvegarde")
    im.add_argument("backup", help="sauvegarde d'origine (.bkf ou .fac)")
    im.add_argument("indir", help="dossier produit par export")
    im.add_argument("-o", "--output", required=True, help="fichier de sortie")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "export":
            cmd_export(args.backup, args.outdir, wav=not args.no_wav)
        else:
            cmd_import(args.backup, args.indir, args.output)
    except StrikeError as exc:
        print("Erreur : %s" % exc, file=sys.stderr)
        return 1
    return 0
