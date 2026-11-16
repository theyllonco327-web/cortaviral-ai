package br.com.cortaviral.mobile;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Pattern;

final class Impact {
    private static final Pattern REACTION = Pattern.compile("\\b(nao acredito|meu deus|impossivel|inacreditavel|absurdo|caramba|que isso|conseguimos|sensacional|surreal)\\b");
    private static final Pattern EVENT = Pattern.compile("\\b(virada|gol|recorde|vitoria|revelacao|nocaute|conseguimos)\\b");
    private static final Pattern STRONG = Pattern.compile("\\b(golaco|virada historica|batemos o recorde|campea[oa]|vencemos a final|recorde mundial|gol da vitoria|ganhamos a final|ultima chance)\\b");

    static int score(String speech, double loudness, double baseline) {
        String text = Normalizer.normalize(speech.toLowerCase(Locale.ROOT), Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "");
        boolean emphatic = REACTION.matcher(text).find();
        boolean strong = STRONG.matcher(text).find();
        boolean event = EVENT.matcher(text).find();
        boolean high = loudness >= -24 && loudness - baseline >= 7;
        if (!strong && !event && !(emphatic && high)) return 0;
        return (strong ? 8 : event ? 4 : 0) + (emphatic ? 3 : 0) + (high ? 3 : 0);
    }

    static double levels(short[] data, int n) {
        double sum = 0;
        for (int i=0;i<n;i++) { double x=data[i]/32768.0; sum+=x*x; }
        return 10 * Math.log10(Math.max(0.000000001,sum/Math.max(1,n)));
    }

    static final class Gate {
        final int threshold;
        long last = -90_000;
        Gate(int threshold) { this.threshold=threshold; }
        boolean accept(int score, long ms) {
            if (score < threshold || ms-last < 35_000) return false;
            last=ms;
            return true;
        }
    }
}
