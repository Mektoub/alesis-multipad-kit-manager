"""Historique des modifications de la sauvegarde ouverte : annuler / rétablir.

Chaque étape est la liste des paramètres modifiés par une action de
l'utilisateur, avec leur ancienne et leur nouvelle valeur : (kit, chemin dans
le JSON du kit, ancienne valeur, nouvelle valeur). Annuler remet les anciennes
valeurs, rétablir les nouvelles, toujours dans l'ordre inverse : quand une étape
est annulée, toutes celles qui la suivaient le sont déjà.

Seules les modifications de paramètres y entrent (éditeur, copie de réglages,
valeurs par défaut, modification de plusieurs pads ou kits). Déplacer,
transférer ou supprimer un kit remplace des kits entiers, octets non identifiés
compris : l'historique est alors vidé (`clear`). L'ajout d'un sample ne s'annule
pas (`untracked`).

Les envois rapprochés de l'éditeur sur les mêmes paramètres d'un kit (curseur,
saisie d'un nom) ne font qu'une étape : voir `MERGE_SECONDS`.
"""

import time
from dataclasses import dataclass, field

from editor.meta import LABELS, LIGHT_LABELS, TITLES

# nombre maximal d'étapes gardées ; les plus anciennes sont oubliées au-delà
LIMIT = 100
# deux envois de l'éditeur sur les mêmes paramètres d'un kit, à moins de ce délai
# l'un de l'autre, sont fusionnés en une étape
MERGE_SECONDS = 1.5

KIT_TITLES = {"name": "Nom du kit", "level": "Volume du kit", "tempo": "Tempo"}
PART_TITLES = {"wave_a": "Wave A", "wave_b": "Wave B"}


def changes(before, after, path=()):
    """[(chemin, ancienne valeur, nouvelle valeur)] entre deux JSON de kit."""
    if isinstance(before, dict) and isinstance(after, dict):
        return [c for k in before if k in after for c in changes(before[k], after[k], (*path, k))]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [c for i, (a, b) in enumerate(zip(before, after, strict=True)) for c in changes(a, b, (*path, i))]
    return [] if before == after else [(path, before, after)]


def set_path(data, path, value):
    for key in path[:-1]:
        data = data[key]
    data[path[-1]] = value


def describe(path, kit):
    """Libellé d'un paramètre : « P1 · Wave A · Volume », « Nom du kit »."""
    if path[0] != "slots":
        return KIT_TITLES.get(path[0], path[0])
    words = [kit["slots"][path[1]]["_label"]]
    words += [PART_TITLES[p] for p in path[2:-1] if p in PART_TITLES]
    return " · ".join([*words, TITLES.get(path[-1], path[-1])])


def value_text(key, value, samples):
    """Valeur lisible : libellé d'une liste (Curve : « Exp2 »), nom de sample,
    nom de kit entre guillemets, « — » pour aucun sample."""
    if value is None:
        return "—"
    if key == "sample":
        return samples.get(value, str(value))
    if isinstance(value, str):
        return "« %s »" % value
    labels = LABELS[key][0] if key in LABELS else LIGHT_LABELS.get(key)
    if labels and isinstance(value, int) and 0 <= value < len(labels) and labels[value]:
        return labels[value]
    return str(value)


@dataclass
class Entry:
    id: int
    label: str
    changes: list  # [(kit, chemin, ancienne valeur, nouvelle valeur)]
    detail: str = ""  # « 90 → 50 » quand l'étape ne modifie qu'un paramètre
    merge_key: object = None  # étape d'éditeur fusionnable
    time: float = 0.0
    kits: list = field(init=False)

    def __post_init__(self):
        self.kits = list(dict.fromkeys(c[0] for c in self.changes))


class History:
    def __init__(self, limit=LIMIT, clock=time.monotonic):
        self.limit, self.clock = limit, clock
        self.done, self.undone = [], []
        self.next_id = 1
        self.base = 0  # étape qui précède la plus ancienne gardée (0 : ouverture)
        self.saved = 0  # étape du dernier enregistrement ; None : plus atteignable

    @property
    def position(self):
        return self.done[-1].id if self.done else self.base

    @property
    def dirty(self):
        """La sauvegarde diffère-t-elle du fichier enregistré ?"""
        return self.position != self.saved

    def summary(self):
        return {
            "undo": self.done[-1].label if self.done else None,
            "redo": self.undone[-1].label if self.undone else None,
        }

    def track(self, backup, nums, fn, label=None, merge=False):
        """Exécute `fn` (modification des kits `nums`) et en garde une étape.

        `label` : libellé de l'action quand elle modifie plusieurs paramètres ;
        `merge` : envoi de l'éditeur, fusionnable avec le précédent.
        """
        before = {n: backup.decode(n) for n in nums}
        result = fn()
        found = [(n, *c) for n in nums for c in changes(before[n], backup.decode(n))]
        if found:
            key = (tuple(nums), frozenset(c[1] for c in found)) if merge else None
            self._push(found, label, key, before, backup.samples())
        return result

    def entries(self):
        """Étapes de la plus ancienne à la plus récente (`done` : faite, sinon
        annulée), `base` : état avant la plus ancienne, `position` : dernière
        étape faite, `saved` : étape du dernier enregistrement (None : aucune)."""
        rows = [(e, True) for e in self.done] + [(e, False) for e in reversed(self.undone)]
        return {
            "entries": [{"id": e.id, "label": e.label, "detail": e.detail, "done": done} for e, done in rows],
            "base": self.base,
            "position": self.position,
            "saved": self.saved,
        }

    def goto(self, backup, target):
        """Annule ou rétablit jusqu'à ce que `target` (id d'une étape, ou `base`)
        soit la dernière étape faite. Renvoie les kits modifiés ; KeyError si
        l'étape n'est pas dans l'historique."""
        if target != self.base and target not in {e.id for e in self.done + self.undone}:
            raise KeyError(target)
        backwards = target == self.base or any(e.id == target for e in self.done)
        kits = []
        while self.position != target:
            entry = self.undo(backup) if backwards else self.redo(backup)
            kits += [n for n in entry.kits if n not in kits]
        return kits

    def _push(self, found, label, key, before, samples):
        now = self.clock()
        last = self.done[-1] if self.done else None
        self.undone.clear()
        if (
            key is not None
            and last is not None
            and last.merge_key == key
            and now - last.time < MERGE_SECONDS
            and last.id != self.saved
        ):
            old = {(c[0], c[1]): c[2] for c in last.changes}
            merged = [(n, p, old[(n, p)], new) for n, p, _, new in found if old[(n, p)] != new]
            self.done.pop()
            if not merged:  # retour aux valeurs d'avant l'étape
                return
            found = merged
        nums = list(dict.fromkeys(c[0] for c in found))
        detail = ""
        if len(found) == 1:
            num, path, old, new = found[0]
            text = describe(path, before[num])
            detail = "%s → %s" % (value_text(path[-1], old, samples), value_text(path[-1], new, samples))
        else:
            text = label or "%d paramètres" % len(found)
        text = "Kit %s · %s" % (nums[0], text) if len(nums) == 1 else "%s · %d kits" % (text, len(nums))
        self.done.append(Entry(self.next_id, text, found, detail, key, now))
        self.next_id += 1
        if len(self.done) > self.limit:
            self.base = self.done.pop(0).id

    def _apply(self, backup, entry, index):
        for num in entry.kits:
            kit = backup.decode(num)
            for n, path, *values in entry.changes:
                if n == num:
                    set_path(kit, path, values[index])
            backup.update(num, kit)
        backup.dirty = self.dirty

    def undo(self, backup):
        """Annule la dernière étape ; la renvoie (None s'il n'y en a pas)."""
        if not self.done:
            return None
        entry = self.done.pop()
        self.undone.append(entry)
        self._apply(backup, entry, 0)
        return entry

    def redo(self, backup):
        if not self.undone:
            return None
        entry = self.undone.pop()
        self.done.append(entry)
        self._apply(backup, entry, 1)
        return entry

    def mark_saved(self):
        self.saved = self.position

    def untracked(self):
        """Modification hors historique (ajout de sample) : l'état enregistré
        n'est plus atteignable par annuler / rétablir."""
        self.saved = None

    def clear(self):
        """Vide l'historique (kit déplacé, transféré ou supprimé)."""
        self.done.clear()
        self.undone.clear()
        self.base = self.next_id  # position distincte de toutes les précédentes
        self.next_id += 1
        self.saved = None
