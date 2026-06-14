import json

VALID_HUMAN_PRESENCE = [
    "none",
    "single_person",
    "hands_only",
    "distant_figure",
]

DEFAULT_CLICHE_AVOID = [
    "mug",
    "notebook",
    "table",
    "window",
    "beach",
    "human",
    "crowd",
    "extra people",
    "generic wellness stock photo",
]

DEFAULT_SCENE_FALLBACK_ORDER = [
    "forest_path",
    "open_meadow",
    "garden_morning",
]

GENERIC_SCENE_CANDIDATES = [
    "forest_path",
    "open_meadow",
    "garden_morning",
    "riverside",
    "mountain_view",
    "sunrise_field",
    "autumn_park",
    "quiet_city_morning",
    "city_park",
    "library_corner",
    "hands_detail",
    "abstract_light",
    "calm_cafe_corner",
    "city_park_before_work",
    "office_morning_light",
]

SCENE_PRESETS = {
    "forest_path": {
        "setting": "quiet forest path with soft morning light, wildflowers, a few butterflies and subtle bird movement in the trees",
        "main_subject": "narrow path between trees, tall grasses and small signs of life rather than an empty desolate landscape",
        "visual_motifs": ["forest", "path", "morning_light", "wildflowers", "butterflies", "birds"],
        "composition": "wide natural landscape, open depth, not table-centered",
        "lighting": "soft morning light",
        "mood": "quiet self-trust and spaciousness",
        "avoid": ["desolate emptiness", "eerie lifeless landscape"],
    },
    "open_meadow": {
        "setting": "open meadow with airy horizon, gentle daylight, wildflowers and a few bees or dragonflies moving through the grass",
        "main_subject": "grasses, wildflowers and light natural movement instead of a barren empty field",
        "visual_motifs": ["meadow", "field", "open_space", "wildflowers", "bees", "dragonflies"],
        "composition": "wide open landscape with breathing space",
        "lighting": "clear soft daylight",
        "mood": "freedom, lightness and inner steadiness",
        "avoid": ["desolate emptiness", "eerie lifeless landscape"],
    },
    "garden_morning": {
        "setting": "calm garden in the morning with dew, soft light, flowering plants and a few butterflies or bees among the leaves",
        "main_subject": "garden path, flowering plants and lived-in fresh air with small natural movement",
        "visual_motifs": ["garden", "flowers", "morning_light", "butterflies", "bees"],
        "composition": "balanced garden scene with natural depth",
        "lighting": "fresh morning light",
        "mood": "gentle renewal and calm optimism",
        "avoid": ["desolate emptiness", "eerie lifeless landscape"],
    },
    "quiet_city_morning": {
        "setting": "quiet city street in the early morning",
        "main_subject": "empty urban street with soft reflections and stillness",
        "visual_motifs": ["city", "street", "morning_light"],
        "composition": "clean urban perspective with open foreground",
        "lighting": "soft cool morning light",
        "mood": "clarity, dignity and calm forward movement",
    },
    "botanical_still_life": {
        "setting": "refined botanical still life in natural daylight",
        "main_subject": "plant forms and flowers arranged with calm simplicity",
        "visual_motifs": ["flowers", "plant", "botanical"],
        "composition": "minimal still life with elegant negative space",
        "lighting": "soft window-adjacent daylight",
        "mood": "quiet care and grounded beauty",
    },
    "hands_detail": {
        "setting": "close lifestyle scene focused on hands and meaningful detail",
        "main_subject": "hands interacting with natural objects or fabric",
        "visual_motifs": ["hands", "detail", "presence"],
        "composition": "close but uncluttered detail shot",
        "lighting": "soft directional daylight",
        "mood": "intimacy, tenderness and grounded attention",
    },
    "mountain_view": {
        "setting": "clear mountain view with expansive air and distance",
        "main_subject": "mountain ridges and open horizon",
        "visual_motifs": ["mountain", "horizon", "open_space"],
        "composition": "wide landscape with layered depth",
        "lighting": "clean natural daylight",
        "mood": "perspective, resilience and calm strength",
    },
    "riverside": {
        "setting": "quiet riverside with gentle current and soft greenery",
        "main_subject": "water edge with grasses and calm reflections",
        "visual_motifs": ["riverside", "water", "greenery"],
        "composition": "grounded riverside scene with gentle leading lines",
        "lighting": "soft daylight with light reflections on water",
        "mood": "flow, calm trust and restoration",
    },
    "library_corner": {
        "setting": "peaceful library corner with soft ambient light, books, a reading chair, lamp glow and a lived-in reflective atmosphere",
        "main_subject": "shelves, chair, books and warm reading details rather than a sterile empty room",
        "visual_motifs": ["library", "books", "quiet_interior", "lamp", "reading_chair"],
        "composition": "intimate interior corner with depth and order",
        "lighting": "warm diffused interior light",
        "mood": "reflection, clarity and inward calm",
        "avoid": ["sterile empty room", "cold office mood"],
    },
    "abstract_light": {
        "setting": "abstract light-filled scene with atmospheric softness",
        "main_subject": "shapes of light, shadow and luminous texture",
        "visual_motifs": ["abstract_light", "glow", "air"],
        "composition": "open abstract composition with spacious balance",
        "lighting": "luminous diffused light",
        "mood": "subtle hope and emotional spaciousness",
    },
    "balcony_garden": {
        "setting": "small balcony garden with fresh air and city quietness",
        "main_subject": "plants, railing light and morning openness",
        "visual_motifs": ["garden", "balcony", "plants"],
        "composition": "layered small-space scene with outward view",
        "lighting": "fresh morning daylight",
        "mood": "small daily joy and grounded optimism",
    },
    "rain_window": {
        "setting": "quiet rain-lit window scene with reflective calm",
        "main_subject": "rain traces, soft glass reflections and light",
        "visual_motifs": ["window", "rain", "light"],
        "composition": "simple reflective composition with soft depth",
        "lighting": "muted rainy daylight",
        "mood": "introspection and emotional softness",
    },
    "autumn_park": {
        "setting": "autumn park with warm leaves and calm pathways",
        "main_subject": "park path framed by autumn trees",
        "visual_motifs": ["path", "trees", "seasonal_leaves"],
        "composition": "gentle park perspective with warm texture",
        "lighting": "soft autumn daylight",
        "mood": "maturity, grounding and peaceful change",
    },
    "sunrise_field": {
        "setting": "sunrise field with open sky and first warm light",
        "main_subject": "field grasses glowing in early sun",
        "visual_motifs": ["sunrise", "field", "open_light"],
        "composition": "wide field scene with clean horizon",
        "lighting": "golden sunrise light",
        "mood": "renewal, hope and quiet beginning",
    },
    "wild_grass_field": {
        "setting": "wild grass field with airy movement and bright open sky",
        "main_subject": "tall untamed grasses bending in a gentle breeze",
        "visual_motifs": ["field", "grass", "wind"],
        "composition": "wide field view with textured foreground and deep horizon",
        "lighting": "clear daylight with soft shimmer on grasses",
        "mood": "untamed freedom and calm aliveness",
    },
    "lake_shore": {
        "setting": "quiet lake shore with still water and soft natural air",
        "main_subject": "shoreline plants and calm water edge",
        "visual_motifs": ["water", "shore", "greenery"],
        "composition": "grounded shoreline scene with open reflective space",
        "lighting": "soft daylight with gentle water reflections",
        "mood": "ease, calm regulation and open breathing space",
    },
    "tree_canopy": {
        "setting": "upward view through tree canopy with moving leaves and light",
        "main_subject": "branches and leaves against bright open sky",
        "visual_motifs": ["trees", "leaves", "sky_light"],
        "composition": "upward-looking composition with layered natural patterns",
        "lighting": "sunlight filtering through leaves",
        "mood": "lift, freshness and quiet wonder",
    },
    "flowering_garden_path": {
        "setting": "flowering garden path with depth, color and fresh outdoor air",
        "main_subject": "garden path framed by flowering plants and soft greenery",
        "visual_motifs": ["garden", "path", "flowers"],
        "composition": "natural leading lines through a richly planted garden",
        "lighting": "fresh morning or late-afternoon garden light",
        "mood": "gentle delight and grounded optimism",
    },
    "rain_on_leaves": {
        "setting": "close outdoor scene of rain on leaves and fresh green texture",
        "main_subject": "leaf surfaces with raindrops and soft background depth",
        "visual_motifs": ["rain", "leaves", "greenery"],
        "composition": "close natural detail with soft layered depth",
        "lighting": "diffused rainy daylight",
        "mood": "refreshment, reset and emotional softening",
    },
    "sea_horizon": {
        "setting": "open sea horizon with calm waves and broad air",
        "main_subject": "clean horizon line over open water",
        "visual_motifs": ["sea", "horizon", "waves"],
        "composition": "wide coastal landscape with open distance",
        "lighting": "clear natural coastal daylight",
        "mood": "space, release and calm perspective",
    },
    "coastal_morning": {
        "setting": "quiet coast in the morning with gentle surf and fresh air",
        "main_subject": "shoreline and soft rhythmic waves",
        "visual_motifs": ["coast", "shoreline", "morning_light"],
        "composition": "balanced coastal scene with shoreline depth",
        "lighting": "fresh morning coastal light",
        "mood": "clean renewal and quiet steadiness",
    },
    "dune_grass": {
        "setting": "coastal dune grass under open sky and airy sea light",
        "main_subject": "wind-shaped dune grass and sandy natural textures",
        "visual_motifs": ["coast", "grass", "dunes"],
        "composition": "low natural foreground with open coastal background",
        "lighting": "bright coastal daylight",
        "mood": "light resilience and healthy spaciousness",
    },
    "rocky_shore": {
        "setting": "rocky shore with textured stone and moving water",
        "main_subject": "wet rocks and wave edges in a calm natural coastal frame",
        "visual_motifs": ["rocks", "shore", "waves"],
        "composition": "structured shoreline composition with strong natural forms",
        "lighting": "clean outdoor light with crisp contrast",
        "mood": "strength, grounding and emotional clarity",
    },
    "quiet_pier": {
        "setting": "quiet pier or boardwalk edge opening into broad water and sky",
        "main_subject": "simple pier line leading into open coastal space",
        "visual_motifs": ["pier", "water", "horizon"],
        "composition": "leading-line composition into calm open distance",
        "lighting": "soft coastal daylight",
        "mood": "pause, perspective and calm direction",
    },
    "city_park": {
        "setting": "quiet city park with open pathways and softened urban edges",
        "main_subject": "park walkway, trees and calm city background",
        "visual_motifs": ["park", "city", "path"],
        "composition": "urban-nature balance with open foreground",
        "lighting": "soft morning or overcast daylight",
        "mood": "gentle forward movement and grounded clarity",
    },
    "soft_color_gradient": {
        "setting": "abstract scene of soft color gradient and airy luminosity",
        "main_subject": "flow of light and color without concrete objects",
        "visual_motifs": ["abstract_light", "gradient", "glow"],
        "composition": "minimal spacious abstract composition",
        "lighting": "luminous blended light",
        "mood": "subtle hope and emotional ease",
    },
    "water_reflection": {
        "setting": "abstracted reflection on water with light, motion and softness",
        "main_subject": "rippling reflected light and blurred natural tones",
        "visual_motifs": ["water", "reflection", "light"],
        "composition": "meditative reflective surface with gentle rhythm",
        "lighting": "shimmering diffused natural light",
        "mood": "inner stillness and fluid calm",
    },
    "hands_with_leaf": {
        "setting": "close natural detail of hands holding a leaf in daylight",
        "main_subject": "hands and leaf texture as grounded focal detail",
        "visual_motifs": ["hands", "leaf", "detail"],
        "composition": "close tactile composition with clean negative space",
        "lighting": "soft directional natural light",
        "mood": "care, grounding and quiet presence",
    },
    "hands_with_fabric": {
        "setting": "close detail of hands with soft fabric in natural light",
        "main_subject": "hands interacting with fabric folds and texture",
        "visual_motifs": ["hands", "fabric", "detail"],
        "composition": "close intimate frame with simple tactile focus",
        "lighting": "gentle side light",
        "mood": "comfort, tenderness and self-support",
    },
    "reading_corner": {
        "setting": "calm reading corner with chair, shelf and quiet soft light",
        "main_subject": "reading chair and surrounding quiet interior atmosphere",
        "visual_motifs": ["reading", "chair", "quiet_interior"],
        "composition": "cozy interior corner with depth and breathing space",
        "lighting": "soft interior daylight",
        "mood": "rest, reflection and grounded comfort",
    },
    "calm_room_wide": {
        "setting": "wide calm room with minimal objects and open restful space",
        "main_subject": "simple interior volume and soft atmosphere rather than props",
        "visual_motifs": ["room", "space", "quiet_interior"],
        "composition": "wide uncluttered interior with open negative space",
        "lighting": "soft diffused daylight",
        "mood": "calm order and emotional spaciousness",
    },
    "calm_cafe_corner": {
        "setting": "calm lived-in cafe corner with terrace-adjacent light, menu card, one or two coffee cups and a few quiet guests in the background",
        "main_subject": "small cafe seating area, warm room atmosphere and distant calm guests rather than a close-up table object or a single cup",
        "visual_motifs": ["cafe", "quiet_corner", "morning_light", "menu_card", "background_guests"],
        "composition": "wide cafe environment with breathing space, small tables as supporting details, not mug-centered and not tabletop close-up",
        "lighting": "soft morning window light across the room",
        "mood": "calm readiness, collected focus and grounded ease",
        "avoid": [
            "empty abandoned cafe",
            "post-apocalyptic street",
            "deserted showroom",
            "sterile dining room",
            "empty classroom",
            "no people anywhere",
            "crowded noisy scene",
        ],
    },
    "quiet_cafe_window": {
        "setting": "quiet cafe by a broad window with terrace seating, city street view, a menu card and a few calm guests at distant tables",
        "main_subject": "cafe interior volume, soft exterior light, small tables and distant seated guests rather than drink props",
        "visual_motifs": ["cafe", "window_light", "urban_morning", "terrace", "background_guests"],
        "composition": "room-focused composition with depth, city-facing openness and no object close-up",
        "lighting": "gentle side light from a large window",
        "mood": "clear thinking and quiet professional steadiness",
        "avoid": [
            "empty abandoned cafe",
            "post-apocalyptic street",
            "deserted showroom",
            "sterile dining room",
            "empty classroom",
            "no people anywhere",
            "crowded noisy scene",
        ],
    },
    "bookstore_cafe": {
        "setting": "peaceful bookstore cafe with shelves, warm order, a menu card, one or two coffee cups and a few calm guests in the background",
        "main_subject": "bookshelves, seating and a lived-in reading-cafe atmosphere rather than table details or a laptop hero shot",
        "visual_motifs": ["books", "cafe", "shelves", "menu_card", "background_guests"],
        "composition": "layered interior with shelves, open walkway and calm background presence",
        "lighting": "warm diffused daylight with soft ambient glow",
        "mood": "thoughtful confidence and gentle concentration",
        "avoid": [
            "empty abandoned cafe",
            "post-apocalyptic street",
            "deserted showroom",
            "sterile dining room",
            "empty classroom",
            "no people anywhere",
            "crowded noisy scene",
        ],
    },
    "city_park_before_work": {
        "setting": "city park in the early morning before work with open paths and composed air",
        "main_subject": "pathway, trees and subtle city structures in the distance",
        "visual_motifs": ["park", "city", "morning_path"],
        "composition": "balanced path scene with urban calm in the background",
        "lighting": "fresh early daylight",
        "mood": "preparedness, clarity and grounded momentum",
    },
    "courtyard_morning": {
        "setting": "quiet courtyard in the morning with clean lines, trees and soft city light",
        "main_subject": "courtyard space, passageway and morning openness",
        "visual_motifs": ["courtyard", "city", "morning_light"],
        "composition": "architectural calm with open foreground",
        "lighting": "soft reflected daylight",
        "mood": "stability, order and quiet confidence",
    },
    "bridge_walkway": {
        "setting": "quiet bridge walkway with open perspective and steady urban air",
        "main_subject": "walkway lines leading forward across water or city space",
        "visual_motifs": ["bridge", "walkway", "urban_space"],
        "composition": "strong leading lines with open forward depth",
        "lighting": "clear morning or overcast urban light",
        "mood": "direction, resolve and steady forward movement",
    },
    "street_after_rain": {
        "setting": "quiet city street after rain with reflective pavement and softened motion",
        "main_subject": "street reflections, facades and calm empty passage",
        "visual_motifs": ["street", "rain_reflection", "city"],
        "composition": "clean street perspective with reflective foreground",
        "lighting": "soft overcast light with reflected glow",
        "mood": "reset, composure and thoughtful clarity",
    },
    "tram_stop_morning": {
        "setting": "calm tram stop in the morning with clean structure and urban stillness",
        "main_subject": "shelter lines, empty platform and open street atmosphere",
        "visual_motifs": ["tram_stop", "city", "morning_commute"],
        "composition": "structured urban frame with open waiting space",
        "lighting": "soft cool daylight",
        "mood": "quiet anticipation and grounded readiness",
    },
    "office_morning_light": {
        "setting": "quiet professional office in the morning with sunlight, a plant, tasteful stationery, notebook planner, coffee cup and calm order",
        "main_subject": "room atmosphere, shelves or desk area as part of a wider environment rather than a cold empty office or laptop close-up",
        "visual_motifs": ["office", "morning_light", "professional_space", "stationery", "planner", "plant"],
        "composition": "wide professional interior with open negative space and balanced work detail, not productivity-stock close-up",
        "lighting": "soft daylight across a calm work setting",
        "mood": "collected competence and steady focus",
        "avoid": ["cold empty office", "generic productivity stock photo"],
    },
    "coworking_quiet_corner": {
        "setting": "quiet coworking corner with natural light, a plant, tasteful stationery, coffee cup and composed professional atmosphere",
        "main_subject": "seating area, shelves and calm shared workspace with lived-in professional detail rather than devices as focal point",
        "visual_motifs": ["coworking", "quiet_corner", "work_space", "stationery", "coffee_cup", "plant"],
        "composition": "environment-focused scene with layered depth and no close object hero",
        "lighting": "soft daylight with warm interior balance",
        "mood": "professional calm and thoughtful momentum",
        "avoid": ["cold empty office", "generic productivity stock photo"],
    },
    "street_cafe_terrace": {
        "setting": "street cafe terrace with awning shade, planters, menu card, one or two coffee cups and a few calm guests at distant tables",
        "main_subject": "terrace seating, facade details and quiet city street life rather than a cup close-up or empty dining hall",
        "visual_motifs": ["cafe", "terrace", "city_morning", "planters", "background_guests"],
        "composition": "wide terrace scene with small tables as supporting details, city street view and no tabletop hero framing",
        "lighting": "soft morning daylight with gentle facade reflections",
        "mood": "social ease, composure and light urban openness",
        "avoid": [
            "empty abandoned cafe",
            "post-apocalyptic street",
            "deserted showroom",
            "sterile dining room",
            "empty classroom",
            "no people anywhere",
            "crowded noisy scene",
        ],
    },
    "city_veranda_morning": {
        "setting": "quiet city veranda in the morning with terrace seating, planters, awning detail and a few calm guests in the background",
        "main_subject": "veranda atmosphere, soft street-facing depth and lived-in cafe detail rather than object close-ups",
        "visual_motifs": ["veranda", "city", "morning_light", "terrace", "background_guests"],
        "composition": "balanced semi-outdoor composition with depth, breathing room and calm background presence",
        "lighting": "fresh morning daylight",
        "mood": "calm anticipation and gentle urban optimism",
        "avoid": [
            "empty abandoned cafe",
            "post-apocalyptic street",
            "deserted showroom",
            "sterile dining room",
            "empty classroom",
            "no people anywhere",
            "crowded noisy scene",
        ],
    },
    "courtyard_cafe": {
        "setting": "courtyard cafe with greenery, terrace seating, menu card and a few calm guests under soft morning light",
        "main_subject": "courtyard seating area, planted edges and warm cafe atmosphere rather than food or drink close-ups",
        "visual_motifs": ["courtyard", "cafe", "greenery", "terrace", "background_guests"],
        "composition": "open courtyard composition with layered space, soft architecture and calm background life",
        "lighting": "soft reflected daylight",
        "mood": "settled confidence and quiet sociability",
        "avoid": [
            "empty abandoned cafe",
            "post-apocalyptic street",
            "deserted showroom",
            "sterile dining room",
            "empty classroom",
            "no people anywhere",
            "crowded noisy scene",
        ],
    },
    "sidewalk_cafe_after_rain": {
        "setting": "sidewalk cafe after rain with reflective pavement, terrace seating, awning detail and a few calm guests under shelter",
        "main_subject": "terrace edge, menu card, street reflections and quiet lived-in cafe detail rather than tabletop objects",
        "visual_motifs": ["cafe", "rain_reflection", "street", "awning", "background_guests"],
        "composition": "street-facing cafe scene with reflective foreground, open depth and calm background presence",
        "lighting": "muted post-rain daylight with gentle glow",
        "mood": "reset, thoughtfulness and calm urban rhythm",
        "avoid": [
            "empty abandoned cafe",
            "post-apocalyptic street",
            "deserted showroom",
            "sterile dining room",
            "empty classroom",
            "no people anywhere",
            "crowded noisy scene",
        ],
    },
    "village_veranda": {
        "setting": "village veranda with morning air, wood textures, potted flowers, a cup of tea and simple lived-in calm",
        "main_subject": "porch space, chairs, surrounding garden hints and maybe a small domestic animal in the distance in a rural home setting",
        "visual_motifs": ["veranda", "wood", "rural_home", "potted_flowers", "tea_cup"],
        "composition": "open porch composition with soft depth and grounded domestic detail",
        "lighting": "warm morning daylight",
        "mood": "rest, safety and gentle rootedness",
        "avoid": ["desolate emptiness", "eerie lifeless rural scene"],
    },
    "cottage_garden": {
        "setting": "cottage garden with path, flowers and a calm home atmosphere nearby",
        "main_subject": "garden edges and cottage details rather than wild open landscape",
        "visual_motifs": ["garden", "cottage", "flowers"],
        "composition": "garden path composition with home detail in the background",
        "lighting": "fresh daylight with soft floral highlights",
        "mood": "belonging, care and steady restoration",
    },
    "orchard_morning": {
        "setting": "orchard in the morning with fruit trees, dew, birds, butterflies and open countryside air",
        "main_subject": "rows of trees, grassy ground and small signs of life in a cared-for rural landscape",
        "visual_motifs": ["orchard", "trees", "morning_air", "birds", "butterflies"],
        "composition": "layered orchard view with grounded natural rhythm",
        "lighting": "clear early daylight",
        "mood": "abundance, softness and calm steadiness",
        "avoid": ["desolate emptiness", "eerie lifeless rural scene"],
    },
    "country_road": {
        "setting": "quiet country road with fields, fences, wildflowers and slow rural morning light",
        "main_subject": "simple road line leading through calm countryside with birds, grasses and signs of care",
        "visual_motifs": ["country_road", "fields", "rural_space", "wildflowers", "birds"],
        "composition": "open leading-line landscape with rural detail",
        "lighting": "soft golden morning light",
        "mood": "direction, patience and grounded calm",
        "avoid": ["desolate emptiness", "eerie lifeless rural scene"],
    },
    "farmhouse_kitchen_window": {
        "setting": "farmhouse kitchen by a window with natural materials and lived-in warmth",
        "main_subject": "wide home atmosphere with shelves, curtains and daylight rather than tabletop close-up",
        "visual_motifs": ["farmhouse", "kitchen", "window_light"],
        "composition": "wide home interior with airy spacing and no mug hero object",
        "lighting": "soft window daylight",
        "mood": "safety, nourishment and domestic ease",
    },
    "greenhouse_calm": {
        "setting": "quiet greenhouse with plants, glass and soft humid daylight",
        "main_subject": "greenhouse path and layered plant life in a calm tended setting",
        "visual_motifs": ["greenhouse", "plants", "garden_path"],
        "composition": "deep greenhouse perspective with gentle botanical structure",
        "lighting": "diffused daylight through glass",
        "mood": "renewal, patience and living support",
    },
    "wooden_porch": {
        "setting": "wooden porch with soft rural light, simple seating, a blanket, a cup of tea and open air",
        "main_subject": "porch boards, railing, surrounding countryside hints and gentle lived-in comfort",
        "visual_motifs": ["porch", "wood", "open_air", "blanket", "tea_cup"],
        "composition": "grounded porch scene with outward depth",
        "lighting": "warm daylight with gentle shadow lines",
        "mood": "quiet shelter and practical comfort",
        "avoid": ["desolate emptiness", "eerie lifeless rural scene"],
    },
    "field_edge_sunrise": {
        "setting": "field edge at sunrise with tall grasses and a nearby rural path",
        "main_subject": "field border and soft early light across open land",
        "visual_motifs": ["field_edge", "sunrise", "grass"],
        "composition": "open field-edge scene with delicate horizon",
        "lighting": "early sunrise glow",
        "mood": "hope, steadiness and new-day softness",
    },
    "bench_under_tree_near_cottage": {
        "setting": "bench under a tree near a cottage with calm shade and garden quiet",
        "main_subject": "simple bench, tree canopy and cottage-side stillness",
        "visual_motifs": ["bench", "tree", "cottage"],
        "composition": "restful outdoor nook with anchored focal point",
        "lighting": "soft filtered daylight through leaves",
        "mood": "pause, comfort and gentle support",
    },
    "warm_living_room": {
        "setting": "warm living room with soft light, quiet order, a book, blanket, lamp, mug and plant in lived-in calm",
        "main_subject": "room atmosphere, chair, shelf, lamp and home details rather than sterile decorative props alone",
        "visual_motifs": ["living_room", "lamp", "soft_home", "book", "blanket", "plant"],
        "composition": "wide room-focused composition with breathing space",
        "lighting": "warm diffused daylight or lamp glow",
        "mood": "safety, comfort and grounded ease",
        "avoid": ["sterile empty room", "furniture showroom"],
    },
    "fireplace_reading_chair": {
        "setting": "reading chair by a fireplace with calm home light, a blanket, book and quiet warmth",
        "main_subject": "chair, hearth glow and surrounding cozy atmosphere with lived-in reading detail",
        "visual_motifs": ["chair", "fireplace", "reading_home", "blanket", "book"],
        "composition": "cozy corner composition centered on atmosphere, not object close-up",
        "lighting": "soft mixed firelight and ambient room light",
        "mood": "restoration, warmth and emotional shelter",
        "avoid": ["sterile empty room", "furniture showroom"],
    },
    "lamp_and_bookshelf": {
        "setting": "bookshelf and lamp in a calm home corner with warm evening softness, books, a plant and a small lived-in mug detail",
        "main_subject": "shelf rhythm, lamp glow and quiet home order rather than a sterile showroom corner",
        "visual_motifs": ["bookshelf", "lamp", "home_corner", "books", "plant", "mug"],
        "composition": "simple vertical interior composition with gentle negative space",
        "lighting": "warm lamp light with soft ambient balance",
        "mood": "continuity, steadiness and thoughtful calm",
        "avoid": ["sterile empty room", "furniture showroom"],
    },
    "fireplace_library": {
        "setting": "library room with fireplace, shelves and a quiet reflective atmosphere",
        "main_subject": "bookshelves and hearth glow in a calm reading environment",
        "visual_motifs": ["library", "fireplace", "books"],
        "composition": "layered interior with quiet depth and no office mood",
        "lighting": "warm ambient light with gentle fire glow",
        "mood": "reflection, depth and protected calm",
    },
    "bookshop_aisle": {
        "setting": "quiet bookshop aisle with shelves, soft light and a thoughtful atmosphere",
        "main_subject": "walkway between bookshelves and calm bookstore rhythm",
        "visual_motifs": ["bookshop", "shelves", "walkway"],
        "composition": "aisle perspective with layered shelf depth",
        "lighting": "warm diffused daylight or interior glow",
        "mood": "curiosity, focus and quiet inspiration",
    },
}


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return []


def _clean_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe_stable(items: list) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = _clean_str(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_human_presence(value) -> str:
    text = _clean_str(value)
    if text in VALID_HUMAN_PRESENCE:
        return text
    return "none"


def _has_professional_theme_context(
    *,
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
    selected_style: str | None = None,
    resolved_style: str | None = None,
    style_mode: str | None = None,
) -> bool:
    haystack = " ".join(
        text.lower()
        for text in (
            _clean_str(sphere),
            _clean_str(subsphere),
            _clean_str(focus_title),
            _clean_str(selected_style),
            _clean_str(resolved_style),
            _clean_str(style_mode),
        )
        if text
    )
    keywords = (
        "money",
        "finance",
        "financial",
        "career",
        "work",
        "professional",
        "job",
        "stability",
        "достаточность",
        "деньги",
        "финансы",
        "карьера",
        "работа",
        "профессион",
        "устойчив",
    )
    return any(keyword in haystack for keyword in keywords)


def resolve_scene_style_family(
    *,
    selected_style: str | None = None,
    resolved_style: str | None = None,
    visual_mode: str | None = None,
    style_mode: str | None = None,
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
) -> str:
    values = " ".join(
        text.lower()
        for text in (
            _clean_str(selected_style),
            _clean_str(resolved_style),
            _clean_str(visual_mode),
            _clean_str(style_mode),
        )
        if text
    )
    if any(marker in values for marker in ("living_nature_photo", "sunny_nature_photo", "living nature", "живая природа")):
        return "living_nature"
    if any(marker in values for marker in ("urban_city_photo", "city style", "городской стиль")):
        return "urban"
    if any(marker in values for marker in ("cafe_terrace_photo", "cafe terrace", "кафе и городские веранды")):
        return "cafe_terrace"
    if any(marker in values for marker in ("rural_calm_photo", "rural calm", "сельское спокойствие")):
        return "rural_calm"
    if any(marker in values for marker in ("cozy_home_photo", "уютный дом", "home_support", "home and grounding")):
        return "cozy_home"
    if any(marker in values for marker in ("book_nook_photo", "книжный уголок", "book nook")):
        return "book_nook"
    if any(marker in values for marker in ("sea_coast_photo", "bright_ocean_coast_photo", "coast", "coastal", "beach", "ocean", "sea_horizon")):
        return "coastal"
    if any(marker in values for marker in ("minimal_botanical", "botanical", "garden", "plant")):
        return "botanical"
    if any(marker in values for marker in ("light_interior_photo", "calm_lifestyle_photo", "quiet_interior", "interior", "cozy")):
        return "interior_cozy"
    if any(marker in values for marker in ("city", "urban")):
        return "urban"
    if any(marker in values for marker in ("abstract", "symbolic", "ethereal", "collage")):
        return "abstract_symbolic"
    if any(marker in values for marker in ("hands", "detail")):
        return "hands_detail"
    if _has_professional_theme_context(
        sphere=sphere,
        subsphere=subsphere,
        focus_title=focus_title,
        selected_style=selected_style,
        resolved_style=resolved_style,
        style_mode=style_mode,
    ):
        return "professional_calm"
    if "photo" in values:
        return "photo_general"
    return "generic"


def normalize_scene_family(scene_type: str | None) -> str | None:
    scene = _clean_str(scene_type)
    if not scene:
        return None
    mapping = {
        "nature_path": {"forest_path", "outdoor_path", "woodland_trail", "tree_canopy", "flowering_garden_path", "autumn_park"},
        "meadow_field": {"open_meadow", "sunrise_field", "wild_grass_field"},
        "garden_botanical": {"garden_morning", "botanical_still_life", "balcony_garden", "flowering_garden_path", "rain_on_leaves"},
        "water_nature": {"riverside", "lake_shore"},
        "mountain": {"mountain_view"},
        "urban_quiet": {"quiet_city_morning", "urban_street", "street_after_rain", "tram_stop_morning", "bridge_walkway"},
        "urban_green": {"city_park", "city_park_before_work", "courtyard_morning"},
        "cafe_terrace": {"street_cafe_terrace", "city_veranda_morning", "courtyard_cafe", "sidewalk_cafe_after_rain"},
        "cafe_quiet": {"calm_cafe_corner", "quiet_cafe_window", "bookstore_cafe"},
        "work_quiet": {"office_morning_light", "coworking_quiet_corner"},
        "rural_quiet": {"village_veranda", "country_road", "wooden_porch"},
        "country_garden": {"cottage_garden", "orchard_morning", "greenhouse_calm", "bench_under_tree_near_cottage", "field_edge_sunrise"},
        "farmhouse_cozy": {"farmhouse_kitchen_window"},
        "cozy_home": {"warm_living_room", "fireplace_reading_chair", "soft_blanket_corner", "lamp_and_bookshelf", "calm_room_wide", "morning_light_wall"},
        "book_nook": {"library_corner", "reading_chair", "fireplace_library", "bookshop_aisle", "reading_corner"},
        "hands_detail": {"hands_detail", "hands_with_leaf", "hands_with_fabric", "hand_on_tree_bark"},
        "abstract_light": {"abstract_light", "soft_color_gradient", "water_reflection", "paper_shadow", "sky_light"},
        "interior_quiet": {"library_corner", "cozy_room", "reading_corner", "calm_room_wide"},
        "desk_workspace": {"desk_journaling", "workspace_corner"},
        "coastal": {"coastal_morning", "beach_path", "sea_horizon", "dune_grass", "rocky_shore", "quiet_pier", "rocky_coast", "coastal_path"},
        "window_scene": {"rain_window", "window_light"},
    }
    for family, members in mapping.items():
        if scene in members:
            return family
    return scene


def get_scene_candidates_for_style(
    *,
    selected_style: str | None = None,
    resolved_style: str | None = None,
    visual_mode: str | None = None,
    style_mode: str | None = None,
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
    visual_memory_context: dict | None = None,
) -> list[str]:
    family = resolve_scene_style_family(
        selected_style=selected_style,
        resolved_style=resolved_style,
        visual_mode=visual_mode,
        style_mode=style_mode,
        sphere=sphere,
        subsphere=subsphere,
        focus_title=focus_title,
    )
    pools = {
        "professional_calm": [
            "quiet_city_morning",
            "calm_cafe_corner",
            "bookstore_cafe",
            "city_park_before_work",
            "courtyard_morning",
            "office_morning_light",
            "coworking_quiet_corner",
            "bridge_walkway",
            "street_after_rain",
            "tram_stop_morning",
            "library_corner",
        ],
        "cafe_terrace": [
            "street_cafe_terrace",
            "city_veranda_morning",
            "courtyard_cafe",
            "sidewalk_cafe_after_rain",
            "quiet_cafe_window",
            "bookstore_cafe",
            "calm_cafe_corner",
        ],
        "living_nature": [
            "forest_path",
            "open_meadow",
            "garden_morning",
            "riverside",
            "mountain_view",
            "sunrise_field",
            "autumn_park",
            "wild_grass_field",
            "lake_shore",
            "tree_canopy",
            "flowering_garden_path",
            "rain_on_leaves",
        ],
        "coastal": [
            "sea_horizon",
            "coastal_morning",
            "dune_grass",
            "rocky_shore",
            "quiet_pier",
        ],
        "botanical": [
            "garden_morning",
            "botanical_still_life",
            "balcony_garden",
            "flowering_garden_path",
            "rain_on_leaves",
            "tree_canopy",
        ],
        "rural_calm": [
            "village_veranda",
            "cottage_garden",
            "orchard_morning",
            "country_road",
            "farmhouse_kitchen_window",
            "greenhouse_calm",
            "wooden_porch",
            "field_edge_sunrise",
            "bench_under_tree_near_cottage",
        ],
        "cozy_home": [
            "warm_living_room",
            "fireplace_reading_chair",
            "soft_blanket_corner",
            "lamp_and_bookshelf",
            "calm_room_wide",
            "morning_light_wall",
        ],
        "book_nook": [
            "library_corner",
            "reading_chair",
            "fireplace_library",
            "bookshop_aisle",
            "bookstore_cafe",
        ],
        "interior_cozy": [
            "library_corner",
            "calm_cafe_corner",
            "quiet_cafe_window",
            "bookstore_cafe",
            "reading_corner",
            "calm_room_wide",
            "rain_window",
            "botanical_still_life",
        ],
        "urban": [
            "quiet_city_morning",
            "city_park",
            "city_park_before_work",
            "courtyard_morning",
            "bridge_walkway",
            "street_after_rain",
            "tram_stop_morning",
            "autumn_park",
            "library_corner",
        ],
        "abstract_symbolic": [
            "abstract_light",
            "soft_color_gradient",
            "water_reflection",
            "hands_detail",
        ],
        "hands_detail": [
            "hands_detail",
            "hands_with_leaf",
            "hands_with_fabric",
        ],
        "photo_general": [
            "quiet_city_morning",
            "calm_cafe_corner",
            "office_morning_light",
            "riverside",
            "garden_morning",
            "lake_shore",
            "library_corner",
            "city_park",
        ],
        "generic": GENERIC_SCENE_CANDIDATES,
    }
    candidates = pools.get(family, GENERIC_SCENE_CANDIDATES)
    if not candidates:
        memory = _safe_dict(visual_memory_context)
        return _dedupe_stable(_safe_list(memory.get("prefer_scene_types")) + DEFAULT_SCENE_FALLBACK_ORDER)
    return _dedupe_stable(candidates)


def build_scene_planner_prompt(
    *,
    focus_title: str | None,
    affirmations: list[str] | None,
    soft_action: str | None,
    visual_memory_context: dict | None,
    language: str = "ru",
) -> str:
    memory = _safe_dict(visual_memory_context)
    aff_list = _dedupe_stable(_safe_list(affirmations))
    focus = _clean_str(focus_title) or "—"
    soft = _clean_str(soft_action) or "—"
    recent_scene_types = ", ".join(_dedupe_stable(_safe_list(memory.get("recent_scene_types")))) or "—"
    recent_motifs = ", ".join(_dedupe_stable(_safe_list(memory.get("recent_motifs")))) or "—"
    overused_motifs = ", ".join(_dedupe_stable(_safe_list(memory.get("overused_motifs")))) or "—"
    hard_avoid = ", ".join(_dedupe_stable(_safe_list(memory.get("hard_avoid_today")))) or "—"
    prefer_scene_types = ", ".join(_dedupe_stable(_safe_list(memory.get("prefer_scene_types")))) or "—"
    affirmations_block = "\n".join(f"- {item}" for item in aff_list) if aff_list else "- —"

    return (
        "You are a Scene Planner for a daily Telegram mood image.\n"
        "Return JSON only.\n"
        "Design one concrete and photographable visual scene that expresses the emotional meaning of the input.\n"
        "Avoid repeats from visual memory context.\n"
        "Avoid hard_avoid_today and recent_scene_types whenever a good alternative exists.\n"
        "Do not use mug, notebook, table, window, beach, or human unless semantically necessary.\n"
        "No crowd. No extra people. No generic wellness stock photo.\n"
        "Prefer nature, garden, forest, meadow, quiet city, hands detail, abstract light, mountain, riverside.\n"
        "Use the emotional meaning from focus_title, affirmations, and soft_action.\n\n"
        f"Interface language: {language}\n"
        f"focus_title: {focus}\n"
        f"soft_action: {soft}\n"
        "affirmations:\n"
        f"{affirmations_block}\n\n"
        "visual_memory_context:\n"
        f"- recent_scene_types: {recent_scene_types}\n"
        f"- recent_motifs: {recent_motifs}\n"
        f"- overused_motifs: {overused_motifs}\n"
        f"- hard_avoid_today: {hard_avoid}\n"
        f"- prefer_scene_types: {prefer_scene_types}\n\n"
        "Expected JSON schema:\n"
        "{\n"
        '  "scene_type": "forest_path",\n'
        '  "setting": "...",\n'
        '  "human_presence": "none",\n'
        '  "main_subject": "...",\n'
        '  "visual_motifs": ["forest", "path", "morning_light"],\n'
        '  "composition": "...",\n'
        '  "lighting": "...",\n'
        '  "mood": "...",\n'
        '  "avoid": ["mug", "notebook", "beach"]\n'
        "}\n"
    )


def parse_scene_plan_response(raw_text: str | None) -> dict | None:
    text = _clean_str(raw_text)
    if not text:
        return None

    candidates = [text]
    if "```" in text:
        chunks = text.split("```")
        for chunk in chunks:
            cleaned = chunk.strip()
            if not cleaned:
                continue
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
            candidates.append(cleaned)

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(text[first_brace:last_brace + 1].strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_scene_plan(
    plan: dict | None,
    visual_memory_context: dict | None = None,
) -> dict:
    safe_plan = _safe_dict(plan)
    memory = _safe_dict(visual_memory_context)
    prefer_scene_types = _dedupe_stable(_safe_list(memory.get("prefer_scene_types")))
    scene_type = _clean_str(safe_plan.get("scene_type")) or (prefer_scene_types[0] if prefer_scene_types else "forest_path")
    preset = _safe_dict(SCENE_PRESETS.get(scene_type))

    setting = _clean_str(safe_plan.get("setting")) or _clean_str(preset.get("setting")) or "quiet natural scene with soft light"
    main_subject = _clean_str(safe_plan.get("main_subject")) or _clean_str(preset.get("main_subject")) or "calm visual focal point with open space"
    composition = _clean_str(safe_plan.get("composition")) or _clean_str(preset.get("composition")) or "balanced open composition"
    lighting = _clean_str(safe_plan.get("lighting")) or _clean_str(preset.get("lighting")) or "soft natural light"
    mood = _clean_str(safe_plan.get("mood")) or _clean_str(preset.get("mood")) or "calm, grounded, emotionally spacious"
    human_presence = _normalize_human_presence(safe_plan.get("human_presence"))

    visual_motifs = _dedupe_stable(
        _safe_list(safe_plan.get("visual_motifs")) + _safe_list(preset.get("visual_motifs"))
    )
    avoid = _dedupe_stable(
        _safe_list(safe_plan.get("avoid"))
        + _safe_list(preset.get("avoid"))
        + _safe_list(memory.get("hard_avoid_today"))
        + DEFAULT_CLICHE_AVOID
    )

    return {
        "scene_type": scene_type,
        "setting": setting,
        "human_presence": human_presence,
        "main_subject": main_subject,
        "visual_motifs": visual_motifs,
        "composition": composition,
        "lighting": lighting,
        "mood": mood,
        "avoid": avoid,
    }


def build_fallback_scene_plan(
    *,
    focus_title: str | None,
    visual_memory_context: dict | None = None,
    selected_style: str | None = None,
    resolved_style: str | None = None,
    visual_mode: str | None = None,
    style_mode: str | None = None,
    sphere: str | None = None,
    subsphere: str | None = None,
) -> dict:
    memory = _safe_dict(visual_memory_context)
    recent_scene_types = _dedupe_stable(_safe_list(memory.get("recent_scene_types")))
    recent_scene_families = _dedupe_stable(_safe_list(memory.get("recent_scene_families")))
    overused_scene_families = set(_dedupe_stable(_safe_list(memory.get("overused_scene_families"))))
    prefer_scene_types = _dedupe_stable(_safe_list(memory.get("prefer_scene_types")))
    has_style_context = any(
        _clean_str(value)
        for value in (selected_style, resolved_style, visual_mode, style_mode)
    ) or _has_professional_theme_context(
        sphere=sphere,
        subsphere=subsphere,
        focus_title=focus_title,
        selected_style=selected_style,
        resolved_style=resolved_style,
        style_mode=style_mode,
    )
    style_candidates = (
        get_scene_candidates_for_style(
            selected_style=selected_style,
            resolved_style=resolved_style,
            visual_mode=visual_mode,
            style_mode=style_mode,
            sphere=sphere,
            subsphere=subsphere,
            focus_title=focus_title,
            visual_memory_context=memory,
        )
        if has_style_context
        else []
    )
    candidates = style_candidates or prefer_scene_types or DEFAULT_SCENE_FALLBACK_ORDER

    recent_family_window = set(recent_scene_families[:3])
    scene_type = None
    for candidate in candidates:
        if candidate in recent_scene_types:
            continue
        family = normalize_scene_family(candidate)
        if family and (family in recent_family_window or family in overused_scene_families):
            continue
        scene_type = candidate
        break
    if scene_type is None:
        for candidate in candidates:
            if candidate not in recent_scene_types:
                scene_type = candidate
                break
    if scene_type is None:
        scene_type = candidates[0] if candidates else DEFAULT_SCENE_FALLBACK_ORDER[0]
    preset = _safe_dict(SCENE_PRESETS.get(scene_type))
    focus = _clean_str(focus_title)
    mood = preset.get("mood") or "calm, grounded, emotionally spacious"
    if focus:
        mood = f"calm, grounded atmosphere for: {focus}"

    scene_family = normalize_scene_family(scene_type)
    human_presence = "distant_figure" if scene_family in {"cafe_terrace", "cafe_quiet", "work_quiet"} else "none"

    raw_plan = {
        "scene_type": scene_type,
        "setting": preset.get("setting"),
        "human_presence": human_presence,
        "main_subject": preset.get("main_subject"),
        "visual_motifs": preset.get("visual_motifs"),
        "composition": preset.get("composition"),
        "lighting": preset.get("lighting"),
        "mood": mood,
        "avoid": _safe_list(memory.get("hard_avoid_today")) + _safe_list(preset.get("avoid")) + DEFAULT_CLICHE_AVOID,
    }
    return normalize_scene_plan(raw_plan, visual_memory_context=memory)


def build_scene_image_prompt(scene_plan: dict, language: str = "ru") -> str:
    normalized = normalize_scene_plan(scene_plan)
    motifs = ", ".join(normalized["visual_motifs"]) or "quiet natural motifs"
    avoid = ", ".join(normalized["avoid"])
    return (
        f"Scene type: {normalized['scene_type']}. "
        f"Setting: {normalized['setting']}. "
        f"Human presence: {normalized['human_presence']}. "
        f"Main subject: {normalized['main_subject']}. "
        f"Visual motifs: {motifs}. "
        f"Composition: {normalized['composition']}. "
        f"Lighting: {normalized['lighting']}. "
        f"Mood: {normalized['mood']}. "
        f"Avoid: {avoid}. "
        "No crowd. No extra people. Avoid generic wellness stock photo."
    )
