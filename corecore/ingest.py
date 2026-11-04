"""Turn a candidate video into a handful of short, normalized clips in the pool."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

from . import config, db, faces, ffmpeg
from .providers import Candidate, get_provider

log = logging.getLogger("corecore.ingest")

Logger = Callable[[str], None]


def auto_tags(stats: dict, info: dict, loud: float | None) -> list[str]:
    """Cheap descriptive tags derived from the pixels, so the sequencer can contrast clips without any ML."""
    tags = []
    b, s, m = stats.get("brightness"), stats.get("saturation"), stats.get("motion")
    if b is not None:
        tags.append("dark" if b < 0.25 else "bright" if b > 0.6 else "mid")
    if s is not None:
        tags.append("muted" if s < 0.12 else "vivid" if s > 0.35 else "")
    if m is not None:
        tags.append("still" if m < 0.012 else "motion" if m > 0.05 else "")
    if info.get("has_audio"):
        tags.append("audio")
        if loud is not None and loud > -20:
            tags.append("loud")
    if info.get("height", 0) > info.get("width", 0):
        tags.append("vertical")
    return [t for t in tags if t]


def ingest_candidate(cand: Candidate, tags: list[str], *, query: str = "", logger: Logger = log.info,
                     should_cancel: Callable[[], bool] = lambda: False) -> int:
    """Download, detect shots, cut clips, compute stats, store. Returns the number of clips added."""
    config.ensure_dirs()
    provider = get_provider(cand.provider)
    conn = db.connect()
    try:
        row = conn.execute("SELECT id, status FROM sources WHERE provider = ? AND external_id = ?",
                           (cand.provider, cand.external_id)).fetchone()
        if row and row["status"] == "done":
            logger(f"skip (already ingested): {cand.title or cand.external_id}")
            return 0
        if row:
            source_id = row["id"]
            conn.execute("UPDATE sources SET status = 'pending', error = NULL, query = ?, tags = ? WHERE id = ?",
                         (query, db.tags_to_db(tags), source_id))
            conn.execute("DELETE FROM clips WHERE source_id = ?", (source_id,))
        else:
            cur = conn.execute(
                "INSERT INTO sources (provider, external_id, url, title, uploader, duration, license, query, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cand.provider, cand.external_id, cand.url, cand.title, cand.uploader, cand.duration, cand.license,
                 query, db.tags_to_db(tags)))
            source_id = cur.lastrowid

        path: Path | None = None
        added = 0
        try:
            path = provider.download(cand, config.SOURCES_DIR, logger)
            info = ffmpeg.probe(path)
            if info["duration"] > config.MAX_SOURCE_DURATION:
                raise RuntimeError(f"source too long ({info['duration']:.0f}s)")
            logger(f"detecting shots in {cand.title or path.name} ({info['duration']:.0f}s)")
            cuts = ffmpeg.detect_shots(path)
            shots = ffmpeg.shots_from_cuts(info["duration"], cuts)
            shots = ffmpeg.spread(shots, config.MAX_CLIPS_PER_SOURCE)
            logger(f"{len(cuts)} cuts -> {len(shots)} clips")
            for i, (start, length) in enumerate(shots):
                if should_cancel():
                    break
                stem = f"{source_id}_{i:03d}"
                seg = config.SEGMENTS_DIR / f"{stem}.{config.SEGMENT_FORMAT}"
                thumb = config.THUMBS_DIR / f"{stem}.jpg"
                try:
                    ffmpeg.cut_segment(path, start, length, seg, has_audio=info["has_audio"])
                    seg_info = ffmpeg.probe(seg)
                    ffmpeg.thumbnail(seg, min(0.5, max(0.0, seg_info["duration"] / 2)), thumb)
                    stats = ffmpeg.frame_stats(seg)
                    loud = ffmpeg.loudness(seg) if seg_info["has_audio"] else None
                    n_faces = faces.faces_in_clip(seg, seg_info["duration"])
                except ffmpeg.FFmpegError as e:
                    logger(f"clip {stem} failed: {e}")
                    for p in (seg, thumb):
                        if p.exists():
                            p.unlink()
                    continue
                clip_tags = list(tags) + [cand.provider] + auto_tags(stats, seg_info, loud)
                if n_faces:
                    clip_tags.append("faces")
                conn.execute(
                    "INSERT INTO clips (source_id, file, thumb, start, duration, width, height, has_audio, brightness, "
                    "saturation, motion, loudness, faces, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (source_id, f"segments/{seg.name}", f"thumbs/{thumb.name}", start, seg_info["duration"],
                     seg_info["width"], seg_info["height"], int(seg_info["has_audio"]), stats["brightness"],
                     stats["saturation"], stats["motion"], loud, n_faces, db.tags_to_db(clip_tags)))
                added += 1
            conn.execute("UPDATE sources SET status = 'done', duration = COALESCE(duration, ?) WHERE id = ?",
                         (info["duration"], source_id))
            logger(f"added {added} clips from {cand.title or cand.external_id}")
        except Exception as e:  # noqa: BLE001 - one bad source must not kill the job
            conn.execute("UPDATE sources SET status = 'failed', error = ? WHERE id = ?", (str(e)[:500], source_id))
            logger(f"failed: {cand.title or cand.external_id}: {e}")
        finally:
            if path and path.exists() and not config.KEEP_SOURCES and not cand.extra.get("keep"):
                try:
                    os.remove(path)
                except OSError:
                    pass
        return added
    finally:
        conn.close()
