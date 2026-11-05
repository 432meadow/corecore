"""Export the player plus a bounded slice of the clip pool as a static site (GitHub Pages, any file host).
The exported index.html flips the player into static mode: clips come from manifest.json instead of the API."""
from __future__ import annotations

import json
import random
import shutil
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config, db, ffmpeg

STATIC_TAG = '<script>window.CORECORE_STATIC = "manifest.json";</script>'


def select_clips(rows: list, media_dir: Path, max_bytes: int, max_clips: int) -> tuple[list, int]:
    """Round-robin across sources (so the export is varied, not the first N files) until a budget is hit."""
    by_source: dict[int, list] = defaultdict(list)
    for r in rows:
        by_source[r["source_id"]].append(r)
    queues = []
    for sid, lst in sorted(by_source.items()):
        random.Random(sid).shuffle(lst)
        queues.append(lst)
    random.Random(0).shuffle(queues)
    chosen: list = []
    total = 0
    while queues and len(chosen) < max_clips:
        for q in list(queues):
            if not q:
                queues.remove(q)
                continue
            r = q.pop(0)
            path = media_dir / r["file"]
            if not path.exists():
                continue
            size = path.stat().st_size
            if total + size > max_bytes:
                return chosen, total
            chosen.append(r)
            total += size
            if len(chosen) >= max_clips:
                break
    return chosen, total


def export_site(out: Path, *, height: int | None = None, max_bytes: int = 450 * 1024 * 1024, max_clips: int = 2000,
                crf: int = 27, tags: list[str] | None = None, log=print) -> dict:
    """`tags`: when given, only clips carrying at least one of these tags are exported (e.g. ["modern"] to
    publish the contemporary set from a pool that also holds archival material)."""
    out = Path(out)
    for sub in ("clips", "thumbs", "web", "music"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    # player
    for p in config.WEB_DIR.iterdir():
        if p.is_file() and p.name != "index.html":
            shutil.copy2(p, out / "web" / p.name)
    index = (config.WEB_DIR / "index.html").read_text(encoding="utf-8")
    marker = '<script type="module"'
    if STATIC_TAG not in index:
        index = index.replace(marker, STATIC_TAG + "\n  " + marker, 1)
    (out / "index.html").write_text(index, encoding="utf-8")
    (out / ".nojekyll").write_text("")

    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT c.*, s.title AS source_title, s.uploader AS source_uploader FROM clips c JOIN sources s ON s.id = c.source_id "
            "WHERE c.banned = 0 ORDER BY c.id").fetchall()
        rows = [dict(r) for r in rows]
        # the blocklist is applied again here: it may have grown since a source was scraped into the pool
        rows = [r for r in rows if not config.blocked_source(r.get("source_title"), r.get("source_uploader"))]
        if tags:
            wanted = {t.strip().lower() for t in tags if t.strip()}
            rows = [r for r in rows if wanted & set(db.tags_from_db(r["tags"]))]
        sources = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM sources WHERE status = 'done'").fetchall()}
    finally:
        conn.close()

    chosen, planned = select_clips(rows, config.MEDIA_DIR, max_bytes, max_clips)
    log(f"exporting {len(chosen)} of {len(rows)} clips (~{planned // 2**20} MB) to {out}")
    manifest_clips = []
    total = 0
    used_sources = set()
    for r in chosen:
        src = config.MEDIA_DIR / r["file"]
        name = Path(r["file"]).name
        dst = out / "clips" / name
        try:
            if height and r.get("height") and height < r["height"]:
                ffmpeg.transcode(src, dst, height=height, crf=crf, has_audio=bool(r.get("has_audio")))
            elif not dst.exists() or dst.stat().st_size != src.stat().st_size:
                shutil.copy2(src, dst)
        except (ffmpeg.FFmpegError, OSError) as e:
            log(f"skip {name}: {e}")
            continue
        size = dst.stat().st_size
        if total + size > max_bytes:
            dst.unlink(missing_ok=True)
            log("size budget reached")
            break
        total += size
        thumb = None
        if r.get("thumb") and (config.MEDIA_DIR / r["thumb"]).exists():
            tname = Path(r["thumb"]).name
            shutil.copy2(config.MEDIA_DIR / r["thumb"], out / "thumbs" / tname)
            thumb = f"thumbs/{tname}"
        used_sources.add(r["source_id"])
        manifest_clips.append({
            "id": r["id"], "source_id": r["source_id"], "file": f"clips/{name}", "thumb": thumb,
            "duration": r["duration"], "width": r["width"], "height": r["height"], "has_audio": bool(r["has_audio"]),
            "brightness": r["brightness"], "saturation": r["saturation"], "motion": r["motion"], "loudness": r["loudness"],
            "faces": r.get("faces") or 0, "tags": db.tags_from_db(r["tags"]),
        })

    manifest_sources = [{
        "id": s["id"], "title": s["title"], "uploader": s["uploader"], "url": s["url"], "license": s["license"],
        "provider": s["provider"], "tags": db.tags_from_db(s["tags"]), "query": s["query"],
    } for sid, s in sorted(sources.items()) if sid in used_sources]

    music = []
    if config.MUSIC_DIR.exists():
        for p in sorted(config.MUSIC_DIR.iterdir()):
            if p.is_file() and p.suffix.lower() in config.MUSIC_EXTENSIONS:
                shutil.copy2(p, out / "music" / p.name)
                music.append({"name": p.name, "url": f"music/{urllib.parse.quote(p.name)}"})

    manifest = {
        "version": 1,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "clips": manifest_clips,
        "sources": manifest_sources,
        "music": music,
        "bytes": total,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    summary = {"clips": len(manifest_clips), "sources": len(manifest_sources), "bytes": total, "music": len(music), "out": str(out)}
    log(f"done: {summary['clips']} clips from {summary['sources']} sources, {total // 2**20} MB")
    return summary
