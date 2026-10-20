#!/usr/bin/env bash
# Vérifie, dans un conteneur Ubuntu propre (voir Dockerfile), l'installation du
# paquet .deb monté dans /paquet, avec la sauvegarde de référence dans /ref et
# les noms de l'application dans /app-names.json :
# installation, fichiers, types de fichier, serveur intégré, lancement de
# l'application (Xvfb), désinstallation. Lancé par ./dev.sh test-deb.
set -uo pipefail

ID="$(sed -n 's/.*"id": *"\([^"]*\)".*/\1/p' /app-names.json)"  # paquet, exécutable, /opt/<id>
export ID  # utilisé dans les bash -c '…'
SERVER="$ID-server"  # serveur figé, dans resources/
FAILED=0
ok() { printf '  \033[32m✔\033[0m %s\n' "$*"; }
ko() { printf '  \033[31m✖\033[0m %s\n' "$*"; FAILED=1; }
check() { local label="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$label"; else ko "$label"; fi; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

deb="$(ls /paquet/*.deb | head -1)"

step "Installation de $(basename "$deb")"
if apt-get install -y --no-install-recommends "$deb" > /tmp/apt.log 2>&1; then
    ok "apt install (dépendances résolues, script d'installation sans erreur)"
else
    ko "apt install"; tail -20 /tmp/apt.log; exit 1
fi
grep -i "apparmor" /tmp/apt.log | sed 's/^/    /'

step "Fichiers installés"
APP="/opt/$ID"
check "commande $ID → $APP/$ID" test "$(readlink -f "/usr/bin/$ID")" -ef "$APP/$ID"
check "serveur intégré resources/$SERVER" test -x "$APP/resources/$SERVER/$SERVER"
check "interface intégrée" test -f "$APP/resources/$SERVER/_internal/editor/web/dist/index.html"
check "icône 512 px" test -f /usr/share/icons/hicolor/512x512/apps/$ID.png
check "entrée de menu valide (desktop-file-validate)" desktop-file-validate /usr/share/applications/$ID.desktop
check "aucun Python sur le système" bash -c '! command -v python3'

step "Types de fichier"
# base des types MIME (xdg-mime query filetype demande un environnement de bureau)
check "*.bkf → application/x-strike-bkf" grep -q "application/x-strike-bkf:\*\.bkf" /usr/share/mime/globs2
check "*.fac → application/x-strike-fac" grep -q "application/x-strike-fac:\*\.fac" /usr/share/mime/globs2
check "application associée aux .bkf et .fac" bash -c 'grep -q "application/x-strike-bkf=.*$ID.desktop" /usr/share/applications/mimeinfo.cache && grep -q "application/x-strike-fac=.*$ID.desktop" /usr/share/applications/mimeinfo.cache'

step "Serveur intégré (test de fumée)"
cp /ref/Backup001.bkf /home/testeur/ && chown testeur: /home/testeur/Backup001.bkf
su testeur -c "STRIKE_TOKEN=t '$APP/resources/$SERVER/$SERVER' --port 0 --open /home/testeur/Backup001.bkf" \
    > /tmp/serveur.out 2> /tmp/serveur.err &
for _ in $(seq 40); do grep -q '"ready"' /tmp/serveur.out && break; sleep 0.25; done
port="$(grep -o '"port": [0-9]*' /tmp/serveur.out | grep -o '[0-9]*$')"
if [[ -n "$port" ]]; then
    ok "prêt sur le port $port"
    base="http://127.0.0.1:$port"
    get() { curl -fsS -H "X-Strike-Token: t" "$base$1"; }
    check "accès refusé sans jeton (403)" bash -c "[[ \$(curl -s -o /dev/null -w '%{http_code}' $base/api/state) == 403 ]]"
    check "sauvegarde ouverte" bash -c "curl -fsS -H 'X-Strike-Token: t' $base/api/state | grep -q '\"path\":\"/home/testeur/Backup001.bkf\"'"
    check "kit 031 lu (WhereIs)" bash -c "curl -fsS -H 'X-Strike-Token: t' $base/api/kits/031 | grep -q '\"name\":\"WhereIs\"'"
    check "WAV servi" bash -c "curl -fsS -o /dev/null -H 'X-Strike-Token: t' -w '%{content_type}' $base/api/samples/8071/wav | grep -q audio/wav"
    check "interface servie" bash -c "curl -fsS $base/ | grep -q '<div id=\"app\">'"
else
    ko "le serveur n'a pas démarré"; sed 's/^/    /' /tmp/serveur.err | tail -10
fi
pkill -f "$SERVER --port 0 --open" ; sleep 0.5

step "Application (Electron sous Xvfb, utilisateur non root)"
su testeur -c "cd ~ && xvfb-run -a $ID --remote-debugging-port=9222 Backup001.bkf" > /tmp/app.log 2>&1 &
pages=""
for _ in $(seq 60); do
    pages="$(curl -fsS http://127.0.0.1:9222/json/list 2>/dev/null)" && grep -q '"url": "http://127.0.0.1:' <<<"$pages" && break
    sleep 0.5
done
if grep -q '"url": "http://127.0.0.1:' <<<"$pages"; then
    ok "fenêtre ouverte sur le serveur local"
    title="$(grep -o '<title>[^<]*' "$APP/resources/$SERVER/_internal/editor/web/dist/index.html" | cut -c8-)"
    for _ in $(seq 20); do  # le titre n'apparaît qu'une fois la page chargée
        grep -qF "\"title\": \"$title\"" <<<"$pages" && break
        sleep 0.5
        pages="$(curl -fsS http://127.0.0.1:9222/json/list 2>/dev/null)"
    done
    check "page de l'éditeur chargée ($title)" grep -qF "\"title\": \"$title\"" <<<"$pages"
    check "serveur lancé par l'application (--watch-stdin)" pgrep -f "resources/$SERVER/$SERVER --port 0 --watch-stdin"
else
    ko "l'application n'a pas ouvert sa fenêtre"; grep -v -i "dbus\|vulkan\|gpu" /tmp/app.log | tail -15 | sed 's/^/    /'
fi
# processus principal (lancé par /usr/bin/<id>, d'où le motif)
pkill -TERM -f "$ID --remote-debugging-port" ; sleep 3
# [s] : le motif ne correspond pas à la ligne de commande de ce bash -c lui-même
check "serveur arrêté avec l'application" bash -c '! pgrep -f "[-]server --port 0 --watch-stdin"'

step "Désinstallation"
apt-get remove -y $ID > /tmp/remove.log 2>&1 && ok "apt remove" || ko "apt remove"
check "$APP supprimé" test ! -e "$APP/$ID"
check "commande $ID supprimée" bash -c '! command -v $ID'
check "entrée de menu supprimée" test ! -e /usr/share/applications/$ID.desktop

echo
if ((FAILED)); then printf '\033[31mÉchec\033[0m\n'; exit 1; fi
printf '\033[32mInstallation vérifiée\033[0m\n'
