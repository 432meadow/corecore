"""yt-dlp provider: YouTube and the thousand-odd other sites yt-dlp supports. Accepts a search query
(YouTube search) or any URL yt-dlp understands (video, playlist, channel).

Caveats: downloading from YouTube is against its terms of service, and YouTube blocks most anonymous
datacenter traffic, so expect this to work from a home connection with YTDLP_COOKIES_FROM_BROWSER set,
and to fail on a cloud box. Keep the output for personal use."""
from __future__ import annotations

from pathlib import Path

from .. import config
from .base import Candidate, Logger, Provider, ProviderError


def _ydl_opts(**extra) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ignoreerrors": True,
        "socket_timeout": 30,
        "retries": 3,
    }
    if config.YTDLP_COOKIES_FILE:
        opts["cookiefile"] = config.YTDLP_COOKIES_FILE
    if config.YTDLP_COOKIES_FROM_BROWSER:
        opts["cookiesfrombrowser"] = (config.YTDLP_COOKIES_FROM_BROWSER,)
    opts.update(extra)
    return opts


def _entries(info: dict | None) -> list[dict]:
    if not info:
        return []
    if "entries" in info:
        out = []
        for e in info["entries"] or []:
            if e and "entries" in e:  # nested playlists (channel tabs)
                out.extend(_entries(e))
            elif e:
                out.append(e)
        return out
    return [info]


class YtDlpProvider(Provider):
    name = "ytdlp"

    def search(self, query: str | None, url: str | None, max_items: int) -> list[Candidate]:
        try:
            import yt_dlp
        except ImportError as e:
            raise ProviderError("yt-dlp is not installed (pip install yt-dlp)") from e
        if not (url or query):
            raise ProviderError("ytdlp provider needs a query or a URL")
        target = url or f"ytsearch{max(1, max_items * 2)}:{query}"
        try:
            # "only_download": skip broken entries inside a playlist, but a failing top-level URL is an error
            with yt_dlp.YoutubeDL(_ydl_opts(extract_flat="in_playlist", skip_download=True, playlistend=max_items * 3,
                                            ignoreerrors="only_download")) as ydl:
                info = ydl.extract_info(target, download=False)
        except yt_dlp.utils.DownloadError as e:
            raise ProviderError(f"yt-dlp: {e}") from e
        cands = []
        for e in _entries(info):
            dur = e.get("duration")
            if dur and dur > config.MAX_SOURCE_DURATION:
                continue
            if e.get("live_status") in ("is_live", "is_upcoming"):
                continue
            page = e.get("webpage_url") or e.get("original_url") or e.get("url")
            ext_id = e.get("id") or page
            if not page or not ext_id:
                continue
            cands.append(Candidate("ytdlp", str(ext_id), page, title=e.get("title") or "", uploader=e.get("uploader")
                                   or e.get("channel") or "", duration=float(dur) if dur else None,
                                   license=e.get("license") or ""))
            if len(cands) >= max_items:
                break
        return cands

    def download(self, cand: Candidate, dest_dir: Path, log: Logger) -> Path:
        import yt_dlp
        h = config.YTDLP_MAX_HEIGHT
        fmt = (f"bv*[height<={h}][ext=mp4]+ba[ext=m4a]/b[height<={h}][ext=mp4]/"
               f"bv*[height<={h}]+ba/b[height<={h}]/bv*+ba/b")
        opts = _ydl_opts(format=fmt, outtmpl=str(dest_dir / "ytdlp_%(id)s.%(ext)s"), merge_output_format="mp4",
                         noplaylist=True, max_filesize=config.MAX_SOURCE_BYTES, ignoreerrors=False)
        log(f"yt-dlp downloading {cand.url}")
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(cand.url, download=True)
        except yt_dlp.utils.DownloadError as e:
            raise ProviderError(f"yt-dlp: {e}") from e
        if not info:
            raise ProviderError("yt-dlp returned nothing")
        # A max_filesize abort is not an error for yt-dlp: it just leaves no filepath (and a .part on disk).
        path = next((Path(d["filepath"]) for d in info.get("requested_downloads") or [] if d.get("filepath")), None)
        if path is None or not path.exists() or path.suffix == ".part":
            for leftover in dest_dir.glob(f"ytdlp_{info.get('id')}.*"):
                leftover.unlink(missing_ok=True)
            raise ProviderError("yt-dlp did not complete the download (too large, or blocked)")
        return path
