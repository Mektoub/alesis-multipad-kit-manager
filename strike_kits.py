#!/usr/bin/env python3
"""Édition des kits de l'Alesis Strike MultiPad via JSON.

Formats pris en charge (rétro-ingénierie, non officiels) :
  - .bkf  « All User Kit And Sample Backup » (en-tête PACKBKF)
  - .fac  « BackUp/STRIKE_BACKUP_KIT.fac »   (en-tête SDRH)

Principe : `export` décode chaque kit en JSON ; `import` repart du fichier de
sauvegarde d'origine, réécrit les kits avec les valeurs du JSON, ajoute les WAV
du dossier `wav/` (.bkf uniquement) et recalcule les sommes de contrôle. Les
octets non décodés sont conservés tels quels, si bien qu'un dossier non modifié
redonne un fichier identique octet pour octet.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

KIT_SIZE = 0x2660
SLOT_COUNT = 24
SLOT_BASE = 0x260
SLOT_SIZE = 0x180

NAME_OFF, NAME_LEN = 0xC0, 16
LEVEL_OFF = 0x0C
TEMPO_OFF = 0x10

# Enregistrements (id, valeur, min, max), dans l'ordre fixe où ils apparaissent
# dans tous les kits. Dans les 8 premiers emplacements des kits KITC, seuls les
# octets « valeur » sont présents (id/min/max remplacés par 0xFF ou 0x00).
PAD_LAYOUT = [(0x00, 0, 100), (0x02, 0, 31), (0x08, 0, 127), (0x09, 0, 4),
              (0x0C, 0, 16), (0x0E, 0, 16), (0x0F, 0, 5), (0x10, 0, 127),
              (0x11, 1, 32), (0x12, 0, 32), (0x13, 0, 7), (0x14, 0, 13),
              (0x15, 0, 1), (0x16, 0, 127), (0x17, 0, 16)]
WAVE_LAYOUT = [(0x00, 0, 100), (0x02, 0, 32), (0x09, 0, 5), (0x10, 0, 127),
               (0x18, 0, 255), (0x19, 0, 1), (0x1A, 0, 100), (0x1B, 0, 100),
               (0x1C, 0, 2)]
PAD_PARAMS = {
    0x00: "volume", 0x02: "pan", 0x08: "midi_note", 0x0C: "sync_group",
    0x0F: "audio_output",
    0x10: "fixed_level", 0x11: "sensitivity", 0x12: "threshold", 0x14: "control",
    0x15: "sound",
}
WAVE_PARAMS = {
    0x00: "volume", 0x02: "pan", 0x1A: "fade_in", 0x1B: "fade_out", 0x1C: "priority",
}
# Éclairage : octet à offset fixe dans l'emplacement -> valeur max.
LIGHT_FIELDS = {"play_color": (0x10, 16), "play_mode": (0x11, 6),
                "stop_color": (0x14, 16), "stop_mode": (0x15, 6)}

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


def record_readable(kit, off, rid, lo, hi):
    """Vrai si l'octet valeur de l'enregistrement à `off` est exploitable."""
    return (kit[off] in (rid, 0xFF, 0x00)
            and (kit[off + 2], kit[off + 3]) in ((lo, hi), (0xFF, 0xFF), (0, 0)))


def decode_params(kit, start, layout, table):
    out = {}
    for k, (rid, lo, hi) in enumerate(layout):
        off = start + 4 * k
        if record_readable(kit, off, rid, lo, hi):
            out[param_name(table, rid)] = kit[off + 1]
    return out


def encode_params(kit, start, layout, table, params, where):
    for name, value in params.items():
        if name.startswith("_"):
            continue
        k = layout_index(layout, table, name)
        rid, lo, hi = layout[k]
        off = start + 4 * k
        if not record_readable(kit, off, rid, lo, hi):
            raise StrikeError("%s : %s non modifiable dans ce kit" % (where, name))
        if kit[off + 1] == value:
            continue
        if not isinstance(value, int) or not lo <= value <= hi:
            raise StrikeError("%s : %s=%r hors plage [%d, %d]" % (where, name, value, lo, hi))
        kit[off + 1] = value


def wave_header_readable(kit, w):
    return kit[w + 2] <= kit[w + 3] <= 127


def slot_label(index):
    return "P%d" % (index + 1) if index < 9 else "slot %d" % (index + 1)


def kit_format(kit):
    kind = bytes(kit[:4]).decode("ascii", "replace")
    if kind not in ("KITH", "KITC"):
        raise StrikeError("kit inconnu : %r" % kind)
    return kind


def decode_kit(kit, samples=None):
    samples = samples or {}
    out = {
        "format": kit_format(kit),
        "name": bytes(kit[NAME_OFF:NAME_OFF + NAME_LEN]).split(b"\0")[0].decode("latin-1"),
        "level": kit[LEVEL_OFF],
        "tempo": struct.unpack(">H", kit[TEMPO_OFF:TEMPO_OFF + 2])[0] / 10,
        "slots": [],
    }
    for i in range(SLOT_COUNT):
        base = SLOT_BASE + i * SLOT_SIZE
        slot = {"slot": i + 1, "_label": slot_label(i)}
        slot["light"] = {k: kit[base + o] for k, (o, hi) in LIGHT_FIELDS.items() if kit[base + o] <= hi}
        slot["params"] = decode_params(kit, base + PAD_RECORDS, PAD_LAYOUT, PAD_PARAMS)
        for wave, woff in WAVES.items():
            w = base + woff
            entry = {}
            if wave_header_readable(kit, w):
                sid = struct.unpack(">H", kit[w:w + 2])[0]
                entry["sample"] = None if sid == NO_SAMPLE else sid
                if sid in samples:
                    entry["_sample_name"] = samples[sid]
                entry["velocity_low"], entry["velocity_high"] = kit[w + 2], kit[w + 3]
            entry["params"] = decode_params(kit, w + WAVE_RECORDS, WAVE_LAYOUT, WAVE_PARAMS)
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
        raise StrikeError("%s : nom de sample ambigu %r (ids %s), utiliser l'id"
                          % (where, value, ", ".join(map(str, sorted(ids)))))
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
    if name != bytes(kit[NAME_OFF:NAME_OFF + NAME_LEN]).split(b"\0")[0]:
        kit[NAME_OFF:NAME_OFF + NAME_LEN] = name.ljust(NAME_LEN, b"\0")

    if data["level"] != kit[LEVEL_OFF]:
        if not 0 <= data["level"] <= 100:
            raise StrikeError("level hors plage [0, 100]")
        kit[LEVEL_OFF] = data["level"]
    tempo = round(data["tempo"] * 10)
    if tempo != struct.unpack(">H", kit[TEMPO_OFF:TEMPO_OFF + 2])[0]:
        if not 300 <= tempo <= 2800:
            raise StrikeError("tempo hors plage [30, 280]")
        kit[TEMPO_OFF:TEMPO_OFF + 2] = struct.pack(">H", tempo)

    for slot in data["slots"]:
        i = slot["slot"] - 1
        where = "emplacement %d" % slot["slot"]
        if not 0 <= i < SLOT_COUNT:
            raise StrikeError("%s inexistant" % where)
        base = SLOT_BASE + i * SLOT_SIZE
        for key, value in slot.get("light", {}).items():
            if key not in LIGHT_FIELDS:
                raise StrikeError("%s : champ light inconnu %s" % (where, key))
            off, limit = LIGHT_FIELDS[key]
            if kit[base + off] == value:
                continue
            if kit[base + off] > limit:
                raise StrikeError("%s : light.%s non modifiable dans ce kit" % (where, key))
            if not isinstance(value, int) or not 0 <= value <= limit:
                raise StrikeError("%s : light.%s=%r hors plage [0, %d]" % (where, key, value, limit))
            kit[base + off] = value
        encode_params(kit, base + PAD_RECORDS, PAD_LAYOUT, PAD_PARAMS, slot.get("params", {}), where)
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
                    kit[w:w + 2] = struct.pack(">H", resolve_sample(header["sample"], samples, label))
                low = header.get("velocity_low", kit[w + 2])
                high = header.get("velocity_high", kit[w + 3])
                if (low, high) != (kit[w + 2], kit[w + 3]):
                    if not (isinstance(low, int) and isinstance(high, int)
                            and 0 <= low <= 126 and 1 <= high <= 127 and low <= high):
                        raise StrikeError("%s : velocity_low=%r / velocity_high=%r invalides "
                                          "(0–126, 1–127, low ≤ high)" % (label, low, high))
                    kit[w + 2], kit[w + 3] = low, high
            encode_params(kit, w + WAVE_RECORDS, WAVE_LAYOUT, WAVE_PARAMS,
                          slot[wave].get("params", {}), label)

    kit[8] = kit_checksum(kit)
    return bytes(kit)


# --------------------------------------------------------------------------
# WAV
# --------------------------------------------------------------------------

def wav_info(data):
    """(canaux, offset des données, taille des données) d'un WAV PCM 16 bits 44,1 kHz."""
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise StrikeError("ce n'est pas un fichier WAV")
    fmt, chunk, o = None, None, 12
    while o + 8 <= len(data):
        cid, size = data[o:o + 4], struct.unpack("<I", data[o + 4:o + 8])[0]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", data[o + 8:o + 24])
        elif cid == b"data":
            chunk = (o + 8, size)
        o += 8 + size + (size & 1)
    if fmt is None or chunk is None:
        raise StrikeError("WAV sans chunk fmt ou data")
    tag, channels, rate, _, _, bits = fmt
    if tag != 1 or bits != 16 or rate != 44100 or channels not in (1, 2):
        raise StrikeError("WAV PCM 16 bits, 44,1 kHz, mono ou stéréo requis "
                          "(reçu : format %d, %d bits, %d Hz, %d canaux)" % (tag, bits, rate, channels))
    if chunk[0] + chunk[1] > len(data):
        raise StrikeError("WAV tronqué")
    return channels, chunk[0], chunk[1]


def make_had(name, channels, data_off, data_len, path):
    had = bytearray(0xE0)
    had[0:4] = b"INTH"
    had[4:6] = b"\x00\x10"
    had[0x14:0x18] = bytes([16, channels]) + struct.pack(">H", 44100)
    end = data_off + data_len
    had[0x18:0x38] = struct.pack(">8I", data_off, data_off, data_len, 0,
                                 data_off, end, data_off, end)
    raw = name.encode("latin-1")
    had[0x3F] = len(raw)
    had[0x40:0x50] = raw[:16].ljust(16, b"\0")
    had[0x58:0x60] = b"PATH" + struct.pack(">I", len(path))
    had[0x60:0x60 + len(path)] = path.encode("latin-1")
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
            if data[p:p + 8] != b"FILEH\0\0\0":
                raise StrikeError("enregistrement FILEH attendu à 0x%x" % p)
            if sum(data[p + 0x10:p + 0x180]) & 0xFF != data[p + 0x0B]:
                raise StrikeError("somme de contrôle FILEH invalide à 0x%x" % p)
            nxt = struct.unpack("<I", data[p + 0x10:p + 0x14])[0]
            path = data[p + 0x60:p + 0xE0].split(b"\0")[0].decode("latin-1")
            name = data[p + 0xF0:p + 0x170].split(b"\0")[0].decode("latin-1")
            size = struct.unpack("<I", data[p + 0x174:p + 0x178])[0]
            end = p + 0x180 + size
            if nxt < end or nxt > len(data):
                raise StrikeError("chaînage FILEH invalide à 0x%x" % p)
            records.append(Record(path, name, data[p + 0x180:end], nxt - end))
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
        flag_id, loc = struct.unpack(">2H", wl[o:o + 4])
        if flag_id != 0x8000 | count:
            raise StrikeError("table des samples non contiguë : cas non pris en charge")
        sid, folder, fileno = count, loc >> 8, loc & 0xFF
        if folder != sid // 100 or fileno != sid % 100 or fileno < 10:
            raise StrikeError("emplacement de sample %03d/%d non vérifié : cas non pris en charge"
                              % (folder, fileno))
        rank = count
        wl[o:o + 2] = struct.pack(">H", sid)
        wl[o + 6:o + 8] = struct.pack(">H", rank)
        wl[0x0A:0x0C] = struct.pack(">H", count + 1)
        self.set_file("WAV/LIST/Wave_list.lst", wl)

        self._add_sort_num(rank, sid)
        self._add_sort_name(sid, name)
        self._add_group_member("New Sample", sid)
        self._add_sort_size(sid, len(wav))

        rel = "\\%03d\\%d" % (folder, fileno)
        self.insert_after_last("S:\\WAV\\HEAD\\", Record(
            "S:\\WAV\\HEAD\\%03d\\" % folder, "%d.had" % fileno,
            make_had(name, channels, data_off, data_len, rel + ".wav")))
        self.insert_after_last("S:\\WAV\\DATA\\", Record(
            "S:\\WAV\\DATA\\%03d\\" % folder, "%d.wav" % fileno, bytes(wav)))
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
            if data[o + 0x10:o + 0x90].split(b"\0")[0].decode("latin-1").lower() > key:
                pos = k
                break
        for k in range(pos, count):
            o = 0x20 + 0x90 * k
            data[o:o + 2] = struct.pack(">H", (struct.unpack(">H", data[o:o + 2])[0] + 1) & 0xFFFF)
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
            members = struct.unpack(">H", data[o + 1:o + 3])[0]
            if data[o + 8:o + 0x18].split(b"\0")[0].decode("latin-1") == group:
                end = o + 0x18 + 4 * members
                data[end:end] = struct.pack(">2H", members, sid)
                data[o + 1:o + 3] = struct.pack(">H", members + 1)
                self._save_list("wave_list_sort_group.lst", data, groups)
                return
            o += 0x18 + 4 * members
        raise StrikeError("groupe %r introuvable" % group)

    def _add_sort_size(self, sid, size):
        data, count = self._list("WaveList_User_SortSize.lst")
        size_total = len(data)
        pos = count
        for k in range(count):
            if struct.unpack(">I", data[0x24 + 8 * k:0x28 + 8 * k])[0] >= size:
                pos = k
                break
        o = 0x20 + 8 * pos
        data[o:o] = struct.pack(">2I", sid, size)
        if any(data[size_total:]):
            raise StrikeError("liste des samples utilisateur pleine")
        del data[size_total:]
        self._save_list("WaveList_User_SortSize.lst", data, count + 1)


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
    while data[p:p + 4] == b"FIEH":
        name = data[p + 8:p + 0x48].split(b"\0")[0].decode("latin-1")
        ext = data[p + 0x48:p + 0x4C].split(b"\0")[0].decode("latin-1")
        size, off = struct.unpack(">I", data[p + 0x4C:p + 0x50])[0], struct.unpack(">I", data[p + 0x54:p + 0x58])[0]
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
        sid = struct.unpack(">H", lst[p + 2:p + 4])[0]
        name = lst[p + 0x10:p + 0x90].split(b"\0")[0].decode("latin-1")
        if name:
            catalog[sid] = name
    return catalog


def sample_catalog(data, entries):
    """id -> nom, à partir de la liste triée par nom et des en-têtes .had."""
    catalog = {}
    for e in entries:
        if e.name.lower() == "wave_list_sort_name.lst":
            catalog.update(sample_catalog_from_list(data[e.offset:e.offset + e.size]))
    for e in entries:
        m = re.search(r"HEAD/(\d+)/$", e.path)
        if m and e.name.endswith(".had"):
            had = data[e.offset:e.offset + e.size]
            sid = int(m.group(1)) * 100 + int(e.name[:-4])
            catalog.setdefault(sid, had[0x40:0x50].split(b"\0")[0].decode("latin-1"))
    return catalog


# --------------------------------------------------------------------------
# Commandes
# --------------------------------------------------------------------------

def safe_filename(text):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "kit"


def wav_filename(name):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name) + ".wav"


def user_wavs(data, entries):
    """[(id, contenu)] des samples utilisateur présents dans la sauvegarde."""
    out = []
    for e in entries:
        m = re.search(r"WAV/DATA/(\d+)/$", e.path)
        if m and e.name.lower().endswith(".wav"):
            out.append((int(m.group(1)) * 100 + int(e.name[:-4]), data[e.offset:e.offset + e.size]))
    return out


def cmd_export(backup, outdir, wav=True):
    data = Path(backup).read_bytes()
    kind, entries = parse_container(data)
    samples = sample_catalog(data, entries)
    out = Path(outdir)
    (out / "kits").mkdir(parents=True, exist_ok=True)
    for e in kit_entries(entries):
        kit = decode_kit(data[e.offset:e.offset + e.size], samples)
        num = e.name[:-4]
        path = out / "kits" / ("%s_%s.json" % (num, safe_filename(kit["name"])))
        path.write_text(json.dumps(kit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    wavs = user_wavs(data, entries) if wav else []
    if wavs:
        (out / "wav").mkdir(exist_ok=True)
        for sid, content in wavs:
            (out / "wav" / wav_filename(samples.get(sid, str(sid)))).write_bytes(content)
    if samples:
        (out / "samples.json").write_text(
            json.dumps({str(k): v for k, v in sorted(samples.items())}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
    print("%d kits et %d WAV exportés dans %s (%s, %d samples référencés)"
          % (len(kit_entries(entries)), len(wavs), out, kind, len(samples)))


def kit_jsons(indir):
    files = sorted((Path(indir) / "kits").glob("*.json"))
    if not files:
        raise StrikeError("aucun JSON dans %s/kits" % indir)
    for f in files:
        try:
            yield f, f.name.split("_")[0].split(".")[0], json.loads(f.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise StrikeError("%s : JSON invalide (%s)" % (f.name, exc))


def apply_kit(f, raw, data, samples):
    try:
        return encode_kit(raw, data, samples)
    except (StrikeError, KeyError, TypeError, ValueError) as exc:
        raise StrikeError("%s : %s" % (f.name, exc))


def import_bkf(data, indir):
    bkf = Bkf.parse(data)
    samples = sample_catalog(data, parse_bkf(data))
    known = set(samples.values())
    contents = {c for _, c in user_wavs(data, parse_bkf(data))}
    for wav in sorted((Path(indir) / "wav").glob("*.wav")) + sorted((Path(indir) / "wav").glob("*.WAV")):
        name, content = wav.stem, wav.read_bytes()
        if name in known or content in contents:
            continue
        try:
            sid = bkf.add_sample(name, content)
        except StrikeError as exc:
            raise StrikeError("%s : %s" % (wav.name, exc))
        samples[sid] = name
        known.add(name)
        contents.add(content)
        print("sample %r ajouté (id %d)" % (name, sid))
    changed = 0
    for f, num, kit in kit_jsons(indir):
        full = "KIT/%s.kit" % num
        raw = bkf.get_file(full)
        new = apply_kit(f, raw, kit, samples)
        if new != raw:
            bkf.set_file(full, new)
            changed += 1
    return bkf.serialize(), changed


def import_fac(data, indir):
    data = bytearray(data)
    if any((Path(indir) / "wav").glob("*.[wW][aA][vV]")):
        raise StrikeError("l'ajout de samples n'est possible qu'avec un .bkf")
    by_num = {e.name[:-4]: e for e in kit_entries(parse_fac(bytes(data)))}
    changed = 0
    for f, num, kit in kit_jsons(indir):
        if num not in by_num:
            raise StrikeError("%s : kit %s absent de la sauvegarde" % (f.name, num))
        e = by_num[num]
        raw = bytes(data[e.offset:e.offset + e.size])
        new = apply_kit(f, raw, kit, {})
        if new != raw:
            data[e.offset:e.offset + e.size] = new
            changed += 1
    return bytes(data), changed


def cmd_import(backup, indir, output):
    if Path(output).resolve() == Path(backup).resolve():
        raise StrikeError("refus d'écraser la sauvegarde d'origine")
    data = Path(backup).read_bytes()
    kind, _ = parse_container(data)
    out, changed = (import_bkf if kind == "bkf" else import_fac)(data, indir)
    parse_container(out)  # revalide le résultat
    Path(output).write_bytes(out)
    print("%d kit(s) modifié(s), écrit dans %s" % (changed, output))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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


if __name__ == "__main__":
    sys.exit(main())
