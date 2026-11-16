package br.com.cortaviral.mobile;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class ClipPlan {
    record Cue(int start, int end, String text) {}
    record Range(int start, int end) {}
    private static final Pattern TIMING = Pattern.compile("(\\d{2}):(\\d{2}):(\\d{2})[,.](\\d{3})\\s+-->\\s+(\\d{2}):(\\d{2}):(\\d{2})[,.](\\d{3})(?:[ \\t].*)?");
    private ClipPlan() {}

    static List<Cue> parse(String raw) {
        List<Cue> cues = new ArrayList<>();
        for (String block : raw.replace("\r","").replace("\uFEFF","").split("\\n[ \\t]*\\n")) {
            String[] lines = block.strip().split("\\n");
            for (int i = 0; i < Math.min(2, lines.length - 1); i++) {
                Matcher m = TIMING.matcher(lines[i].strip());
                if (!m.matches()) continue;
                int start = time(m, 1), end = time(m, 5);
                StringBuilder caption = new StringBuilder();
                for (int j = i+1; j < lines.length; j++) {
                    if (caption.length() > 0) caption.append('\n');
                    caption.append(lines[j]);
                }
                if (end > start && caption.length() > 0) cues.add(new Cue(start,end,caption.toString()));
                break;
            }
        }
        cues.sort(Comparator.comparingInt(Cue::start));
        return cues;
    }

    private static int time(Matcher m, int offset) {
        int h=Integer.parseInt(m.group(offset)), min=Integer.parseInt(m.group(offset+1));
        int sec=Integer.parseInt(m.group(offset+2));
        return ((h*60 + min)*60+sec)*1000 + Integer.parseInt(m.group(offset+3));
    }

    static Range adjust(int requestedStart, int requestedEnd, int duration, List<Cue> cues) {
        int start = Math.max(0, Math.min(requestedStart,duration));
        int end = Math.max(start, Math.min(requestedEnd,duration));
        // Merge nearby caption lines until punctuation indicates the end of the phrase.
        int first = -1, last = -1;
        String previous = "";
        for (Cue cue : cues) {
            if (first >= 0 && (cue.start() - last > 900 || endsSentence(previous))) {
                if (start > first && start < last) start = first;
                if (end > first && end < last) end = last;
                first = -1;
            }
            if (first < 0) { first = cue.start(); last = cue.end(); }
            else last = Math.max(last,cue.end());
            previous = cue.text().replaceAll("<[^>]*>","");
        }
        if (first >= 0) {
            if (start > first && start < last) start = first;
            if (end > first && end < last) end = last;
        }
        return new Range(start,Math.min(end,duration));
    }

    private static boolean endsSentence(String value) {
        String text = value.replaceAll("[\\p{Pe}\\p{Pf}]+", "").stripTrailing();
        return !text.isEmpty() && ".!?…".indexOf(text.charAt(text.length()-1)) >= 0;
    }

    static String captionAt(List<Cue> cues, int position) {
        for (Cue cue : cues) {
            if (cue.start() > position) break;
            if (position < cue.end()) return cue.text().replaceAll("<[^>]*>","");
        }
        return "";
    }
}
