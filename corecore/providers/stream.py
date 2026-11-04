"""Public live streams (HLS .m3u8, RTSP, anything ffmpeg can open): record a slice and clip it.
Traffic cameras, harbour cams, city webcams: the surveillance register of the genre, straight from the
source. Give it URLs, one per line. Each recording is a new source, so the same camera can be recorded
again and again."""
from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

from .. import config
from .base import Candidate, Logger, Provider, ProviderError


def _seconds() -> int:
    try:
        return max(10, int(os.environ.get("CORECORE_STREAM_SECONDS", "90")))
    except ValueError:
        return 90


class StreamProvider(Provider):
    name = "stream"

    def search(self, query: str | None, url: str | None, max_items: int) -> list[Candidate]:
        urls = [u for u in f"{url or ''} {query or ''}".split() if u.startswith(("http://", "https://", "rtsp://", "rtmp://"))]
        if not urls:
            raise ProviderError("stream provider needs one or more http(s)/rtsp/rtmp stream URLs")
        if max_items > 0:
            urls = urls[:max_items]
        stamp = int(time.time())
        out = []
        for u in urls:
            host = urlparse(u).netloc or u
            tail = urlparse(u).path.rstrip("/").rsplit("/", 1)[-1][:40]
            out.append(Candidate("stream", f"{u}@{stamp}", u, title=f"{host} {tail}".strip(), uploader=host,
                                 duration=float(_seconds())))
        return out

    def download(self, cand: Candidate, dest_dir: Path, log: Logger) -> Path:
        seconds = _seconds()
        digest = hashlib.sha1(cand.external_id.encode()).hexdigest()[:12]
        dest = dest_dir / f"stream_{digest}.mp4"
        args = [config.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostats"]
        if cand.url.startswith("rtsp://"):
            args += ["-rtsp_transport", "tcp"]
        args += ["-i", cand.url, "-t", str(seconds), "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(dest)]
        log(f"recording {seconds}s from {cand.url}")
        try:
            proc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=seconds + 120)
        except subprocess.TimeoutExpired as e:
            dest.unlink(missing_ok=True)
            raise ProviderError("recording timed out") from e
        if proc.returncode != 0 or not dest.exists() or dest.stat().st_size < 1024:
            dest.unlink(missing_ok=True)
            err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
            raise ProviderError(f"ffmpeg could not record the stream: {err[-1] if err else 'unknown error'}")
        return dest
