"""HTTP API + static frontend. Run with `python -m corecore serve`."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db
from .jobs import Worker, create_job
from .providers import PROVIDER_NAMES, ProviderError

log = logging.getLogger("corecore.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    db.init()
    worker = None
    if os.environ.get("CORECORE_NO_WORKER") != "1":
        worker = Worker()
        worker.start()
    try:
        yield
    finally:
        if worker:
            worker.stop()


app = FastAPI(title="corecore", version="0.1.0", lifespan=lifespan)


class JobIn(BaseModel):
    provider: str = Field(default="archive", description="archive | ytdlp | local")
    query: str | None = None
    url: str | None = None
    max_items: int = Field(default=5, ge=0, le=200)
    tags: list[str] | str | None = None


@app.get("/api/health")
def health():
    return {"ok": True, "version": "0.1.0"}


@app.get("/api/stats")
def stats():
    with db.connect() as conn:
        return db.stats(conn)


def _parse_ids(raw: str | None) -> list[int] | None:
    out = []
    for tok in (raw or "").split(","):
        try:
            v = int(tok.strip())
        except ValueError:
            continue
        if 0 <= v < 2**62:
            out.append(v)
    return out or None


@app.get("/api/clips/sample")
def clips_sample(n: int = Query(100, ge=1, le=500), tags: str | None = None, exclude: str | None = None,
                 seed: int | None = None):
    tag_list = [t for t in (tags or "").split(",") if t.strip()] or None
    excl = _parse_ids(exclude)
    with db.connect() as conn:
        rows = db.sample_clips(conn, n=n, tags=tag_list, exclude=excl, seed=seed)
        return {"clips": [db.clip_to_dict(r) for r in rows]}


@app.get("/api/clips")
def clips_list(offset: int = Query(0, ge=0), limit: int = Query(60, ge=1, le=500), tag: str | None = None,
               include_banned: bool = False):
    where = [] if include_banned else ["c.banned = 0"]
    params: list = []
    if tag:
        pattern = db.tag_like(tag)
        if not pattern:
            return {"clips": [], "offset": offset, "limit": limit}
        where.append("c.tags LIKE ? ESCAPE '\\'")
        params.append(pattern)
    sql = ("SELECT c.*, s.title AS source_title, s.uploader AS source_uploader, s.url AS source_url, s.provider AS provider,"
           " s.license AS license FROM clips c JOIN sources s ON s.id = c.source_id")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY c.id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with db.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return {"clips": [db.clip_to_dict(r) for r in rows], "offset": offset, "limit": limit}


@app.post("/api/clips/{clip_id}/ban")
def clip_ban(clip_id: int, undo: bool = False):
    with db.connect() as conn:
        cur = conn.execute("UPDATE clips SET banned = ? WHERE id = ?", (0 if undo else 1, clip_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "no such clip")
    return {"ok": True, "id": clip_id, "banned": not undo}


@app.post("/api/clips/{clip_id}/played")
def clip_played(clip_id: int):
    with db.connect() as conn:
        conn.execute("UPDATE clips SET plays = plays + 1 WHERE id = ?", (clip_id,))
    return {"ok": True}


@app.get("/api/sources")
def sources(limit: int = Query(100, ge=1, le=1000)):
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT s.*, (SELECT COUNT(*) FROM clips c WHERE c.source_id = s.id AND c.banned = 0) AS clip_count "
            "FROM sources s ORDER BY s.id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["tags"] = db.tags_from_db(d.get("tags"))
            out.append(d)
        return {"sources": out}


@app.get("/api/jobs")
def jobs_list(limit: int = Query(50, ge=1, le=500)):
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["tags"] = db.tags_from_db(d.get("tags"))
            out.append(d)
        return {"jobs": out, "providers": PROVIDER_NAMES}


@app.post("/api/jobs", status_code=201)
def jobs_create(job: JobIn):
    if not (job.query or job.url) and job.provider != "local":
        raise HTTPException(400, "query or url is required")
    try:
        job_id = create_job(job.provider, job.query, job.url, job.max_items, job.tags)
    except ProviderError as e:
        raise HTTPException(400, str(e))
    return {"id": job_id, "status": "queued"}


@app.post("/api/jobs/{job_id}/cancel")
def jobs_cancel(job_id: int):
    with db.connect() as conn:
        cur = conn.execute("UPDATE jobs SET status = 'cancelled', updated_at = datetime('now') "
                           "WHERE id = ? AND status IN ('queued', 'running')", (job_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "job not found or already finished")
    return {"ok": True}


@app.post("/api/seed")
def seed(set: str = "contemporary"):
    from .seeds import SEED_SETS
    jobs_list = SEED_SETS.get(set)
    if jobs_list is None:
        raise HTTPException(400, f"unknown set {set!r}; use contemporary, archival or all")
    ids = [create_job(j["provider"], j.get("query"), j.get("url"), j.get("max_items", 5), j.get("tags")) for j in jobs_list]
    return {"queued": ids, "set": set}


@app.get("/")
def index():
    return FileResponse(config.WEB_DIR / "index.html")


@app.exception_handler(ProviderError)
async def provider_error(_, exc: ProviderError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


config.ensure_dirs()
# Only the public subfolders are served: the database, the inbox and in-flight downloads also live under media/.
for sub in ("segments", "thumbs"):
    app.mount(f"/media/{sub}", StaticFiles(directory=str(config.MEDIA_DIR / sub)), name=f"media-{sub}")
app.mount("/web", StaticFiles(directory=str(config.WEB_DIR)), name="web")
