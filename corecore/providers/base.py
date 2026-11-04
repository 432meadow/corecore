from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


class ProviderError(RuntimeError):
    pass


@dataclass
class Candidate:
    provider: str
    external_id: str
    url: str
    title: str = ""
    uploader: str = ""
    duration: float | None = None
    license: str = ""
    extra: dict = field(default_factory=dict)


Logger = Callable[[str], None]


class Provider:
    name = "base"

    def search(self, query: str | None, url: str | None, max_items: int) -> list[Candidate]:
        raise NotImplementedError

    def download(self, cand: Candidate, dest_dir: Path, log: Logger) -> Path:
        """Fetch the candidate into dest_dir and return the local path. Set cand.extra['keep'] = True
        when the file is not ours to delete (e.g. the user's own footage)."""
        raise NotImplementedError
