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
- Opção para ativar ou desativar legendas queimadas no vídeo.
- Legendas de publicação e hashtags sugeridas, com cópia rápida.
- Compartilhamento do corte pelo menu nativo do celular quando disponível.
- Diagnóstico visível da API, versão e commit publicado; erros HTML, HTTP 404 e HTTP 405 recebem explicação específica.
- Estado das tarefas espelhado em JSON no disco temporário do servidor para melhorar a recuperação após reinício do processo.
- Legendas automáticas quando a transcrição está disponível.
- Pré-visualização e download dos cortes.
- Histórico local no dispositivo, sem banco remoto de histórico.
- Configuração do endereço HTTPS do servidor, com rejeição de URLs de plataformas de vídeo usadas por engano como servidor.

## Versão alternativa Streamlit

O projeto também contém uma interface independente em \`streamlit_app.py\`, corrigida para MoviePy 2.x. Ela não substitui nem altera a interface Android/FastAPI usada pelo APK.

Para executar essa versão em outro ambiente Python 3.11 com FFmpeg instalado:

\`\`\`bash
python -m pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
\`\`\`

A interface alternativa permite importar um vídeo, baixar links públicos compatíveis com yt-dlp, selecionar cortes de 30 a 90 segundos, recortar para 9:16 ou 1:1, aproveitar legendas SRT disponíveis e baixar os cortes individualmente ou em ZIP. O teste automatizado gera um vídeo sintético e verifica o processamento MoviePy 2.x.

No GitHub Codespaces, o contêiner também encaminha a porta 8501 e inicia o Studio automaticamente junto da API na porta 8000. Abra a aba **Ports** e selecione **CortaViral AI Studio (Streamlit)** para testar essa interface pelo navegador do celular.

A instalação Streamlit fica em um arquivo de dependências separado para não aumentar a imagem Docker do servidor Android nem piorar seu tempo de inicialização no Render.

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
- A pontuação de potencial viral é heurística e não garante visualizações.
