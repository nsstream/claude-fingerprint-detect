#!/bin/bash
# Install:   curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash
# Uninstall: curl -fsSL https://raw.githubusercontent.com/nsstream/claude-fingerprint-detect/main/install.sh | bash -s -- --uninstall
set -euo pipefail

REPO="https://github.com/nsstream/claude-fingerprint-detect"
NAME="claude-fingerprint-detect"
DIR="${CFD_HOME:-$HOME/.claude-fingerprint-detect}"
BIN_DIR="${CFD_BIN_DIR:-$HOME/.local/bin}"
BIN="$BIN_DIR/$NAME"
PATH_LINE="export PATH=\"$BIN_DIR:\$PATH\""

if [ "$(uname -s)" != "Darwin" ]; then
  echo "$NAME only supports macOS." >&2
  exit 1
fi

rc_file() {
  case "${SHELL:-}" in
    */bash) echo "$HOME/.bash_profile" ;;
    *) echo "$HOME/.zshrc" ;;
  esac
}

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$BIN"
  echo "Removed $BIN"
  if [ -d "$DIR/backups" ] || [ -d "$DIR/reports" ]; then
    echo "Kept $DIR because it contains backups/ or reports/. Delete it yourself when you no longer need them:"
    echo "  rm -rf \"$DIR\""
  else
    rm -rf "$DIR"
    echo "Removed $DIR"
  fi
  exit 0
fi

if [ ! -x /usr/bin/python3 ] || ! /usr/bin/python3 -c "" >/dev/null 2>&1; then
  echo "Python 3 is missing. Run: xcode-select --install   then run this installer again." >&2
  exit 1
fi

if [ -d "$DIR/.git" ] && command -v git >/dev/null 2>&1; then
  echo "Updating $DIR ..."
  git -C "$DIR" pull --ff-only --quiet
elif command -v git >/dev/null 2>&1 && [ ! -e "$DIR" ]; then
  echo "Installing to $DIR ..."
  git clone --quiet --depth 1 "$REPO.git" "$DIR"
else
  echo "Installing to $DIR ..."
  mkdir -p "$DIR"
  curl -fsSL "$REPO/archive/refs/heads/main.tar.gz" | tar -xz --strip-components=1 -C "$DIR"
fi

mkdir -p "$BIN_DIR"
cat > "$BIN" <<EOF
#!/bin/bash
CFD_PROG="$NAME" exec /usr/bin/python3 "$DIR/claude_fingerprint_detect.py" "\$@"
EOF
chmod 755 "$BIN"

case ":$PATH:" in
  *":$BIN_DIR:"*) ON_PATH=1 ;;
  *) ON_PATH=0 ;;
esac
if [ "$ON_PATH" = 0 ]; then
  RC="$(rc_file)"
  if ! grep -qsF "$PATH_LINE" "$RC"; then
    printf '\n%s\n' "$PATH_LINE" >> "$RC"
  fi
fi

echo
echo "Installed: $("$BIN" --version)"
echo
if [ "$ON_PATH" = 0 ]; then
  echo "Open a new terminal window (or run: source \"$RC\"), then:"
else
  echo "Run:"
fi
echo "  $NAME check     # fingerprint check (read-only)"
echo "  $NAME backup    # back up every Claude trace"
echo "  $NAME clean     # remove every Claude trace"
echo "  $NAME           # interactive menu"
