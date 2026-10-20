#!/usr/bin/env bash
# Profil AppArmor pour l'Electron de développement (desktop/node_modules).
#
# Depuis Ubuntu 24.04, AppArmor interdit par défaut les « user namespaces » non
# privilégiés (kernel.apparmor_restrict_unprivileged_userns = 1), dont Chromium
# a besoin pour isoler ses processus : Electron s'arrête alors avec « The SUID
# sandbox helper binary was found, but is not configured correctly ». Comme
# Chrome ou VS Code, cet Electron a besoin d'un profil qui les autorise.
#
#   ./apparmor.sh            affiche le profil (à installer avec sudo, voir ci-dessous)
#   ./apparmor.sh --check    prévient si Electron ne pourra pas démarrer (npm start)
#
# Installation (une fois ; le chemin de l'exécutable ne change pas avec npm ci) :
#   ./apparmor.sh | sudo tee /etc/apparmor.d/strike-kit-editor-dev
#   sudo apparmor_parser -r /etc/apparmor.d/strike-kit-editor-dev
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ELECTRON="$HERE/node_modules/electron/dist/electron"
PROFILE=/etc/apparmor.d/strike-kit-editor-dev

if [[ "${1:-}" == --check ]]; then
    restricted="$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null || echo 0)"
    sandbox="$HERE/node_modules/electron/dist/chrome-sandbox"
    if [[ "$restricted" == 1 && ! -f "$PROFILE" && ! ( -u "$sandbox" && "$(stat -c %u "$sandbox")" == 0 ) ]]; then
        cat >&2 <<MSG
Attention : AppArmor bloque la sandbox de Chromium sur ce système ; Electron
risque de s'arrêter au démarrage. Installer une fois le profil (voir
docs/application-bureau.md) :

  desktop/apparmor.sh | sudo tee $PROFILE
  sudo apparmor_parser -r $PROFILE

MSG
    fi
    exit 0
fi

cat <<PROFILE
# Electron de développement de Strike Kit Editor ($HERE).
# Comme les profils de Chrome ou VS Code : aucune restriction (unconfined) ;
# le profil sert à autoriser les user namespaces de la sandbox de Chromium.

abi <abi/5.0>,
include <tunables/global>

profile strike-kit-editor-dev "$ELECTRON" flags=(unconfined) {
  userns,
  @{exec_path} mr,

  include if exists <local/strike-kit-editor-dev>
}
PROFILE
