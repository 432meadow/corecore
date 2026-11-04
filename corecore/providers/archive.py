"""Internet Archive (archive.org). Public-domain and Creative Commons footage: the Prelinger ephemeral films,
NASA, newsreels, old commercials, community uploads. The most dependable *and* most legally comfortable source."""
from __future__ import annotations

import json
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


def choose_file(files: list[dict]) -> dict | None:
    """Pick the best mp4 derivative from an item's file list."""
    best = None
    best_key = None
    for f in files:
        name = f.get("name", "")
        if not name.lower().endswith(".mp4"):
            continue
        fmt = f.get("format", "")
        try:
            size = int(f.get("size") or 0)
        except ValueError:
            size = 0
        if size and size > config.MAX_SOURCE_BYTES:
            continue
        rank = PREFERRED_FORMATS.index(fmt) if fmt in PREFERRED_FORMATS else len(PREFERRED_FORMATS)
        # prefer the preferred format, then the smaller file (we re-encode to 720p anyway)
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
        q = query if "mediatype:" in query else f"({query}) AND mediatype:movies"
        params = [("q", q), ("rows", str(max(1, max_items * 3))), ("page", "1"), ("output", "json"),
                  ("sort[]", "downloads desc")]
        for fl in ("identifier", "title", "creator", "licenseurl", "runtime"):
            params.append(("fl[]", fl))
        data = _get_json(SEARCH_URL + "?" + urllib.parse.urlencode(params))
        docs = data.get("response", {}).get("docs", [])
        cands = []
        for d in docs:
            dur = _runtime_seconds(d.get("runtime"))
            if dur and dur > config.MAX_SOURCE_DURATION:
                continue
            ident = d.get("identifier")
            if not ident:
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
            raise ProviderError(f"{cand.external_id}: no mp4 derivative under {config.MAX_SOURCE_BYTES // 2**20} MB")
        url = DOWNLOAD_URL + urllib.parse.quote(cand.external_id) + "/" + urllib.parse.quote(f["name"])
        dest = dest_dir / f"archive_{cand.external_id}.mp4"
        log(f"downloading {f['name']} ({int(f.get('size') or 0) // 2**20} MB)")
        req = urllib.request.Request(url, headers={"User-Agent": config.HTTP_USER_AGENT})
        got = 0
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                got += len(chunk)
                if got > config.MAX_SOURCE_BYTES:
                    raise ProviderError("download exceeded MAX_SOURCE_BYTES")
        return dest
