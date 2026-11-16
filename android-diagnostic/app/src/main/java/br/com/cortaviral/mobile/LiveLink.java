package br.com.cortaviral.mobile;

import java.net.URI;
import java.util.Locale;
import java.util.regex.Pattern;

final class LiveLink {
    record Source(String url, String platform, String packageName) {}
    private static final Pattern YT_ID = Pattern.compile("[A-Za-z0-9_-]{11}");
    static Source parse(String text) {
        if (text == null || text.length() > 2048) throw bad();
        URI u;
        try {u=URI.create(text.strip());} catch (IllegalArgumentException e) {throw bad();}
        if (!"https".equalsIgnoreCase(u.getScheme()) || u.getHost()==null ||
                u.getRawUserInfo()!=null || u.getPort()!=-1) throw bad();
        String host=u.getHost().toLowerCase(Locale.ROOT), p=u.getRawPath();
        if ("youtu.be".equals(host) || "youtube.com".equals(host) || "www.youtube.com".equals(host) || "m.youtube.com".equals(host)) {
            String id="";
            if (host.equals("youtu.be") && p.startsWith("/")) id=p.substring(1);
            else if (p.startsWith("/live/")) id=p.substring(6);
            else if (p.equals("/watch") && u.getRawQuery()!=null)
                for (String q:u.getRawQuery().split("&")) if (q.startsWith("v=")) {id=q.substring(2);break;}
            if (!YT_ID.matcher(id).matches()) throw bad();
            return new Source("https://www.youtube.com/live/"+id,"YouTube","com.google.android.youtube");
        }
        if (host.equals("vt.tiktok.com") || host.equals("vm.tiktok.com") ||
                host.equals("www.tiktok.com") || host.equals("tiktok.com") || host.equals("m.tiktok.com")) {
            if (p.isEmpty() || p.equals("/")) throw bad();
            return new Source(u.toASCIIString(),"TikTok","com.zhiliaoapp.musically");
        }
        throw bad();
    }
    private static IllegalArgumentException bad() {return new IllegalArgumentException("Cole um link HTTPS de live do YouTube ou TikTok.");}
}
