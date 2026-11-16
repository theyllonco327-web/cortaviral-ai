package br.com.cortaviral.mobile;
class ImpactTest {
    public static void main(String[] args) {
        assert Impact.score("Vamos seguir.",-7,-29)==0;
        assert Impact.score("O gol anterior.",-18,-20)<8;
        assert Impact.score("Meu Deus! Ganhamos a final!",-15,-30)>=10;
        assert Impact.score("Foi o gol da vitória.",-22,-22)==8;
        var gate=new Impact.Gate(8);
        assert !gate.accept(4,0);
        assert gate.accept(9,12000);
        assert !gate.accept(11,28000);
        assert gate.accept(10,48000);
        assert Impact.levels(new short[20],20)<-60;
        System.out.println("Filtro Android: frases comuns ignoradas, destaque aceito e repetição bloqueada.");
    }
}
