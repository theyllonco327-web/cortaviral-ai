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

# v1.5 additional functions: paste link, choose number of clips, aspect ratio and ZIP export.
source = source.replace(
    "        inputCard.addView(urlInput, urlParams);\n",
    """        inputCard.addView(urlInput, urlParams);
        Button pasteButton = button("COLAR LINK DA ÁREA DE TRANSFERÊNCIA", false);
        LinearLayout.LayoutParams pasteParams = new LinearLayout.LayoutParams(-1, dp(42));
        pasteParams.topMargin = dp(8);
        inputCard.addView(pasteButton, pasteParams);
        pasteButton.setOnClickListener(v -> pasteLink());
""", 1
)
source = source.replace(
    '        galleryButton.setOnClickListener(v -> openGallery());\n',
    """        galleryButton.setOnClickListener(v -> openGallery());
        TextView optionsLabel = text("PREFERÊNCIAS DE CORTE", 10, MUTED, true);
        LinearLayout.LayoutParams optionsLabelParams = new LinearLayout.LayoutParams(-1, -2);
        optionsLabelParams.topMargin = dp(16);
        inputCard.addView(optionsLabel, optionsLabelParams);
        LinearLayout optionsRow = new LinearLayout(this);
        optionsRow.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams optionsRowParams = new LinearLayout.LayoutParams(-1, dp(48));
        optionsRowParams.topMargin = dp(8);
        inputCard.addView(optionsRow, optionsRowParams);
        clipCountButton = button(selectedClips + " CORTES", false);
        aspectRatioButton = button("FORMATO " + selectedAspectRatio, false);
        optionsRow.addView(clipCountButton, new LinearLayout.LayoutParams(0, -1, 1));
        LinearLayout.LayoutParams ratioParams = new LinearLayout.LayoutParams(0, -1, 1);
        ratioParams.leftMargin = dp(8);
        optionsRow.addView(aspectRatioButton, ratioParams);
        clipCountButton.setOnClickListener(v -> chooseClipCount());
        aspectRatioButton.setOnClickListener(v -> chooseAspectRatio());
""", 1
)
source = source.replace('body.put("clips", 5);', 'body.put("clips", selectedClips);\n                body.put("aspect_ratio", selectedAspectRatio);', 1)
old_upload = 'out.writeBytes("Content-Disposition: form-data; name=\\"clips\\"\\r\\n\\r\\n5\\r\\n");'
new_upload = """out.writeBytes("Content-Disposition: form-data; name=\\"clips\\"\\r\\n\\r\\n" + selectedClips + "\\r\\n");
                out.writeBytes("--" + boundary + "\\r\\n");
                out.writeBytes("Content-Disposition: form-data; name=\\"aspect_ratio\\"\\r\\n\\r\\n" + selectedAspectRatio + "\\r\\n");"""
if old_upload not in source:
    raise SystemExit("Campo multipart clips não encontrado para adicionar formato.")
source = source.replace(old_upload, new_upload, 1)

source = source.replace(
    "    private void beginPolling(String jobId) {\n",
    "    private void beginPolling(String jobId) {\n        currentJobId = jobId;\n",
    1
)
source = source.replace("runOnUiThread(() -> showResults(job));", "runOnUiThread(() -> showResults(job, jobId));", 1)
source = source.replace("    private void showResults(JSONObject job) {", "    private void showResults(JSONObject job, String jobId) {", 1)
zip_anchor = "        resultsBox.addView(explanation, expParams);\n"
if zip_anchor not in source:
    raise SystemExit("Área de resultados não encontrada.")
source = source.replace(zip_anchor, zip_anchor + """
        Button downloadAll = button("BAIXAR TODOS OS CORTES (.ZIP)", true);
        LinearLayout.LayoutParams downloadAllParams = new LinearLayout.LayoutParams(-1, dp(48));
        downloadAllParams.topMargin = dp(12);
        resultsBox.addView(downloadAll, downloadAllParams);
        downloadAll.setOnClickListener(v -> downloadFile(
                apiBase() + "/api/jobs/" + jobId + "/download-all",
                "CortaViral_todos_os_cortes.zip"));
""", 1)

friendly_anchor = """            String detail = (message == null || message.trim().isEmpty())
                    ? "Erro de conexão. Confira a URL do servidor nas configurações ⚙."
                    : message;
"""
if friendly_anchor not in source:
    raise SystemExit("Trecho de mensagem de erro não encontrado.")
source = source.replace(friendly_anchor, friendly_anchor + """
            String lowerDetail = detail.toLowerCase(java.util.Locale.ROOT);
            boolean youtubeBotBlock = lowerDetail.contains("not a bot")
                    || (lowerDetail.contains("sign in to confirm") && lowerDetail.contains("youtube"))
                    || lowerDetail.contains("confirm you’re not");
            if (youtubeBotBlock) {
                detail = "O YouTube bloqueou a leitura automática deste link. O servidor está conectado, mas a plataforma não liberou o arquivo. Para continuar, toque em IMPORTAR VÍDEO DA GALERIA e selecione um vídeo que você tenha autorização para editar. Não informe senha nem cookies.";
            }
""", 1)

methods = """
    private void pasteLink() {
        try {
            ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (clipboard != null && clipboard.hasPrimaryClip() && clipboard.getPrimaryClip().getItemCount() > 0) {
                CharSequence value = clipboard.getPrimaryClip().getItemAt(0).coerceToText(this);
                if (value != null) {
                    urlInput.setText(value.toString().trim());
                    urlInput.setSelection(urlInput.length());
                    toast("Link colado.");
                    return;
                }
            }
            toast("A área de transferência está vazia.");
        } catch (Exception error) {
            toast("Não foi possível acessar a área de transferência.");
        }
    }

    private void chooseClipCount() {
        String[] labels = {"1 corte", "3 cortes", "5 cortes", "7 cortes", "10 cortes"};
        int[] values = {1, 3, 5, 7, 10};
        int selected = 2;
        for (int i = 0; i < values.length; i++) if (values[i] == selectedClips) selected = i;
        new AlertDialog.Builder(this).setTitle("Quantidade de cortes")
                .setSingleChoiceItems(labels, selected, (dialog, which) -> {
                    selectedClips = values[which];
                    preferences.edit().putInt("clip_count", selectedClips).apply();
                    clipCountButton.setText(selectedClips + " CORTES");
                    dialog.dismiss();
                }).setNegativeButton("CANCELAR", null).show();
    }

    private void chooseAspectRatio() {
        String[] labels = {"Vertical 9:16 (Reels / TikTok / Shorts)", "Quadrado 1:1", "Horizontal 16:9"};
        String[] values = {"9:16", "1:1", "16:9"};
        int selected = 0;
        for (int i = 0; i < values.length; i++) if (values[i].equals(selectedAspectRatio)) selected = i;
        new AlertDialog.Builder(this).setTitle("Formato dos cortes")
                .setSingleChoiceItems(labels, selected, (dialog, which) -> {
                    selectedAspectRatio = values[which];
                    preferences.edit().putString("aspect_ratio", selectedAspectRatio).apply();
                    aspectRatioButton.setText("FORMATO " + selectedAspectRatio);
                    dialog.dismiss();
                }).setNegativeButton("CANCELAR", null).show();
    }

"""
hide_anchor = "    private void hideKeyboard() {\n"
if hide_anchor not in source:
    raise SystemExit("Ponto de inserção dos novos métodos não encontrado.")
source = source.replace(hide_anchor, methods + hide_anchor, 1)
cover_asset = Path("android/app/src/main/res/drawable-nodpi/cover_photo.jpg")
if cover_asset.exists():
    cover_asset.unlink()

# The active job identifier is used by the new download-all ZIP action.
source = source.replace(
    "    private Button aspectRatioButton;\n",
    "    private Button aspectRatioButton;\n    private String currentJobId = \"\";\n",
    1
)

# v1.7: keep analysis history in a private SQLite database on the Android phone.
source = source.replace(
    '    private String currentJobId = "";\n',
    '''    private String currentJobId = "";
    private LocalHistoryDb localHistoryDb;
    private LinearLayout historyBox;
    private String currentSourceLabel = "Vídeo";
''',
    1
)
source = source.replace(
    "        preferences = getSharedPreferences(PREFS, MODE_PRIVATE);\n",
    "        preferences = getSharedPreferences(PREFS, MODE_PRIVATE);\n        localHistoryDb = new LocalHistoryDb(this);\n",
    1
)
source = source.replace(
    "        page.addView(resultsBox, resultsParams);\n",
    """        page.addView(resultsBox, resultsParams);

        historyBox = new LinearLayout(this);
        historyBox.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams historyParams = new LinearLayout.LayoutParams(-1, -2);
        historyParams.topMargin = dp(18);
        page.addView(historyBox, historyParams);
        renderLocalHistory();
""",
    1
)
source = source.replace(
    '        String url = urlInput.getText().toString().trim();\n',
    '        String url = urlInput.getText().toString().trim();\n        currentSourceLabel = url;\n',
    1
)
source = source.replace(
    '                String filename = displayName(uri);\n',
    '                String filename = displayName(uri);\n                currentSourceLabel = filename;\n',
    1
)
source = source.replace(
    "    private void showResults(JSONObject job, String jobId) {\n",
    "    private void showResults(JSONObject job, String jobId) {\n        saveAnalysisOnPhone(jobId, job);\n",
    1
)
source = source.replace(
    "    private void hideKeyboard() {\n",
    """    private void saveAnalysisOnPhone(String jobId, JSONObject job) {
        try {
            JSONArray items = job.optJSONArray("results");
            int count = items == null ? 0 : items.length();
            localHistoryDb.save(
                    jobId,
                    currentSourceLabel == null ? "Vídeo" : currentSourceLabel,
                    count,
                    job.optString("score_note", ""),
                    items == null ? "[]" : items.toString()
            );
            renderLocalHistory();
        } catch (Exception error) {
            toast("A análise foi concluída, mas não foi possível salvar o histórico no celular.");
        }
    }

    private void renderLocalHistory() {
        if (historyBox == null || localHistoryDb == null) return;
        historyBox.removeAllViews();
        TextView heading = text("HISTÓRICO SALVO NESTE CELULAR", 13, WHITE, true);
        historyBox.addView(heading);
        TextView subtitle = text("Suas análises ficam no aparelho, sem banco de dados externo.", 10, MUTED, false);
        LinearLayout.LayoutParams subtitleParams = new LinearLayout.LayoutParams(-1, -2);
        subtitleParams.topMargin = dp(4);
        historyBox.addView(subtitle, subtitleParams);

        Cursor cursor = localHistoryDb.getRecent();
        if (cursor == null) return;
        try {
            if (cursor.getCount() == 0) {
                TextView empty = text("Nenhuma análise salva ainda. Quando um vídeo for processado, ele aparecerá aqui.", 11, MUTED, false);
                LinearLayout.LayoutParams emptyParams = new LinearLayout.LayoutParams(-1, -2);
                emptyParams.topMargin = dp(10);
                historyBox.addView(empty, emptyParams);
                return;
            }
            Button clearButton = button("LIMPAR HISTÓRICO", false);
            LinearLayout.LayoutParams clearParams = new LinearLayout.LayoutParams(-1, dp(42));
            clearParams.topMargin = dp(10);
            historyBox.addView(clearButton, clearParams);
            clearButton.setOnClickListener(v -> new AlertDialog.Builder(this)
                    .setTitle("Apagar histórico deste celular?")
                    .setMessage("Isso apaga apenas os registros locais do CortaViral AI. Os vídeos já baixados na pasta Downloads não serão apagados.")
                    .setNegativeButton("CANCELAR", null)
                    .setPositiveButton("APAGAR", (dialog, which) -> {
                        localHistoryDb.clear();
                        renderLocalHistory();
                        toast("Histórico local apagado.");
                    }).show());

            while (cursor.moveToNext()) {
                String title = cursor.getString(cursor.getColumnIndexOrThrow("title"));
                long createdAt = cursor.getLong(cursor.getColumnIndexOrThrow("created_at"));
                int count = cursor.getInt(cursor.getColumnIndexOrThrow("result_count"));
                String date = new java.text.SimpleDateFormat(
                        "dd/MM/yyyy 'às' HH:mm", java.util.Locale.getDefault()
                ).format(new java.util.Date(createdAt));
                LinearLayout item = card();
                LinearLayout.LayoutParams itemParams = new LinearLayout.LayoutParams(-1, -2);
                itemParams.topMargin = dp(9);
                historyBox.addView(item, itemParams);
                TextView itemTitle = text(title == null || title.trim().isEmpty() ? "Vídeo analisado" : title, 12, WHITE, true);
                item.addView(itemTitle);
                TextView metadata = text(count + " corte(s)  •  " + date, 10, MUTED, false);
                LinearLayout.LayoutParams metadataParams = new LinearLayout.LayoutParams(-1, -2);
                metadataParams.topMargin = dp(5);
                item.addView(metadata, metadataParams);
            }
        } finally {
            cursor.close();
        }
    }

    private void hideKeyboard() {
""",
    1
)

# Generate the SQLite helper as part of every Android build.
Path("android/app/src/main/java/com/cortaviral/ai/LocalHistoryDb.java").write_text("""package com.cortaviral.ai;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

public final class LocalHistoryDb extends SQLiteOpenHelper {
    private static final String DB_NAME = "cortaviral_phone.db";
    private static final int DB_VERSION = 1;
    private static final String TABLE = "analysis_history";

    public LocalHistoryDb(Context context) {
        super(context, DB_NAME, null, DB_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE " + TABLE + " (" +
                "job_id TEXT PRIMARY KEY NOT NULL, " +
                "title TEXT NOT NULL, " +
                "created_at INTEGER NOT NULL, " +
                "result_count INTEGER NOT NULL, " +
                "score_note TEXT, " +
                "results_json TEXT NOT NULL)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        // Preserve local history when the schema is extended in a later release.
    }

    public void save(String jobId, String title, int resultCount, String scoreNote, String resultsJson) {
        if (jobId == null || jobId.trim().isEmpty()) return;
        ContentValues values = new ContentValues();
        values.put("job_id", jobId);
        values.put("title", title == null ? "Vídeo" : title);
        values.put("created_at", System.currentTimeMillis());
        values.put("result_count", resultCount);
        values.put("score_note", scoreNote == null ? "" : scoreNote);
        values.put("results_json", resultsJson == null ? "[]" : resultsJson);
        getWritableDatabase().insertWithOnConflict(TABLE, null, values, SQLiteDatabase.CONFLICT_REPLACE);
    }

    public Cursor getRecent() {
        return getReadableDatabase().query(
                TABLE,
                new String[]{"job_id", "title", "created_at", "result_count", "score_note", "results_json"},
                null, null, null, null, "created_at DESC", "50"
        );
    }

    public void clear() {
        getWritableDatabase().delete(TABLE, null, null);
    }
}
""", encoding="utf-8")

path.write_text(source, encoding="utf-8")
print("Android: interface preservada; polling limitado, timeout e erro detalhado aplicados.")
