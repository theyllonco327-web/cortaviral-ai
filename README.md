# CortaViral AI

Aplicativo web responsivo para analisar vídeos por URL, localizar trechos com sinais de potencial de retenção e exportar cortes verticais MP4 com legendas automáticas.

## Recursos do MVP
- Importação de vídeos por URL com yt-dlp, quando o site permite acesso público.
- Transcrição de fala com Faster-Whisper.
- Seleção de trechos com baixa sobreposição.
- Ranking heurístico baseado em curiosidade, emoção, ritmo e densidade de fala.
- Exportação em MP4 vertical 9:16 com legendas.
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

## Publicar
O repositório inclui um Dockerfile e render.yaml para iniciar uma publicação em serviço compatível com Docker, como Render. Revise o plano e os recursos antes de publicar. Processamento de vídeo exige CPU, memória e espaço em disco; instâncias gratuitas podem dormir, limitar execução e perder arquivos temporários.

## Sobre a pontuação
A nota é uma estimativa heurística baseada no conteúdo transcrito. Não é uma previsão confiável de visualizações e não garante viralização. O desempenho real depende do público, assunto, edição, distribuição e histórico do canal.

## Limitações
- Alguns sites exigem login, bloqueiam downloads ou não permitem extração por URL.
- Conteúdo privado, DRM e vídeos protegidos não são suportados.
- O enquadramento vertical atual usa corte central; ainda não faz rastreamento inteligente de rosto.
- A primeira versão não publica automaticamente nas redes sociais.
- Os arquivos temporários ficam no servidor e precisam de política de limpeza/armazenamento para uso contínuo.

## Segurança e direitos autorais
Este MVP é para uso pessoal e testes. Antes de abrir ao público, implemente autenticação, limites de uso, fila de processamento, proteção adicional contra SSRF, limpeza automática e armazenamento persistente. Use apenas vídeos próprios, licenciados ou cujo uso você tenha autorização.
