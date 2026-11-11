from __future__ import annotations

import io
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import streamlit as st
import yt_dlp
from moviepy import CompositeVideoClip, TextClip, VideoFileClip

st.set_page_config(page_title="CortaViral AI · Studio", page_icon="✂️", layout="wide")
st.title("✂️ CortaViral AI — Studio")
st.caption("Crie cortes de 30 a 90 segundos a partir de vídeos que você tem direito de usar.")

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
)
FONT_PATH = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)


def get_workspace() -> Path:
    if "workspace" not in st.session_state:
        st.session_state.workspace = tempfile.mkdtemp(prefix="cortaviral_")
    folder = Path(st.session_state.workspace)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def safe_filename(value: str, fallback: str = "video") -> str:
    original = Path(value)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", original.stem).strip("_")
    suffix = re.sub(r"[^A-Za-z0-9.]", "", original.suffix.lower())
    return (stem[:48] or fallback) + suffix


def find_downloaded_video(folder: Path) -> Path:
    # yt-dlp may change the extension after merging audio and video.
    candidates = [p for p in folder.glob("video.*") if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not candidates:
        candidates = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not candidates:
        raise RuntimeError("O yt-dlp terminou, mas não encontrei o arquivo de vídeo baixado.")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def download_video(url: str, folder: Path, fetch_subtitles: bool) -> tuple[Path, Path | None, str]:
    if not re.match(r"^https?://", url.strip(), re.IGNORECASE):
        raise ValueError("Cole um endereço completo começando com https:// ou http://.")

    options: dict[str, Any] = {
        "format": "bv*+ba/b",
        "outtmpl": str(folder / "video.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
    }
    if fetch_subtitles:
        options.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["pt-BR", "pt", "en"],
            "subtitlesformat": "srt/best",
        })

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url.strip(), download=True)

    video_path = find_downloaded_video(folder)
    subtitle_candidates = sorted(folder.glob("video*.srt"), key=lambda p: p.stat().st_mtime, reverse=True)
    subtitle_path = subtitle_candidates[0] if subtitle_candidates else None
    return video_path, subtitle_path, str(info.get("title") or "video")


def parse_srt(path: Path | None) -> list[tuple[float, float, str]]:
    if not path or not path.exists():
        return []

    def to_seconds(stamp: str) -> float:
        hours, minutes, rest = stamp.replace(",", ".").split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(rest)

    raw = path.read_text(encoding="utf-8", errors="replace")
    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\r?\n\s*\r?\n", raw.strip()):
        lines = block.strip().splitlines()
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0:
            continue
        match = re.search(r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)", lines[timing_index])
        if not match:
            continue
        start, end = to_seconds(match.group(1)), to_seconds(match.group(2))
        text = re.sub(r"<[^>]+>", "", " ".join(lines[timing_index + 1:])).strip()
        if end > start and text:
            cues.append((start, end, text))
    return cues


def frame_activity(video_path: Path) -> tuple[list[float], list[float]]:
    """Lightweight visual activity score using sampled frames, not every frame."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("Não consegui abrir o vídeo para análise. Verifique se o arquivo está íntegro.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if frame_count > 0 else 0.0
    sample_step = 1.25
    times: list[float] = []
    scores: list[float] = []
    previous: np.ndarray | None = None

    try:
        if duration <= 0:
            raise RuntimeError("Não consegui identificar a duração do vídeo.")
        for timestamp in np.arange(0.0, duration, sample_step):
            cap.set(cv2.CAP_PROP_POS_MSEC, float(timestamp) * 1000.0)
            ok, frame = cap.read()
            if not ok:
                continue
            small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            activity = 0.0 if previous is None else float(cv2.absdiff(gray, previous).mean()) / 255.0
            times.append(float(timestamp))
            scores.append(activity)
            previous = gray
    finally:
        cap.release()
    return times, scores


def analyze_moments(video_path: Path, minimum: int, maximum: int, count: int) -> tuple[float, list[tuple[float, float, float]]]:
    with VideoFileClip(str(video_path)) as clip:
        total = float(clip.duration or 0)
    if total < minimum:
        raise ValueError(f"O vídeo tem {total:.1f}s. Para criar cortes de pelo menos {minimum}s, envie um vídeo mais longo.")

    window = min(float(maximum), total)
    step = max(5.0, min(15.0, window / 4.0))
    starts = list(np.arange(0, max(0.0, total - window) + 0.001, step))
    last_start = max(0.0, total - window)
    if not starts or abs(starts[-1] - last_start) > 0.5:
        starts.append(last_start)

    times, activity = frame_activity(video_path)
    candidates: list[tuple[float, float, float]] = []
    for start in sorted(set(round(float(x), 2) for x in starts)):
        end = min(total, start + window)
        if end - start < minimum:
            continue
        values = [score for timestamp, score in zip(times, activity) if start <= timestamp <= end]
        if values:
            average = float(np.mean(values))
            peak = float(np.percentile(values, 85))
            score = average * 0.65 + peak * 0.35
        else:
            score = 0.0
        center_bonus = 0.02 * (1.0 - abs(((start + end) / 2) / total - 0.5) * 2.0)
        candidates.append((score + center_bonus, start, end))

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[float, float, float]] = []
    for candidate in candidates:
        _, start, end = candidate
        if all(end <= chosen[1] or start >= chosen[2] for chosen in selected):
            selected.append(candidate)
        if len(selected) >= count:
            break
    if not selected:
        raise RuntimeError("Não encontrei janelas válidas para gerar os cortes.")
    return total, sorted(selected, key=lambda item: item[1])


def crop_to_ratio(clip: VideoFileClip, ratio_name: str):
    if ratio_name == "Original":
        return clip
    target_ratio = 9 / 16 if ratio_name == "9:16 vertical" else 1.0
    width, height = clip.size
    current_ratio = width / height
    if current_ratio > target_ratio:
        crop_width = int(height * target_ratio)
        x1 = max(0, (width - crop_width) // 2)
        cropped = clip.cropped(x1=x1, y1=0, x2=x1 + crop_width, y2=height)
    else:
        crop_height = int(width / target_ratio)
        y1 = max(0, (height - crop_height) // 2)
        cropped = clip.cropped(x1=0, y1=y1, x2=width, y2=y1 + crop_height)
    if ratio_name == "9:16 vertical":
        return cropped.resized(new_size=(720, 1280))
    return cropped.resized(new_size=(1080, 1080))


def add_subtitles(clip, cues: list[tuple[float, float, str]], offset: float, font_size: int, text_color: str, background: str):
    if not cues:
        return clip
    if FONT_PATH is None:
        st.warning("Não encontrei uma fonte TrueType no servidor; os cortes serão exportados sem legenda embutida.")
        return clip

    overlays = []
    for start, end, text in cues:
        local_start = max(0.0, start - offset)
        local_end = min(float(clip.duration), end - offset)
        if local_end <= local_start:
            continue
        overlay = TextClip(
            font=FONT_PATH,
            text=text,
            font_size=font_size,
            color=text_color,
            bg_color=background,
            method="caption",
            size=(max(200, int(clip.w * 0.88)), 110),
            text_align="center",
            horizontal_align="center",
            vertical_align="center",
        ).with_start(local_start).with_end(local_end).with_position(("center", "bottom"))
        overlays.append(overlay)

    if not overlays:
        return clip
    result = CompositeVideoClip([clip, *overlays], size=clip.size).with_duration(clip.duration)
    if clip.audio is not None:
        result = result.with_audio(clip.audio)
    return result


def export_clips(video_path: Path, moments: list[tuple[float, float, float]], output_dir: Path,
                 ratio_name: str, subtitle_cues: list[tuple[float, float, str]],
                 burn_subtitles: bool, font_size: int, text_color: str, background: str,
                 progress_callback) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    source = VideoFileClip(str(video_path))
    try:
        for index, (_, start, end) in enumerate(moments, start=1):
            cut = source.subclipped(start, end)
            transformed = crop_to_ratio(cut, ratio_name)
            if burn_subtitles:
                transformed = add_subtitles(transformed, subtitle_cues, start, font_size, text_color, background)

            output_path = output_dir / f"corte_{index:02d}.mp4"
            try:
                transformed.write_videofile(
                    str(output_path),
                    codec="libx264",
                    audio_codec="aac",
                    fps=source.fps or 30,
                    preset="veryfast",
                    threads=2,
                    logger=None,
                )
            finally:
                if transformed is not cut:
                    transformed.close()
                cut.close()

            results.append({"path": output_path, "start": start, "end": end, "duration": end - start})
            progress_callback(index / len(moments))
    finally:
        source.close()
    return results


with st.sidebar:
    st.header("⚙️ Configurações")
    min_seconds = st.slider("Duração mínima do corte", 30, 90, 30, step=5)
    max_seconds = st.slider("Duração máxima do corte", 30, 90, 60, step=5)
    if max_seconds < min_seconds:
        st.warning("A duração máxima precisa ser igual ou maior que a mínima. Ajustei para o valor mínimo.")
        max_seconds = min_seconds
    number_of_clips = st.slider("Quantidade de cortes", 1, 10, 3)
    aspect_ratio = st.radio("Formato", ["9:16 vertical", "1:1 quadrado", "Original"])
    burn_subtitles = st.checkbox("Embutir legendas no vídeo", value=True)
    fetch_subtitles = st.checkbox("Buscar legendas do YouTube", value=True)
    font_size = st.slider("Tamanho da legenda", 18, 54, 32)
    text_color = st.color_picker("Cor do texto", "#FFFFFF")
    background_color = st.color_picker("Fundo da legenda", "#101010")

url_tab, file_tab = st.tabs(["🔗 Link de vídeo", "📁 Galeria do aparelho"])

with url_tab:
    url = st.text_input("URL pública do vídeo", placeholder="https://...")
    if st.button("Baixar vídeo", type="primary", disabled=not url.strip(), use_container_width=True):
        folder = get_workspace() / "source"
        folder.mkdir(parents=True, exist_ok=True)
        with st.spinner("Baixando vídeo e procurando legendas disponíveis..."):
            try:
                video, subtitles, title = download_video(url, folder, fetch_subtitles)
                st.session_state.source_path = str(video)
                st.session_state.subtitle_path = str(subtitles) if subtitles else None
                st.session_state.source_title = title
                st.session_state.generated = []
                st.success(f"Vídeo recebido: {title}")
            except Exception as exc:
                st.error(f"Não foi possível baixar esse link: {exc}")
                st.caption("Links privados, com DRM, login obrigatório ou bloqueio da plataforma não são suportados.")

with file_tab:
    uploaded = st.file_uploader("Escolha um vídeo do aparelho", type=["mp4", "mov", "mkv", "webm", "avi"])
    if uploaded is not None and st.button("Usar este vídeo", use_container_width=True):
        folder = get_workspace() / "source"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / safe_filename(uploaded.name)
        target.write_bytes(uploaded.getbuffer())
        st.session_state.source_path = str(target)
        st.session_state.subtitle_path = None
        st.session_state.source_title = uploaded.name
        st.session_state.generated = []
        st.success(f"Vídeo carregado: {uploaded.name}")

source_value = st.session_state.get("source_path")
if source_value and Path(source_value).exists():
    source_path = Path(source_value)
    st.divider()
    st.subheader(f"🎬 {st.session_state.get('source_title', source_path.name)}")
    try:
        with VideoFileClip(str(source_path)) as preview:
            duration = float(preview.duration)
            col1, col2, col3 = st.columns(3)
            col1.metric("Duração", f"{duration:.1f} s")
            col2.metric("Resolução", f"{preview.w} × {preview.h}")
            col3.metric("FPS", f"{preview.fps:.1f}")
        st.video(str(source_path))
    except Exception as exc:
        st.error(f"Não consegui abrir esse vídeo: {exc}")
        st.stop()

    if st.button("✂️ Analisar e gerar cortes", type="primary", use_container_width=True):
        output_dir = get_workspace() / "cuts"
        output_dir.mkdir(parents=True, exist_ok=True)
        progress = st.progress(0.0)
        status = st.empty()
        try:
            status.info("Analisando movimento e mudanças visuais...")
            _, moments = analyze_moments(source_path, min_seconds, max_seconds, number_of_clips)
            subtitle_path_value = st.session_state.get("subtitle_path")
            cues = parse_srt(Path(subtitle_path_value) if subtitle_path_value else None)
            if burn_subtitles and not cues:
                st.info("Não encontrei legendas no vídeo. Os cortes serão gerados sem legendas embutidas.")

            status.info(f"Gerando {len(moments)} corte(s)...")
            results = export_clips(
                source_path, moments, output_dir, aspect_ratio, cues,
                burn_subtitles, font_size, text_color, background_color,
                lambda value: progress.progress(value),
            )
            st.session_state.generated = [
                {"path": str(item["path"]), "start": item["start"], "end": item["end"], "duration": item["duration"]}
                for item in results
            ]
            progress.progress(1.0)
            status.success(f"Concluído: {len(results)} corte(s) gerado(s).")
        except Exception as exc:
            status.error(f"Falha no processamento: {exc}")
            st.exception(exc)

    generated = st.session_state.get("generated", [])
    if generated:
        st.divider()
        st.subheader("📦 Cortes prontos")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in generated:
                file_path = Path(item["path"])
                if file_path.exists():
                    archive.write(file_path, arcname=file_path.name)
        st.download_button(
            "⬇️ Baixar todos os cortes (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="cortaviral_cortes.zip",
            mime="application/zip",
            use_container_width=True,
        )
        for index, item in enumerate(generated, start=1):
            file_path = Path(item["path"])
            if not file_path.exists():
                continue
            with st.expander(f"Corte {index} · {item['start']:.1f}s–{item['end']:.1f}s · {item['duration']:.0f}s", expanded=index == 1):
                st.video(str(file_path))
                st.download_button(
                    f"Baixar corte {index}",
                    data=file_path.read_bytes(),
                    file_name=file_path.name,
                    mime="video/mp4",
                    key=f"download_{index}_{file_path.name}",
                    use_container_width=True,
                )
else:
    st.info("Cole um link público ou escolha um vídeo da galeria para começar.")

st.caption("A seleção de momentos usa atividade visual como sinal aproximado de interesse; não promete viralização. Use somente vídeos que você tem direito de baixar e editar.")
