# CortaViral AI — Site

O CortaViral AI é uma aplicação web responsiva para transformar vídeos em cortes curtos com apoio de IA. O site funciona no navegador do celular e do computador; não é necessário instalar o APK.

## Endereços do site

- **Página inicial:** `/`
- **Estúdio de edição:** `/app/`
- **Diagnóstico da API:** `/api/health`

A página inicial apresenta o produto e encaminha o usuário ao estúdio. O estúdio recebe um link público ou um arquivo de vídeo do dispositivo, acompanha o processamento e permite visualizar e baixar os cortes.

## Sem banco de dados

Esta versão não usa banco de dados, cadastro ou login.

- **Histórico:** fica no `localStorage` do navegador, no próprio aparelho.
- **Estado temporário dos trabalhos:** arquivos JSON dentro da pasta `work/` do servidor.
- **Vídeos e cortes processados:** ficam temporariamente nas pastas `work/` e `outputs/`.
- **Sem sincronização entre aparelhos:** o histórico do navegador não é compartilhado entre celulares ou computadores.
- **Sem persistência garantida no servidor:** em hospedagens com disco efêmero, reinícios, suspensão ou novo deploy podem apagar tarefas e arquivos. O usuário deve baixar os cortes assim que estiverem prontos.

Não adicione PostgreSQL, MySQL, SQLite, Redis ou outro banco para executar o fluxo atual.

## Como funciona

1. O navegador abre o site e envia um link ou vídeo ao backend.
2. A API FastAPI cria uma tarefa e grava seu estado temporário em JSON.
3. O backend usa yt-dlp para obter vídeos de URLs compatíveis, Faster-Whisper para transcrição quando disponível e FFmpeg para renderizar os cortes.
4. O navegador consulta o andamento, exibe os resultados e salva uma referência ao projeto no histórico local.

## Recursos implementados

- Importação de vídeos da galeria pelo navegador.
- Análise de links públicos compatíveis com yt-dlp.
- Escolha de 1, 3, 5, 7 ou 10 cortes.
- Formatos 9:16, 1:1 e 16:9.
- Duração configurável entre 30 e 90 segundos.
- Análise de fala e atividade visual.
- Legendas incorporadas quando a transcrição está disponível.
- Pré-visualização, download individual e download em ZIP.
- Legendas sugeridas e hashtags para publicação.
- Histórico local no navegador, sem conta e sem banco de dados.

A pontuação de potencial viral é heurística e não garante visualizações. Vídeos privados, protegidos por DRM, paywall ou login obrigatório podem não ser processados; o sistema não tenta contornar essas proteções.

## Arquitetura

- **Frontend:** HTML, CSS e JavaScript em `static/`.
- **Página inicial:** `static/index.html`.
- **Estúdio:** `static/app.html`.
- **Lógica do navegador:** `static/app.js`.
- **Backend:** FastAPI/Python em `app.py`.
- **Processamento de mídia:** yt-dlp, FFmpeg e Faster-Whisper.
- **API e site no mesmo serviço:** o navegador usa o domínio atual do site para chamar `/api/*`; não é necessário configurar um segundo domínio de API.

## Publicação do site

O repositório inclui `Dockerfile` e `render.yaml` para publicar o site e o backend como um único serviço web no Render.

1. Conecte o repositório GitHub ao Render.
2. Crie um serviço usando o Blueprint do arquivo `render.yaml`.
3. Mantenha o runtime Docker e as variáveis de ambiente definidas no Blueprint.
4. Aguarde a publicação e abra o domínio HTTPS gerado pelo Render.
5. Teste `https://SEU-DOMINIO/api/health`; a resposta deve conter `"ok": true` e `"database": "none"`.
6. Abra `/app/` para usar o estúdio.

O plano gratuito pode suspender o serviço quando estiver inativo e tem limites de CPU, memória e tempo de execução. O processamento de vídeos grandes pode exceder esses limites. Não há banco de dados nem disco persistente configurado neste projeto.

## Limitações de privacidade e armazenamento

Os vídeos enviados são transferidos ao servidor para processamento. Não existe armazenamento permanente ou sincronização na nuvem nesta configuração. O histórico local pode ser apagado ao limpar os dados do navegador. Não envie conteúdo privado ou sensível se não estiver confortável com o processamento no servidor.
