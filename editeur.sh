#!/usr/bin/env bash
# Lance l'éditeur dans le navigateur sur une sauvegarde : lancement local rapide,
# dans le même mode que l'application Electron (jeton, chemins absolus).
#
# Usage : ./editeur.sh FICHIER [--port N] [--host ADRESSE] [--no-browser]
#
#   ./editeur.sh Backups/Backup001.bkf
#   ./editeur.sh ~/Strike/STRIKE_BACKUP_KIT.fac --port 9000 --no-browser
#
# Au besoin, prépare d'abord le venv et l'interface (scripts/preparer.sh ;
# variables PYTHON et REBUILD=1).
set -euo pipefail

usage() { sed -n '5,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# Arguments vérifiés avant les étapes de préparation, plus lentes.
case "${1:-}" in
    -h | --help) usage; exit 0 ;;
    "" | -*) usage >&2; exit 2 ;;
esac
[[ -f "$1" ]] || { printf 'Erreur : fichier introuvable : %s\n' "$1" >&2; exit 2; }
FILE="$(realpath -- "$1")"
shift

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$PROJECT/scripts/preparer.sh"

# --- Lancement ------------------------------------------------------------------
cd "$PROJECT"
exec "$PROJECT/.venv/bin/python" -m editor --open "$FILE" "$@"
