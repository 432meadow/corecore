"""Thin wrappers around ffmpeg/ffprobe: probing, shot detection, cutting, thumbnails and cheap image stats."""
from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

from . import config


class FFmpegError(RuntimeError):
    pass


def _run(args: list[str], timeout: float | None = None, capture_stdout: bool = True) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE if capture_stdout else subprocess.DEVNULL,
                              stderr=subprocess.PIPE, timeout=timeout, check=False)
    except FileNotFoundError as e:
        raise FFmpegError(f"{args[0]} not found; install ffmpeg") from e
    except subprocess.TimeoutExpired as e:
        raise FFmpegError(f"{args[0]} timed out after {timeout}s") from e
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise FFmpegError(f"{args[0]} failed ({proc.returncode}): {err[-1] if err else 'unknown error'}")
    return proc


def probe(path: Path | str) -> dict:
    proc = _run([config.FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                timeout=120)
    info = json.loads(proc.stdout.decode("utf-8", "replace") or "{}")
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if video is None:
        raise FFmpegError("no video stream")
    duration = float(info.get("format", {}).get("duration") or video.get("duration") or 0.0)
    # where the picture ends: a cut from a stream that stalled can hold less picture than sound (mp4 gives the
    # stream's duration; webm only a DURATION tag, as h:mm:ss.fraction)
    try:
        length = video.get("duration")
        if length is None:
            h, m, s = (video.get("tags") or {}).get("DURATION", "").split(":")
            length = int(h) * 3600 + int(m) * 60 + float(s)
        picture = float(video.get("start_time") or 0.0) + float(length)
    except (TypeError, ValueError):
        picture = duration
    fps = 0.0
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    try:
        num, den = rate.split("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except ValueError:
        pass
    return {
        "duration": duration,
        "picture_end": min(picture, duration) if picture > 0 else duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": fps,
        "has_audio": audio is not None,
        "codec": video.get("codec_name"),
    }


_PTS_RE = re.compile(r"pts_time:([0-9.]+)")


def detect_shots(path: Path | str, threshold: float = config.SCENE_THRESHOLD,
                 max_seconds: float | None = None) -> list[float]:
    """Return timestamps (seconds) where ffmpeg's scene-change score exceeds `threshold`."""
    vf = f"scale={config.ANALYSIS_WIDTH}:-2,select='gt(scene,{threshold})',metadata=print:file=-"
    args = [config.FFMPEG, "-hide_banner", "-nostats", "-loglevel", "error"]
    if max_seconds:
        args += ["-t", f"{max_seconds:.3f}"]
    args += ["-i", str(path), "-an", "-sn", "-vf", vf, "-f", "null", "-"]
    proc = _run(args, timeout=60 * 60)
    cuts = []
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        m = _PTS_RE.search(line)
        if m:
            cuts.append(float(m.group(1)))
    return sorted(set(cuts))


def shots_from_cuts(duration: float, cuts: list[float], min_len: float = config.MIN_SHOT,
                    max_len: float = config.MAX_SHOT, max_chunks: int = config.MAX_CHUNKS_PER_SHOT,
                    edge_trim: float = 0.08) -> list[tuple[float, float]]:
    """Turn cut points into (start, length) shots. Long shots are carved into evenly spread chunks."""
    bounds = [0.0] + [c for c in cuts if 0 < c < duration] + [duration]
    shots: list[tuple[float, float]] = []
    for a, b in zip(bounds, bounds[1:]):
        length = b - a - 2 * edge_trim
        if length < min_len:
            continue
        start = a + edge_trim
        if length <= max_len:
            shots.append((start, length))
            continue
        n = min(max_chunks, max(1, int(length // max_len)))
        stride = (length - max_len) / max(1, n - 1) if n > 1 else 0.0
        for i in range(n):
            shots.append((start + i * stride, max_len))
    return shots


def spread(items: list, limit: int) -> list:
    """Keep at most `limit` items, evenly spaced through the list so clips come from the whole source."""
    if limit <= 0 or len(items) <= limit:
        return list(items)
    step = len(items) / limit
    return [items[min(len(items) - 1, int(i * step + step / 2))] for i in range(limit)]


def cut_segment(src: Path | str, start: float, length: float, out: Path | str, *, height: int = config.SEGMENT_HEIGHT,
                fmt: str = config.SEGMENT_FORMAT, has_audio: bool = True) -> None:
    args = [config.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostats",
            "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{length:.3f}",
            "-vf", f"scale=-2:{height}", "-fps_mode", "cfr", "-map", "0:v:0"]
    if has_audio:
        args += ["-map", "0:a:0?"]
    if fmt == "webm":
        args += ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "33", "-deadline", "realtime", "-cpu-used", "4", "-row-mt", "1"]
        args += ["-c:a", "libopus", "-b:a", "64k", "-ac", "2"] if has_audio else ["-an"]
    else:
        args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-profile:v", "main",
                 "-movflags", "+faststart"]
        args += ["-c:a", "aac", "-b:a", "96k", "-ac", "2"] if has_audio else ["-an"]
    args += [str(out)]
    _run(args, timeout=600, capture_stdout=False)


# More sound than picture by this much, and a clip is trimmed to its picture.
PICTURE_SLACK = 0.5


def fit_to_picture(path: Path | str, info: dict | None = None) -> dict:
    """A cut from a stream that stalled can stop its picture early while the sound runs on, and a player then holds
    the last frame, frozen, to the end. Trim such a file where its picture ends (a stream copy: nothing is
    re-encoded) and return its probe, with "trimmed" set; a file whose picture runs to its end is left as it is.
    A stall the stream recovers from inside the cut is another matter: cut_segment's constant frame rate fills it
    with copies of the frame before it, so the picture runs to the end and this cannot see the freeze."""
    path = Path(path)
    info = info or probe(path)
    if info["duration"] - info["picture_end"] <= PICTURE_SLACK:
        return {**info, "trimmed": False}
    tmp = path.with_name(f"{path.stem}.fit{path.suffix}")
    args = [config.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostats", "-i", str(path),
            "-t", f"{info['picture_end']:.3f}", "-map", "0", "-c", "copy"]
    if path.suffix.lower() in (".mp4", ".mov", ".m4v"):
        args += ["-movflags", "+faststart"]
    try:
        _run(args + [str(tmp)], timeout=120, capture_stdout=False)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return {**probe(path), "trimmed": True}


def transcode(src: Path | str, out: Path | str, *, height: int, crf: int = 27, has_audio: bool = True) -> None:
    """Re-encode an existing clip at a smaller height (used by the static exporter)."""
    args = [config.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostats", "-i", str(src),
            "-vf", f"scale=-2:{height}", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-profile:v", "main", "-movflags", "+faststart"]
    args += ["-c:a", "aac", "-b:a", "80k", "-ac", "2"] if has_audio else ["-an"]
    args += [str(out)]
    _run(args, timeout=600, capture_stdout=False)


def thumbnail(src: Path | str, t: float, out: Path | str, width: int = 320) -> None:
    _run([config.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostats", "-ss", f"{t:.3f}", "-i", str(src),
          "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "4", str(out)], timeout=120, capture_stdout=False)


def frame_stats(path: Path | str, w: int = 32, h: int = 18, fps: int = 4) -> dict:
    """Mean brightness, saturation and inter-frame motion from a tiny raw decode. No numpy needed."""
    proc = _run([config.FFMPEG, "-hide_banner", "-loglevel", "error", "-nostats", "-i", str(path), "-an",
                 "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], timeout=300)
    data = proc.stdout
    frame_bytes = w * h * 3
    n = len(data) // frame_bytes
    if n == 0:
        return {"brightness": None, "saturation": None, "motion": None}
    bright = sat = 0.0
    motion = 0.0
    pixels = w * h
    prev: bytes | None = None
    for f in range(n):
        frame = data[f * frame_bytes:(f + 1) * frame_bytes]
        fb = fs = 0.0
        for i in range(0, frame_bytes, 3):
            r, g, b = frame[i], frame[i + 1], frame[i + 2]
            fb += 0.299 * r + 0.587 * g + 0.114 * b
            mx = max(r, g, b)
            if mx:
                fs += (mx - min(r, g, b)) / mx
        bright += fb / pixels / 255.0
        sat += fs / pixels
        if prev is not None:
            motion += sum(abs(x - y) for x, y in zip(frame, prev)) / frame_bytes / 255.0
        prev = frame
    return {
        "brightness": round(bright / n, 4),
        "saturation": round(sat / n, 4),
        "motion": round(motion / max(1, n - 1), 4) if n > 1 else 0.0,
    }


_VOL_RE = re.compile(r"mean_volume:\s*(-?[0-9.]+)\s*dB")


def loudness(path: Path | str) -> float | None:
    proc = subprocess.run([config.FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "volumedetect",
                           "-f", "null", "-"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=300)
    m = _VOL_RE.search(proc.stderr.decode("utf-8", "replace"))
    if not m:
        return None
    val = float(m.group(1))
    return None if math.isinf(val) else val
