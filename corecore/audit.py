"""Removes footage the piece must never show from the pool itself: every clip of a source whose title or
uploader, or (for Internet Archive items) description and subjects, name Hitler, the Nazis, fascism or the
world wars (config.HARD_BLOCKLIST). Those clips are banned and their files deleted, so no later export can
bring them back. Each archive item is looked up once; the flag is kept in sources.audited."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from . import config, db


def remove_source(conn, source_id: int, reason: str) -> int:
    rows = conn.execute("SELECT id, file, thumb FROM clips WHERE source_id = ? AND banned = 0", (source_id,)).fetchall()
    for r in rows:
        for rel in (r["file"], r["thumb"]):
            if rel:
                try:
                    (config.MEDIA_DIR / rel).unlink()
                except FileNotFoundError:
                    pass
    conn.execute("UPDATE clips SET banned = 1 WHERE source_id = ?", (source_id,))
    conn.execute("UPDATE sources SET status = 'blocked', error = ?, audited = 1 WHERE id = ?", (reason, source_id))
    return len(rows)


def audit(fetch: Callable[[str], dict] | None = None, workers: int = 8, log: Callable[[str], None] = print) -> dict:
    from .providers.archive import fetch_metadata, hard_blocked_metadata
    fetch = fetch or fetch_metadata
    removed_sources = removed_clips = checked = unreachable = 0
    with db.connect() as conn:
        rows = conn.execute("SELECT id, provider, external_id, title, uploader, audited FROM sources "
                            "WHERE status != 'blocked'").fetchall()
        pending = []
        for r in rows:  # titles and uploaders, every provider, no network
            if config.hard_blocked(f"{r['title'] or ''} {r['uploader'] or ''}"):
                removed_clips += remove_source(conn, r["id"], "hard blocklist: title or uploader")
                removed_sources += 1
                log(f"removed: {r['title']} ({r['uploader'] or 'no uploader'})")
            elif not r["audited"]:
                if r["provider"] == "archive":
                    pending.append(r)
                else:
                    conn.execute("UPDATE sources SET audited = 1 WHERE id = ?", (r["id"],))

        def look(r):
            try:
                return r, fetch(r["external_id"])
            except Exception as e:  # network trouble: try again on the next audit
                return r, e

        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:  # descriptions and subjects, once per item
            for r, md in ex.map(look, pending):
                if isinstance(md, Exception):
                    unreachable += 1
                    continue
                checked += 1
                if hard_blocked_metadata(md):
                    removed_clips += remove_source(conn, r["id"], "hard blocklist: description or subjects")
                    removed_sources += 1
                    log(f"removed: {r['title']} ({r['uploader'] or 'no uploader'}), named in its description or subjects")
                else:
                    conn.execute("UPDATE sources SET audited = 1 WHERE id = ?", (r["id"],))
    return {"looked_up": checked, "unreachable": unreachable, "sources_removed": removed_sources, "clips_removed": removed_clips}
