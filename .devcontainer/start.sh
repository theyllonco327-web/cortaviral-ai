#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/cortaviral-ai
export PATH="$HOME/.deno/bin:$PATH"
export WHISPER_MODEL="${WHISPER_MODEL:-tiny}"
export WHISPER_CPU_THREADS="${WHISPER_CPU_THREADS:-1}"

mkdir -p work outputs

if ! curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  nohup .venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 \
    > /tmp/cortaviral-ai.log 2>&1 < /dev/null &
fi

if ! .venv/bin/python -c "import streamlit, yt_dlp, cv2, moviepy" >/dev/null 2>&1; then
  echo "Instalando o motor Streamlit/MoviePy pela primeira vez..."
  if ! .venv/bin/pip install --no-cache-dir -r requirements-streamlit.txt; then
    echo "Não foi possível instalar a interface Streamlit; a API Android continua iniciando."
    exit 0
  fi
fi

if ! curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
  nohup .venv/bin/streamlit run streamlit_app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false \
    > /tmp/cortaviral-streamlit.log 2>&1 < /dev/null &
fi

api_ready=false
studio_ready=false
for attempt in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then api_ready=true; fi
  if curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then studio_ready=true; fi
  if [[ "$api_ready" == true && "$studio_ready" == true ]]; then
    echo "CortaViral API pronta na porta 8000."
    echo "CortaViral Studio pronto na porta 8501."
    exit 0
  fi
  sleep 2
done

echo "Estado de inicialização:"
echo "API (8000): $api_ready"
echo "Studio (8501): $studio_ready"
tail -n 40 /tmp/cortaviral-ai.log 2>/dev/null || true
tail -n 40 /tmp/cortaviral-streamlit.log 2>/dev/null || true
if [[ "$api_ready" != true ]]; then exit 1; fi
exit 0
