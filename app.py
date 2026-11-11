import os, re, uuid, socket, ipaddress, subprocess, threading, math, zipfile
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
WORK, OUT = BASE / "work", BASE / "outputs"
WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
app = FastAPI(title="CortaViral AI", version="1.9")
JOBS, LOCK = {}, threading.Lock()
MODEL_LOCK = threading.Lock()
WHISPER_INSTANCE = None
WHISPER_INSTANCE_NAME = None
MIN_CLIP_SECONDS = 30
MAX_CLIP_SECONDS = 90

class AnalyzeRequest(BaseModel):
    url: str
    clips: int = Field(5, ge=1, le=10)
    aspect_ratio: str = Field("9:16", pattern=r"^(9:16|1:1|16:9)$")
    subtitles: bool = True

def update(job, **data):
    # O estado da tarefa fica apenas na memória enquanto o processamento ocorre.
    # O histórico permanente das análises é guardado no SQLite privado do Android.
    with LOCK:
        state = JOBS.setdefault(job, {})
        state.update(data)

def run(cmd, timeout=900):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        detail = (p.stderr or p.stdout or "Falha no processamento")[-1800:]
        raise RuntimeError(detail)
    return p.stdout.strip()

def validate_url(url):
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Informe uma URL pública começando com http:// ou https://.")
    host = p.hostname.lower()
    if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
        raise ValueError("Endereço local não permitido.")
    try:
        addresses = socket.getaddrinfo(host, None)
        if not addresses:
            raise ValueError("Não foi possível localizar o endereço do vídeo.")
        for item in addresses:
            if not ipaddress.ip_address(item[4][0]).is_global:
                raise ValueError("O endereço informado não é público.")
    except socket.gaierror:
        raise ValueError("Não foi possível localizar o endereço do vídeo.")
    return url.strip()

def download(url, folder):
    # yt-dlp cobre centenas de sites e links diretos, mas plataformas podem
    # bloquear extrações automatizadas ou exigir que o vídeo seja público.
    host = (urlparse(url).hostname or "").lower()
    is_tiktok = host == "tiktok.com" or host.endswith(".tiktok.com")
    is_youtube = host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"} or host.endswith(".youtube.com")
    command = [
        "yt-dlp", "--js-runtimes", "deno", "--no-playlist", "--no-warnings", "--no-progress",
        "--socket-timeout", "30", "--retries", "5",
        "--fragment-retries", "5", "--extractor-retries", "5",
        "--concurrent-fragments", "2",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", str(folder / "source.%(ext)s"),
    ]
    if is_tiktok:
        # Cabeçalhos de navegador melhoram compatibilidade, mas não contornam
        # vídeos privados, autenticação ou bloqueios impostos pelo TikTok.
        command += [
            "--referer", "https://www.tiktok.com/",
            "--user-agent",
            "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        ]
    command.append(url)
    try:
        run(command, timeout=1800)
    except RuntimeError as first_error:
        # Tenta o extrator genérico como segunda opção em sites não bloqueados.
        # Isso não contorna login, DRM, paywall ou bloqueios da plataforma.
        error = first_error
        if not is_youtube and not is_tiktok:
            for partial in folder.glob("source.*"):
                if partial.is_file():
                    partial.unlink(missing_ok=True)
            generic_command = command[:-1] + ["--force-generic-extractor", url]
            try:
                run(generic_command, timeout=1800)
            except RuntimeError as generic_error:
                error = generic_error
        detail = str(error)
        lowered = detail.lower()
        if is_youtube and ("not a bot" in lowered or "sign in to confirm" in lowered or "confirm you’re not" in lowered):
            raise RuntimeError(
                "O YouTube bloqueou a leitura automática deste link. O servidor está funcionando, mas não recebeu o arquivo do vídeo. "
                "Não precisamos da sua senha nem dos cookies da sua conta. "
                "Para continuar agora, use IMPORTAR VÍDEO DA GALERIA e selecione um arquivo de vídeo que você tenha autorização para editar. "
                "Links do YouTube podem voltar a funcionar quando a plataforma liberar o acesso automático."
            ) from error
        if is_tiktok and ("no video" in lowered or "video not available" in lowered
                          or "ip address is blocked" in lowered):
            raise RuntimeError(
                "O TikTok não disponibilizou o arquivo de vídeo ao servidor. "
                "Confirme que a publicação é pública e tente o link completo do vídeo. "
                "Se o TikTok continuar bloqueando o acesso, importe o MP4 pela galeria."
            ) from error
        raise
    extensions = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".ts", ".mpg", ".mpeg", ".3gp", ".3g2"}
    files = [p for p in folder.glob("source.*") if p.suffix.lower() in extensions and p.is_file()]
    if not files:
        raise RuntimeError("Não foi possível obter o vídeo. O site pode não ser compatível, exigir login ou bloquear o download.")
    return max(files, key=lambda p: p.stat().st_size)

def duration_of(path):
    return float(run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], 60))

def transcribe(path):
    global WHISPER_INSTANCE, WHISPER_INSTANCE_NAME
    from faster_whisper import WhisperModel
    model_name = (os.getenv("WHISPER_MODEL", "tiny").strip() or "tiny")
    cpu_threads = max(1, min(2, int(os.getenv("WHISPER_CPU_THREADS", "1"))))
    # Um modelo compartilhado evita recarregar pesos e multiplicar o uso de RAM.
    # A transcrição é serializada para respeitar a memória do plano gratuito.
    with MODEL_LOCK:
        if WHISPER_INSTANCE is None or WHISPER_INSTANCE_NAME != model_name:
            WHISPER_INSTANCE = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                cpu_threads=cpu_threads,
                num_workers=1,
            )
            WHISPER_INSTANCE_NAME = model_name
        segments, info = WHISPER_INSTANCE.transcribe(
            str(path),
            beam_size=1,
            best_of=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        data = [
            {"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
            for s in segments if s.text and s.text.strip()
        ]
    return data, getattr(info, "language", "detectado")

HOOKS = [
    "como", "por que", "porque", "segredo", "ninguém", "nunca",
    "incrível", "absurdo", "verdade", "descobri", "atenção",
    "impossível", "resultado", "aconteceu", "não acredito",
    "olha isso", "o que aconteceu", "você sabia"
]
EMOTIONS = [
    "medo", "feliz", "triste", "chocado", "chocante", "emocionante",
    "perigo", "urgente", "vitória", "perdi", "ganhei", "surpresa",
    "engraçado", "terrível", "amo", "odeio", "inacreditável"
]
FILLERS = ["ééé", "tipo assim", "né", "basicamente", " então "]

def score_text(text, seconds, speech):
    low = " " + text.lower() + " "
    words = re.findall(r"\b[\wÀ-ÿ'-]+\b", low)
    count = max(1, len(words))
    wpm = count / max(seconds, 1) * 60
    hook_hits = sum(1 for phrase in HOOKS if phrase in low)
    emotion_hits = sum(1 for phrase in EMOTIONS if phrase in low)
    questions = low.count("?")
    exclamations = low.count("!")
    speech_ratio = min(1, speech / max(seconds, 1))

    score = min(24, hook_hits * 5 + questions * 3 + exclamations * 2)
    score += min(20, emotion_hits * 6)
    score += 18 if 115 <= wpm <= 210 else 12 if 85 <= wpm <= 240 else 6
    score += int(16 * speech_ratio)
    score += 12 if count >= 45 else 8 if count >= 25 else 4
    score += 10 if 45 <= seconds <= 75 else 7
    if any(filler in low for filler in FILLERS):
        score -= 3

    reasons = []
    if hook_hits or questions:
        reasons.append("abre curiosidade")
    if emotion_hits:
        reasons.append("linguagem emocional")
    if 115 <= wpm <= 210:
        reasons.append("ritmo dinâmico")
    if speech_ratio > .75:
        reasons.append("fala contínua")
    if exclamations:
        reasons.append("ênfase na fala")
    return max(0, min(100, score)), reasons or ["trecho com fala contínua"]

def candidates(segs, total):
    found = []
    if not segs:
        # Sem transcrição, distribuir janelas pelo vídeo inteiro sem fingir
        # que existe uma análise semântica do conteúdo.
        # Janelas próximas de 90s, respeitando o mínimo de 30s.
        count = min(60, max(1, math.ceil(total / MAX_CLIP_SECONDS)))
        step = total / count
        for index in range(count):
            start = index * step
            window = min(MAX_CLIP_SECONDS, step)
            end = min(total, start + window)
            if MIN_CLIP_SECONDS <= end - start <= MAX_CLIP_SECONDS:
                found.append({
                    "start": start, "end": end, "text": "", "score": 50,
                    "reasons": ["janela de duração válida; transcrição indisponível"]
                })
        return found

    for i, first in enumerate(segs):
        start = max(0, first["start"] - .35)
        for j in range(i, len(segs)):
            end = segs[j]["end"] + .25
            length = end - start
            if length > MAX_CLIP_SECONDS:
                break
            if length < MIN_CLIP_SECONDS:
                continue
            part = segs[i:j + 1]
            text = " ".join(x["text"] for x in part)
            speech = sum(max(0, x["end"] - x["start"]) for x in part)
            if len(text.split()) < 15:
                continue
            score, reasons = score_text(text, length, speech)
            found.append({
                "start": start, "end": end, "text": text,
                "score": score, "reasons": reasons
            })
            # Explora a faixa inteira permitida, até 90 segundos.
            if length >= MAX_CLIP_SECONDS:
                break

    found.sort(key=lambda x: x["score"], reverse=True)
    unique = []
    for candidate in found:
        if all(
            abs(candidate["start"] - item["start"]) > 8
            or abs(candidate["end"] - item["end"]) > 8
            for item in unique
        ):
            unique.append(candidate)
    return unique[:120]

def stamp(seconds):
    milliseconds = int(max(0, seconds) * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

def make_srt(segs, start, end, path):
    lines, number = [], 1
    for segment in segs:
        if segment["end"] <= start or segment["start"] >= end:
            continue
        lines += [
            str(number),
            f"{stamp(max(0, segment['start'] - start))} --> {stamp(min(end, segment['end']) - start)}",
            segment["text"].replace("-->", "—"), ""
        ]
        number += 1
    path.write_text("\n".join(lines), encoding="utf-8")

def render(source, candidate, index, folder, segs, aspect_ratio="9:16", subtitles_enabled=True):
    start, end = candidate["start"], candidate["end"]
    duration = end - start
    if not MIN_CLIP_SECONDS <= duration <= MAX_CLIP_SECONDS:
        raise RuntimeError("Um corte ficou fora da duração permitida de 30 a 90 segundos.")
    output = OUT / f"{folder.name}_corte_{index:02}.mp4"
    srt = folder / f"clip_{index:02}.srt"
    make_srt(segs, start, end, srt)
    dimensions = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}
    width, height = dimensions.get(aspect_ratio, dimensions["9:16"])
    video_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"
    if subtitles_enabled and srt.exists() and srt.stat().st_size:
        srt_path = str(srt).replace("\\", "/").replace(":", "\\:")
        video_filter += (
            f",subtitles='{srt_path}':force_style="
            "'FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=3,"
            "Alignment=2,MarginV=110'"
        )
    command = [
        "ffmpeg", "-y", "-threads", "1", "-filter_threads", "1",
        "-ss", str(start), "-i", str(source),
        "-t", str(duration), "-vf", video_filter,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-threads", "1",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(output)
    ]
    try:
        run(command, 1800)
    except Exception:
        # Se o filtro de legendas falhar, ainda entrega o corte vertical.
        command[command.index("-vf") + 1] = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"
        )
        run(command, 1800)
    return output

def process_source(job, clips, source, folder, aspect_ratio="9:16", subtitles_enabled=True):
    total = duration_of(source)
    if total < MIN_CLIP_SECONDS:
        raise RuntimeError("O vídeo de origem precisa ter pelo menos 30 segundos.")
    update(job, progress=20, message="Vídeo recebido. Transcrevendo o conteúdo completo…")
    try:
        segs, language = transcribe(source)
        note = f"Transcrição concluída. Idioma detectado: {language}."
    except Exception as error:
        segs = []
        note = (
            "A transcrição não ficou disponível (" + str(error)[:220] +
            "). Os cortes foram distribuídos por duração, sem análise semântica do conteúdo."
        )
    update(job, progress=45, message="Encontrando os melhores momentos entre 30 e 90 segundos…")
    options = candidates(segs, total)
    chosen = []
    for candidate in options:
        if all(
            candidate["end"] <= item["start"] or candidate["start"] >= item["end"]
            for item in chosen
        ):
            chosen.append(candidate)
        if len(chosen) >= clips:
            break
    if not chosen:
        raise RuntimeError("Não encontramos trechos de 30 a 90 segundos neste vídeo. Tente outro vídeo ou uma quantidade menor de cortes.")
    chosen.sort(key=lambda item: item["start"])
    results = []
    for index, candidate in enumerate(chosen, 1):
        update(
            job,
            progress=50 + int(45 * (index - 1) / max(1, len(chosen))),
            message=f"Renderizando corte {index} de {len(chosen)}…"
        )
        file = render(source, candidate, index, folder, segs, aspect_ratio, subtitles_enabled)
        text = candidate["text"]
        results.append({
            "number": index,
            "score": candidate["score"],
            "start": round(candidate["start"], 1),
            "end": round(candidate["end"], 1),
            "duration": round(candidate["end"] - candidate["start"], 1),
            "hook": " ".join(text.split()[:9]) or f"Melhor momento {index}",
            "text": text[:700],
            "reasons": candidate["reasons"],
            "url": f"/outputs/{file.name}"
        })
    update(
        job, status="completed", progress=100, message="Cortes prontos!",
        results=results, transcript_note=note,
        source_duration=round(total, 1),
        score_note="A nota é uma estimativa heurística de potencial de retenção; não prevê nem garante viralização."
    )

def process(job, req):
    folder = WORK / job
    folder.mkdir(parents=True, exist_ok=True)
    try:
        update(job, status="processing", progress=3, message="Baixando vídeo da URL informada…")
        source = download(validate_url(req.url), folder)
        process_source(job, req.clips, source, folder, req.aspect_ratio, req.subtitles)
    except Exception as error:
        update(job, status="error", progress=0, message=str(error)[:1800])

def process_local_upload(job, clips, source, folder, aspect_ratio="9:16", subtitles_enabled=True):
    try:
        update(job, status="processing", progress=15, message="Vídeo recebido. Preparando análise…")
        process_source(job, clips, source, folder, aspect_ratio, subtitles_enabled)
    except Exception as error:
        update(job, status="error", progress=0, message=str(error)[:1800])

@app.post("/api/analyze-upload")
async def analyze_upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    clips: int = Form(5),
    aspect_ratio: str = Form("9:16"),
    subtitles: bool = Form(True)
):
    if clips < 1 or clips > 10:
        raise HTTPException(400, "A quantidade de cortes precisa ficar entre 1 e 10.")
    if aspect_ratio not in {"9:16", "1:1", "16:9"}:
        raise HTTPException(400, "Formato inválido. Escolha 9:16, 1:1 ou 16:9.")
    filename = file.filename or "video.mp4"
    extension = Path(filename).suffix.lower()
    allowed = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv", ".ts", ".mpg", ".mpeg", ".3gp", ".3g2"}
    if extension not in allowed:
        raise HTTPException(415, "Formato de vídeo não suportado. Use MP4, MOV, MKV, WEBM ou AVI.")
    if file.content_type and not file.content_type.startswith("video/") and file.content_type != "application/octet-stream":
        raise HTTPException(415, "O arquivo enviado não foi identificado como vídeo.")
    job = uuid.uuid4().hex[:12]
    folder = WORK / job
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / ("source" + extension)
    try:
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise HTTPException(400, "Não foi possível receber o arquivo de vídeo.")
    finally:
        await file.close()
    if destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(400, "O arquivo de vídeo está vazio.")
    update(job, status="queued", progress=5, message="Vídeo enviado. Entrando na fila…")
    background.add_task(process_local_upload, job, clips, destination, folder, aspect_ratio, subtitles)
    return {"job_id": job}

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, background: BackgroundTasks):
    job = uuid.uuid4().hex[:12]
    (WORK / job).mkdir(parents=True, exist_ok=True)
    update(job, status="queued", progress=0, message="Na fila…")
    background.add_task(process, job, req)
    return {"job_id": job}

@app.get("/api/jobs/{job}/download-all")
def download_all(job: str):
    if not re.fullmatch(r"[a-f0-9]{12}", job):
        raise HTTPException(400, "Identificador de análise inválido.")
    with LOCK:
        current = JOBS.get(job)
        state = dict(current) if current is not None else None
    if state is None:
        raise HTTPException(404, "Análise não está mais disponível no servidor. O histórico salvo no celular continua preservado.")
    if state.get("status") != "completed":
        raise HTTPException(409, "Os cortes ainda não estão prontos para baixar.")
    items = state.get("results", [])
    archive = OUT / f"{job}_todos_os_cortes.zip"
    added = 0
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in items:
            filename = Path(urlparse(item.get("url", "")).path).name
            candidate = OUT / filename
            if filename and candidate.is_file():
                bundle.write(candidate, arcname=f"CortaViral_corte_{int(item.get('number', added + 1)):02}.mp4")
                added += 1
    if added == 0:
        raise HTTPException(404, "Nenhum arquivo de corte foi encontrado para esta análise.")
    return FileResponse(archive, media_type="application/zip", filename="CortaViral_todos_os_cortes.zip")

@app.get("/api/jobs/{job}")
def status(job):
    with LOCK:
        current = JOBS.get(job)
        if current is None:
            raise HTTPException(404, "Análise não está mais ativa no servidor. O histórico concluído permanece salvo no celular.")
        return dict(current)

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app": "CortaViral AI",
        "version": "1.9",
        "api_contract": "cortaviral-v1",
        "deployment_commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "whisper_model": os.getenv("WHISPER_MODEL", "tiny"),
        "sources": ["yt_dlp_supported_sites", "generic_web_pages", "direct_video_url", "gallery_upload"],
        "clip_duration_seconds": {"minimum": MIN_CLIP_SECONDS, "maximum": MAX_CLIP_SECONDS},
        "url_download": "yt_dlp_auto_extractor_with_generic_fallback",
        "upload_endpoint": "/api/analyze-upload",
        "url_endpoint": "/api/analyze",
        "download_all_endpoint": "/api/jobs/{job_id}/download-all",
        "aspect_ratios": ["9:16", "1:1", "16:9"],
        "features": ["broad_url_extractor_support", "generic_extractor_fallback", "gallery_upload", "optional_subtitles", "30_to_90_second_clips", "batch_download", "multiple_aspect_ratios", "local_device_history"],
        "history_storage": "android_device_only"
    }

app.mount("/outputs", StaticFiles(directory=str(OUT)), name="outputs")
app.mount("/", StaticFiles(directory=str(BASE / "static"), html=True), name="static")
