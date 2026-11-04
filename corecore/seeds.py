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
    # Mirrored short-form uploads: TikTok (78k items), Instagram reels (11k), Twitter video (142k). Titles are
    # the original captions, so hashtag words work as queries. Short clips: a few shots each, many sources.
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(vlog OR dayinmylife OR \"day in my life\" OR grwm)" + _NEW,
     "max_items": 10, "tags": ["vlog", "faces", "home", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(dashcam OR driving OR roadtrip OR nightdrive)" + _NEW,
     "max_items": 8, "tags": ["dashcam", "traffic", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(asmr OR satisfying OR relaxing OR cleaning)" + _NEW,
     "max_items": 8, "tags": ["asmr", "quiet", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(cat OR dog OR kitten OR puppy)" + _NEW,
     "max_items": 8, "tags": ["animals", "home", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(pov OR \"a day\" OR walk OR city OR night)" + _NEW,
     "max_items": 8, "tags": ["city", "vlog", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:instagram-*" + _NEW, "max_items": 10,
     "tags": ["reels", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:twitter-* AND title:(dashcam OR cctv OR \"caught on\" OR doorbell)" + _NEW,
     "max_items": 8, "tags": ["cctv", "modern"]},
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
    {"provider": "archive", "query": _MT + 'title:("time lapse" OR timelapse OR hyperlapse OR "drone footage" OR "drone view" OR "4k drone")' + _NEW,
     "max_items": 4, "tags": ["city", "nature", "time", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(minecraft OR fortnite OR roblox OR "gta 5") AND title:(funny OR moments OR fail OR glitch)' + _NEW,
     "max_items": 4, "tags": ["screens", "games", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(grocery OR supermarket OR walmart OR costco OR "shopping")' + _NEW,
     "max_items": 4, "tags": ["consumerism", "crowd", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("my cat" OR "my dog" OR kitten OR puppy OR "funny animals")' + _NEW,
     "max_items": 4, "tags": ["animals", "home", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("oddly satisfying" OR satisfying OR relaxing OR ambient)' + _NEW,
     "max_items": 4, "tags": ["quiet", "still", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("first day" OR "last day" OR "we moved" OR "moving out" OR goodbye)' + _NEW,
     "max_items": 4, "tags": ["home", "faces", "modern"]},
    # More of the mundane and the strange: transit, weather, liminal places, work, animals, rituals, crowds.
    {"provider": "archive", "query": _MT + 'title:(train OR subway OR metro OR tram) AND title:(ride OR pov OR window OR "cab view")' + _NEW,
     "max_items": 5, "tags": ["traffic", "city", "modern", "transit"]},
    {"provider": "archive", "query": _MT + 'title:("plane window" OR takeoff OR landing OR "airport") AND title:(view OR pov OR timelapse OR walk)' + _NEW,
     "max_items": 4, "tags": ["traffic", "crowd", "modern", "transit"]},
    {"provider": "archive", "query": _MT + 'title:(rain OR snow OR fog OR thunderstorm OR "heavy rain") AND title:(walk OR drive OR window OR "4k" OR night)' + _NEW,
     "max_items": 5, "tags": ["nature", "quiet", "modern", "weather"]},
    {"provider": "archive", "query": _MT + 'title:(abandoned OR urbex OR liminal OR "empty mall" OR "dead mall")' + _NEW,
     "max_items": 5, "tags": ["liminal", "quiet", "modern", "fear"]},
    {"provider": "archive", "query": _MT + 'title:(laundromat OR "gas station" OR "parking lot" OR "convenience store" OR "24 hours" OR "3am")' + _NEW,
     "max_items": 4, "tags": ["liminal", "city", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(aquarium OR "fish tank" OR jellyfish OR "bird feeder" OR "trail cam")' + _NEW,
     "max_items": 4, "tags": ["animals", "quiet", "modern", "nature"]},
    {"provider": "archive", "query": _MT + 'title:("street food" OR "night market" OR "food stall" OR "what i eat")' + _NEW,
     "max_items": 4, "tags": ["crowd", "consumerism", "modern", "food"]},
    {"provider": "archive", "query": _MT + 'title:(skate OR skateboarding OR parkour OR bmx OR "longboard")' + _NEW,
     "max_items": 4, "tags": ["motion", "city", "modern", "faces"]},
    {"provider": "archive", "query": _MT + 'title:(factory OR "production line" OR "how it\'s made" OR warehouse OR "assembly line")' + _NEW,
     "max_items": 4, "tags": ["industry", "work", "machines", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("day in the life") AND title:(nurse OR driver OR worker OR teacher OR barista OR "delivery")' + _NEW,
     "max_items": 4, "tags": ["work", "vlog", "faces", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(graduation OR wedding OR "first day of school" OR "birthday party" OR "baby")' + _NEW,
     "max_items": 4, "tags": ["home", "childhood", "faces", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(concert OR festival OR "crowd" OR "mosh pit" OR "fireworks")' + _NEW,
     "max_items": 4, "tags": ["crowd", "modern", "noise"]},
    {"provider": "archive", "query": _MT + 'title:(karaoke OR "singing in the car" OR "car karaoke" OR "singing at")' + _NEW,
     "max_items": 3, "tags": ["faces", "voice", "home", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("live cam" OR webcam OR "earth cam" OR "beach cam" OR "harbor cam")' + _NEW,
     "max_items": 4, "tags": ["cctv", "quiet", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("screen recording" OR "desktop" OR "scrolling" OR "typing")' + _NEW,
     "max_items": 3, "tags": ["screens", "modern", "quiet"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(rain OR night OR fog OR snow OR sunset)" + _NEW,
     "max_items": 8, "tags": ["nature", "quiet", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(cooking OR recipe OR \"what i eat\" OR coffee)" + _NEW,
     "max_items": 6, "tags": ["home", "food", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(gym OR workout OR running OR \"morning run\")" + _NEW,
     "max_items": 6, "tags": ["faces", "motion", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(roadtrip OR \"road trip\" OR travel OR airport OR train)" + _NEW,
     "max_items": 6, "tags": ["traffic", "transit", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(thrift OR \"thrift store\" OR \"garage sale\" OR \"flea market\")" + _NEW,
     "max_items": 5, "tags": ["consumerism", "modern", "phone"]},
    # Dailymotion search (public API); downloads need yt-dlp's impersonation extra, see README
    {"provider": "dailymotion", "query": "russian dashcam compilation", "max_items": 3, "tags": ["dashcam", "traffic", "modern"]},
    {"provider": "dailymotion", "query": "caught on dashcam", "max_items": 3, "tags": ["dashcam", "traffic", "modern"]},
]

SEED_SETS = {"contemporary": CONTEMPORARY_JOBS, "archival": ARCHIVAL_JOBS, "all": CONTEMPORARY_JOBS + ARCHIVAL_JOBS}
STARTER_JOBS = CONTEMPORARY_JOBS  # what `seed` and `build-site` use unless --set says otherwise
