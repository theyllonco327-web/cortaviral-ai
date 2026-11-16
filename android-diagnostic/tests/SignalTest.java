package br.com.cortaviral.mobile;
import java.util.Arrays;
class SignalTest {
    public static void main(String[] args) {
        var youtube=LiveLink.parse("https://www.youtube.com/live/abcdefghijk?feature=shared");
        assert youtube.platform().equals("YouTube");
        assert youtube.url().endsWith("/abcdefghijk");
        var tiktok=LiveLink.parse("https://vt.tiktok.com/exampleShareCode/");
        assert tiktok.platform().equals("TikTok");
        try{LiveLink.parse("https://youtube.com.invalid.test/live/abcdefghijk");throw new AssertionError();}
        catch(IllegalArgumentException expected){}
        Signal sample=new Signal();
        short[] pcm=new short[1600];
        int[] black=new int[Signal.PIXELS], bright=new int[Signal.PIXELS], mid=new int[Signal.PIXELS];
        for(int i=0;i<3;i++){sample.audio(pcm,pcm.length);sample.image(black);}
        assert !sample.result().audio() && !sample.result().image();
        Arrays.fill(pcm,(short)5000); Arrays.fill(bright,120);Arrays.fill(mid,60);
        for(int i=0;i<3;i++){sample.audio(pcm,pcm.length);sample.image(bright);}
        assert sample.result().audio() && !sample.result().image();
        sample.image(mid); sample.image(bright);
        assert sample.result().passed();
        System.out.println("URLs das duas plataformas aceitas e distinção entre áudio, imagem estática e movimento verificada.");
    }
}
