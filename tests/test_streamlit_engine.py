"""Smoke tests for the MoviePy 2.x media helpers in streamlit_app.py."""
import ast
import re
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from moviepy import CompositeVideoClip, TextClip, VideoClip, VideoFileClip


class StreamlitStub:
    @staticmethod
    def warning(_message):
        pass


def load_helpers():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    module = ast.Module(body=definitions, type_ignores=[])
    namespace = {
        "Path": Path,
        "Any": Any,
        "re": re,
        "cv2": cv2,
        "np": np,
        "VideoFileClip": VideoFileClip,
        "CompositeVideoClip": CompositeVideoClip,
        "TextClip": TextClip,
        "st": StreamlitStub,
        "FONT_PATH": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    }
    exec(compile(module, "streamlit_app.py", "exec"), namespace)
    return namespace


def test_moviepy_v2_video_pipeline():
    helpers = load_helpers()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_path = root / "synthetic.mp4"

        def moving_frame(timestamp):
            frame = np.zeros((180, 320, 3), dtype=np.uint8)
            x = int((timestamp % 5) / 5 * 260)
            frame[35:145, x:x + 60, :] = [30, 180, 240]
            return frame

        synthetic = VideoClip(frame_function=moving_frame, duration=35)
        synthetic.write_videofile(
            str(source_path), fps=10, codec="libx264", audio=False, logger=None
        )
        synthetic.close()

        assert helpers["safe_filename"]("Meu vídeo.mp4").endswith(".mp4")
        total, moments = helpers["analyze_moments"](source_path, 30, 30, 1)
        assert total >= 34
        assert len(moments) == 1
        assert 30 <= moments[0][2] - moments[0][1] <= 90

        with VideoFileClip(str(source_path)) as original:
            cut = original.subclipped(0, 30)
            vertical = helpers["crop_to_ratio"](cut, "9:16 vertical")
            assert vertical.size == (720, 1280)
            vertical.close()
            cut.close()

        subtitle_path = root / "video.srt"
        subtitle_path.write_text(
            "1\n00:00:01,000 --> 00:00:03,000\nTeste de legenda\n",
            encoding="utf-8",
        )
        cues = helpers["parse_srt"](subtitle_path)
        assert cues and cues[0][2] == "Teste de legenda"

        with VideoFileClip(str(source_path)) as original:
            cut = original.subclipped(0, 30)
            subtitled = helpers["add_subtitles"](
                cut, cues, 0, 24, "#FFFFFF", "#101010"
            )
            assert subtitled.duration == 30
            subtitled.close()
            cut.close()

        output_dir = root / "cuts"
        output_dir.mkdir()
        results = helpers["export_clips"](
            source_path, moments, output_dir, "Original", cues, False,
            24, "#FFFFFF", "#101010", lambda _progress: None,
        )
        assert results
        exported = Path(results[0]["path"])
        assert exported.exists() and exported.stat().st_size > 1000
