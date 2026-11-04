"""Local files: anything you drop into media/inbox (or a directory / glob you point it at)."""
from __future__ import annotations

import glob
from pathlib import Path

from .. import config
from .base import Candidate, Logger, Provider, ProviderError


def allowed(path: Path) -> bool:
    """Only paths under an allowed root may be ingested: an unauthenticated POST /api/jobs must not be able to
    read arbitrary files on the host."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in config.LOCAL_ROOTS:
        try:
            if resolved.is_relative_to(root.resolve()):
                return True
        except OSError:
            continue
    return False


class LocalProvider(Provider):
    name = "local"

    def search(self, query: str | None, url: str | None, max_items: int) -> list[Candidate]:
        target = (url or query or "").strip()
        if target.startswith("file://"):
            target = target[len("file://"):]
        base = Path(target).expanduser() if target else config.INBOX_DIR
        if base.is_dir():
            files = sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in config.VIDEO_EXTENSIONS
                           and not any(part.startswith(".") for part in p.relative_to(base).parts))
        elif base.is_file():
            if base.suffix.lower() not in config.VIDEO_EXTENSIONS:
                raise ProviderError(f"{base.name} is not a video file")
            files = [base]
        else:
            files = sorted(Path(p) for p in glob.glob(str(base), recursive=True)
                           if Path(p).is_file() and Path(p).suffix.lower() in config.VIDEO_EXTENSIONS)
        files = [f for f in files if allowed(f)]
        if not files:
            raise ProviderError(f"no video files found at {base} (the local provider only reads media/inbox and "
                                f"CORECORE_LOCAL_ROOTS; the CLI may pass any path)")
        if max_items > 0:
            files = files[:max_items]
        return [Candidate("local", str(p.resolve()), p.resolve().as_uri(), title=p.stem, extra={"keep": True})
                for p in files]

    def download(self, cand: Candidate, dest_dir: Path, log: Logger) -> Path:
        cand.extra["keep"] = True
        return Path(cand.external_id)
