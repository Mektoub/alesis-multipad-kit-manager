"""API de l'éditeur : une sauvegarde ouverte à la fois, éditée en mémoire.

Un seul mode, pour l'application Electron comme pour le lancement local
(./dev.sh serve) : chaque requête /api/* doit porter l'en-tête X-KitManager-Token avec
le jeton donné au lancement, et les fichiers sont ouverts et enregistrés par
chemin absolu, comme dans tout éditeur, mais seulement dans les dossiers
autorisés : le dossier personnel, les supports amovibles de l'utilisateur et les
dossiers ajoutés au lancement (--allow), chemins résolus.
« Enregistrer » écrit dans le fichier ouvert ; au premier enregistrement d'une
session sur un fichier d'origine, son état précédent est copié dans <fichier>.N.bak.
Les préférences de l'utilisateur (editor/preferences.py) sont servies par
/api/preferences.
"""

import getpass
import json
import os
import secrets
import shutil
import string
import sys
import threading
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import strike_kits as sk
from editor.history import History
from editor.meta import TITLES, meta
from editor.preferences import Preferences

WEB_DIST = Path(__file__).resolve().parent / "web" / "dist"
# noms et version de l'application (à la racine du dépôt ; à côté du paquet editor/ une fois figé)
APP_NAMES = json.loads((Path(__file__).resolve().parent.parent / "app-names.json").read_text(encoding="utf-8"))
EXTENSIONS = (".bkf", ".fac")
TOKEN_HEADER = "X-KitManager-Token"
UNSAVED = "des modifications ne sont pas enregistrées"


class OpenRequest(BaseModel):
    path: str
    force: bool = False


class SaveRequest(BaseModel):
    path: str | None = None  # absent : enregistrer dans le fichier ouvert
    overwrite: bool = False


class CopyRequest(BaseModel):
    source: int
    targets: list[int]
    parts: list[str]
    include_midi_note: bool = False


class SetRequest(BaseModel):
    targets: list[int]
    field: str
    value: int | str | None


class MultiSetRequest(SetRequest):
    kits: list[str]


class ResetRequest(BaseModel):
    targets: list[int]
    fields: list[str]


class MoveRequest(BaseModel):
    target: str


class GotoRequest(BaseModel):
    id: int


class TransferRequest(BaseModel):
    target: str
    mode: Literal["copy", "swap"]


def default_roots(platform=sys.platform, env=os.environ):
    """Zone autorisée par défaut : le dossier personnel et les supports amovibles
    de l'utilisateur (clé USB, Strike branché en USB) ; sous Windows, tous les
    lecteurs sauf celui du système, même branchés après le lancement."""
    home = str(Path.home())
    if platform == "win32":
        system = env.get("SystemDrive", "C:").upper()
        return [home, *("%s:\\" % c for c in string.ascii_uppercase if "%s:" % c != system)]
    if platform == "darwin":
        return [home, "/Volumes"]
    user = getpass.getuser()
    return [home, "/media/" + user, "/run/media/" + user]


def outside_roots(path, roots):
    """Message d'erreur si `path` (résolu) n'est dans aucun des `roots`, sinon None."""
    if any(path.is_relative_to(root) for root in roots):
        return None
    return "hors des dossiers autorisés (%s) : %s" % (", ".join(str(r) for r in roots), path)


def next_backup_path(path):
    """Premier <fichier>.N.bak libre (N = 1, 2…)."""
    n = 1
    while path.with_name("%s.%d.bak" % (path.name, n)).exists():
        n += 1
    return path.with_name("%s.%d.bak" % (path.name, n))


class Session:
    def __init__(self, roots, preferences):
        self.roots = roots  # dossiers autorisés, résolus
        self.preferences = preferences
        self.backup = None
        self.file = None  # fichier ouvert (chemin absolu)
        self.original = False  # le fichier ouvert n'a pas été écrit par l'éditeur
        self.backed_up = False  # copie .bak déjà faite pour cette session
        self.history = self.new_history()  # annuler / rétablir (editor/history.py)
        self.lock = threading.Lock()

    def resolve(self, path):
        """Chemin absolu résolu (liens symboliques suivis), dans la zone autorisée."""
        p = Path(path)
        if not p.is_absolute():
            raise HTTPException(400, "chemin absolu attendu : %s" % path)
        p = p.resolve()
        error = outside_roots(p, self.roots)
        if error:
            raise HTTPException(403, error)
        return p

    def check_unsaved(self, force):
        """409 si des modifications seraient perdues, sauf confirmation (`force`)."""
        if self.backup is not None and self.backup.dirty and not force:
            raise HTTPException(409, UNSAVED)

    def require(self):
        if self.backup is None:
            raise HTTPException(409, "aucune sauvegarde ouverte")
        return self.backup

    def new_history(self):
        return History(limit=self.preferences["history_limit"])

    def set_opened(self, backup, path):
        self.backup, self.file, self.original, self.backed_up = backup, path, True, False
        self.history = self.new_history()
        self.preferences.opened(path)

    def state(self):
        if self.backup is None:
            return {"path": None}
        b = self.backup
        kits = []
        for num in b.kit_numbers():
            raw = b.get_raw(num)
            kits.append(
                {
                    "num": num,
                    "format": sk.kit_format(raw),
                    "name": sk.decode_kit(raw)["name"],
                    "empty": sk.is_empty_kit(raw),
                }
            )
        return {
            "path": str(self.file),
            "kind": b.kind,
            "dirty": b.dirty,
            "kits": kits,
            "user_samples": len(b.user_sample_ids()),
            "history": self.history.summary(),
        }


def load_backup(path, roots=None):
    """Sauvegarde .bkf/.fac du chemin absolu `path`, dans `roots` s'ils sont
    donnés ; StrikeError sinon."""
    path = Path(path)
    if not path.is_absolute():
        raise sk.StrikeError("chemin absolu attendu : %s" % path)
    error = roots is not None and outside_roots(path.resolve(), roots)
    if error:
        raise sk.StrikeError(error)
    if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
        raise sk.StrikeError("sauvegarde introuvable : %s" % path)
    return sk.Backup.open(path)


def field_title(field):
    """« params.sensitivity » → « Sensitivity »."""
    name = field.rsplit(".", 1)[-1]
    return TITLES.get(name, name)


def strike_errors(fn):
    try:
        return fn()
    except sk.StrikeError as exc:
        raise HTTPException(400, str(exc)) from exc


def create_app(token, open_file=None, allow=(), preferences=None):
    """`token` : jeton exigé sur /api/* ; `open_file` : sauvegarde ouverte au
    démarrage ; `allow` : dossiers autorisés en plus de la zone par défaut ;
    `preferences` : Preferences de l'utilisateur (par défaut, en mémoire).

    Sans `open_file`, la dernière sauvegarde est rouverte si la préférence
    reopen_last le demande (rien si elle n'est plus lisible)."""
    if not token:
        raise ValueError("un jeton est obligatoire")
    s = Session([Path(r).resolve() for r in [*default_roots(), *allow]], preferences or Preferences())
    if open_file is not None:
        path = Path(open_file)
        s.set_opened(load_backup(path, s.roots), path.resolve())
    elif s.preferences["reopen_last"] and s.preferences["recent_files"]:
        path = Path(s.preferences["recent_files"][0])
        try:
            s.set_opened(load_backup(path, s.roots), path.resolve())
        except sk.StrikeError:
            pass
    app = FastAPI(title=APP_NAMES["long"], version=APP_NAMES["version"])

    @app.middleware("http")
    async def require_token(request: Request, call_next):
        if request.url.path.startswith("/api/") and not secrets.compare_digest(
            request.headers.get(TOKEN_HEADER, ""), token
        ):
            return JSONResponse({"detail": "jeton absent ou invalide"}, status_code=403)
        return await call_next(request)

    @app.post("/api/open")
    def open_backup(req: OpenRequest):
        path = s.resolve(req.path)
        with s.lock:
            s.check_unsaved(req.force)
        backup = strike_errors(lambda: load_backup(path))
        with s.lock:
            s.check_unsaved(req.force)  # une modification a pu arriver pendant la lecture
            s.set_opened(backup, path)
            return s.state()

    @app.get("/api/state")
    def state():
        with s.lock:
            return s.state()

    @app.get("/api/meta")
    def get_meta():
        return meta()

    def kit_or_404(num):
        b = s.require()
        if num not in b.kit_numbers():
            raise HTTPException(404, "kit %s inexistant" % num)
        return b

    def kit_result(kit, skipped):
        return {"kit": kit, "skipped": [{"slot": n, "field": f} for n, f in skipped], "history": s.history.summary()}

    @app.get("/api/kits/{num}")
    def get_kit(num: str):
        with s.lock:
            return kit_or_404(num).decode(num)

    @app.put("/api/kits/{num}")
    def put_kit(num: str, kit: dict):
        with s.lock:
            b = kit_or_404(num)
            return strike_errors(lambda: s.history.track(b, [num], lambda: b.update(num, kit), merge=True))

    @app.post("/api/kits/{num}/copy")
    def copy_slot(num: str, req: CopyRequest):
        with s.lock:
            b = kit_or_404(num)
            label = "Copie des réglages de %s" % sk.slot_label(req.source - 1)
            kit, skipped = strike_errors(
                lambda: s.history.track(
                    b, [num], lambda: b.copy_slot(num, req.source, req.targets, req.parts, req.include_midi_note), label
                )
            )
            return kit_result(kit, skipped)

    @app.post("/api/kits/set")
    def set_slots_in_kits(req: MultiSetRequest):
        """Même valeur, mêmes emplacements, dans plusieurs kits (tout ou rien)."""
        with s.lock:
            b = s.require()
            nums = [n for n in dict.fromkeys(req.kits) if n in b.kit_numbers()]
            skipped = strike_errors(
                lambda: s.history.track(
                    b,
                    nums,
                    lambda: b.set_slots_in_kits(req.kits, req.targets, req.field, req.value),
                    field_title(req.field),
                )
            )
            return dict(s.state(), skipped=[{"kit": k, "slot": n, "field": f} for k, n, f in skipped])

    @app.post("/api/kits/{num}/set")
    def set_slots(num: str, req: SetRequest):
        """Applique une même valeur à un champ de plusieurs emplacements."""
        with s.lock:
            b = kit_or_404(num)
            kit, skipped = strike_errors(
                lambda: s.history.track(
                    b, [num], lambda: b.set_slots(num, req.targets, req.field, req.value), field_title(req.field)
                )
            )
            return kit_result(kit, skipped)

    @app.post("/api/kits/{num}/reset")
    def reset_slots(num: str, req: ResetRequest):
        """Remet des champs d'emplacements aux valeurs du kit vide de l'appareil."""
        with s.lock:
            b = kit_or_404(num)
            kit, skipped = strike_errors(
                lambda: s.history.track(
                    b, [num], lambda: b.reset_slots(num, req.targets, req.fields), "Valeurs par défaut"
                )
            )
            return kit_result(kit, skipped)

    @app.post("/api/kits/{num}/move")
    def move_kit(num: str, req: MoveRequest):
        """Déplace le kit au numéro `target` ; les kits entre les deux se décalent."""
        with s.lock:
            b = kit_or_404(num)
            strike_errors(lambda: b.move_kit(num, req.target))
            s.history.clear()  # kits entiers remplacés : hors historique
            return s.state()

    @app.post("/api/kits/{num}/transfer")
    def transfer_kit(num: str, req: TransferRequest):
        """Copie le kit `num` vers `target`, ou échange les deux kits."""
        with s.lock:
            b = kit_or_404(num)
            op = b.copy_kit if req.mode == "copy" else b.swap_kits
            strike_errors(lambda: op(num, req.target))
            s.history.clear()
            return s.state()

    @app.post("/api/kits/{num}/clear")
    def clear_kit(num: str):
        """Supprime le kit : le remplace par le kit vide de l'appareil."""
        with s.lock:
            kit_or_404(num).clear_kit(num)
            s.history.clear()
            return s.state()

    @app.get("/api/samples")
    def samples():
        with s.lock:
            b = s.require()
            user = set(b.user_sample_ids())
            return [{"id": sid, "name": name, "user": sid in user} for sid, name in sorted(b.samples().items())]

    @app.get("/api/samples/{sid}/wav")
    def sample_wav(sid: int):
        with s.lock:
            b = s.require()
            if sid not in b.user_sample_ids():
                raise HTTPException(404, "seuls les samples utilisateur sont dans la sauvegarde")
            return Response(b.user_wav(sid), media_type="audio/wav")

    @app.post("/api/samples")
    async def add_sample(file: Annotated[UploadFile, File()]):
        content = await file.read()
        name = Path(file.filename or "").stem
        with s.lock:
            b = s.require()
            sid = strike_errors(lambda: b.add_sample(name, content))
            s.history.untracked()  # l'ajout d'un sample ne s'annule pas
            return {"id": sid, "name": name, "user": True}

    @app.post("/api/save")
    def save(req: SaveRequest):
        """Sans chemin : « Enregistrer » dans le fichier ouvert. Avec un chemin :
        « Enregistrer sous » (confirmation si un autre fichier existe déjà)."""
        with s.lock:
            b = s.require()
            path = s.file if req.path is None else s.resolve(req.path)
            if path.suffix.lower() != "." + b.kind:
                raise HTTPException(400, "l'extension doit être .%s" % b.kind)
            same = path == s.file
            if not same and path.exists() and not req.overwrite:
                raise HTTPException(409, "le fichier existe déjà : %s" % path)
            data = b.serialize()
            strike_errors(lambda: sk.parse_container(data))
            if same and s.original and not s.backed_up and path.exists():
                shutil.copy2(path, next_backup_path(path))
                s.backed_up = True
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            if not same:
                s.file, s.original = path, False
                s.preferences.opened(path)
            b.dirty = False
            s.history.mark_saved()
            return s.state()

    @app.get("/api/preferences")
    def get_preferences():
        with s.lock:
            return s.preferences.get()

    @app.patch("/api/preferences")
    def patch_preferences(changes: dict):
        """Modifie les préférences données (toutes valides, ou aucune : 400)."""
        with s.lock:
            try:
                values = s.preferences.update(changes)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from None
            s.history.set_limit(values["history_limit"])
            return values

    def step(name):
        with s.lock:
            b = s.require()
            entry = getattr(s.history, name)(b)
            if entry is None:
                raise HTTPException(409, "rien à %s" % ("annuler" if name == "undo" else "rétablir"))
            return dict(s.state(), done=entry.label, detail=entry.detail, changed=entry.kits)

    @app.get("/api/history")
    def history():
        """Étapes de l'historique, de la plus ancienne à la plus récente."""
        with s.lock:
            s.require()
            return s.history.entries()

    @app.post("/api/history/goto")
    def history_goto(req: GotoRequest):
        """Annule ou rétablit jusqu'à l'étape `id` (`base` : avant la plus ancienne)."""
        with s.lock:
            b = s.require()
            try:
                changed = s.history.goto(b, req.id)
            except KeyError:
                raise HTTPException(404, "étape %s absente de l'historique" % req.id) from None
            return dict(s.state(), changed=changed)

    @app.post("/api/undo")
    def undo():
        """Annule la dernière modification de paramètres ; `done` : son libellé,
        `changed` : les kits modifiés."""
        return step("undo")

    @app.post("/api/redo")
    def redo():
        """Rétablit la dernière modification annulée."""
        return step("redo")

    if WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(WEB_DIST / "index.html")

    return app
