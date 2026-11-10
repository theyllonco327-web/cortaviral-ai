from pathlib import Path

path = Path("android/app/src/main/java/com/cortaviral/ai/MainActivity.java")
source = path.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global source
    if old not in source:
        raise SystemExit("Não foi possível aplicar ajuste Android: " + label)
    source = source.replace(old, new, 1)

replace_once(
    'TextView eyebrow = text("EDIÇÃO INTELIGENTE • 9:16", 10, NEON, true);',
    'TextView eyebrow = text("EDITOR INTELIGENTE  •  YOUTUBE  •  TIKTOK  •  GALERIA", 9, NEON, true);',
    "fontes no cabeçalho"
)
replace_once(
    'TextView title = text("Seus melhores\\nmomentos começam aqui.", 30, WHITE, true);',
    'TextView title = text("Transforme vídeos\\nem cortes incríveis.", 29, WHITE, true);',
    "título"
)
replace_once(
    'TextView subtitle = text("Cole um link ou escolha um vídeo do celular. A IA encontra os trechos e prepara seus cortes.", 14, MUTED, false);',
    'TextView subtitle = text("Use links do YouTube, TikTok e outras fontes compatíveis, ou importe um vídeo da galeria do celular.", 14, MUTED, false);',
    "descrição"
)
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
    'inputCard.addView(sectionTitle("ANALISAR POR URL"));',
    '''inputCard.addView(sectionTitle("ANALISAR POR LINK"));
        TextView supportedSources = text("YOUTUBE  •  TIKTOK  •  OUTRAS URLS COMPATÍVEIS", 9, MUTED, true);
        LinearLayout.LayoutParams sourceParams = new LinearLayout.LayoutParams(-1, -2);
        sourceParams.topMargin = dp(5);
        inputCard.addView(supportedSources, sourceParams);''',
    "rótulo de fontes"
)
replace_once(
    'urlInput.setHint("Cole o link público do vídeo aqui");',
    'urlInput.setHint("Cole o link do YouTube, TikTok ou vídeo...");',
    "campo de URL"
)
replace_once(
    'galleryButton = button("▣  ESCOLHER DA GALERIA", false);',
    'galleryButton = button("▣  IMPORTAR VÍDEO DA GALERIA", false);',
    "botão da galeria"
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

dialog_start = source.index("    private void showServerDialog() {")
dialog_end = source.index("\n    private boolean requireServer()", dialog_start)
new_dialog = '''    private void showServerDialog() {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setTextColor(WHITE);
        input.setHintTextColor(MUTED);
        input.setHint("https://seu-servico.onrender.com");
        input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        input.setText(apiBase());
        input.setPadding(dp(13), dp(10), dp(13), dp(10));
        input.setBackground(shape(BLACK, NEON, 12));

        LinearLayout wrapper = new LinearLayout(this);
        wrapper.setOrientation(LinearLayout.VERTICAL);
        wrapper.setPadding(dp(20), dp(8), dp(20), dp(8));
        TextView helper = text("Este campo é somente para o SERVIDOR Render. Links de YouTube e TikTok devem ser colados na tela principal.", 12, MUTED, false);
        wrapper.addView(helper);
        LinearLayout.LayoutParams inputParams = new LinearLayout.LayoutParams(-1, dp(54));
        inputParams.topMargin = dp(12);
        wrapper.addView(input, inputParams);
        TextView status = text("A conexão será testada antes de salvar.", 10, NEON, false);
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(-1, -2);
        statusParams.topMargin = dp(9);
        wrapper.addView(status, statusParams);

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Conectar ao servidor")
                .setMessage("Informe a URL base HTTPS do serviço CortaViral AI hospedado no Render.")
                .setView(wrapper)
                .setPositiveButton("TESTAR E SALVAR", null)
                .setNegativeButton("CANCELAR", (d, w) -> d.dismiss())
                .create();
        dialog.setOnShowListener(d -> {
            if (dialog.getWindow() != null) {
                dialog.getWindow().setBackgroundDrawable(shape(PANEL, 0xFF28663C, 18));
            }
            int titleId = getResources().getIdentifier("alertTitle", "id", "android");
            TextView title = dialog.findViewById(titleId);
            if (title != null) title.setTextColor(WHITE);
            TextView message = dialog.findViewById(android.R.id.message);
            if (message != null) message.setTextColor(MUTED);
            Button positive = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
            Button negative = dialog.getButton(AlertDialog.BUTTON_NEGATIVE);
            positive.setTextColor(NEON);
            negative.setTextColor(MUTED);
            positive.setOnClickListener(v -> {
                String value = input.getText().toString().trim().replaceAll("/+$", "");
                Uri parsed = Uri.parse(value);
                String host = parsed.getHost();
                if (!value.startsWith("https://") || host == null || host.trim().isEmpty()) {
                    input.setError("Informe a URL HTTPS base do servidor Render.");
                    return;
                }
                if (isVideoPlatformHost(host)) {
                    input.setError("Este é um link de vídeo, não o endereço do servidor.");
                    status.setText("Cole aqui a URL do Render. O link do vídeo vai na tela principal.");
                    status.setTextColor(0xFFFF9999);
                    return;
                }
                if (parsed.getPath() != null && !parsed.getPath().isEmpty() && !"/".equals(parsed.getPath())) {
                    input.setError("Use somente o domínio base, sem /dashboard ou /api.");
                    return;
                }
                positive.setEnabled(false);
                status.setText("Testando conexão com o CortaViral AI…");
                status.setTextColor(NEON);
                executor.execute(() -> {
                    try {
                        JSONObject health = requestJson("GET", value + "/api/health", null);
                        if (!health.optBoolean("ok", false)
                                || !"CortaViral AI".equalsIgnoreCase(health.optString("app", ""))) {
                            throw new IllegalStateException("Esse endereço não respondeu como servidor do CortaViral AI.");
                        }
                        preferences.edit().putString(SERVER_KEY, value).apply();
                        runOnUiThread(() -> {
                            dialog.dismiss();
                            toast("Servidor conectado e validado.");
                        });
                    } catch (Exception error) {
                        runOnUiThread(() -> {
                            positive.setEnabled(true);
                            String detail = error.getMessage() == null ? "Não foi possível validar o servidor." : error.getMessage();
                            status.setText(detail);
                            status.setTextColor(0xFFFF9999);
                            input.setError("Servidor inválido ou indisponível.");
                        });
                    }
                });
            });
        });
        dialog.show();
    }

    private boolean isVideoPlatformHost(String host) {
        String value = host.toLowerCase(java.util.Locale.ROOT);
        return value.equals("youtube.com") || value.endsWith(".youtube.com")
                || value.equals("youtu.be") || value.equals("tiktok.com")
                || value.endsWith(".tiktok.com") || value.equals("vm.tiktok.com")
                || value.equals("vt.tiktok.com");
    }
'''
source = source[:dialog_start] + new_dialog + source[dialog_end:]
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
    "validação do servidor"
)
replace_once(
    'urlInput.setError("Cole uma URL válida de vídeo.");',
    'urlInput.setError("Cole um link público do YouTube, TikTok ou outra fonte compatível.");',
    "mensagem de URL"
)
replace_once(
    '''                String filename = displayName(uri);
                String mime = getContentResolver().getType(uri);
                if (mime == null || !mime.startsWith("video/")) mime = "video/mp4";''',
    '''                String filename = displayName(uri);
                String mime = getContentResolver().getType(uri);
                if (mime == null || !mime.startsWith("video/")) mime = "video/mp4";
                if (!filename.contains(".")) {
                    if (mime.equalsIgnoreCase("video/quicktime")) filename += ".mov";
                    else if (mime.equalsIgnoreCase("video/webm")) filename += ".webm";
                    else if (mime.equalsIgnoreCase("video/3gpp")) filename += ".3gp";
                    else filename += ".mp4";
                }''',
    "extensão de arquivo da galeria"
)

path.write_text(source, encoding="utf-8")
print("Android UI and server validation updated")
