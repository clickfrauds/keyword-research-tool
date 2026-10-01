"""
service_architecture.py  (STAGE 2.7 — Volume-Tier Service Architecture, VTSA)
-------------------------------------------------------------------------------
Runs AFTER score_keywords.py, BEFORE analyze_with_claude.py.

WHY THIS EXISTS (Sep 2026 test run):
  7 services in (washing machine, dryer, dishwasher, refrigerator, fridge,
  wine chiller, LED TV) -> 4 ad groups out. Stage 3 let the model decide the
  group COUNT and the keyword SORTING, with a prompt that says "never split,
  small datasets stay in one group". Result: services merged, brand and
  problem queries mixed into generic groups, and a different structure on
  every run (which is also what broke the two-part push — see push fix).

  Structure is arithmetic, not creativity. This stage makes it deterministic:

  1. SERVICES   one per seed; synonyms merged (fridge == refrigerator)
  2. ASSIGN     every Planner keyword -> exactly one service
                (longest alias wins: "wine fridge" -> wine chiller,
                 "dish washer" -> dishwasher, "washer dryer" -> washing machine)
  3. FILTER     drops what a SERVICE business never converts:
                product shopping ("washing machine price", "buy fridge"),
                jobs/courses, DIY/how-to, parts shops, wrong emirates/countries
  4. LAYER      every kept keyword gets ONE layer, fixed precedence:
                   EMERGENCY (only when OPEN_24_7) > BRAND > PROBLEM > CORE
                ("samsung washer not draining" is a BRAND query first).
                Near me / at home / open now / "who can" / today are
                MODIFIERS, not a layer: they stay in CORE with its local and
                voice catchers. Symptom-only queries ("fridge not cooling")
                get an EXACT test group at SYMPTOM_BID x the core bid.
  5. TIER       slots per service from its own relevant volume V:
                   slots = clamp(ceil(V / 1000), 1, 4)
                   (V<=1000 ->1, <=2000 ->2, <=3000 ->3, >3000 ->4)
                A layer takes a slot only when it can buy MIN_LAYER_CLICKS
                (50) clicks a month = min(30.4 x budget x share / CPC,
                volume x ASSUMED_IS x ASSUMED_CTR), CPC from the Planner.
                Most clicks first. Unviable layers fold back into CORE; the
                budget guard (~3 clicks/day per group) folds more if needed.
                Never padded: unused slots stay unused. Seeds that do not
                cover the demand STOP the run (NEEDS_SERVICE_MAP) — no model
                fallback.
  6. SILO       precedence-aware negatives (a group negates only the layers
                ABOVE it) + cross-service head-term negatives.
  7. PAGES      one landing page per SERVICE (all its groups share it, each
                layer gets an anchored section) + a keyword_map that tells
                the website builder exactly which terms go in title / meta /
                H1 / H2 / body / FAQ / schema.

Single-service runs (e.g. only "plumber dubai"): the umbrella seed is split
into sub-services from SERVICES_JSON if given, otherwise each seed is a
service and the tier rule allows up to MAX_SLOTS_SINGLE (default 5) groups.

INPUT : scored_keywords.json (ALL rows, not only kept_for_ai — the Stage 2.5
        percentile floor otherwise deletes small services like wine chiller)
OUTPUT: ad_group_plan.json ; scored_keywords.json rewritten so exactly the
        planned keywords are kept_for_ai (Stage 3 then sees the same set)

Env:
  SEED_KEYWORDS (required), TARGET_LOCATION
  SERVICES_JSON     optional [{"name": "Drain Unblocking", "aliases": ["drain","blocked drain"]}]
  EXTRA_BRANDS      comma list added to the brand lexicon
  EXTRA_JUNK        comma list of extra exclusion tokens/phrases
  TIER_STEP         default 1000 (volume per extra ad group)
  MAX_SLOTS         default 4 ; MAX_SLOTS_SINGLE default 5
  MIN_LAYER_CLICKS  default 50 ; ASSUMED_IS 0.5 ; ASSUMED_CTR 0.07
  DAILY_BUDGET      account currency; AVG_CPC overrides the Planner CPC
  OPEN_24_7         on = Emergency 24/7 groups (default off)
  SYMPTOM_TEST      default on ; SYMPTOM_BID 0.6 ; SYMPTOM_MIN_CLICKS 10
  NICHE_DESCRIPTION, BUSINESS_MODEL, NEGATIVE_ALLOW  niche allow list (negative_packs)
"""

import os
import re
import sys
import json
import math
from collections import defaultdict

IN_FILE = "scored_keywords.json"
OUT_PLAN = "ad_group_plan.json"

TIER_STEP = int(os.environ.get("TIER_STEP", "1000") or 1000)
MAX_SLOTS = int(os.environ.get("MAX_SLOTS", "4") or 4)
MAX_SLOTS_SINGLE = int(os.environ.get("MAX_SLOTS_SINGLE", "5") or 5)
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip().lower()


def _env_on(name, default="off"):
    return (os.environ.get(name, "") or default).strip().lower() in ("on", "yes", "true", "1")


def _env_float(name, default):
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return float(default)


# SPLIT GATE (GPT review, Sep 2026). A layer earns its own ad group only when
# it can buy enough clicks to learn from: expected clicks/month =
#   min(30.4 x DAILY_BUDGET x share / CPC,  volume x ASSUMED_IS x ASSUMED_CTR)
# and the split needs >= MIN_LAYER_CLICKS of them. Searches and keyword counts
# are not the constraint — a layer with 400 searches at a 2,600 PKR CPC on a
# small budget never gets the clicks to learn anything.
MIN_LAYER_CLICKS = _env_float("MIN_LAYER_CLICKS", 50)
ASSUMED_IS = _env_float("ASSUMED_IS", 0.5)
ASSUMED_CTR = _env_float("ASSUMED_CTR", 0.07)
# TRUE EMERGENCY is its own layer only for a business that really answers
# 24/7. Otherwise "emergency fridge repair" is served by the core group
# during the ad schedule, and no ad promises what the client does not do.
OPEN_24_7 = _env_on("OPEN_24_7")
# SYMPTOM TEST. "fridge not cooling" is mostly DIY research, but not all of
# it: on, those queries get one EXACT-match group per service at
# SYMPTOM_BID x the core bid, so the data decides. Off, they go to the FAQ.
SYMPTOM_TEST = _env_on("SYMPTOM_TEST", "on")
SYMPTOM_BID = _env_float("SYMPTOM_BID", 0.6)
# ...but only where there is something to learn: a symptom test that cannot
# buy SYMPTOM_MIN_CLICKS a month stays in the page FAQ instead.
SYMPTOM_MIN_CLICKS = _env_float("SYMPTOM_MIN_CLICKS", 10)

# ─────────────────────────────────────────────────────────────────────────
# Vocabularies — generic across home/auto services. Extend by env, never by
# editing per client.
# ─────────────────────────────────────────────────────────────────────────
ACTION_WORDS = {
    "repair", "repairs", "repairing", "fix", "fixing", "service", "services",
    "servicing", "maintenance", "technician", "technicians", "mechanic",
    "engineer", "installation", "install", "installer", "cleaning", "clean",
    "refill", "recharge", "workshop", "center", "centre", "specialist",
    "company", "contractor", "expert", "shop", "replacement", "replace",
    "unblocking", "unblock", "leak", "detection", "fixer", "tech", "techs",
    # Arabic
    "تصليح", "اصلاح", "إصلاح", "صيانة", "صيانه", "فني", "فنيين", "تركيب", "تنظيف", "ورشة",
    "تعبئة", "تبديل", "استبدال", "خدمة", "خدمات", "مركز", "شركة", "مصلح", "تصليحات",
}
SERVICE_VERBS = ACTION_WORDS - {"shop", "company", "center", "centre"}
# The PERSON you hire is as much a hire signal as the verb: "plumber dubai",
# "carpenter reviews", "electrician al barsha" are people choosing a trade,
# not shoppers. Without this every trade campaign lost its head term as a
# "bare product".
PROVIDER_NOUNS = {
    "plumber", "plumbers", "electrician", "electricians", "carpenter", "carpenters",
    "handyman", "handymen", "locksmith", "locksmiths", "painter", "painters",
    "roofer", "roofers", "exterminator", "exterminators", "mechanic", "mechanics",
    "technician", "technicians", "contractor", "contractors", "installer", "installers",
    "cleaner", "cleaners", "gardener", "gardeners", "welder", "welders", "mason", "masons",
    "tiler", "tilers", "glazier", "glaziers",
    "سباك", "كهربائي", "نجار", "فني", "فنيين", "مصلح", "دهان", "حداد",
}
HIRE_WORDS = SERVICE_VERBS | PROVIDER_NOUNS | {"inspection", "inspect"}

# Synonym families. Any two seeds whose heads fall in one family = one service.
SYNONYMS = [
    {"fridge", "refrigerator", "fridge freezer", "freezer", "refrig", "ثلاجة", "ثلاجات"},
    {"washing machine", "washer", "washing machines", "laundry machine", "wash machine",
     "clothes washer", "غسالة", "غسالات"},
    {"dishwasher", "dish washer", "dishwashers", "غسالة صحون"},
    {"dryer", "tumble dryer", "clothes dryer", "dryers", "نشافة"},
    {"wine chiller", "wine cooler", "wine fridge", "wine chillers"},
    # bare "led"/"lcd" are NOT aliases: "led light repair" is an electrician
    # query, not a TV one. Only screen/display phrasings count.
    {"led tv", "tv", "television", "lcd tv", "smart tv", "oled tv", "led screen",
     "led display", "led panel", "lcd screen", "lcd panel", "تلفزيون"},
    {"ac", "air conditioner", "air conditioning", "aircon", "a/c", "مكيف", "مكيفات"},
    {"oven", "cooker", "stove", "cooking range", "gas cooker", "فرن"},
    {"microwave", "microwave oven"},
    {"water heater", "geyser", "boiler", "سخان"},
    {"plumber", "plumbing", "سباك"},
    {"electrician", "electrical", "كهربائي"},
    {"handyman"},
    {"roof", "roofing", "roofer", "roof leak"},
    {"painter", "painting", "paint job"},
    {"pest control", "pest", "exterminator", "termite", "cockroach", "bed bug"},
    {"locksmith", "lock", "locks"},
    {"garage door", "gate", "automatic gate"},
    {"carpenter", "carpentry", "نجار"},
]

BRANDS = {
    # appliances / electronics
    "samsung", "lg", "bosch", "siemens", "whirlpool", "ariston", "indesit",
    "electrolux", "zanussi", "aeg", "miele", "beko", "haier", "hisense",
    "midea", "panasonic", "sharp", "toshiba", "hitachi", "sony", "tcl",
    "philips", "smeg", "gorenje", "frigidaire", "ge", "kenwood", "candy",
    "hoover", "daewoo", "teka", "fisher", "paykel", "liebherr", "sub-zero",
    "subzero", "viking", "wolf", "kitchenaid", "maytag", "amana", "blomberg",
    "vestel", "super", "general", "nikai", "westpoint", "hotpoint", "defy",
    "gree", "carrier", "daikin", "trane", "york", "mitsubishi", "o-general",
    "fujitsu", "haier", "xiaomi", "vizio", "skyworth", "caple", "dometic",
    "vinotemp", "eurocave", "klarstein",
    # plumbing fixtures
    "grohe", "hansgrohe", "kohler", "roca", "duravit", "geberit", "rak",
    "ideal", "ariston", "rheem", "ferroli",
    # auto
    "toyota", "nissan", "lexus", "bmw", "mercedes", "audi", "honda", "kia",
    "hyundai", "ford", "chevrolet", "range", "rover", "land", "porsche",
    "mazda", "volkswagen", "vw", "jeep", "dodge", "infiniti", "mitsubishi",
    # Arabic spellings of the big ones
    "سامسونج", "ال جي", "بوش", "سيمنز", "ويرلبول", "اريستون",
}
BRANDS |= {b.strip().lower() for b in os.environ.get("EXTRA_BRANDS", "").split(",") if b.strip()}
# "general" / "super" / "ideal" / "land" / "range" are too generic alone —
# they only count as a brand in these pairs.
_WEAK_BRANDS = {"general", "super", "ideal", "land", "range", "rover", "fisher", "paykel", "wolf", "rak"}
_BRAND_PAIRS = {("general", "electric"), ("fisher", "paykel"), ("land", "rover"),
                ("range", "rover"), ("super", "general"), ("rak", "ceramics")}

PROBLEM_TOKENS = {
    "not", "wont", "won't", "doesnt", "doesn't", "dont", "don't", "cant",
    "stopped", "stop", "leak", "leaking", "leaks", "noise", "noisy", "loud",
    "error", "code", "broken", "problem", "problems", "issue", "issues",
    "fault", "faulty", "smell", "smells", "smelly", "vibrating", "vibration",
    "shaking", "overheating", "tripping", "trips", "stuck", "jammed", "blinking",
    "flashing", "beeping", "burning", "sparking", "dead", "dripping", "blocked",
    "clogged", "frozen", "icing", "ice", "sweating", "humming", "clicking",
    # parts
    "compressor", "motor", "pcb", "board", "pump", "thermostat", "bearing",
    "bearings", "belt", "drum", "gasket", "seal", "heater", "element",
    "backlight", "panel", "screen", "capacitor", "fan", "valve", "timer",
    "sensor", "door", "lock", "hinge", "gas", "coil", "inverter", "relay",
    "filter", "hose", "drain", "spin", "spinning", "draining", "cooling",
    "heating", "power",
    # Arabic
    "لا", "لايعمل", "عطل", "اعطال", "أعطال", "تسريب", "صوت", "ضاغط", "كمبروسر",
}
# These only mean "problem" when they carry a negation or fault word:
# "drain", "cooling", "gas", "door", "heating" etc. appear in plain service
# queries too ("gas refill", "door repair"). They are part-level problems —
# still PROBLEM layer, because a query naming a part is a diagnosed fault.
_ERROR_CODE = re.compile(r"^(?:[a-z]{1,2}\d{1,3}|\d{1,2}[a-z]{1,2})$")

URGENT_TOKENS = {
    "near", "nearby", "me", "local", "emergency", "urgent", "24", "24/7", "247",
    "24x7", "same", "today", "now", "tonight", "open", "home", "doorstep",
    "onsite", "call", "fast", "quick", "immediate", "who", "where",
    "قريب", "طوارئ", "عاجل", "فوري", "الان", "اليوم",
}
# Tokens that only count as URGENT inside a phrase
_URGENT_PHRASES = ["قريب مني", "بالقرب مني", "24 ساعة", "في المنزل",
                   "near me", "close to me", "around me", "nearest", "closest",
                   "open near me", "near me open", "open now", "open today", "open 24",
                   "24 hours", "right now", "same day", "at home", "home service", "open now",
                   "24 hour", "24 hours", "24/7", "who can", "who fixes",
                   "where can i", "call out"]
# The words above are MODIFIERS ("near me", "at home", "who can", "open now",
# "today"): they make a query local or spoken, not a different job, so they
# stay in whatever layer the query already belongs to — mostly CORE, which
# is where the local / voice / near-me catchers live. Only these words mean a
# genuine emergency, and they are a layer only when OPEN_24_7 is on.
EMERGENCY_TOKENS = {"emergency", "urgent", "24/7", "24x7", "247", "tonight",
                    "طوارئ", "عاجل", "فوري"}
EMERGENCY_PHRASES = ["24 hour", "24 hours", "24 hrs", "after hours", "out of hours",
                     "late night", "24 ساعة"]

JUNK_TOKENS = {
    # product shopping
    "buy", "sale", "sell", "selling", "shopping", "showroom", "deal", "deals",
    "discount", "installment", "installments", "emi", "specs", "specification",
    "specifications", "dimensions", "size", "kg", "inch", "inches", "litre",
    "liter", "vs", "versus", "compare", "comparison",
    "secondhand", "olx", "dubizzle", "noon", "amazon",
    "carrefour", "sharaf", "lulu", "emax", "jumbo", "ikea", "danube",
    "rent", "rental", "rentals", "lease",
    # jobs / training
    "job", "jobs", "vacancy", "vacancies", "salary", "hiring", "career",
    "careers", "course", "courses", "training", "institute", "learn",
    "learning", "certificate", "certification", "cv",
    # DIY / info
    "diy", "pdf", "diagram", "youtube", "video", "videos",
    "tutorial", "meaning", "wikipedia", "reset", "myself",
    # parts retail
    "wholesale", "supplier", "suppliers", "trading", "llc",
    # free
    "free",
    # Arabic
    "شراء", "بيع", "للبيع", "مستعمل", "مستعملة", "وظائف", "وظيفة", "راتب", "دورة",
    "كورس", "قطع", "غيار", "يوتيوب", "كتالوج", "عروض", "تخفيضات",
}
JUNK_TOKENS |= {t.strip().lower() for t in os.environ.get("EXTRA_JUNK", "").split(",") if t.strip()}
# SOFT junk: junk only when nothing in the query says "hire someone".
# "washing machine manual" / "fridge parts" / "tv reviews" are shoppers and
# readers; "manual gearbox repair", "fridge parts replacement", "carpenter
# reviews", "used car inspection" are buyers. ("wiring" is not junk at all:
# "electrical wiring repair" is a job; "wiring diagram" still dies on "diagram".)
SOFT_JUNK_TOKENS = {"manual", "manuals", "used", "second", "parts", "spare", "spares",
                    "review", "reviews", "قطع", "غيار", "مستعمل", "مستعملة"}
JUNK_TOKENS -= SOFT_JUNK_TOKENS


def _niche_allow():
    """The niche's own buyer words (negative_packs allow list): a garage keeps
    "manual" and "used", an AC business keeps "gas". Never raises — the packs
    are an extra, not a dependency of the grouping."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import negative_packs
        seeds = [s.strip() for s in os.environ.get("SEED_KEYWORDS", "").split(",") if s.strip()]
        _block, allow, _packs = negative_packs.build(
            os.environ.get("NICHE_DESCRIPTION", ""), seeds,
            os.environ.get("BUSINESS_MODEL", "service") or "service")
        return {a for a in allow if " " not in a}
    except Exception as e:
        print(f"   ⚠️ negative_packs allow list unavailable ({str(e)[:60]}) — none applied")
        return set()


NICHE_ALLOW = _niche_allow()
JUNK_TOKENS -= NICHE_ALLOW
SOFT_JUNK_TOKENS -= NICHE_ALLOW

def _niche_exclusions():
    """Wrong-JOB phrases for this niche (negative_packs: aggregators every
    niche, plus the detected niche's "exclude" list — e.g. appliance: "hair
    dryer", "dryer vent"). Data, per niche, never hard-coded here."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import negative_packs
        seeds = [s.strip() for s in os.environ.get("SEED_KEYWORDS", "").split(",") if s.strip()]
        return negative_packs.exclusions(os.environ.get("NICHE_DESCRIPTION", ""), seeds,
                                         os.environ.get("BUSINESS_MODEL", "service") or "service")
    except Exception as e:
        print(f"   ⚠️ niche exclusions unavailable ({str(e)[:60]}) — none applied")
        return []


JUNK_PHRASES = _niche_exclusions()
# A HOME-service business (any trade: "home appliance repair", "residential
# plumbing", "household pest control") does not sell to factories, fleets or
# cars. Read from the niche text, so a commercial-refrigeration or auto
# business is unaffected.
if re.search(r"\b(home|household|residential|domestic)\b",
             os.environ.get("NICHE_DESCRIPTION", ""), re.IGNORECASE):
    JUNK_TOKENS |= {"commercial", "industrial", "car", "cars", "سيارة", "سيارات",
                    "السيارات", "السيارة"} - NICHE_ALLOW
# OTHER TRADES. Filled per run in register_other_services(): the head noun of
# a trade this plan did not seed is someone else's job — "ac washing machine
# repair" in an appliance plan, "electrician" in a plumbing plan. Trade NAMES
# only: "electrical fault" stays an appliance problem, "water heater" can be
# an appliance or a plumbing job, so neither is listed. A seeded trade is
# never junk.
OTHER_SERVICE_PHRASES = []
_OTHER_FAMILIES = [
    {"ac", "air conditioner", "air conditioning", "aircon", "a/c", "hvac", "مكيف", "مكيفات", "تكييف"},
    {"plumber", "plumbers", "plumbing", "سباك", "سباكة"},
    {"electrician", "electricians", "كهربائي"},
    {"roofer", "roofers", "roofing"},
    {"locksmith", "locksmiths"},
    {"pest control", "exterminator", "مكافحة حشرات"},
    {"carpenter", "carpenters", "carpentry", "نجار"},
    {"painter", "painters", "دهان"},
    {"mechanic shop", "auto repair", "car repair", "car service"},
]
# Real words the typo fixer must never "correct": "refrigeration" is HVAC
# work, two edits from "refrigerator", and was being read as a fridge query.
_NO_FIX = {"refrigeration", "refrigerant", "refrigerated", "conditioning", "ventilation"}

# BID KEYWORDS (1 Oct 2026). Every Planner row that maps to a service stays
# on the page (keyword_map) and in the group's demand. The BID list is
# smaller: 1,321 of run 2476776a's 1,485 bid keywords had <= 10 searches, and
# 50-70% per group were already reached by a shorter PHRASE keyword in the
# same group ("washing machine repair" matches "samsung washing machine repair
# dubai"). Kept: every keyword not covered that way with MIN_BID_VOLUME+
# searches, and at least MIN_KEYWORDS_PER_GROUP per group.
MIN_BID_VOLUME = _env_float("MIN_BID_VOLUME", 20)
MIN_KEYWORDS_PER_GROUP = int(_env_float("MIN_KEYWORDS_PER_GROUP", 10))
# How many of a group's unreached low-volume rows Stage 3's model is shown to
# pick buyer queries from (it may add up to RESCUE_MAX_PER_GROUP of them).
RESCUE_POOL = int(_env_float("RESCUE_POOL", 40))
# "price/cost" is shopping ONLY without a service verb:
# "washing machine price" = junk ; "washing machine repair cost" = CORE.
PRICE_TOKENS = {"price", "prices", "cost", "costs", "cheap", "cheapest", "rate", "rates", "charges",
                "سعر", "اسعار", "أسعار", "تكلفة", "كم"}
# "how to fix my washing machine" = DIY ; "who can fix my washing machine" = hire
DIY_STARTS = ("how to ", "how do i ", "how can i ", "can i ", "why does ",
              "why is ", "what is ", "what does ", "what causes ",
              "كيف ", "كيفي ", "طريق ", "لماذا ", "ليش ", "ما هو ", "ما سبب ")

# Wrong locations, by target city. Generic GCC table; extend with WRONG_LOCATIONS.
_SIBLINGS = {
    "dubai": ["abu dhabi", "sharjah", "ajman", "al ain", "ras al khaimah", "rak",
              "fujairah", "umm al quwain", "uaq", "khor fakkan", "oman", "muscat",
              "qatar", "doha", "saudi", "riyadh", "jeddah", "bahrain", "kuwait",
              "india", "pakistan", "uk", "london", "usa", "canada", "australia",
              "ابوظبي", "أبوظبي", "الشارقة", "عجمان", "العين"],
    "abu dhabi": ["dubai", "sharjah", "ajman", "ras al khaimah", "fujairah",
                  "umm al quwain", "oman", "qatar", "saudi", "india", "pakistan",
                  "دبي", "الشارقة", "عجمان"],
    "sharjah": ["dubai", "abu dhabi", "ajman", "al ain", "ras al khaimah",
                "fujairah", "oman", "qatar", "saudi", "india", "pakistan",
                "دبي", "ابوظبي", "عجمان"],
}


def _raw_toks(s):
    return re.findall(r"[^\W_]+(?:/[^\W_]+)?", str(s).lower(), re.UNICODE)


# Vocabulary the normaliser may correct TOWARDS (filled in by build_services
# with the aliases of this run's services). Only these words are ever used as
# corrections, so a typo can only ever become one of our own service words.
_CANON = set()
_GLUE = {}   # "washingmachine" -> "washing machine", "fridgerepair" -> "fridge repair"


def _lev(a, b, cap=2):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def _fix_token(t):
    """Glued words and typos, towards OUR vocabulary only.
    "washingmachine" -> "washing machine", "fridgerepair" -> "fridge repair",
    "refrigirator" -> "refrigerator", "machne" -> "machine", "repiar" -> "repair".
    Same first letter required, 5+ letters, 1 edit (2 for 9+ letters) — so
    "bridge" can never become "fridge" and short words are left alone."""
    if t in _GLUE:
        return _GLUE[t]
    if t in _CANON or t in _NO_FIX or len(t) < 5 or not t.isalpha():
        return t
    cap = 2 if len(t) >= 9 else 1
    best, bd = None, cap + 1
    # sorted: a set's order changes between processes (hash seed), and a
    # tie between two corrections must resolve the same way on every run —
    # and in the silo router, which walks the same sorted list.
    for w in sorted(_CANON):
        if w[0] == t[0] and abs(len(w) - len(t)) <= cap:
            d = _lev(t, w, cap)
            if d < bd:
                best, bd = w, d
    return best if best and bd <= cap else t


_AR_RE = re.compile(r"[\u0600-\u06FF]")
_AR_DIAC = re.compile(r"[\u064B-\u0652\u0640]")


def _ar_norm(t):
    """Light Arabic normaliser so one word has one form everywhere:
    diacritics/tatweel out, alef variants -> ا, ى -> ي, the article and
    its clitics stripped (الثلاجة/بالثلاجة -> ثلاجة), then the feminine/
    plural ending (ثلاجة/ثلاجات/ثلاجه -> ثلاج). Words of 3 letters or less
    ("لا", "ال", "جي") are never touched."""
    t = _AR_DIAC.sub("", t)
    t = re.sub("[أإآ]", "ا", t).replace("ى", "ي")
    if len(t) <= 3:
        return t
    for pre in ("وال", "بال", "فال", "كال", "لل", "ال"):
        if t.startswith(pre) and len(t) - len(pre) >= 3:
            t = t[len(pre):]
            break
    for suf in ("ات", "ة", "ه"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            t = t[: -len(suf)]
            break
    return t


def is_arabic(s):
    return bool(_AR_RE.search(str(s)))


def toks(s):
    out = []
    for t in _raw_toks(s):
        if _AR_RE.search(t):
            out.append(_ar_norm(t))
        else:
            out.extend(_fix_token(t).split())
    return out


def norm_phrase(s):
    return " ".join(toks(s))


def _build_normaliser(services):
    words = set()
    for s in services:
        for a in s["aliases"]:
            words.update(w for w in a.split() if len(w) >= 5 and w.isalpha())
    words.update(w for w in SERVICE_VERBS if len(w) >= 5 and w.isalpha())
    _CANON.clear(); _CANON.update(words)
    _GLUE.clear()
    for s in services:
        for a in s["aliases"]:
            # only when the glued form is NOT itself a real alias:
            # "washingmachine" -> "washing machine", but "dishwasher" stays
            if " " in a and a.replace(" ", "") not in {x for sv in services for x in sv["aliases"]}:
                _GLUE[a.replace(" ", "")] = a
            for v in ("repair", "service", "fix", "technician", "installation", "cleaning"):
                _GLUE[a.replace(" ", "") + v] = f"{a} {v}"


def has_phrase(text, phrase):
    return re.search(r"(^|\s)" + re.escape(phrase) + r"(\s|$)", " " + text + " ") is not None


_TRANSLIT = {"ا": "a", "أ": "a", "إ": "i", "آ": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j",
             "ح": "h", "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh",
             "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a", "غ": "gh", "ف": "f", "ق": "q",
             "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "w", "ي": "y", "ى": "a",
             "ة": "a", "ء": "", "ؤ": "u", "ئ": "i"}


def _translit(s):
    return "".join(_TRANSLIT.get(ch, ch) for ch in str(s))


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)[:60]


def title(s):
    small = {"and", "or", "of", "in", "&"}
    keep_up = {"tv", "led", "lcd", "oled", "ac", "lg", "ge", "aeg", "tcl", "pcb", "24/7"}
    out = []
    for i, w in enumerate(str(s).split()):
        lw = w.lower()
        out.append(lw.upper() if lw in keep_up else (lw if (i and lw in small) else lw.capitalize()))
    return " ".join(out)


# ─────────────────────────────────────────────────────────────────────────
# 1. Services from seeds
# ─────────────────────────────────────────────────────────────────────────
CITY_AR = {"dubai": "دبي", "abu dhabi": "أبوظبي", "sharjah": "الشارقة", "ajman": "عجمان",
           "al ain": "العين", "ras al khaimah": "رأس الخيمة", "fujairah": "الفجيرة",
           "riyadh": "الرياض", "jeddah": "جدة", "doha": "الدوحة", "kuwait": "الكويت",
           "muscat": "مسقط", "manama": "المنامة"}


def city_names():
    en = TARGET_LOCATION.split(",")[0].strip()
    return en, CITY_AR.get(en.lower(), "")


def _loc_tokens():
    en, ar = city_names()
    return set(toks(TARGET_LOCATION)) | set(toks(ar))


# The one English name per trade family — used to name the Arabic twin and
# to give it the SAME slug as the English page (published under /ar/).
CANONICAL_EN = {"washing machine", "refrigerator", "fridge", "dishwasher", "dryer",
                "wine chiller", "led tv", "tv", "ac", "air conditioner", "oven", "microwave",
                "water heater", "plumber", "electrician", "handyman", "carpenter", "roof",
                "painter", "pest control", "locksmith", "garage door"}

EN_VERB = {"تصليح": "repair", "اصلاح": "repair", "صيانة": "maintenance", "صيان": "maintenance",
           "تنظيف": "cleaning", "تركيب": "installation", "تعبئة": "refill", "تعبئ": "refill",
           "تبديل": "replacement"}


def seed_head(seed):
    """'Fridge repair dubai' -> 'fridge'. Strips action words and location."""
    loc = _loc_tokens()
    words = [w for w in toks(seed) if w not in ACTION_WORDS and w not in loc
             and w not in {"in", "near", "me", "uae", "best", "the"}]
    return " ".join(words).strip()


def seed_display(seed):
    """What the business actually sells, in its own words: the seed minus the
    location and filler. "Curtain installation dubai" -> "Curtain Installation",
    "Handyman dubai" -> "Handyman". Never appends "Repair" to a service that
    is not a repair."""
    loc = _loc_tokens()
    words = [w for w in _raw_toks(seed) if norm_phrase(w) not in loc
             and w not in {"in", "near", "me", "uae", "best", "the", "services", "service"}]
    out = " ".join(words)
    return (out if is_arabic(out) else title(out)) or seed


def seed_surface_head(seed):
    """The service noun exactly as typed in the seed (Arabic keeps its real
    spelling: "غسالات", not the normalised stem used for matching)."""
    loc = _loc_tokens()
    return " ".join(w for w in _raw_toks(seed)
                    if norm_phrase(w) not in loc and norm_phrase(w) not in ACTION_WORDS
                    and w not in {"in", "near", "me", "uae", "best", "the"}).strip()


def family_of(head):
    for fam in SYNONYMS:
        if head in fam or head in {norm_phrase(x) for x in fam}:
            return fam
    return None


def build_services(seeds):
    manual = os.environ.get("SERVICES_JSON", "").strip()
    if manual:
        try:
            svcs = json.loads(manual)
            return [{"name": title(s["name"]), "display": title(s["name"]), "lang": "en",
                     "neg_heads": list(s["aliases"]), "surface_heads": [], "eng_head": s["name"],
                     "aliases": sorted({a.lower() for a in s["aliases"]},
                                                                 key=lambda a: -len(a)),
                     "seeds": []} for s in svcs if s.get("aliases")]
        except Exception as e:
            print(f"⚠️ SERVICES_JSON unreadable ({e}) — falling back to seeds.")

    services = []
    for seed in seeds:
        head = seed_head(seed)
        if not head:
            continue
        # ONE LANGUAGE PER SERVICE. "washing machine repair" and "تصليح غسالات"
        # are the same trade but can never share an ad group: an RSA is
        # written in one language and the page lives under /ar/ or not.
        lang = "ar" if is_arabic(seed) else "en"
        fam = family_of(head)
        fam_lang = {x for x in (fam or ()) if is_arabic(x) == (lang == "ar")}
        surface = seed_surface_head(seed)
        raw_aliases = (fam_lang | {surface}) if surface else (fam_lang or {head})
        aliases = {norm_phrase(x) for x in raw_aliases} | {head}
        eng = sorted((x for x in (fam or ()) if not is_arabic(x)), key=len)
        canon = [x for x in eng if x in CANONICAL_EN]
        eng_head = head if lang == "en" else (canon[-1] if canon else (eng[-1] if eng else ""))
        fam_key = frozenset(norm_phrase(x) for x in fam) if fam else frozenset({head})
        merged = False
        for s in services:
            if s["lang"] == lang and set(s["aliases"]) & aliases:
                s["aliases"] = sorted(set(s["aliases"]) | aliases, key=lambda a: -len(a))
                s["neg_heads"] = sorted(set(s["neg_heads"]) | raw_aliases)
                s["seeds"].append(seed)
                merged = True
                print(f"   🔗 '{seed}' merged into '{s['name']}' (synonym)")
                break
        if not merged:
            neg = set(raw_aliases)
            if lang == "ar":   # negatives match whole words: add the ال forms
                neg |= {"ال" + x for x in raw_aliases if " " not in x and not x.startswith("ال")}
            services.append({
                "name": title(eng_head or head) + (" (AR)" if lang == "ar" else ""),
                "display": seed_display(seed),
                "lang": lang,
                "aliases": sorted(aliases, key=lambda a: -len(a)),
                "neg_heads": sorted(neg),
                "surface_heads": [surface] if surface else [],
                "eng_head": eng_head,
                "fam_key": fam_key,
                "seeds": [seed]})
    # "led" and "lcd" alone are too broad unless the service IS a TV — they
    # stay only in the TV family, which is where they came from.
    return services


def _singular(text):
    return " ".join(w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w
                    for w in text.split())


_SUFFIXES = ("s", "es", "ing", "er", "ers", "ed")


def _alias_hit(text, alias):
    """Whole-word alias match that also accepts inflections of a single-word
    alias: "roof" matches "roofing"/"roofer", "paint" matches "painting".
    Only for aliases of 4+ letters, so "tv"/"ac" can never over-match."""
    if has_phrase(text, alias):
        return True
    if " " in alias or len(alias) < 4:
        return False
    return any(has_phrase(text, alias + suf) for suf in _SUFFIXES)


def assign_service(kw, services):
    """Longest alias wins; ties -> earliest position in the query.
    Plural-insensitive: "bosch refrigerators repair" -> refrigerator."""
    text = _singular(" ".join(toks(kw)))
    lang = "ar" if is_arabic(kw) else "en"
    best, best_len, best_pos = None, 0, 10**6
    for i, s in enumerate(services):
        if s.get("lang", "en") != lang:
            continue
        for a in s["aliases"]:
            if _alias_hit(text, a):
                alen = len(a.split())
                pos = (" " + text + " ").find(" " + a + " ")
                if alen > best_len or (alen == best_len and pos < best_pos):
                    best, best_len, best_pos = i, alen, pos
    return best


# ─────────────────────────────────────────────────────────────────────────
# 3/4. Junk filter + layer classifier
# ─────────────────────────────────────────────────────────────────────────
def wrong_locations():
    out = []
    for city, sib in _SIBLINGS.items():
        if city in TARGET_LOCATION:
            out += sib
    out += [x.strip().lower() for x in os.environ.get("WRONG_LOCATIONS", "").split(",") if x.strip()]
    return out


WRONG_LOCS = wrong_locations()


# Faults the owner cannot fix alone -> they hire. "washing machine drum
# broken", "fridge compressor dead", "dishwasher burst" convert.
HARD_FAULTS = {"broken", "broke", "burst", "damaged", "damage", "dead", "cracked",
               "sparking", "smoke", "smoking", "burnt", "burned", "shock", "exploded",
               "flooding", "failed", "failure", "tripping", "trips",
               "خربان", "خربانة", "مكسور", "مكسورة", "محروق", "محروقة", "معطل", "معطلة", "تالف"}
# Soft symptoms WITHOUT any hire signal are research: "fridge not cooling",
# "washing machine not spinning", "dishwasher error e24". People search them
# to fix it themselves; they go to the page FAQ, not to the ads.
HIRE_SIGNALS = HIRE_WORDS | {"near", "nearby", "emergency", "urgent", "company",
                             "call", "book", "shop",
                             "center", "centre", "today", "now", "open", "hire",
                             "قريب", "طوارئ", "عاجل", "فوري", "شركة", "مركز", "رقم", "اتصال"}


def symptom_only(text):
    tset = set(text.split())
    trig = {t for t in tset if t in PROBLEM_TOKENS or _ERROR_CODE.match(t)}
    if not trig:
        return False
    return not (tset & HIRE_SIGNALS) and not (tset & HARD_FAULTS)


def junk_reason(kw):
    text = " ".join(toks(kw))
    tset = set(text.split())
    has_hire = bool(tset & HIRE_WORDS)
    for loc in WRONG_LOCS:
        if has_phrase(text, loc):
            return f"wrong location: {loc}"
    if text.startswith(DIY_STARTS):
        return "diy/info question"
    hit = tset & JUNK_TOKENS
    if hit:
        return f"non-service intent: {sorted(hit)[0]}"
    for ph in JUNK_PHRASES:
        if has_phrase(text, ph):
            return f"non-service intent: {ph}"
    for ph in OTHER_SERVICE_PHRASES:
        if has_phrase(text, ph):
            return f"other service (not seeded): {ph}"
    soft = tset & SOFT_JUNK_TOKENS
    if soft and not has_hire:
        return f"non-service intent: {sorted(soft)[0]}"
    if (tset & PRICE_TOKENS) and not has_hire:
        return "product price (no service word)"
    if symptom_only(text):
        return "symptom only (DIY/info - goes to page FAQ)"
    if not has_hire and not (tset & HARD_FAULTS) and not (tset & URGENT_TOKENS)             and not any(has_phrase(text, p) for p in _URGENT_PHRASES):
        # bare "washing machine dubai" / "samsung fridge" = shoppers
        return "no service intent (bare product)"
    return None


def brands_in(text):
    ts = text.split()
    found = []
    for i, t in enumerate(ts):
        if t in BRANDS and t not in _WEAK_BRANDS:
            found.append(t)
        elif t in _WEAK_BRANDS and i + 1 < len(ts) and (t, ts[i + 1]) in _BRAND_PAIRS:
            found.append(f"{t} {ts[i + 1]}")
    for b in BRANDS:
        if " " in b and has_phrase(text, b):
            found.append(b)
    return found


_PROBLEM_NEG = {"not", "wont", "won't", "doesnt", "doesn't", "dont", "don't", "cant",
                "stopped", "stop", "لا", "لايعمل"}
_FAULT_WORDS = {"leak", "leaking", "leaks", "noise", "noisy", "loud", "error",
                "code", "broken", "problem", "problems", "issue", "issues",
                "fault", "faulty", "smell", "smells", "smelly", "vibrating",
                "vibration", "shaking", "overheating", "tripping", "trips",
                "stuck", "jammed", "blinking", "flashing", "beeping",
                "burning", "sparking", "dead", "dripping", "blocked",
                "clogged", "frozen", "icing", "sweating", "humming",
                "clicking", "عطل", "اعطال", "أعطال", "تسريب", "صوت"} | _PROBLEM_NEG
_STRONG_PARTS = {"compressor", "motor", "pcb", "board", "pump", "thermostat",
                 "bearing", "bearings", "belt", "drum", "gasket", "seal",
                 "element", "backlight", "panel", "screen", "capacitor",
                 "valve", "timer", "sensor", "hinge", "coil", "inverter",
                 "relay", "hose", "lock", "ضاغط", "كمبروسر"}


def problem_hits(text, service_aliases):
    tset = set(text.split())
    alias_toks = {w for a in service_aliases for w in a.split()}
    hits = {t for t in tset if (t in PROBLEM_TOKENS or _ERROR_CODE.match(t))
            and t not in alias_toks}
    # "gas refill" / "drain cleaning" are services, not faults — a part word
    # next to a service verb with no negation stays CORE.
    hits |= (tset & HARD_FAULTS)
    fault_words = hits & _FAULT_WORDS
    if fault_words or any(_ERROR_CODE.match(t) for t in hits):
        return sorted(hits)
    # part-only queries ("washing machine motor repair", "fridge compressor
    # replacement") are diagnosed faults -> PROBLEM; generic service phrases
    # like "cooling", "power", "door", "gas" alone are not.
    return sorted((hits - fault_words) & _STRONG_PARTS)


_NEGATIONS = {"not", "wont", "won't", "doesnt", "doesn't", "dont", "don't", "cant",
               "stopped", "stop"}
_GENERIC_PART_WORDS = {"cooling", "heating", "spinning", "draining", "drain", "spin",
                       "power", "gas", "door", "fan", "filter", "ice", "screen", "panel",
                       "board", "seal", "element", "code"}


def problem_triggers(text, service_aliases):
    """The tokens that MAKE a query a problem query — safe to negate in the
    groups below. "not spinning" -> {"not"}; "fridge not cooling" -> {"not"};
    "compressor repair" -> {"compressor"}. Incidental words ("cooling",
    "draining", "gas") are never negated: "fridge cooling repair" and
    "fridge gas refill" are CORE queries and must keep a home."""
    return {t for t in problem_hits(text, service_aliases)
            if t not in _GENERIC_PART_WORDS}


def urgent_hits(text):
    """Local / voice / time MODIFIERS ("near me", "who can", "today"). They
    no longer choose a layer — they only mark a query as a hire, not info."""
    tset = set(text.split())
    hits = [p for p in _URGENT_PHRASES if has_phrase(text, p)]
    single = tset & (URGENT_TOKENS - {"me", "same", "open", "home", "who", "where", "call"})
    return sorted(set(hits) | single)


def emergency_hits(text):
    tset = set(text.split())
    return sorted({p for p in EMERGENCY_PHRASES if has_phrase(text, p)}
                  | (tset & EMERGENCY_TOKENS))


def layer_of(kw, service):
    """EMERGENCY (only for a 24/7 business) > BRAND > PROBLEM > CORE.
    Brand beats problem: "samsung washer not draining" is bought by the
    person who wants a Samsung specialist, and the brand is the one word the
    headline can match exactly. Near-me / voice / "today" never choose a
    layer. (The SYMPTOM layer is decided by the junk stage, not here.)"""
    text = " ".join(toks(kw))
    if OPEN_24_7:
        e = emergency_hits(text)
        if e:
            return "emergency", e
    b = brands_in(text)
    if b:
        return "brand", b
    ph = problem_hits(text, service["aliases"])
    if ph:
        return "problem", ph
    return "core", []


def classify(kw, services):
    """(service index, layer) exactly as main() files a keyword — minus the
    Planner-only 'informational intent' flag, which a search term lacks.
    (i, None) = junk for that service; (None, None) = no service."""
    i = assign_service(kw, services)
    if i is None:
        return None, None
    why = junk_reason(kw)
    if why:
        if SYMPTOM_TEST and why.startswith("symptom only"):
            return i, "symptom"
        return i, None
    return i, layer_of(kw, services[i])[0]


def owner_of(kw, services, groups):
    """The ad group that owns a query. groups = {"<service>|<layer>": name}.
    A folded layer falls back to the service's core group; a symptom query
    without a symptom test group has no owner."""
    i, layer = classify(kw, services)
    if i is None or layer is None:
        return None
    name = services[i]["name"]
    if layer == "symptom":
        return groups.get(f"{name}|symptom")
    return groups.get(f"{name}|{layer}") or groups.get(f"{name}|core")


# Every run-dependent piece of the classifier (env, niche allow list, the
# typo vocabulary built from this run's services). Saved in the plan so the
# silo router and Stage 3 decide exactly as this stage did.
_SNAPSHOT_SETS = ("JUNK_TOKENS", "SOFT_JUNK_TOKENS", "BRANDS", "HIRE_WORDS", "HIRE_SIGNALS",
                  "PROBLEM_TOKENS", "HARD_FAULTS", "PRICE_TOKENS", "URGENT_TOKENS",
                  "EMERGENCY_TOKENS", "_WEAK_BRANDS", "_FAULT_WORDS", "_STRONG_PARTS", "_NO_FIX")
_SNAPSHOT_LISTS = ("WRONG_LOCS", "DIY_STARTS", "_URGENT_PHRASES", "EMERGENCY_PHRASES",
                   "JUNK_PHRASES", "OTHER_SERVICE_PHRASES")


def classifier_snapshot():
    g = globals()
    snap = {n: sorted(g[n]) for n in _SNAPSHOT_SETS}
    snap.update({n: list(g[n]) for n in _SNAPSHOT_LISTS})
    snap["_BRAND_PAIRS"] = sorted(" ".join(p) for p in _BRAND_PAIRS)
    snap["_CANON"] = sorted(_CANON)
    snap["_GLUE"] = dict(sorted(_GLUE.items()))
    snap["OPEN_24_7"] = OPEN_24_7
    snap["SYMPTOM_TEST"] = SYMPTOM_TEST
    return snap


def restore_classifier(snap):
    """Load a plan's snapshot into this module (Stage 3 / router)."""
    if not snap:
        return
    g = globals()
    for n in _SNAPSHOT_SETS:
        g[n] = set(snap[n])
    for n in _SNAPSHOT_LISTS:
        g[n] = tuple(snap[n]) if n == "DIY_STARTS" else list(snap[n])
    g["_BRAND_PAIRS"] = {tuple(p.split(" ", 1)) for p in snap["_BRAND_PAIRS"]}
    _CANON.clear(); _CANON.update(snap["_CANON"])
    _GLUE.clear(); _GLUE.update(snap["_GLUE"])
    g["OPEN_24_7"] = snap["OPEN_24_7"]
    g["SYMPTOM_TEST"] = snap["SYMPTOM_TEST"]


def _norm_set(sset):
    return set(sset) | {norm_phrase(x) for x in sset if norm_phrase(x)}


for _name in ("ACTION_WORDS", "SERVICE_VERBS", "BRANDS", "PROBLEM_TOKENS", "URGENT_TOKENS",
              "JUNK_TOKENS", "SOFT_JUNK_TOKENS", "PRICE_TOKENS", "HARD_FAULTS", "HIRE_SIGNALS",
              "PROVIDER_NOUNS", "HIRE_WORDS", "EMERGENCY_TOKENS"):
    globals()[_name] = _norm_set(globals()[_name])
_URGENT_PHRASES = list(dict.fromkeys(_URGENT_PHRASES + [norm_phrase(x) for x in _URGENT_PHRASES]))
JUNK_PHRASES = list(dict.fromkeys(JUNK_PHRASES + [norm_phrase(x) for x in JUNK_PHRASES]))
EMERGENCY_PHRASES = list(dict.fromkeys(EMERGENCY_PHRASES + [norm_phrase(x) for x in EMERGENCY_PHRASES]))
DIY_STARTS = tuple(dict.fromkeys(DIY_STARTS + tuple(norm_phrase(x) + " " for x in DIY_STARTS)))
WRONG_LOCS = list(dict.fromkeys(WRONG_LOCS + [norm_phrase(x) for x in WRONG_LOCS]))


LAYER_PRECEDENCE = ["emergency", "brand", "problem", "symptom", "core"]
LAYER_LABEL = {
    "core": "{disp}",
    "brand": "{disp} - Brands",
    "problem": "{svc} Problems & Parts",
    "symptom": "{disp} - Symptoms (Test)",
    "emergency": "{disp} - Emergency 24/7",
}
LAYER_LABEL_AR = {
    "core": "{disp}",
    "brand": "{disp} - ماركات",
    "problem": "{disp} - أعطال",
    "symptom": "{disp} - أعراض (تجربة)",
    "emergency": "{disp} - طوارئ 24 ساعة",
}
LAYER_ANCHOR = {"core": "services", "brand": "brands", "problem": "problems",
                "symptom": "problems", "emergency": "emergency"}
LAYER_BID = {"core": 1.0, "brand": 1.0, "problem": 1.15, "symptom": SYMPTOM_BID,
             "emergency": 1.2}
LAYER_MATCH = {"symptom": "exact"}   # everything else: phrase


# ─────────────────────────────────────────────────────────────────────────
# 5. Tiering
# ─────────────────────────────────────────────────────────────────────────
def slots_for(volume, single_service):
    cap = MAX_SLOTS_SINGLE if single_service else MAX_SLOTS
    return max(1, min(cap, math.ceil(volume / TIER_STEP) if volume > 0 else 1))


VOLUME_BASIS = {"value": "estimated"}


def real_volume(rows):
    """Sum of searches with Planner close-variant clusters counted ONCE.

    When the rows carry Google's own `close_variants` (Planner historical
    metrics), those clusters are used and the number is exact. Otherwise it
    is an ESTIMATE: the Planner reports one shared number for a whole variant
    cluster ("washing machine repair", "fix washing machine", "washer fixer"
    all came back at 6,600 in the Sep 2026 Dubai run — the naive sum said
    55,120 for a service with ~9,000), so rows sharing volume + competition
    index + bid range are taken as one cluster. Small rows (<100) are left
    alone: equal 10s and 20s are common and genuinely different searches.
    The plan records which of the two it was (volume_basis)."""
    if any(r.get("close_variants") for r in rows):
        VOLUME_BASIS["value"] = "google close_variants"
        seen, total = set(), 0
        for r in rows:
            key = min([r["keyword"].lower()] + [c.lower() for c in r.get("close_variants") or []])
            if key in seen:
                continue
            seen.add(key)
            total += r["avg_monthly_searches"]
        return total
    seen, total = set(), 0
    for r in rows:
        v = r["avg_monthly_searches"]
        if v >= 100:
            sig = (v, r.get("competition_index", 0), r.get("low_top_bid", 0), r.get("high_top_bid", 0))
            if sig in seen:
                continue
            seen.add(sig)
        total += v
    return total


def row_cpc(r):
    """Planner's expected CPC for a row: the middle of its top-of-page bid
    range (account currency). 0 when the Planner gave no bid."""
    lo, hi = float(r.get("low_top_bid") or 0), float(r.get("high_top_bid") or 0)
    return (lo + hi) / 2 if hi else lo


def avg_cpc(rows):
    """Volume-weighted Planner CPC. AVG_CPC (env) overrides; 0 = unknown."""
    forced = _env_float("AVG_CPC", 0)
    if forced > 0:
        return forced
    num = den = 0.0
    for r in rows:
        c = row_cpc(r)
        if c > 0:
            num += c * r["avg_monthly_searches"]
            den += r["avg_monthly_searches"]
    return num / den if den else 0.0


def expected_clicks(volume, cpc, share):
    """Clicks/month a layer can realistically buy:
    min(budget side 30.4 x B x share / CPC, demand side V x IS x CTR).
    Without a DAILY_BUDGET (sized later from the bids) or a CPC, only the
    demand side is known."""
    demand = volume * ASSUMED_IS * ASSUMED_CTR
    budget = _env_float("DAILY_BUDGET", 0)
    if budget > 0 and cpc > 0:
        return min(demand, 30.4 * budget * share / cpc)
    return demand


def plan_service(svc, rows, single_service, campaign_volume):
    V = real_volume([r for r in rows if r["_layer"] != "symptom"])
    slots = slots_for(V, single_service)
    by_layer = defaultdict(list)
    for r in rows:
        by_layer[r["_layer"]].append(r)
    layer_vol = {l: real_volume(rs) for l, rs in by_layer.items()}
    layer_cpc = {l: avg_cpc(rs) for l, rs in by_layer.items()}
    layer_clicks = {l: round(expected_clicks(layer_vol[l], layer_cpc[l],
                                             layer_vol[l] / max(campaign_volume, 1)), 1)
                    for l in by_layer}

    # A layer splits only when it can buy MIN_LAYER_CLICKS a month (the
    # GPT-review rule). The volume tier above still caps the COUNT: slots =
    # ceil(V / TIER_STEP), max MAX_SLOTS. Most clicks first — that is where
    # the separate ad copy earns the most.
    viable = [l for l in ("emergency", "brand", "problem")
              if by_layer.get(l) and layer_clicks[l] >= MIN_LAYER_CLICKS]
    candidates = sorted(viable, key=lambda l: -layer_clicks[l])
    split = candidates[: max(0, slots - 1)]
    folded = [l for l in ("emergency", "brand", "problem") if by_layer.get(l) and l not in split]

    groups = {"core": list(by_layer.get("core", []))}
    for l in folded:
        groups["core"] += by_layer[l]
    for l in split:
        groups[l] = by_layer[l]
    if not groups["core"]:
        # every keyword was brand/problem/emergency: the biggest split layer
        # becomes the core so the service still has its generic group
        biggest = split.pop(0)
        groups["core"] = groups.pop(biggest)
    # The symptom TEST group sits outside the slot count: exact match, low
    # bid, and it never takes a slot from brand or problem.
    to_faq = []
    if by_layer.get("symptom"):
        if layer_clicks["symptom"] >= SYMPTOM_MIN_CLICKS:
            groups["symptom"] = by_layer["symptom"]
        else:
            to_faq = by_layer["symptom"]

    return {
        "service": svc["name"],
        "volume": V,
        "slots_allowed": slots,
        "layer_volume": {l: layer_vol.get(l, 0) for l in LAYER_PRECEDENCE},
        "layer_clicks_per_month": {l: layer_clicks.get(l, 0) for l in LAYER_PRECEDENCE},
        "layer_cpc": {l: round(layer_cpc.get(l, 0), 2) for l in LAYER_PRECEDENCE},
        "split_layers": split,
        "folded_into_core": folded,
        "groups": groups,
        "symptom_to_faq": to_faq,
    }


def budget_guard(service_plans, all_rows):
    """Fewer groups when the budget cannot feed them. Each ad group needs
    ~3 clicks/day to learn anything. When DAILY_BUDGET / CPC < 3 x groups,
    the symptom tests go first, then the smallest split layers fold back
    into their core. CPC is the Planner's own (AVG_CPC overrides) — before
    Sep 2026 nothing passed AVG_CPC, so this guard never ran."""
    budget = _env_float("DAILY_BUDGET", 0)
    cpc = avg_cpc(all_rows)
    if budget <= 0 or cpc <= 0:
        print("   ℹ️ Budget guard: no DAILY_BUDGET (or no Planner CPC) — group count "
              "set by volume tier and demand-side clicks only")
        return
    max_groups = max(len(service_plans), int(budget / cpc / 3))
    total = sum(len(p["groups"]) for p in service_plans)
    print(f"   💸 Budget guard: {budget:g}/day at ~{cpc:.0f} CPC supports ~{max_groups} "
          f"group(s); plan has {total}")
    for p in service_plans:
        if total <= max_groups:
            break
        if "symptom" in p["groups"]:
            p["symptom_to_faq"] = p.get("symptom_to_faq", []) + p["groups"].pop("symptom")
            total -= 1
            print(f"   💸 Budget guard: dropped the symptom test for '{p['service']}'")
    while total > max_groups:
        cands = [(sum(r["avg_monthly_searches"] for r in p["groups"][l]), p, l)
                 for p in service_plans for l in p["split_layers"]]
        if not cands:
            break
        _, p, l = min(cands, key=lambda x: x[0])
        p["groups"]["core"] += p["groups"].pop(l)
        p["split_layers"].remove(l)
        p["folded_into_core"].append(l)
        total -= 1
        print(f"   💸 Budget guard: folded '{p['service']} / {l}' into core")


# ─────────────────────────────────────────────────────────────────────────
# 6. Negatives
# ─────────────────────────────────────────────────────────────────────────
def layer_tokens(rows, layer, service):
    out = set()
    for r in rows:
        text = " ".join(toks(r["keyword"]))
        if layer == "brand":
            out |= set(brands_in(text))
        elif layer == "problem":
            out |= problem_triggers(text, service["aliases"])
        elif layer == "emergency":
            out |= set(emergency_hits(text))
    # never negate negation words alone in Arabic ("لا" is too common)
    return {t for t in out if t not in {"لا"}}


SURFACE = defaultdict(set)   # normalised token -> spellings seen in the data


def silo_negatives(service_plans, services):
    by_name = {s["name"]: s for s in services}
    _AMBIGUOUS = {"led", "lcd", "ac", "a/c", "power", "boiler"}
    # negatives must be words people TYPE (Google matches negatives on the
    # surface form), so the raw alias spellings are used, not the stems
    heads = {s["name"]: [a for a in (s.get("neg_heads") or s["aliases"])
                         if len(a) > 2 and a not in _AMBIGUOUS]
             for s in services}
    for p in service_plans:
        svc = by_name[p["service"]]
        ltoks = {l: layer_tokens(p["groups"][l], l, svc) for l in p["split_layers"]}
        p["negatives"] = {}
        for l, rows in p["groups"].items():
            if l == "symptom":
                # exact match: it only ever serves its own queries
                p["negatives"][l] = []
                continue
            own_text = " | ".join(" ".join(toks(r["keyword"])) for r in rows)
            negs = set()
            # intra-service: negate every split layer ABOVE this one
            my_rank = LAYER_PRECEDENCE.index(l)
            for other in p["split_layers"]:
                if LAYER_PRECEDENCE.index(other) < my_rank:
                    negs |= ltoks[other]
            # cross-service: other services' head terms
            for other_svc, hs in heads.items():
                if other_svc == p["service"]:
                    continue
                for h in hs:
                    negs.add(h)
            # self-block guard (belt; analyze_with_claude has the braces)
            clean = sorted(n for n in negs if not has_phrase(own_text.replace(" | ", "  "), n)
                           and not any(has_phrase(" ".join(toks(r["keyword"])), n) for r in rows))
            # stems -> every real spelling seen in the data ("مكسور" -> "مكسورة")
            p["negatives"][l] = sorted({sf for n in clean for sf in SURFACE.get(n, {n})})


def service_heads(rows, svc, n=2):
    """The alias words people actually typed for this service, by volume.
    Arabic: the seed's own spelling — the match aliases are normalised
    stems ("غسال") that nobody types."""
    if svc.get("lang") == "ar":
        return svc.get("surface_heads") or [svc["display"]]
    vol = defaultdict(int)
    for r in rows:
        text = " ".join(toks(r["keyword"]))
        for a in svc["aliases"]:
            if has_phrase(text, a):
                vol[a] += r["avg_monthly_searches"]
                break
    return [a for a, _ in sorted(vol.items(), key=lambda x: -x[1])][:n] or [svc["aliases"][0]]


def silo_catchers(p, svc):
    """Every token the core negates must still match a POSITIVE keyword in
    the group that owns it, or the query falls between groups and is lost
    (phrase "fridge water leaking" does not catch "fridge leaking repair").
    One short phrase keyword per negated trigger does it: "fridge leaking",
    "samsung fridge", "fridge near me"."""
    all_rows = [r for rs in p["groups"].values() for r in rs]
    heads = service_heads(all_rows, svc)
    verb = service_verb(svc)
    out = defaultdict(list)
    ar = svc.get("lang") == "ar"
    for l in p["split_layers"]:
        trig = layer_tokens(p["groups"][l], l, svc)
        for h in heads:
            for t in sorted(trig):
                if ar:
                    # Arabic word order: verb + noun + qualifier
                    if _ERROR_CODE.match(t):
                        continue
                    kw = (f"{verb} {h} لا تعمل" if t == "لا" else f"{verb} {h} {t}")
                    if kw not in out[l]:
                        out[l].append(kw)
                    continue
                if l == "problem":
                    # with a service word: phrase "fridge leaking repair" catches
                    # "fridge leaking repair near me" but NOT the DIY query
                    # "fridge leaking" (blocked as symptom-only everywhere)
                    kw = (f"{h} not working {verb}" if t in _NEGATIONS
                          else f"{h} {t} {verb}" if t not in HARD_FAULTS else f"{h} {t}")
                elif l == "brand":
                    kw = f"{t} {h} {verb}"
                else:  # emergency — always with the service word, never "fridge now"
                    if t in ("near", "near me", "nearby", "close to me", "around me",
                             "open near me", "near me open", "open now", "open today"):
                        kw = f"{h} {verb} {'near me' if t == 'near' else t}"
                    elif t in ("emergency", "urgent", "same day", "24 hour", "24/7", "24", "24 hours"):
                        kw = f"{'24 hour' if t in ('24', '24 hours') else t} {h} {verb}"
                    elif t in ("nearest", "closest"):
                        kw = f"{t} {h} {verb}"
                    else:
                        continue   # "now", "who can"... are covered by the templates
                if _ERROR_CODE.match(t):
                    continue          # "washing machine e20" is not a keyword
                if kw not in out[l]:
                    out[l].append(kw)
    return {l: v[:15] for l, v in out.items()}


def service_verb(svc):
    """The action the business sells, from its own seed ("repair",
    "installation", "تصليح"...), in its real spelling."""
    for seed in svc.get("seeds", []) or [svc.get("display", "")]:
        for w in _raw_toks(seed):
            if norm_phrase(w) in SERVICE_VERBS and w not in {"service", "services", "company"}:
                return w
    return "تصليح" if svc.get("lang") == "ar" else "service"


# UAE areas used for geo query detection and the page's "areas served"
# block. Extend per market with GEO_AREAS (comma list).
_GEO_AREAS = ["dubai marina", "jlt", "jumeirah lake towers", "jvc", "jumeirah village circle",
              "downtown dubai", "business bay", "al barsha", "palm jumeirah", "arabian ranches",
              "dubai hills", "mirdif", "jumeirah", "umm suqeim", "al quoz", "motor city",
              "sports city", "damac hills", "the springs", "the meadows", "emirates hills",
              "silicon oasis", "al nahda", "al qusais", "bur dubai", "karama", "deira",
              "discovery gardens", "international city", "town square", "al furjan",
              "jebel ali", "the greens", "al warqa", "mudon", "creek harbour", "al safa"]
_GEO_AREAS += [a.strip().lower() for a in os.environ.get("GEO_AREAS", "").split(",") if a.strip()]


def intent_templates(p, svc, city):
    """Queries Planner rarely returns but buyers type — local, voice, geo and
    word-order variants — generated from THIS service's own words, then
    routed to the owning layer by the same classifier. Free (no API):
      local   "{h} {v} near me", "... near me open now", "... open now"
      urgent  "emergency {h} {v}", "24 hour {h} {v}", "same day {h} {v}"
      voice   "who can {v} my {h}", "{v} my {h}", "{h} {v} at home"
      order   "{v} {h} {city}", "{h} {v} {city}"
      brand   "{b} {h} {v} {city}" for the brands people searched
      geo     "{h} {v} {area}" only for areas that already show up in the
              Planner data (a made-up area keyword is 'low search volume')"""
    all_rows = [r for rs in p["groups"].values() for r in rs]
    heads = service_heads(all_rows, svc, n=2)
    v = service_verb(svc)
    city = (city or "").lower()
    brand_vol = defaultdict(int)
    geo_seen = set()
    for r in all_rows:
        text = " ".join(toks(r["keyword"]))
        for b in brands_in(text):
            brand_vol[b] += r["avg_monthly_searches"]
        for a in _GEO_AREAS:
            if has_phrase(text, a):
                geo_seen.add(a)
    brands = [b for b, _ in sorted(brand_vol.items(), key=lambda x: -x[1])][:3]
    out = []
    if svc.get("lang") == "ar":
        city_ar = city_names()[1]
        for h in heads:
            out += [f"{v} {h} قريب مني", f"{v} {h} {city_ar}".strip(), f"فني {h}",
                    f"فني {h} قريب مني", f"صيانة {h}", f"{v} {h} طوارئ", f"{v} {h} 24 ساعة",
                    f"{v} {h} في المنزل", f"شركة {v} {h}", f"رقم {v} {h}"]
            out += [f"{v} {h} {b}" for b in brands]
            out += [f"{v} {h} {a}" for a in sorted(geo_seen)[:5]]
        return list(dict.fromkeys(o for o in out if o))
    for h in heads:
        hv = f"{h} {v}".strip()
        out += [f"{hv} near me", f"{hv} near me open now", f"{hv} open now",
                f"emergency {hv}", f"24 hour {hv}", f"same day {hv}",
                f"who can {v} my {h}", f"{v} my {h}", f"{hv} at home",
                f"{v} {h} {city}".strip(), f"{hv} {city}".strip(),
                f"{h} technician near me"]
        out += [f"{b} {hv} {city}".strip() for b in brands]
        out += [f"{hv} {a}" for a in sorted(geo_seen)[:5]]
    return list(dict.fromkeys(o for o in out if o))


CAMPAIGN_NEGATIVES = sorted(
    {"buy", "for sale", "sale", "second hand", "used", "olx", "dubizzle", "job", "jobs",
     "vacancy", "salary", "hiring", "course", "training", "diy", "manual", "pdf",
     "youtube", "spare parts", "wholesale", "rent", "rental", "free", "specs",
     "showroom", "how to"}
    | {t for t in os.environ.get("EXTRA_JUNK", "").split(",") if t.strip()})


# ─────────────────────────────────────────────────────────────────────────
# 7. Landing page keyword map
# ─────────────────────────────────────────────────────────────────────────
def keyword_map(p, svc, location, symptoms=()):
    all_rows = [r for rs in p["groups"].values() for r in rs]
    all_rows.sort(key=lambda r: -r["avg_monthly_searches"])
    loc = location.split(",")[0].strip().lower()
    if svc.get("lang") == "ar":
        # an Arabic page's title reads "تصليح غسالات دبي", never "... dubai"
        loc = city_names()[1] or ""
    core = sorted(p["groups"].get("core", []), key=lambda r: -r["avg_monthly_searches"])

    def _plain(kw):
        text = " ".join(toks(kw))
        return not urgent_hits(text) and not emergency_hits(text)

    # primary: highest-volume CORE keyword with a service verb and no
    # modifier — this is the H1 / title term. "dishwasher repair near me" is
    # often the biggest row, but "Dishwasher Repair Near Me Dubai" is not a
    # headline; the modifier variants stay in the body and the FAQ.
    _verb = [r["keyword"] for r in core if set(toks(r["keyword"])) & SERVICE_VERBS]
    primary = next((k for k in _verb if _plain(k)),
                   _verb[0] if _verb else (core[0]["keyword"] if core else svc["name"].lower()))
    if loc and loc not in primary:
        primary_loc = f"{primary} {loc}"
    else:
        primary_loc = primary
    secondary = [r["keyword"] for r in core if r["keyword"] != primary][:10]

    brand_vol = defaultdict(int)
    for r in all_rows:
        for b in brands_in(" ".join(toks(r["keyword"]))):
            brand_vol[b] += r["avg_monthly_searches"]
    brands = [title(b) for b, _ in sorted(brand_vol.items(), key=lambda x: -x[1])][:10]

    problems = [r["keyword"] for r in sorted(p["groups"].get("problem", []) or
                                             [r for r in all_rows if r["_layer"] == "problem"],
                                             key=lambda r: -r["avg_monthly_searches"])][:12]
    emergency = [r["keyword"] for r in all_rows if emergency_hits(" ".join(toks(r["keyword"])))][:10]
    # near me / at home / open now / who can — the local + voice layer of the
    # page (they live in the core ad group, so the page must answer them too)
    urgent = [r["keyword"] for r in all_rows if urgent_hits(" ".join(toks(r["keyword"])))][:10]
    symptoms = list(dict.fromkeys([r["keyword"] for r in p["groups"].get("symptom", [])]
                                  + list(symptoms)))
    questions = [r["keyword"] for r in all_rows
                 if toks(r["keyword"])[:1] and toks(r["keyword"])[0] in
                 {"who", "where", "which", "what", "how", "can", "is", "does"}][:8]
    areas_seen = sorted({a for r in all_rows for a in _GEO_AREAS
                         if has_phrase(" ".join(toks(r["keyword"])), a)})
    return {
        "primary": primary_loc,
        "areas_in_queries": areas_seen,
        "secondary": secondary,
        "brands": brands,
        "problems": problems,
        "urgent_local": urgent,
        "emergency": emergency,
        "voice_questions": questions,
        "placement": {
            "title": f"{title(primary_loc)} | Same-Day, All Brands"[:60],
            "meta_description_must_include": [primary_loc] + secondary[:1],
            "h1": title(primary_loc),
            "h2_sections": [
                {"layer": l, "anchor": LAYER_ANCHOR[l],
                 "must_include": (brands[:3] if l == "brand" else
                                  problems[:3] if l == "problem" else
                                  symptoms[:3] if l == "symptom" else
                                  emergency[:3] if l == "emergency" else
                                  (secondary[:2] + urgent[:1]))}
                # symptom shares the #problems section (its group lands there)
                for l in LAYER_PRECEDENCE if p["groups"].get(l) and l != "symptom"
            ] + ([{"layer": "brand", "anchor": "brands", "must_include": brands[:3]}]
                 if brands and "brand" not in p["groups"] else [])
              + ([{"layer": "problem", "anchor": "problems",
                   "must_include": (problems[:3] or symptoms[:3])}]
                 if (problems or symptoms) and "problem" not in p["groups"] else []),
            # symptom-only searches are not bought in ads, but they are the
            # exact questions the page's FAQ should answer (topical relevance
            # for Quality Score, and rich results for SEO)
            "faq_from": (questions + list(symptoms))[:10] or [f"how much does {primary} cost",
                                                              f"do you offer same day {primary}"],
            "symptom_faq": list(symptoms)[:10],
            "body_rules": "primary 3-5x naturally; every secondary once; each brand "
                          "and problem once in its section; no stuffing, no hidden text",
        },
        "schema": {
            "types": ["LocalBusiness", "Service", "FAQPage", "BreadcrumbList"],
            "service.serviceType": title(primary),
            "service.name": title(primary_loc),
            "service.areaServed": location,
            "offer_catalog": [f"{b} {svc.get('display', svc['name'])}" for b in brands[:6]]
                             + [title(x) for x in problems[:6]],
            "never": "no AggregateRating/Review unless real, verifiable reviews exist",
        },
    }


def register_other_services(services):
    """Trades in _OTHER_FAMILIES that this run did NOT seed become junk. A
    trade named in the niche or the seeds counts as seeded even when the
    services came from SERVICES_JSON ("drain", "leak"), so a plumbing
    business never loses "plumber near me"."""
    seeded = {a for s in services for a in s["aliases"]}
    told = " " + norm_phrase(os.environ.get("NICHE_DESCRIPTION", "") + " "
                             + os.environ.get("SEED_KEYWORDS", "").replace(",", " ")) + " "
    OTHER_SERVICE_PHRASES[:] = []
    for fam in _OTHER_FAMILIES:
        fam_n = {norm_phrase(x) for x in fam} | set(fam)
        if fam_n & seeded or any(has_phrase(told, x) for x in fam_n if x):
            continue
        OTHER_SERVICE_PHRASES.extend(sorted(x for x in fam_n if x))


def geo_context():
    """(areas inside the target city, other provinces/states of its country)
    from the same Google geo-target data Stage 3.9 uses — any city, any
    country, nothing per market in the code. Areas feed the geo templates and
    the page's areas block; other provinces become wrong-location junk
    ("fridge repair sharjah" in a Dubai plan, "plumber dallas" in a Seattle
    one). GEO_LOOKUP=off or any failure -> ([], []), and the built-in table
    plus GEO_AREAS / WRONG_LOCATIONS stay in charge."""
    GEO_CITIES.clear()
    if not TARGET_LOCATION or not _env_on("GEO_LOOKUP", "on"):
        return [], []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import generate_locations as gl
        index = gl.fetch_json(f"{gl.GEO_BASE}/index.json")
        cc, _rest = gl.resolve_country(TARGET_LOCATION, index)
        if not cc:
            return [], []
        geo = gl.fetch_json(f"{gl.GEO_BASE}/{cc}.json")
        # The city is whichever comma part names a real place EXACTLY:
        # "Seattle, WA, United States" -> "Seattle". No exact place, no geo
        # context — the country-level fallback would call every state an
        # "area" of the target.
        names = {gl.norm(g.get("n", "")) for g in geo}
        city = next((p.strip() for p in TARGET_LOCATION.split(",")
                     if p.strip() and gl.norm(p) in names), "")
        if not city:
            return [], []
        cnorm = gl.norm(city)
        exact = [g for g in geo if gl.norm(g.get("n", "")) == cnorm]
        # inside = every place whose canonical path runs through the target
        # ("Ballard,Seattle,Washington,..."), whether the target is a city
        # or a province; ancestors = the target's own state/country, which
        # are never a "wrong" location ("plumber seattle washington").
        anc_paths = {g["n"] for g in exact}
        ancestors = {gl.norm(p) for g in exact for p in str(g.get("c", "")).split(",")}
        chosen = exact + [g for g in geo if g not in exact and any(
            ("," + a + ",") in ("," + str(g.get("c", "")) + ",") for a in anc_paths)]
        inside = {id(g) for g in chosen}
        # Some countries' data skips the city in a neighbourhood's path
        # (US: "Ballard,Washington,United States"), so a neighbourhood of the
        # target's own state/province counts as an area too. Over-inclusive on
        # purpose: an area is only ever protected or used in templates when the
        # data mentions it, while a wrong "wrong location" drops a buyer.
        parents = {str(g.get("c", "")).split(",")[1] for g in exact
                   if len(str(g.get("c", "")).split(",")) >= 3}
        nearby = [g for g in geo if id(g) not in inside
                  and g.get("t") in ("Neighborhood", "District", "Borough")
                  and len(str(g.get("c", "")).split(",")) >= 3
                  and str(g.get("c", "")).split(",")[1] in parents]
        chosen += nearby
        _own = {gl.norm(g["n"]) for g in chosen}
        areas = sorted({g["n"].lower() for g in chosen
                        if gl.norm(g["n"]) != cnorm and g.get("t") != "Country"})
        wrong = sorted({g["n"].lower() for g in geo
                        if g.get("t") in ("Province", "State", "Region", "Governorate", "Territory")
                        and id(g) not in inside and gl.norm(g["n"]) not in ancestors})
        # every OTHER town of the country, for wrong_city_names() to match
        # against the data (only the names that actually occur are kept)
        GEO_CITIES.update(gl.norm(g["n"]) for g in geo
                          if g.get("t") in ("City", "Municipality", "Town", "County")
                          and id(g) not in inside and gl.norm(g["n"]) not in ancestors
                          and gl.norm(g["n"]) not in _own)
        return areas, wrong
    except Exception as e:
        print(f"   ⚠️ geo lookup failed ({str(e)[:80]}) — built-in area lists used")
        return [], []


GEO_CITIES = set()   # filled by geo_context(); other towns of the target's country


def wrong_city_names(keywords, services, own_areas):
    """Other towns that appear in THIS data as the place a search is about:
    the last 1-3 words of a query, straight after a hire word, a service word,
    "in" or "near" ("plumber portland", "fridge repair in al ain"). Matching
    on position keeps town names that are ordinary words out of it, and only
    names found in the data are returned, so the list stays small enough for
    the plan and the silo router."""
    if not GEO_CITIES:
        return []
    before = set(HIRE_WORDS) | {w for s in services for a in s["aliases"] for w in a.split()} \
        | {"in", "near", "at", "around"}
    own = {norm_phrase(a) for a in own_areas} | set(own_areas) | set(_loc_tokens())
    vocab = set(HIRE_WORDS) | set(URGENT_TOKENS) | set(BRANDS) | set(PROBLEM_TOKENS)
    found = set()
    for kw in keywords:
        t = str(kw).lower().split()
        for n in (3, 2, 1):
            if len(t) <= n:
                continue
            tail = " ".join(t[-n:])
            if tail in GEO_CITIES and t[-n - 1] in before and tail not in own \
                    and not (n == 1 and (tail in vocab or len(tail) < 4)):
                found.add(tail)
                break
    return sorted(found)


def resolve_cannibalization(groups):
    """One owner per query. groups: [{"name", "language", "match_type",
    "keywords": [...], "negatives": [...]}] — keywords = everything the group
    bids on (Planner rows, catchers, expansions, rescues).

    When group A's PHRASE keyword reaches group B's keyword ("dryer repair"
    reaches "washer dryer repair"), both bid on the same search and compete
    with each other in the auction. B's keyword is the more specific one, so
    B owns it: it is added to A as a phrase negative — unless A itself bids
    on something containing it (that would block A's own keyword) or A
    already negates it. Same language only. Returns (added, unresolved) and
    edits the groups' "negatives" in place."""
    keyed = [(g, [(_phrase_key(k), k) for k in g["keywords"]]) for g in groups]
    added, unresolved = [], []
    for gb, kb_list in keyed:
        for kb, kb_text in kb_list:
            for ga, ka_list in keyed:
                if ga is gb or ga.get("language") != gb.get("language") \
                        or ga.get("match_type", "phrase") != "phrase":
                    continue
                if not any(_contains(kb, ka) for ka, _ in ka_list):
                    continue
                neg_keys = [_phrase_key(n) for n in ga["negatives"]]
                if any(_contains(kb, nk) for nk in neg_keys):
                    continue
                if any(_contains(ka, kb) for ka, _ in ka_list):
                    unresolved.append((ga["name"], gb["name"], kb_text))
                    continue
                ga["negatives"].append(kb_text)
                added.append((ga["name"], gb["name"], kb_text))
    return added, unresolved


def _phrase_key(kw):
    """A keyword as Google's phrase match reads it: our normalised words,
    plurals folded (close variants). Arabic is compared LIGHTLY — diacritics
    and alef forms only. Our matching stem folds "الغسالة" and "غسالات"
    together, but nothing says Google's phrase match does, and run 2476776a
    would have dropped the head term "تصليح غسالات" (210) for "تصليح الغسالة"."""
    if is_arabic(kw):
        return [re.sub("[أإآ]", "ا", _AR_DIAC.sub("", w)).replace("ى", "ي")
                for w in _raw_toks(kw)]
    return _singular(" ".join(toks(kw))).split()


def _contains(longer, shorter):
    n = len(shorter)
    return 0 < n <= len(longer) and any(longer[i:i + n] == shorter
                                        for i in range(len(longer) - n + 1))


def select_bid_rows(rows, exact=False):
    """The keywords an ad group actually bids on, out of all its rows.

    A keyword whose words contain a chosen keyword's words, contiguous and in
    order, is reached by that one's PHRASE match and is not bid on twice.
    Pass 1 walks SHORTEST first, so the covering term ("washer repair") is
    chosen before what it covers ("clothes washer repair"), and keeps every
    uncovered keyword with MIN_BID_VOLUME+ searches. Pass 2 tops a group up
    to MIN_KEYWORDS_PER_GROUP with its highest-volume uncovered rows — an
    Arabic group whose Planner rows are all "10" still gets its head terms.
    Exact-match groups (the symptom test) skip containment: an exact keyword
    reaches nothing but itself."""
    def _covered(k, keys):
        return not exact and any(_contains(k, c) for c in keys)

    keyed = [(_phrase_key(r["keyword"]), r) for r in rows]
    chosen, keys = [], []
    for k, r in sorted(keyed, key=lambda x: (len(x[0]), -x[1]["avg_monthly_searches"],
                                             x[1]["keyword"])):
        if r["avg_monthly_searches"] >= MIN_BID_VOLUME and not _covered(k, keys):
            chosen.append(r)
            keys.append(k)
    if len(chosen) < MIN_KEYWORDS_PER_GROUP:
        for k, r in sorted(keyed, key=lambda x: (-x[1]["avg_monthly_searches"], len(x[0]),
                                                 x[1]["keyword"])):
            if len(chosen) >= MIN_KEYWORDS_PER_GROUP:
                break
            if r in chosen or _covered(k, keys):
                continue
            # a short keyword added here may cover one chosen before it
            chosen = [c for c, ck in zip(chosen, keys) if not (not exact and _contains(ck, k))]
            keys = [ck for ck in keys if not (not exact and _contains(ck, k))]
            chosen.append(r)
            keys.append(k)
    return chosen, keys


# ─────────────────────────────────────────────────────────────────────────
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    seeds = [s.strip() for s in os.environ.get("SEED_KEYWORDS", "").split(",") if s.strip()]
    if not seeds and not os.environ.get("SERVICES_JSON"):
        print("⚠️ No SEED_KEYWORDS — VTSA skipped, Stage 3 runs in legacy mode.")
        return
    with open(IN_FILE, encoding="utf-8") as f:
        data = json.load(f)
    rows = data["keywords"]
    services = build_services(seeds)
    _build_normaliser(services)
    register_other_services(services)
    _areas, _wrong = geo_context()
    if _areas:
        _GEO_AREAS[:] = list(dict.fromkeys(_areas + [a.strip().lower() for a in
                                                     os.environ.get("GEO_AREAS", "").split(",")
                                                     if a.strip()]))
    # the client's own service areas (GEO_AREAS / advanced.service_areas) are
    # never a wrong location, even when the geo data calls them another town
    _towns = wrong_city_names([r["keyword"] for r in rows], services, list(_GEO_AREAS) + _areas)
    _wrong = _wrong + _towns
    if _wrong:
        WRONG_LOCS.extend(w for w in dict.fromkeys(_wrong + [norm_phrase(x) for x in _wrong])
                          if w and w not in WRONG_LOCS)
    print(f"   🗺️ Geo: {len(_areas)} area(s) in the target city, {len(_wrong) - len(_towns)} "
          f"other province(s)/state(s) and {len(_towns)} other town(s) found in the data "
          f"treated as wrong locations" + (f": {', '.join(_towns[:12])}" if _towns else "")
          + ("" if _areas or _wrong else " (lookup off/failed — built-in lists)"))
    single = len(services) == 1
    print(f"🧭 VTSA: {len(services)} service(s): " + ", ".join(s["name"] for s in services))

    per_service = defaultdict(list)
    excluded = []
    for r in rows:
        for raw in _raw_toks(r["keyword"]):
            if is_arabic(raw):
                SURFACE[_ar_norm(raw)].add(raw)
    langs_with_service = {s["lang"] for s in services}
    for r in rows:
        i = assign_service(r["keyword"], services)
        if i is None:
            _l = "ar" if is_arabic(r["keyword"]) else "en"
            excluded.append({"id": r["id"], "keyword": r["keyword"],
                             "why": ("matches no service" if _l in langs_with_service else
                                     f"language '{_l}' has no seed — add a seed in that language")})
            continue
        why = junk_reason(r["keyword"])
        if why and SYMPTOM_TEST and why.startswith("symptom only"):
            r["_layer"], r["_hits"] = "symptom", []
            per_service[i].append(r)
            continue
        if why:
            excluded.append({"id": r["id"], "keyword": r["keyword"], "why": why,
                             "service": services[i]["name"]})
            continue
        if r.get("intent") in ("question", "informational") and \
                not urgent_hits(" ".join(toks(r["keyword"]))):
            excluded.append({"id": r["id"], "keyword": r["keyword"], "why": "informational (SEO)"})
            continue
        r["_layer"], r["_hits"] = layer_of(r["keyword"], services[i])
        per_service[i].append(r)

    # UMBRELLA-SEED GUARD. One broad seed ("handyman dubai") has one alias,
    # so "tv mounting", "curtain installation", "furniture assembly" match no
    # service and would silently vanish. When the unmatched keywords that DO
    # carry service intent outweigh half of what matched, the seeds do not
    # describe this business well enough for a formula. The run STOPS here
    # (NEEDS_SERVICE_MAP) instead of handing the grouping back to the model:
    # that legacy path is exactly what produced 4 groups for 7 services.
    matched_vol = sum(real_volume(rs) for rs in per_service.values())
    unmatched = [r for r in rows if r["id"] in {e["id"] for e in excluded
                                                 if e["why"] == "matches no service"}
                 and set(toks(r["keyword"])) & HIRE_WORDS
                 and not junk_reason(r["keyword"])]
    unmatched_vol = real_volume(unmatched)
    if unmatched_vol > 0.5 * max(matched_vol, 1):
        top = sorted(unmatched, key=lambda r: -r["avg_monthly_searches"])[:8]
        print(f"::error::NEEDS_SERVICE_MAP — {unmatched_vol} searches with service intent match "
              f"none of the seeds (vs {matched_vol} matched). Give one seed per sub-service, "
              f"or advanced.services_json "
              f'[{{"name": "Drain Unblocking", "aliases": ["drain", "blocked drain"]}}, ...]. '
              f"Examples: " + "; ".join(r["keyword"] for r in top))
        with open(OUT_PLAN, "w", encoding="utf-8") as f:
            json.dump({"version": "vtsa-2", "needs_service_map": True,
                       "matched_volume": matched_vol, "unmatched_volume": unmatched_vol,
                       "unmatched_examples": [r["keyword"] for r in top]}, f, indent=1)
        sys.exit(2)

    service_plans = []
    # symptom tests are research volume, not demand for the service — they
    # never count toward a service's tier or its share of the budget
    campaign_volume = sum(real_volume([r for r in rs if r["_layer"] != "symptom"])
                          for rs in per_service.values())
    for i, svc in sorted(enumerate(services), key=lambda x: x[1].get("lang") == "ar"):
        rs = per_service.get(i, [])
        if not rs:
            print(f"   ⚠️ '{svc['name']}': 0 relevant keywords — no ad group (check the seed)")
            continue
        service_plans.append(plan_service(svc, rs, single, campaign_volume))
    budget_guard(service_plans, [r for rs in per_service.values() for r in rs])
    # symptom queries that did not get a test group go back to the page FAQ
    for p in service_plans:
        for r in p.pop("symptom_to_faq", []):
            excluded.append({"id": r["id"], "keyword": r["keyword"], "service": p["service"],
                             "why": "symptom only (DIY/info - goes to page FAQ)"})
    silo_negatives(service_plans, services)
    _city = os.environ.get("TARGET_LOCATION", "").split(",")[0].strip()
    for p in service_plans:
        svc = next(s for s in services if s["name"] == p["service"])
        p["catchers"] = silo_catchers(p, svc)
        _real = {tuple(sorted(set(toks(r["keyword"])))) for rs in p["groups"].values() for r in rs}
        for _l in list(p["catchers"]):
            _kept, _seen = [], set()
            for c in p["catchers"][_l]:
                sig = tuple(sorted(set(toks(c))))
                if sig not in _real and sig not in _seen:
                    _seen.add(sig); _kept.append(c)
            p["catchers"][_l] = _kept
        # Intent templates -> routed to the layer that owns them. A template
        # already present as a real keyword (same words, any order) is skipped.
        have = {tuple(sorted(set(toks(r["keyword"])))) for rs in p["groups"].values() for r in rs}
        have |= {tuple(sorted(set(toks(c)))) for cs in p["catchers"].values() for c in cs}
        # Small services get few templates: Google marks a keyword nobody
        # searches as "low search volume" and it never serves anyway.
        _cap = max(6, min(24, p["volume"] // 60))
        _added = 0
        for t in intent_templates(p, svc, _city):
            if _added >= _cap:
                break
            sig = tuple(sorted(set(toks(t))))
            if sig in have or junk_reason(t):
                continue
            have.add(sig)
            layer, _ = layer_of(t, svc)
            target = layer if layer in p["groups"] else "core"
            p["catchers"].setdefault(target, []).append(t)
            _added += 1

    loc_label = os.environ.get("TARGET_LOCATION", "").strip() or ""
    by_id_vol = {r["id"]: r["avg_monthly_searches"] for r in rows}
    plan_groups, pages, kept_ids = [], [], set()
    _bid_n = [0, 0]      # bid keywords, all rows
    svc_by_name = {s["name"]: s for s in services}
    for p in service_plans:
        svc = svc_by_name[p["service"]]
        # City suffix, matching the live Mode 1 URLs (/washing-machine-repair-dubai/)
        _city = (loc_label.split(",")[0].strip() if loc_label else "")
        _disp = svc.get("display", p["service"])
        if svc.get("lang") == "ar":
            # Same clean English slug as the English page; the builder puts
            # the Arabic one under /ar/ (lang_url_prefix). Transliteration
            # only when the trade has no English twin.
            _v = service_verb(svc)
            _eh = svc.get("eng_head") or ""
            _twin = next((pp for pp in pages if pp.get("language") == "en"
                          and pp.get("_fam_key") == svc.get("fam_key")), None)
            page_slug = (_twin["url_slug"] if _twin else
                         slug(f"{_eh} {EN_VERB.get(_v, EN_VERB.get(norm_phrase(_v), 'repair'))} {_city}")
                         if _eh else slug(_translit(f"{_disp} {_city}")))
        else:
            page_slug = slug(f"{_disp} {_city}")
        names = []
        for l in LAYER_PRECEDENCE:
            rs = p["groups"].get(l)
            if not rs:
                continue
            _lab = LAYER_LABEL_AR if svc.get("lang") == "ar" else LAYER_LABEL
            name = _lab[l].format(svc=p["service"], disp=svc.get("display", p["service"]))[:60]
            names.append(name)
            bid_rows, bid_keys = select_bid_rows(rs, exact=LAYER_MATCH.get(l) == "exact")
            kept_ids |= {r["id"] for r in bid_rows}
            # a catcher or template the group's own phrase keywords already
            # reach is a duplicate bid, not a new home for anything
            _catch = [c for c in p["catchers"].get(l, [])
                      if not any(_contains(_phrase_key(c), k) for k in bid_keys)]
            _bid_n[0] += len(bid_rows)
            _bid_n[1] += len(rs)
            plan_groups.append({
                "name": name,
                "service": p["service"],
                "layer": l,
                "keyword_ids": [r["id"] for r in bid_rows],
                # every row the layer owns — demand, the page's keyword map
                "all_keyword_ids": [r["id"] for r in sorted(rs, key=lambda r: -r["avg_monthly_searches"])],
                # Rows the bid list does NOT reach: below the floor and not
                # inside any chosen phrase keyword. Stage 3's model picks the
                # buyer ones among them (rescue); the rest stay page-only.
                "rescue_candidate_ids": [r["id"] for r in sorted(
                    (r for r in rs if r not in bid_rows
                     and not any(_contains(_phrase_key(r["keyword"]), k) for k in bid_keys)),
                    key=lambda r: (-r["avg_monthly_searches"], len(r["keyword"])))][:RESCUE_POOL],
                "volume": real_volume(rs),
                "negative_keywords": p["negatives"][l],
                # positive phrase keywords (volume unknown) that give every
                # token negated elsewhere a home in THIS group
                "silo_catchers": _catch,
                "copy_rules": (["never say authorized/official/genuine service centre — "
                                "independent all-brand repair only (trademark + misleading-claims policy)"]
                               if l == "brand" else []),
                "bid_multiplier": (LAYER_BID[l] if l == "symptom" or p["volume"] >= 300
                                   else 0.9),
                "match_type": LAYER_MATCH.get(l, "phrase"),
                "landing_anchor": LAYER_ANCHOR[l],
                "language": svc.get("lang", "en"),
                "url_slug": page_slug,
            })
        pages.append({
            "page_name": _disp,
            "url_slug": page_slug,
            "language": svc.get("lang", "en"),
            "_fam_key": svc.get("fam_key"),
            "service_name": _disp,
            "ad_groups_covered": names,
            "keyword_map": keyword_map(p, svc, loc_label, symptoms=[
                e["keyword"] for e in sorted(
                    (e for e in excluded if e.get("service") == svc["name"]
                     and e["why"].startswith("symptom only")),
                    key=lambda e: -by_id_vol.get(e["id"], 0))][:10]),
        })
        print(f"   📦 {p['service']:<22} V={p['volume']:>6}  slots={p['slots_allowed']}  "
              f"groups={len(names)}  split={p['split_layers'] or '-'}  "
              f"folded={p['folded_into_core'] or '-'}")

    print(f"   🎯 Bid keywords: {_bid_n[0]} of {_bid_n[1]} relevant rows — the rest are reached "
          f"by a shorter phrase keyword or have < {MIN_BID_VOLUME:g} searches (min "
          f"{MIN_KEYWORDS_PER_GROUP}/group); all of them stay in the page keyword maps")
    for r in rows:
        r["kept_for_ai"] = r["id"] in kept_ids
        r.pop("_layer", None)
        r.pop("_hits", None)
    with open(IN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)

    for pg in pages:
        pg.pop("_fam_key", None)
    plan = {
        "version": "vtsa-2",
        "rule": (f"slots = clamp(ceil(V/{TIER_STEP}), 1, {MAX_SLOTS_SINGLE if single else MAX_SLOTS}); "
                 f"precedence {'emergency>' if OPEN_24_7 else ''}brand>problem>core; a layer "
                 f"splits at >= {MIN_LAYER_CLICKS:g} expected clicks/month = min(30.4 x budget "
                 f"x share / CPC, volume x {ASSUMED_IS:g} IS x {ASSUMED_CTR:g} CTR)"
                 + (f"; symptom test groups exact @ {SYMPTOM_BID:g}x" if SYMPTOM_TEST else "")),
        "settings": {"open_24_7": OPEN_24_7, "symptom_test": SYMPTOM_TEST,
                     "symptom_bid": SYMPTOM_BID, "min_layer_clicks": MIN_LAYER_CLICKS,
                     "min_bid_volume": MIN_BID_VOLUME,
                     "min_keywords_per_group": MIN_KEYWORDS_PER_GROUP,
                     "bid_keywords": _bid_n[0], "relevant_rows": _bid_n[1],
                     "assumed_is": ASSUMED_IS, "assumed_ctr": ASSUMED_CTR,
                     "daily_budget": _env_float("DAILY_BUDGET", 0),
                     "avg_cpc": round(avg_cpc([r for r in rows if r.get("kept_for_ai")]), 2)},
        "volume_basis": VOLUME_BASIS["value"],
        "classifier": classifier_snapshot(),
        "single_service": single,
        "services": [{"name": s["name"], "display": s.get("display", s["name"]),
                      "lang": s.get("lang", "en"), "aliases": s["aliases"],
                      "neg_heads": s.get("neg_heads", []), "seeds": s["seeds"]} for s in services],
        "service_summary": [{k: v for k, v in p.items() if k not in ("groups", "negatives")}
                            for p in service_plans],
        "ad_groups": plan_groups,
        "landing_pages": pages,
        "excluded": excluded,
        "campaign_negatives": CAMPAIGN_NEGATIVES + [w for w in WRONG_LOCS if " " in w or len(w) > 3],
    }
    with open(OUT_PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    print(f"✅ {OUT_PLAN}: {len(plan_groups)} ad groups, {len(pages)} landing pages, "
          f"{len(kept_ids)} keywords kept, {len(excluded)} excluded")
    from collections import Counter
    top_why = Counter(e["why"].split(":")[0] for e in excluded).most_common(6)
    print("   Excluded by reason: " + ", ".join(f"{w}={n}" for w, n in top_why))


if __name__ == "__main__":
    main()
