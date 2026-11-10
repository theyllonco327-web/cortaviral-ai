import os, re, uuid, socket, ipaddress, subprocess, threading
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
WORK, OUT = BASE / "work", BASE / "outputs"
WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
app = FastAPI(title="CortaViral AI", version="1.0")
JOBS, LOCK = {}, threading.Lock()

class AnalyzeRequest(BaseModel):
    url: str
    clips: int = Field(5, ge=1, le=10)
    min_seconds: int = Field(20, ge=10, le=45)
    max_seconds: int = Field(45, ge=15, le=90)

def update(job, **data):
    with LOCK: JOBS[job].update(data)

def run(cmd, timeout=900):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "Falha no processamento")[-1400:])
    return p.stdout.strip()

def validate_url(url):
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Informe uma URL pública começando com http:// ou https://.")
    host = p.hostname.lower()
    if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
        raise ValueError("Endereço local não permitido.")
    try:
        for item in socket.getaddrinfo(host, None):
            if not ipaddress.ip_address(item[4][0]).is_global:
                raise ValueError("O endereço informado não é público.")
    except socket.gaierror:
        raise ValueError("Não foi possível localizar o endereço do vídeo.")
    return url.strip()

def download(url, folder):
    run(["yt-dlp", "--no-playlist", "--no-warnings", "--max-filesize", "1G",
         "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
         "--merge-output-format", "mp4", "-o", str(folder / "source.%(ext)s"), url], 1200)
    files = [p for p in folder.glob("source.*") if p.suffix.lower() in (".mp4",".mkv",".webm",".mov")]
    if not files:
        raise RuntimeError("Não foi possível obter o vídeo. Verifique se a URL é pública e permite download.")
    return max(files, key=lambda p: p.stat().st_size)

def duration_of(path):
    return float(run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","default=noprint_wrappers=1:nokey=1",str(path)],60))

def transcribe(path):
    from faster_whisper import WhisperModel
    model = WhisperModel(os.getenv("WHISPER_MODEL","base"), device="cpu", compute_type="int8")
    segs, info = model.transcribe(str(path), beam_size=3, vad_filter=True)
    data = [{"start":float(s.start),"end":float(s.end),"text":s.text.strip()}
            for s in segs if s.text and s.text.strip()]
    return data, getattr(info,"language","detectado")

HOOKS = ["como","por que","porque","segredo","ninguém","nunca","incrível","absurdo","verdade","descobri","atenção","impossível","resultado","aconteceu","não acredito","olha isso"]
EMOTIONS = ["medo","feliz","triste","chocado","chocante","emocionante","perigo","urgente","vitória","perdi","ganhei","surpresa","engraçado","terrível","amo","odeio"]

def score_text(text, seconds, speech):
    low = text.lower()
    words = re.findall(r"\b[\wÀ-ÿ'-]+\b", low)
    n = max(1,len(words)); wpm = n / max(seconds,1) * 60
    hooks = sum(1 for x in HOOKS if x in low)
    emotions = sum(1 for x in EMOTIONS if x in low)
    score = min(25,hooks*6 + low.count("?")*3 + low.count("!")*2)
    score += min(20,emotions*7)
    score += 20 if 115 <= wpm <= 210 else 14 if 85 <= wpm <= 240 else 7
    score += min(15,int(15*min(1,speech/max(seconds,1))))
    score += 12 if n >= 35 else 8 if n >= 18 else 4
    score += 8 if 20 <= seconds <= 40 else 6
    reasons=[]
    if hooks or "?" in low: reasons.append("abre curiosidade")
    if emotions: reasons.append("linguagem emocional")
    if 115 <= wpm <= 210: reasons.append("ritmo dinâmico")
    if speech/max(seconds,1) > .7: reasons.append("fala contínua")
    return min(100,score), reasons or ["trecho com fala contínua"]

def candidates(segs, total, min_s, max_s):
    found=[]
    if not segs:
        step=max(min_s,int((total-min_s)/5) if total>min_s else min_s)
        start=0
        while start+min_s <= total and len(found)<20:
            end=min(total,start+min(max_s,30))
            found.append({"start":start,"end":end,"text":"","score":50,"reasons":["trecho selecionado por duração"]})
            start += max(10,step)
        return found
    for i, first in enumerate(segs):
        start=max(0,first["start"]-.35)
        for j in range(i,min(len(segs),i+35)):
            end=segs[j]["end"]+.25; length=end-start
            if length<min_s: continue
            if length>max_s: break
            part=segs[i:j+1]; text=" ".join(x["text"] for x in part)
            speech=sum(max(0,x["end"]-x["start"]) for x in part)
            if len(text.split())<12: continue
            score,reasons=score_text(text,length,speech)
            found.append({"start":start,"end":end,"text":text,"score":score,"reasons":reasons})
            if length >= min(max_s*.78,32): break
    found.sort(key=lambda x:x["score"],reverse=True)
    unique=[]
    for c in found:
        if all(abs(c["start"]-u["start"])>8 or abs(c["end"]-u["end"])>8 for u in unique):
            unique.append(c)
    return unique[:60] or candidates([],total,min_s,max_s)

def stamp(t):
    ms=int(max(0,t)*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(segs,start,end,path):
    lines=[]; n=1
    for s in segs:
        if s["end"]<=start or s["start"]>=end: continue
        lines += [str(n),f"{stamp(max(0,s['start']-start))} --> {stamp(min(end,s['end'])-start)}",s["text"].replace("-->","—"),""]
        n+=1
    path.write_text("\n".join(lines),encoding="utf-8")

def render(source,c,index,folder,segs):
    start,end=c["start"],c["end"]
    out=OUT/f"{folder.name}_corte_{index:02}.mp4"
    srt=folder/f"clip_{index:02}.srt"; make_srt(segs,start,end,srt)
    vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    if srt.exists() and srt.stat().st_size:
        srt_path=str(srt).replace("\\","/").replace(":","\\:")
        vf+=f",subtitles='{srt_path}':force_style='FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=110'"
    cmd=["ffmpeg","-y","-ss",str(start),"-i",str(source),"-t",str(end-start),"-vf",vf,
         "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","160k","-movflags","+faststart",str(out)]
    try: run(cmd,900)
    except Exception:
        cmd[cmd.index("-vf")+1]="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
        run(cmd,900)
    return out

def process(job,req):
    folder=WORK/job; folder.mkdir(parents=True,exist_ok=True)
    try:
        update(job,status="processing",progress=5,message="Validando e baixando o vídeo…")
        source=download(validate_url(req.url),folder); total=duration_of(source)
        if total<req.min_seconds: raise RuntimeError("O vídeo é menor que a duração mínima escolhida.")
        update(job,progress=25,message="Transcrevendo e analisando os momentos…")
        try: segs,language=transcribe(source); note=f"Idioma detectado: {language}."
        except Exception: segs=[]; note="Transcrição indisponível; foram selecionadas janelas por duração."
        options=candidates(segs,total,req.min_seconds,req.max_seconds); chosen=[]
        for c in options:
            if all(c["end"]<=x["start"] or c["start"]>=x["end"] for x in chosen):
                chosen.append(c)
            if len(chosen)>=req.clips: break
        chosen.sort(key=lambda x:x["start"]); results=[]
        for i,c in enumerate(chosen,1):
            update(job,progress=30+int(65*(i-1)/max(1,len(chosen))),message=f"Gerando corte {i} de {len(chosen)}…")
            file=render(source,c,i,folder,segs); txt=c["text"]
            results.append({"number":i,"score":c["score"],"start":round(c["start"],1),"end":round(c["end"],1),
              "duration":round(c["end"]-c["start"],1),"hook":" ".join(txt.split()[:9]) or f"Melhor momento {i}",
              "text":txt[:700],"reasons":c["reasons"],"url":f"/outputs/{file.name}"})
        update(job,status="completed",progress=100,message="Cortes prontos!",results=results,
          transcript_note=note,score_note="Nota heurística de potencial de retenção; não prevê nem garante viralização.")
    except Exception as e:
        update(job,status="error",progress=100,message=str(e)[:1200])

@app.post("/api/analyze")
def analyze(req:AnalyzeRequest,background:BackgroundTasks):
    if req.max_seconds<req.min_seconds: raise HTTPException(400,"A duração máxima precisa ser maior que a mínima.")
    job=uuid.uuid4().hex[:12]
    with LOCK: JOBS[job]={"status":"queued","progress":0,"message":"Na fila…"}
    background.add_task(process,job,req)
    return {"job_id":job}

@app.get("/api/jobs/{job}")
def status(job):
    with LOCK:
        if job not in JOBS: raise HTTPException(404,"Análise não encontrada.")
        return JOBS[job]

@app.get("/api/health")
def health(): return {"ok":True,"app":"CortaViral AI"}

app.mount("/outputs",StaticFiles(directory=str(OUT)),name="outputs")
app.mount("/",StaticFiles(directory=str(BASE/"static"),html=True),name="static")
