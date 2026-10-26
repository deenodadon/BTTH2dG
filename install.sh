#!/usr/bin/env bash
# Downloads the Ikemen GO engine (free, open-source MUGEN-compatible) and installs
# the Battle Through the Heavens 2.5D characters and stages into it.
# usage: ./install.sh [target-dir]      (default: ./ikemen)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$HERE/ikemen}"
case "$(uname -s)" in
  Linux*)  OS=linux ;;
  Darwin*) OS=mac ;;
  *) echo "Unsupported OS; on Windows run install.ps1"; exit 1 ;;
esac
if [ ! -d "$DEST/data" ]; then
  echo "Looking up the latest Ikemen GO release..."
  URL=$(curl -fsSL https://api.github.com/repos/ikemen-engine/Ikemen-GO/releases/latest \
        | grep -o '"browser_download_url": *"[^"]*"' | cut -d'"' -f4 | grep -i "$OS" | grep -i '\.zip$' | head -1)
  if [ -z "$URL" ]; then
    echo "Could not find a $OS download. Get Ikemen GO from https://github.com/ikemen-engine/Ikemen-GO/releases,"
    echo "unzip it to $DEST and run this script again."
    exit 1
  fi
  echo "Downloading $URL"
  TMP="$(mktemp -d)"
  curl -fL "$URL" -o "$TMP/ikemen.zip"
  mkdir -p "$DEST"
  unzip -q "$TMP/ikemen.zip" -d "$TMP/x"
  # the zip may contain a top-level folder
  SRC="$(dirname "$(find "$TMP/x" -maxdepth 3 -type d -name data | head -1)")"
  cp -R "$SRC/." "$DEST/"
  rm -rf "$TMP"
fi
echo "Installing characters and stages into $DEST"
mkdir -p "$DEST/chars" "$DEST/stages"
cp -R "$HERE/game/chars/." "$DEST/chars/"
cp -R "$HERE/game/stages/." "$DEST/stages/"
if [ -f "$DEST/data/select.def" ] && [ ! -f "$DEST/data/select.def.orig" ]; then
  cp "$DEST/data/select.def" "$DEST/data/select.def.orig"
fi
cp "$HERE/game/data/select.def" "$DEST/data/select.def"
chmod +x "$DEST"/Ikemen_GO* 2>/dev/null || true
echo "Done. Start the game with: $DEST/Ikemen_GO_Linux (Linux) or the Ikemen_GO app (macOS)."
