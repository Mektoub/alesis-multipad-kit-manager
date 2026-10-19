#!/usr/bin/env bash
# Lance l'éditeur web des kits du Strike MultiPad.
#
# Au besoin, crée l'environnement virtuel Python (.venv), installe ou met à jour
# les dépendances de requirements.txt et (re)construit l'interface Svelte.
# Les arguments sont transmis à `python -m editor` (--root, --port, --host,
# --no-browser) ; sans --root, le dossier Backups/ du projet est utilisé s'il
# existe (sinon Strike/, puis le dossier courant).
#
#   ./editeur.sh                      # racine : Backups/
#   ./editeur.sh --root ~/Strike      # autre dossier de sauvegardes
#   ./editeur.sh --port 9000 --no-browser
#
# Variables : PYTHON (interpréteur pour créer le venv, défaut python3),
# REBUILD=1 (forcer la reconstruction de l'interface).
set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT/.venv"
WEB="$PROJECT/editor/web"
PYTHON="${PYTHON:-python3}"

info() { printf '\033[1m==> %s\033[0m\n' "$*"; }
die() { printf 'Erreur : %s\n' "$*" >&2; exit 1; }

# --- Environnement Python -------------------------------------------------------
if [[ ! -x "$VENV/bin/python" ]]; then
    command -v "$PYTHON" >/dev/null || die "$PYTHON introuvable (installer Python 3 ou définir PYTHON)"
    info "Création de l'environnement virtuel (.venv)"
    "$PYTHON" -m venv "$VENV"
fi

STAMP="$VENV/.requirements.sha256"
wanted="$(sha256sum "$PROJECT/requirements.txt" | cut -d' ' -f1)"
if [[ ! -f "$STAMP" || "$(cat "$STAMP")" != "$wanted" ]]; then
    info "Installation des dépendances Python"
    "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$PROJECT/requirements.txt"
    echo "$wanted" > "$STAMP"
fi

# --- Interface Svelte -----------------------------------------------------------
needs_build() {
    [[ "${REBUILD:-0}" == 1 || ! -f "$WEB/dist/index.html" ]] && return 0
    # reconstruit si une source est plus récente que l'interface construite
    [[ -n "$(find "$WEB/src" "$WEB/index.html" "$WEB/package.json" "$WEB/vite.config.js" \
               -newer "$WEB/dist/index.html" -print -quit)" ]]
}

if needs_build; then
    command -v npm >/dev/null || die "npm introuvable : installer Node.js pour construire l'interface"
    if [[ ! -d "$WEB/node_modules" || "$WEB/package-lock.json" -nt "$WEB/node_modules" ]]; then
        info "Installation des dépendances de l'interface (npm ci)"
        (cd "$WEB" && npm ci --no-audit --no-fund)
        touch "$WEB/node_modules"
    fi
    info "Construction de l'interface"
    (cd "$WEB" && npm run build --silent)
fi

# --- Lancement ------------------------------------------------------------------
args=("$@")
has_root=0
for a in "${args[@]}"; do
    [[ "$a" == --root || "$a" == --root=* ]] && has_root=1
done
if [[ $has_root == 0 ]]; then
    for dir in Backups Strike; do
        if [[ -d "$PROJECT/$dir" ]]; then
            args=(--root "$PROJECT/$dir" "${args[@]}")
            break
        fi
    done
fi

cd "$PROJECT"
exec "$VENV/bin/python" -m editor "${args[@]}"
