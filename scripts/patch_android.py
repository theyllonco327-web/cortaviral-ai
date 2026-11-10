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

path.write_text(source, encoding="utf-8")
print("Android: chips de origem, layout refinado e validação do servidor aplicados.")
