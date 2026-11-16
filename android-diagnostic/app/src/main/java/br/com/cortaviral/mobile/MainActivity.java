package br.com.cortaviral.mobile;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.projection.MediaProjectionConfig;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.util.UUID;

public final class MainActivity extends Activity {
    private static final int MIC=60, PROJECTION=61;
    private static final int BG=0xff15161c, PANEL=0xff22242e, WHITE=0xfff3f4f5, MUTED=0xffb6b9c7, GREEN=0xffd0fc68;
    private EditText link;
    private TextView status;
    private Button start,stop;
    private String run="";
    private LiveLink.Source source;
    private final BroadcastReceiver monitor=new BroadcastReceiver(){
        @Override public void onReceive(Context c, Intent i){
            String id=i.getStringExtra("run");
            if(CaptureService.READY.equals(i.getAction()) && source!=null && run.equals(id)){open();return;}
            update();
        }
    };

    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(BG);
        LinearLayout page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);
        int margin=dp(21);
        page.setPadding(margin,dp(24),margin,dp(24));scroll.addView(page);
        scroll.setOnApplyWindowInsetsListener((v,insets)->{
            if(Build.VERSION.SDK_INT>=30){
                android.graphics.Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
                v.setPadding(safe.left,safe.top,safe.right,safe.bottom);
            }
            return insets;
        });
        setContentView(scroll);
        title(page,"CORTAVIRAL AI  •  ANDROID",13,GREEN,true);
        title(page,"Sua live funciona no CortaViral?",34,WHITE,true);
        title(page,"Teste se o Android recebe áudio e imagem de uma live do YouTube ou TikTok.",15,MUTED,false);
        LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);card.setPadding(dp(16),dp(11),dp(16),dp(14));
        GradientDrawable panel=new GradientDrawable();panel.setColor(PANEL);panel.setCornerRadius(dp(16));card.setBackground(panel);
        LinearLayout.LayoutParams box=new LinearLayout.LayoutParams(-1,-2);box.setMargins(0,dp(22),0,dp(10));page.addView(card,box);
        TextView label=title(card,"Link público da live",15,WHITE,true);
        link=new EditText(this);link.setId(View.generateViewId());label.setLabelFor(link.getId());
        link.setTextColor(WHITE);link.setHintTextColor(MUTED);link.setHint("https://…");
        link.setSingleLine(true);link.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_URI);
        link.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);card.addView(link,new LinearLayout.LayoutParams(-1,dp(54)));
        start=new Button(this);start.setText("Testar áudio e imagem");start.setAllCaps(false);start.setTextColor(BG);
        start.setBackgroundTintList(android.content.res.ColorStateList.valueOf(GREEN));card.addView(start,new LinearLayout.LayoutParams(-1,dp(48)));
        start.setOnClickListener(v->begin());
        stop=new Button(this);stop.setText("Parar teste");stop.setAllCaps(false);card.addView(stop,new LinearLayout.LayoutParams(-1,dp(46)));
        stop.setOnClickListener(v->startService(new Intent(this,CaptureService.class).setAction(CaptureService.STOP)));
        status=title(card,"Nenhum teste realizado.",15,WHITE,false);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        title(page,"Abra o resultado depois de deixar a live tocar por cerca de 20 segundos. Use um trecho com fala e movimento. O teste de live não grava arquivos.",14,MUTED,false);
        Button studio=new Button(this);studio.setAllCaps(false);studio.setText("Abrir prévia de corte");
        page.addView(studio,new LinearLayout.LayoutParams(-1,-2));
        studio.setOnClickListener(v->startActivity(new Intent(this,ClipActivity.class)));
        if(state!=null){
            run=state.getString("run","");
            String old=state.getString("source");
            if(old!=null){
                link.setText(old);
                try{source=LiveLink.parse(old);}catch(IllegalArgumentException ignored){}
            }
        }
        IntentFilter events=new IntentFilter(CaptureService.READY);events.addAction(CaptureService.UPDATE);
        if (Build.VERSION.SDK_INT>=33)registerReceiver(monitor,events,Context.RECEIVER_NOT_EXPORTED);
        else registerReceiver(monitor,events);
        update();
    }
    private TextView title(LinearLayout group,String value,int sp,int color,boolean bold){
        TextView t=new TextView(this);t.setText(value);t.setTextSize(sp);t.setTextColor(color);
        if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        t.setPadding(0,dp(9),0,dp(6));group.addView(t);return t;
    }
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private void begin(){
        try{source=LiveLink.parse(link.getText().toString());}
        catch(IllegalArgumentException e){link.setError(e.getMessage());return;}
        new AlertDialog.Builder(this)
                .setTitle("Diagnóstico da live")
                .setMessage("O Android pedirá para compartilhar a tela inteira e permitir a leitura do áudio interno. Durante o teste, mantenha só a live em reprodução. O CortaViral mede o sinal e descarta as amostras.")
                .setNegativeButton("Cancelar",null).setPositiveButton("Continuar",(d,b)->audioPermission()).show();
    }
    private void audioPermission(){
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},MIC);
        else authorize();
    }
    private void authorize(){
        MediaProjectionManager p=getSystemService(MediaProjectionManager.class);
        Intent consent=Build.VERSION.SDK_INT>=34 ?
                p.createScreenCaptureIntent(MediaProjectionConfig.createConfigForDefaultDisplay()) : p.createScreenCaptureIntent();
        startActivityForResult(consent,PROJECTION);
    }
    @Override public void onRequestPermissionsResult(int request,String[] perms,int[] values){
        super.onRequestPermissionsResult(request,perms,values);
        if(request==MIC && values.length>0 && values[0]==PackageManager.PERMISSION_GRANTED)authorize();
        else if(request==MIC)status.setText("Sem permissão para ler o áudio interno.");
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request!=PROJECTION)return;
        if(result!=RESULT_OK || data==null || source==null){status.setText("Captura não autorizada.");return;}
        run=UUID.randomUUID().toString();
        Intent service=new Intent(this,CaptureService.class).putExtra("projection",data).putExtra("run",run);
        try{
            int uid=getPackageManager().getApplicationInfo(source.packageName(),0).uid;
            if(getPackageManager().resolveActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(source.url())).setPackage(source.packageName()),0)!=null)
                service.putExtra("uid",uid);
        }catch(PackageManager.NameNotFoundException ignored){}
        start.setEnabled(false);
        status.setText("Iniciando a captura…");
        try{startForegroundService(service);}
        catch(RuntimeException e){start.setEnabled(true);status.setText("O Android não iniciou o serviço de captura.");}
    }
    private void open(){
        Intent launch=new Intent(Intent.ACTION_VIEW,Uri.parse(source.url()));
        Intent preferred=new Intent(launch).setPackage(source.packageName());
        try{startActivity(preferred);}
        catch(ActivityNotFoundException e){
            try{startActivity(launch);}
            catch(ActivityNotFoundException ex){startService(new Intent(this,CaptureService.class).setAction(CaptureService.STOP));}
        }
    }
    private void update(){
        SharedPreferences p=getSharedPreferences(CaptureService.PREF,MODE_PRIVATE);
        String mode=p.getString("state","");
        boolean active="running".equals(mode)&&CaptureService.isRunning;
        stop.setVisibility(active?View.VISIBLE:View.GONE);
        start.setEnabled(!active);
        if(active){status.setText(p.getString("message","Teste em andamento."));return;}
        if("done".equals(mode)){
            String audio=p.getBoolean("audio",false)?"Áudio interno detectado":"Áudio interno não detectado";
            String image=p.getBoolean("image",false)?"Imagem em movimento detectada":
                    p.getBoolean("light",false)?"Imagem visível, movimento inconclusivo":"Imagem útil não detectada";
            status.setText(p.getString("message","Diagnóstico concluído.")+"\n\n"+audio+"\n"+image+
                    "\n\nSe foi um trecho escuro, silencioso ou o link não abriu, repita em outro momento. Movimento da interface também pode contar como imagem.");
        }else if("error".equals(mode))status.setText(p.getString("message","Não foi possível concluir."));
        else if("running".equals(mode))status.setText("O Android encerrou a sessão antes de concluir o teste.");
    }
    @Override protected void onResume(){super.onResume();update();}
    @Override protected void onSaveInstanceState(Bundle b){
        super.onSaveInstanceState(b);b.putString("run",run);
        if(source!=null)b.putString("source",source.url());
    }
    @Override protected void onDestroy(){unregisterReceiver(monitor);super.onDestroy();}
}
