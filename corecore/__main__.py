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

    sub.add_parser("seed", help="queue the starter Internet Archive jobs")
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
        job_id = create_job(args.provider, args.query, args.url, args.max_items, args.tags)
        run_job(job_id, echo=lambda m: print(f"  {m}"))
        with db.connect() as conn:
            row = conn.execute("SELECT status, clips_added, message FROM jobs WHERE id = ?", (job_id,)).fetchone()
        print(f"job {job_id}: {row['status']} ({row['clips_added']} clips) {row['message']}")
        return 0 if row["status"] == "done" else 1

    if args.cmd == "seed":
        from .jobs import create_job
        from .seeds import STARTER_JOBS
        for j in STARTER_JOBS:
            jid = create_job(j["provider"], j.get("query"), j.get("url"), j.get("max_items", 5), j.get("tags"))
            print(f"queued job {jid}: {j['provider']} {j.get('query') or j.get('url')}")
        print("start `python -m corecore serve` (or `worker`) to run them")
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
