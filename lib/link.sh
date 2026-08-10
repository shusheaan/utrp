#!/bin/sh
# Expose this repo's assets to the hosts via symlinks:
#   Surge XT browser  <- lib/surge (patches)
#   REAPER Scripts    <- lib/tools/reaper (ReaScript bridge), if REAPER config exists
# Rerun after a system reinstall (this repo is not managed by gral's installer).
set -eu
SURGE_USER="$HOME/.Surge Synth Team/Surge XT/Patches"
SRC="$(cd "$(dirname "$0")/surge" && pwd)"
mkdir -p "$SURGE_USER"
ln -sfn "$SRC" "$SURGE_USER/utrp"
echo "linked: $SURGE_USER/utrp -> $SRC"

REAPER_SCRIPTS="$HOME/.config/REAPER/Scripts"
if [ -d "$HOME/.config/REAPER" ]; then
    mkdir -p "$REAPER_SCRIPTS"
    LUA_SRC="$(cd "$(dirname "$0")/tools/reaper" && pwd)"
    ln -sfn "$LUA_SRC" "$REAPER_SCRIPTS/utrp"
    echo "linked: $REAPER_SCRIPTS/utrp -> $LUA_SRC"
else
    echo "skip: ~/.config/REAPER not found (run REAPER once, then rerun)"
fi
