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
                   PROBLEM  > BRAND  > URGENT  > CORE
                ("samsung washer not draining" is a PROBLEM query first)
  5. TIER       slots per service from its own relevant volume V:
                   slots = clamp(ceil(V / 1000), 1, 4)
                   (V<=1000 ->1, <=2000 ->2, <=3000 ->3, >3000 ->4)
                Slots beyond CORE go to the BIGGEST viable layers first.
                A layer is viable only with >= MIN_LAYER_VOL searches and
                >= MIN_LAYER_KWS keywords — a group with no traffic never
                learns anything. Unviable layers fold back into CORE.
                Never padded: unused slots stay unused.
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
  MIN_LAYER_VOL     default 150 ; MIN_LAYER_KWS default 3
  DAILY_BUDGET, AVG_CPC   optional budget guard (see budget_guard)
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
MIN_LAYER_VOL = int(os.environ.get("MIN_LAYER_VOL", "150") or 150)
MIN_LAYER_KWS = int(os.environ.get("MIN_LAYER_KWS", "3") or 3)
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip().lower()

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

JUNK_TOKENS = {
    # product shopping
    "buy", "sale", "sell", "selling", "shopping", "showroom", "deal", "deals",
    "discount", "installment", "installments", "emi", "specs", "specification",
    "specifications", "dimensions", "size", "kg", "inch", "inches", "litre",
    "liter", "review", "reviews", "vs", "versus", "compare", "comparison",
    "second", "used", "secondhand", "olx", "dubizzle", "noon", "amazon",
    "carrefour", "sharaf", "lulu", "emax", "jumbo", "ikea", "danube",
    "rent", "rental", "rentals", "lease",
    # jobs / training
    "job", "jobs", "vacancy", "vacancies", "salary", "hiring", "career",
    "careers", "course", "courses", "training", "institute", "learn",
    "learning", "certificate", "certification", "cv",
    # DIY / info
    "diy", "manual", "manuals", "pdf", "diagram", "youtube", "video", "videos",
    "tutorial", "wiring", "meaning", "wikipedia", "reset", "myself",
    # parts retail
    "spare", "spares", "parts", "wholesale", "supplier", "suppliers",
    "trading", "llc",
    # free
    "free",
    # Arabic
    "شراء", "بيع", "للبيع", "مستعمل", "مستعملة", "وظائف", "وظيفة", "راتب", "دورة",
    "كورس", "قطع", "غيار", "يوتيوب", "كتالوج", "عروض", "تخفيضات",
}
JUNK_TOKENS |= {t.strip().lower() for t in os.environ.get("EXTRA_JUNK", "").split(",") if t.strip()}
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
    if t in _CANON or len(t) < 5 or not t.isalpha():
        return t
    cap = 2 if len(t) >= 9 else 1
    best, bd = None, cap + 1
    for w in _CANON:
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
HIRE_SIGNALS = SERVICE_VERBS | {"near", "nearby", "emergency", "urgent", "company",
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
    has_verb = bool(tset & SERVICE_VERBS)
    for loc in WRONG_LOCS:
        if has_phrase(text, loc):
            return f"wrong location: {loc}"
    if text.startswith(DIY_STARTS):
        return "diy/info question"
    hit = tset & JUNK_TOKENS
    # "service center" queries are NOT junk even with "shop"-like words
    if hit:
        # "used" inside "used to" etc. is rare in this data; accept the risk.
        return f"non-service intent: {sorted(hit)[0]}"
    if (tset & PRICE_TOKENS) and not has_verb:
        return "product price (no service word)"
    if symptom_only(text):
        return "symptom only (DIY/info - goes to page FAQ)"
    if not has_verb and not (tset & HARD_FAULTS) and not (tset & URGENT_TOKENS) \
            and not any(has_phrase(text, p) for p in _URGENT_PHRASES):
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


def problem_hits(text, service_aliases):
    tset = set(text.split())
    alias_toks = {w for a in service_aliases for w in a.split()}
    hits = {t for t in tset if (t in PROBLEM_TOKENS or _ERROR_CODE.match(t))
            and t not in alias_toks}
    # "gas refill" / "drain cleaning" are services, not faults — a part word
    # next to a service verb with no negation stays CORE.
    neg = {"not", "wont", "won't", "doesnt", "doesn't", "dont", "don't", "cant",
           "stopped", "stop", "لا", "لايعمل"}
    hits |= (tset & HARD_FAULTS)
    fault_words = hits & ({"leak", "leaking", "leaks", "noise", "noisy", "loud", "error",
                           "code", "broken", "problem", "problems", "issue", "issues",
                           "fault", "faulty", "smell", "smells", "smelly", "vibrating",
                           "vibration", "shaking", "overheating", "tripping", "trips",
                           "stuck", "jammed", "blinking", "flashing", "beeping",
                           "burning", "sparking", "dead", "dripping", "blocked",
                           "clogged", "frozen", "icing", "sweating", "humming",
                           "clicking", "عطل", "اعطال", "أعطال", "تسريب", "صوت"} | neg)
    parts = hits - fault_words
    if fault_words or any(_ERROR_CODE.match(t) for t in hits):
        return sorted(hits)
    # part-only queries ("washing machine motor repair", "fridge compressor
    # replacement") are diagnosed faults -> PROBLEM; generic service phrases
    # like "cooling", "power", "door", "gas" alone are not.
    strong_parts = parts & {"compressor", "motor", "pcb", "board", "pump", "thermostat",
                            "bearing", "bearings", "belt", "drum", "gasket", "seal",
                            "element", "backlight", "panel", "screen", "capacitor",
                            "valve", "timer", "sensor", "hinge", "coil", "inverter",
                            "relay", "hose", "lock", "ضاغط", "كمبروسر"}
    return sorted(strong_parts)


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
    tset = set(text.split())
    hits = [p for p in _URGENT_PHRASES if has_phrase(text, p)]
    single = tset & (URGENT_TOKENS - {"me", "same", "open", "home", "who", "where", "call"})
    return sorted(set(hits) | single)


def layer_of(kw, service):
    text = " ".join(toks(kw))
    ph = problem_hits(text, service["aliases"])
    if ph:
        return "problem", ph
    b = brands_in(text)
    if b:
        return "brand", b
    u = urgent_hits(text)
    if u:
        return "urgent", u
    return "core", []


def _norm_set(sset):
    return set(sset) | {norm_phrase(x) for x in sset if norm_phrase(x)}


for _name in ("ACTION_WORDS", "SERVICE_VERBS", "BRANDS", "PROBLEM_TOKENS", "URGENT_TOKENS",
              "JUNK_TOKENS", "PRICE_TOKENS", "HARD_FAULTS", "HIRE_SIGNALS"):
    globals()[_name] = _norm_set(globals()[_name])
_URGENT_PHRASES = list(dict.fromkeys(_URGENT_PHRASES + [norm_phrase(x) for x in _URGENT_PHRASES]))
DIY_STARTS = tuple(dict.fromkeys(DIY_STARTS + tuple(norm_phrase(x) + " " for x in DIY_STARTS)))
WRONG_LOCS = list(dict.fromkeys(WRONG_LOCS + [norm_phrase(x) for x in WRONG_LOCS]))


LAYER_PRECEDENCE = ["problem", "brand", "urgent", "core"]
LAYER_LABEL = {
    "core": "{disp}",
    "brand": "{disp} - Brands",
    "problem": "{svc} Problems & Parts",
    "urgent": "{disp} - Emergency & Near Me",
}
LAYER_LABEL_AR = {
    "core": "{disp}",
    "brand": "{disp} - ماركات",
    "problem": "{disp} - أعطال",
    "urgent": "{disp} - طوارئ وقريب",
}
LAYER_ANCHOR = {"core": "services", "brand": "brands", "problem": "problems", "urgent": "emergency"}
LAYER_BID = {"core": 1.0, "brand": 1.0, "problem": 1.15, "urgent": 1.2}


# ─────────────────────────────────────────────────────────────────────────
# 5. Tiering
# ─────────────────────────────────────────────────────────────────────────
def slots_for(volume, single_service):
    cap = MAX_SLOTS_SINGLE if single_service else MAX_SLOTS
    return max(1, min(cap, math.ceil(volume / TIER_STEP) if volume > 0 else 1))


def real_volume(rows):
    """Sum of searches with Planner close-variant clusters counted ONCE.

    The Planner reports one shared number for a whole variant cluster:
    "washing machine repair", "fix washing machine", "laundry machine repair",
    "washer fixer" all came back at 6,600 in the Sep 2026 Dubai run — the
    naive sum said 55,120 searches for a service with ~9,000. Rows sharing
    volume + competition index + bid range are one cluster. Small rows
    (<100) are left alone: equal 10s and 20s are common and genuinely
    different searches."""
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


def plan_service(svc, rows, single_service):
    V = real_volume(rows)
    slots = slots_for(V, single_service)
    by_layer = defaultdict(list)
    for r in rows:
        by_layer[r["_layer"]].append(r)
    layer_vol = {l: real_volume(rs) for l, rs in by_layer.items()}

    min_vol = max(MIN_LAYER_VOL, int(0.08 * V))
    # Viable = enough traffic AND enough keywords to learn from — except when
    # the traffic alone is 3x the floor: "fridge repair near me" at 1,900 is a
    # real layer even with only two phrasings of it.
    viable = [l for l in ("brand", "problem", "urgent")
              if layer_vol.get(l, 0) >= min_vol
              and (len(by_layer.get(l, [])) >= MIN_LAYER_KWS or layer_vol.get(l, 0) >= 3 * min_vol)]
    # Split where the AD COPY changes most. Brand and problem queries need
    # their own headlines ("Samsung Washer Repair", "Washer Not Spinning?");
    # near-me/emergency queries read almost the same as core copy plus an
    # urgency line, so they only get their own group as the LAST slot.
    candidates = sorted((l for l in viable if l != "urgent"), key=lambda l: -layer_vol[l])
    if "urgent" in viable:
        candidates.append("urgent")
    split = candidates[: max(0, slots - 1)]
    folded = [l for l in ("brand", "problem", "urgent") if by_layer.get(l) and l not in split]

    groups = {"core": list(by_layer.get("core", []))}
    for l in folded:
        groups["core"] += by_layer[l]
    for l in split:
        groups[l] = by_layer[l]
    if not groups["core"]:
        # every keyword was brand/problem/urgent: the biggest split layer
        # becomes the core so the service still has its generic group
        biggest = split.pop(0)
        groups["core"] = groups.pop(biggest)

    return {
        "service": svc["name"],
        "volume": V,
        "slots_allowed": slots,
        "layer_volume": {l: layer_vol.get(l, 0) for l in LAYER_PRECEDENCE},
        "split_layers": split,
        "folded_into_core": folded,
        "groups": groups,
    }


def budget_guard(service_plans):
    """Optional: fewer groups when the budget cannot feed them.
    Each ad group needs ~3 clicks/day to learn anything. When
    DAILY_BUDGET / AVG_CPC < 3 x groups, fold the smallest split layers
    (smallest service first) back into their core until it fits."""
    try:
        budget = float(os.environ.get("DAILY_BUDGET", "") or 0)
        cpc = float(os.environ.get("AVG_CPC", "") or 0)
    except ValueError:
        return
    if budget <= 0 or cpc <= 0:
        return
    max_groups = max(len(service_plans), int(budget / cpc / 3))
    total = sum(len(p["groups"]) for p in service_plans)
    while total > max_groups:
        cands = [(p["groups"][l] and sum(r["avg_monthly_searches"] for r in p["groups"][l]), p, l)
                 for p in service_plans for l in p["split_layers"]]
        if not cands:
            break
        _, p, l = min(cands, key=lambda x: x[0])
        p["groups"]["core"] += p["groups"].pop(l)
        p["split_layers"].remove(l)
        p["folded_into_core"].append(l)
        total -= 1
        print(f"   💸 Budget guard: folded '{p['service']} / {l}' into core "
              f"(budget supports ~{max_groups} groups)")


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
        elif layer == "urgent":
            out |= set(urgent_hits(text))
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
                else:  # urgent — always with the service word, never "fridge now"
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
    core = sorted(p["groups"].get("core", []), key=lambda r: -r["avg_monthly_searches"])
    # primary: highest-volume CORE keyword that contains the service head and
    # a service verb — this is the H1 / title term
    primary = next((r["keyword"] for r in core
                    if set(toks(r["keyword"])) & SERVICE_VERBS), core[0]["keyword"] if core else svc["name"].lower())
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
    urgent = [r["keyword"] for r in all_rows if r["_layer"] == "urgent"][:10]
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
        "voice_questions": questions,
        "placement": {
            "title": f"{title(primary_loc)} | Same-Day, All Brands"[:60],
            "meta_description_must_include": [primary_loc] + secondary[:1],
            "h1": title(primary_loc),
            "h2_sections": [
                {"layer": l, "anchor": LAYER_ANCHOR[l],
                 "must_include": (brands[:3] if l == "brand" else
                                  problems[:3] if l == "problem" else
                                  urgent[:3] if l == "urgent" else secondary[:3])}
                for l in LAYER_PRECEDENCE if p["groups"].get(l)
            ] + ([{"layer": "brand", "anchor": "brands", "must_include": brands[:3]}]
                 if brands and "brand" not in p["groups"] else [])
              + ([{"layer": "problem", "anchor": "problems", "must_include": problems[:3]}]
                 if problems and "problem" not in p["groups"] else []),
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
    # describe this business well enough for a formula: fall back to the
    # legacy model grouping for this run and say so, instead of shipping a
    # campaign that covers a fraction of the demand.
    matched_vol = sum(real_volume(rs) for rs in per_service.values())
    unmatched = [r for r in rows if r["id"] in {e["id"] for e in excluded
                                                 if e["why"] == "matches no service"}
                 and set(toks(r["keyword"])) & SERVICE_VERBS
                 and not junk_reason(r["keyword"])]
    unmatched_vol = real_volume(unmatched)
    if unmatched_vol > 0.5 * max(matched_vol, 1):
        top = sorted(unmatched, key=lambda r: -r["avg_monthly_searches"])[:8]
        print(f"⚠️ VTSA fallback: {unmatched_vol} searches with service intent match none of "
              f"the seeds (vs {matched_vol} matched). Give one seed per sub-service, "
              f"or SERVICES_JSON. Examples: " + "; ".join(r["keyword"] for r in top))
        with open(OUT_PLAN, "w", encoding="utf-8") as f:
            json.dump({"version": "vtsa-1", "fallback_legacy": True,
                       "matched_volume": matched_vol, "unmatched_volume": unmatched_vol,
                       "unmatched_examples": [r["keyword"] for r in top]}, f, indent=1)
        for r in rows:
            r.pop("_layer", None); r.pop("_hits", None)
        return

    service_plans = []
    for i, svc in sorted(enumerate(services), key=lambda x: x[1].get("lang") == "ar"):
        rs = per_service.get(i, [])
        if not rs:
            print(f"   ⚠️ '{svc['name']}': 0 relevant keywords — no ad group (check the seed)")
            continue
        service_plans.append(plan_service(svc, rs, single))
    budget_guard(service_plans)
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
            kept_ids |= {r["id"] for r in rs}
            plan_groups.append({
                "name": name,
                "service": p["service"],
                "layer": l,
                "keyword_ids": [r["id"] for r in sorted(rs, key=lambda r: -r["avg_monthly_searches"])],
                "volume": real_volume(rs),
                "negative_keywords": p["negatives"][l],
                # positive phrase keywords (volume unknown) that give every
                # token negated elsewhere a home in THIS group
                "silo_catchers": p["catchers"].get(l, []),
                "copy_rules": (["never say authorized/official/genuine service centre — "
                                "independent all-brand repair only (trademark + misleading-claims policy)"]
                               if l == "brand" else []),
                "bid_multiplier": LAYER_BID[l] if p["volume"] >= 300 else 0.9,
                "match_type": "phrase",
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

    for r in rows:
        r["kept_for_ai"] = r["id"] in kept_ids
        r.pop("_layer", None)
        r.pop("_hits", None)
    with open(IN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)

    for pg in pages:
        pg.pop("_fam_key", None)
    plan = {
        "version": "vtsa-1",
        "rule": f"slots = clamp(ceil(V/{TIER_STEP}), 1, {MAX_SLOTS_SINGLE if single else MAX_SLOTS}); "
                f"layer precedence problem>brand>urgent>core; layer viable at >= "
                f"max({MIN_LAYER_VOL}, 8% of V) searches and >= {MIN_LAYER_KWS} keywords",
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
