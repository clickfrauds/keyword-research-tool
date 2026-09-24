"""Map Naseem's 853-service list onto the 30 LeadSmart campaigns his account
has been given (offers.ringba.com/leadsmart -> Manage Campaigns).

The campaign list is the authority. Not the coverage feed, which is only a
snapshot of where bids are live right now (NM Electrical shows 16 towns while
the Electrician campaign is Nationwide), and not a model's guess at grouping.

Patterns are regexes with explicit word boundaries: plain substrings put
"access control systems" and "central vac repair" into HVAC via " ac ".
"""
import json
import re
import sys

SRC = r"C:/Users/HP/Downloads/services_list.json"
OUT = r"C:/Users/HP/keyword-research-tool/data/leadsmart_campaigns.json"

# ---------------------------------------------------------------- campaigns
# key | offer title exactly as LeadSmart shows it | payout | status | local-SEO fit
CAMPAIGNS = [
    ("Plumbing",            "Plumbers - Plumbing - Nationwide",                      "call+cpl", "live",  True),
    ("Electrical",          "Electrician - Nationwide - Variable Rate",              "call",     "live",  True),
    ("HVAC",                "HVAC - Nationwide - Variable Rate",                     "call",     "apply", True),
    ("Roofing",             "Roofing - Nationwide",                                  "call+cpl", "apply", True),
    ("Pest Control",        "Pest Control - Nationwide - Variable Rate",             "call",     "apply", True),
    ("Appliance Repair",    "Appliance Repair",                                      "call",     "apply", True),
    ("Gutters",             "Gutters - Nationwide - Variable Rate",                  "call",     "apply", True),
    ("Tree Services",       "Tree Service - Variable Rate",                          "call",     "apply", True),
    ("Lawncare & Landscaping", "Lawn Care and Landscaping",                          "call",     "apply", True),
    ("Garage Door",         "Garage Door / Opener Repair - Nationwide",              "call",     "apply", True),
    ("Painting",            "Painting",                                              "call",     "apply", True),
    ("Windows",             "Windows $40/150 seconds  +  Windows CPL",               "call+cpl", "apply", True),
    ("Fencing",             "Fencing - Variable Rate",                               "call",     "apply", True),
    ("Carpet & Flooring",   "Carpet and Flooring Installation",                      "call",     "apply", True),
    ("Decking",             "Main Decking Variable Rate 1500+ zips",                 "cpl",      "apply", True),
    ("Siding",              "Siding Services - Up to $120",                          "cpl",      "apply", True),
    ("Foundation Repair",   "Foundation Repair - mainly cpl",                        "cpl",      "apply", True),
    ("Waterproofing",       "Waterproofing",                                         "cpl",      "apply", True),
    ("Bathroom & Kitchen Remodeling", "Bathroom Remodeling Variable Rate",           "cpl",      "apply", True),
    ("Water, Fire & Mold Restoration", "Water Damage, Fire Damage and Mold Remediation - Variable Rate", "cpl", "apply", True),
    ("Bio Hazard Cleanup",  "Bio Hazard Cleanup",                                    "cpl",      "apply", True),
    ("Solar",               "Solar Variable Rate",                                   "cpl",      "apply", True),
    ("Moving",              "Long and Short Distance Moving Variable Rate",          "call",     "apply", True),
    ("Dumpster & Porta Potty", "Dumpster and Porta Potty Raw Calls - $7.5/45",       "call",     "apply", True),
    ("Self Storage",        "Self Storage Nationwide",                               "call",     "apply", True),
    ("Walk In Tubs",        "Walk In Tubs $25/120 Seconds",                          "call",     "apply", True),
    ("Dentist",             "Dentist - SEO Only",                                    "call",     "apply", True),
    ("Garage Door (FB Marketplace)", "Facebook Marketplace Allowed Garage Door",     "call",     "apply", False),
    ("Airline Tickets",     "Airline Ticket Calls",                                  "call",     "apply", False),
]

# Which campaign the coverage feed carries ZIP payouts for, under which label.
FEED_NICHE = {
    "Plumbing": "Plumbing", "Electrical": "Electrical", "HVAC": "HVAC",
    "Roofing": "Roofing", "Pest Control": "Pest Control",
    "Appliance Repair": "Appliance", "Gutters": "Gutters",
    "Tree Services": "Tree Services", "Lawncare & Landscaping": "Landscaping",
    "Garage Door": "Garage Door", "Painting": "Painting", "Decking": "Deck",
    "Siding": "Siding", "Foundation Repair": "Foundation Repair",
    "Waterproofing": "Waterproofing",
    "Bathroom & Kitchen Remodeling": "Bathroom Remodeling",
    "Water, Fire & Mold Restoration": "Water Damage",
    "Bio Hazard Cleanup": "Biohazard", "Solar": "Solar",
}

# ------------------------------------------------------------------ excluded
# Checked before every rule: retail, cleaning-only trades, and anything no
# campaign on the list buys. The middle column is the let-through: a name that
# also carries a campaign's own word is not excluded, so "asphalt shingle
# roofing" stays Roofing and "pool fencing" stays Fencing while plain
# "asphalt paving" and "pool repair" still go.
EXCLUDE = [
    (r"\bsales\b|\bsupplies\b|\bkit\b", None, "retail, not a service call"),
    (r"\b(carpet|rug|house|window|upholstery|floor|grout|blind|drapery|pool|"
     r"chimney|exterior|green|tile)\s+(cleaning|cleaners|washing|washiing)\b",
     None, "cleaning trade - no campaign"),
    (r"\bmaid\b|\bhousekeep", None, "cleaning trade - no campaign"),
    (r"\b(auto|car|truck|vehicle|motorcycle|boat|bicycle|bike|rv|marine|tire|"
     r"brake|muffler|exhaust|transmission|collision|windshield|dash cam|"
     r"alloy wheel|trailer hitch|remote start|sunroof)\b", None, "automotive"),
    (r"\b(laptop|phone|computer|tv|electronic|copier|drone|camera|radio|"
     r"eyeglass|watch|clock|jewellery|jewelry|av installer|network|voip|"
     r"antenna|cable|surround sound|home audio|home theater|home automation)\b",
     None, "electronics / personal goods"),
    (r"\b(pool|spa)\b", r"\b(fenc|landscap|solar|plumb|leak|deck|heater)\b",
     "swimming pools - no campaign"),
    (r"\b(security|alarm|cctv|surveillance|access control|childproof)\b",
     None, "security systems - no campaign"),
    (r"\blocksmith\b", None, "locksmith - no campaign"),
    (r"\b(masonry|brick|stone|concrete|asphalt|paving|driveway|quikrete)\b",
     r"\b(roof|siding|foundation|floor|countertop|stain|shingle)\b",
     "masonry / paving - no campaign"),
    (r"\b(chimney|chimmney|fireplace)\b", None, "chimney & fireplace - no campaign"),
    (r"\b(blinds?|shutters?|shades?|drapes?|drapery|curtain|awning)\b",
     None, "window treatments - no campaign"),
    (r"\b(junk|debris)\s+removal\b|\bfurniture\b", None, "haul-away - no campaign"),
    (r"\bcustom\b",
     r"\b(kitchen|bathroom|cabinet|countertop|window|floor|vanit|shower|"
     r"door|rug)\b", "bespoke build, not a lead-gen service"),
    (r"\b(design|designers?|plans?|planning|drafting|rendering|staging|stagers|"
     r"appraisals?|surveying|engineering|architect|organiz|declutter|"
     r"downsizing|color consulting)\b",
     r"\b(kitchen|bathroom|landscape|landscaping|deck|sunroom|patio|garden)\b",
     "design / advisory only"),
    (r"\binspections?\b",
     r"\b(electrical|hvac|plumbing|roof|sewer|foundation|termite|pest)\b",
     "advisory only"),
    (r"\b(therapy|therapist|medicine|sculpting|cartilage|hair removal|"
     r"denture|denturist)\b", None, "medical"),
    (r"\b(lessons?|tutor|management|marketing|credit|notary|studio|coach|"
     r"embroidery|artwork|framing|blacksmith|welding|fabrication|"
     r"photograph|wedding|event planner|flower|real estate|"
     r"beautician|personal trainer|\bpet\b|\bdog\b|groomer|walker|sitter)\b",
     r"\b(pet|dog) door\b", "not a home service"),
    (r"\b(asbestos|radon|lead paint)\b", None, "abatement - no campaign"),
    (r"\b(elevator|sauna|trampoline|playhouse|treehouse|wine cellar|"
     r"storm shelter|tiny house|modular|prefab|multigenerational)\b",
     None, "speciality build - no campaign"),
    (r"\b(new home|home additions?|home extensions?|house framing|"
     r"general contracting|demolition|excavat|garage build|attic conversion|"
     r"green building|energy[- ]efficient|home efficiency|energy audit)",
     None, "new build - no campaign"),
    (r"\b(carpenters?|carpentry|millwork|wainscoting|trim work|crown molding|"
     r"quarter round|shelving|stairs?|acoustic ceiling|stretch ceiling|"
     r"soundproof|fireproof)\b", None, "carpentry - no campaign"),
    (r"\b(holiday|christmas)\b", None, "seasonal decor"),
    (r"\b(small engine|electric motor|mower|vacuum|sewing machine|lamp|"
     r"leather|boot|shoe|"
     r"upholstery|fire extinguisher|pat testing)\b", None, "equipment repair"),
    (r"\bgardens?\b", r"\b(design|landscap)\b", "hobby gardening"),
    (r"\b(shed|carport|garage storage|closet|art installation|wall stenciling|"
     r"wall upholstery|environmental services)\b", None, "no campaign covers it"),
]

# -------------------------------------------------------------------- rules
# First match wins, so the order is the priority order.
RULES = [
    ("Bio Hazard Cleanup", r"biohazard|bio hazard|crime scene|hoarding|"
                           r"trauma clean|unattended death|sewage (clean|remov)"),
    ("Water, Fire & Mold Restoration",
     r"\b(water|flood|fire|smoke|storm)\s+(damage|restoration|extraction|"
     r"mitigation|removal)|\bmou?ld\b|\bsoot\b|odor removal|"
     r"\b(disaster|sewage)\s+restoration\b"),
    ("Waterproofing", r"waterproof|french drain|sump pump|damp proof|"
                      r"vapor barrier|dehumidif|dry wells?|crawl space encapsulation"),
    ("Foundation Repair", r"foundation|slab ?jack|mud ?jack|pier and beam|"
                          r"house lifting|structural repair|underpinning|"
                          r"floor leveling|earthquake retrofit|crawl space repair"),
    ("Dentist", r"\bdentist|\bdental\b|orthodont|endodont|periodont|invisalign"),
    ("Walk In Tubs", r"walk[- ]in tub|hot tub|wheelchair ramp|grab bar|"
                     r"accessible bath"),
    ("Solar", r"\bsolar\b|photovoltaic"),
    ("Self Storage", r"self storage|storage (unit|facilit)|sports equipment storage"),
    ("Dumpster & Porta Potty", r"dumpster|porta potty|portable (toilet|restroom)|roll[- ]?off"),
    ("Moving", r"\bmov(ing|ers)\b|relocation|packing service|packers"),
    ("Pest Control",
     r"\bpest\b|exterminat|termite|bed ?bug|rodent|\bmice\b|\brats?\b|"
     r"cockroach|roach|ant control|wasp|bee removal|hornet|spider|flea|"
     r"\btick\b|mosquito|(wildlife|animal|bird|bat|snake) removal|squirrel|"
     r"raccoon|o?possum|fumigat"),
    ("Tree Services", r"\btrees?\b|arborist|stump|shrub|hedge|brush (removal|clearing)|"
                      r"land clearing|branch|wood chipping"),
    ("Lawncare & Landscaping",
     r"\blawn\b|landscap|\bsod\b|\bturf\b|irrigation|sprinkler|mowing|mulch|"
     r"hardscap|retaining wall|paver|\byard\b|weed|fertiliz|grading|xeriscap|"
     r"artificial grass|leaf removal|(snow|ice) removal|snow plow|"
     r"outdoor lighting|\bpond\b|planting|rototilling|living walls?"),
    ("Gutters", r"gutter|downspout|leaf guard|fascia|soffit"),
    ("Roofing", r"\broof|roofer|shingle|skylight|\beaves\b"),
    ("Siding", r"siding|stucco|cladding|exterior wall"),
    ("Windows", r"window|\bglass\b|glazier|glazing|egress|weather ?strip|"
                r"\b(exterior|storm|sliding|patio) door\b|mirror|"
                r"\bscreen (repair|install)"),
    ("Fencing", r"\bfenc(e|ing)\b|\bgate\b|privacy screen"),
    ("Decking", r"\bdeck(s|ing)?\b|pergola|gazebo|patio|porch|railing|balcony|"
                r"sunroom|screened[- ]in|\bdock\b|trellis"),
    ("Garage Door", r"garage door|garage opener|overhead door|roller door|garage spring"),
    ("Carpet & Flooring",
     r"carpet|floor(ing)?\b|hardwood|laminate floor|vinyl (plank|floor)|"
     r"linoleum|epoxy floor|sub ?floor|\brugs?\b|baseboard|floor (sanding|"
     r"refinish|polish|repair|install)"),
    ("Bathroom & Kitchen Remodeling",
     r"bathroom|bath remodel|kitchen|\bshower\b|bathtub|\bvanity\b|countertop|"
     r"cabinet|backsplash|tile (install|repair)|tiling|remodel|renovation|"
     r"wet room"),
    ("Painting", r"\bpaint|wallpaper|drywall|plaster|(pressure|power|soft) wash|"
                 r"stain(ing)?\b|popcorn ceiling|graffiti removal|wood finishing|"
                 r"wall texture"),
    ("Plumbing",
     r"plumb|\bdrain\b|sewer|water heater|tankless|faucet|toilet|"
     r"garbage disposal|water (line|main|softener|filtration|treatment|testing)|"
     r"\bpipes?\b|piping|\bleaks?\b|re-?pipe|backflow|\bwells?\b|septic|"
     r"gas (line|leak|pipe)|propane|hydro ?jet|rooter|\bsinks?\b|hose bib|"
     r"\bsump\b|water removal"),
    ("Electrical",
     r"electric|wiring|rewir|panel upgrade|breaker|outlet|switch install|"
     r"light(ing)? install|ceiling fan|generator|ev charger|surge protect|"
     r"gfci|low voltage|smoke detector|recessed light|smart (home|lighting)"),
    ("HVAC",
     r"\bhvac\b|\bac\b|air condition|furnace|heating|heat pump|boiler|"
     r"mini[- ]split|ductless|\bducts?\b|ductwork|thermostat|air quality|"
     r"air handler|evaporator|condenser|refrigerant|swamp cooler|"
     r"evaporative cool|radiant (floor )?heat|underfloor heating|"
     r"in floor heating|ventilation|exhaust fan|attic fan|insulation|"
     r"oil to gas|"
     r"humidifier|geothermal|range hood"),
    ("Appliance Repair",
     r"appliance|refrigerator|fridge|freezer|\bwasher\b|washing machine|"
     r"\bdryer\b|dishwasher|\boven\b|stove|range repair|microwave|"
     r"ice (maker|machine)|icemaker|cooktop|wine cooler"),
]


# The terms the /towns volume probe measures for a campaign. Not the whole
# service list -- that is alphabetical after the head terms, so "water heater
# repair" sits near the end while "faucet installation" comes near the front,
# and a ten-term probe would miss the money. These are the ten a homeowner
# actually types, head term first, chosen for demand rather than for spelling.
PROBE = {
    "Plumbing": ["plumbers", "emergency plumber", "drain cleaning",
                 "water heater repair", "water heater replacement",
                 "clogged drain", "sewer line repair", "leak detection",
                 "toilet repair", "burst pipe repair"],
    "Electrical": ["electricians", "emergency electrician", "electrical repair",
                   "electrical panel upgrade", "ceiling fan installation",
                   "outlet repair", "generator installation",
                   "ev charger installation", "house rewiring",
                   "lighting installation"],
    "Roofing": ["roofers", "roof repair", "roof replacement", "roof leak repair",
                "metal roof installation", "storm damage roof repair",
                "roof inspection", "shingle replacement", "flat roof repair",
                "emergency roof repair"],
    "HVAC": ["hvac", "ac repair", "air conditioning repair", "furnace repair",
             "ac installation", "heating repair", "ac replacement",
             "furnace installation", "emergency ac repair", "hvac maintenance"],
    "Pest Control": ["pest control", "exterminator", "termite treatment",
                     "bed bug treatment", "rodent control", "ant exterminator",
                     "cockroach exterminator", "mosquito control",
                     "wildlife removal", "termite inspection"],
    "Appliance Repair": ["appliance repair", "refrigerator repair",
                         "washer repair", "dryer repair", "dishwasher repair",
                         "oven repair", "stove repair", "freezer repair",
                         "ice maker repair", "washing machine repair"],
    "Gutters": ["gutters", "gutter cleaning", "gutter installation",
                "gutter repair", "gutter guards", "seamless gutters",
                "downspout repair", "gutter replacement"],
    "Tree Services": ["tree service", "tree removal", "tree trimming",
                      "stump removal", "stump grinding", "emergency tree removal",
                      "tree cutting", "arborist"],
    "Lawncare & Landscaping": ["landscaping", "lawn care", "lawn mowing",
                               "sod installation", "sprinkler repair",
                               "landscape design", "yard cleanup",
                               "irrigation repair", "tree and shrub care"],
    "Garage Door": ["garage door repair", "garage door installation",
                    "garage door spring repair", "garage door opener repair",
                    "garage door replacement", "emergency garage door repair"],
    "Painting": ["painters", "house painting", "interior painting",
                 "exterior painting", "cabinet painting", "drywall repair",
                 "pressure washing", "commercial painting"],
    "Siding": ["siding", "siding installation", "siding repair",
               "siding replacement", "vinyl siding", "stucco repair"],
    "Decking": ["deck builders", "deck repair", "deck building",
                "deck staining", "patio cover", "pergola builders"],
    "Foundation Repair": ["foundation repair", "foundation crack repair",
                          "house leveling", "slab leak repair",
                          "foundation inspection", "pier and beam repair"],
    "Waterproofing": ["waterproofing", "basement waterproofing",
                      "crawl space waterproofing", "sump pump installation",
                      "sump pump repair", "french drain installation"],
    "Bathroom & Kitchen Remodeling": ["bathroom remodeling", "kitchen remodeling",
                                      "bathroom renovation", "kitchen renovation",
                                      "shower installation", "bathtub replacement",
                                      "cabinet installation", "countertop installation"],
    "Water, Fire & Mold Restoration": ["water damage restoration", "mold removal",
                                       "water damage repair", "fire damage restoration",
                                       "mold remediation", "flood cleanup",
                                       "smoke damage restoration", "water extraction"],
    "Bio Hazard Cleanup": ["biohazard cleanup", "crime scene cleanup",
                           "hoarding cleanup", "sewage cleanup"],
    "Solar": ["solar installers", "solar panel installation", "solar panel repair",
              "solar companies", "solar panel cleaning"],
}

COMPILED_EXCLUDE = [(re.compile(p), re.compile(u) if u else None, why)
                    for p, u, why in EXCLUDE]
COMPILED_RULES = [(c, re.compile(p)) for c, p in RULES]


def classify(name):
    n = re.sub(r"\s+", " ", name.lower().strip())
    for rx, unless, why in COMPILED_EXCLUDE:
        if rx.search(n) and not (unless and unless.search(n)):
            return None, why
    for camp, rx in COMPILED_RULES:
        if rx.search(n):
            return camp, None
    return None, "no campaign covers it"


def build():
    services = [s["name"] for s in json.load(open(SRC, encoding="utf-8"))]
    by_camp, dropped = {}, {}
    for s in services:
        camp, why = classify(s)
        if camp:
            by_camp.setdefault(camp, []).append(s)
        else:
            dropped.setdefault(why, []).append(s)
    return services, by_camp, dropped


HEAD_TERM = {
    "Plumbing": ["plumbers", "plumbing"], "Electrical": ["electricians", "electrical"],
    "HVAC": ["hvac", "air conditioning"], "Roofing": ["roofers", "roofing"],
    "Pest Control": ["pest control", "exterminators"],
    "Appliance Repair": ["appliance repair"], "Gutters": ["gutters"],
    "Tree Services": ["tree service", "tree removal"],
    "Lawncare & Landscaping": ["landscaping", "lawn care"],
    "Garage Door": ["garage door repair"], "Painting": ["painters", "painting"],
    "Windows": ["window replacement", "windows"], "Fencing": ["fence company", "fencing"],
    "Carpet & Flooring": ["flooring", "carpet installation"],
    "Decking": ["deck builders", "decks"], "Siding": ["siding"],
    "Foundation Repair": ["foundation repair"], "Waterproofing": ["waterproofing"],
    "Bathroom & Kitchen Remodeling": ["bathroom remodeling", "kitchen remodeling"],
    "Water, Fire & Mold Restoration": ["water damage restoration", "mold removal"],
    "Bio Hazard Cleanup": ["biohazard cleanup"], "Solar": ["solar installers"],
    "Moving": ["movers", "moving company"],
    "Dumpster & Porta Potty": ["dumpster rental", "porta potty rental"],
    "Self Storage": ["self storage"], "Walk In Tubs": ["walk in tubs"],
    "Dentist": ["dentist"], "Garage Door (FB Marketplace)": ["garage door repair"],
    "Airline Tickets": ["airline tickets"],
}


# The 853-service list barely covers a few of the campaigns (one entry for
# Self Storage, one for Dentist). These fill those out. Service names only --
# nothing here is a claim, a price or a promise.
EXTRA = {
    "Gutters": ["gutter cleaning", "gutter guards", "gutter installation",
                "gutter repair", "gutter replacement", "seamless gutters"],
    "Garage Door": ["garage door cable repair", "garage door installation",
                    "garage door off track", "garage door opener installation",
                    "garage door opener repair", "garage door panel replacement",
                    "garage door spring replacement", "garage door tune up"],
    "Moving": ["apartment movers", "commercial movers", "labor only movers",
               "last minute movers", "local movers", "long distance movers",
               "office movers", "senior moving services", "storage and moving"],
    "Walk In Tubs": ["barrier free shower", "bathtub to shower conversion",
                     "senior bathroom remodel", "step in shower installation",
                     "tub cut out", "walk in shower installation"],
    "Dumpster & Porta Potty": ["construction dumpster rental",
                               "event porta potty rental", "handicap porta potty",
                               "residential dumpster rental", "roll off dumpster rental",
                               "temporary toilet rental", "yard waste dumpster"],
    "Self Storage": ["boat storage", "climate controlled storage",
                     "drive up storage units", "indoor storage units",
                     "rv storage", "storage units near me", "vehicle storage"],
    "Dentist": ["cosmetic dentistry", "dental crowns", "dental implants",
                "emergency dentist", "family dentist", "root canal",
                "teeth cleaning", "teeth whitening", "tooth extraction",
                "wisdom tooth removal"],
    "Bio Hazard Cleanup": ["biohazard remediation", "crime scene cleanup",
                           "hoarding cleanup", "sewage cleanup",
                           "trauma scene cleanup", "unattended death cleanup"],
    "Solar": ["battery storage installation", "solar inspection",
              "solar panel cleaning", "solar panel installation",
              "solar panel repair", "solar water heating"],
    "Pest Control": ["ant exterminator", "bed bug treatment", "cockroach exterminator",
                     "flea treatment", "mosquito control", "rodent control",
                     "spider control", "termite inspection", "termite treatment",
                     "wasp nest removal", "wildlife removal"],
    "Foundation Repair": ["basement wall repair", "crawl space jacks",
                          "foundation crack repair", "foundation inspection",
                          "house leveling", "pier installation", "slab leak repair"],
    "Waterproofing": ["basement waterproofing", "crawl space vapor barrier",
                      "exterior waterproofing", "interior drain tile",
                      "sump pump installation", "sump pump repair"],
    "Water, Fire & Mold Restoration": [
        "basement flood cleanup", "black mold removal", "burst pipe cleanup",
        "ceiling water damage repair", "emergency water extraction",
        "fire and smoke restoration", "mold inspection", "mold testing",
        "smoke damage cleanup", "storm damage restoration",
        "structural drying", "water damage repair"],
    "Garage Door (FB Marketplace)": [
        "garage door installation", "garage door opener repair",
        "garage door spring replacement"],
}


def main():
    services, by_camp, dropped = build()
    for camp, extra in EXTRA.items():
        have = {s.lower() for s in by_camp.get(camp, [])}
        by_camp.setdefault(camp, []).extend(e for e in extra if e not in have)
    if "--dropped" in sys.argv:
        want = sys.argv[sys.argv.index("--dropped") + 1] if len(sys.argv) > 2 else None
        for why, names in sorted(dropped.items(), key=lambda x: -len(x[1])):
            if want and want not in why:
                continue
            print("== %s (%d)" % (why, len(names)))
            print("   " + ", ".join(names))
        return
    if "--camp" in sys.argv:
        print(", ".join(by_camp.get(sys.argv[sys.argv.index("--camp") + 1], [])))
        return
    if "--write" in sys.argv:
        # Payout medians come from the coverage feed, which only carries the
        # niches with live bids; a campaign it does not list still runs, it
        # just has no ZIP-level rate to show.
        old = json.load(open(r"C:/Users/HP/keyword-research-tool/data/"
                             r"services_by_niche.json", encoding="utf-8"))["niches"]
        intel = {}
        for line in open(r"C:/Users/HP/Ai-website-Builder/call_intel/niches.csv",
                         encoding="utf-8").read().splitlines()[1:]:
            if line.strip():
                c = line.split("|")
                intel[c[0]] = {"calls": int(c[1]), "paid_pct": int(c[4]),
                               "booked_pct": int(c[5])}
        intel_key = {
            "Appliance Repair": "appliance repair", "Plumbing": "plumbing",
            "Electrical": "electrical", "HVAC": "hvac", "Roofing": "roofing",
            "Pest Control": "pest control", "Gutters": "gutters",
            "Tree Services": "tree services", "Painting": "painting",
            "Lawncare & Landscaping": "lawncare & landscaping",
            "Garage Door": "garage door", "Windows": "window repair",
            "Water, Fire & Mold Restoration": "water damage",
            "Bathroom & Kitchen Remodeling": "remodeling",
        }
        out = {"source": "LeadSmart Manage Campaigns (offers.ringba.com/leadsmart), "
                         "read from the account dashboard 2026-09-24",
               "campaigns": {}}
        for key, title, payout, status, fit in CAMPAIGNS:
            # Head term first, always: the plan's order is the site's order and
            # "[trade] [city]" is the page that earns.
            heads = HEAD_TERM.get(key, [])
            subs = [s for s in sorted(set(by_camp.get(key, []))) if s not in heads]
            feed = FEED_NICHE.get(key)
            econ = dict((old.get(feed) or {}).get("economics") or {})
            ci = intel.get(intel_key.get(key, ""), {})
            if ci:
                econ["calls_seen"] = ci["calls"]
                econ["paid_pct"] = ci["paid_pct"]
                econ["booked_pct"] = ci["booked_pct"]
            out["campaigns"][key] = {
                "offer_title": title, "payout_type": payout, "status": status,
                "local_seo": fit, "feed_niche": feed, "economics": econ,
                "head_terms": HEAD_TERM.get(key, []),
                "probe_terms": PROBE.get(key, HEAD_TERM.get(key, [])[:1]),
                "services": heads + subs,
            }
        out["dropped"] = {why: sorted(n) for why, n in dropped.items()}
        json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("wrote", OUT)
        return

    print("mapped %d / %d   dropped %d"
          % (sum(len(v) for v in by_camp.values()), len(services),
             sum(len(v) for v in dropped.values())))
    for key, _t, _p, _s, _f in CAMPAIGNS:
        print("  %-34s %d" % (key, len(by_camp.get(key, []))))
    print()
    for why, names in sorted(dropped.items(), key=lambda x: -len(x[1])):
        print("  drop %-42s %d" % (why, len(names)))


if __name__ == "__main__":
    main()
