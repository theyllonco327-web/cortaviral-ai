from pathlib import Path

path = Path("android/app/src/main/java/com/cortaviral/ai/MainActivity.java")
source = path.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global source
    if old not in source:
        raise SystemExit("Não foi possível aplicar ajuste Android: " + label)
    source = source.replace(old, new, 1)

replace_once(
    '        page.addView(subtitle, subParams);\n\n        FrameLayout coverFrame = new FrameLayout(this);',
    '''        page.addView(subtitle, subParams);

        LinearLayout sourceChips = new LinearLayout(this);
        sourceChips.setOrientation(LinearLayout.HORIZONTAL);
        sourceChips.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams chipsParams = new LinearLayout.LayoutParams(-1, -2);
        chipsParams.topMargin = dp(13);
        page.addView(sourceChips, chipsParams);
        String[] sources = {"YOUTUBE", "TIKTOK", "GALERIA"};
        for (int i = 0; i < sources.length; i++) {
            TextView chip = sourceChip(sources[i]);
            LinearLayout.LayoutParams chipParams = new LinearLayout.LayoutParams(-2, -2);
            if (i > 0) chipParams.leftMargin = dp(7);
            sourceChips.addView(chip, chipParams);
        }

        FrameLayout coverFrame = new FrameLayout(this);''',
    "indicadores de fontes"
)
replace_once(
    'LinearLayout.LayoutParams coverParams = new LinearLayout.LayoutParams(-1, dp(260));',
    'LinearLayout.LayoutParams coverParams = new LinearLayout.LayoutParams(-1, dp(232));',
    "proporção da capa"
)
replace_once(
    '''    private TextView sectionTitle(String value) {
        return text(value, 11, NEON, true);
    }
''',
    '''    private TextView sectionTitle(String value) {
        return text(value, 11, NEON, true);
    }

    private TextView sourceChip(String value) {
        TextView chip = text(value, 9, NEON, true);
        chip.setLetterSpacing(0.06f);
        chip.setPadding(dp(10), dp(7), dp(10), dp(7));
        chip.setBackground(shape(0xFF0D1A11, 0xFF28663C, 30));
        return chip;
    }
''',
    "componente de chips"
)
replace_once(
    '''    private boolean requireServer() {
        if (apiBase().isEmpty()) {
            showServerDialog();
            return false;
        }
        return true;
    }''',
    '''    private boolean requireServer() {
        String base = apiBase();
        if (base.isEmpty()) {
            showServerDialog();
            return false;
        }
        String host = Uri.parse(base).getHost();
        if (host == null || isVideoPlatformHost(host)) {
            toast("A configuração do servidor está incorreta. Informe a URL do Render em ⚙; o link do vídeo vai na tela principal.");
            showServerDialog();
            return false;
        }
        return true;
    }''',
    "validação do servidor salvo"
)

replace_once(
    '''    private void beginPolling(String jobId) {
        runOnUiThread(() -> setBusy(true, "Vídeo recebido. Iniciando análise…", 8));
        executor.schedule(() -> poll(jobId), 2, TimeUnit.SECONDS);
    }

    private void poll(String jobId) {
        try {
            JSONObject job = requestJson("GET", apiBase() + "/api/jobs/" + jobId, null);
            String state = job.optString("status", "processing");
            int progress = job.optInt("progress", 0);
            String message = job.optString("message", "Analisando vídeo…");
            runOnUiThread(() -> setBusy(true, message, progress));
            if ("completed".equals(state)) {
                runOnUiThread(() -> showResults(job));
            } else if ("error".equals(state)) {
                showError(job.optString("message", "Falha ao processar o vídeo."));
            } else {
                executor.schedule(() -> poll(jobId), 4, TimeUnit.SECONDS);
            }
        } catch (Exception error) {
            runOnUiThread(() -> statusText.setText("Reconectando ao servidor…"));
            executor.schedule(() -> poll(jobId), 7, TimeUnit.SECONDS);
        }
    }
''',
    '''    private void beginPolling(String jobId) {
        runOnUiThread(() -> setBusy(true, "Vídeo recebido. Iniciando análise…", 8));
        long startedAt = android.os.SystemClock.elapsedRealtime();
        executor.schedule(() -> poll(jobId, 0, startedAt), 2, TimeUnit.SECONDS);
    }

    private void poll(String jobId, int failures, long startedAt) {
        if (android.os.SystemClock.elapsedRealtime() - startedAt > TimeUnit.MINUTES.toMillis(45)) {
            showError("A análise ultrapassou 45 minutos. O servidor pode estar sem recursos; tente novamente mais tarde.");
            return;
        }
        try {
            JSONObject job = requestJson("GET", apiBase() + "/api/jobs/" + jobId, null);
            String state = job.optString("status", "processing");
            int progress = job.optInt("progress", 0);
            String message = job.optString("message", "Analisando vídeo…");
            runOnUiThread(() -> setBusy(true, message, progress));
            if ("completed".equals(state)) {
                runOnUiThread(() -> showResults(job));
            } else if ("error".equals(state)) {
                showError(job.optString("message", "Falha ao processar o vídeo."));
            } else if ("queued".equals(state) || "processing".equals(state)) {
                executor.schedule(() -> poll(jobId, 0, startedAt), 5, TimeUnit.SECONDS);
            } else {
                showError("O servidor retornou um estado de análise desconhecido: " + state);
            }
        } catch (Exception error) {
            String detail = error.getMessage() == null ? "" : error.getMessage();
            if (detail.contains("HTTP 404")) {
                showError("A tarefa de análise não está mais disponível. O servidor pode ter reiniciado; envie o vídeo novamente.");
                return;
            }
            int nextFailures = failures + 1;
            if (nextFailures >= 6) {
                showError("Não foi possível recuperar a análise após 6 tentativas. Último erro: " + detail);
                return;
            }
            int attempt = nextFailures;
            runOnUiThread(() -> statusText.setText("Reconectando ao servidor (" + attempt + "/6)…"));
            executor.schedule(() -> poll(jobId, nextFailures, startedAt), 5, TimeUnit.SECONDS);
        }
    }
''',
    "polling com limite de tentativas e timeout"
)

replace_once(
    '''    private void showError(String message) {
        runOnUiThread(() -> {
            setBusy(false, "Não foi possível concluir a análise.", 0);
            statusText.setTextColor(0xFFFF8A8A);
            String detail = (message == null || message.trim().isEmpty())
                    ? "Erro de conexão. Confira a URL do servidor nas configurações ⚙."
                    : message;
            toast(detail);
        });
    }
''',
    '''    private void showError(String message) {
        runOnUiThread(() -> {
            setBusy(false, "Não foi possível concluir a análise.", 0);
            String detail = (message == null || message.trim().isEmpty())
                    ? "Erro de conexão. Confira a URL do servidor nas configurações ⚙."
                    : message;
            statusText.setText("Falha: " + (detail.length() > 220 ? detail.substring(0, 220) + "…" : detail));
            statusText.setTextColor(0xFFFF8A8A);
            resultsBox.removeAllViews();
            TextView details = text(detail, 11, MUTED, false);
            resultsBox.addView(details);
            toast(detail);
        });
    }
''',
    "exibição do erro completo"
)


# v1.5 visual refresh: Telegram-inspired blue palette, no hero photo.
source = source.replace("private static final int BLACK = Color.rgb(5, 8, 5);", "private static final int BLACK = Color.rgb(10, 16, 24);")
source = source.replace("private static final int PANEL = Color.rgb(15, 22, 16);", "private static final int PANEL = Color.rgb(18, 27, 39);")
source = source.replace("private static final int PANEL_2 = Color.rgb(20, 31, 22);", "private static final int PANEL_2 = Color.rgb(24, 37, 52);")
source = source.replace("private static final int NEON = Color.rgb(57, 255, 114);", "private static final int NEON = Color.rgb(42, 153, 255);")
source = source.replace("private static final int MUTED = Color.rgb(153, 171, 157);", "private static final int MUTED = Color.rgb(151, 171, 193);")
source = source.replace(
    "    private SharedPreferences preferences;\n",
    """    private SharedPreferences preferences;
    private int selectedClips = 5;
    private String selectedAspectRatio = "9:16";
    private Button clipCountButton;
    private Button aspectRatioButton;
"""
)
source = source.replace(
    "        preferences = getSharedPreferences(PREFS, MODE_PRIVATE);\n",
    """        preferences = getSharedPreferences(PREFS, MODE_PRIVATE);
        selectedClips = preferences.getInt("clip_count", 5);
        selectedAspectRatio = preferences.getString("aspect_ratio", "9:16");
"""
)
cover_start = source.find("        FrameLayout coverFrame = new FrameLayout(this);")
cover_end_marker = "        page.addView(coverFrame, coverParams);\n"
cover_end = source.find(cover_end_marker, cover_start)
if cover_start < 0 or cover_end < 0:
    raise SystemExit("Não foi possível localizar a foto de capa antiga.")
cover_end += len(cover_end_marker)
welcome = """        LinearLayout welcomeBubble = new LinearLayout(this);
        welcomeBubble.setOrientation(LinearLayout.VERTICAL);
        welcomeBubble.setPadding(dp(16), dp(14), dp(16), dp(14));
        welcomeBubble.setBackground(shape(PANEL_2, 0xFF294B70, 18));
        welcomeBubble.addView(text("Olá! Vamos transformar seu vídeo em cortes.", 14, WHITE, true));
        TextView welcomeMessage = text("Envie um link público compatível ou escolha um arquivo da galeria. A análise aparece aqui, como uma conversa.", 12, MUTED, false);
        LinearLayout.LayoutParams welcomeMessageParams = new LinearLayout.LayoutParams(-1, -2);
        welcomeMessageParams.topMargin = dp(6);
        welcomeBubble.addView(welcomeMessage, welcomeMessageParams);
        LinearLayout.LayoutParams welcomeParams = new LinearLayout.LayoutParams(-1, -2);
        welcomeParams.topMargin = dp(18);
        page.addView(welcomeBubble, welcomeParams);

"""
source = source[:cover_start] + welcome + source[cover_end:]
path.write_text(source, encoding="utf-8")
print("Android: interface preservada; polling limitado, timeout e erro detalhado aplicados.")
