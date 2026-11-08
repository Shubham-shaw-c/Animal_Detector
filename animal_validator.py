"""
animal_validator.py
High-precision zoological validation engine.
Verifies whether a user-submitted entity is a genuine animal species before allowing
folder creation, image scraping, or neural network retraining.
"""

import re
import urllib.request
import urllib.parse
import json

# Comprehensive zoological dictionary covering common mammals, birds, reptiles,
# amphibians, marine life, and invertebrates.
KNOWN_ANIMALS = {
    # Domestic & Farm Mammals
    "cat", "kitten", "dog", "puppy", "hound", "cow", "cattle", "bull", "calf", "ox",
    "horse", "stallion", "mare", "foal", "pony", "donkey", "mule", "sheep", "lamb",
    "ram", "ewe", "goat", "kid", "pig", "piglet", "hog", "boar", "swine", "llama",
    "alpaca", "yak", "water buffalo", "camel", "dromedary",

    # Wild Big Cats & Canines
    "lion", "lioness", "tiger", "tigress", "leopard", "snow leopard", "clouded leopard",
    "cheetah", "jaguar", "panther", "black panther", "cougar", "mountain lion", "puma",
    "lynx", "bobcat", "ocelot", "caracal", "serval", "wildcat", "wolf", "gray wolf",
    "timber wolf", "red wolf", "arctic wolf", "fox", "red fox", "arctic fox", "fennec fox",
    "coyote", "jackal", "dingo", "hyena", "spotted hyena", "striped hyena", "wild dog",
    "african wild dog",

    # Bears & Mustelids
    "bear", "brown bear", "grizzly bear", "polar bear", "black bear", "sloth bear",
    "sun bear", "spectacled bear", "panda", "giant panda", "red panda", "koala",
    "badger", "honey badger", "otter", "sea otter", "river otter", "giant otter",
    "weasel", "stoat", "ferret", "black-footed ferret", "mink", "wolverine", "marten",
    "fisher", "skunk", "raccoon", "coati", "kinkajou", "mongoose", "meerkat",

    # Herbivores & Ungulates
    "elephant", "african elephant", "asian elephant", "mammoth", "mastodon",
    "giraffe", "okapi", "hippopotamus", "hippo", "pygmy hippo", "rhinoceros", "rhino",
    "white rhino", "black rhino", "indian rhino", "zebra", "plains zebra", "mountain zebra",
    "deer", "stag", "doe", "fawn", "reindeer", "caribou", "elk", "moose", "antelope",
    "gazelle", "impala", "wildebeest", "gnu", "bison", "american bison", "wisent",
    "buffalo", "cape buffalo", "ibex", "chamois", "mouflon", "bighorn sheep", "tapir",
    "peccary", "warthog", "babirusa",

    # Primates
    "monkey", "ape", "chimpanzee", "chimp", "bonobo", "gorilla", "silverback",
    "orangutan", "gibbon", "baboon", "mandrill", "macaque", "rhesus macaque",
    "capuchin", "howler monkey", "spider monkey", "tamarin", "marmoset", "squirrel monkey",
    "colobus", "langur", "proboscis monkey", "lemur", "ring-tailed lemur", "aye-aye",
    "tarsier", "bushbaby", "loris", "slow loris",

    # Marsupials & Monotremes
    "kangaroo", "red kangaroo", "wallaby", "wallaroo", "tree kangaroo", "quokka",
    "wombat", "tasmanian devil", "tasmanian tiger", "possum", "opossum", "sugar glider",
    "bandicoot", "bilby", "numbat", "platypus", "echidna",

    # Rodents, Lagomorphs & Insectivores
    "rabbit", "hare", "cottontail", "jackrabbit", "bunny", "pika", "guinea pig",
    "hamster", "gerbil", "chinchilla", "degu", "capybara", "nutria", "beaver",
    "porcupine", "squirrel", "flying squirrel", "chipmunk", "groundhog", "woodchuck",
    "marmot", "prairie dog", "gopher", "rat", "mouse", "dormouse", "vole", "lemming",
    "mole", "star-nosed mole", "shrew", "hedgehog", "tenrec", "armadillo", "giant armadillo",
    "anteater", "giant anteater", "tamandua", "sloth", "two-toed sloth", "three-toed sloth",
    "pangolin", "aardvark",

    # Marine Mammals
    "whale", "blue whale", "fin whale", "humpback whale", "sperm whale", "minke whale",
    "gray whale", "bowhead whale", "right whale", "beluga", "beluga whale", "narwhal",
    "killer whale", "orca", "pilot whale", "dolphin", "bottlenose dolphin", "spinner dolphin",
    "porpoise", "seal", "harbor seal", "elephant seal", "leopard seal", "fur seal",
    "sea lion", "california sea lion", "walrus", "manatee", "dugong", "sea cow",

    # Birds of Prey
    "eagle", "bald eagle", "golden eagle", "harpy eagle", "hawk", "red-tailed hawk",
    "falcon", "peregrine falcon", "kestrel", "osprey", "kite", "buzzard", "owl",
    "barn owl", "great horned owl", "snowy owl", "screech owl", "eagle owl",
    "vulture", "turkey vulture", "condor", "california condor", "andean condor",

    # Waterbirds & Coastal Birds
    "penguin", "emperor penguin", "king penguin", "adelie penguin", "gentoo penguin",
    "flamingo", "pelican", "albatross", "gull", "seagull", "tern", "puffin",
    "duck", "mallard", "teal", "canvasback", "goose", "canada goose", "swan",
    "mute swan", "black swan", "heron", "great blue heron", "egret", "bittern",
    "stork", "marabou stork", "crane", "whooping crane", "sandhill crane", "ibis",
    "spoonbill", "cormorant", "gannet", "booby", "frigatebird", "loon", "grebe",

    # Land Birds & Game Birds
    "peacock", "peafowl", "peahen", "ostrich", "emu", "cassowary", "rhea", "kiwi",
    "turkey", "wild turkey", "chicken", "rooster", "hen", "pheasant", "quail",
    "partridge", "grouse", "guineafowl", "roadrunner",

    # Songbirds & Parrots
    "parrot", "macaw", "scarlet macaw", "cockatoo", "cockatiel", "parakeet", "budgie",
    "lovebird", "lorikeet", "toucan", "hornbill", "woodpecker", "kingfisher",
    "hummingbird", "crow", "raven", "magpie", "blue jay", "jay", "canary", "finch",
    "sparrow", "robin", "cardinal", "swallow", "swift", "nightingale", "starling",
    "blackbird", "thrush", "pigeon", "dove", "mourning dove", "cuckoo",

    # Reptiles
    "crocodile", "nile crocodile", "saltwater crocodile", "alligator", "american alligator",
    "caiman", "gharial", "turtle", "sea turtle", "green sea turtle", "leatherback sea turtle",
    "loggerhead sea turtle", "snapping turtle", "tortoise", "galapagos tortoise",
    "giant tortoise", "lizard", "gecko", "leopard gecko", "crested gecko", "chameleon",
    "iguana", "green iguana", "marine iguana", "komodo dragon", "monitor lizard",
    "bearded dragon", "gila monster", "skink", "anole", "snake", "python", "ball python",
    "burmese python", "reticulated python", "boa", "boa constrictor", "anaconda",
    "green anaconda", "cobra", "king cobra", "mamba", "black mamba", "viper",
    "pit viper", "rattlesnake", "sidewinder", "copperhead", "cottonmouth", "adder",

    # Amphibians
    "frog", "tree frog", "poison dart frog", "bullfrog", "toad", "cane toad",
    "salamander", "fire salamander", "axolotl", "newt", "caecilian", "tadpole",

    # Fish & Sharks
    "shark", "great white shark", "tiger shark", "hammerhead shark", "whale shark",
    "mako shark", "bull shark", "basking shark", "ray", "stingray", "manta ray",
    "electric ray", "sawfish", "salmon", "trout", "tuna", "bluefin tuna", "cod",
    "halibut", "swordfish", "marlin", "sailfish", "barracuda", "piranha", "catfish",
    "carp", "goldfish", "koi", "betta", "clownfish", "angelfish", "guppy", "seahorse",
    "pipefish", "eel", "moray eel", "electric eel", "pufferfish", "blowfish", "lionfish",

    # Aquatic Invertebrates
    "octopus", "giant pacific octopus", "blue-ringed octopus", "squid", "giant squid",
    "colossal squid", "cuttlefish", "nautilus", "jellyfish", "box jellyfish", "sea anemone",
    "coral", "starfish", "sea star", "sea urchin", "sea cucumber", "crab", "king crab",
    "hermit crab", "blue crab", "lobster", "spiny lobster", "crayfish", "shrimp",
    "prawn", "krill", "clam", "oyster", "mussel", "scallop", "snail", "sea snail", "slug",

    # Terrestrial Invertebrates & Insects
    "ant", "bullet ant", "army ant", "bee", "honeybee", "bumblebee", "wasp", "hornet",
    "yellowjacket", "butterfly", "monarch butterfly", "moth", "caterpillar", "beetle",
    "stag beetle", "hercules beetle", "ladybug", "firefly", "dragonfly", "damselfly",
    "mantis", "praying mantis", "grasshopper", "locust", "cricket", "cicada",
    "spider", "tarantula", "black widow", "scorpion", "centipede", "millipede",
    "earthworm", "worm"
}

# Irregular plural mapping
IRREGULAR_PLURALS = {
    "wolves": "wolf",
    "calves": "calf",
    "halves": "half",
    "geese": "goose",
    "mice": "mouse",
    "oxen": "ox",
    "teeth": "tooth",
    "feet": "foot",
    "hippos": "hippo",
    "rhinos": "rhino"
}

# Known non-animal words that should be explicitly rejected with high confidence
KNOWN_NON_ANIMALS = {
    "car", "automobile", "bike", "bicycle", "truck", "bus", "van", "airplane", "plane",
    "train", "boat", "ship", "helicopter", "rocket", "motorcycle", "scooter",
    "computer", "laptop", "phone", "smartphone", "tablet", "screen", "keyboard", "mouse_pad",
    "table", "chair", "desk", "bed", "sofa", "couch", "furniture", "door", "window",
    "house", "building", "room", "kitchen", "bathroom", "school", "hospital",
    "pen", "pencil", "paper", "book", "bottle", "glass", "cup", "plate", "fork", "spoon",
    "food", "pizza", "burger", "bread", "apple", "banana", "fruit", "vegetable",
    "shirt", "pant", "shoe", "dress", "hat", "clothes", "watch", "ring",
    "human", "person", "man", "woman", "boy", "girl", "child", "baby", "shubham",
    "python_lang", "javascript", "code", "software", "program", "app", "website"
}


def singularize(word: str) -> str:
    """Converts common plural forms back to singular."""
    w = word.strip().lower()
    if w in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[w]

    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ses", "xes", "zes", "ches", "shes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is")) and len(w) > 3:
        return w[:-1]
    return w


def clean_animal_input(raw_name: str) -> str:
    """Trims, strips leading articles, and normalizes spacing."""
    if not raw_name or not isinstance(raw_name, str):
        return ""
    text = raw_name.strip().lower()
    # Remove leading articles
    text = re.sub(r"^(a|an|the)\s+", "", text)
    # Replace hyphens and multiple spaces with a single space
    text = re.sub(r"[-_\s]+", " ", text).strip()
    return text


def is_zoological_animal(name: str) -> bool:
    """
    Evaluates whether the given string represents a valid biological animal.
    Uses multi-stage check:
    1. Exact match in KNOWN_ANIMALS
    2. Singularized match
    3. Compound name root checking (e.g. 'snow leopard' -> 'leopard')
    4. Explicit non-animal word rejection
    """
    clean = clean_animal_input(name)
    if not clean:
        return False

    # Immediate rejection if in explicit non-animal list
    if clean in KNOWN_NON_ANIMALS:
        return False

    # 1. Direct match
    if clean in KNOWN_ANIMALS:
        return True

    # 2. Singular match
    sing = singularize(clean)
    if sing in KNOWN_ANIMALS:
        return True

    # 3. Check individual words in compound names (e.g. "bengal tiger", "african elephant", "brown bear")
    parts = clean.split()
    if len(parts) > 1:
        # Check last word (head noun, e.g. 'tiger' in 'bengal tiger')
        head_noun = singularize(parts[-1])
        if head_noun in KNOWN_ANIMALS:
            # Make sure modifier is not non-animal modifier like 'toy', 'plastic', 'car'
            disallowed_modifiers = {"toy", "fake", "plastic", "robot", "wooden", "paper", "cartoon", "car", "phone"}
            if not any(p in disallowed_modifiers for p in parts[:-1]):
                return True

    return False


def validate_new_animal(raw_name: str, existing_classes: list = None) -> tuple[bool, str, str, str]:
    """
    Validates a proposed new animal class for the model retraining pipeline.
    Returns:
        (is_valid: bool, normalized_key: str, display_name: str, error_msg: str)
    """
    if not raw_name or not isinstance(raw_name, str):
        return False, "", "", "Animal name cannot be empty. Please enter a valid animal name."

    cleaned = clean_animal_input(raw_name)
    if len(cleaned) < 2 or len(cleaned) > 35:
        return False, "", "", "Animal name must be between 2 and 35 characters long."

    # Validate characters (letters, spaces, hyphens only)
    if not re.match(r"^[a-zA-Z\s-]+$", raw_name.strip()):
        return False, "", "", "Invalid characters detected. Please use letters only (no numbers or symbols)."

    # Core Zoological Validation: Must be a genuine animal species
    if not is_zoological_animal(cleaned):
        formatted_name = raw_name.strip().capitalize()
        return (
            False,
            "",
            formatted_name,
            f"'{formatted_name}' is not recognized as an animal species. The autonomous pipeline only trains on real animals (mammals, birds, reptiles, fish, etc.). Please enter a valid animal name."
        )

    # Normalized folder key (lowercase, underscores)
    normalized_key = singularize(cleaned).replace(" ", "_")
    display_name = " ".join(w.capitalize() for w in cleaned.split())

    # Duplicate check against already trained classes
    if existing_classes:
        lower_existing = [c.lower().replace(" ", "_") for c in existing_classes]
        if normalized_key in lower_existing or cleaned.replace(" ", "_") in lower_existing:
            return (
                False,
                normalized_key,
                display_name,
                f"Animal '{display_name}' is already supported by the AI model! You can already test it directly."
            )

    return True, normalized_key, display_name, ""

