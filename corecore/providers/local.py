"""Local files: anything you drop into media/inbox (or a directory / glob you point it at)."""
from __future__ import annotations

import glob
from pathlib import Path

from .. import config
from .base import Candidate, Logger, Provider, ProviderError


class LocalProvider(Provider):
    name = "local"

    def search(self, query: str | None, url: str | None, max_items: int) -> list[Candidate]:
        target = (url or query or "").strip()
        if target.startswith("file://"):
            target = target[len("file://"):]
        base = Path(target).expanduser() if target else config.INBOX_DIR
        if base.is_dir():
            files = sorted(p for p in base.rglob("*") if p.suffix.lower() in config.VIDEO_EXTENSIONS)
        elif base.is_file():
            files = [base]
        else:
            files = sorted(Path(p) for p in glob.glob(str(base), recursive=True)
                           if Path(p).suffix.lower() in config.VIDEO_EXTENSIONS)
        if not files:
            raise ProviderError(f"no video files found at {base}")
        if max_items > 0:
            files = files[:max_items]
        return [Candidate("local", str(p.resolve()), p.resolve().as_uri(), title=p.stem, extra={"keep": True})
                for p in files]

    def download(self, cand: Candidate, dest_dir: Path, log: Logger) -> Path:
        cand.extra["keep"] = True
        return Path(cand.external_id)
