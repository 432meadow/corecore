"""SQLite storage for sources, clips and ingest jobs. One connection per call; WAL mode."""
from __future__ import annotations

import random
import sqlite3
from collections import Counter
from typing import Iterable

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  provider TEXT NOT NULL,
  external_id TEXT NOT NULL,
  url TEXT,
  title TEXT,
  uploader TEXT,
  duration REAL,
  license TEXT,
  query TEXT,
  tags TEXT DEFAULT ',',
  status TEXT DEFAULT 'pending',
  error TEXT,
  audited INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(provider, external_id)
);
CREATE TABLE IF NOT EXISTS clips (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  file TEXT NOT NULL,
  thumb TEXT,
  start REAL,
  duration REAL,
  width INTEGER,
  height INTEGER,
  has_audio INTEGER DEFAULT 0,
  brightness REAL,
  saturation REAL,
  motion REAL,
  loudness REAL,
  tags TEXT DEFAULT ',',
  faces INTEGER DEFAULT 0,
  banned INTEGER DEFAULT 0,
  plays INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS clips_source ON clips(source_id);
CREATE INDEX IF NOT EXISTS clips_banned ON clips(banned);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY,
  provider TEXT NOT NULL,
  query TEXT,
  url TEXT,
  max_items INTEGER DEFAULT 5,
  tags TEXT DEFAULT ',',
  status TEXT DEFAULT 'queued',
  progress REAL DEFAULT 0,
  message TEXT DEFAULT '',
  clips_added INTEGER DEFAULT 0,
  owner TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(clips)")}
        if "faces" not in cols:  # databases created before face tagging existed
            conn.execute("ALTER TABLE clips ADD COLUMN faces INTEGER DEFAULT 0")
        jcols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
        if "owner" not in jcols:
            conn.execute("ALTER TABLE jobs ADD COLUMN owner TEXT")
        scols = {r["name"] for r in conn.execute("PRAGMA table_info(sources)")}
        if "audited" not in scols:  # sources scraped before the hard blocklist checked descriptions
            conn.execute("ALTER TABLE sources ADD COLUMN audited INTEGER DEFAULT 0")


# Tags are stored as ",a,b,c," so that `tags LIKE '%,a,%'` is an exact-token match.
def tags_to_db(tags: Iterable[str] | str | None) -> str:
    if tags is None:
        return ","
    if isinstance(tags, str):
        tags = tags.split(",")
    clean = []
    for t in tags:
        t = t.strip().lower().replace(" ", "-")
        if t and t not in clean:
            clean.append(t)
    return "," + ",".join(clean) + "," if clean else ","


def tags_from_db(s: str | None) -> list[str]:
    return [t for t in (s or "").split(",") if t]


def tag_like(tag: str) -> str | None:
    """LIKE pattern matching exactly one stored tag token. Normalised like storage, with the LIKE
    metacharacters escaped (use with `LIKE ? ESCAPE '\\'`)."""
    norm = tags_from_db(tags_to_db([tag]))
    if not norm:
        return None
    t = norm[0].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%,{t},%"


def sample_clips(conn: sqlite3.Connection, n: int = 100, tags: list[str] | None = None,
                 exclude: list[int] | None = None, seed: int | None = None) -> list[sqlite3.Row]:
    """Random sample of playable clips, joined with their source. A seed makes the order repeatable
    over an unchanged pool (a seeded shuffle of the matching ids)."""
    where = ["c.banned = 0"]
    params: list = []
    if tags:
        patterns = [p for p in (tag_like(t) for t in tags) if p]
        if not patterns:
            return []
        where.append("(" + " OR ".join("c.tags LIKE ? ESCAPE '\\'" for _ in patterns) + ")")
        params.extend(patterns)
    if exclude:
        exclude = [int(x) for x in exclude][:2000]
        where.append(f"c.id NOT IN ({','.join('?' * len(exclude))})")
        params.extend(exclude)
    select = ("SELECT c.*, s.title AS source_title, s.uploader AS source_uploader, s.url AS source_url, "
              "s.provider AS provider, s.license AS license FROM clips c JOIN sources s ON s.id = c.source_id")
    if seed is None:
        return conn.execute(f"{select} WHERE {' AND '.join(where)} ORDER BY RANDOM() LIMIT ?", [*params, int(n)]).fetchall()
    ids = [r[0] for r in conn.execute(f"SELECT c.id FROM clips c WHERE {' AND '.join(where)} ORDER BY c.id", params)]
    random.Random(int(seed)).shuffle(ids)
    ids = ids[: int(n)]
    if not ids:
        return []
    rows = conn.execute(f"{select} WHERE c.id IN ({','.join('?' * len(ids))})", ids).fetchall()
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def clip_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = tags_from_db(d.get("tags"))
    d["url"] = f"/media/{d['file']}"
    d["thumb_url"] = f"/media/{d['thumb']}" if d.get("thumb") else None
    d["has_audio"] = bool(d.get("has_audio"))
    return d


def stats(conn: sqlite3.Connection) -> dict:
    clips = conn.execute("SELECT COUNT(*) FROM clips WHERE banned = 0").fetchone()[0]
    banned = conn.execute("SELECT COUNT(*) FROM clips WHERE banned = 1").fetchone()[0]
    sources = conn.execute("SELECT COUNT(*) FROM sources WHERE status = 'done'").fetchone()[0]
    total_seconds = conn.execute("SELECT COALESCE(SUM(duration), 0) FROM clips WHERE banned = 0").fetchone()[0]
    counter: Counter[str] = Counter()
    for (tags,) in conn.execute("SELECT tags FROM clips WHERE banned = 0"):
        counter.update(tags_from_db(tags))
    with_audio = conn.execute("SELECT COUNT(*) FROM clips WHERE banned = 0 AND has_audio = 1").fetchone()[0]
    return {
        "clips": clips,
        "banned": banned,
        "sources": sources,
        "seconds": round(total_seconds, 1),
        "with_audio": with_audio,
        "tags": dict(counter.most_common()),
    }
