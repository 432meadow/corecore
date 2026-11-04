"""Starter ingest jobs: Internet Archive queries chosen for the material corecore edits lean on. Mostly the
Prelinger Archives (public-domain ephemeral films: ads, suburbs, industry, civil defence, hygiene films),
plus NASA and community uploads. Tags are the sequencer's contrast vocabulary (see CONTRAST_PAIRS in
web/sequencer.js), so each query carries the themes its footage will be cut against.

These are suggestions, not a curated dataset: search results shift, and not every item has an mp4
derivative. `python -m corecore seed` queues them; the CI build runs them within a time budget."""

STARTER_JOBS = [
    # consumerism / ads / home
    {"provider": "archive", "query": "collection:prelinger AND subject:(television commercials OR advertising)",
     "max_items": 5, "tags": ["archive", "ads", "consumerism"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(shopping OR supermarkets OR department stores)",
     "max_items": 4, "tags": ["archive", "consumerism", "crowd"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(suburbs OR family life OR home)",
     "max_items": 5, "tags": ["archive", "home", "childhood"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(teenagers OR dating OR etiquette)",
     "max_items": 4, "tags": ["archive", "childhood", "faces"]},
    # work / industry / machines
    {"provider": "archive", "query": "collection:prelinger AND subject:(industry OR factories OR manufacturing OR steel)",
     "max_items": 5, "tags": ["archive", "industry", "work", "machines"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(agriculture OR farming OR food)",
     "max_items": 3, "tags": ["archive", "nature", "work"]},
    # fear / war
    {"provider": "archive", "query": "collection:prelinger AND subject:(civil defense OR atomic OR nuclear)",
     "max_items": 4, "tags": ["archive", "war", "fear"]},
    # city / traffic / crowds
    {"provider": "archive", "query": "collection:prelinger AND subject:(cities OR traffic OR highways OR automobiles)",
     "max_items": 5, "tags": ["archive", "city", "traffic"]},
    # screens / tech / future
    {"provider": "archive", "query": "collection:prelinger AND subject:(computers OR television OR future OR automation)",
     "max_items": 4, "tags": ["archive", "screens", "future"]},
    {"provider": "archive", "query": "collection:computerchronicles", "max_items": 3,
     "tags": ["archive", "screens", "tech", "voice"]},
    # faces / voice
    {"provider": "archive", "query": "collection:prelinger AND subject:(mental health OR psychology OR hygiene)",
     "max_items": 4, "tags": ["archive", "faces", "voice"]},
    {"provider": "archive", "query": "collection:newsandpublicaffairs AND subject:(news)", "max_items": 3,
     "tags": ["news", "voice", "modern"]},
    # space / earth / nature
    {"provider": "archive", "query": "collection:nasa AND (subject:(apollo) OR subject:(earth) OR subject:(shuttle))",
     "max_items": 5, "tags": ["space", "earth"]},
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(nature OR wildlife OR ocean OR forest)",
     "max_items": 5, "tags": ["nature"]},
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(timelapse OR time-lapse)",
     "max_items": 4, "tags": ["city", "time", "modern"]},
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(surveillance OR cctv OR dashcam)",
     "max_items": 3, "tags": ["cctv", "modern"]},
]
