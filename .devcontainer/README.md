# CortaViral AI no GitHub Codespaces

Este ambiente permite testar o backend pelo navegador, inclusive em um celular, sem computador local e sem banco de dados.

## Criar o Codespace

1. Abra o repositório no GitHub.
2. Toque em **Code** > **Codespaces** > **Create codespace on main**.
3. Selecione a máquina de **2 cores** para usar a cota gratuita com mais eficiência.
4. Aguarde a configuração automática. O script instala FFmpeg, Deno e as dependências Python.
5. O servidor inicia automaticamente na porta 8000.

## Publicar a porta para o APK

1. Abra a aba **Ports** no VS Code Web.
2. Na linha da porta 8000, abra o menu de contexto.
3. Escolha **Port Visibility** > **Public**.
4. Copie o endereço encaminhado, no formato `https://NOME-DO-CODESPACE-8000.app.github.dev`.
5. Teste acrescentando `/api/health`.
6. Cole a URL base (sem `/api/health`) nas configurações do APK.

A porta pública permite que qualquer pessoa que tenha o endereço acesse a API. Use-a somente durante os testes e torne-a privada ou pare o Codespace ao terminar.

## Limites

O GitHub Free inclui 120 core-hours e 15 GB-month de armazenamento por mês para Codespaces pessoais. Uma máquina de 2 cores consome 2 core-hours por hora ligada (aproximadamente 60 horas de execução por mês). Quando a cota acabar, o Codespace gratuito será bloqueado até a renovação, se não houver forma de pagamento cadastrada.

O Codespace não é hospedagem 24/7: pode parar por inatividade e a URL encaminhada só funciona enquanto o Codespace e o servidor estiverem ativos.

## Logs

No terminal:

```bash
tail -f /tmp/cortaviral-ai.log
```

O projeto usa arquivos locais em `work/` e `outputs/`; não há banco de dados externo.
