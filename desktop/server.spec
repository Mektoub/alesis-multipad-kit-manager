# Recette PyInstaller du serveur de l'éditeur : un dossier <id>-server/
# (exécutable et bibliothèques), avec l'interface construite (editor/web/dist) ;
# <id> : identifiant de ../app-names.json (alesis-kit-manager).
# Construction : ./dev.sh freeze (sortie dans desktop/build/<id>-server/).
import json
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# retire les symboles de débogage des bibliothèques (Python compilé localement,
# par asdf ou pyenv : 73 Mo sinon) ; `strip` n'existe pas sous Windows
STRIP = sys.platform != "win32"
PROJECT = Path(SPECPATH).parent  # noqa: F821 (défini par PyInstaller)
DIST = PROJECT / "editor" / "web" / "dist"
SERVER = json.loads((PROJECT / "app-names.json").read_text(encoding="utf-8"))["id"] + "-server"
if not (DIST / "index.html").is_file():
    raise SystemExit("Interface non construite : lancer ./dev.sh build")

a = Analysis(  # noqa: F821
    [str(PROJECT / "desktop" / "server_entry.py")],
    pathex=[str(PROJECT)],
    # uvicorn choisit ses boucles et protocoles à l'exécution (importlib)
    hiddenimports=collect_submodules("uvicorn"),
    # l'interface est lue à côté de editor/server.py (WEB_DIST), les noms de
    # l'application à côté du paquet editor/ (APP_NAMES)
    datas=[(str(DIST), "editor/web/dist"), (str(PROJECT / "app-names.json"), ".")],
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=SERVER,
    strip=STRIP,
    console=True,  # sorties standard lues par l'application
)
coll = COLLECT(exe, a.binaries, a.datas, strip=STRIP, name=SERVER)  # noqa: F821
