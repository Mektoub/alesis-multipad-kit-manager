"""Lance l'éditeur : python -m editor [--open FICHIER] [--port 8765].

L'API exige toujours un jeton (en-tête X-KitManager-Token) :
  - application Electron : le jeton est donné par la variable d'environnement
    KITMANAGER_TOKEN ; une fois le serveur prêt, une ligne JSON
    `{"ready": true, "port": N}` est écrite sur la sortie standard ;
  - lancement local (./dev.sh serve) : sans KITMANAGER_TOKEN, un jeton est créé et
    transmis au navigateur dans l'adresse (http://…/#token=…).
Avec --port 0, un port libre est choisi. Avec --watch-stdin, le serveur s'arrête
quand son entrée standard se ferme : l'application qui l'a lancé s'est arrêtée,
même brutalement.
"""

import argparse
import json
import os
import secrets
import socket
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn

import strike_kits as sk
from editor.server import APP_NAMES, WEB_DIST, create_app


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


def watch_stdin(server):
    """Arrête `server` quand l'entrée standard se ferme (fin de fichier)."""

    def wait_eof():
        while sys.stdin.buffer.read(4096):
            pass
        server.should_exit = True

    threading.Thread(target=wait_eof, name="watch-stdin", daemon=True).start()


def run(app, host, port, on_ready=None):
    """Sert `app` sur host:port (port 0 : port libre) jusqu'à l'arrêt du serveur."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    config = uvicorn.Config(app, log_level="warning")
    _Server(config, sock.getsockname()[1], on_ready).run(sockets=[sock])


def main():
    ap = argparse.ArgumentParser(description="Éditeur web des kits du Strike MultiPad")
    ap.add_argument("--open", metavar="FICHIER", help="sauvegarde .bkf ou .fac à ouvrir au démarrage")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765, help="port d'écoute (0 : port libre)")
    ap.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    ap.add_argument(
        "--allow",
        metavar="DOSSIER",
        action="append",
        default=[],
        help="dossier autorisé en plus du dossier personnel et des supports amovibles (répétable)",
    )
    ap.add_argument(
        "--watch-stdin", action="store_true", help="s'arrêter quand l'entrée standard se ferme (application arrêtée)"
    )
    ap.add_argument("--version", action="version", version="%s-server %s" % (APP_NAMES["id"], APP_NAMES["version"]))
    args = ap.parse_args()
    desktop_token = os.environ.get("KITMANAGER_TOKEN") or None
    token = desktop_token or secrets.token_urlsafe(24)
    try:
        app = create_app(token, open_file=Path(args.open).resolve() if args.open else None, allow=args.allow)
    except sk.StrikeError as exc:
        print("Erreur : %s" % exc, file=sys.stderr)
        sys.exit(2)
    if not WEB_DIST.is_dir():
        print(
            "Interface non construite : lancer ./dev.sh build, ou `npm ci && npm run build` dans editor/web.",
            file=sys.stderr,  # avertissement : la sortie standard reste réservée aux lignes utiles
        )

    def on_ready(server, port):
        if args.watch_stdin:
            watch_stdin(server)
        if desktop_token:
            print(ready_line(port), flush=True)
            return
        url = "http://%s:%d/#token=%s" % (args.host, port, token)
        print("Éditeur disponible sur %s" % url, flush=True)
        if not args.no_browser:
            threading.Timer(0.5, webbrowser.open, [url]).start()

    try:
        run(app, args.host, args.port, on_ready)
    except KeyboardInterrupt:
        # uvicorn s'arrête proprement puis relance l'interruption reçue (Ctrl+C) :
        # on la considère comme un arrêt normal, sans trace d'erreur.
        pass
    print("Éditeur arrêté.", flush=True)


if __name__ == "__main__":
    main()
