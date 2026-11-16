package br.com.cortaviral.mobile;

final class Signal {
    static final int GRID=16, PIXELS=GRID*GRID;
    private int[] prior;
    private int visualFrames, videoChanges, audioChunks;
    private double peak=-90;
    synchronized void audio(short[] pcm, int len) {
        if (len <= 0) return;
        double db=Impact.levels(pcm,len);
        peak=Math.max(peak,db);
        if(db>=-53) audioChunks++;
    }
    synchronized void image(int[] values) {
        int lit=0,changed=0;
        for(int i=0;i<PIXELS;i++) {
            if(values[i]>=32) lit++;
            if(prior!=null && Math.abs(values[i]-prior[i])>=19) changed++;
        }
        if(lit>=PIXELS/5) visualFrames++;
        if(changed>=PIXELS/12) videoChanges++;
        prior=values;
    }
    synchronized Result result() {
        return new Result(audioChunks>=3,visualFrames>=3 && videoChanges>=2,visualFrames>0,
                audioChunks,visualFrames,videoChanges,(int)Math.round(peak));
    }
    record Result(boolean audio,boolean image,boolean light,int audioChunks,int visualFrames,int changes,int peakDb) {
        boolean passed(){return audio && image;}
    }
}
