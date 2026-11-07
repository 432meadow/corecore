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
    # Beauty: kindness, subtle natural poignance, machines watching nature. The pool leans dark without it.
    # Title words on the mirror found games, manga dubs and news ("fox" gave Star Fox, "paid for" gave campaign
    # news, "blossom" gave product reviews), so these go to corners of the archive where the footage is what
    # it says: the park service's own camera work (public domain), Flickr's wildlife clips (CC BY), nature
    # centres' trail cameras, nest cams, a bear cam. The mirrors are kept to phrases junk rarely carries; the
    # short-form mirrors were dropped here, since half of what their wildlife hashtags found was sketches.
    {"provider": "archive", "query": 'identifier:nps-video-* AND creator:("Neal Herbert") AND NOT title:(what OR how OR why OR does OR has OR should OR when OR will OR program OR crowd OR "pre-show" OR fight OR visiting OR managing OR collaring OR "in depth" OR inside OR short OR vendors OR interview OR challenges OR kill OR carcass OR plowing OR webinar OR talk OR musical OR rumor OR equipment OR chase OR discusses OR ranger OR jams) |sort=downloads desc',
     "max_items": 12, "tags": ["nature", "animals", "light", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND title:(deer OR fawn OR fox OR owl OR owlet OR owlets OR heron OR egret OR squirrel OR raccoon OR hummingbird OR chickadee OR nuthatch OR woodpecker OR bluebird OR cardinal OR hedgehog OR badger OR "bird feeder" OR "bird bath" OR "trail camera" OR "game camera" OR "baby birds" OR "backyard birds" OR nestlings OR fledgling OR fledglings OR ducklings OR goslings OR "bird nest" OR "on the nest") AND NOT title:("owl city" OR albatross OR attacks OR prey OR preying OR shredding OR rat OR raid OR injured OR biologists OR "photo credit") |sort=downloads desc',
     "max_items": 12, "tags": ["nature", "animals", "trailcam", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'mediatype:movies AND NOT collection:mirrortube AND title:("trail cam" OR "trail camera" OR "trail cameras" OR trailcam OR "game camera" OR "game cam" OR "wildlife camera" OR "wildlife cam" OR "critter cam" OR "nature cam") AND NOT title:(godot OR petito OR review OR unboxing OR weird OR "fox den" OR volunteers OR "slide show" OR wakefield OR albatross OR switching) |sort=downloads desc',
     "max_items": 10, "tags": ["trailcam", "nature", "animals", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'mediatype:movies AND NOT collection:mirrortube AND title:("eagle cam" OR "osprey cam" OR "owl cam" OR "falcon cam" OR "heron cam" OR "nest cam" OR nestcam OR "nest box" OR "owl box" OR "hummingbird nest" OR "bluebird box" OR "eagle nest" OR "osprey nest" OR eaglets OR owlets OR "feeder cam" OR "hummingbird feeder") AND NOT title:("fox den" OR "bird box" OR news OR episode OR wakefield OR meeting OR council OR review OR challenge OR google OR team OR veranda OR elementary OR puts OR relocation OR plans OR renovations OR nowthis OR wearable OR "how to" OR install OR installing OR build OR prey OR shredding OR greeting OR attack OR attacks OR basketball OR baseball OR "orchard lake" OR "at home" OR "owl box in") |sort=downloads desc',
     "max_items": 8, "tags": ["trailcam", "nature", "animals", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'mediatype:movies AND NOT collection:mirrortube AND title:("Brooks Falls" OR "bear cam" OR bearcam OR (Katmai AND (bear OR bears OR grazer OR cubs))) AND NOT title:(fight OR skirmish OR bulldozes OR runs OR tourists OR school) |sort=date desc',
     "max_items": 6, "tags": ["trailcam", "nature", "animals", "beauty", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("street piano" OR "public piano" OR busker OR "street musician") AND NOT title:(tutorial OR lesson OR cover OR karaoke)' + _NEW,
     "max_items": 5, "tags": ["kind", "crowd", "voice", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND creator:(USFWS OR "Fish and Wildlife" OR "National Park" OR "Bureau of Land Management") AND NOT title:(drone OR training OR burn OR burning OR fire OR wildfire OR "leave no trace" OR "off-highway" OR ohv OR psa OR meeting OR webinar OR interview OR talk OR ceremony OR press OR announcement OR "how to" OR safety OR hunting OR hunt OR "public lands day" OR volunteers OR video) |sort=downloads desc',
     "max_items": 10, "tags": ["nature", "animals", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND title:(sunrise OR sunset OR "golden hour" OR fog OR mist OR snowfall OR "first snow" OR "falling snow" OR aurora OR "northern lights" OR "milky way" OR dusk OR dawn OR moonrise OR rainbow) AND NOT title:(party OR wedding OR concert OR festival OR drone OR timelapse OR time-lapse) |sort=downloads desc',
     "max_items": 10, "tags": ["light", "nature", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND title:(waves OR surf OR creek OR brook OR stream OR waterfall OR "river" OR forest OR meadow OR "in the wind" OR "rain on" OR "cherry blossom" OR blossoms OR lavender OR "fall colors" OR "autumn leaves" OR "wheat field" OR fireflies) AND NOT title:(party OR wedding OR concert OR festival OR drone OR race OR boat OR jet) |sort=downloads desc',
     "max_items": 10, "tags": ["nature", "weather", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND title:("my dog" OR "my cat" OR "our dog" OR "our cat" OR puppy OR puppies OR kitten OR kittens OR "first steps" OR "first snow" OR grandma OR grandpa OR grandmother OR grandfather OR "snow day" OR sledding OR playground OR bedtime OR "blowing bubbles") AND NOT title:(party OR wedding OR drone OR test) |sort=downloads desc',
     "max_items": 8, "tags": ["kind", "home", "childhood", "animals", "beauty", "modern"]},
    # Kindness, home and weather, each query scouted through the provider and re-rated by an independent
    # reader before it went in; the 1930s-60s home movies they also found are archival, so they stay out.
    # buskers and the people who stop, outside the YouTube mirror (rated 28/30 good of 104)
    {"provider": "archive", "query": "mediatype:movies AND NOT collection:(mirrortube OR movie_trailers OR roguetv) AND NOT identifier:tiktok-* AND title:(busker OR buskers OR busking OR \"street performer\" OR \"street performers\" OR \"street musician\" OR \"street musicians\" OR \"street piano\" OR \"public piano\") AND NOT title:(interview OR interviews OR documentary OR \"Tonight Show\" OR \"Stray Kids\" OR \"Scam School\" OR committee OR meeting OR regulations OR \"Happy Hour\" OR VOD OR stream OR Muslim OR LondonIsOpen OR Auditioning OR \"Picture Box\" OR Blobby OR Kickoff OR \"Opening Concert\" OR \"Lunch Concert\" OR Installations OR \"Hong Kong\" OR Disney OR Worst OR \"Text To Speech\" OR request OR Routine OR \"Shout Out\" OR \"Peek Bytes\" OR Happening OR \"In Your Neighborhood\" OR \"Blues Buskers\" OR Tribute OR \"Busker Hunt\" OR \"Human Transformer\" OR Lifestyle OR CityStream OR harmonious OR mission OR cover OR Gift OR panning OR Project OR y2mate OR Iran OR Fearless OR \"open mic\" OR Balladeer OR \"BBC Archive\") AND NOT creator:(\"Mayor of London\" OR \"Achievement Hunter\" OR \"Rooster Teeth\" OR \"Middle East Eye\" OR OpenPublica OR \"Let Me Explain Studios\" OR \"Revision 3\" OR WCCA OR \"Terry Love\" OR \"City of Seattle\" OR \"Boston City TV\") |sort=downloads desc",
     "max_items": 4, "tags": ["kind", "voice", "crowd", "beauty", "modern"]},
    # the 2005-06 camcorder years: first steps, birthdays, grandparents, a sleeping dog (rated 26/30 good of 118)
    {"provider": "archive", "query": "collection:ourmedia AND mediatype:movies AND title:(\"my grandmother\" OR \"my grandfather\" OR grandma OR grandpa OR oma OR \"my garden\" OR \"our garden\" OR \"the garden\" OR \"my dog\" OR \"my cat\" OR \"our dog\" OR \"our cat\" OR \"new puppy\" OR \"new kitten\" OR \"my son\" OR \"my daughter\" OR \"our baby\" OR \"baby's first\" OR \"laughing baby\" OR \"first birthday\" OR \"first steps\" OR \"learning to walk\" OR \"kids at play\" OR \"kids playing\" OR \"children playing\" OR \"playing in the snow\" OR \"in the snow\" OR \"at the beach\" OR \"at the park\" OR \"in the pool\" OR \"in the leaves\" OR \"bath time\" OR \"on the swing\" OR \"flying a kite\" OR \"christmas morning\" OR \"opening presents\" OR \"pumpkin patch\" OR \"feeding the ducks\" OR chickens) AND NOT title:(speech OR lobbyist OR myspace OR shares OR \"home movies\" OR \"show it\" OR \"he's\" OR atv OR trailer OR teaser OR interview OR conversations OR music OR song OR remix OR mv OR huggies OR frosty OR exile OR angels OR robot OR victoria OR \"how to\" OR irrigation OR \"mad city\" OR tribute OR remembering OR test OR househunting OR service OR sermon OR crew OR productions OR \"in common\" OR episode OR ppv OR nightmare OR wrestling) |sort=downloads desc",
     "max_items": 6, "tags": ["home", "childhood", "kind", "beauty", "modern"]},
    # back gardens, bees, hens, mowing the lawn, cows (rated 26/30 good of 124)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(garden OR allotment OR backyard OR \"back yard\" OR porch OR lawn OR \"bird bath\" OR greenhouse OR orchard OR chickens OR hens OR rooster OR goats OR lambs OR piglets OR pigs OR farm OR cows OR calf OR donkey OR pony OR beehive OR bees) AND NOT title:(drone OR training OR slideshow OR mountain OR \"dall sheep\" OR eden OR disco OR library OR hotel OR dead OR \"wind farm\" OR attack OR explains OR battle OR theatre OR burning OR barge OR cemetery OR memorial OR engines OR smoldering OR \"farm bill\" OR tribute OR truffled OR barrel) |sort=downloads desc",
     "max_items": 6, "tags": ["home", "nature", "animals", "beauty", "modern"]},
    # kids in puddles and surf, family walks and dinners (rated 25/30 good of 81)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(kids OR children OR family OR mom OR dad OR \"my son\" OR \"my daughter\" OR birthday OR \"christmas morning\" OR xmas OR toddler OR boys OR girls) AND NOT title:(party OR wedding OR drone OR test OR concert OR festival OR interviewing OR interview OR dead OR fire OR robot OR ribbon OR rescue OR service OR voicemail OR live OR show OR museum OR burn OR clockwork OR coral OR corals OR slug OR slugs OR beetle OR larva OR \"sea cucumber\" OR rat OR pigeon OR tech OR queen OR sky OR \"beach boys\" OR berkhof OR muslim OR photographed OR memorial OR cemetery OR calder OR statefairtx OR invitational) |sort=downloads desc",
     "max_items": 6, "tags": ["childhood", "home", "kind", "beauty", "modern"]},
    # pets at home and at the park (rated 25/30 good of 39)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(dog OR dogs OR doggy OR cat OR cats OR kitty OR bunny OR rabbit OR parrot OR budgie OR cockatiel OR tortoise OR goldfish OR hamster OR \"guinea pig\" OR pets OR pony OR horse OR horses) AND NOT title:(\"my dog\" OR \"my cat\" OR puppy OR kitten OR show OR race OR racing OR rodeo OR police OR parade OR drone OR test OR wild OR scan OR banksy OR animatronic OR botulism OR paints OR gather OR roundup OR fish OR \"prairie dog\" OR \"dog-faced\" OR snake OR \"sea\" OR hotdog OR \"hot dog\" OR tick OR fight OR summit) |sort=downloads desc",
     "max_items": 4, "tags": ["animals", "home", "beauty", "modern"]},
    # rain, storms seen from balconies, hail, wind (rated 24/30 good of 243)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(rain OR raining OR rainy OR raindrops OR drizzle OR downpour OR puddle OR puddles OR umbrella OR umbrellas OR \"rain shower\" OR rainstorm OR \"rain storm\" OR thunderstorm OR thunderstorms OR \"summer storm\" OR \"storm clouds\" OR hail OR hailstorm OR windy OR breeze OR swaying OR \"wind chimes\" OR \"wind in the trees\") AND NOT title:(dance OR dancing OR \"rain on\" OR \"in the wind\" OR concert OR festival OR party OR wedding OR game OR race OR racing OR flood OR flooding OR damage OR drone OR rainforest OR \"rain forest\" OR sprinkler OR \"purple rain\" OR stevie OR sinatra OR song OR chasing OR chaser OR gamma OR disco OR \"hail mary\" OR sailing OR kite OR kiteboarding OR surfing OR windsurfing OR turbine OR turbines OR trial OR test OR skeleton OR performs OR tournament OR challenge OR exhibit OR \"rain check\" OR kingdom) AND NOT creator:(NASA) |sort=downloads desc",
     "max_items": 6, "tags": ["weather", "quiet", "nature", "beauty", "modern"]},
    # snow falling on streets and yards, from train windows (rated 26/30 good of 69)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(snowing OR snowflakes OR \"snow falling\" OR \"snowy night\" OR \"snowy day\" OR \"snowy street\" OR blizzard OR \"snow storm\" OR snowstorm OR \"heavy snow\" OR \"lake effect\" OR \"let it snow\" OR \"winter wonderland\" OR icicles OR \"winter night\" OR \"snow at night\") AND NOT title:(\"first snow\" OR \"falling snow\" OR snowfall OR \"snow day\" OR owl OR sledding OR skiing OR snowboard OR snowmobile OR plow OR plowing OR crash OR party OR concert OR game OR pictures OR slideshow OR nokia OR canon OR \"ice storm\") |sort=downloads desc",
     "max_items": 6, "tags": ["weather", "quiet", "beauty", "modern"]},
    # lighthouses, moonlight, street lights, views from windows (rated 23/30 good of 54)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(lighthouse OR \"city lights\" OR \"street lights\" OR streetlights OR \"night lights\" OR \"harbor lights\" OR lanterns OR moonlight OR moonlit OR \"full moon\" OR \"christmas lights\" OR \"city at night\" OR twilight OR \"blue hour\" OR nightfall OR \"night falls\" OR \"after dark\" OR \"evening light\" OR \"my window\" OR \"out the window\" OR \"office window\" OR \"bedroom window\" OR \"kitchen window\" OR \"apartment window\" OR \"hotel window\" OR \"cabin window\" OR \"plane window\" OR \"train window\" OR \"from the train\" OR \"night drive\") AND NOT title:(\"friday night\" OR antique OR gallery OR frame OR concert OR festival OR party OR wedding OR parade OR race OR club OR show OR drone OR \"milky way\" OR test OR trial OR \"stained glass\" OR \"twilight zone\" OR saga OR skeleton) AND NOT creator:(\"Comrade King\") |sort=downloads desc",
     "max_items": 5, "tags": ["light", "quiet", "transit", "beauty", "modern"]},
    # the park service's soundscapes and weather time-lapses (rated 25/30 good of 36)
    {"provider": "archive", "query": "identifier:nps-video-* AND NOT creator:(\"Neal Herbert\") AND title:(\"b-roll\" OR \"b roll\" OR broll OR soundscape OR soundscapes OR timelapse OR \"time-lapse\" OR \"time lapse\" OR \"static shot\" OR \"bear byte\" OR \"sound byte\") AND title:(snow OR winter OR rain OR storm OR clouds OR fog OR mist OR sunrise OR sunset OR night OR stars OR weather OR lightning OR tides OR moon OR forest OR wind OR spring OR autumn OR fall OR summer OR dusk OR dawn OR water OR river OR creek OR lake) AND NOT title:(package OR installation OR installing OR panels OR construction OR crew OR \"re-vegetating\" OR battlefield OR fort OR memorial OR church OR mission OR climbers OR fire OR burn OR chats OR talk OR program) |sort=downloads desc",
     "max_items": 5, "tags": ["nature", "weather", "quiet", "beauty", "modern"]},
    # a Virginia videographer: fog, creeks, barns in rain, cows (rated 25/30 good of 484)
    {"provider": "archive", "query": "creator:(\"C. E. Price\") AND NOT title:(\"Harvest Of Death\" OR western OR montage OR \"Henry VIII\" OR CGI OR exercise OR projector OR phooning OR inspirations OR god OR lord OR blessed OR brethren OR \"wise men\" OR patience OR wisdom OR victory OR thine OR \"his breath\" OR contentment OR razors OR hart OR existing OR \"the kids\" OR \"higher than\" OR \"earthly peace\" OR faith OR jitney OR flatiron OR \"nature of things\" OR \"sing a song\" OR halloween OR hamburger OR TVA OR \"heating oil\" OR lonely OR intersection OR traffic OR vehicles) |sort=downloads desc",
     "max_items": 6, "tags": ["nature", "weather", "quiet", "beauty", "modern"]},
    # Grand Canyon b-roll: rafts, falls, sunrise, cloud inversions (rated 24/30 good of 143)
    {"provider": "archive", "query": "identifier:nps-video-* AND creator:(Blum OR Quinn OR \"Richard Burton\") AND NOT title:(\"visitor center\" OR director OR experiment OR store) |sort=downloads desc",
     "max_items": 6, "tags": ["nature", "light", "quiet", "beauty", "modern"]},
    # Pixabay nature clips: rain on a window at night, a fog forest, swans (rated 27/30 good of 85)
    {"provider": "archive", "query": "identifier:pixabay-* AND title:(bird OR birds OR swan OR duck OR robin OR hummingbird OR sunset OR sunrise OR sea OR ocean OR waves OR beach OR forest OR nature OR river OR lake OR waterfall OR flowers OR flower OR meadow OR field OR rain OR snow OR clouds OR sky OR mountains OR landscape OR cows OR horse OR dog OR cat OR leaves OR tree OR trees) AND NOT title:(render OR abstract OR background OR backgrounds OR loop OR animation OR particles OR space OR galaxy OR cosmos OR plexus OR neon OR explosion OR fire OR wormhole OR fractal OR digital OR \"3d\" OR snowflake OR \"jet ski\") |sort=downloads desc",
     "max_items": 5, "tags": ["nature", "weather", "light", "beauty", "modern"]},
    # long quiet tanks: jellies, sea dragons, a kelp forest (rated 23/30 good of 126)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(aquarium OR jellyfish OR jellies OR \"sea dragon\" OR seahorse OR seahorses OR \"kelp forest\" OR \"fish tank\" OR \"sea otter\" OR \"sea otters\" OR penguins OR \"manta ray\" OR \"sea turtle\" OR \"coral reef\") AND NOT title:(laser OR mapping OR mating OR watching) |sort=downloads desc",
     "max_items": 5, "tags": ["animals", "quiet", "nature", "beauty", "modern"]},
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

# Queries taken out of the sets because of what they brought in. The audit removes every source they ever
# ingested from the pool, files and all.
RETIRED_QUERIES = [
    # caught-on-camera tweets: an animal kicked in the street, a man beaten to death, deaths, a plane crash,
    # riots, partisan posts; the mirrortube dashcam queries cover the dashcams
    "identifier:twitter-* AND title:(dashcam OR cctv OR \"caught on\" OR doorbell)" + _NEW,
]

# Sources taken out and then put back by the owner of the piece ("I will flag if something feels off"). Their
# files were deleted with them, so a build fetches each one again by its address until it is in the pool.
REINSTATED = [
    {"provider": "archive", "url": "https://archive.org/details/" + ident, "max_items": 1, "tags": tags}
    for ident, tags in (
        ("Instagram-DdeICa9AIqS", ["reels", "modern", "phone"]),
        ("youtube-FtWXWKUK6rg", ["dashcam", "traffic", "modern"]),
        ("youtube-hCU65_u4poM", ["liminal", "city", "modern"]),
        ("TikTok-7147085836130094382", ["nature", "animals", "modern", "phone"]),
        ("youtube-IWbXnhcdIfU", ["animals", "quiet", "modern", "nature"]),
        ("youtube-Zg-4zw7EcTY", ["home", "faces", "modern"]),
        ("youtube-__yfsYoKoNE", ["dashcam", "traffic", "modern"]),
        ("youtube-4YtwK9dGWrY", ["dashcam", "traffic", "modern"]),
    )
]

# INTERNET_JOBS: the pool had come to lean on nature and animals, so the owner asked for more of the internet
# itself: social media, weird happenings, vlogs. The set is the queries above that bring those (phone posts,
# vlogs, cameras catching odd things, liminal places; not the pets, weather and nature ones), plus
# NEW_INTERNET_JOBS, scouted for it. `--set internet` scrapes just these; weekly builds keep them in rotation.
NEW_INTERNET_JOBS: list[dict] = [
    # Each scouted through the provider and rated by a second reader on 20 items from two result pages and
    # their thumbnails (light sensuality passes, porn does not). Long NOT lists stay under the archive's limit
    # of 2,047 characters for the whole query, wrapper included.
    # Twitter, weird: the caption-less 'no context' repost accounts of 2020-21 (No Context Humans, Strangest Media
    # Online, Unusual Videos...): a man vacuum-sealing himself in a bin bag, a glass floor over a fish tank. No
    # caption means no filter can read them, so every item was looked at and the unsafe ones (fights, a slap,
    # crashes, an arrest) are excluded by identifier (rated 19/20). A closed set of 95: should the count grow,
    # unseen posts have been mirrored under these names. At 2,028 of the archive's 2,047 characters: full.
    {"provider": "archive", "query": "identifier:twitter-* AND creator:(\"No Context Humans\" OR \"Out of Context Human Race\" OR \"Humans do shit\" OR \"Strangest Videos Online\" OR \"Strangest Media Online\" OR \"Unusual Videos\" OR \"Unexpected Scenes\" OR \"Unexpected Moments\" OR \"WeirdestMp4s\" OR \"Videos in my folder\" OR \"What Magic is This\" OR \"What Magic And This\" OR \"People born to make us laugh\" OR \"People doing funny and stupid things\" OR \"Just Viral\" OR \"videos that improve your day\" OR \"No Context Laughs\" OR \"This is rare, but it happens\" OR \"Out of Context India\") AND NOT identifier:(twitter-1256235305482493958 OR twitter-1266739197525647360 OR twitter-1284191519646375943 OR twitter-1297076159167922176 OR twitter-1310877027923161088 OR twitter-1327672646142746627 OR twitter-1327753930785263616 OR twitter-1352983465763852288 OR twitter-1355825120825106432 OR twitter-1360672276589510660 OR twitter-1363283318545014784 OR twitter-1366709074453127172 OR twitter-1374673106556624896 OR twitter-1377509162406572033 OR twitter-1380124514584047618 OR twitter-1383751702008922114 OR twitter-1386268511387865088 OR twitter-1386327934701555716 OR twitter-1386594652271349764 OR twitter-1386643254888775683 OR twitter-1386715663956316163 OR twitter-1386931709728501764 OR twitter-1389539599098159104 OR twitter-1390639556857237504 OR twitter-1392485780677926917 OR twitter-1393964786845691908 OR twitter-1394303788547117058 OR twitter-1400785873051033602 OR twitter-1402563091708186625 OR twitter-1403307508597497862 OR twitter-1404422989714804740 OR twitter-1404467925965152259 OR twitter-1404557244163895301 OR twitter-1404881737348530180 OR twitter-1405043681283903488 OR twitter-1406211778002915329 OR twitter-1410687994584080388 OR twitter-1413762460675366916 OR twitter-1414577803421528067 OR twitter-1414970398295433221 OR twitter-1425070692085604358 OR twitter-1437115153603039233 OR twitter-1440742310896025600 OR twitter-1441516799065919496 OR twitter-1441815325025181699 OR twitter-1442155098675810306 OR twitter-1364456308980674563) |sort=date desc",
     "max_items": 10, "tags": ["weird", "social", "modern", "phone", "faces", "home", "motion"]},
    # Twitter, random: posts with no text from the 2021 repost accounts, June-December: pets, cooking, crafts,
    # building work, machines, small human moments (rated 18/20; every row CI can reach was looked at)
    {"provider": "archive", "query": "identifier:twitter-* AND title:(\"t.co\") AND collection:(qinpro_video_mirror OR mirrortube) AND date:[2021-06-01 TO 2021-12-31] AND NOT creator:(fails OR failure OR failures OR karma OR died OR die OR death OR alive OR lives OR live OR longer OR nut OR shots OR extreme OR jerks OR scary OR dark OR predators OR wild OR fighting OR fight OR drunk OR drunks OR idiot OR idiots OR stupid OR prizes OR iq OR hurt OR escaped OR diseaster OR catastrophic OR licenses OR cars OR vehicles OR cameras OR crazy OR insanity OR freakout OR defense OR regret OR risking OR risk OR shit OR shitting OR shitt OR fucking OR fuck OR unexpected OR wrong OR attempt OR mistake OR cheating OR \"close call\" OR \"oh no\" OR \"went well\" OR survive OR paranormal OR \"believe it or not\" OR \"hold my\" OR laughs OR funny OR cop OR bitch OR derps OR \"kids are\" OR \"girls getting\" OR public OR scream OR strangest OR \"you seeing\" OR story OR times OR hq OR army OR thai OR yubo OR brandinside OR shop OR euros OR utd OR anime OR pokemon OR vtubers OR akb48 OR bloopers OR movies OR porn OR \"美国之音中文网\" OR \"hunger game\" OR styx OR gifs OR memes OR memepedia OR *bnk48* OR \"💩\" OR hit OR \"Ricardo Claure\" OR \"ซาแซงประชารัฐ\" OR \"ひめにぃ様\" OR Dimitrescu OR \"No Context Humans\" OR \"ตี๋เร้ก\" OR \"ช่างแม่ง\" OR Sarah OR \"Joe Merrick\" OR americans OR \"Dan Short\" OR MISSION OR rare OR bros OR construction) |sort=date desc",
     "max_items": 10, "tags": ["random", "social", "modern", "phone", "home", "motion"]},
    # Twitter, random: the same for April-May 2021, more people at home: a family's bottle trick at dinner, a
    # driver stopping traffic for ducks, a boy's third-birthday cake (rated 18/20)
    {"provider": "archive", "query": "identifier:twitter-* AND title:(\"t.co\") AND collection:(qinpro_video_mirror OR mirrortube) AND date:[2021-04-01 TO 2021-05-31] AND NOT creator:(fails OR failure OR karma OR die OR alive OR lives OR extreme OR scary OR cruel OR wild OR idiots OR stupid OR prizes OR iq OR catastrophic OR catasteophe OR chaos OR licenses OR insane OR robbery OR defense OR repenting OR shit OR fucked OR fucking OR ruined OR legendary OR \"1000 ways\" OR ufo OR laugh OR unusual OR instagram OR jibtan OR \"淫乱\" OR \"男の娘\" OR \"美国之音中文网\" OR *bnk48* OR \"💩\" OR hit OR \"Moe Lord\" OR \"No Context Humans\" OR less OR news OR tv OR trump OR police OR porn OR anime OR official OR uoq OR PJN OR \"ヌゥ\" OR \"ᴇᴀʀᴛʜ ᴇᴀᴛᴇʀ\" OR \"Sh*t videos\" OR \"ちかめ\" OR \"accepting now\" OR Faruk OR \"Living On Earth\") |sort=date desc",
     "max_items": 10, "tags": ["random", "social", "modern", "phone", "home", "faces"]},
    # Twitter's Periscope: single-take walking streams of 2020: Central Park at dusk, cycling through Paris, a
    # window-seat takeoff, lunch on a volcano in Hakone, Devon beaches (rated 10/10; 22 streams in all)
    {"provider": "archive", "query": "identifier:periscope-* AND creator:(MaryNYC OR MikeTendsToTravel OR markshorland OR naisuguy OR \"Irina Ideas\" OR ChantalTV) AND item_size:[0 TO 80000000] AND NOT title:(protest OR protests OR protesters OR \"tear gas\" OR police OR cops OR torn OR riot OR lockdown OR covid OR coronavirus OR rally OR \"first responders\" OR tribute OR remembering OR piano OR music) |sort=downloads desc",
     "max_items": 5, "tags": ["vlog", "social", "city", "phone", "voice", "quiet", "modern"]},
    # Twitter, sincere: the 2021 feel-good repost accounts: Hot Wheels left on strangers' Jeeps, a delivery
    # driver lifting an old woman onto the kerb with his tail lift (rated 10/10; an accident clip excluded)
    {"provider": "archive", "query": "identifier:twitter-* AND creator:(\"Humans Being Bros\" OR \"that,s what hero does\" OR \"this profile makes you happy\" OR \"This profile will makes you happy\" OR \"this account will make you happy\" OR \"This profile makes your day better\" OR \"videos that make your day better\" OR \"videos that improve your day\" OR \"the best you will see today\" OR \"this profile will heal you\" OR \"profile that cure your stress\" OR \"that's why I love this profile\" OR \"Wholesome TikTok\") AND NOT identifier:(twitter-1390911389313552387 OR twitter-1401197432814247946 OR twitter-1391711997620748288 OR twitter-1391233362442919936 OR twitter-1414103823799308294 OR twitter-1421149081628405762 OR twitter-1405907182680383495 OR twitter-1390904586609643520 OR twitter-1559937176942497792 OR twitter-1463986707464953856 OR twitter-1414647390640873478 OR twitter-1406568573846364163 OR twitter-1406552817557458947 OR twitter-1404880898017746944 OR twitter-1399687499753037826 OR twitter-1398908898896072704 OR twitter-1392051194118369283 OR twitter-1389287703443742720 OR twitter-1390955914660777989) |sort=downloads desc",
     "max_items": 6, "tags": ["kind", "faces", "childhood", "home", "phone", "modern", "social", "sincere"]},
    # Twitter, sincere: an older German presenter's own phone diary, 2016-19: Sunday coffee, the first asparagus,
    # Advent candles, sweeping snow, a storm on the dunes (rated 10/10)
    {"provider": "archive", "query": "identifier:twitter-* AND creator:(\"Walter Freiwald\") AND NOT description:(gehwaehlen OR btw17 OR btw2017 OR europawahlen2019 OR voteforclimate OR wirsindmehr OR chemnitz OR rtl OR hypnoseshow OR promisunterhypnose OR twintvofficial OR satire OR promibb OR instagram) AND NOT identifier:(twitter-card-1089768690231504898 OR twitter-card-961543956747227137 OR twitter-card-962639798480580609 OR twitter-card-929294153753808896 OR twitter-card-1097394835529629696 OR twitter-card-779336421870018560 OR twitter-card-1079709694955057152) |sort=downloads desc",
     "max_items": 4, "tags": ["faces", "home", "voice", "vlog", "phone", "modern", "social", "sincere"]},
    # TikTok, vlogs, found through the whole caption rather than the cut title: day in the life, grwm, come with
    # me, vanlife, room tours, a grandmother's morning routine, a move from the UK to Korea (rated 20/20)
    {"provider": "archive", "query": "identifier:tiktok-* AND (vlog OR vlogs OR vlogger OR vlogging OR dailyvlog OR vlogmas OR dayinmylife OR adayinmylife OR dayinthelife OR adayinthelife OR \"day in my life\" OR \"day in the life\" OR ditl OR grwm OR getreadywithme OR morningroutine OR \"morning routine\" OR nightroutine OR \"come with me\" OR comewithme OR \"come along\" OR roomtour OR diary OR \"dear diary\" OR \"my day\" OR momlife OR dadlife OR collegelife OR vanlife OR solotravel OR \"get ready with me\" OR \"room tour\" OR \"moving day\" OR \"what i eat in a day\") AND NOT (music OR song OR dance OR game OR vrchat OR virtual OR sl OR comedy OR humour OR meme OR capcut OR greenscreen OR ai OR cosplay OR amazon OR code OR spons OR review OR ootd OR court OR custody OR lawyer OR politics OR news OR \"passed away\" OR death OR rip OR shot OR kirk OR nosleep OR squishable OR gymtok OR fitness OR cat OR catsoftiktok OR dog OR crow OR crowtok OR animals OR animalsoftiktok OR cowsoftiktok OR highlandcow OR wap OR milfs OR gilfs OR geopolitics OR popthebottle OR 2020evolution OR spawnim OR yakub OR agartha OR vril OR shitpost OR epstein OR zip OR \"live streams\" OR doctor) AND NOT title:(vlog OR dayinmylife OR \"day in my life\" OR grwm) AND NOT creator:(\"pearlmania500\" OR \"minitruckmommygarage\" OR \"scotty.k.fitness\" OR \"_kristyjessica\" OR \"okaygnomie\" OR \"winter7th\" OR \"thertpod\" OR \"sam.shan.shops\" OR \"2001cursed\" OR \"jessiepascua0976123\" OR \"MarcusLaw\" OR \"Swoll Guy\" OR \"allgoodnoworries\" OR \"evaaviolett\" OR \"beaucupples\" OR \"lamarrwilson\" OR \"the_jewish_agency\" OR \"covenacademy\" OR \"kennethudut\" OR \"onlyjayus\" OR \"kamalaharris\" OR \"dxxdy.kxrlx\" OR \"spectrum_vlog\" OR \"debbie\" OR \"rsmlpnes\" OR \"dr_omoregret_offical\" OR \"nakai_diary\" OR \"YakubianUnc\" OR \"Tamsin\" OR \"johnshahi2050\") |sort=date desc",
     "max_items": 6, "tags": ["vlog", "faces", "home", "phone", "voice", "modern", "sincere"]},
    # TikTok, social: Singaporeans filming their own city: 150 people walking an MRT line, a 90-year-old's first
    # automatic mahjong table, buskers (rated 20/20, once a busking set that turned into a confrontation was out)
    {"provider": "archive", "query": "identifier:tiktok-* AND (fypsg OR singapore OR mrt OR sgtiktok OR tiktoksg OR sgfyp OR singaporetiktok) AND NOT (news OR sgnews OR ge2025 OR sgelections OR election OR vote OR minister OR pritam OR makeover OR shopee OR shopeehaul OR haul OR ad OR code OR linktree OR sponsored OR music OR cover OR song OR acoustic OR chords OR dance OR dancechallenge OR dc OR kpop OR katseye OR concert OR qwer OR fanmeet OR zip OR cat OR catsoftiktok OR fishing OR prison OR police OR crash OR accident OR confrontation OR incident OR hurt OR fight OR fighting OR altercation OR harass OR harassment OR scold OR scolding OR mating OR edit) AND NOT creator:(\"ltasg\" OR \"mothershipsg\" OR \"channelnewsasia\" OR \"motsingapore\" OR \"friedrice entertainment\" OR \"wise\" OR \"psasingapore\" OR \"benwoah\" OR \"heyhihazelle\" OR \"boonhuilu\" OR \"aijou.music\" OR \"lawrencewongst\" OR \"orchardroadfashion\" OR \"sleepyreggy\" OR \"hal.baddie\" OR \"kimipiggay\" OR \"naploes\" OR \"valariepepper\" OR \"noahcorolla\" OR \"youallkanasai\" OR \"maetan\" OR \"estellefly\" OR \"germaineleonora\" OR \"saffronsharpe_\" OR \"gloria.soh\" OR \"xinandxuan\" OR \"evantellstories\" OR \"sgag_sg\" OR \"adiel_rusyaidi\" OR \"cutekorkor\" OR \"migraineyy\" OR \"theprivacytaopoon_\" OR \"hwztech\" OR \"yoasobi_ayase_ikura\" OR \"turritopsisdohrniii\" OR \"8_aron\" OR \"zhul.rahim\") |sort=date desc",
     "max_items": 6, "tags": ["social", "city", "crowd", "faces", "phone", "modern"]},
    # TikTok, weird: strange things people caught on a phone: a hidden room under a house, bunnies on a trampoline
    # at night on a Ring camera, eclipse crescents (rated 18/20; some is staged or performative)
    {"provider": "archive", "query": "identifier:tiktok-* AND ((ufo OR orb OR eclipse OR meteor OR unexplained OR ringdoorbell OR abandoned OR urbex OR \"only in\" OR onlyinsingapore OR ghosthunting OR hauntedhouse) OR ((weird OR creepy OR scary OR ghost OR mystery OR glitch OR spotted OR \"the sky\" OR odd) AND (street OR house OR sky OR spotted OR today OR night OR walk OR caught OR real OR life OR london OR room OR happened))) AND NOT (podcast OR roblox OR forsaken OR spawn OR spawnism OR game OR gaming OR anime OR art OR movie OR film OR trailer OR conspiracy OR truecrime OR edit OR ai OR story OR storytime OR creepypasta OR history OR squishable OR plush OR music OR dance OR comedy OR meme OR news OR police OR crash OR fight OR died OR death OR dead OR epstein OR squishables OR greenscreenvideo OR therian OR spawnist OR alien OR aliens OR extraterrestrial OR ancient OR archeological OR megalodon OR phenomena OR piracy OR spacecraft OR zip OR scandal OR cgi OR vfx OR backrooms OR cat OR catsoftiktok OR kitten OR kittensoftiktok OR pets OR \"true crime\" OR vote OR election OR thalassaphobia OR droneshow OR droneshows OR corecore OR disturbing OR horrify) AND NOT creator:(\"30morbidminutes\" OR \"_kristyjessica\" OR \"ajplus\" OR \"az_desert_rider_26\" OR \"crumbl\" OR \"evaaviolett\" OR \"itsoraduplass\" OR \"kamalaharris\" OR \"kennethudut\" OR \"lily_kennard\" OR \"longogla\" OR \"minitruckmommygarage\" OR \"myuz_gaza1\" OR \"newlinersseries\" OR \"nunchakusdragon\" OR \"okaygnomie\" OR \"pearlmania500\" OR \"psasingapore\" OR \"regulationletsplay\" OR \"theredweb\" OR \"todayfriendsbest\" OR \"tweetneypie\" OR \"thestandardth\" OR \"golfpichaya\" OR \"factsforpeace\" OR \"obs.oscar99\" OR \"hidden.on.google.earth\" OR \"lights are off\" OR \"hearts2hearts\" OR \"turbiyoan.christisreal\" OR \"ghost_london\" OR \"hawkdunlap\" OR \"Hoodwinkedfool\" OR \"AlEkSeY\" OR \"ufouncensored\" OR \"squishable.twelve\" OR \"firefly_droneshows\" OR \"Firefly Drone Shows\" OR \"JoeSpinsTheGlobe\" OR \"Nick Bosse\" OR \"Oddities on Elm Street\" OR \"user6208797968164\") |sort=date desc",
     "max_items": 5, "tags": ["weird", "fear", "home", "phone", "modern"]},
    # TikTok, weird: odd everyday moments the archiver described in subjects, captions often only #fyp: mushrooms
    # on a Kaohsiung traffic island, a Thai school freezing for the anthem, Edo-period running (rated 13/13)
    {"provider": "archive", "query": "identifier:tiktok-* AND subject:(funny OR infrastructure OR old OR restaurant OR road OR school OR subway OR walk OR weird OR festival OR temple OR escalator OR cyberpunk OR food) AND subject:(malaysia OR indonesia OR philippines OR thailand OR taiwan OR japan OR china OR uk) AND NOT subject:(dance OR trend OR challenge OR song OR music OR remix OR meme OR swimsuit OR choreography OR facts OR singapore OR flood OR katseye OR \"i-dle\" OR npc OR crazy OR angry OR scam OR scammer OR fart OR farting OR cat OR earthquake OR zoo OR typhoon OR tsunami OR fire OR accident OR police OR election OR politics OR news) AND NOT creator:(\"bell_fu___\" OR \"satit.psu.secondary\" OR \"tuotuolive\" OR \"qabi_xiaomin\" OR \"jackmtfchardman\" OR \"lukeaustin777\" OR \"spicy.reddd\" OR \"celebritykid\" OR \"morgzyh\") |sort=date desc",
     "max_items": 5, "tags": ["weird", "city", "motion", "faces", "phone", "modern"]},
    # YouTube, the camera roll: uploads still titled with the phone's filename (IMG 9087, DSC 5796), posted as
    # they were: a party under red neon, a plane cabin, a tractor in a lot (rated 18/20)
    {"provider": "archive", "query": "collection:mirrortube AND identifier:youtube-* AND title:((IMG OR MVI OR DSC OR DSCN) AND (0* OR 1* OR 2* OR 3* OR 4* OR 5* OR 6* OR 7* OR 8* OR 9*)) AND NOT title:(the OR and OR of OR to OR in OR for OR with OR on OR at OR is OR my OR a OR de OR la OR el OR en OR le OR et OR der OR die OR und OR och OR i OR del OR vs OR pt OR townhall OR vid OR video OR official OR part OR mov OR avi OR jpg OR mp4 OR review OR sony OR nikon OR canon OR camera OR test) AND NOT creator:(Robertramirez0223 OR \"David Reeb\" OR \"Mech Arena Official\" OR \"Lars Faurholt\" OR Dopamine OR ShopMVB OR \"Abu Dhabi Media Network\" OR svechnoistanok OR \"Million Dollar Extreme 3\" OR \"Kane Pixels\" OR \"Download Free\" OR \"The Fuppits\" OR \"Northern Mockingbird\" OR Kilothesaurus OR \"Adam George\" OR \"Lee Gale\" OR \"Steve Snyder\" OR \"Thibault Jacobi\" OR \"DIGEST CORP.\" OR \"BHSHOES BHSHOESINC\" OR \"Boîte Pandore\" OR \"眾新聞\" OR \"張阿哲\" OR \"天眼查档\" OR \"Kawaii Potato\" OR \"Hai Nguyen thi\" OR REComps9 OR \"CS Fola\" OR \"Ole, My Son\") |sort=date desc",
     "max_items": 10, "tags": ["phone", "home", "faces", "crowd", "modern", "social", "random"]},
    # YouTube, weird: elevator enthusiasts' phone rides: call buttons, chimes, doors opening on empty fluorescent
    # floors, a 1960s Otis on its last ride (rated 20/20; keep it small, it is all doors and buttons)
    {"provider": "archive", "query": "collection:mirrortube AND title:((elevator OR elevators OR escalator OR escalators) AND (hydraulic OR traction OR otis OR schindler OR kone OR thyssenkrupp OR dover OR montgomery OR westinghouse OR haughton OR mitsubishi OR ride OR mall OR hotel OR garage OR library OR station)) AND NOT title:(music OR song OR minecraft OR roblox OR game OR simulator OR prank OR film OR animation OR survive OR secret OR dangerous OR trapped OR chaos OR remix OR voice OR prompts) AND NOT creator:(\"Zack D. Films\" OR \"Zeck Felms\") |sort=date desc",
     "max_items": 4, "tags": ["phone", "liminal", "quiet", "machines", "weird", "modern", "social"]},
    # YouTube, weird: hotel fire alarms at 4:30 a.m., strobes down dark corridors, guests filming from their
    # beds (rated 17/19; loud)
    {"provider": "archive", "query": "collection:mirrortube AND title:((\"fire alarm\" OR \"fire alarms\") AND (test OR testing OR activation OR \"goes off\" OR \"going off\" OR hotel OR motel OR inspection OR drill)) AND NOT title:(tantrum OR grounded OR suspended OR arrested OR pull OR pulled OR pulling OR kids OR \"bad apple\" OR music OR song OR minecraft OR roblox OR game OR simulator OR prank OR film OR animation OR remix) AND NOT creator:(\"Oh Shiitake Mushrooms\" OR \"911 VIDEO NEWS\") |sort=date desc",
     "max_items": 3, "tags": ["phone", "fear", "liminal", "weird", "modern", "social"]},
    # YouTube, vlogs: personal uploads (People & Blogs), newest first, in many languages (влог, ルーティン, un día
    # conmigo, ein tag mit mir), capped at 400 MB: Tokyo trains, a drive to an empty beach (rated 18/20; an account
    # selling sex videos excluded)
    {"provider": "archive", "query": "collection:mirrortube AND subject:(\"People & Blogs\") AND item_size:[0 TO 400000000] AND title:(\"weekly vlog\" OR \"week in my life\" OR \"days in my life\" OR \"living alone\" OR \"moving vlog\" OR \"moving day\" OR \"moving into\" OR \"car vlog\" OR \"first vlog\" OR \"vlog #1\" OR \"vlog 1\" OR \"my first video\" OR \"video diary\" OR \"daily vlog\" OR \"life update\" OR \"chit chat\" OR \"weekend vlog\" OR \"apartment tour\" OR \"room tour\" OR влог OR влоги OR ルーティン OR 日常vlog OR 暮らし OR 社会人 OR 休日 OR \"un dia conmigo\" OR \"un día conmigo\" OR \"um dia comigo\" OR \"ein tag mit mir\" OR \"une journée avec moi\" OR \"una giornata con me\" OR \"benimle bir gün\" OR \"vlog diario\" OR \"mi rutina\" OR \"minha rotina\" OR \"ma routine\" OR \"mein alltag\") AND NOT title:(minecraft OR roblox OR game OR gaming OR animated OR animation OR tg OR caption OR textingstory.com OR aquestalk OR masturbation OR boobs OR bra OR braless OR topless OR erotic OR porn OR spicy OR hookup OR kink OR thong OR twerk OR abusive OR punta OR pinamar OR milipilis OR amigas OR jk OR 女子高生 OR ノーブラ OR 水着 OR 下着 OR 漫画 OR \"world trade center\" OR \"waist beads\" OR halo) AND NOT creator:(\"Hannah Witton\" OR \"Lustful Geeks\" OR \"Venus O'Hara\" OR \"Indigo White\" OR \"Housewife Ginger\" OR \"Madi Collins\" OR \"Adreena Winters\" OR ToplessTopics OR RHRPaige OR Anisa OR \"Evie Lupine\" OR \"Modelo Julinha\" OR \"Meg Turney\" OR \"Ginnastica San Biagio\" OR Pornhuber OR \"Daelynn r\" OR Howlyyn OR \"Mad Kirb\" OR \"Jay_Marish\") |sort=date desc",
     "max_items": 5, "tags": ["vlog", "faces", "home", "voice", "modern", "social", "sincere"]},
    # YouTube, weird: the 11foot8 'can-opener' bridge camera: trucks peeled and wedged while traffic waits;
    # property only, nobody hurt (rated 20/20)
    {"provider": "archive", "query": "collection:mirrortube AND creator:(yovo68) AND title:(11foot8 OR \"11foot8+8\" OR \"11 foot 8\") AND NOT title:(compilation OR pedestrian OR pedestrians OR car OR cars OR driver OR preparing OR raise OR raising OR ceremony OR interview OR update OR \"behind the scenes\") |sort=downloads desc",
     "max_items": 2, "tags": ["cctv", "traffic", "machines", "weird", "modern", "social"]},
    # YouTube, vlogs, the early years (2007-15): webcam-lit bedrooms, first vlogs, a kid's room tour, a walk
    # through a new house (rated 17/21; parodies and a jump-scare excluded)
    {"provider": "archive", "query": "collection:mirrortube AND date:[2005-01-01 TO 2015-12-31] AND title:(vlog OR vlogs OR vlogging OR \"video blog\" OR \"video diary\" OR \"first vlog\" OR \"my first video\" OR \"daily vlog\" OR \"room tour\" OR \"house tour\" OR \"life update\" OR \"update video\" OR \"my day\" OR \"day in the life\" OR \"day in my life\" OR \"moving day\" OR \"living alone\" OR \"car vlog\" OR влог) AND NOT title:(dev OR developer OR diary OR minecraft OR roblox OR game OR gaming OR gameplay OR \"let's play\" OR wow OR pax OR e3 OR gamescom OR comic OR con OR animated OR animation OR \"draw my life\" OR rant OR insider OR producer OR episode OR ep OR panel OR mtv OR clip OR trailer OR \"official video\" OR marijuana OR weed OR grow OR serial OR killer OR opinion OR opinión OR immigration OR inmigración OR roosh OR bynes OR orlando OR \"elliot rodger\" OR bgs OR paranormal OR septembre OR conspirationniste OR chandler OR \"chris chan\" OR samsung OR airasia OR reacting OR endure OR darksydephil OR halloween OR scary OR screamer OR prank OR \"nikki narcotic\") AND NOT creator:(\"CNA Insider\" OR TotalBiscuit OR GameSpot OR \"The Escapist\" OR VG247.com OR thecreaturehub OR \"Elliot Rodger\" OR \"Hannah Witton\" OR \"Intelligent Stoner\" OR \"Red Pill Philosophy\" OR retsupurae OR \"Tiffany Alvord\" OR pigwiththefaceofaboy OR \"Drunken Peasants\" OR 90sShowJames OR \"Roosh V\" OR TheRagMagRejects OR \"Lauren Orlando\" OR \"Johnny Orlando\" OR fefe448 OR jaybauman OR \"Ami Yamato\" OR ViralVideoLab OR Newsweek OR \"J'suis pas content TV\" OR \"Mike Diva\" OR \"Novi Stars\" OR Pedrodbr OR SaveCChandler OR \"Brian Maiorana\" OR \"airasia Super App\" OR \"Vic Berger\" OR UndoTube OR communitychannel OR Shoe0nHead OR xjunesVlogx OR AuronPlay OR BiGrV1213 OR \"Bonnie Bucqueroux\") |sort=downloads desc",
     "max_items": 4, "tags": ["vlog", "faces", "home", "voice", "modern", "social", "sincere"]},
]
_INTERNET_KINDS = {"vlog", "phone", "reels", "cctv", "liminal", "asmr"}
INTERNET_JOBS = NEW_INTERNET_JOBS + [
    j for j in CONTEMPORARY_JOBS
    if _INTERNET_KINDS & set(j["tags"]) and not {"beauty", "animals", "nature"} & set(j["tags"]) and j["provider"] == "archive"]
CONTEMPORARY_JOBS = CONTEMPORARY_JOBS + NEW_INTERNET_JOBS

# The sunset variation (`[ sunsets ]` in the controls): suns setting or low on the horizon, golden hour, dusk
# skies, afterglow, filmed by people. Every job is tagged sunset, which the export publishes within a budget of
# its own and the main mix leaves out; they ride in the contemporary rotation so weekly builds keep it fresh.
# Each was scouted through the provider and rated twice, by two readers on different result pages, and every item
# CI's page rotation (1-6) takes was looked at. Those found wanting (daytime, text on screen, a duplicate angle)
# are passed over with |skip=, which leaves every page where it was, so the rest stays as rated.
SUNSET_JOBS = [
    # Flickr: sunset and sunrise time-lapses over deserts, mountains, coasts and lakes, and clips titled in other
    # languages (atardecer, Sonnenuntergang, 日落...); city titles are left to the city job (rated 18/20 and 18/20)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND ((title:(sunset OR sunsets OR sunrise OR sunrises OR sundown OR afterglow OR \"golden hour\" OR \"setting sun\" OR \"sun sets\" OR \"sun setting\") AND title:(timelapse OR \"time lapse\" OR \"time-lapse\" OR timelapses OR hyperlapse OR \"time laps\" OR \"fast forward\" OR \"fast-motion\")) OR title:(atardecer OR \"puesta de sol\" OR sonnenuntergang OR \"coucher de soleil\" OR zonsondergang OR solnedgang OR solnedgangen OR solnedgång OR tramonto OR \"pôr do sol\" OR \"por do sol\" OR 夕陽 OR 日落 OR 夕焼け OR 夕日 OR 落日 OR 夕阳 OR 晚霞 OR 火燒雲 OR amanecer OR sonnenaufgang OR \"lever de soleil\" OR zonsopgang OR anochecer)) AND NOT title:(city OR skyline OR street OR streets OR bridge OR tower OR downtown OR rooftop OR roof OR building OR buildings OR manhattan OR nyc OR \"new york\" OR tokyo OR yokohama OR london OR paris OR amsterdam OR singapore OR \"san francisco\" OR chicago OR boston OR seattle OR brisbane OR taipei OR 台北 OR macau OR manila OR glasgow OR bern OR geneva OR milan OR rotterdam OR baltimore OR portland OR sydney OR melbourne OR \"hong kong\" OR westminster OR traffic OR highway OR freeway OR train OR tram OR cars OR shops OR port) AND NOT title:(Newark OR editado) |sort=downloads desc |skip=Flickr-30121944064,Flickr-41499479180,Flickr-3694135602,Flickr-7981216896,Flickr-7914860548,Flickr-14998348579,Flickr-5111863100",
     "max_items": 10, "tags": ["sunset", "light", "quiet", "nature", "modern"]},
    # TikTok: phone sunsets, Maldives beaches, the midnight sun in Finnmark, Paris rooftops, a red sky over a garden;
    # the pool is small and max_items covers it (rated 18/20 and 16/20; heavily graded posts excluded)
    {"provider": "archive", "query": "identifier:tiktok-* AND (sunset OR sunsets OR sunrise OR sunrises OR goldenhour OR \"golden hour\" OR sunsetlover OR sunsetlovers OR sunsetview OR sunsetvibes OR sunsetchaser OR sunsetphotography OR midnattsol OR midnattsola OR atardecer OR tramonto OR 夕焼け OR 夕日 OR \"red sky\" OR \"sky tonight\" OR \"pink sky\" OR \"orange sky\" OR \"evening sky\" OR \"sky on fire\") AND NOT creator:(_kristyjessica OR minitruckmommygarage OR okaygnomie OR pearlmania500 OR \"kidsnextdoor.18\" OR \"epic.sound.effects\" OR cristianbrennhovd OR gregley55 OR foofee_da_gamer OR tweetneypie OR ajplus OR \"squish.laplaza\" OR nearlybandori OR lamarrwilson OR mayliprop OR cherieluna_ OR heydearquincy OR \"dev.xxxx\" OR gin888 OR israel OR \"israel.films\" OR idf OR officialpeta OR \".listl\" OR justjolv) AND NOT (minecraft OR roblox OR game OR gamer OR gaming OR bloxfruits OR podcast OR lamp OR sunsetlamp OR controller OR debate OR movement OR outfit OR graduation OR grief OR capcut OR slideshow OR lyrics OR song OR cover OR dance OR trend OR hummingbird OR losingadog OR classroom) AND NOT identifier:TikTok-6949956977028107525 |sort=date desc",
     "max_items": 24, "tags": ["sunset", "light", "quiet", "modern", "phone", "nature"]},
    # The YouTube mirror's real sunsets: a place, a view, a time-lapse or a drone next to the word, songs, games,
    # festivals and streams left out; drone shorts, Bali and Idaho phone sunsets, Haleakala (rated 26/26 and 19/20)
    {"provider": "archive", "query": "collection:mirrortube AND title:(sunset OR sunsets OR sunrise OR sunrises OR dusk) AND (title:(beach OR ocean OR sea OR waves OR surf OR lake OR river OR creek OR bay OR harbour OR harbor OR coast OR island OR pier OR mountain OR mountains OR summit OR volcano OR hill OR desert OR field OR forest OR park OR sky OR clouds OR timelapse OR time-lapse OR \"time lapse\" OR hyperlapse OR drone OR fpv OR aerial OR 4k OR walk OR drive OR driving OR ride OR cruise OR boat OR flight OR plane OR takeoff OR window OR balcony OR rooftop OR birds OR beautiful OR amazing OR stunning OR gorgeous OR epic OR golden OR view OR views OR watching OR footage OR \"real time\" OR relaxing OR ambience OR nature OR skyline OR monica OR northwoods) OR creator:(scruffld OR loserlex OR vectorchaotix1 OR wootcrisp)) AND NOT title:(overdrive OR shimmer OR boulevard OR blvd OR strip OR limited OR crash OR survivors OR police OR fractal OR remix OR music OR song OR lyrics OR cover OR feat OR ncs OR copyright OR lofi OR synthwave OR mix OR demo OR album OR official OR teaser OR gameplay OR game OR games OR gaming OR playthrough OR minecraft OR roblox OR 2b2t OR botw OR movement OR elementary OR samsung OR galaxy OR iphone OR cannabis OR weed OR yoga OR reaping OR film OR films OR painting OR paint OR art OR speedpaint OR drawing OR animation OR animated OR render OR dprk OR pyongyang OR kill OR festival OR fancam OR concert OR dance OR compilation OR \"top 5\" OR most OR jvke OR service OR stream OR irl OR shot OR tour OR fallow OR reptiles OR roofing OR peaceful OR \"IG Story\" OR space OR cutecat OR catlover OR spooky OR resoloution) AND NOT creator:(news OR \"Bob Ross\" OR \"Maths Town\" OR Pogo OR \"Maximum Mellow\" OR Lichu OR \"Piper Blush\" OR \"chillin station\" OR Xinhua OR DPRK OR \"Benjamin Ratterman\" OR rAwTiMe OR \"Scandinavian Airlines\" OR \"Candy Yuen\" OR \"Top Fives\" OR \"Roland Fields TV\" OR ONSCENE OR \"Darya ASMR\" OR Yobelprize OR McDrod OR efryo) |sort=date desc |skip=youtube-4L1mo-qIi-U,youtube-qYLrCo-Ot-s,youtube-aRoykTXiVLQ,youtube-W92n0b_3x8U",
     "max_items": 8, "tags": ["sunset", "light", "quiet", "nature", "ocean", "phone", "modern"]},
    # Flickr: real-time sunsets and sunrises people filmed, beaches, piers, the sea, deserts, from planes and
    # balconies; newest first, so it reaches others than the beauty query does (rated 17/20 and 17/20)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(sunset OR sunsets OR sunrise OR sunrises OR sundown OR afterglow OR \"golden hour\" OR \"setting sun\" OR \"sun sets\" OR \"sun setting\") AND NOT title:(timelapse OR \"time lapse\" OR \"time-lapse\" OR timelapses OR hyperlapse OR \"time laps\" OR \"fast forward\" OR \"fast-motion\") AND NOT title:(city OR skyline OR street OR streets OR bridge OR tower OR downtown OR rooftop OR roof OR building OR buildings OR manhattan OR nyc OR \"new york\" OR tokyo OR yokohama OR london OR paris OR amsterdam OR singapore OR \"san francisco\" OR chicago OR boston OR seattle OR brisbane OR taipei OR 台北 OR macau OR manila OR glasgow OR bern OR geneva OR milan OR rotterdam OR baltimore OR portland OR sydney OR melbourne OR \"hong kong\" OR westminster OR traffic OR highway OR freeway OR train OR tram OR cars OR shops OR port) AND NOT title:(\"Sunset Dam\" OR \"Sunset Beach\" OR \"Sunset Camp\" OR \"Moon Palace\" OR \"Sunrise Lodge\" OR \"spine of the Blue Ridge\") |sort=date desc |skip=Flickr-43162323442,Flickr-41652606502,Flickr-29644881090,Flickr-27908116633,Flickr-18228914023,Flickr-13155285144,Flickr-15533933237,Flickr-15584067086",
     "max_items": 10, "tags": ["sunset", "light", "quiet", "nature", "modern"]},
    # Instagram: Puget Sound time-lapses, a kitesurfer against a red sea, a cockpit above the clouds at sunset, a
    # balcony over the sea in Buenos Aires; the pool is small and max_items covers it (rated 12/13 and 12/13)
    {"provider": "archive", "query": "identifier:instagram-* AND (sunset OR sunsets OR sunrise OR sunrises OR goldenhour OR \"golden hour\" OR atardecer OR atardeceres OR amanecer OR tramonto OR \"puesta de sol\" OR サンセット) AND NOT title:(mina_horie OR eyesofacres OR onlyindade OR teamfubon111_official OR roosterteeth OR earthlocus OR djlobsterdust OR tigerairaustralia OR flyvair OR olanactor OR airasia_jpn) AND NOT identifier:(Instagram-8ciT9gqtld OR Instagram-BTU85JdDSB- OR Instagram-B7ZcbIaJIDW) AND NOT (motionleap OR lightricks) |sort=date desc",
     "max_items": 15, "tags": ["sunset", "light", "quiet", "modern", "phone", "nature", "ocean"]},
    # The open sources besides Flickr: stock and CC clips, park-service sunsets, the LBRY mirror's Punta del Este,
    # community uploads that name a landscape; films, songs and place names left out (rated 20/20 and 16/20)
    {"provider": "archive", "query": "(identifier:nps-video-* OR collection:stock_footage OR identifier:(pixabay-* OR lbry-*) OR creator:(\"C. E. Price\") OR title:(\"CC BY Nature Clip\" OR \"stock footage\" OR \"free footage\" OR \"stock video\" OR \"free stock\" OR \"royalty free\" OR \"free hd\" OR \"free video\") OR (collection:opensource_movies AND title:(timelapse OR \"time lapse\" OR \"time-lapse\" OR beach OR ocean OR sea OR lake OR river OR bay OR mountain OR mountains OR sky OR clouds OR desert OR island OR pier OR harbor OR harbour OR coast OR field OR silhouette OR palm OR waves OR hills OR marsh OR pasture OR forest OR tree OR trees OR horizon OR pacific OR atlantic))) AND title:(sunset OR sunsets OR sunrise OR sunrises OR sundown OR \"golden hour\" OR afterglow OR alpenglow OR \"setting sun\" OR atardecer OR amanecer OR \"puesta de sol\") AND NOT collection:mirrortube AND NOT identifier:(youtube-* OR yt-archive-* OR loc-film-* OR nst-* OR IMB_SF_* OR RiverSunset OR PacificSunsetParagliders OR pixabay-4006 OR nps-video-grca-slow-pan-grand-canyon-winter-sunrise) AND NOT creator:(KandaoVR OR HPWERN OR \"Neal Herbert\") AND NOT subject:(\"DJ Mix\" OR \"deep house\" OR \"flat earth\") AND NOT title:(shelling OR donetsk OR animation OR animated OR render OR blender OR thumbnail OR \"sunset boulevard\" OR \"sunset strip\" OR \"sunset beach\" OR \"Sunset Crater\" OR \"Mount Rainier\" OR \"Louis Michot\" OR wildflowers OR \"Sunset Series\" OR \"Point Imperial\" OR \"Tower of Ra\" OR scouting OR epstein OR leagues OR \"play for today\" OR leaky OR girl OR girls OR \"studio 210\" OR gumi OR macross OR cover OR news OR dancers OR routine OR show OR \"here's how\" OR transition OR cruises OR jump OR \"electric forest\" OR balloon OR preview OR concept OR parrot OR \"sunset n sunrise\" OR ambience OR laptop OR Caustrita OR \"Hatchet Pond\" OR \"beach club\" OR pool OR bikini) |sort=downloads desc |skip=SunsetWavesClosseUp,SunsetWavesMediumShot,SunsetTimelapse003,Clip7PeopleOnABeachAtSunsetFishingAerialFootage,MVI3708,LonelyTreeAtSunset4KCCBYNatureClip,DenaliDayAndSunsetTimelapse,backgroundvideos,sunrise-sunset-time-lapse-27-september-2020-033,sunset-at-tywyn-beach,img-2970_202311,sunset-in-the-clouds",
     "max_items": 8, "tags": ["sunset", "light", "quiet", "nature", "modern"]},
    # YouTube mirrors kept outside mirrortube: sunset time-lapses and views, the Golden Gate's green flash, Acapulco
    # bay, saguaros at dusk; the chemtrail and politics uploads that crowd them excluded (rated 12/14 and 14/14)
    {"provider": "archive", "query": "identifier:youtube-* AND NOT collection:mirrortube AND title:(sunset OR sunsets OR sunrise OR sunrises OR dusk) AND (title:(timelapse OR time-lapse OR \"time lapse\" OR hyperlapse OR beach OR bay OR cove OR coast OR ocean OR sea OR island OR canyon OR desert OR valley OR clouds OR sky OR \"green flash\" OR beautiful OR tokyo) OR creator:(\"Urban Computing design\")) AND NOT title:(chemtrail OR chemtrails OR chemtrailing OR chemical OR nibiru OR niburu OR haarp OR geoengineering OR gaza OR palestine OR israel OR russia OR russian OR moscow OR ukraine OR sota OR hamradio OR morse OR doppler OR restaurant OR news OR police OR audit OR music OR song OR remix OR lyrics OR cover OR feat OR album OR game OR gameplay OR overdrive OR minecraft OR trailer OR review OR podcast OR interview OR painting OR speedpaint OR art OR animation OR render OR ufo OR alien OR flat OR conspiracy OR truth OR strip OR boulevard OR blvd OR movement OR \"american sunrise\" OR band OR marines OR 5s) AND NOT creator:(news OR \"Brutal Truth\" OR \"3rd World Man\" OR \"Chemtrail Crimes\" OR \"Good Prevails\" OR \"Real Russia\" OR \"EXPAT American\" OR \"Savage Audits\" OR \"Jason Bermas\" OR \"Ivory Hecker\" OR \"John Mark Dougan\" OR \"WTVR CBS 6\" OR N7KOM OR \"Ham Radio\" OR REALTRUTHTALK OR \"Canadian Infidel\" OR \"American Revolution\" OR YashiCroRiders OR \"Andy Dybala\") AND NOT identifier:(youtube-sSEqGoj1hLU OR youtube-6cbBSzBlDAw OR youtube-REkXAbQLMx4) |sort=downloads desc",
     "max_items": 14, "tags": ["sunset", "light", "quiet", "nature", "ocean", "modern"]},
    # Flickr, cities: skylines, bridges, ports and rooftops at sunset, tagged city so the stream can set them
    # against the open land (rated 17/20 and 15/20)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(sunset OR sunsets OR sunrise OR sunrises OR sundown OR afterglow OR \"golden hour\" OR \"setting sun\" OR \"sun sets\" OR 日落 OR 夕陽 OR atardecer OR sonnenuntergang OR zonsondergang OR tramonto OR \"coucher de soleil\") AND title:(city OR skyline OR street OR streets OR bridge OR tower OR downtown OR rooftop OR roof OR building OR buildings OR manhattan OR nyc OR \"new york\" OR tokyo OR yokohama OR london OR paris OR amsterdam OR singapore OR \"san francisco\" OR chicago OR boston OR seattle OR brisbane OR taipei OR 台北 OR macau OR manila OR glasgow OR bern OR geneva OR milan OR rotterdam OR baltimore OR portland OR sydney OR melbourne OR \"hong kong\" OR westminster OR traffic OR highway OR freeway OR train OR tram OR cars OR shops OR port) AND NOT title:(\"Sunset Camp\" OR \"Sunset Beach\" OR \"Lincoln City\" OR \"radar tower\") AND NOT (title:yokohama AND NOT title:(timelapse OR \"time-lapse\" OR \"time lapse\")) |sort=downloads desc |skip=Flickr-2710255155,Flickr-5212154567,Flickr-2719866525,Flickr-22284125821,Flickr-21109718929,Flickr-5384746047,Flickr-2710638732,Flickr-37349256100,Flickr-9362290199,Flickr-11243050343",
     "max_items": 6, "tags": ["sunset", "light", "quiet", "city", "modern"]},
    # Twitter: the few clean sunsets there, the Salar de Uyuni's mirror, a ring-of-fire sunrise, a sea cave, the
    # ISS crossing the terminator (a closed set of 6, rated 6/6 and 6/6)
    {"provider": "archive", "query": "identifier:twitter-* AND ((creator:(\"World Tourism\" OR \"Wonder of Science\" OR \"Crazy Science\") AND (sunset OR sunsets OR sunrise OR sunrises)) OR identifier:(twitter-1441354493640118282 OR twitter-1404384887642083329))",
     "max_items": 6, "tags": ["sunset", "light", "quiet", "modern", "nature"]},
    # Periscope: sunset walks along Devon's estuaries and the sea, short enough to ingest (rated 5/5 and 5/5)
    {"provider": "archive", "query": "identifier:periscope-* AND title:(sunset OR sunsets OR \"sky is on fire\") AND NOT creator:(kino) AND (item_size:[0 TO 100000000] OR identifier:periscope-1djGXoDLnlLKZ) |sort=downloads desc",
     "max_items": 5, "tags": ["sunset", "light", "quiet", "phone", "ocean", "nature", "modern"]},
]
CONTEMPORARY_JOBS = CONTEMPORARY_JOBS + SUNSET_JOBS

BEAUTY_JOBS = [j for j in CONTEMPORARY_JOBS if "beauty" in j["tags"]]
# the Twitter part (Periscope included), first in the owner's order, for runs that take more of its pages
TWITTER_JOBS = [j for j in INTERNET_JOBS if "twitter-" in j["query"] or "periscope-" in j["query"]]
SEED_SETS = {"contemporary": CONTEMPORARY_JOBS, "internet": INTERNET_JOBS, "twitter": TWITTER_JOBS, "beauty": BEAUTY_JOBS,
             "sunset": SUNSET_JOBS, "archival": ARCHIVAL_JOBS, "all": CONTEMPORARY_JOBS + ARCHIVAL_JOBS}
STARTER_JOBS = CONTEMPORARY_JOBS  # what `seed` and `build-site` use unless --set says otherwise
