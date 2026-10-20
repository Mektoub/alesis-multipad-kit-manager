#!/usr/bin/env bash
# Commandes de développement : lancement de l'éditeur, analyse, tests et build
# comme la CI.
#
#   ./dev.sh serve FICHIER [--port N] [--host ADRESSE] [--allow DOSSIER]… [--no-browser]
#                                éditeur dans le navigateur sur cette sauvegarde
#                                (lancement rapide, sans Electron) ; --allow :
#                                dossier autorisé en plus du dossier personnel
#   ./dev.sh start [--frozen] [FICHIER]
#                                application de bureau, sur ce fichier ;
#                                --frozen : avec le serveur figé, reconstruit si
#                                une source a changé
#   ./dev.sh lint [--fix]        ruff check, ruff format --check, ESLint (interface
#                                et application de bureau)
#                                (--fix : corrige et reformate au lieu de vérifier)
#   ./dev.sh test [TESTS…]       tests Python, de l'interface et de l'application
#                                de bureau ; avec TESTS, seulement les tests
#                                Python indiqués (ex. tests.test_editor.Lancement)
#   ./dev.sh build               build de l'interface (editor/web/dist)
#   ./dev.sh freeze              serveur figé (PyInstaller) dans
#                                desktop/build/<id>-server/, puis test de fumée
#   ./dev.sh package             paquet .deb de l'application dans desktop/dist/
#                                (interface, serveur figé testé, electron-builder)
#   ./dev.sh test-deb            installe et teste le .deb dans un conteneur Docker
#                                Ubuntu 24.04 (reconstruit le paquet s'il est périmé)
#   ./dev.sh all [--fix]         tout ; continue après un échec et affiche un bilan
#
# Au besoin, crée l'environnement virtuel (.venv), installe requirements-dev.txt
# et les paquets de editor/web et desktop (npm ci) ; serve et start
# (re)construisent l'interface si une de ses sources a changé. Variables :
# PYTHON (interpréteur pour créer le venv, défaut python3), REBUILD=1 (forcer
# la reconstruction de l'interface).
set -uo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT/.venv"
WEB="$PROJECT/editor/web"
DESKTOP="$PROJECT/desktop"
PYTHON="${PYTHON:-python3}"
# serveur figé : <id>-server, <id> étant l'identifiant de app-names.json
APP_ID="$(sed -n 's/.*"id": *"\([^"]*\)".*/\1/p' "$PROJECT/app-names.json")"
SERVER="$APP_ID-server"
FROZEN_EXE="$DESKTOP/build/$SERVER/$SERVER"

info() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf 'Erreur : %s\n' "$*" >&2; exit 2; }
usage() { sed -n '2,34p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

# --- Dépendances --------------------------------------------------------------

python_deps() {
    if [[ ! -x "$VENV/bin/python" ]]; then
        command -v "$PYTHON" >/dev/null || die "$PYTHON introuvable (installer Python 3 ou définir PYTHON)"
        info "Création de l'environnement virtuel (.venv)"
        "$PYTHON" -m venv "$VENV" || die "création du venv impossible"
    fi
    local stamp="$VENV/.requirements-dev.sha256" wanted
    wanted="$(cat "$PROJECT/requirements.txt" "$PROJECT/requirements-dev.txt" | sha256sum | cut -d' ' -f1)"
    if [[ ! -f "$stamp" || "$(cat "$stamp")" != "$wanted" ]]; then
        info "Installation des dépendances Python (requirements-dev.txt)"
        "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$PROJECT/requirements-dev.txt" \
            || die "installation des dépendances Python impossible"
        echo "$wanted" > "$stamp"
    fi
}

# npm ci dans $1 si node_modules manque ou est plus ancien que package-lock.json.
node_deps() {
    command -v npm >/dev/null || die "npm introuvable : installer Node.js"
    if [[ ! -d "$1/node_modules" || "$1/package-lock.json" -nt "$1/node_modules" ]]; then
        info "Installation des paquets de ${1#"$PROJECT"/} (npm ci)"
        (cd "$1" && npm ci --no-audit --no-fund) || die "npm ci a échoué"
        touch "$1/node_modules"
    fi
}
web_deps() { node_deps "$WEB"; }
desktop_deps() { node_deps "$DESKTOP"; }

# Construit l'interface si elle manque ou si une de ses sources est plus récente.
web_ready() {
    local index="$WEB/dist/index.html"
    if [[ "${REBUILD:-0}" == 1 || ! -f "$index" || -n "$(find "$WEB/src" "$WEB/index.html" \
            "$WEB/package.json" "$WEB/vite.config.js" "$PROJECT/app-names.json" -newer "$index" -print -quit)" ]]; then
        step_build || die "build de l'interface impossible"
    fi
}

# --- Étapes (chacune renvoie 0 si elle réussit) -------------------------------

ruff() { "$VENV/bin/ruff" "$@"; }

step_lint_python() {
    python_deps
    if [[ $FIX == 1 ]]; then
        info "Python : corrections (ruff check --fix, ruff format)"
        (cd "$PROJECT" && ruff check --fix . && ruff format .)
    else
        info "Python : analyse (ruff check, ruff format --check)"
        (cd "$PROJECT" && ruff check . && ruff format --check .)
    fi
}

step_lint_web() {
    web_deps
    if [[ $FIX == 1 ]]; then
        info "Interface : corrections (ESLint --fix)"
        (cd "$WEB" && npm run --silent lint -- --fix)
    else
        info "Interface : analyse (ESLint)"
        (cd "$WEB" && npm run --silent lint)
    fi
}

step_test() {
    python_deps
    info "Tests${TESTS:+ : $TESTS}"
    if [[ -n "$TESTS" ]]; then
        # shellcheck disable=SC2086
        (cd "$PROJECT" && "$VENV/bin/python" -m unittest $TESTS)
    else
        (cd "$PROJECT" && "$VENV/bin/python" -m unittest discover -s tests -t .)
    fi
}

step_test_web() {
    web_deps
    info "Tests de l'interface (Vitest)"
    (cd "$WEB" && npm run --silent test)
}

step_lint_desktop() {
    desktop_deps
    if [[ $FIX == 1 ]]; then
        info "Application de bureau : corrections (ESLint --fix)"
        (cd "$DESKTOP" && npm run --silent lint -- --fix)
    else
        info "Application de bureau : analyse (ESLint)"
        (cd "$DESKTOP" && npm run --silent lint)
    fi
}

step_test_desktop() {
    desktop_deps
    info "Tests de l'application de bureau (node:test)"
    (cd "$DESKTOP" && npm run --silent test)
}

step_build() {
    web_deps
    info "Build de l'interface"
    (cd "$WEB" && npm run --silent build)
}

step_freeze() {
    python_deps
    info "Serveur figé (PyInstaller)"
    # LC_ALL=C : PyInstaller lit la sortie de ldconfig, qu'il ne comprend qu'en anglais
    (cd "$PROJECT" && LC_ALL=C "$VENV/bin/pyinstaller" --noconfirm --log-level WARN \
        --distpath desktop/build --workpath desktop/build/.work desktop/server.spec)
}

step_test_frozen() {
    desktop_deps
    info "Test de fumée du serveur figé"
    # sans exécutable, node:test ignorerait le test au lieu d'échouer
    [[ -x "$FROZEN_EXE" ]] || { echo "serveur figé introuvable : $FROZEN_EXE" >&2; return 1; }
    (cd "$DESKTOP" && KITMANAGER_SERVER="$FROZEN_EXE" \
        node --test --test-name-pattern "serveur figé" test/server.test.js)
}

step_package() {
    desktop_deps
    info "Paquet de l'application (electron-builder)"
    rm -rf "$DESKTOP/dist"
    (cd "$DESKTOP" && npm run --silent package) || return 1
    local deb
    deb="$(ls "$DESKTOP"/dist/*.deb 2>/dev/null | head -1)"
    [[ -n "$deb" ]] || { echo "aucun .deb produit" >&2; return 1; }
    # le serveur figé et l'interface doivent être dans le paquet
    local content
    content="$(dpkg-deb -c "$deb")"
    for f in "resources/$SERVER/$SERVER" "resources/$SERVER/_internal/editor/web/dist/index.html" \
             resources/app.asar; do
        grep -q "$f" <<<"$content" || { echo "absent du paquet : $f" >&2; return 1; }
    done
    info "Paquet : ${deb#"$PROJECT"/} ($(du -h "$deb" | cut -f1))"
}

# Le paquet manque, ou une de ses sources (application, serveur figé) est plus récente.
deb_outdated() {
    local deb
    deb="$(ls "$DESKTOP"/dist/*.deb 2>/dev/null | head -1)"
    [[ -z "$deb" ]] && return 0
    frozen_outdated && return 0
    [[ -n "$(find "$DESKTOP/main.js" "$DESKTOP/preload.cjs" "$DESKTOP/server.js" "$DESKTOP/package.json" \
               "$DESKTOP/electron-builder.config.mjs" "$PROJECT/app-names.json" \
               "$DESKTOP/build-resources" "$FROZEN_EXE" -newer "$deb" -print -quit)" ]]
}

step_test_deb() {
    command -v docker >/dev/null || { echo "docker introuvable" >&2; return 1; }
    local image=alesis-kit-manager-test:24.04
    info "Image de test ($image)"
    docker build --quiet -t "$image" "$DESKTOP/test-deb" >/dev/null || return 1
    info "Installation et test du paquet dans le conteneur"
    docker run --rm --security-opt seccomp=unconfined \
        -v "$DESKTOP/dist:/paquet:ro" \
        -v "$PROJECT/tests/ressources:/ref:ro" \
        -v "$DESKTOP/test-deb/verifier.sh:/verifier.sh:ro" \
        -v "$PROJECT/app-names.json:/app-names.json:ro" \
        "$image" bash /verifier.sh
}

# Le serveur figé manque, ou une de ses sources est plus récente que lui.
frozen_outdated() {
    local exe="$FROZEN_EXE"
    [[ ! -x "$exe" ]] && return 0
    [[ -n "$(find "$PROJECT/strike_kits.py" "$PROJECT/requirements.txt" "$PROJECT/app-names.json" "$PROJECT/editor" \
               "$DESKTOP/server.spec" "$DESKTOP/server_entry.py" \
               \( -name node_modules -o -name dist -o -name __pycache__ \) -prune -o \
               -newer "$exe" -print -quit)" ]]
}

# Les commandes de lancement remplacent ce script (exec), pour que Ctrl+C les arrête.

# Éditeur dans le navigateur (python -m editor --open FICHIER).
serve() {
    python_deps
    web_ready
    cd "$PROJECT" || die "dossier du projet introuvable"
    exec "$VENV/bin/python" -m editor --open "$FILE" "${SERVE_ARGS[@]}"
}

# Application de bureau (npm start).
start_app() {
    desktop_deps
    python_deps
    if [[ $FROZEN == 1 ]]; then
        if frozen_outdated; then
            step_build && step_freeze || die "construction du serveur figé impossible"
        fi
        export KITMANAGER_SERVER="$FROZEN_EXE"
        info "Application de bureau (serveur figé)"
    else
        web_ready
        info "Application de bureau"
    fi
    cd "$DESKTOP" || die "dossier desktop introuvable"
    exec npm start --silent -- ${FILE:+"$FILE"}
}

# Lance les étapes données, puis affiche un bilan si plusieurs ont tourné.
run_steps() {
    local failed=() step
    for step in "$@"; do
        "step_$step" || failed+=("$step")
    done
    if (($# > 1)); then
        info "Bilan"
        for step in "$@"; do
            if [[ " ${failed[*]} " == *" $step "* ]]; then
                printf '  \033[31mÉCHEC\033[0m %s\n' "${LABELS[$step]}"
            else
                printf '  \033[32mOK\033[0m    %s\n' "${LABELS[$step]}"
            fi
        done
    fi
    ((${#failed[@]} == 0))
}

declare -A LABELS=(
    [lint_python]="analyse Python"
    [lint_web]="analyse de l'interface"
    [test]="tests Python"
    [test_web]="tests de l'interface"
    [freeze]="serveur figé"
    [test_frozen]="test de fumée du serveur figé"
    [lint_desktop]="analyse de l'application de bureau"
    [test_desktop]="tests de l'application de bureau"
    [build]="build de l'interface"
    [package]="paquet de l'application"
    [test_deb]="test d'installation du paquet"
)

# --- Arguments ----------------------------------------------------------------

(($# >= 1)) || usage 2
COMMAND="$1"
shift
FIX=0
TESTS=""
FROZEN=0
FILE=""
SERVE_ARGS=()
case "$COMMAND" in
    lint | all)
        for a in "$@"; do
            [[ "$a" == --fix ]] && FIX=1 || die "option inconnue pour $COMMAND : $a"
        done
        ;;
    test) TESTS="$*" ;;
    serve)
        while (($#)); do
            case "$1" in
                --port | --host | --allow)
                    (($# >= 2)) || die "valeur attendue après $1"
                    SERVE_ARGS+=("$1" "$2")
                    shift
                    ;;
                --no-browser) SERVE_ARGS+=("$1") ;;
                -*) die "option inconnue pour serve : $1" ;;
                *)
                    [[ -z "$FILE" ]] || die "un seul fichier à la fois"
                    [[ -f "$1" ]] || die "fichier introuvable : $1"
                    FILE="$(realpath -- "$1")"
                    ;;
            esac
            shift
        done
        [[ -n "$FILE" ]] || { printf 'Fichier attendu : ./dev.sh serve FICHIER [--port N] [--host ADRESSE] [--allow DOSSIER]… [--no-browser]\n' >&2; exit 2; }
        ;;
    start)
        for a in "$@"; do
            case "$a" in
                --frozen) FROZEN=1 ;;
                -*) die "option inconnue pour start : $a" ;;
                *)
                    [[ -z "$FILE" ]] || die "un seul fichier à la fois"
                    [[ -f "$a" ]] || die "fichier introuvable : $a"
                    FILE="$(realpath -- "$a")"
                    ;;
            esac
        done
        ;;
    build | freeze | package | test-deb) (($# == 0)) || die "$COMMAND n'accepte pas d'argument" ;;
    -h | --help | help) usage 0 ;;
    *) printf 'Commande inconnue : %s\n\n' "$COMMAND" >&2; usage 2 ;;
esac

case "$COMMAND" in
    lint) run_steps lint_python lint_web lint_desktop ;;
    test) if [[ -n "$TESTS" ]]; then run_steps test; else run_steps test test_web test_desktop; fi ;;
    build) run_steps build ;;
    freeze) step_build && step_freeze && run_steps test_frozen ;;
    package) step_build && step_freeze && step_test_frozen && run_steps package ;;
    test-deb)
        if deb_outdated; then
            step_build && step_freeze && step_test_frozen && step_package || die "construction du paquet impossible"
        fi
        run_steps test_deb
        ;;
    serve) serve ;;
    start) start_app ;;
    all) run_steps lint_python test lint_web test_web build lint_desktop test_desktop ;;
esac
