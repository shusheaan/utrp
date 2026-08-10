#!/bin/sh
# Expose this repo's Surge patches to the Surge XT browser via a symlink.
# Rerun after a system reinstall (this repo is not managed by gral's installer).
set -eu
SURGE_USER="$HOME/.Surge Synth Team/Surge XT/Patches"
SRC="$(cd "$(dirname "$0")/surge" && pwd)"
mkdir -p "$SURGE_USER"
ln -sfn "$SRC" "$SURGE_USER/utrp"
echo "linked: $SURGE_USER/utrp -> $SRC"
