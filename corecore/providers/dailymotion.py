"""Dailymotion: public search API (no key) for discovery, yt-dlp for the download. Lots of contemporary
user uploads (dashcam compilations, news clips, vlogs). Note: yt-dlp's Dailymotion extractor needs its
browser-impersonation extra (`pip install curl_cffi`); without it downloads fail with a clear message."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

from .. import config
from .base import Candidate, Logger, Provider, ProviderError

API = "https://api.dailymotion.com/videos"


def _get_json(url: str, timeout: float = 60) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": config.HTTP_USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


class DailymotionProvider(Provider):
    name = "dailymotion"

    def search(self, query: str | None, url: str | None, max_items: int) -> list[Candidate]:
        if url:
            vid = url.rstrip("/").split("/")[-1].split("?")[0]
            return [Candidate("dailymotion", vid, url, title=vid)]
        if not query:
            raise ProviderError("dailymotion provider needs a search query or a video URL")
        params = {
            "search": query, "fields": "id,title,owner.screenname,duration,url,created_time",
            "sort": "relevance", "limit": str(min(100, max(1, max_items * 3))),
        }
        data = _get_json(API + "?" + urllib.parse.urlencode(params))
        if "error" in data:
            raise ProviderError(f"dailymotion: {data['error'].get('message', data['error'])}")
        cands = []
        for v in data.get("list", []):
            dur = v.get("duration") or 0
            if dur > config.MAX_SOURCE_DURATION or config.blocked_title(v.get("title")):
                continue
            cands.append(Candidate("dailymotion", v["id"], v["url"], title=v.get("title") or v["id"],
                                   uploader=v.get("owner.screenname") or "", duration=float(dur) or None))
            if len(cands) >= max_items:
                break
        return cands

    def download(self, cand: Candidate, dest_dir: Path, log: Logger) -> Path:
        from .ytdlp import YtDlpProvider
        try:
            return YtDlpProvider().download(cand, dest_dir, log)
        except ProviderError as e:
            if "impersonat" in str(e):
                raise ProviderError("dailymotion downloads need yt-dlp's impersonation extra: pip install curl_cffi") from e
            raise
