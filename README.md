# CortaViral AI

Aplicativo Android híbrido com **Java + HTML + CSS + JavaScript**.

## Site e aplicativo

- A página pública de apresentação fica em `/`, com formulário de link, explicação dos recursos, fluxo de uso e perguntas frequentes.
- O estúdio de edição continua disponível em `/app/`; os links enviados pela página inicial são encaminhados para o campo de URL do editor.
- O APK Android abre diretamente em `/app/`, preservando a experiência de aplicativo.

## Arquitetura atual

- **Java Android (WebMainActivity)**: abre o aplicativo em WebView, permite escolher vídeos da galeria e recebe downloads.
- **HTML (static/index.html)**: estrutura das telas.
- **CSS (static/styles.css)**: identidade visual responsiva inspirada em aplicativos de mensagens.
- **JavaScript (static/app.js)**: envio de links e vídeos, acompanhamento das tarefas, apresentação dos cortes e histórico local via localStorage do navegador/WebView.
- **Backend de processamento**: FastAPI/Python integra yt-dlp, FFmpeg e Faster-Whisper; o APK e o navegador usam a mesma API, sem um segundo servidor Streamlit.

## Recursos

- Download por URL usando os extratores automáticos do yt-dlp, com nova tentativa pelo extrator genérico para páginas comuns que falhem no primeiro método.
- Suporte a diferentes sites e links diretos de vídeo quando o conteúdo estiver publicamente acessível e tecnicamente extraível.
- Importação de vídeos da galeria Android.
- Escolha de 1, 3, 5, 7 ou 10 cortes.
- Formatos 9:16, 1:1 e 16:9.
- Duração mínima e máxima configurável entre 30 e 90 segundos.
- Análise combinada de fala, palavras de impacto e atividade visual em quadros reduzidos; quando a transcrição falha, o sistema ainda classifica janelas pela atividade visual.
- Opção para ativar ou desativar legendas queimadas no vídeo.
- Legendas de publicação e hashtags sugeridas, com cópia rápida.
- Compartilhamento do corte pelo menu nativo do celular quando disponível.
- Diagnóstico visível da API, versão e commit publicado; erros HTML, HTTP 404 e HTTP 405 recebem explicação específica.
- Estado das tarefas espelhado em JSON no disco temporário do servidor para melhorar a recuperação após reinício do processo.
- Legendas automáticas quando a transcrição está disponível.
- Pré-visualização e download dos cortes.
- Histórico local no dispositivo, sem banco remoto de histórico.
- Configuração do endereço HTTPS do servidor, com rejeição de URLs de plataformas de vídeo usadas por engano como servidor.

## Publicar e gerar APK

O Render publica o backend e a interface estática a partir da branch main. O GitHub Actions verifica a sintaxe JavaScript, valida o backend e compila o APK Android.

1. Abra a aba Actions.
2. Selecione Build CortaViral AI APK.
3. Aguarde backend-check e build-apk terminarem com sucesso.
4. Baixe o artefato cortaviral-ai-debug-apk, extraia e instale app-debug.apk.

## Limites importantes

- O espelho JSON de tarefas no servidor usa armazenamento temporário da instância; não substitui um disco persistente e não sobrevive necessariamente a um novo deploy ou troca de instância.

- O histórico fica no armazenamento local do navegador/WebView neste aparelho. Limpar os dados do aplicativo pode apagá-lo.
- Os arquivos de vídeo são enviados ao servidor para processamento; apenas o histórico fica local.
- A compatibilidade de URL é ampla, não universal: vídeos privados, DRM, paywalls, login obrigatório, URLs expiradas ou bloqueios da plataforma podem impedir o download. Não há tentativa de contornar essas proteções.
- Vídeos privados, protegidos por DRM ou que exijam login podem não funcionar.
- A pontuação de potencial viral combina sinais heurísticos de fala e movimento visual e não garante visualizações.
