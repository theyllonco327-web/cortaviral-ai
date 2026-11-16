package br.com.cortaviral.mobile;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.*;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.*;
import android.view.WindowManager;
import java.nio.ByteBuffer;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

public final class CaptureService extends Service {
    static final String CHANNEL="diagnostico";
    static final String STOP="br.com.cortaviral.mobile.STOP";
    static final String READY="br.com.cortaviral.mobile.READY";
    static final String UPDATE="br.com.cortaviral.mobile.UPDATE";
    static final String PREF="diagnostico";
    private static final int DURATION=20_000, WARMUP=4_000;
    private final Handler main=new Handler(Looper.getMainLooper());
    private HandlerThread worker;
    private MediaProjection projection;
    private VirtualDisplay display;
    private ImageReader images;
    private volatile AudioRecord record;
    private volatile long measureAt;
    private long frameAt;
    private String run="";
    static volatile boolean isRunning;
    private final AtomicBoolean active=new AtomicBoolean();
    private final AtomicReference<String> audioError=new AtomicReference<>();
    private final Signal signal=new Signal();

    @Override public IBinder onBind(Intent i){return null;}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent==null){stopSelf();return START_NOT_STICKY;}
        if(STOP.equals(intent.getAction())){finish("Teste interrompido.",false);return START_NOT_STICKY;}
        if(!active.compareAndSet(false,true))return START_NOT_STICKY;
        isRunning=true;
        run=intent.getStringExtra("run");
        try{
            notification();
            Intent data=Build.VERSION.SDK_INT>=33 ? intent.getParcelableExtra("projection",Intent.class) :
                    intent.getParcelableExtra("projection");
            if(data==null)throw new IllegalStateException("Autorização de captura não recebida.");
            projection=getSystemService(MediaProjectionManager.class).getMediaProjection(Activity.RESULT_OK,data);
            if(projection==null)throw new IllegalStateException("O Android não iniciou a projeção.");
            worker=new HandlerThread("cortaviral-imagem");worker.start();
            Handler io=new Handler(worker.getLooper());
            projection.registerCallback(new MediaProjection.Callback(){
                @Override public void onStop(){main.post(()->finish("Compartilhamento encerrado pelo Android.",false));}
            },io);
            setupFrames(io);
            int uid=intent.getIntExtra("uid",-1);
            int min=AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);
            if(min<=0) throw new IllegalStateException("O dispositivo não aceitou a configuração de áudio.");
            AudioPlaybackCaptureConfiguration.Builder ac=new AudioPlaybackCaptureConfiguration.Builder(projection)
                    .addMatchingUsage(AudioAttributes.USAGE_MEDIA).addMatchingUsage(AudioAttributes.USAGE_GAME)
                    .addMatchingUsage(AudioAttributes.USAGE_UNKNOWN);
            if(uid>=0)ac.addMatchingUid(uid);
            record=new AudioRecord.Builder().setAudioFormat(new AudioFormat.Builder().setSampleRate(16000)
                    .setChannelMask(AudioFormat.CHANNEL_IN_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
                    .setBufferSizeInBytes(Math.max(min*2,6400)).setAudioPlaybackCaptureConfig(ac.build()).build();
            if(record.getState()!=AudioRecord.STATE_INITIALIZED)throw new IllegalStateException("Não foi possível iniciar a captura de áudio interno.");
            measureAt=SystemClock.elapsedRealtime()+WARMUP;
            record.startRecording();
            store("running","Abra a live e deixe tocar com movimento e fala por cerca de 20 segundos.",null);
            new Thread(this::readAudio,"cortaviral-audio").start();
            sendBroadcast(new Intent(READY).setPackage(getPackageName()).putExtra("run",run));
            main.postDelayed(()->finish("Diagnóstico concluído.",true), DURATION+WARMUP);
        }catch(RuntimeException e){
            String msg=e.getMessage();
            finish("Falha ao iniciar a captura"+(msg==null?".":". "+msg),false);
        }
        return START_NOT_STICKY;
    }
    private void notification(){
        NotificationManager n=getSystemService(NotificationManager.class);
        n.createNotificationChannel(new NotificationChannel(CHANNEL,"Teste de áudio e imagem",NotificationManager.IMPORTANCE_LOW));
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,CaptureService.class).setAction(STOP),PendingIntent.FLAG_IMMUTABLE);
        Notification notice=new Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.ic_media_play)
                .setContentTitle("CortaViral · diagnóstico").setContentText("Verificando áudio interno e imagem. Nada é salvo.")
                .setContentIntent(open).setOngoing(true)
                .addAction(new Notification.Action.Builder(null,"Parar teste",stop).build()).build();
        if(Build.VERSION.SDK_INT>=29)startForeground(41,notice,ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
        else startForeground(41,notice);
    }
    private void setupFrames(Handler io){
        WindowManager wm=getSystemService(WindowManager.class);
        android.util.DisplayMetrics m=new android.util.DisplayMetrics();
        wm.getDefaultDisplay().getRealMetrics(m);
        double scale=640.0/Math.max(m.widthPixels,m.heightPixels);
        int w=Math.max(32,(int)(m.widthPixels*scale)),h=Math.max(32,(int)(m.heightPixels*scale));
        images=ImageReader.newInstance(w,h,PixelFormat.RGBA_8888,2);
        images.setOnImageAvailableListener(reader->{
            try(Image im=reader.acquireLatestImage()){
                long now=SystemClock.elapsedRealtime();
                if(!active.get()||im==null||measureAt==0||now<measureAt||now-frameAt<240)return;
                frameAt=now;
                Image.Plane plane=im.getPlanes()[0];
                ByteBuffer pixels=plane.getBuffer();
                int[] values=new int[Signal.PIXELS];
                // Measure a central region so system bars and status icons do not dominate.
                for(int y=0;y<Signal.GRID;y++)for(int x=0;x<Signal.GRID;x++){
                    int px=(int)(w*(.12+.76*(x+.5)/Signal.GRID));
                    int py=(int)(h*(.22+.56*(y+.5)/Signal.GRID));
                    int i=py*plane.getRowStride()+px*plane.getPixelStride();
                    if(i+2>=pixels.limit())continue;
                    values[y*Signal.GRID+x]=((pixels.get(i)&255)*3+(pixels.get(i+1)&255)*6+(pixels.get(i+2)&255))/10;
                }
                signal.image(values);
            }catch(IllegalStateException ignored){}
        },io);
        display=projection.createVirtualDisplay("CortaViral-compatibilidade",w,h,m.densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,images.getSurface(),null,io);
        if(display==null)throw new IllegalStateException("O Android não entregou a imagem da tela.");
    }
    private void readAudio(){
        short[] block=new short[1600];
        try{
            AudioRecord r=record;
            if(r==null)return;
            while(active.get()){
                int count=r.read(block,0,block.length,AudioRecord.READ_BLOCKING);
                if(count<0){
                    if(active.get())audioError.set("O Android interrompeu a leitura de áudio interno.");
                    break;
                }
                if(SystemClock.elapsedRealtime()>=measureAt)signal.audio(block,count);
            }
        }catch(RuntimeException e){if(active.get())audioError.set("O Android interrompeu a leitura de áudio interno.");}
    }
    private void store(String state,String msg,Signal.Result stats){
        SharedPreferences.Editor edit=getSharedPreferences(PREF,MODE_PRIVATE).edit()
                .putString("run",run).putString("state",state).putString("message",msg);
        if(stats!=null){
            edit.putBoolean("audio",stats.audio()).putBoolean("image",stats.image())
                    .putBoolean("light",stats.light()).putInt("peak",stats.peakDb())
                    .putInt("frames",stats.visualFrames()).putInt("changes",stats.changes());
        }
        edit.apply();
        sendBroadcast(new Intent(UPDATE).setPackage(getPackageName()).putExtra("run",run));
    }
    private void finish(String text,boolean completed){
        if(!active.compareAndSet(true,false))return;
        main.removeCallbacksAndMessages(null);
        isRunning=false;
        Signal.Result result=signal.result();
        if(completed && audioError.get()!=null)text=audioError.get();
        store(completed?"done":"error",text,result);
        release();
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
    }
    private void release(){
        if(record!=null){
            try{record.stop();}catch(RuntimeException ignored){}
            record.release();record=null;
        }
        if(display!=null){display.release();display=null;}
        if(images!=null){images.close();images=null;}
        if(projection!=null){projection.stop();projection=null;}
        if(worker!=null){worker.quitSafely();worker=null;}
    }
    @Override public void onDestroy(){
        isRunning=false;
        if(active.getAndSet(false)){main.removeCallbacksAndMessages(null);release();}
        super.onDestroy();
    }
}
