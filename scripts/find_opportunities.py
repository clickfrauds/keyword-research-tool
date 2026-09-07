"""
find_opportunities.py  (OPPORTUNITY FINDER — payout data × SERP weakness)
------------------------------------------------------------------------
Hand-checking SERPs does not scale. The coverage feed carries 280,000+
rows (24 niches × ~29,000 ZIPs) and every one of them has 5-30 sub-service
queries hanging off it. Seven manual checks told us nothing except that
seven queries were busy — the sample was far too small to conclude
anything about the other few million.

This does the same check mechanically, in the only order that makes
financial sense:

    STAGE 1  pull coverage            free      (static JSON, no key)
    STAGE 2  revenue filter           free      (payout / population band)
    STAGE 3  city rollup + bundles    free      (one site, many niches)
    STAGE 4  SERP scan                COSTS     (SerpApi, hard-capped)
    STAGE 5  score, rank, publish     free

Stages 1-3 are free and cut 280,000 rows to a few hundred candidates.
Only then does anything paid run, and MAX_SERP_CHECKS caps that. Running
a SERP query against every row would cost thousands of dollars to learn
what a population filter answers for nothing.

WHERE THE COVERAGE DATA COMES FROM
  The coverage site bakes every query into static JSON under /api/ on a
  daily CI run, so there is a stable file contract and nothing to scrape:

    /api/meta.json            niche list + payout_type + top payout
    /api/states.json          per-state niche/zip/city counts
    /api/state/<ST>.json      the actual rows for one state

  A state shard is column-compressed — string tables plus integer rows:

    { city:[...], niche:[...], ptype:[...], county:[...],
      rows: [[cityIdx, zip, nicheIdx, ptypeIdx, payout,
              population, density, lat, lng, countyIdx], ...] }

WHAT THE SERP SCORE MEANS
  Built from what real SERPs in this vertical actually contain, not from
  a generic difficulty metric. A directory in the top 10 is an OPENING
  (nobody local built a page). A dedicated service+city page is a real
  competitor. A programmatic subdomain (willis-tx.example.com) is a
  competitor that is beatable on depth but still holds the slot.

Env (all optional except the SERP stage):
  COVERAGE_BASE      default https://leadsmart-coverage.netlify.app
  NICHES             comma list, blank = every niche in the feed
  PAYOUT_TYPE        Call | CPL | both        (default Call)
  MIN_PAYOUT         default 35
  MIN_POP / MAX_POP  default 8000 / 120000    (the winnable band)
  STATES             comma list, blank = all 53
  MIN_BUNDLE_NICHES  default 1 (2+ finds multi-niche cities)
  MAX_SERP_CHECKS    default 120  — this is the money knob
  SERPAPI_API_KEY    without it stages 1-3 still run and publish
  SERP_GL            default us

Out: opportunities.json, opportunities.csv, opportunity_report.md
"""

import os
import re
import csv
import sys
import json
import time
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE       = os.environ.get("COVERAGE_BASE", "https://leadsmart-coverage.netlify.app").rstrip("/")
NICHES     = [n.strip() for n in os.environ.get("NICHES", "").split(",") if n.strip()]
PAYOUT_T   = os.environ.get("PAYOUT_TYPE", "Call").strip() or "Call"
MIN_PAYOUT = float(os.environ.get("MIN_PAYOUT", "35") or 35)
MIN_POP    = int(os.environ.get("MIN_POP", "8000") or 8000)
MAX_POP    = int(os.environ.get("MAX_POP", "120000") or 120000)
STATES     = [s.strip().upper() for s in os.environ.get("STATES", "").split(",") if s.strip()]
MIN_BUNDLE = int(os.environ.get("MIN_BUNDLE_NICHES", "1") or 1)
MAX_SERP   = int(os.environ.get("MAX_SERP_CHECKS", "120") or 120)
SERP_KEY   = os.environ.get("SERPAPI_API_KEY", "").strip()
SERP_GL    = os.environ.get("SERP_GL", "us").strip() or "us"
# How the SERP budget is spent. 1 niche × 3 subs = a deep read on each city's
# best offer. 3 niches × 1 sub = a bundle read — is this city open across
# several offers, or only one? Both matter, at different points.
NICHES_PER_CITY = int(os.environ.get("NICHES_PER_CITY", "1") or 1)
SUBS_PER_NICHE  = int(os.environ.get("SUBS_PER_NICHE", "3") or 3)

# ── Sub-services per niche ────────────────────────────────────────────────
# The head term ("plumbing Boise") is never the target — it is always taken.
# These are the queries an unranked site can realistically enter on.
SUB_SERVICES = {
    "Plumbing": ["drain cleaning", "hydro jetting", "sewer line repair",
                 "sewer camera inspection", "slab leak detection",
                 "burst pipe repair", "water heater repair",
                 "sump pump repair", "toilet repair", "repiping",
                 "gas line repair", "frozen pipe repair"],
    "HVAC": ["ac repair", "furnace repair", "heat pump repair",
             "duct cleaning", "ac installation", "thermostat installation",
             "emergency hvac repair", "mini split installation"],
    "Roofing": ["roof leak repair", "storm damage roof repair",
                "hail damage roof repair", "roof replacement",
                "emergency roof tarping", "flat roof repair",
                "roof inspection", "shingle replacement"],
    "Electrical": ["panel upgrade", "electrical rewiring", "ev charger installation",
                   "generator installation", "outlet repair",
                   "emergency electrician", "ceiling fan installation"],
    "Pest Control": ["rodent removal", "bed bug treatment", "termite inspection",
                     "wildlife removal", "wasp nest removal", "ant control",
                     "cockroach extermination", "mosquito control"],
    "Water Damage": ["water damage restoration", "sewage backup cleanup",
                     "basement flooding cleanup", "crawl space water removal",
                     "ceiling water damage repair", "emergency water extraction",
                     "structural drying"],
    "Mold Removal": ["mold remediation", "black mold removal",
                     "crawl space mold removal", "attic mold removal",
                     "mold inspection"],
    "Gutters": ["gutter cleaning", "gutter repair", "gutter guard installation",
                "gutter replacement", "downspout repair"],
    "Garage Door": ["garage door spring repair", "garage door opener repair",
                    "garage door off track", "garage door cable repair"],
    "Foundation Repair": ["foundation crack repair", "basement waterproofing",
                          "crawl space encapsulation", "pier and beam repair"],
    "Tree Services": ["emergency tree removal", "storm damage tree removal",
                      "tree stump removal", "tree trimming"],
    "Appliance": ["refrigerator repair", "washer repair", "dryer repair",
                  "dishwasher repair", "oven repair"],
    "Siding": ["siding repair", "siding replacement", "storm damage siding repair"],
    "Waterproofing": ["basement waterproofing", "foundation waterproofing",
                      "french drain installation", "sump pump installation"],
    "Biohazard": ["biohazard cleanup", "crime scene cleanup",
                  "hoarding cleanup", "unattended death cleanup"],
    "Fire Damage Removal": ["fire damage restoration", "smoke damage cleanup",
                            "soot removal", "board up services"],
    "Bathroom Remodeling": ["bathroom remodel", "shower replacement",
                            "tub to shower conversion", "walk in tub installation",
                            "bathroom renovation"],
    "Kitchen": ["kitchen remodel", "kitchen cabinet refacing",
                "countertop installation", "kitchen renovation"],
    "Painting": ["interior painting", "exterior painting",
                 "cabinet painting", "house painters"],
    "Deck": ["deck building", "deck repair", "deck staining",
             "composite deck installation"],
    "Landscaping": ["landscaping services", "sod installation",
                    "retaining wall installation", "irrigation installation"],
    "Solar": ["solar panel installation", "solar panel repair",
              "residential solar installation"],
    "Roofing CPL": ["roof replacement", "roof leak repair",
                    "storm damage roof repair", "roof inspection"],
}

# A niche with no entry here generates no queries, so its cities drop out of
# stage 4 without a word. Bathroom Remodeling — a Call niche across 11,090
# ZIPs — was being silently skipped exactly this way.
_MISSING_SUBS = set()

# ── SERP occupant classification ─────────────────────────────────────────
# Derived from real result sets in this vertical, not a generic list.
DIRECTORIES = ("yelp.com", "bbb.org", "angi.com", "angieslist.com",
               "homeadvisor.com", "thumbtack.com", "yellowpages.com",
               "houzz.com", "porch.com", "nodig.com", "expertise.com",
               "networx.com", "buildzoom.com", "manta.com", "homeyou.com",
               "contractorplus.app", "fixr.com", "mapquest.com")
FORUMS      = ("reddit.com", "quora.com", "houzz.com/discussions",
               "city-data.com", "diychatroom.com", "terrylove.com")
# A business's Facebook page ranking on page 1 is the same signal as a
# directory: nobody built a real page for this query. Classified as
# "dedicated" it was scoring like a serious competitor instead.
SOCIAL      = ("facebook.com", "instagram.com", "linkedin.com", "x.com",
               "twitter.com", "nextdoor.com", "youtube.com", "tiktok.com",
               "pinterest.com")
# Big-box retail runs programmatic location pages in every city. Huge
# authority, thin pages — a national occupant, not a local competitor.
BIGBOX      = ("homedepot.com", "lowes.com", "menards.com", "acehardware.com",
               "costco.com", "walmart.com", "sears.com", "bestbuy.com")
NATIONALS   = ("rotorooter.com", "servpro.com", "terminix.com", "orkin.com",
               "mrrooter.com", "rainbowrestores.com", "aptive.com",
               "rentokil.com", "benjaminfranklinplumbing.com",
               "arsrescuerooter.com", "rescuerooter.com", "911restoration.com",
               "servicemaster", "pauldavis.com", "trugreen.com", "aramark",
               "mosquitojoe.com", "roto-rooter.com")

_SUBDOMAIN_PSEO = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-[a-z]{2}\.", re.I)

# SerpApi's `location` wants a full place string, not a postal code.
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def j(url, tries=3):
    """GET JSON. Fail-open — a dead endpoint must not kill the run."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "opportunity-finder/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                print(f"   ⚠️ {url} failed: {str(e)[:90]}")
                return None
            time.sleep(1.5 * (i + 1))
    return None


# ══════════════════════════════════════════════════════════════════
# STAGE 1 — pull coverage
# ══════════════════════════════════════════════════════════════════
def pull_coverage():
    print("── STAGE 1: coverage pull ─────────────────────────────")
    meta = j(f"{BASE}/api/meta.json")
    if not meta:
        print("   ❌ meta.json unreachable — cannot continue")
        return None, []
    print(f"   📅 dataset {meta.get('data_date')} · "
          f"{meta.get('niche_count')} niches · {meta.get('coverage_rows')} rows")

    states = STATES or [s["state_id"] for s in (j(f"{BASE}/api/states.json") or [])]
    if not states:
        print("   ❌ no states resolved")
        return meta, []

    rows = []
    for i, st in enumerate(states, 1):
        shard = j(f"{BASE}/api/state/{st}.json")
        if not shard or not shard.get("rows"):
            continue
        city, niche = shard.get("city", []), shard.get("niche", [])
        ptype, county = shard.get("ptype", []), shard.get("county", [])
        for r in shard["rows"]:
            try:
                rows.append({
                    "state": st,
                    "city":   city[r[0]]   if r[0] >= 0 and r[0] < len(city)   else None,
                    "zip":    r[1],
                    "niche":  niche[r[2]]  if r[2] >= 0 and r[2] < len(niche)  else None,
                    "ptype":  ptype[r[3]]  if r[3] >= 0 and r[3] < len(ptype)  else None,
                    "payout": float(r[4] or 0),
                    "pop":    int(r[5] or 0),
                    "county": county[r[9]] if len(r) > 9 and r[9] >= 0 and r[9] < len(county) else None,
                })
            except Exception:
                continue
        if i % 10 == 0 or i == len(states):
            print(f"   📦 {i}/{len(states)} states · {len(rows):,} rows")
    print(f"   ✅ {len(rows):,} coverage rows\n")
    return meta, rows


# ══════════════════════════════════════════════════════════════════
# STAGE 2 + 3 — filter, roll up to cities, detect bundles
# ══════════════════════════════════════════════════════════════════
def price_modes(rows):
    """
    GATE 05 — is this niche geographically priced, or one flat rate?

    Counted from the rows already in hand, so it costs nothing. A niche with
    a handful of distinct payouts nationwide has no high-payout ZIP to hunt:
    picking a market buys you nothing there, and the city decision collapses
    to search volume and competition alone. A niche with hundreds of distinct
    values is the opposite — the market you pick IS the lever.
    """
    vals = {}
    for r in rows:
        if r["niche"] and r["payout"]:
            vals.setdefault((r["niche"], r["ptype"]), set()).add(r["payout"])
    out = {}
    for k, v in vals.items():
        n = len(v)
        out[k] = {"distinct": n, "mode": "flat" if n <= 3 else "geo"}
    print("── Pricing model per niche ────────────────────────────")
    for (niche, pt), m in sorted(out.items(), key=lambda kv: -kv[1]["distinct"])[:12]:
        tag = "GEO " if m["mode"] == "geo" else "FLAT"
        print(f"   {tag} {niche:<22} {pt:<5} {m['distinct']:>5} distinct payouts")
    print()
    return out


def shortlist(rows, pricing):
    print("── STAGE 2: revenue filter ────────────────────────────")
    keep = []
    for r in rows:
        if not r["city"] or not r["niche"]:
            continue
        if PAYOUT_T != "both" and (r["ptype"] or "") != PAYOUT_T:
            continue
        if r["payout"] < MIN_PAYOUT:
            continue
        if not (MIN_POP <= r["pop"] <= MAX_POP):
            continue
        if NICHES and r["niche"] not in NICHES:
            continue
        keep.append(r)
    print(f"   payout ≥ ${MIN_PAYOUT:g} · pop {MIN_POP:,}-{MAX_POP:,} "
          f"· type {PAYOUT_T}")
    print(f"   ✅ {len(rows):,} → {len(keep):,} rows\n")

    print("── STAGE 3: city rollup + bundles ─────────────────────")
    cities = {}
    for r in keep:
        k = (r["state"], r["city"])
        c = cities.setdefault(k, {
            "state": r["state"], "city": r["city"], "county": r["county"],
            "pop": r["pop"], "niches": {}, "zips": set(),
        })
        c["zips"].add(r["zip"])
        n = c["niches"].setdefault(r["niche"], {"best": 0.0, "zips": 0})
        n["best"] = max(n["best"], r["payout"])
        n["zips"] += 1

    out = []
    for c in cities.values():
        if len(c["niches"]) < MIN_BUNDLE:
            continue
        top = sorted(c["niches"].items(), key=lambda kv: -kv[1]["best"])
        # Bundle value: the best niche in full, plus half of each additional
        # one. A second niche on the same domain is real money but it does
        # not double the traffic — it shares the site's authority.
        bundle = top[0][1]["best"] + sum(v["best"] for _, v in top[1:]) * 0.5
        c["zips"] = len(c["zips"])
        c["top_niche"]  = top[0][0]
        c["top_payout"] = round(top[0][1]["best"], 2)
        c["niche_list"] = [
            {"niche": n, "payout": round(v["best"], 2),
             "pricing": (pricing.get((n, PAYOUT_T)) or {}).get("mode", "?")}
            for n, v in top
        ]
        c["top_pricing"] = c["niche_list"][0]["pricing"]
        c["bundle_value"] = round(bundle, 2)
        out.append(c)

    out.sort(key=lambda c: -c["bundle_value"])
    multi = sum(1 for c in out if len(c["niche_list"]) > 1)
    print(f"   ✅ {len(out):,} candidate cities · {multi:,} with 2+ niches\n")
    return out


# ══════════════════════════════════════════════════════════════════
# STAGE 4 — SERP scan (the only stage that costs money)
# ══════════════════════════════════════════════════════════════════
_UULE_KEY = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
             "0123456789-_")


def _uule(location):
    """Google's own canonical-name location encoding, computed locally."""
    import base64
    b = base64.b64encode(location.encode("utf-8")).decode("ascii")
    return "w+CAIQICI" + _UULE_KEY[len(location) % len(_UULE_KEY)] + b


def serp(query, location=None):
    """
    `location` is not optional for local intent. Without it SerpApi answers
    from a default US locale, and "roof leak repair Redwood City CA" comes
    back as a generic national SERP — which is how a page-1 stack of two city
    EMDs and four exact-match pages once scored a clean 100 here. The whole
    point of the scan is the LOCAL result set, so send the city every time.
    """
    if not SERP_KEY:
        return None
    params = {
        "engine": "google", "q": query, "num": 10,
        "gl": SERP_GL, "hl": "en", "api_key": SERP_KEY,
    }
    if location:
        # Both, deliberately. `location` depends on SerpApi resolving the
        # string against its own place database and fails quietly for smaller
        # cities; `uule` is Google's own encoding and needs no lookup. A run
        # that sent only `location` came back with national cost-aggregator
        # SERPs while reporting them as wide-open local ones.
        params["location"] = location
        params["uule"] = _uule(location)
    q = urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(f"https://serpapi.com/search?{q}", timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"      ⚠️ SERP failed: {str(e)[:70]}")
        return None


def score_serp(data, service, city):
    """
    100 = wide open, 0 = fully occupied.

    Weights come from what these SERPs actually hold. A dedicated
    service+city page is the expensive competitor. A directory is an
    opening — it means nobody local built the page.
    """
    if not data:
        return None
    results = (data.get("organic_results") or [])[:10]
    if not results:
        return None

    # GATE 07 — map pack. In most local service niches the pack takes the
    # majority of the clicks, so an open organic SERP sitting under three
    # 500-review businesses is not the opportunity it looks like. This rides
    # on the same response the organic scan already paid for.
    pack = (data.get("local_results") or {})
    if isinstance(pack, dict):
        pack = pack.get("places") or []
    pack = pack if isinstance(pack, list) else []
    pack_reviews = sorted(
        (int(p.get("reviews") or 0) for p in pack), reverse=True)[:3]
    pack_n   = len(pack)
    pack_max = pack_reviews[0] if pack_reviews else 0
    pack_med = pack_reviews[len(pack_reviews) // 2] if pack_reviews else 0

    svc_words = [w for w in re.split(r"\W+", service.lower()) if len(w) > 3]
    city_l = city.lower()
    city_slug = city_l.replace(" ", "-")
    city_flat = city_slug.replace("-", "")
    tally = {"dedicated": 0, "pseo": 0, "national": 0, "emd": 0,
             "directory": 0, "forum": 0, "other_local": 0, "results": len(results),
             "pack_size": pack_n, "pack_top_reviews": pack_max,
             "pack_median_reviews": pack_med}
    occupants = []

    for res in results:
        link  = (res.get("link") or "").lower()
        title = (res.get("title") or "").lower()
        host  = urllib.parse.urlparse(link).netloc.lower()
        bare  = host[4:] if host.startswith("www.") else host
        flat  = bare.replace("-", "").replace(".", "")
        blob  = f"{title} {link}"
        kinds = []

        if any(d in bare for d in DIRECTORIES):
            tally["directory"] += 1; kinds.append("directory")
        elif any(s_ in bare for s_ in SOCIAL):
            tally["directory"] += 1; kinds.append("social profile")
        elif any(f in bare for f in FORUMS):
            tally["forum"] += 1; kinds.append("forum")
        elif any(n in bare for n in NATIONALS) or any(b in bare for b in BIGBOX):
            tally["national"] += 1; kinds.append("national brand")
        else:
            # An EMD is USUALLY also an exact-match page, so these are counted
            # together rather than as an either/or. The old elif chain let a
            # city EMD serving a dedicated page book the cheaper of the two
            # penalties and skip the expensive one.
            if _SUBDOMAIN_PSEO.match(bare) and city_slug in bare:
                tally["pseo"] += 1; kinds.append("pSEO subdomain")
            if city_flat in flat:
                tally["emd"] += 1; kinds.append("city EMD")
            if city_l in blob and any(w in blob for w in svc_words):
                tally["dedicated"] += 1; kinds.append("dedicated page")
            if not kinds:
                # A local contractor ranking here without the city in its
                # title is still a competitor. Left unclassified these were
                # invisible — a SERP of ten real businesses scored a clean
                # 100 because not one of them fell into a bucket.
                tally["other_local"] += 1; kinds.append("independent site")
        if kinds:
            occupants.append({"host": bare, "kind": " + ".join(kinds)})

    # GUARD — is this even a local SERP? A service+city query answered by
    # Google always surfaces local businesses. A result set carrying none,
    # mostly national cost aggregators, is the signature of a request whose
    # location never took effect. Scoring it produced a "wide open, 100/100"
    # verdict on Duarte CA, whose real page one holds a city EMD and two
    # programmatic subdomains. Refuse it instead of scoring it.
    local_any = (tally["dedicated"] + tally["emd"] +
                 tally["pseo"] + tally["other_local"])
    if local_any == 0:
        return None

    s = 100
    s -= tally["dedicated"]   * 18
    s -= tally["emd"]         * 20   # the single strongest occupant
    s -= tally["pseo"]        * 12
    s -= tally["national"]    * 10
    s -= tally["other_local"] * 4
    # Bonuses are capped. Uncapped, eight directories paid +48 and cancelled
    # two dedicated pages outright — the score then read 100 on a SERP the
    # report's own rules say to walk away from.
    s += min(tally["directory"] * 6, 12)
    s += min(tally["forum"] * 8, 16)
    if tally["dedicated"] == 0 and tally["emd"] == 0:
        s += 10

    # Pack penalty scales with how entrenched it is, not merely whether one
    # exists. Three businesses at 500+ reviews each is a different market
    # from three at 40.
    if pack_n == 0:
        s += 10
    elif pack_med >= 500:
        s -= 18
    elif pack_med >= 200:
        s -= 12
    elif pack_med >= 100:
        s -= 6

    s = max(0, min(100, s))

    # HARD CAPS. The report tells the reader to STOP on any EMD, any pSEO
    # network, or two dedicated pages — so the number must not then say 100.
    # These are ceilings, not deductions: no amount of directory presence can
    # lift a SERP back over an occupant that is already sitting in it.
    if tally["emd"]:
        s = min(s, 25)
    if tally["pseo"]:
        s = min(s, 30)
    if tally["dedicated"] >= 2:
        s = min(s, 35)

    return s, tally, occupants


def scan(cands):
    print("── STAGE 4: SERP scan ─────────────────────────────────")
    if not SERP_KEY:
        print("   ℹ️ no SERPAPI_API_KEY — stages 1-3 published, SERP skipped.")
        print("      Set the secret to rank candidates by real competition.\n")
        return []

    # BREADTH BEFORE DEPTH. Laid out city-major, the cap would burn the whole
    # budget on the first few cities and tell us nothing about the rest. Passes
    # are built rank-major instead: every city gets its first query before any
    # city gets its second, so a cap anywhere still leaves a comparable read
    # across the whole shortlist.
    passes = []
    for c in cands:
        for ni, nrec in enumerate(c["niche_list"][:NICHES_PER_CITY]):
            if nrec["niche"] not in SUB_SERVICES:
                _MISSING_SUBS.add(nrec["niche"])
                continue
            for si, sub in enumerate(SUB_SERVICES.get(nrec["niche"], [])[:SUBS_PER_NICHE]):
                passes.append((ni * 100 + si, c, nrec["niche"], nrec["payout"],
                               nrec.get("pricing", "?"), sub))
    passes.sort(key=lambda p: p[0])
    jobs = [p[1:] for p in passes][:MAX_SERP]
    print(f"   {len(jobs)} queries (cap {MAX_SERP}) · "
          f"{NICHES_PER_CITY} niche(s) × {SUBS_PER_NICHE} sub(s) per city")
    if _MISSING_SUBS:
        print(f"   ⚠️ no sub-services defined for {sorted(_MISSING_SUBS)} — "
              f"those cities were skipped. Add them to SUB_SERVICES.")
    if len(jobs) < len(cands):
        print(f"   ℹ️ cap reached: the top {len(jobs)} cities by bundle value "
              f"were tested on their best niche. {len(cands) - len(jobs)} "
              f"candidates went untested — raise max_serp_checks to reach them.")

    found = []
    for i, (c, niche_name, niche_payout, niche_pricing, sub) in enumerate(jobs, 1):
        query = f"{sub} {c['city']} {c['state']}"
        loc   = f"{c['city']}, {STATE_NAMES.get(c['state'], c['state'])}, United States"
        res   = score_serp(serp(query, loc), sub, c["city"])
        if not res:
            continue
        sc, tally, occ = res
        found.append({
            "city": c["city"], "state": c["state"], "county": c["county"],
            "population": c["pop"], "zips": c["zips"],
            "niche": niche_name, "sub_service": sub, "query": query,
            "payout": niche_payout, "pricing": niche_pricing,
            "bundle_value": c["bundle_value"],
            "niches_here": c["niche_list"],
            "serp_score": sc, "serp_breakdown": tally, "occupants": occ,
            # What a page here is worth: openness × revenue. A wide-open
            # SERP on a $12 payout is not an opportunity, and neither is a
            # $160 payout behind six dedicated pages.
            "opportunity": round(sc / 100 * c["bundle_value"], 2),
        })
        if i % 10 == 0 or i == len(jobs):
            print(f"   🔎 {i}/{len(jobs)} · best so far "
                  f"{max((f['opportunity'] for f in found), default=0):.0f}")
        time.sleep(0.7)

    found.sort(key=lambda f: -f["opportunity"])
    print(f"   ✅ {len(found)} scored\n")
    return found


# ══════════════════════════════════════════════════════════════════
# STAGE 5 — output
# ══════════════════════════════════════════════════════════════════
def write(meta, cands, scored, pricing=None):
    payload = {
        "pricing_model_by_niche": {
            f"{n} ({p})": v for (n, p), v in (pricing or {}).items()
        },
        "generated":    time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "dataset_date": (meta or {}).get("data_date"),
        "filters": {
            "payout_type": PAYOUT_T, "min_payout": MIN_PAYOUT,
            "population": [MIN_POP, MAX_POP], "niches": NICHES or "all",
            "states": STATES or "all", "min_bundle_niches": MIN_BUNDLE,
        },
        "candidate_cities": len(cands),
        "serp_scanned":     len(scored),
        "opportunities":    scored[:200],
        "top_candidates_unscanned": [
            {k: c[k] for k in ("city", "state", "county", "pop", "zips",
                               "top_niche", "top_payout", "bundle_value", "niche_list")}
            for c in cands[:200]
        ],
    }
    with open("opportunities.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with open("opportunities.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "opportunity", "serp_score", "payout", "pricing",
                    "bundle_value", "niche", "sub_service", "city", "state",
                    "county", "population", "zips", "dedicated", "emd", "pseo",
                    "national", "other_local", "directory", "pack_size",
                    "pack_median_reviews", "query", "occupants"])
        for i, o in enumerate(scored[:200], 1):
            b = o["serp_breakdown"]
            w.writerow([i, o["opportunity"], o["serp_score"], o["payout"],
                        o.get("pricing", "?"),
                        o["bundle_value"], o["niche"], o["sub_service"],
                        o["city"], o["state"], o["county"], o["population"],
                        o["zips"], b["dedicated"], b.get("emd", 0), b["pseo"],
                        b["national"], b.get("other_local", 0), b["directory"],
                        b.get("pack_size", 0), b.get("pack_median_reviews", 0),
                        o["query"],
                        " | ".join(f"{x['host']} ({x['kind']})" for x in o["occupants"][:10])])

    lines = [
        "# Opportunity scan",
        "",
        f"- Dataset **{(meta or {}).get('data_date')}** · scanned {time.strftime('%Y-%m-%d')}",
        f"- Filters: `{PAYOUT_T}` · payout ≥ **${MIN_PAYOUT:g}** · "
        f"population **{MIN_POP:,}–{MAX_POP:,}** · niches **{', '.join(NICHES) or 'all'}**",
        f"- **{len(cands):,}** candidate cities · **{len(scored)}** SERP-scored",
        "",
    ]
    if scored:
        lines += ["## Top 30 by opportunity", "",
                  "| # | Opp | SERP | Payout | Pricing | Pack | Query | Occupied by |",
                  "|---|---|---|---|---|---|---|---|"]
        for i, o in enumerate(scored[:30], 1):
            b = o["serp_breakdown"]
            occ = (f"{b['dedicated']} dedicated, {b.get('emd',0)} EMD, "
                   f"{b['pseo']} pSEO, {b.get('other_local',0)} local, "
                   f"{b['directory']} directory")
            pk = (f"{b.get('pack_size',0)}× {b.get('pack_median_reviews',0)} rev"
                  if b.get("pack_size") else "none")
            lines.append(f"| {i} | **{o['opportunity']:.0f}** | {o['serp_score']} "
                         f"| ${o['payout']:.2f} | {o.get('pricing','?')} | {pk} "
                         f"| `{o['query']}` | {occ} |")
        lines += ["", "### Reading a row",
                  "",
                  "- **STOP** on any `EMD > 0` or `pSEO > 0` — a city exact-match "
                  "domain or a programmatic network already holds that slot with "
                  "authority a new domain does not have.",
                  "- **STOP** on `dedicated >= 2` — the local trades already built "
                  "that page.",
                  "- `pricing: flat` means the payout is identical nationwide, so "
                  "choosing this market over another buys nothing on the revenue "
                  "side; judge it on volume and competition alone.",
                  "- A pack of three businesses at 500+ reviews takes most of the "
                  "clicks even when the organic SERP is open.",
                  "",
                  "### Gates this scan cannot answer",
                  "",
                  "Two decisions are not in any feed and must be confirmed with "
                  "the network before a domain is bought:",
                  "",
                  "1. **Is the offer duration-based or buyer-qualified?** Only a "
                  "stated billable duration is verifiable from your own call log. "
                  "\"Booked appointment\" is the buyer's judgement, not a number.",
                  "2. **What hours does the buyer answer?** Emergency niches earn "
                  "at 2am. A 9-to-5 buyer drops exactly the traffic that converts "
                  "best.",
                  "",
                  "Search volume is the third gate this scan skips — run the "
                  "**Mode 5 Area Plan** workflow on the winning city with the "
                  "*broad* service (not a sub-service) and `min_area_volume: 20`."]
    else:
        lines += ["## Candidate cities (no SERP key — revenue side only)", "",
                  "| # | City | Niches | Top payout | Bundle | Pop | ZIPs |",
                  "|---|---|---|---|---|---|---|"]
        for i, c in enumerate(cands[:30], 1):
            ns = ", ".join(f"{n['niche']} ${n['payout']:.0f}" for n in c["niche_list"][:4])
            lines.append(f"| {i} | {c['city']}, {c['state']} | {ns} "
                         f"| ${c['top_payout']:.2f} | {c['bundle_value']:.0f} "
                         f"| {c['pop']:,} | {c['zips']} |")
    lines += ["", "---",
              "`opportunity = serp_score / 100 × bundle_value`. An open SERP on a "
              "cheap payout and a rich payout behind six dedicated pages both score "
              "low, which is the point."]
    with open("opportunity_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("── STAGE 5: written ───────────────────────────────────")
    print("   📄 opportunities.json · opportunities.csv · opportunity_report.md")


def main():
    print("\n🔍 OPPORTUNITY FINDER\n" + "=" * 55)
    meta, rows = pull_coverage()
    if not rows:
        print("❌ no coverage rows — nothing to do")
        write(meta, [], [])
        return
    pricing = price_modes(rows)
    cands   = shortlist(rows, pricing)
    scored  = scan(cands)
    write(meta, cands, scored, pricing)

    if scored:
        print("\n🏆 TOP 10")
        for i, o in enumerate(scored[:10], 1):
            print(f"  {i:2}. {o['opportunity']:6.0f}  SERP {o['serp_score']:3}  "
                  f"${o['payout']:7.2f}  {o['query']}")
    elif cands:
        print("\n🏆 TOP 10 CITIES (revenue side only)")
        for i, c in enumerate(cands[:10], 1):
            print(f"  {i:2}. {c['bundle_value']:6.0f}  {c['city']}, {c['state']}  "
                  f"{len(c['niche_list'])} niches  top ${c['top_payout']:.2f}")
    print()


if __name__ == "__main__":
    main()
