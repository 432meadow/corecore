"""Starter ingest jobs. All Internet Archive queries, chosen for the kinds of material corecore edits lean on:
mid-century ephemeral films (ads, suburbs, industry, civil defence), space footage, nature, cities, screens.

These are suggestions, not a curated dataset: Internet Archive search results shift, and not every item has an
mp4 derivative. Run `python -m corecore seed` and let the worker chew through them, then prune in the UI."""

STARTER_JOBS = [
    # Prelinger Archives: public-domain ephemeral films. The spine of the archival look.
    {"provider": "archive", "query": "collection:prelinger AND subject:(television commercials)", "max_items": 6,
     "tags": ["archive", "ads", "consumerism"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(suburbs OR family OR home)", "max_items": 5,
     "tags": ["archive", "home", "childhood"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(industry OR factories OR manufacturing)",
     "max_items": 5, "tags": ["archive", "industry", "work"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(civil defense OR atomic OR nuclear)", "max_items": 4,
     "tags": ["archive", "war", "fear"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(cities OR traffic OR highways)", "max_items": 5,
     "tags": ["archive", "city", "traffic"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(computers OR television OR future)", "max_items": 4,
     "tags": ["archive", "screens", "future"]},
    # NASA and space agencies
    {"provider": "archive", "query": "collection:nasa AND (subject:(apollo) OR subject:(earth))", "max_items": 5,
     "tags": ["space", "earth"]},
    # Open community uploads
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(nature OR wildlife OR ocean)", "max_items": 5,
     "tags": ["nature"]},
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(timelapse OR time-lapse)", "max_items": 5,
     "tags": ["city", "time"]},
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(surveillance OR cctv OR dashcam)",
     "max_items": 4, "tags": ["cctv", "modern"]},
    {"provider": "archive", "query": "collection:computerchronicles", "max_items": 4,
     "tags": ["archive", "screens", "tech", "voice"]},
    {"provider": "archive", "query": "collection:newsandpublicaffairs AND subject:(news)", "max_items": 4,
     "tags": ["news", "voice", "modern"]},
]
