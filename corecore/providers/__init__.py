"""Footage providers. Each one knows how to search for candidate videos and download one of them."""
from __future__ import annotations

from .base import Candidate, Provider, ProviderError


def get_provider(name: str) -> Provider:
    name = (name or "").strip().lower()
    if name in ("archive", "ia", "internetarchive", "internet-archive"):
        from .archive import ArchiveProvider
        return ArchiveProvider()
    if name in ("ytdlp", "yt-dlp", "youtube", "yt"):
        from .ytdlp import YtDlpProvider
        return YtDlpProvider()
    if name in ("local", "file", "files", "inbox"):
        from .local import LocalProvider
        return LocalProvider()
    if name in ("dailymotion", "dm"):
        from .dailymotion import DailymotionProvider
        return DailymotionProvider()
    if name in ("stream", "hls", "rtsp", "webcam"):
        from .stream import StreamProvider
        return StreamProvider()
    if name in ("reddit",):
        from .reddit import RedditProvider
        return RedditProvider()
    raise ProviderError(f"unknown provider {name!r} (use archive, ytdlp, dailymotion, reddit, stream or local)")


PROVIDER_NAMES = ["archive", "ytdlp", "dailymotion", "reddit", "stream", "local"]

__all__ = ["Candidate", "Provider", "ProviderError", "get_provider", "PROVIDER_NAMES"]
