#!/usr/bin/env bash
# Download the GAIN dataset (1.34 GB zip) into .context/data and decompress.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DEST="$ROOT/.context/data"
mkdir -p "$DEST"
cd "$DEST"

if [ ! -f data.zip ]; then
  echo "Downloading 1.34 GB data.zip from Google Drive..."
  gdown --folder "https://drive.google.com/drive/folders/1HhcFbD4Zf0cOD0Ib-89aV4zLoylJ1UiP" -O .
fi
if [ ! -d data ]; then
  echo "Decompressing data.zip..."
  unzip -q data.zip -d .
  rm -rf __MACOSX || true
fi
echo "OK: $DEST/data ($(du -sh data | awk '{print $1}'))"
