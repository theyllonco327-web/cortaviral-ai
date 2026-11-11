# CortaViral AI

Aplicativo Android híbrido com **Java + HTML + CSS + JavaScript**.

## Arquitetura atual

- **Java Android (WebMainActivity)**: abre o aplicativo em WebView, permite escolher vídeos da galeria e recebe downloads.
- **HTML (static/index.html)**: estrutura das telas.
- **CSS (static/styles.css)**: identidade visual responsiva inspirada em aplicativos de mensagens.
- **JavaScript (static/app.js)**: envio de links e vídeos, acompanhamento das tarefas, apresentação dos cortes e histórico local via localStorage do navegador/WebView.
- **Backend de processamento**: FastAPI/Python permanece temporariamente responsável por yt-dlp, FFmpeg e Faster-Whisper. Essa parte não foi reescrita porque trocar a linguagem não elimina bloqueios de acesso impostos pelo YouTube e uma migração do motor de mídia exige testes próprios.

## Recursos

- Download por URL usando os extratores automáticos do yt-dlp, com nova tentativa pelo extrator genérico para páginas comuns que falhem no primeiro método.
- Suporte a diferentes sites e links diretos de vídeo quando o conteúdo estiver publicamente acessível e tecnicamente extraível.
- Importação de vídeos da galeria Android.
- Escolha de 1, 3, 5, 7 ou 10 cortes.
- Formatos 9:16, 1:1 e 16:9.
- Cortes de 30 a 90 segundos; janelas automáticas procuram aproveitar a faixa até 90s.
- Legendas automáticas quando a transcrição está disponível.
- Pré-visualização e download dos cortes.
- Histórico local no dispositivo, sem banco remoto de histórico.
- Configuração do endereço HTTPS do servidor.

## Publicar e gerar APK

O Render publica o backend e a interface estática a partir da branch main. O GitHub Actions verifica a sintaxe JavaScript, valida o backend e compila o APK Android.

1. Abra a aba Actions.
2. Selecione Build CortaViral AI APK.
3. Aguarde backend-check e build-apk terminarem com sucesso.
4. Baixe o artefato cortaviral-ai-debug-apk, extraia e instale app-debug.apk.

## Limites importantes

- O histórico fica no armazenamento local do navegador/WebView neste aparelho. Limpar os dados do aplicativo pode apagá-lo.
- Os arquivos de vídeo são enviados ao servidor para processamento; apenas o histórico fica local.
- A compatibilidade de URL é ampla, não universal: vídeos privados, DRM, paywalls, login obrigatório, URLs expiradas ou bloqueios da plataforma podem impedir o download. Não há tentativa de contornar essas proteções.
- Vídeos privados, protegidos por DRM ou que exijam login podem não funcionar.
- A pontuação de potencial viral é heurística e não garante visualizações.
