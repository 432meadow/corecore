"""Optional face tagging with OpenCV's bundled Haar cascade. Faces are the most human thing a montage can
cut to (the genre's crying Margot Robbie, screaming Jake Gyllenhaal), so the sequencer prefers them for
climaxes and motifs. When cv2 is not installed everything here quietly returns 0."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

log = logging.getLogger("corecore.faces")

_cascade = None
_unavailable = False


def available() -> bool:
    return _get_cascade() is not None


def _get_cascade():
    global _cascade, _unavailable
    if _cascade is not None or _unavailable:
        return _cascade
    try:
        import cv2  # noqa: WPS433 - optional dependency

        path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(str(path))
        if cascade.empty():
            raise RuntimeError(f"could not load {path}")
        _cascade = cascade
    except Exception as e:  # noqa: BLE001
        log.info("face detection unavailable (%s); install opencv-python-headless to enable it", e)
        _unavailable = True
    return _cascade


def count_faces(image_path: Path | str) -> int:
    cascade = _get_cascade()
    if cascade is None:
        return 0
    import cv2

    img = cv2.imread(str(image_path))
    if img is None:
        return 0
    gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
    return 0 if faces is None else len(faces)


def faces_in_clip(segment: Path | str, duration: float) -> int:
    """Largest face count seen on three frames, but only if faces appear on at least two of them
    (Haar cascades hallucinate on grainy archival footage; a one-frame hit is noise)."""
    if _get_cascade() is None:
        return 0
    from . import ffmpeg

    best = hits = 0
    with tempfile.TemporaryDirectory(prefix="corecore-faces-") as tmp:
        for frac in (0.2, 0.5, 0.8):
            frame = Path(tmp) / f"frame_{int(frac * 100)}.jpg"
            try:
                ffmpeg.thumbnail(segment, max(0.0, duration * frac), frame, width=480)
            except ffmpeg.FFmpegError:
                continue
            n = count_faces(frame)
            if n:
                hits += 1
                best = max(best, n)
    return best if hits >= 2 else 0
