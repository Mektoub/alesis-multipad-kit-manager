"""Lance l'éditeur : python -m editor [--root DOSSIER] [--port 8765].

Mode bureau (application Electron) : si la variable d'environnement STRIKE_TOKEN
est définie, l'API exige ce jeton et les fichiers sont désignés par chemin absolu.
Avec --port 0, un port libre est choisi. Une fois le serveur prêt, une ligne JSON
`{"ready": true, "port": N}` est écrite sur la sortie standard en mode bureau.
"""

import argparse
import json
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn

from editor.server import WEB_DIST, create_app


def ready_line(port):
    return json.dumps({"ready": True, "port": port})


class _Server(uvicorn.Server):
    """Serveur uvicorn qui prévient `on_ready(serveur, port)` une fois à l'écoute."""

    def __init__(self, config, port, on_ready):
        super().__init__(config)
        self._port, self._on_ready = port, on_ready

    async def startup(self, sockets=None):
        await super().startup(sockets)
        if self.started and self._on_ready:
            self._on_ready(self, self._port)


def run(app, host, port, on_ready=None):
    """Sert `app` sur host:port (port 0 : port libre) jusqu'à l'arrêt du serveur."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    config = uvicorn.Config(app, log_level="warning")
    _Server(config, sock.getsockname()[1], on_ready).run(sockets=[sock])


def main():
    ap = argparse.ArgumentParser(description="Éditeur web des kits du Strike MultiPad")
    ap.add_argument(
        "--root",
        default=".",
        help="mode développement : dossier des sauvegardes, hors duquel rien n'est lu ni écrit "
        "(défaut : dossier courant ; ignoré en mode bureau)",
    )
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765, help="port d'écoute (0 : port libre)")
    ap.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    args = ap.parse_args()
    token = os.environ.get("STRIKE_TOKEN") or None
    if not WEB_DIST.is_dir():
        print(
            "Interface non construite : lancer ./editeur.sh, ou `npm ci && npm run build` dans editor/web.",
            file=sys.stderr if token else sys.stdout,
        )

    def on_ready(_server, port):
        if token:
            print(ready_line(port), flush=True)
            return
        url = "http://%s:%d/" % (args.host, port)
        print("Éditeur disponible sur %s (racine : %s)" % (url, Path(args.root).resolve()), flush=True)
        if not args.no_browser:
            threading.Timer(0.5, webbrowser.open, [url]).start()

    try:
        run(create_app(args.root, token=token), args.host, args.port, on_ready)
    except KeyboardInterrupt:
        # uvicorn s'arrête proprement puis relance l'interruption reçue (Ctrl+C) :
        # on la considère comme un arrêt normal, sans trace d'erreur.
        pass
    print("Éditeur arrêté.", flush=True)


if __name__ == "__main__":
    main()
