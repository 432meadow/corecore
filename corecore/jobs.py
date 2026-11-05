"""Ingest jobs: a tiny persistent queue in SQLite and a worker thread that drains it."""
from __future__ import annotations

import logging
import os
import socket
import threading
import time
from typing import Callable

from . import config, db
from .ingest import ingest_candidate
from .providers import ProviderError, get_provider

log = logging.getLogger("corecore.jobs")


def create_job(provider: str, query: str | None, url: str | None, max_items: int, tags: list[str] | str | None) -> int:
    get_provider(provider)  # validates the name early
    with db.connect() as conn:
        cur = conn.execute("INSERT INTO jobs (provider, query, url, max_items, tags) VALUES (?, ?, ?, ?, ?)",
                           (provider, query or None, url or None, int(max_items), db.tags_to_db(tags)))
        return cur.lastrowid


def owner_token() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def owner_alive(token: str | None) -> bool:
    """A 'running' job is only stale if its owner process is gone. Other hosts can't be checked: assume alive."""
    if not token or ":" not in token:
        return False
    host, _, pid = token.rpartition(":")
    if host != socket.gethostname() or not pid.isdigit():
        return True
    if int(pid) == os.getpid():
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _update(job_id: int, **fields) -> None:
    cols = ", ".join(f"{k} = ?" for k in fields)
    with db.connect() as conn:
        conn.execute(f"UPDATE jobs SET {cols}, updated_at = datetime('now') WHERE id = ?", (*fields.values(), job_id))


def _status(job_id: int) -> str | None:
    with db.connect() as conn:
        row = conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return row["status"] if row else None


def run_job(job_id: int, echo: Callable[[str], None] | None = None, deadline: float | None = None) -> None:
    """Run one job to completion. `deadline` is a time.monotonic() value after which the job stops early
    (it is then marked done with whatever it managed, which is what a CI build wants)."""
    with db.connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job is None:
        return

    def logger(msg: str) -> None:
        log.info("job %s: %s", job_id, msg)
        if echo:
            echo(msg)
        _update(job_id, message=msg[:300])

    def out_of_time() -> bool:
        return deadline is not None and time.monotonic() > deadline

    def cancelled() -> bool:
        return out_of_time() or _status(job_id) == "cancelled"

    _update(job_id, status="running", progress=0.0, message="searching", owner=owner_token())
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
        if out_of_time():
            _update(job_id, status="done", clips_added=added, message=f"stopped at time budget: {added} clips added")
            return
        if cancelled():
            _update(job_id, message="cancelled")
            return
        try:
            added += ingest_candidate(cand, tags, query=job["query"] or job["url"] or "", logger=logger,
                                      should_cancel=cancelled)
        except Exception as e:  # noqa: BLE001
            logger(f"error: {e}")
        _update(job_id, progress=(i + 1) / len(cands), clips_added=added)
    if out_of_time():
        _update(job_id, status="done", clips_added=added, message=f"stopped at time budget: {added} clips added")
        return
    if cancelled():
        _update(job_id, message="cancelled")
        return
    _update(job_id, status="done", progress=1.0, clips_added=added, message=f"done: {added} clips added")


def _cursor_file():
    return config.MEDIA_DIR / "starter_cursor.json"


def run_starter_jobs(time_budget: float, echo: Callable[[str], None] | None = None, seed_set: str = "contemporary") -> dict:
    """Run a curated starter list in the foreground within a time budget (used by `build-site` and CI).

    Each run picks up where the last one stopped: the cursor is kept with the pool, so a list longer than
    one budget is worked through over successive runs instead of its tail never running."""
    import json
    from . import seeds

    jobs_list = seeds.SEED_SETS.get(seed_set, seeds.STARTER_JOBS)
    try:
        cursors = json.loads(_cursor_file().read_text())
    except (OSError, ValueError):
        cursors = {}
    start = int(cursors.get(seed_set, 0)) % len(jobs_list) if jobs_list else 0
    order = jobs_list[start:] + jobs_list[:start]
    deadline = time.monotonic() + time_budget
    summary = {"jobs": 0, "clips": 0, "stopped_early": False, "set": seed_set, "from_job": start}
    for j in order:
        if time.monotonic() > deadline:
            summary["stopped_early"] = True
            break
        job_id = create_job(j["provider"], j.get("query"), j.get("url"), j.get("max_items", 5), j.get("tags"))
        if echo:
            echo(f"job {job_id}: {j['provider']} {j.get('query') or j.get('url')}")
        run_job(job_id, echo=echo, deadline=deadline)
        with db.connect() as conn:
            row = conn.execute("SELECT clips_added FROM jobs WHERE id = ?", (job_id,)).fetchone()
        summary["jobs"] += 1
        summary["clips"] += int(row["clips_added"] or 0)
    if jobs_list:
        cursors[seed_set] = (start + summary["jobs"]) % len(jobs_list)
        try:
            _cursor_file().write_text(json.dumps(cursors))
        except OSError:
            pass
    return summary


def run_reinstated(echo: Callable[[str], None] | None = None) -> dict:
    """Fetch again, by address, every source the owner put back (seeds.REINSTATED) that is not in the pool."""
    from . import seeds

    summary = {"fetched": 0, "clips": 0}
    for j in seeds.REINSTATED:
        ident = j["url"].rstrip("/").rsplit("/", 1)[-1]
        with db.connect() as conn:
            row = conn.execute("SELECT status FROM sources WHERE provider = ? AND external_id = ?",
                               (j["provider"], ident)).fetchone()
        if row and row["status"] == "done":
            continue
        job_id = create_job(j["provider"], None, j["url"], j.get("max_items", 1), j.get("tags"))
        if echo:
            echo(f"job {job_id}: putting back {j['url']}")
        run_job(job_id, echo=echo)
        with db.connect() as conn:
            r = conn.execute("SELECT clips_added FROM jobs WHERE id = ?", (job_id,)).fetchone()
        summary["fetched"] += 1
        summary["clips"] += int(r["clips_added"] or 0)
    return summary


def claim_next() -> int | None:
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT id FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1").fetchone()
        if row is None:
            conn.execute("COMMIT")
            return None
        conn.execute("UPDATE jobs SET status = 'running', owner = ?, updated_at = datetime('now') WHERE id = ?",
                     (owner_token(), row["id"]))
        conn.execute("COMMIT")
        return row["id"]


class Worker(threading.Thread):
    """Drains queued jobs one at a time. Start one per process; ffmpeg already uses all the cores."""

    def __init__(self) -> None:
        super().__init__(name="corecore-worker", daemon=True)
        self.stop_event = threading.Event()

    def run(self) -> None:
        # jobs left 'running' by a crashed process go back to the queue; jobs a live process owns are left alone
        with db.connect() as conn:
            for row in conn.execute("SELECT id, owner FROM jobs WHERE status = 'running'").fetchall():
                if not owner_alive(row["owner"]):
                    conn.execute("UPDATE jobs SET status = 'queued', owner = NULL WHERE id = ?", (row["id"],))
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
