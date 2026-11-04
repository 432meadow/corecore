"""Internet Archive (archive.org). Public-domain and Creative Commons footage: the Prelinger ephemeral films,
NASA, newsreels, old commercials, community uploads. The most dependable *and* most legally comfortable source."""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from .. import config
from .base import Candidate, Logger, Provider, ProviderError

SEARCH_URL = "https://archive.org/advancedsearch.php"
META_URL = "https://archive.org/metadata/"
DOWNLOAD_URL = "https://archive.org/download/"

# Derivative formats in order of preference. Everything here is an .mp4 that browsers and ffmpeg both like.
PREFERRED_FORMATS = ["h.264 IA", "h.264", "512Kb MPEG4", "MPEG4", "HiRes MPEG4", "h.264 HD", "MPEG4 (H.264)"]
SMALL_FIRST = ["512Kb MPEG4", "h.264 IA", "h.264", "MPEG4", "MPEG4 (H.264)", "HiRes MPEG4", "h.264 HD"]
_DETAILS_RE = re.compile(r"archive\.org/(?:details|download|embed)/([^/?#]+)")


def _get_json(url: str, timeout: float = 60) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": config.HTTP_USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _runtime_seconds(s) -> float | None:
    if not s:
        return None
    if isinstance(s, list):
        s = s[0]
    try:
        parts = [float(p) for p in str(s).strip().split(":")]
    except ValueError:
        return None
    secs = 0.0
    for p in parts:
        secs = secs * 60 + p
    return secs or None


def _first(v):
    return v[0] if isinstance(v, list) and v else v


# Any container ffmpeg reads is fine (everything is re-encoded); mp4 derivatives rank first, then the
# originals people upload (yt-dlp mirrors are mostly .webm/.mkv), then legacy formats.
VIDEO_SUFFIXES = {".mp4": 0, ".m4v": 0, ".webm": 1, ".mkv": 1, ".mov": 2, ".ogv": 3, ".avi": 3, ".mpg": 3, ".mpeg": 3,
                  ".flv": 4, ".wmv": 4, ".m2ts": 4, ".ts": 4}


def choose_file(files: list[dict], prefer_small: bool | None = None) -> dict | None:
    """Pick the best video file from an item's file list. CORECORE_ARCHIVE_PREFER_SMALL=1 favours the
    512 kb/s derivative, which downloads several times faster and is plenty for a 540p clip pool."""
    if prefer_small is None:
        prefer_small = os.environ.get("CORECORE_ARCHIVE_PREFER_SMALL", "0") == "1"
    order = SMALL_FIRST if prefer_small else PREFERRED_FORMATS
    best = None
    best_key = None
    for f in files:
        name = f.get("name", "")
        suffix = "." + name.lower().rsplit(".", 1)[-1] if "." in name else ""
        if suffix not in VIDEO_SUFFIXES:
            continue
        fmt = f.get("format", "")
        try:
            size = int(f.get("size") or 0)
        except ValueError:
            size = 0
        if size and size > config.MAX_SOURCE_BYTES:
            continue
        rank = order.index(fmt) if fmt in order else len(order) + VIDEO_SUFFIXES[suffix]
        # prefer the preferred format, then the smaller file (we re-encode anyway)
        key = (rank, size or 10 ** 12)
        if best_key is None or key < best_key:
            best, best_key = f, key
    return best


class ArchiveProvider(Provider):
    name = "archive"

    def search(self, query: str | None, url: str | None, max_items: int) -> list[Candidate]:
        if url:
            m = _DETAILS_RE.search(url)
            if not m:
                raise ProviderError("expected an archive.org/details/<identifier> URL")
            ident = m.group(1)
            meta = _get_json(META_URL + urllib.parse.quote(ident))
            md = meta.get("metadata", {})
            return [Candidate("archive", ident, f"https://archive.org/details/{ident}", title=str(_first(md.get("title")) or ident),
                              uploader=str(_first(md.get("creator")) or ""), duration=_runtime_seconds(md.get("runtime")),
                              license=str(_first(md.get("licenseurl")) or ""))]
        if not query:
            raise ProviderError("archive provider needs a query or an item URL")
        sort = "downloads desc"
        if "|sort=" in query:  # e.g. "collection:mirrortube AND title:(vlog) |sort=date desc"
            query, _, sort = query.partition("|sort=")
            query, sort = query.strip(), sort.strip() or "downloads desc"
        q = query if "mediatype:" in query else f"({query}) AND mediatype:movies"
        page = os.environ.get("CORECORE_ARCHIVE_PAGE", "1")  # rotate pages across scheduled builds for fresh material
        params = [("q", q), ("rows", str(max(1, max_items * 3))), ("page", page if page.isdigit() else "1"),
                  ("output", "json"), ("sort[]", sort)]
        for fl in ("identifier", "title", "creator", "licenseurl", "runtime"):
            params.append(("fl[]", fl))
        data = _get_json(SEARCH_URL + "?" + urllib.parse.urlencode(params))
        if "error" in data or "response" not in data:  # advancedsearch answers bad queries with HTTP 200 + {"error": ...}
            raise ProviderError(f"archive search error: {data.get('error', data)}")
        docs = data.get("response", {}).get("docs", [])
        cands = []
        for d in docs:
            dur = _runtime_seconds(d.get("runtime"))
            if dur and dur > config.MAX_SOURCE_DURATION:
                continue
            ident = d.get("identifier")
            if not ident or config.blocked_title(str(_first(d.get("title")) or "")):
                continue
            cands.append(Candidate("archive", ident, f"https://archive.org/details/{ident}",
                                   title=str(_first(d.get("title")) or ident), uploader=str(_first(d.get("creator")) or ""),
                                   duration=dur, license=str(_first(d.get("licenseurl")) or "")))
            if len(cands) >= max_items:
                break
        return cands

    def download(self, cand: Candidate, dest_dir: Path, log: Logger) -> Path:
        meta = _get_json(META_URL + urllib.parse.quote(cand.external_id))
        f = choose_file(meta.get("files", []))
        if not f:
            raise ProviderError(f"{cand.external_id}: no video file under {config.MAX_SOURCE_BYTES // 2**20} MB")
        url = DOWNLOAD_URL + urllib.parse.quote(cand.external_id) + "/" + urllib.parse.quote(f["name"])
        suffix = "." + f["name"].rsplit(".", 1)[-1].lower()
        dest = dest_dir / f"archive_{cand.external_id}{suffix}"
        log(f"downloading {f['name']} ({int(f.get('size') or 0) // 2**20} MB)")
        req = urllib.request.Request(url, headers={"User-Agent": config.HTTP_USER_AGENT})
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
            part.unlink(missing_ok=True)  # never leave a truncated file where the next run could trust it
            raise
        return dest
