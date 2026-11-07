"""CLI: python -m corecore <serve|ingest|seed|worker|stats>"""
from __future__ import annotations

import argparse
import logging
import sys

from . import config, db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="corecore", description="corecore: endless found-footage montage")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("serve", help="run the web app (API + player + background ingest worker)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")

    p = sub.add_parser("ingest", help="scrape + clip footage right now, in the foreground")
    p.add_argument("--provider", default="archive", help="archive | ytdlp | local")
    p.add_argument("--query", "-q")
    p.add_argument("--url", "-u")
    p.add_argument("--max", "-n", type=int, default=5, dest="max_items")
    p.add_argument("--tags", "-t", default="", help="comma-separated tags, e.g. nature,archive")

    p = sub.add_parser("seed", help="queue a starter set of scrape jobs")
    p.add_argument("--set", default="contemporary", choices=["contemporary", "internet", "twitter", "beauty", "sunset", "archival", "all"], dest="seed_set")

    p = sub.add_parser("export", help="write the player + a bounded slice of the pool as a static site")
    p.add_argument("--out", default="site")
    p.add_argument("--height", type=int, default=None, help="re-encode clips taller than this (default: copy as is)")
    p.add_argument("--max-mb", type=float, default=450, dest="max_mb")
    p.add_argument("--sunset-mb", type=float, default=150, dest="sunset_mb", help="the sunset variation's own budget in MB, on top of --max-mb")
    p.add_argument("--max-clips", type=int, default=2000, dest="max_clips",
                   help="the most clips in each footage: the main mix, and the sunsets on top of it")
    p.add_argument("--tags", default="", help="export only clips with at least one of these comma-separated tags")

    p = sub.add_parser("build-site", help="scrape the starter list within a time budget, then export (what CI runs)")
    p.add_argument("--out", default="site")
    p.add_argument("--time-budget", type=float, default=1500, dest="time_budget", help="seconds of scraping before export")
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--max-mb", type=float, default=450, dest="max_mb")
    p.add_argument("--sunset-mb", type=float, default=150, dest="sunset_mb", help="the sunset variation's own budget in MB, on top of --max-mb")
    p.add_argument("--max-clips", type=int, default=2000, dest="max_clips",
                   help="the most clips in each footage: the main mix, and the sunsets on top of it")
    p.add_argument("--skip-ingest", action="store_true", dest="skip_ingest")
    p.add_argument("--set", default="contemporary", choices=["contemporary", "internet", "twitter", "beauty", "sunset", "archival", "all"], dest="seed_set")
    p.add_argument("--tags", default="", help="export only clips with at least one of these comma-separated tags")
    p.add_argument("--min-clips", type=int, default=0, dest="min_clips",
                   help="if the pool holds fewer clips than this, scrape for --fallback-budget seconds even when --time-budget is 0")
    p.add_argument("--fallback-budget", type=float, default=1200, dest="fallback_budget")
    p.add_argument("--pages", default="", help="result pages to take in turn within the budget, e.g. 1,2,4 (each "
                   "query takes the same number of items from each); default: the page in CORECORE_ARCHIVE_PAGE")

    p = sub.add_parser("audit", help="remove from the pool every source that names Hitler, the Nazis or the world wars")
    p.add_argument("--workers", type=int, default=8)
    sub.add_parser("tag-faces", help="(re)run face detection over the pool; needs opencv-python-headless")
    sub.add_parser("worker", help="run only the ingest worker (drain queued jobs)")
    sub.add_parser("stats", help="print pool statistics")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    config.ensure_dirs()
    db.init()

    if args.cmd == "serve":
        import uvicorn
        uvicorn.run("corecore.app:app", host=args.host, port=args.port, reload=args.reload, log_level="info")
        return 0

    if args.cmd == "ingest":
        from .jobs import create_job, run_job
        if args.provider in ("local", "file", "files", "inbox"):
            from pathlib import Path
            given = (args.url or args.query or "").replace("file://", "")
            if given:
                target = Path(given).expanduser()
                config.LOCAL_ROOTS.append(target if target.is_dir() else target.parent)
        job_id = create_job(args.provider, args.query, args.url, args.max_items, args.tags)
        run_job(job_id, echo=lambda m: print(f"  {m}"))
        with db.connect() as conn:
            row = conn.execute("SELECT status, clips_added, message FROM jobs WHERE id = ?", (job_id,)).fetchone()
        print(f"job {job_id}: {row['status']} ({row['clips_added']} clips) {row['message']}")
        return 0 if row["status"] == "done" else 1

    if args.cmd == "seed":
        from .jobs import create_job
        from .seeds import SEED_SETS
        for j in SEED_SETS[args.seed_set]:
            jid = create_job(j["provider"], j.get("query"), j.get("url"), j.get("max_items", 5), j.get("tags"))
            print(f"queued job {jid}: {j['provider']} {j.get('query') or j.get('url')}")
        print("start `python -m corecore serve` (or `worker`) to run them")
        return 0

    if args.cmd in ("export", "build-site"):
        from .export import export_site
        if args.cmd == "build-site" and not args.skip_ingest:
            from .jobs import run_reinstated, run_starter_jobs
            print(f"put back: {run_reinstated(echo=lambda m: print(f'  {m}'))}")
            budget = args.time_budget
            with db.connect() as conn:
                have = db.stats(conn)["clips"]
            if budget <= 0 and args.min_clips and have < args.min_clips:
                print(f"pool holds {have} clips (< {args.min_clips}); scraping for {args.fallback_budget:.0f}s")
                budget = args.fallback_budget
            if budget > 0:
                import os
                import time
                from .jobs import parse_pages
                deadline = time.monotonic() + budget
                for page in parse_pages(args.pages):
                    left = deadline - time.monotonic()
                    if left <= 0:
                        break
                    if page:   # the archive provider reads its page from here at every search
                        os.environ["CORECORE_ARCHIVE_PAGE"] = page
                    summary = run_starter_jobs(left, echo=lambda m: print(f"  {m}"), seed_set=args.seed_set)
                    print(f"ingest{f' (page {page})' if page else ''}: {summary}")
            else:
                print(f"ingest skipped: pool holds {have} clips")
        if args.cmd == "build-site":
            from .audit import audit
            print(f"audit: {audit(log=lambda m: print(f'  {m}'))}")
        result = export_site(args.out, height=args.height, max_bytes=int(args.max_mb * 1024 * 1024), max_clips=args.max_clips,
                             sunset_bytes=int(args.sunset_mb * 1024 * 1024),
                             tags=[t for t in args.tags.split(",") if t.strip()] or None)
        print(result)
        return 0

    if args.cmd == "audit":
        from .audit import audit
        print(audit(workers=args.workers))
        return 0

    if args.cmd == "tag-faces":
        from . import faces
        if not faces.available():
            print("opencv not available: pip install opencv-python-headless")
            return 1
        with db.connect() as conn:
            rows = conn.execute("SELECT id, file, duration, tags FROM clips").fetchall()
            for r in rows:
                n = faces.faces_in_clip(config.MEDIA_DIR / r["file"], r["duration"] or 0)
                tags = [t for t in db.tags_from_db(r["tags"]) if t != "faces"] + (["faces"] if n else [])
                conn.execute("UPDATE clips SET faces = ?, tags = ? WHERE id = ?", (n, db.tags_to_db(tags), r["id"]))
                print(f"clip {r['id']}: {n} face(s)")
        return 0

    if args.cmd == "worker":
        from .jobs import Worker
        w = Worker()
        w.start()
        print("worker running; ctrl-c to stop")
        try:
            while w.is_alive():
                w.join(1.0)
        except KeyboardInterrupt:
            w.stop()
        return 0

    if args.cmd == "stats":
        import json
        with db.connect() as conn:
            print(json.dumps(db.stats(conn), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
