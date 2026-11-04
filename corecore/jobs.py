"""Ingest jobs: a tiny persistent queue in SQLite and a worker thread that drains it."""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from . import db
from .ingest import ingest_candidate
from .providers import ProviderError, get_provider

log = logging.getLogger("corecore.jobs")


def create_job(provider: str, query: str | None, url: str | None, max_items: int, tags: list[str] | str | None) -> int:
    get_provider(provider)  # validates the name early
    with db.connect() as conn:
        cur = conn.execute("INSERT INTO jobs (provider, query, url, max_items, tags) VALUES (?, ?, ?, ?, ?)",
                           (provider, query or None, url or None, int(max_items), db.tags_to_db(tags)))
        return cur.lastrowid


def _update(job_id: int, **fields) -> None:
    cols = ", ".join(f"{k} = ?" for k in fields)
    with db.connect() as conn:
        conn.execute(f"UPDATE jobs SET {cols}, updated_at = datetime('now') WHERE id = ?", (*fields.values(), job_id))


def _status(job_id: int) -> str | None:
    with db.connect() as conn:
        row = conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return row["status"] if row else None


def run_job(job_id: int, echo: Callable[[str], None] | None = None) -> None:
    with db.connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job is None:
        return

    def logger(msg: str) -> None:
        log.info("job %s: %s", job_id, msg)
        if echo:
            echo(msg)
        _update(job_id, message=msg[:300])

    def cancelled() -> bool:
        return _status(job_id) == "cancelled"

    _update(job_id, status="running", progress=0.0, message="searching")
    tags = db.tags_from_db(job["tags"])
    try:
        provider = get_provider(job["provider"])
        cands = provider.search(job["query"], job["url"], int(job["max_items"]))
    except Exception as e:  # noqa: BLE001
        _update(job_id, status="failed", message=f"search failed: {e}"[:300])
        log.exception("job %s search failed", job_id)
        return
    if not cands:
        _update(job_id, status="done", progress=1.0, message="no candidates found")
        return
    logger(f"{len(cands)} candidate(s)")
    added = 0
    for i, cand in enumerate(cands):
        if cancelled():
            _update(job_id, message="cancelled")
            return
        try:
            added += ingest_candidate(cand, tags, query=job["query"] or job["url"] or "", logger=logger,
                                      should_cancel=cancelled)
        except Exception as e:  # noqa: BLE001
            logger(f"error: {e}")
        _update(job_id, progress=(i + 1) / len(cands), clips_added=added)
    if cancelled():
        _update(job_id, message="cancelled")
        return
    _update(job_id, status="done", progress=1.0, clips_added=added, message=f"done: {added} clips added")


def claim_next() -> int | None:
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT id FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1").fetchone()
        if row is None:
            conn.execute("COMMIT")
            return None
        conn.execute("UPDATE jobs SET status = 'running', updated_at = datetime('now') WHERE id = ?", (row["id"],))
        conn.execute("COMMIT")
        return row["id"]


class Worker(threading.Thread):
    """Drains queued jobs one at a time. Start one per process; ffmpeg already uses all the cores."""

    def __init__(self) -> None:
        super().__init__(name="corecore-worker", daemon=True)
        self.stop_event = threading.Event()

    def run(self) -> None:
        # jobs left 'running' by a previous crashed process go back to the queue
        with db.connect() as conn:
            conn.execute("UPDATE jobs SET status = 'queued' WHERE status = 'running'")
        while not self.stop_event.is_set():
            job_id = claim_next()
            if job_id is None:
                self.stop_event.wait(1.5)
                continue
            try:
                run_job(job_id)
            except Exception:  # noqa: BLE001
                log.exception("job %s crashed", job_id)
                _update(job_id, status="failed", message="crashed; see server log")
            if not self.stop_event.is_set():
                time.sleep(0.2)

    def stop(self) -> None:
        self.stop_event.set()
