#!/bin/sh
# Install r1cmd — works from a git clone or: curl -fsSL https://jalinuxy.ir/r1cmd | sh
set -eu

# Resolve script directory (when piped via curl | sh, $0 is "sh" — cwd is fine)
if [ -n "${0##*/*}" ] || [ "$0" = "sh" ] || [ "$0" = "dash" ] || [ "$0" = "bash" ]; then
    ROOT="$(pwd)"
else
    ROOT="$(cd "$(dirname "$0")" && pwd)"
fi

VENV_DIR="${R1_VENV_DIR:-$ROOT/.venv}"
MIN_PYTHON="3.9"
INSTALL_MODE=""
WITH_DEV=0
R1CMD_REPO="${R1CMD_REPO:-https://github.com/jalinuxy/r1cmd.git}"
R1CMD_VERSION="${R1CMD_VERSION:-}"

usage() {
    cat <<'EOF'
Usage: ./install.sh [options]

Install the r1 CLI (r1cmd) for ArvanCloud Object Storage.

Quick install (from the internet):
  curl -fsSL https://jalinuxy.ir/r1cmd | sh

Options:
  --user        Install into ~/.local (good for curl | sh)
  --system      Install into the active Python (requires write access)
  --venv        Install into a virtualenv (default when run from a git clone)
  --dev         Also install development dependencies (pytest, moto)
  --venv-path   Custom virtualenv directory (default: .venv next to install.sh)
  -h, --help    Show this help

Environment variables:
  R1CMD_VERSION   Pin version, e.g. 0.2.0 (PyPI) or a git branch/tag
  R1CMD_REPO      Git URL when installing from source (default: GitHub)
  R1_VENV_DIR     Override virtualenv path

After install:
  r1 setup        Save Access Key and Secret Key (one-time)
  r1              Open the interactive menu
EOF
}

log()  { printf '→ %s\n' "$*"; }
ok()   { printf '✓ %s\n' "$*"; }
fail() { printf '✗ %s\n' "$*" >&2; exit 1; }

is_local_clone() {
    [ -f "$ROOT/pyproject.toml" ]
}

is_piped_install() {
    [ ! -t 0 ]
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --user)   INSTALL_MODE="user"; shift ;;
        --system) INSTALL_MODE="system"; shift ;;
        --venv)   INSTALL_MODE="venv"; shift ;;
        --dev)    WITH_DEV=1; shift ;;
        --venv-path)
            [ "$#" -ge 2 ] || fail "Missing path after --venv-path"
            VENV_DIR="$2"
            shift 2
            ;;
        -h|--help) usage; exit 0 ;;
        *) fail "Unknown option: $1 (run install.sh --help)" ;;
    esac
done

if [ -z "$INSTALL_MODE" ]; then
    if is_local_clone; then
        INSTALL_MODE="venv"
    else
        INSTALL_MODE="user"
    fi
fi

find_python() {
    for cmd in python3 python3.12 python3.11 python3.10 python3.9; do
        if command -v "$cmd" >/dev/null 2>&1; then
            ver=$("$cmd" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null || echo "unknown")
            if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
                echo "$cmd"
                return 0
            fi
            log "Skipping $cmd ($ver) — need Python >= $MIN_PYTHON"
        fi
    done
    return 1
}

pip_spec() {
    if is_local_clone; then
        if [ "$WITH_DEV" -eq 1 ]; then
            printf '%s' "-e $ROOT[dev]"
        else
            printf '%s' "$ROOT"
        fi
        return 0
    fi

    if [ -n "$R1CMD_VERSION" ] && [ "$R1CMD_VERSION" != main ] && [ "$R1CMD_VERSION" != master ]; then
        case "$R1CMD_VERSION" in
            [0-9]*)
                echo "r1cmd==${R1CMD_VERSION}"
                ;;
            *)
                echo "r1cmd @ git+${R1CMD_REPO}@${R1CMD_VERSION}"
                ;;
        esac
        return 0
    fi

    echo "r1cmd"
}

run_pip() {
    if [ "$USE_VENV_PIP" -eq 1 ]; then
        pip install "$@"
    elif [ "$USE_USER_PIP" -eq 1 ]; then
        "$PYTHON" -m pip install --user "$@"
    else
        "$PYTHON" -m pip install "$@"
    fi
}

install_remote_package() {
    spec=$(pip_spec)
    fallback="r1cmd @ git+${R1CMD_REPO}"

    if [ "$WITH_DEV" -eq 1 ]; then
        spec="${spec}[dev]"
        fallback="r1cmd[dev] @ git+${R1CMD_REPO}"
    fi

    log "Installing $spec"
    if run_pip "$spec" 2>/dev/null; then
        return 0
    fi

    log "PyPI install unavailable — falling back to GitHub source"
    run_pip "$fallback"
}

ensure_user_path() {
    bindir="$HOME/.local/bin"
    case ":$PATH:" in
        *:"$bindir":*) return 0 ;;
    esac
    echo
    echo "Add ~/.local/bin to your PATH (once):"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    echo "  source ~/.bashrc"
    echo
    echo "Or run r1 directly:"
    echo "  $HOME/.local/bin/r1 setup"
}

PYTHON=$(find_python) || fail "Python $MIN_PYTHON or newer not found. Install it and retry."

log "Using $PYTHON ($($PYTHON --version 2>&1))"

if is_piped_install && ! is_local_clone; then
    log "Remote install (curl | sh)"
fi

USE_VENV_PIP=0
USE_USER_PIP=0
activate_hint=""

case "$INSTALL_MODE" in
    venv)
        if [ ! -d "$VENV_DIR" ]; then
            log "Creating virtual environment at $VENV_DIR"
            "$PYTHON" -m venv "$VENV_DIR"
        else
            log "Reusing virtual environment at $VENV_DIR"
        fi
        PATH="$VENV_DIR/bin:$PATH"
        USE_VENV_PIP=1
        activate_hint="source \"$VENV_DIR/bin/activate\""
        ;;
    user)
        USE_USER_PIP=1
        ;;
    system)
        ;;
esac

log "Upgrading pip"
run_pip --upgrade pip wheel setuptools --quiet

if is_local_clone; then
    log "Installing r1cmd from local source ($ROOT)"
    if [ "$WITH_DEV" -eq 1 ]; then
        run_pip -e "$ROOT[dev]"
    else
        run_pip "$ROOT"
    fi
else
    install_remote_package
fi

if command -v r1 >/dev/null 2>&1; then
    R1_BIN=$(command -v r1)
elif [ -x "${VENV_DIR}/bin/r1" ]; then
    R1_BIN="$VENV_DIR/bin/r1"
elif [ -x "$HOME/.local/bin/r1" ]; then
    R1_BIN="$HOME/.local/bin/r1"
else
    fail "Install finished but 'r1' command was not found on PATH."
fi

if ! "$R1_BIN" --help >/dev/null 2>&1; then
    fail "'r1' is installed but failed to run."
fi

ok "r1cmd installed successfully"
echo
echo "  r1 binary : $R1_BIN"
if [ -n "$activate_hint" ]; then
    echo "  activate  : $activate_hint"
fi

if [ "$INSTALL_MODE" = "user" ]; then
    ensure_user_path
fi

echo "Next steps:"
echo "  r1 setup    # save Access Key and Secret Key (one-time)"
echo "  r1          # open the interactive menu"
echo
