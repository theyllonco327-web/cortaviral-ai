# CortaViral AI — diagnóstico Android

Projeto nativo para Android 10 ou superior. Esta é uma versão de **diagnóstico de captura**, não a versão de cortes automáticos. O código recebe links do YouTube e do TikTok, abre o player e solicita consentimento do Android para medir o áudio interno e a imagem em movimento. Não salva nem envia áudio ou imagens. O filtro de impacto também está no código, mas não está ligado à captura nem à exportação MP4.

## Gerar o APK

- Android Studio: abra esta pasta, sincronize o Gradle com o SDK Android 35 e gere o APK de depuração pelo menu Build. O arquivo deverá ficar em `app/build/outputs/apk/debug/app-debug.apk`.
- Linha de comando: use JDK 17, Gradle 8.9, Android SDK com plataforma 35 e Build Tools 34.0.0. Execute `gradle :app:assembleDebug`. O APK de depuração é assinado pelo Android Gradle Plugin.
- GitHub Actions: em um repositório que contenha estes arquivos na raiz, o fluxo **Compilar APK de diagnóstico** pode ser disparado manualmente na aba Actions. Ele executa os testes Java, gera o APK e verifica a assinatura antes de publicar o artefato do job. O fluxo faz parte deste pacote, mas não foi executado aqui.

## Teste no celular após gerar e instalar o APK

1. Abra o CortaViral AI e cole o link da live.
2. Toque em **Testar áudio e imagem** e autorize a captura quando o Android pedir.
3. Deixe a live tocar com fala e movimento por cerca de 20 segundos.
4. Volte ao CortaViral e veja os resultados de áudio e imagem separadamente.
5. Repita com a outra plataforma. Se a transmissão estiver em silêncio ou estática, repita em outro trecho. A detecção de movimento é indicativa e também pode reagir à interface do player.

## Estado da verificação

Os dois formatos de link apresentados no projeto e a lógica de sinais e impacto foram testados na JVM com amostras simuladas. O projeto não foi compilado como aplicativo nem testado em dispositivo Android neste ambiente. A captura real do YouTube e do TikTok continua pendente.
