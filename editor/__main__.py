"""Lance l'éditeur : python -m editor [--root DOSSIER] [--port 8765]."""
import argparse
import threading
import webbrowser
from pathlib import Path

import uvicorn

from editor.server import WEB_DIST, create_app


def main():
    ap = argparse.ArgumentParser(description="Éditeur web des kits du Strike MultiPad")
    ap.add_argument("--root", default=".", help="dossier contenant les sauvegardes (défaut : dossier courant)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    args = ap.parse_args()
    if not WEB_DIST.is_dir():
        print("Interface non construite : lancer ./editeur.sh, ou `npm ci && npm run build` dans editor/web.")
    url = "http://%s:%d/" % (args.host, args.port)
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    print("Éditeur disponible sur %s (racine : %s)" % (url, Path(args.root).resolve()))
    uvicorn.run(create_app(args.root), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
