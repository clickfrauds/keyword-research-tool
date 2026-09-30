"""
negative_packs.py — campaign-level negative keywords, niche-aware.
------------------------------------------------------------------
Deterministic: the same niche always gets the same base list, whether or not
the Claude call in Stage 3.6 succeeds. Claude's niche words and the account's
own excluded keywords are ADDED on top by generate_ads_script.py, and all of
it goes through the bid-keyword collision filter there.

Three layers:
  UNIVERSAL   junk for ANY local service business: jobs/cv/salary, courses,
              manuals/pdf, DIY, second hand/used, marketplaces, suppliers.
  NICHE PACK  junk specific to the trade (appliance: "for sale", "specs",
              retail chains; auto: "car for sale", "insurance"; AC: "ac
              price", "window ac"...). Picked from the niche text + seeds.
  ALLOW       words that look like junk but are BUYERS in this niche. They
              are removed from every list, even the universal one:
                auto repair    -> "manual" (manual gearbox), "parts" fitting
                AC             -> "installation", "gas"
                appliance      -> "shop" ("tv repair shop near me" converts)
              "company" is never negated in any niche: "ac repair company
              dubai" is one of the best-converting phrasings there is.

BUSINESS_MODEL env overrides what counts as junk:
  service (default)  sells labour: parts/supplier/wholesale = junk
  parts              sells parts: "spare parts", "supplier" become allowed
  retail             sells units: "buy", "price", "sale" become allowed
  installer          "installation", "fitting", "supply and install" allowed
"""

import os
import re

UNIVERSAL = [
    # jobs / careers
    "job", "jobs", "vacancy", "vacancies", "hiring", "recruitment", "career",
    "careers", "salary", "salaries", "cv", "resume", "walk in interview",
    "internship", "apprenticeship", "visa", "part time",
    # education
    "course", "courses", "training", "institute", "academy", "certificate",
    "certification", "diploma", "learn", "learning", "classes",
    # manuals / info / DIY
    "manual", "manuals", "pdf", "user guide", "instructions", "diagram",
    "schematic", "datasheet", "specs", "specifications", "tutorial", "youtube",
    "video", "diy", "do it yourself", "how to", "wikipedia", "meaning",
    # second hand / marketplaces
    "second hand", "secondhand", "used", "pre owned", "refurbished", "scrap",
    "olx", "dubizzle", "facebook marketplace", "for sale", "sell my", "buy",
    # trade / supply chain
    "supplier", "suppliers", "wholesale", "wholesaler", "distributor",
    "manufacturer", "manufacturers", "trading", "trading llc", "importer",
    "exporter", "spare parts", "spares", "parts shop", "parts store",
    # free / fake intent
    "free", "download", "apk", "logo", "png", "wallpaper",
    # Arabic — same intents (jobs, courses, DIY, second hand, parts trade)
    "وظائف", "وظيفة", "مطلوب فني", "راتب", "دورة", "دورات", "كورس", "تعليم",
    "كيف", "طريقة", "يوتيوب", "كتالوج", "مستعمل", "مستعملة", "للبيع", "شراء",
    "قطع غيار", "جملة", "مورد", "مجانا",
]

PACKS = {
    "appliance": {
        "detect": ["appliance", "washing machine", "washer", "fridge", "refrigerator",
                   "dishwasher", "dryer", "oven", "cooker", "microwave", "wine chiller",
                   "tv repair", "led tv"],
        "block": ["buy", "sale", "offers", "deal", "deals", "discount", "installment",
                  "emi", "price in dubai", "price in uae", "dimensions", "size",
                  "capacity", "kg", "inch", "review", "reviews", "vs", "compare",
                  "best brand", "which brand", "showroom", "outlet", "warranty check",
                  "customer care number", "complaint number", "rental", "rent",
                  "carrefour", "sharaf dg", "lulu", "emax", "jumbo", "noon", "amazon",
                  "ikea", "danube", "plug in", "remote control", "app", "mini fridge",
                  "portable"],
        "allow": ["shop", "service center", "service centre", "company", "installation"],
    },
    "ac": {
        "detect": ["ac repair", "ac service", "air conditioner", "air conditioning",
                   "aircon", "hvac", "ac maintenance", "duct cleaning"],
        "block": ["buy", "sale", "window ac price", "split ac price", "ac price",
                  "tonnage", "btu", "inverter vs", "review", "reviews", "vs",
                  "showroom", "rent", "rental", "carrefour", "sharaf dg", "emax",
                  "portable ac", "car ac", "remote", "remote code", "error code list",
                  "wallpaper"],
        "allow": ["installation", "gas", "gas refill", "company", "maintenance contract",
                  "shop"],
    },
    "plumbing": {
        "detect": ["plumber", "plumbing", "drain", "blocked", "leak detection",
                   "water heater", "geyser", "toilet", "pipe"],
        "block": ["plumbing tools", "pipe price", "pipe sizes", "fittings price",
                  "pvc price", "sanitary ware", "sanitary shop", "bathroom accessories",
                  "tiles", "hardware store", "ace hardware", "dragon mart", "plumbing materials",
                  "plumbing supplies"],
        "allow": ["installation", "fitting", "company", "shop"],
    },
    "electrician": {
        "detect": ["electrician", "electrical", "wiring", "switch", "socket", "db board"],
        "block": ["electrical supplies", "electrical shop", "cable price", "wire price",
                  "switch price", "electrical materials", "dewa bill", "dewa pay",
                  "dewa complaint", "power cut", "load shedding", "electrician tools",
                  "multimeter"],
        "allow": ["installation", "wiring", "company", "maintenance"],
    },
    "auto": {
        "detect": ["car repair", "auto repair", "garage", "mechanic", "car service",
                   "workshop", "recovery", "towing", "battery", "tyre", "tire"],
        "block": ["car for sale", "used cars for sale", "used car price", "car price", "new car", "car rental",
                  "rent a car", "car insurance", "insurance", "rta test", "driving license",
                  "driving school", "registration", "renewal", "fine", "fines", "salik",
                  "car wash near me", "toy", "toys", "game", "games"],
        # "used" is a buyer here ("used car inspection") — the pack blocks
        # the junk phrasings instead
        "allow": ["manual", "parts", "spare parts", "workshop", "company", "shop",
                  "battery", "tyre", "used", "pre owned"],
    },
    "handyman": {
        "detect": ["handyman", "maintenance company", "home maintenance", "painter",
                   "painting", "carpenter", "carpentry", "furniture assembly", "tv mounting"],
        "block": ["paint price", "paint colors", "paint shop", "wood price", "plywood price",
                  "hardware store", "ace hardware", "dragon mart", "furniture for sale",
                  "furniture shop", "ikea"],
        "allow": ["installation", "fitting", "company", "shop", "assembly"],
    },
    "cleaning": {
        "detect": ["cleaning", "cleaner", "maid", "sofa cleaning", "deep cleaning",
                   "carpet cleaning", "pest control"],
        "block": ["cleaning products", "cleaning supplies", "detergent", "vacuum price",
                  "maid visa", "housemaid visa", "maid salary", "maid agency", "tadbeer",
                  "pesticide price", "spray price"],
        "allow": ["company", "services", "deep"],
    },
}

MODEL_ALLOW = {
    "service": [],
    "parts": ["buy", "spare parts", "spares", "parts shop", "parts store", "supplier",
              "suppliers", "wholesale", "distributor", "trading"],
    "retail": ["buy", "sale", "offers", "deal", "deals", "discount", "price in dubai",
               "price in uae", "showroom", "outlet", "installment", "emi", "for sale"],
    "installer": ["installation", "fitting", "supply and install", "supplier"],
}

NEVER_NEGATE = {"company", "companies", "service", "services", "repair", "near me",
                "dubai", "uae", "emergency", "technician"}


def _norm(s):
    return " ".join(re.findall(r"[^\W_]+", str(s).lower(), re.UNICODE))


def detect_packs(niche_text, seeds=()):
    text = " " + _norm(niche_text + " " + " ".join(seeds)) + " "
    found = [name for name, p in PACKS.items()
             if any((" " + _norm(d) + " ") in text for d in p["detect"])]
    return found


def build(niche_text, seeds=(), business_model=None):
    """-> (block_list, allow_list, packs_used). Pure; no API."""
    business_model = (business_model or os.environ.get("BUSINESS_MODEL", "service")
                      or "service").strip().lower()
    packs = detect_packs(niche_text, seeds)
    block = list(UNIVERSAL)
    allow = set(NEVER_NEGATE) | set(MODEL_ALLOW.get(business_model, []))
    for name in packs:
        block += PACKS[name]["block"]
        allow |= set(PACKS[name]["allow"])
    allow |= {a.strip().lower() for a in os.environ.get("NEGATIVE_ALLOW", "").split(",") if a.strip()}
    block += [b.strip().lower() for b in os.environ.get("EXTRA_JUNK", "").split(",") if b.strip()]
    allow_n = {_norm(a) for a in allow}

    def _sing(w):
        return w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w

    allow_sing = {" ".join(_sing(w) for w in a.split()) for a in allow_n}

    def allowed(term):
        # EQUALITY (plural-insensitive), not containment: a garage keeps
        # "manual" but still blocks "manual pdf"; an appliance shop that
        # allows "shop" still blocks "parts shop". Phrase collisions with
        # the real bid keywords are caught later by filter_forbidden().
        return " ".join(_sing(w) for w in _norm(term).split()) in allow_sing

    out, seen = [], set()
    for b in block:
        n = _norm(b)
        if n and n not in seen and not allowed(n):
            seen.add(n)
            out.append(n)
    return out, sorted(allow_n), packs
