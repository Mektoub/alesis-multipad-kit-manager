"""API de l'éditeur : une sauvegarde ouverte à la fois, éditée en mémoire.

Les chemins sont relatifs au dossier racine donné au lancement ; rien n'est lu
ni écrit en dehors.
"""
import threading
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import strike_kits as sk
from editor.meta import meta

WEB_DIST = Path(__file__).resolve().parent / "web" / "dist"
EXTENSIONS = (".bkf", ".fac")


class OpenRequest(BaseModel):
    path: str


class SaveRequest(BaseModel):
    path: str
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


class TransferRequest(BaseModel):
    target: str
    mode: Literal["copy", "swap"]


class Session:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.backup = None
        self.path = None        # relatif à la racine
        self.source = None      # fichier d'origine, jamais écrasé
        self.lock = threading.Lock()

    def resolve(self, rel):
        path = (self.root / rel).resolve()
        if path != self.root and self.root not in path.parents:
            raise HTTPException(400, "chemin hors du dossier de travail : %s" % rel)
        return path

    def relative(self, path):
        return path.relative_to(self.root).as_posix()

    def require(self):
        if self.backup is None:
            raise HTTPException(409, "aucune sauvegarde ouverte")
        return self.backup

    def state(self):
        if self.backup is None:
            return {"path": None, "root": str(self.root)}
        b = self.backup
        kits = []
        for num in b.kit_numbers():
            raw = b.get_raw(num)
            kits.append({"num": num, "format": sk.kit_format(raw),
                         "name": sk.decode_kit(raw)["name"]})
        return {"path": self.path, "root": str(self.root), "kind": b.kind, "dirty": b.dirty,
                "kits": kits, "user_samples": len(b.user_sample_ids())}


def strike_errors(fn):
    try:
        return fn()
    except sk.StrikeError as exc:
        raise HTTPException(400, str(exc))


def create_app(root):
    s = Session(root)
    app = FastAPI(title="Éditeur Strike MultiPad")

    @app.get("/api/backups")
    def backups():
        found = sorted(p for p in s.root.rglob("*") if p.suffix.lower() in EXTENSIONS and p.is_file()
                       and ".venv" not in p.parts and "node_modules" not in p.parts)
        return [{"path": s.relative(p), "size": p.stat().st_size} for p in found]

    @app.post("/api/open")
    def open_backup(req: OpenRequest):
        path = s.resolve(req.path)
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            raise HTTPException(400, "sauvegarde introuvable : %s" % req.path)
        backup = strike_errors(lambda: sk.Backup.open(path))
        with s.lock:
            s.backup, s.path, s.source = backup, s.relative(path), path
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

    @app.get("/api/kits/{num}")
    def get_kit(num: str):
        with s.lock:
            return kit_or_404(num).decode(num)

    @app.put("/api/kits/{num}")
    def put_kit(num: str, kit: dict):
        with s.lock:
            b = kit_or_404(num)
            return strike_errors(lambda: b.update(num, kit))

    @app.post("/api/kits/{num}/copy")
    def copy_slot(num: str, req: CopyRequest):
        with s.lock:
            b = kit_or_404(num)
            kit, skipped = strike_errors(lambda: b.copy_slot(
                num, req.source, req.targets, req.parts, req.include_midi_note))
            return {"kit": kit, "skipped": [{"slot": n, "field": f} for n, f in skipped]}

    @app.post("/api/kits/set")
    def set_slots_in_kits(req: MultiSetRequest):
        """Même valeur, mêmes emplacements, dans plusieurs kits (tout ou rien)."""
        with s.lock:
            b = s.require()
            skipped = strike_errors(lambda: b.set_slots_in_kits(req.kits, req.targets, req.field, req.value))
            return dict(s.state(), skipped=[{"kit": k, "slot": n, "field": f} for k, n, f in skipped])

    @app.post("/api/kits/{num}/set")
    def set_slots(num: str, req: SetRequest):
        """Applique une même valeur à un champ de plusieurs emplacements."""
        with s.lock:
            b = kit_or_404(num)
            kit, skipped = strike_errors(lambda: b.set_slots(num, req.targets, req.field, req.value))
            return {"kit": kit, "skipped": [{"slot": n, "field": f} for n, f in skipped]}

    @app.post("/api/kits/{num}/transfer")
    def transfer_kit(num: str, req: TransferRequest):
        """Copie le kit `num` vers `target`, ou échange les deux kits."""
        with s.lock:
            b = kit_or_404(num)
            op = b.copy_kit if req.mode == "copy" else b.swap_kits
            strike_errors(lambda: op(num, req.target))
            return s.state()

    @app.get("/api/samples")
    def samples():
        with s.lock:
            b = s.require()
            user = set(b.user_sample_ids())
            return [{"id": sid, "name": name, "user": sid in user}
                    for sid, name in sorted(b.samples().items())]

    @app.get("/api/samples/{sid}/wav")
    def sample_wav(sid: int):
        with s.lock:
            b = s.require()
            if sid not in b.user_sample_ids():
                raise HTTPException(404, "seuls les samples utilisateur sont dans la sauvegarde")
            return Response(b.user_wav(sid), media_type="audio/wav")

    @app.post("/api/samples")
    async def add_sample(file: UploadFile = File(...)):
        content = await file.read()
        name = Path(file.filename or "").stem
        with s.lock:
            b = s.require()
            sid = strike_errors(lambda: b.add_sample(name, content))
            return {"id": sid, "name": name, "user": True}

    @app.post("/api/save")
    def save(req: SaveRequest):
        with s.lock:
            b = s.require()
            path = s.resolve(req.path)
            if path.suffix.lower() != "." + b.kind:
                raise HTTPException(400, "l'extension doit être .%s" % b.kind)
            if path == s.source:
                raise HTTPException(400, "refus d'écraser la sauvegarde d'origine")
            if path.exists() and not req.overwrite:
                raise HTTPException(409, "le fichier existe déjà : %s" % req.path)
            data = b.serialize()
            strike_errors(lambda: sk.parse_container(data))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            b.dirty = False
            s.path = s.relative(path)
            return s.state()

    if WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(WEB_DIST / "index.html")

    return app
