package br.com.cortaviral.mobile;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.*;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;

public final class ClipActivity extends Activity {
    private static final int VIDEO = 91, SRT = 92;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private List<ClipPlan.Cue> cues = List.of();
    private VideoView player;
    private TextView caption, result;
    private EditText start, end;
    private Button preview;
    private int duration;
    private int stopAt = -1;
    private boolean follow;
    private final Runnable render = new Runnable() {
        @Override public void run() {
            if (follow) {
                int position = player.getCurrentPosition();
                if (position >= stopAt) { player.pause(); caption.setText(""); follow = false; }
                else caption.setText(ClipPlan.captionAt(cues, position));
            }
            handler.postDelayed(this, 120);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        ScrollView scroll = new ScrollView(this);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(20),dp(12),dp(20),dp(24));
        scroll.addView(page);
        scroll.setOnApplyWindowInsetsListener((v,insets)->{
            if(android.os.Build.VERSION.SDK_INT>=30){
                android.graphics.Insets safe=insets.getInsets(android.view.WindowInsets.Type.systemBars()|android.view.WindowInsets.Type.displayCutout());
                v.setPadding(safe.left,safe.top,safe.right,safe.bottom);
            }
            return insets;
        });
        setContentView(scroll);
        TextView heading = label(page,"Prévia de corte");
        heading.setTextSize(27);
        label(page,"Escolha um vídeo da galeria e informe o início e o fim em segundos. Uma legenda SRT ajuda a ajustar os limites para preservar as frases.");
        button(page,"Escolher vídeo", () -> pick(VIDEO, "video/*"));
        button(page,"Importar legenda SRT", () -> pick(SRT,"*/*"));
        start = timeField(page,"Início em segundos");
        end = timeField(page,"Fim em segundos");
        preview = button(page,"Reproduzir trecho", this::play);
        preview.setEnabled(false);
        result = label(page,"Nenhum vídeo selecionado.");
        player = new VideoView(this);
        page.addView(player,new LinearLayout.LayoutParams(-1,dp(224)));
        caption = label(page,"");
        caption.setTextSize(18);
        caption.setGravity(android.view.Gravity.CENTER);
        label(page,"A prévia roda no aparelho. Esta versão não exporta o vídeo nem gera legendas automaticamente.");
        player.setOnPreparedListener(mp -> {
            duration = mp.getDuration();
            start.setText("0");
            end.setText(seconds(Math.min(duration,30_000)));
            preview.setEnabled(duration > 0);
            result.setText("Vídeo pronto · " + seconds(duration) + " s");
            player.seekTo(1);
        });
        player.setOnCompletionListener(mp -> { follow=false; caption.setText(""); });
        player.setOnErrorListener((mp,what,extra)->{
            preview.setEnabled(false); follow=false;
            result.setText("O Android não conseguiu abrir este vídeo.");
            return true;
        });
    }

    private int dp(int n) { return Math.round(n * getResources().getDisplayMetrics().density); }
    private TextView label(LinearLayout page, String value) {
        TextView text=new TextView(this); text.setText(value); text.setTextSize(15);
        text.setPadding(0, dp(6), 0, dp(6)); page.addView(text); return text;
    }
    private Button button(LinearLayout page, String title, Runnable action) {
        Button b = new Button(this); b.setAllCaps(false); b.setText(title);
        b.setOnClickListener(v->action.run()); page.addView(b); return b;
    }
    private EditText timeField(LinearLayout page, String hint) {
        EditText input = new EditText(this); input.setHint(hint);
        input.setInputType(android.text.InputType.TYPE_CLASS_NUMBER|android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        TextView label=label(page,hint);
        input.setId(android.view.View.generateViewId()); label.setLabelFor(input.getId());
        page.addView(input); return input;
    }
    private void pick(int request, String mime) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType(mime).addCategory(Intent.CATEGORY_OPENABLE);
        startActivityForResult(intent, request);
    }
    @Override protected void onActivityResult(int request, int code, Intent data) {
        super.onActivityResult(request,code,data);
        if (code!=RESULT_OK || data==null || data.getData()==null) return;
        Uri uri=data.getData();
        if(request==VIDEO) {
            follow=false; duration=0; preview.setEnabled(false); cues=List.of(); caption.setText("");
            result.setText("Abrindo vídeo…"); player.setVideoURI(uri);
        } else if (request==SRT) {
            try (InputStream stream=getContentResolver().openInputStream(uri)) {
                if (stream==null) throw new java.io.IOException();
                java.io.ByteArrayOutputStream bytes=new java.io.ByteArrayOutputStream();
                byte[] chunk=new byte[8192];
                int n;
                while ((n=stream.read(chunk))!=-1) {
                    if (bytes.size()+n>1_048_576) throw new java.io.IOException();
                    bytes.write(chunk,0,n);
                }
                List<ClipPlan.Cue> parsed=ClipPlan.parse(new String(bytes.toByteArray(),StandardCharsets.UTF_8));
                if (parsed.isEmpty()) result.setText("Nenhuma legenda válida. Escolha um SRT em UTF-8.");
                else { cues=parsed; result.setText("Legenda carregada · "+cues.size()+" linhas"); }
            } catch (Exception e) { result.setText("Não foi possível abrir a legenda. Use um SRT de até 1 MB."); }
        }
    }

    private static String seconds(int ms) { return String.format(Locale.US,"%.3f",ms/1000.0); }
    private int readTime(EditText input) {
        double s=Double.parseDouble(input.getText().toString().trim().replace(',','.'));
        if (!Double.isFinite(s) || s<0 || s>duration/1000.0+0.001) throw new NumberFormatException();
        return (int)Math.round(s*1000);
    }
    private void play() {
        try {
            int a=readTime(start), b=readTime(end);
            if (a>=b) throw new NumberFormatException();
            ClipPlan.Range range=ClipPlan.adjust(a,b,duration,cues);
            stopAt=range.end();
            follow=true;
            player.pause(); player.seekTo(range.start()); player.start();
            result.setText("Trecho · "+seconds(range.start()).replace('.',',')+" a "
                   +seconds(range.end()).replace('.',',')+" s"
                   +(a==range.start() && b==range.end() ? "" : " · ajustado pela legenda"));
        } catch (NumberFormatException e) {
            result.setText("Informe início e fim válidos dentro da duração do vídeo.");
        }
    }
    @Override protected void onResume() { super.onResume(); handler.removeCallbacks(render); handler.post(render); }
    @Override protected void onPause() { handler.removeCallbacks(render); follow=false; player.pause(); super.onPause(); }
}
