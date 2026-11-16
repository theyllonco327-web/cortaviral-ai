package br.com.cortaviral.mobile;

import android.content.Context;
import java.io.*;
import java.net.URL;
import java.nio.file.*;
import java.util.zip.*;

final class SpeechModel {
    static final String NAME="vosk-model-small-pt-0.3";
    private static final String URL_PATH="https://alphacephei.com/vosk/models/"+NAME+".zip";
    static File folder(Context c) { return new File(c.getFilesDir(),NAME); }
    static boolean ready(Context c) { return new File(folder(c),"am/final.mdl").isFile()
            && new File(folder(c),"conf/model.conf").isFile() && new File(folder(c),".ready").isFile(); }
    interface Progress { void update(String text); }

    static synchronized void download(Context c, Progress progress) throws IOException {
        if (ready(c)) return;
        File stage=new File(c.getCacheDir(),"speech-"+System.nanoTime());
        if (!stage.mkdirs()) throw new IOException("Falha ao abrir pasta temporária.");
        try {
            java.net.URLConnection con=new URL(URL_PATH).openConnection();
            con.setConnectTimeout(20000); con.setReadTimeout(30000);
            long total=0, last=-1;
            try (ZipInputStream in=new ZipInputStream(new BufferedInputStream(con.getInputStream()))) {
                ZipEntry e; byte[] buf=new byte[65536];
                while ((e=in.getNextEntry())!=null) {
                    if (!e.getName().startsWith(NAME+"/")) continue;
                    File dst=new File(stage,e.getName());
                    if (!dst.getCanonicalPath().startsWith(stage.getCanonicalPath()+File.separator)) throw new IOException("Arquivo inválido.");
                    if (e.isDirectory()) {dst.mkdirs(); continue;}
                    dst.getParentFile().mkdirs();
                    try (OutputStream out=new BufferedOutputStream(new FileOutputStream(dst))) {
                        int n;
                        while ((n=in.read(buf))!=-1) {
                            total+=n;
                            if (total>300L*1024*1024) throw new IOException("O modelo excedeu o tamanho esperado.");
                            out.write(buf,0,n);
                            if (total/(8*1024*1024)!=last) {
                                last=total/(8*1024*1024);
                                progress.update("Preparando modelo · "+total/(1024*1024)+" MB extraídos");
                            }
                        }
                    }
                }
            }
            File source=new File(stage,NAME);
            if (!new File(source,"am/final.mdl").isFile() || !new File(source,"conf/model.conf").isFile())
                throw new IOException("O modelo recebido está incompleto.");
            Files.write(new File(source,".ready").toPath(),new byte[]{1});
            clear(folder(c));
            Files.move(source.toPath(),folder(c).toPath());
        } finally {clear(stage);}
    }

    static void clear(File file) {
        File[] list=file.listFiles();
        if(list!=null) for(File f:list) clear(f);
        file.delete();
    }
}
