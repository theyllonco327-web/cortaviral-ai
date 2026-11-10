# CortaViral AI

Aplicativo web para analisar vídeos por URL, encontrar trechos com sinais de potencial de retenção e exportar cortes verticais MP4 com legendas automáticas.

## Recursos da versão 1.1
- Compatibilidade ampla com sites suportados pelo yt-dlp e links diretos de mídia.
- Sem limite artificial de duração do vídeo original configurado no aplicativo.
- Sem limite fixo de tamanho de arquivo configurado no yt-dlp.
- Transcrição do conteúdo com Faster-Whisper.
- Seleção de cortes entre **30 e 60 segundos**.
- Ranking heurístico baseado em curiosidade, emoção, ritmo e densidade de fala.
- Exportação MP4 vertical 9:16 com legendas automáticas.
- Acompanhamento do processamento e download dos cortes.

## Tecnologias
- Python 3.11
- FastAPI
- yt-dlp
- Faster-Whisper
- FFmpeg / FFprobe
- HTML, CSS e JavaScript

## Executar localmente

Instale Python 3.11+ e FFmpeg/FFprobe.

### Windows
```powershell
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000 no navegador.

## Publicação
O repositório inclui Dockerfile e render.yaml para serviços compatíveis com Docker, como Render. Um novo commit na branch principal pode iniciar um deploy automático se o serviço estiver configurado para auto-deploy.

## Limites reais de processamento
O aplicativo não define um limite fixo de duração do vídeo original nem de tamanho de download no yt-dlp. Isso **não significa processamento infinito**: CPU, RAM, disco, velocidade da conexão, tempo de execução do provedor e armazenamento temporário continuam sendo limites reais. Instâncias gratuitas podem dormir, reiniciar, ter pouco espaço e perder arquivos temporários. Vídeos muito longos podem demorar bastante ou exceder os recursos disponíveis.

## Compatibilidade e direitos autorais
O yt-dlp suporta muitos sites, mas nenhum programa consegue garantir download de qualquer URL. Links privados, DRM, vídeos que exigem autenticação, paywalls e plataformas que bloqueiam extração podem falhar. O aplicativo não tenta contornar DRM ou controles de acesso. Use apenas vídeos próprios, licenciados ou cujo download e edição você tenha autorização para fazer.

## Sobre a pontuação
A nota de 0 a 100 é uma estimativa heurística baseada na transcrição, em sinais de curiosidade e emoção e no ritmo da fala. Não é uma previsão confiável de visualizações e não garante viralização. Se a transcrição falhar, a versão atual seleciona janelas válidas por duração, mas não consegue avaliar semanticamente esses trechos.

## Melhorias futuras
- Rastreamento de rosto e reenquadramento vertical inteligente.
- Mais estilos de legenda e modelos de título/gancho.
- Fila de tarefas, autenticação, histórico e armazenamento persistente.
- Métricas reais dos vídeos publicados para calibrar o ranking.
