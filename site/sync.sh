#!/bin/sh
# Export the catalogue, rebuild the site and rsync it to SYNC_TARGET (or the contents of ../.sync-target).
set -eu

target="${SYNC_TARGET:-}"
if [ -z "$target" ] && [ -f ../.sync-target ]; then
  target=$(tr -d '[:space:]' < ../.sync-target)
fi
if [ -z "$target" ]; then
  echo "No sync target. Set SYNC_TARGET or put one in .sync-target, e.g. user@host:/var/www/my-shelf/" >&2
  exit 1
fi

python3 ../books.py export
npm run build
rsync -avz --delete _site/ "$target"
