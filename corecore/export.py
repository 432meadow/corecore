"""Export the player plus a bounded slice of the clip pool as a static site (GitHub Pages, any file host).
The exported index.html flips the player into static mode: clips come from manifest.json instead of the API."""
from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config, db, ffmpeg

STATIC_TAG = '<script>window.CORECORE_STATIC = "manifest.json";</script>'
# an import between the player's modules: from './audio.js'
_IMPORT_RE = re.compile(r"""(\bfrom\s+['"]\./[^'"?]+\.js)(['"])""")


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


# Clips scraped for the sunset variation carry this tag. They are published within a budget of their own, so the
# variation has its footage without the sunsets crowding the main mix (which leans on nature easily enough).
SUNSET = "sunset"


def export_site(out: Path, *, height: int | None = None, max_bytes: int = 450 * 1024 * 1024, max_clips: int = 2000,
                crf: int = 27, tags: list[str] | None = None, sunset_bytes: int = 150 * 1024 * 1024, log=print) -> dict:
    """`tags`: when given, only clips carrying at least one of these tags are exported (e.g. ["modern"] to
    publish the contemporary set from a pool that also holds archival material). `max_bytes` is the main mix's
    budget; clips tagged sunset have `sunset_bytes` to themselves."""
    out = Path(out)
    for sub in ("clips", "thumbs", "web"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    # player. Every script and stylesheet address carries a version, a hash of the player's own code, so a
    # page never meets scripts from another deploy in a CDN's cache (which holds files for minutes): the page
    # links ?v=<hash>, and so does every import between the modules.
    files = sorted(p for p in config.WEB_DIR.iterdir() if p.is_file() and p.name != "index.html")
    version = hashlib.sha1(b"".join(p.name.encode() + p.read_bytes() for p in files)).hexdigest()[:10]
    for p in files:
        if p.suffix == ".js":
            code = p.read_text(encoding="utf-8")
            code = _IMPORT_RE.sub(lambda m: f"{m.group(1)}?v={version}{m.group(2)}", code)
            (out / "web" / p.name).write_text(code, encoding="utf-8")
        else:
            shutil.copy2(p, out / "web" / p.name)
    index = (config.WEB_DIR / "index.html").read_text(encoding="utf-8")
    index = index.replace('href="web/styles.css"', f'href="web/styles.css?v={version}"')
    index = index.replace('src="web/app.js"', f'src="web/app.js?v={version}"')
    marker = '<script type="module"'
    if STATIC_TAG not in index:
        index = index.replace(marker, STATIC_TAG + "\n  " + marker, 1)
    (out / "index.html").write_text(index, encoding="utf-8")
    (out / ".nojekyll").write_text("")

    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT c.*, s.title AS source_title, s.uploader AS source_uploader, s.provider AS source_provider, "
            "s.external_id AS source_external_id FROM clips c JOIN sources s ON s.id = c.source_id "
            "WHERE c.banned = 0 ORDER BY c.id").fetchall()
        rows = [dict(r) for r in rows]
        # the blocklist is applied again here: it may have grown since a source was scraped into the pool
        rows = [r for r in rows if not config.blocked_source(r.get("source_title"), r.get("source_uploader"))]
        # and the bans made on the live site (bans.txt)
        rows = [r for r in rows if not config.banned_clip(f"{r['source_provider']}:{r['source_external_id']}", r.get("start"))]
        if tags:
            wanted = {t.strip().lower() for t in tags if t.strip()}
            rows = [r for r in rows if wanted & set(db.tags_from_db(r["tags"]))]
        sources = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM sources WHERE status = 'done'").fetchall()}
    finally:
        conn.close()

    main = [r for r in rows if SUNSET not in db.tags_from_db(r["tags"])]
    sun = [r for r in rows if SUNSET in db.tags_from_db(r["tags"])]
    chosen, planned = select_clips(main, config.MEDIA_DIR, max_bytes, max_clips)
    sun_chosen, sun_planned = select_clips(sun, config.MEDIA_DIR, sunset_bytes, max_clips)
    log(f"exporting {len(chosen)} of {len(main)} clips (~{planned // 2**20} MB) and {len(sun_chosen)} of {len(sun)} "
        f"sunset clips (~{sun_planned // 2**20} MB) to {out}")
    manifest_clips = []
    total = 0
    used_sources = set()
    budgets = [(chosen, max_bytes), (sun_chosen, sunset_bytes)]
    for part, budget in budgets:
        spent = 0
        for r in part:
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
            if spent + size > budget:
                dst.unlink(missing_ok=True)
                log("size budget reached")
                break
            spent += size
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
                "start": round(r["start"], 2) if r.get("start") is not None else None,
            })

    manifest_sources = [{
        "id": s["id"], "key": f"{s['provider']}:{s['external_id']}", "title": s["title"], "uploader": s["uploader"],
        "url": s["url"], "license": s["license"],
        "provider": s["provider"], "tags": db.tags_from_db(s["tags"]), "query": s["query"],
    } for sid, s in sorted(sources.items()) if sid in used_sources]

    manifest = {
        "version": 1,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "clips": manifest_clips,
        "sources": manifest_sources,
        "bytes": total,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    summary = {"clips": len(manifest_clips), "sources": len(manifest_sources), "bytes": total, "out": str(out),
               "sunset_clips": sum(1 for c in manifest_clips if SUNSET in c["tags"])}
    log(f"done: {summary['clips']} clips from {summary['sources']} sources, {total // 2**20} MB")
    return summary
