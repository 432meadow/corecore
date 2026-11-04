"""Reddit video posts (v.redd.it) from one or more subreddits, through Reddit's OAuth API.

Reddit refuses unauthenticated listings from datacenters, so this needs a free "script" app:
https://www.reddit.com/prefs/apps -> create app -> script. Then set REDDIT_CLIENT_ID and
REDDIT_CLIENT_SECRET (and optionally REDDIT_USER_AGENT). Query: subreddit names, e.g. "dashcam,
oddlyterrifying, liminalspace"; or a post URL. The DASH video and audio tracks are fetched directly
and merged with ffmpeg, so yt-dlp is not involved."""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from .. import config
from .base import Candidate, Logger, Provider, ProviderError

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
_POST_RE = re.compile(r"reddit\.com/r/([^/]+)/comments/([a-z0-9]+)")


def _ua() -> str:
    return os.environ.get("REDDIT_USER_AGENT", "corecore/0.1 (montage tool; by u/corecore)")


def _token() -> str:
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        raise ProviderError("reddit provider needs REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET (a free script app)")
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(TOKEN_URL, data=data, headers={"Authorization": f"Basic {auth}", "User-Agent": _ua()})
    with urllib.request.urlopen(req, timeout=30) as resp:
        tok = json.loads(resp.read().decode("utf-8", "replace"))
    if "access_token" not in tok:
        raise ProviderError(f"reddit token error: {tok}")
    return tok["access_token"]


def _get(path: str, token: str) -> dict:
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {token}", "User-Agent": _ua()})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _candidates_from_posts(posts: list[dict], max_items: int) -> list[Candidate]:
    out = []
    for p in posts:
        d = p.get("data", p)
        rv = ((d.get("secure_media") or d.get("media") or {}).get("reddit_video")) or {}
        if not d.get("is_video") or not rv.get("fallback_url") or d.get("over_18"):
            continue
        if config.blocked_title(d.get("title")):
            continue
        dur = float(rv.get("duration") or 0) or None
        if dur and dur > config.MAX_SOURCE_DURATION:
            continue
        out.append(Candidate("reddit", d["id"], "https://www.reddit.com" + d.get("permalink", ""), title=d.get("title") or d["id"],
                             uploader=f"r/{d.get('subreddit', '')}", duration=dur,
                             extra={"video": rv["fallback_url"].split("?")[0]}))
        if max_items > 0 and len(out) >= max_items:
            break
    return out


class RedditProvider(Provider):
    name = "reddit"

    def search(self, query: str | None, url: str | None, max_items: int) -> list[Candidate]:
        token = _token()
        if url:
            m = _POST_RE.search(url)
            if not m:
                raise ProviderError("expected a reddit.com/r/<sub>/comments/<id> URL")
            data = _get(f"/r/{m.group(1)}/comments/{m.group(2)}?raw_json=1&limit=1", token)
            posts = data[0]["data"]["children"] if isinstance(data, list) else []
            return _candidates_from_posts(posts, 1)
        subs = [s.strip().lstrip("r/").strip("/") for s in (query or "").replace(" ", ",").split(",") if s.strip()]
        if not subs:
            raise ProviderError("reddit provider needs subreddit names (e.g. dashcam, oddlyterrifying) or a post URL")
        per = max(5, (max_items * 3) // max(1, len(subs)) + 5)
        cands: list[Candidate] = []
        for sub in subs:
            data = _get(f"/r/{urllib.parse.quote(sub)}/top?t=week&limit={min(100, per)}&raw_json=1", token)
            cands.extend(_candidates_from_posts(data.get("data", {}).get("children", []), 0))
        return cands[:max_items] if max_items > 0 else cands

    def download(self, cand: Candidate, dest_dir: Path, log: Logger) -> Path:
        video = cand.extra.get("video")
        if not video:
            raise ProviderError("no video url on candidate")
        base = video.rsplit("/", 1)[0]
        vpath = dest_dir / f"reddit_{cand.external_id}_v.mp4"
        apath = dest_dir / f"reddit_{cand.external_id}_a.mp4"
        dest = dest_dir / f"reddit_{cand.external_id}.mp4"
        self._fetch(video, vpath, log)
        got_audio = False
        for name in ("DASH_AUDIO_128.mp4", "DASH_AUDIO_64.mp4", "DASH_audio.mp4"):
            try:
                self._fetch(f"{base}/{name}", apath, log)
                got_audio = apath.stat().st_size > 1024
                if got_audio:
                    break
            except Exception:  # noqa: BLE001 - many posts have no audio track
                continue
        if got_audio:
            proc = subprocess.run([config.FFMPEG, "-y", "-loglevel", "error", "-i", str(vpath), "-i", str(apath),
                                   "-c", "copy", "-movflags", "+faststart", str(dest)], stderr=subprocess.PIPE, timeout=300)
            apath.unlink(missing_ok=True)
            if proc.returncode == 0:
                vpath.unlink(missing_ok=True)
                return dest
        vpath.replace(dest)
        return dest

    @staticmethod
    def _fetch(url: str, dest: Path, log) -> None:
        req = urllib.request.Request(url, headers={"User-Agent": _ua()})
        part = dest.with_suffix(".part")
        got = 0
        try:
            with urllib.request.urlopen(req, timeout=120) as resp, open(part, "wb") as out:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
                    got += len(chunk)
                    if got > config.MAX_SOURCE_BYTES:
                        raise ProviderError("download exceeded MAX_SOURCE_BYTES")
            part.replace(dest)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
