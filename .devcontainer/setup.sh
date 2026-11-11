#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/cortaviral-ai

sudo apt-get update
sudo apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core curl ca-certificates
sudo rm -rf /var/lib/apt/lists/*

if ! command -v deno >/dev/null 2>&1 && [[ ! -x "$HOME/.deno/bin/deno" ]]; then
  curl -fsSL https://deno.land/install.sh | sh
fi

export PATH="$HOME/.deno/bin:$PATH"
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install --no-cache-dir -r requirements.txt

mkdir -p work outputs
printf '\nCortaViral AI dependencies installed.\n'
