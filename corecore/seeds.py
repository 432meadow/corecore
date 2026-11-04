"""Starter ingest jobs, in two sets.

ARCHIVAL_JOBS: Internet Archive queries chosen for the material corecore edits lean on. Mostly the
Prelinger Archives (public-domain ephemeral films: ads, suburbs, industry, civil defence, hygiene films),
plus NASA and community uploads. Tags are the sequencer's contrast vocabulary (see CONTRAST_PAIRS in
web/sequencer.js), so each query carries the themes its footage will be cut against.

These are suggestions, not a curated dataset: search results shift, and not every item has an mp4
derivative. `python -m corecore seed` queues them; the CI build runs them within a time budget."""

ARCHIVAL_JOBS = [
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


# CONTEMPORARY_JOBS: internet-native material. The Internet Archive's `mirrortube` collection holds about two
# million YouTube videos people archived (920k from 2022 on), with H.264 files: dashcams, vlogs, walking tours,
# driving POVs, game clips, pets, raw footage. Queries use quoted phrases (the archive's search treats
# `dash cam` as dash OR cam), newest-first ordering, and the title blocklist in config.py. These are other
# people's uploads: fine for a personal pool, your call for anything you publish.
_MT = "collection:mirrortube AND "
_NEW = " |sort=date desc"
CONTEMPORARY_JOBS = [
    {"provider": "archive", "query": _MT + 'title:("dash cam" OR dashcam)' + _NEW, "max_items": 6,
     "tags": ["dashcam", "traffic", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(dashcam OR "dash cam") AND title:(russia OR russian OR winter OR snow OR compilation)' + _NEW,
     "max_items": 4, "tags": ["dashcam", "traffic", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("driving pov" OR "drive with me" OR "driving in" OR "night drive")' + _NEW,
     "max_items": 4, "tags": ["traffic", "city", "modern"]},
    {"provider": "archive", "query": _MT + "title:(vlog) AND date:[2022-01-01 TO 2029-12-31]" + _NEW, "max_items": 6,
     "tags": ["vlog", "faces", "home", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("day in my life" OR "day in the life" OR "morning routine" OR "come with me")' + _NEW,
     "max_items": 5, "tags": ["vlog", "home", "faces", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("walking tour" OR "night walk" OR "4k walk" OR "walk in")' + _NEW,
     "max_items": 5, "tags": ["city", "crowd", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("caught on camera" OR "security camera" OR "ring doorbell" OR cctv)' + _NEW,
     "max_items": 4, "tags": ["cctv", "modern", "fear"]},
    {"provider": "archive", "query": _MT + "title:(asmr)" + _NEW, "max_items": 4, "tags": ["asmr", "faces", "quiet", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("time lapse" OR timelapse OR hyperlapse OR drone)' + _NEW, "max_items": 4,
     "tags": ["city", "nature", "time", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(minecraft OR fortnite OR roblox OR "gta 5") AND title:(funny OR moments OR fail OR glitch)' + _NEW,
     "max_items": 4, "tags": ["screens", "games", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("raw footage" OR "raw video") AND date:[2023-01-01 TO 2029-12-31]' + _NEW,
     "max_items": 4, "tags": ["news", "modern", "crowd"]},
    {"provider": "archive", "query": _MT + 'title:(grocery OR supermarket OR walmart OR costco OR "shopping")' + _NEW,
     "max_items": 4, "tags": ["consumerism", "crowd", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("my cat" OR "my dog" OR kitten OR puppy OR "funny animals")' + _NEW,
     "max_items": 4, "tags": ["animals", "home", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("oddly satisfying" OR satisfying OR relaxing OR ambient)' + _NEW,
     "max_items": 4, "tags": ["quiet", "still", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("first day" OR "last day" OR "we moved" OR "moving out" OR goodbye)' + _NEW,
     "max_items": 4, "tags": ["home", "faces", "modern"]},
    # Dailymotion search (public API); downloads need yt-dlp's impersonation extra, see README
    {"provider": "dailymotion", "query": "russian dashcam compilation", "max_items": 3, "tags": ["dashcam", "traffic", "modern"]},
    {"provider": "dailymotion", "query": "caught on dashcam", "max_items": 3, "tags": ["dashcam", "traffic", "modern"]},
]

SEED_SETS = {"contemporary": CONTEMPORARY_JOBS, "archival": ARCHIVAL_JOBS, "all": CONTEMPORARY_JOBS + ARCHIVAL_JOBS}
STARTER_JOBS = CONTEMPORARY_JOBS  # what `seed` and `build-site` use unless --set says otherwise
