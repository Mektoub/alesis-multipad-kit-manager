#!/usr/bin/env bash
# Commandes de développement : analyse, tests et build, comme la CI.
#
#   ./dev.sh lint [--fix]        ruff check, ruff format --check, ESLint (interface
#                                et application de bureau)
#                                (--fix : corrige et reformate au lieu de vérifier)
#   ./dev.sh test [TESTS…]       tests Python, de l'interface et de l'application
#                                de bureau ; avec TESTS, seulement les tests
#                                Python indiqués (ex. tests.test_editor.Lancement)
#   ./dev.sh build               build de l'interface (editor/web/dist)
#   ./dev.sh freeze              serveur figé (PyInstaller) dans
#                                desktop/build/strike-server/, puis test de fumée
#   ./dev.sh all [--fix]         tout ; continue après un échec et affiche un bilan
#   ./dev.sh start [--frozen] [FICHIER]
#                                lance l'application de bureau, sur ce fichier ;
#                                --frozen : avec le serveur figé, reconstruit si
#                                une source a changé
#
# Au besoin, crée l'environnement virtuel (.venv), installe requirements-dev.txt
# et les paquets de editor/web et desktop (npm ci). Variable : PYTHON
# (interpréteur pour créer le venv, défaut python3).
set -uo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT/.venv"
WEB="$PROJECT/editor/web"
DESKTOP="$PROJECT/desktop"
PYTHON="${PYTHON:-python3}"

info() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf 'Erreur : %s\n' "$*" >&2; exit 2; }
usage() { sed -n '2,21p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

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
        --distpath desktop/build --workpath desktop/build/.work desktop/strike-server.spec)
}

step_test_frozen() {
    desktop_deps
    info "Test de fumée du serveur figé"
    (cd "$DESKTOP" && STRIKE_SERVER="$DESKTOP/build/strike-server/strike-server" \
        node --test --test-name-pattern "serveur figé" test/server.test.js)
}

# Le serveur figé manque, ou une de ses sources est plus récente que lui.
frozen_outdated() {
    local exe="$DESKTOP/build/strike-server/strike-server"
    [[ ! -x "$exe" ]] && return 0
    [[ -n "$(find "$PROJECT/strike_kits.py" "$PROJECT/requirements.txt" "$PROJECT/editor" \
               "$DESKTOP/strike-server.spec" "$DESKTOP/strike_server.py" \
               \( -name node_modules -o -name dist -o -name __pycache__ \) -prune -o \
               -newer "$exe" -print -quit)" ]]
}

# Lance l'application (npm start) ; remplace ce script, pour que Ctrl+C l'arrête.
start_app() {
    desktop_deps
    if [[ $FROZEN == 1 ]]; then
        if frozen_outdated; then
            step_build && step_freeze || die "construction du serveur figé impossible"
        fi
        export STRIKE_SERVER="$DESKTOP/build/strike-server/strike-server"
        info "Application de bureau (serveur figé)"
    else
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
)

# --- Arguments ----------------------------------------------------------------

(($# >= 1)) || usage 2
COMMAND="$1"
shift
FIX=0
TESTS=""
FROZEN=0
FILE=""
case "$COMMAND" in
    lint | all)
        for a in "$@"; do
            [[ "$a" == --fix ]] && FIX=1 || die "option inconnue pour $COMMAND : $a"
        done
        ;;
    test) TESTS="$*" ;;
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
    build | freeze) (($# == 0)) || die "$COMMAND n'accepte pas d'argument" ;;
    -h | --help | help) usage 0 ;;
    *) printf 'Commande inconnue : %s\n\n' "$COMMAND" >&2; usage 2 ;;
esac

case "$COMMAND" in
    lint) run_steps lint_python lint_web lint_desktop ;;
    test) if [[ -n "$TESTS" ]]; then run_steps test; else run_steps test test_web test_desktop; fi ;;
    build) run_steps build ;;
    freeze) step_build && step_freeze && run_steps test_frozen ;;
    start) start_app ;;
    all) run_steps lint_python test lint_web test_web build lint_desktop test_desktop ;;
esac
