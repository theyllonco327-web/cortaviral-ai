package br.com.cortaviral.mobile;
public final class ClipPlanTest {
    public static void main(String[] args) {
        var cues=ClipPlan.parse("1\r\n00:00:02,000 --> 00:00:04,000\r\nEu acho que\r\n\r\n2\n00:00:04,100 --> 00:00:06,000\nconseguimos!\n\n3\n00:00:06,100 --> 00:00:09,000\nAgora espera.");
        assert cues.size()==3;
        assert ClipPlan.adjust(3200,4800,10000,cues).equals(new ClipPlan.Range(2000,6000));
        assert ClipPlan.adjust(7000,8000,8500,cues).equals(new ClipPlan.Range(6100,8500));
        assert ClipPlan.adjust(0,2000,10000,cues).equals(new ClipPlan.Range(0,2000));
        assert ClipPlan.captionAt(cues,4200).equals("conseguimos!");
        assert ClipPlan.captionAt(cues,4000).isEmpty();
        assert ClipPlan.parse("not a caption").isEmpty();
        System.out.println("Legenda SRT e ajuste dos limites da prévia verificados.");
    }
}
