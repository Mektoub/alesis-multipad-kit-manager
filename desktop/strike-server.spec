# Recette PyInstaller du serveur de l'éditeur : un dossier strike-server/
# (exécutable et bibliothèques), avec l'interface construite (editor/web/dist).
# Construction : ./dev.sh freeze (sortie dans desktop/build/strike-server/).
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# retire les symboles de débogage des bibliothèques (Python compilé localement,
# par asdf ou pyenv : 73 Mo sinon) ; `strip` n'existe pas sous Windows
STRIP = sys.platform != "win32"
PROJECT = Path(SPECPATH).parent  # noqa: F821 (défini par PyInstaller)
DIST = PROJECT / "editor" / "web" / "dist"
if not (DIST / "index.html").is_file():
    raise SystemExit("Interface non construite : lancer ./dev.sh build")

a = Analysis(  # noqa: F821
    [str(PROJECT / "desktop" / "strike_server.py")],
    pathex=[str(PROJECT)],
    # uvicorn choisit ses boucles et protocoles à l'exécution (importlib)
    hiddenimports=collect_submodules("uvicorn"),
    # l'interface est lue à côté de editor/server.py (WEB_DIST)
    datas=[(str(DIST), "editor/web/dist")],
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="strike-server",
    strip=STRIP,
    console=True,  # sorties standard lues par l'application
)
coll = COLLECT(exe, a.binaries, a.datas, strip=STRIP, name="strike-server")  # noqa: F821
