# CortaViral AI

O CortaViral AI agora possui um backend FastAPI e um aplicativo Android nativo.

## Gerar o APK
1. Abra a aba **Actions** deste repositório.
2. Selecione **Build CortaViral AI APK**.
3. Aguarde os jobs **backend-check** e **build-apk** concluírem com sucesso.
4. Abra a execução e baixe o artefato **cortaviral-ai-debug-apk**.
5. Extraia o arquivo baixado e instale `app-debug.apk` no Android.

O workflow também pode ser iniciado manualmente em **Actions → Build CortaViral AI APK → Run workflow**.

## Recursos do app Android
- Interface nativa em preto com contornos e destaques verde neon.
- Foto enviada pelo usuário na capa.
- Análise de vídeos por URL.
- Seleção e envio de vídeos da galeria do Android.
- Acompanhamento do processamento.
- Download dos cortes MP4 gerados.
- Cortes com duração entre **30 e 60 segundos**.
- Campo para configurar o endereço HTTPS do backend Render.

## Configuração do servidor
Na primeira abertura, informe a URL HTTPS pública do serviço Render. O app utiliza:
- `POST /api/analyze` para links do YouTube, TikTok e outras fontes compatíveis;
- `POST /api/analyze-upload` para vídeos selecionados no celular;
- `GET /api/jobs/{job_id}` para acompanhar o processamento.

## Limites reais
A aplicação não impõe limite artificial de duração ao vídeo original, mas o servidor ainda depende de CPU, RAM, espaço em disco, conexão e limites de execução do provedor. O yt-dlp suporta muitos sites, mas não garante qualquer URL. Vídeos privados, DRM, paywalls e links que exigem autenticação podem falhar. O suporte depende das regras e da disponibilidade de cada plataforma; o app não contorna proteção nem autenticação. Use somente vídeos que você tenha autorização para baixar e editar.

A nota de potencial viral é heurística e não garante visualizações.
