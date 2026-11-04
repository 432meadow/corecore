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
    raise ProviderError(f"unknown provider {name!r} (use archive, ytdlp or local)")


PROVIDER_NAMES = ["archive", "ytdlp", "local"]

__all__ = ["Candidate", "Provider", "ProviderError", "get_provider", "PROVIDER_NAMES"]
