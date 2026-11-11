#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/cortaviral-ai
export PATH="$HOME/.deno/bin:$PATH"
export WHISPER_MODEL="${WHISPER_MODEL:-tiny}"
export WHISPER_CPU_THREADS="${WHISPER_CPU_THREADS:-1}"

mkdir -p work outputs

if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  echo "CortaViral AI já está em execução."
  exit 0
fi

nohup .venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 \
  > /tmp/cortaviral-ai.log 2>&1 < /dev/null &

for attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "CortaViral AI iniciado na porta 8000."
    exit 0
  fi
  sleep 2
done

echo "Falha ao iniciar. Últimas linhas do log:"
tail -n 80 /tmp/cortaviral-ai.log || true
exit 1
