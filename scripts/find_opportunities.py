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
    STAGE 3.5 search demand           free      (Keyword Planner; MIN_VOLUME)
    STAGE 4  SERP scan                COSTS     (SerpApi, hard-capped, cached)
    STAGE 5  verdict + launch plan    free      (GO / WATCH / STOP, builder forms)

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

  SERP_RESERVE       default 10 — credits never spent, kept for hand checks
  SERP_CACHE_DAYS    default 30 — a cached SERP younger than this is free

Out: opportunities.json, opportunities.csv, opportunity_report.md,
     launch_plan.json (the GO cities with every form filled in)
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
# Deep-check mode: "Lawton OK, Daytona Beach FL". Only these cities go past
# stage 3, so subs_per_niche 3 spends its credits on the WATCH cities a broad
# run found, not on the head of a list that is already known to be STOP.
CITIES     = {tuple(x.strip().rsplit(" ", 1)) for x in os.environ.get("CITIES", "").split(",")
              if len(x.strip().rsplit(" ", 1)) == 2}
CITIES     = {(c.lower(), st.upper()) for c, st in CITIES}
MAX_SERP   = int(os.environ.get("MAX_SERP_CHECKS", "120") or 120)
SERP_KEY   = os.environ.get("SERPAPI_API_KEY", "").strip()
SERP_GL    = os.environ.get("SERP_GL", "us").strip() or "us"
# "location" (SerpApi resolves the place name) or "uule" (Google's own
# encoding, no lookup). Never both — see serp().
SERP_LOC_MODE = os.environ.get("SERP_LOC_MODE", "location").strip().lower()
# How many raw SerpApi responses to write to serp_debug.json. The scan's
# scores disagreed with four hand-checked SERPs in a row, and a score cannot
# show why — only the response can.
SERP_DEBUG_N  = int(os.environ.get("SERP_DEBUG_N", "3") or 3)
# How the SERP budget is spent. 1 niche × 3 subs = a deep read on each city's
# best offer. 3 niches × 1 sub = a bundle read — is this city open across
# several offers, or only one? Both matter, at different points.
NICHES_PER_CITY = int(os.environ.get("NICHES_PER_CITY", "1") or 1)
SUBS_PER_NICHE  = int(os.environ.get("SUBS_PER_NICHE", "3") or 3)
# Demand gate (free — Google Ads Keyword Planner, not SerpApi). A city whose
# broad "{trade} {city}" search is under this is dropped before any SERP
# credit is spent on it. 0 = measure and report, drop nothing.
MIN_VOLUME      = int(os.environ.get("MIN_VOLUME", "0") or 0)
# Credits the scan leaves on the account. The cross-check that follows every
# run — typing the top cities into Google by hand, or a Difficulty run on one
# of them — needs a few, and a scan that spends the balance to zero leaves
# nothing to confirm its own answer with.
SERP_RESERVE    = int(os.environ.get("SERP_RESERVE", "10") or 0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serp_client  # noqa: E402  (shared cache + balance, see that file)

# ── Sub-services per niche ────────────────────────────────────────────────
# In a metro the head term is always taken, and these are the queries an
# unranked site can enter on. In a town of 20-80k it is the other way round:
# nearly all the demand is the head term ("plumber kingman" 880/mo, every
# Kingman sub-service 0-10), so the scan tests BROAD[niche] first (see
# STAGE 3.5) and these after it.
# ─────────────────────────────────────────────────────────────────────────────
# SUB-SERVICES — from 5,000+ real calls, not from guesses
#
# These used to be my own list of plausible-sounding terms. They are now the
# specific services the mentor's Call Intelligence recorded across 20 niches,
# ordered by EARNING POWER (call volume x the share of those calls that
# actually paid), and rewritten from taxonomy labels into the phrasing someone
# would type into Google.
#
# The guessed list was wrong in both directions. It led with "hydro jetting",
# "sump pump repair" and "frozen pipe repair"; the call data puts leak
# detection, drain cleaning and sewer line repair at the top, and shows
# "drain snaking" and "sewer backup" converting at 100% while sump pumps paid
# on 18% of 11 calls. A term nobody rings about cannot be rescued by a weak
# SERP, so the SERP budget should never have been spent on it.
#
# The number in each comment is (calls, % of those calls that paid).
SUB_SERVICES = {
    # 1,064 calls · 79% paid · 45% urgent — the strongest Call niche on both feeds
    "Plumbing": [
        "leak detection",            # 119, 77%
        "drain cleaning",            #  56, 93%
        "sewer line repair",         #  44, 93%
        "clogged drain repair",      #  45, 78%
        "water heater leak repair",  #  48, 69%
        "faucet repair",             #  44, 82%
        "slab leak repair",          #  33, 85%
        "water line repair",         #  28, 86%
        "toilet repair",             #  32, 75%
        "sewer backup cleanup",      #  19, 100%
        "drain snaking",             #  20, 100%
        "ceiling leak repair",       #  20, 85%
        "tankless water heater repair",  # 20, 90%
        "water softener installation",   # 23, 91%
    ],
    # 274 calls · 72% paid — highest Call median payout ($38.06)
    "HVAC": [
        "ac repair",                 # 41, 76%
        "hvac tune up",              # 37, 76%
        "mini split repair",         # 44, 59%
        "ac not cooling",            # 18, 83%
        "hvac replacement",          # 33, 55%
        "furnace repair",            # 12, 83%
        "central ac repair",         #  7, 86%
        "air duct cleaning",         #  4, 100%
        "ac drain line clog",        #  5, 100%
    ],
    # 159 calls · 61% paid · 32,251 ZIPs — widest Call coverage
    "Roofing": [
        "roof leak repair",          # 37, 97%
        "roof repair",               # 34, 50%
        "roof replacement",          # 16, 75%
        "roof inspection",           # 15, 60%
        "shingle repair",            # 10, 80%
        "missing shingle repair",    #  3, 100%
        "tile roof replacement",     #  3, 100%
    ],
    # 109 calls · 81% paid · 49% booked — best conversion of any niche
    "Electrical": [
        "outlet repair",             # 17, 100%
        "house rewiring",            # 13, 69%
        "light fixture installation",# 10, 80%
        "electrical panel repair",   #  4, 50%
        "ev charger installation",   #  4, 100%
        "partial power outage",      #  3, 100%
        "range wiring",              #  5, 100%
    ],
    # 1,115 calls but only 51% paid / 15% booked, and a FLAT $42.50 everywhere
    "Pest Control": [
        "rodent control",            # 109, 59%
        "wasp nest removal",         #  84, 61%
        "ant control",               #  64, 63%
        "cockroach exterminator",    #  41, 66%
        "carpenter ant treatment",   #  23, 74%
        "rodent droppings cleanup",  #  21, 71%
        "spider control",            #  27, 52%
        "termite treatment",         #  40, 35%
    ],
    # CPL, median $205 — by far the highest payout in the feed
    "Water Damage": [
        "ceiling water damage repair",  # 14, 86%
        "water damage restoration",     #  3, 100%
        "mold remediation",             # 11, 73%
        "mold inspection",              #  9, 44%
    ],
    "Mold Removal": [
        "mold remediation", "mold inspection", "black mold removal",
        "attic mold removal", "crawl space mold removal",
    ],
    # 1,056 calls · median payout $9.63 — the clearest volume trap in the feed
    "Tree Services": [
        "tree removal",              # 195, 71%
        "tree trimming",             # 168, 67%
        "storm damage tree removal", #  88, 75%
        "stump grinding",            #  51, 84%
        "tree branch removal",       #  78, 68%
        "emergency tree removal",    #  17, 88%
        "land clearing",             #  13, 85%
    ],
    "Gutters": [
        "gutter cleaning",           # 36, 42%
        "gutter repair",             # 13, 77%
        "ice dam removal",           # 30, 30%
        "gutter replacement",        #  6, 67%
        "gutter guard installation", #  6, 33%
    ],
    "Painting": [
        "interior painting",         # 23, 78%
        "exterior painting",         # 16, 75%
        "cabinet painting",          #  3, 100%
        "lead paint removal",        #  3, 100%
        "deck staining",
    ],
    "Landscaping": [
        "lawn mowing",               # 39, 62%
        "weed control",              # 23, 87%
        "hedge trimming",            # 18, 72%
        "sprinkler repair",          # 11, 82%
        "yard cleanup",              # 13, 77%
        "mulch installation",        #  6, 100%
    ],
    # 1,148 calls — the MOST of any niche — on a median payout of $6.88
    "Appliance": [
        "refrigerator repair", "washer repair", "dryer repair",
        "dishwasher repair", "oven repair",
    ],
    "Garage Door": [
        "garage door repair", "garage door spring replacement",
        "garage door opener repair", "garage door off track",
    ],
    "Foundation Repair": [
        "foundation repair", "foundation crack repair",
        "basement wall repair", "house leveling",
    ],
    "Waterproofing": [
        "basement waterproofing", "crawl space encapsulation",
        "french drain installation", "sump pump installation",
    ],
    "Siding": [
        "siding repair", "siding replacement", "vinyl siding installation",
    ],
    "Bathroom Remodeling": [
        "bathroom remodel", "tub to shower conversion", "walk in shower installation",
    ],
    "Kitchen": [
        "kitchen remodel", "kitchen cabinet refacing", "countertop installation",
    ],
    "Deck": ["deck repair", "deck building", "deck staining"],
    "Solar": ["solar panel installation", "solar panel repair"],
    "Fire Damage Removal": [
        "fire damage restoration", "smoke damage cleanup", "soot removal",
    ],
    "Biohazard": [
        "biohazard cleanup", "crime scene cleanup", "hoarding cleanup",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# NICHE ECONOMICS — what a call in this niche is actually worth
#
# revenue per call = median payout x the share of calls that actually pay.
#
# Both halves used to be a hardcoded table sitting next to a CSV holding the
# same numbers, which is two copies of one fact waiting to disagree. Now each
# half comes from the place that owns it:
#
#   median payout  LIVE from /api/niche_summary.json, so a rate change shows
#                  up on the next run with nothing to edit
#   paid %         data/call_intel/niches.csv, a dated snapshot of the Call
#                  Intelligence dashboard — it needs a login and is not an
#                  API, so it cannot be fetched (see that folder's README and
#                  extract_call_intel.js for the refresh)
#
# Reading the feed's `top_payout` as the payout is what this replaced: it is
# the single best ZIP in the country, and on it Plumbing reads $221.95 against
# a median of $34.38. The ranking that falls out is not the ranking by call
# volume — the three highest-volume niches in the feed, Appliance (1,148
# calls), Pest Control (1,115) and Tree Services (1,056), come out at $4.88,
# $21.68 and $6.64 a call.

# The two feeds name some niches differently.
_CI_ALIAS = {
    "hvac": "HVAC",                 # .title() gives "Hvac"; the feed says HVAC
    "appliance repair": "Appliance",
    "lawncare & landscaping": "Landscaping",
    "water damage": "Water Damage",
    "pest control": "Pest Control",
    "tree services": "Tree Services",
    "garage door": "Garage Door",
}

# Below this, a SERP credit spent on the niche cannot pay for itself: even a
# wide-open first page only wins calls worth a few dollars each.
MIN_REV_PER_CALL = float(os.environ.get("MIN_REV_PER_CALL", "15") or 15)

_PAID_PCT = {}          # coverage-feed niche name -> paid %
# How many survived each stage, for the report's funnel. Without it a run that
# ends in "0 GO" cannot say whether the market is closed or the filters were.
_FUNNEL = {}
_MEDIAN = {}            # (niche, ptype) -> median payout, filled in stage 1


def load_call_intel():
    """paid % per niche from the snapshot CSV. Fail-open: without it the
    economics gate simply does not fire, exactly as before it existed."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "data", "call_intel", "niches.csv")
    if not os.path.isfile(path):
        print(f"   ⚠️ {os.path.basename(path)} missing — economics gate off")
        return
    with open(path, encoding="utf-8") as fh:
        # The snapshot is comma-separated. Read with delimiter="|" every row
        # was one unsplit column, no niche ever matched, and the gate printed
        # "paid% for 0 niches" and let Appliance ($4.88 a call) through on
        # every run. Take the delimiter from the header instead of assuming.
        head = fh.readline()
        fh.seek(0)
        delim = "|" if head.count("|") > head.count(",") else ","
        for row in csv.DictReader(fh, delimiter=delim):
            raw = (row.get("niche") or "").strip().lower()
            if not raw:
                continue
            name = _CI_ALIAS.get(raw, raw.title())
            try:
                _PAID_PCT[name] = int(row["paid_pct"])
            except (KeyError, TypeError, ValueError):
                continue
    print(f"   📞 call intel: paid% for {len(_PAID_PCT)} niches")
    if not _PAID_PCT:
        print("   ⚠️ call intel parsed to nothing — economics gate is OFF this run")


def revenue_per_call(niche, ptype):
    """What one call is worth, or None when either half is unknown."""
    med = _MEDIAN.get((niche, ptype))
    paid = _PAID_PCT.get(niche)
    if med is None or paid is None:
        return None
    return med * paid / 100.0


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
               "contractorplus.app", "fixr.com", "mapquest.com",
               # plumb-pa-ga-03: local.yahoo.com and a todayshomeowner.com
               # "best plumbers in Ephrata" list were booked as dedicated pages.
               # Both are listings — an opening, not a competitor.
               "yahoo.com", "superpages.com", "chamberofcommerce.com",
               "birdeye.com", "hotfrog.com", "merchantcircle.com",
               "todayshomeowner.com", "bobvila.com", "thisoldhouse.com",
               "consumeraffairs.com", "forbes.com", "threebestrated.com",
               "bestprosintown.com", "nextdoor.com",
               # electrical run: job boards, suppliers, chambers and city
               # guides were booked as "dedicated" pages. Lawton OK read as
               # 3 dedicated when two of them were indeed.com and an
               # electrical supply store — a competitor count that decides
               # STOP has to count competitors only.
               "indeed.com", "glassdoor.com", "ziprecruiter.com", "simplyhired.com",
               "craigslist.org", "namesandnumbers.com", "citylocal101.com",
               "homeguide.com", "diamondcertified.org", "orangebook.com",
               "rexelusa.com", "graybar.com", "chamber", "askparkcity.com",
               "loc8nearme.com", "yellowbook.com")
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

# Words that make a city domain a trade domain (see the EMD check).
_TRADE_HOST = ("plumb", "drain", "rooter", "sewer", "leak", "pipe", "waterheater",
               "hvac", "heat", "cool", "aircondition", "furnace", "electric", "roof",
               "pest", "termite", "garage", "door", "tree", "mold", "water",
               "restor", "remodel", "paint", "gutter", "appliance", "repair",
               "service", "handyman", "contractor", "mechanical")

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


# Google Ads geo target ids for the US states, from Google's own geotargets
# file (geotargets-2026-08-12.csv, Target Type = State). Resolving the state by
# NAME is what broke Georgia: the Planner's first suggestion for "Georgia" is
# the country (id 2268), so plumb-pa-ga-03 measured "plumber buford ga" among
# Georgians in Tbilisi, found almost nothing, and dropped every GA city before
# a single SERP was read. An id cannot be misread.
STATE_GEO_ID = {
    "AK": "21132", "AL": "21133", "AR": "21135", "AZ": "21136", "CA": "21137", "CO": "21138", "CT": "21139",
    "DC": "21140", "DE": "21141", "FL": "21142", "GA": "21143", "HI": "21144", "IA": "21145", "ID": "21146",
    "IL": "21147", "IN": "21148", "KS": "21149", "KY": "21150", "LA": "21151", "MA": "21152", "MD": "21153",
    "ME": "21154", "MI": "21155", "MN": "21156", "MO": "21157", "MS": "21158", "MT": "21159", "NC": "21160",
    "ND": "21161", "NE": "21162", "NH": "21163", "NJ": "21164", "NM": "21165", "NV": "21166", "NY": "21167",
    "OH": "21168", "OK": "21169", "OR": "21170", "PA": "21171", "RI": "21172", "SC": "21173", "SD": "21174",
    "TN": "21175", "TX": "21176", "UT": "21177", "VA": "21178", "VT": "21179", "WA": "21180", "WI": "21182",
    "WV": "21183", "WY": "21184",
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

    # Median payout per niche, live. meta.json only carries top_payout, which
    # is one ZIP and six times the median on Plumbing.
    summary = j(f"{BASE}/api/niche_summary.json")
    for row in ((summary or {}).get("niches") or []):
        try:
            _MEDIAN[(row["niche"], row["payout_type"])] = float(row["median"])
        except (KeyError, TypeError, ValueError):
            continue
    if _MEDIAN:
        print(f"   💵 median payout for {len(_MEDIAN)} niche/type pairs")
    load_call_intel()

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
    _FUNNEL["coverage rows"] = len(rows)
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
    drop_econ = {}
    keep = []
    for r in rows:
        if not r["city"] or not r["niche"]:
            continue
        if PAYOUT_T != "both" and (r["ptype"] or "") != PAYOUT_T:
            continue
        if r["payout"] < MIN_PAYOUT:
            continue
        # Niche filter before the economics gate, so the gate's report lists
        # only niches this run asked about, not every cheap niche in the feed.
        if NICHES and r["niche"] not in NICHES:
            continue
        if CITIES and (r["city"].lower(), r["state"]) not in CITIES:
            continue
        # Economics gate. MIN_PAYOUT only asks what the buyer pays; this asks
        # what a call is actually WORTH once the share that never pays is taken
        # out. Appliance clears a $35 payout filter on its best ZIPs while its
        # median is $6.88 and it is the highest-volume niche in the feed — the
        # exact shape that wastes a SERP budget. Niches with no call data pass
        # through untouched, so this can only ever remove a known-bad one.
        # Call rows only: paid % is the share of CALLS that paid. Applied to a
        # CPL row it would judge a lead by a call statistic.
        _rev = revenue_per_call(r["niche"], r["ptype"]) if r["ptype"] == "Call" else None
        if _rev is not None and _rev < MIN_REV_PER_CALL:
            d = drop_econ.setdefault(r["niche"], {"rows": 0, "rev": _rev})
            d["rows"] += 1
            continue
        if not (MIN_POP <= r["pop"] <= MAX_POP):
            continue
        keep.append(r)
    print(f"   payout ≥ ${MIN_PAYOUT:g} · rev/call ≥ ${MIN_REV_PER_CALL:g} "
          f"· pop {MIN_POP:,}-{MAX_POP:,} · type {PAYOUT_T}")
    # The old line looked the median up under PAYOUT_T, which is "both" on a
    # both-types run — a KeyError the moment the gate first fired.
    for _n, _d in sorted(drop_econ.items(), key=lambda kv: -kv[1]["rows"]):
        print(f"   ⛔ {_n:<16} {_d['rows']:>7,} rows dropped — "
              f"${_d['rev']:.2f}/call ({_PAID_PCT.get(_n, '?')}% of calls paid)")
    _FUNNEL["economics dropped"] = {n: round(d["rev"], 2) for n, d in drop_econ.items()}
    print(f"   ✅ {len(rows):,} → {len(keep):,} rows\n")
    _FUNNEL["rows after payout/pop filter"] = len(keep)

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
    _FUNNEL["candidate cities"] = len(out)
    return out


# ══════════════════════════════════════════════════════════════════
# STAGE 3.5 — demand (free: Google Ads Keyword Planner)
# ══════════════════════════════════════════════════════════════════
# What people in a small town actually type is the trade, not the job:
# Arizona's matrix has "plumber kingman" at 880/mo and every Kingman
# sub-service at 0-10. Scanning "leak detection Kingman AZ" measured a SERP
# nobody sees. The broad term is what the demand check sums and what the SERP
# scan tests first.
BROAD = {
    "Plumbing": "plumber", "HVAC": "ac repair", "Electrical": "electrician",
    "Roofing": "roofer", "Pest Control": "pest control", "Appliance": "appliance repair",
    "Gutters": "gutter cleaning", "Garage Door": "garage door repair",
    "Tree Services": "tree service", "Water Damage": "water damage restoration",
    "Bathroom Remodeling": "bathroom remodel", "Painting": "painters",
    "Mold Removal": "mold removal", "Foundation Repair": "foundation repair",
    "Siding": "siding contractor", "Kitchen": "kitchen remodel", "Deck": "deck builder",
    "Waterproofing": "basement waterproofing", "Fire Damage Removal": "fire damage restoration",
    "Biohazard": "biohazard cleanup", "Solar": "solar installer",
}


def demand(cands):
    """Monthly searches for each city's broad trade term; drop below MIN_VOLUME.

    Fail-open: without Google Ads credentials, or on any API error, every
    candidate goes through unmeasured, exactly as before.
    """
    print("── STAGE 3.5: search demand (Keyword Planner) ─────────")
    if not os.environ.get("GOOGLE_ADS_CUSTOMER_ID"):
        print("   ℹ️ no Google Ads credentials — demand not measured.\n")
        return cands
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from city_service_volume import volumes
    except Exception as e:
        print(f"   ⚠️ volume module unavailable ({e}) — demand not measured.\n")
        return cands
    by_state = {}
    for c in cands:
        term = BROAD.get(c["top_niche"])
        if not term:
            continue
        c["_q"] = [f"{term} {c['city']} {c['state']}".lower(), f"{term} {c['city']}".lower()]
        by_state.setdefault(c["state"], []).append(c)
    measured = 0
    for n_st, (st, group) in enumerate(by_state.items()):
        qs = sorted({q for c in group for q in c["_q"]})
        geo = STATE_GEO_ID.get(st) or f"{STATE_NAMES.get(st, st)}, United States"
        # Paced, and one patient retry. The all-states electrical run asked
        # for 20 states back to back and the Planner answered KS, MO and CO
        # with 429 "Resource has been exhausted"; their cities went to the
        # SERP stage unmeasured and spent credits on towns with no known
        # demand. Planner calls are free -- waiting costs only seconds.
        if n_st:
            time.sleep(2)
        vol = volumes(qs, geo)
        if vol is None:
            print(f"   ⏳ {st}: Planner refused — waiting 30s and asking once more")
            time.sleep(30)
            vol = volumes(qs, geo)
        if vol is None:
            print(f"   ⚠️ {st}: volume lookup failed — kept unmeasured")
            continue
        for c in group:
            c["volume"] = max(vol.get(q, 0) for q in c["_q"])
            measured += 1
    keep = [c for c in cands if c.get("volume") is None or c["volume"] >= MIN_VOLUME]
    # Expected revenue first: payout alone put 1-ZIP places like Waddell at the
    # top; searches x payout puts the markets that actually ring first.
    keep.sort(key=lambda c: -((c.get("volume") or 0) * c["bundle_value"]))
    print(f"   measured {measured} cities · min {MIN_VOLUME}/mo · "
          f"{len(cands)} → {len(keep)} kept")
    _FUNNEL["cities with enough searches"] = len(keep)
    for c in keep[:10]:
        print(f"      {c.get('volume', '?'):>6}/mo  ${c['top_payout']:.0f}  {c['city']}, {c['state']}")
    print()
    return keep


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
    Try `location`, fall back to `uule`.

    SerpApi resolves `location` against its own place database, and the
    coverage feed spells plenty of towns differently to it — "Lees Summit"
    against Lee's Summit, "Ft Mitchell" against Fort Mitchell, "Saint Peters"
    against St. Peters. Those come back as `Unsupported location`, and simply
    dropping them loses real candidates for a spelling difference.

    `uule` is Google's own encoding and needs no lookup, so it answers for any
    place name. It is the fallback rather than the default because when
    SerpApi *does* know a city, its own resolution is the more reliable of the
    two. A rejected request is not billed, so the retry costs one search, not
    two.
    """
    data = _serp_once(query, location, SERP_LOC_MODE)
    if data is None and location and SERP_LOC_MODE == "location" and _LAST_UNSUPPORTED:
        return _serp_once(query, location, "uule")
    return data


def _serp_once(query, location, mode):
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
        # ONE of these, never both. SerpApi treats `location` and `uule` as
        # mutually exclusive and answers a request carrying both with a flat
        # HTTP 400 — a run that sent both failed all 200 queries and scored
        # nothing at all.
        if mode == "uule":
            params["uule"] = _uule(location)
        else:
            params["location"] = location
    global _LAST_UNSUPPORTED
    _LAST_UNSUPPORTED = False
    # Through the shared client: a SERP already read by any workflow in the
    # last SERP_CACHE_DAYS comes back from disk and costs nothing.
    data, err, _cached = serp_client.fetch(params)
    if data is not None:
        return data
    if err and "unsupported" in err.lower() and "location" in err.lower():
        # Recoverable: retried with uule by the caller, so it is not a
        # real failure and should not be counted as one.
        _LAST_UNSUPPORTED = True
        return None
    _serp_err(err or "no response")
    return None


_SERP_ERRS = {}
_LAST_UNSUPPORTED = False


_QUOTA_HIT = []


def _serp_err(msg):
    """Print each distinct failure once, with a count, instead of 200 lines."""
    # A free SerpApi plan is 250 searches a month, so running dry mid-scan is
    # an ordinary event, not an edge case. Every query after this point is
    # guaranteed to fail, so stage 4 stops and keeps what it already scored.
    low = msg.lower()
    if any(w in low for w in ("run out of searches", "ran out of searches",
                              "exceeded your", "account limit", "plan limit",
                              "searches left", "upgrade your plan")):
        _QUOTA_HIT.append(msg)
    _SERP_ERRS[msg] = _SERP_ERRS.get(msg, 0) + 1
    if _SERP_ERRS[msg] <= 2:
        print(f"      ⚠️ SERP failed: {msg}")
    elif _SERP_ERRS[msg] == 3:
        print(f"      ⚠️ (further identical failures suppressed: {msg})")


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

    # GUARD — is page one even about the service? hvac-az-01 ranked
    # "hvac tune up Scottsdale AZ" #1 on a page of tune.com, acousticguitar.com
    # and apps.apple.com, "ac repair Chandler AZ" #4 on gottman.com and
    # arpa-e.energy.gov, and Rio Rico, Sierra Vista and Cortaro all on the same
    # list of az.gov pages. None of those results mention air conditioning, so
    # none of them is a competitor, and a page with no competitors scored as
    # wide open. Google did not answer the query that was asked; refuse it.
    # Only the words that name the trade. "repair" and "tune" match
    # gottman.com's "repair attempts" and tune.com as happily as an AC page.
    _generic = {"repair", "repairs", "service", "services", "installation", "install",
                "replacement", "replace", "tune", "cost", "near", "company", "emergency",
                "maintenance", "inspection", "cleaning", "upgrade", "removal", "local",
                "house", "home", "residential", "partial"}
    _topic = {w for w in re.split(r"\W+", service.lower()) if len(w) > 3 and w not in _generic}
    if re.search(r"\b(ac|hvac|a/c)\b", service.lower()):
        _topic |= {"hvac", "air conditioning", "cooling", "heating", "air condition"}
    # The broad trade terms name the tradesman; the pages that answer them
    # name the trade. "plumber kingman" is answered by "Kingman Plumbing Co.",
    # and with only "plumber" to match, an ordinary local page one read as
    # off-topic and the city's most important query was thrown away.
    for _w, _alt in (("plumber", {"plumbing"}), ("electrician", {"electrical", "electric"}),
                     ("roofer", {"roofing", "roof"}), ("painters", {"painting", "painter"}),
                     ("installer", {"install"}), ("builder", {"build"})):
        if _w in _topic:
            _topic |= _alt
    # A job-level query is answered by pages that name the trade, not the job:
    # "house rewiring Lawton OK" came back as Code Electric's "Home Wiring
    # Services" and Sooner Services' "Electrical Repair" -- zero pages said
    # "rewiring", so the guard refused a perfectly local, on-topic SERP.
    _svc = service.lower()
    for _jobs, _trade in ((("outlet", "wiring", "panel", "breaker", "charger", "fixture",
                            "power outage", "range"), {"electric"}),
                          (("leak", "drain", "sewer", "faucet", "toilet", "water heater",
                            "water line", "softener", "pipe"), {"plumb"}),
                          (("roof", "shingle"), {"roof"})):
        if any(j in _svc for j in _jobs):
            _topic |= _trade
    _hits = sum(1 for r in results
                if any(t in f"{r.get('title', '')} {r.get('link', '')} {r.get('snippet', '')}".lower()
                       for t in _topic))
    if _topic and _hits < 3:
        return None
    # Same failure, different costume: hvac-midwest-01 put "ac repair Lees
    # Summit MO" first on seven YouTube videos, Wikipedia and acsaf.org. The
    # video titles say "AC repair", so the check above passes, but a page one
    # made of videos and encyclopaedias is Google answering a how-to, not a
    # local hire -- and it says nothing about who holds the local results.
    _media = sum(1 for r in results
                 if re.search(r"(youtube\.com|youtu\.be|wikipedia\.org|tiktok\.com|instagram\.com)",
                              str(r.get("link", "")).lower()))
    if _media >= 4:
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
    # One competitor is one competitor however many of its pages rank.
    # elec-deep-01 counted soonersvcs.com twice on "outlet repair Lawton OK"
    # (its service page and its Lawton area page) and turned one local firm
    # into the "2 dedicated" that means STOP.
    _dedicated_hosts = set()

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
        elif (any(b in bare for b in BIGBOX)
              or (any(n in bare for n in NATIONALS)
                  and not (city_slug in link or city_flat in link.replace("-", "")))):
            # Big-box retail is national even WITH the city in the URL:
            # homedepot.com/l/Lawton/OK/... is a store-locator page, and it
            # was booked as a dedicated competitor on "house rewiring Lawton".
            # A national brand with no city page is weak here — it ranks on
            # domain strength alone. But rotorooter.com/doverpa and
            # americanleakdetection.com/harrisburg ARE city pages, and this
            # elif was letting them skip the dedicated check entirely: the
            # single hardest occupant on the page booked the cheapest label.
            # Only the brand WITHOUT a city path takes this branch now.
            tally["national"] += 1; kinds.append("national brand")
        else:
            # An EMD is USUALLY also an exact-match page, so these are counted
            # together rather than as an either/or. The old elif chain let a
            # city EMD serving a dedicated page book the cheaper of the two
            # penalties and skip the expensive one.
            if _SUBDOMAIN_PSEO.match(bare) and city_slug in bare:
                tally["pseo"] += 1; kinds.append("pSEO subdomain")
            # A city name in the host is only an EMD when the host also names
            # the trade. hanover.com is an insurance company; it was booked as
            # a city EMD on "leak detection Hanover PA" and capped the score
            # at 25 on its own. lebanonpaplumbingguys.com is the real thing.
            if city_flat in flat and any(t in flat for t in _TRADE_HOST):
                tally["emd"] += 1; kinds.append("city EMD")
            # Requiring a service word in the title or URL was too strict.
            # jmlapp.com/city/willow-street is titled just "Willow Street" and
            # neffsvilleph.com/service-area/willow-street-pa says "Plumbing and
            # HVAC Service" — neither contains "leak", so both scored as
            # nothing while sitting on page one for "leak detection <city>".
            # Google already judged relevance by ranking them; the city in the
            # title or URL is the signal that the page was built FOR this city.
            _city_hit = (city_l in blob or city_slug in link
                         or city_flat in link.replace("-", ""))
            _path_hit = any(seg in link for seg in
                            ("/city/", "/cities/", "/service-area", "/service_area",
                             "/locations/", "/location/", "/areas/", "/areas-served",
                             "/plumber-", "/plumbers-"))
            if _city_hit and (any(w in blob for w in svc_words) or _path_hit
                              or city_l in title):
                if bare not in _dedicated_hosts:
                    tally["dedicated"] += 1
                _dedicated_hosts.add(bare)
                kinds.append("dedicated page")
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
            _subs = SUB_SERVICES.get(nrec["niche"], [])
            _b = BROAD.get(nrec["niche"])
            # Broad term FIRST, even when the list already holds it further
            # down. Water Damage lists "water damage restoration" second, so
            # the old "not in" test left "ceiling water damage repair Lawton
            # OK" as the one query run -- Google answered it with Nike videos
            # and Wikipedia, and the credit bought nothing.
            if _b:
                _subs = [_b] + [x for x in _subs if x != _b]
            for si, sub in enumerate(_subs[:SUBS_PER_NICHE]):
                passes.append((ni * 100 + si, c, nrec["niche"], nrec["payout"],
                               nrec.get("pricing", "?"), sub))
    passes.sort(key=lambda p: p[0])

    # The cap is on CREDITS, not queries. Cached SERPs are free, so a re-run
    # with a higher cap pays only for the cities the last run never reached.
    # The account balance is read first (free) so the scan can never be the
    # thing that empties it.
    budget = MAX_SERP
    left = serp_client.searches_left(SERP_KEY)
    if left is not None:
        usable = max(0, left - SERP_RESERVE)
        print(f"   💳 SerpApi balance {left} · reserve {SERP_RESERVE} · usable {usable}")
        if usable < budget:
            print(f"   ⚠️ cap lowered {budget} → {usable} to keep the reserve")
            budget = usable
    else:
        print("   💳 SerpApi balance unreadable — using the cap as given")
    # Several cities share a spelling across states only in theory; the same
    # (query, location) twice in one run is always a wasted credit.
    _seen, jobs = set(), []
    for p in passes:
        k = (p[5], p[1]["city"], p[1]["state"])
        if k not in _seen:
            _seen.add(k)
            jobs.append(p[1:])
    print(f"   {len(jobs)} queries queued · credit cap {budget} · "
          f"{NICHES_PER_CITY} niche(s) × {SUBS_PER_NICHE} sub(s) per city")
    if _MISSING_SUBS:
        print(f"   ⚠️ no sub-services defined for {sorted(_MISSING_SUBS)} — "
              f"those cities were skipped. Add them to SUB_SERVICES.")

    found, raw_dump = [], []
    _tested = set()
    for i, (c, niche_name, niche_payout, niche_pricing, sub) in enumerate(jobs, 1):
        if serp_client.stats()["spent"] >= budget:
            _untested = len({(x[0]["city"], x[0]["state"]) for x in jobs[i - 1:]} - _tested)
            print(f"   ⏹️ credit cap {budget} reached after {i - 1} queries — "
                  f"{_untested} cities untested. Re-run with a higher cap: the "
                  f"{i - 1} already read come from cache for free.")
            break
        _tested.add((c["city"], c["state"]))
        query = f"{sub} {c['city']} {c['state']}"
        loc   = f"{c['city']}, {STATE_NAMES.get(c['state'], c['state'])}, United States"
        _spent_before = serp_client.stats()["spent"]
        data  = serp(query, loc)
        c.setdefault("_scanned", []).append(sub)
        if _QUOTA_HIT:
            print(f"   ⏹️ SerpApi quota exhausted after {i} queries — "
                  f"{len(found)} scored and kept. ({_QUOTA_HIT[0]})")
            break

        # Keep the first few responses verbatim. Four hand-checks in a row
        # found heavy occupation — pSEO subdomains, dedicated pages, city
        # domains — where the scan reported none, and the classifier scores
        # those same result sets correctly when handed them directly. So the
        # disagreement is in what comes back from the API, and that cannot be
        # diagnosed from a score. This writes down what actually arrived.
        if data and len(raw_dump) < SERP_DEBUG_N:
            raw_dump.append({
                "query": query,
                "location_sent": loc,
                "search_parameters": data.get("search_parameters"),
                "search_information": data.get("search_information"),
                "organic_results": [
                    {"position": r.get("position"), "title": r.get("title"),
                     "link": r.get("link")}
                    for r in (data.get("organic_results") or [])
                ],
                "local_results_count": len(
                    (data.get("local_results") or {}).get("places", [])
                    if isinstance(data.get("local_results"), dict)
                    else (data.get("local_results") or [])),
            })

        res = score_serp(data, sub, c["city"])
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
            "volume": c.get("volume"),
            # openness x payout x searches: the monthly money a page here can reach
            "value": round(sc / 100 * c["bundle_value"] * (c.get("volume") or 0), 1),
        })
        if _QUOTA_HIT:
            print(f"   ⏹️ SerpApi quota exhausted after {i} queries — "
                  f"{len(found)} scored and kept. ({_QUOTA_HIT[0]})")
            break

        # Fail fast on a broken request. The last run sent 200 queries that
        # were all rejected for the same reason and reported "0 scored" at the
        # end — the misconfiguration was knowable after the first ten.
        if i >= 10 and not found and sum(_SERP_ERRS.values()) >= i:
            print(f"   ❌ first {i} queries all failed — aborting rather than "
                  f"spending the rest of the budget on the same error.")
            break

        if i % 10 == 0 or i == len(jobs):
            print(f"   🔎 {i}/{len(jobs)} · {serp_client.stats()['spent']} credits · best so far "
                  f"{max((f['opportunity'] for f in found), default=0):.0f}")
        if serp_client.stats()["spent"] > _spent_before:
            time.sleep(0.7)   # pace live calls only; cache hits need none

    if raw_dump:
        with open("serp_debug.json", "w", encoding="utf-8") as f:
            json.dump(raw_dump, f, indent=2)
        print(f"   🧪 wrote serp_debug.json — {len(raw_dump)} raw responses")

    found.sort(key=lambda f: (-(f["value"] or 0), -f["opportunity"]))
    print(f"   ✅ {len(found)} scored · {serp_client.summary_line()}")
    if _SERP_ERRS:
        print("   Failure summary:")
        for msg, n in sorted(_SERP_ERRS.items(), key=lambda kv: -kv[1]):
            print(f"      {n:>4}×  {msg}")
    print()
    return found


# ══════════════════════════════════════════════════════════════════
# STAGE 5a — verdict per city
# ══════════════════════════════════════════════════════════════════
# The report used to print the rules ("STOP on any EMD…") and leave the reader
# to apply them to thirty rows by eye. Every one of those rules is mechanical,
# so the scan applies them itself and says GO, WATCH or STOP with the reason.
#
# A city is judged on its WORST scored query, not its best. One open
# sub-service under a head term held by four dedicated pages is not an open
# market — it is one page's worth of traffic. Conservative on purpose: a
# false GO costs a domain and a build, a false STOP costs nothing.
GO_SCORE    = int(os.environ.get("GO_SCORE", "60") or 60)
GO_VOLUME   = int(os.environ.get("GO_VOLUME", "100") or 100)


def verdict(o):
    """(label, [reasons]) for one scored query."""
    b = o["serp_breakdown"]
    why = []
    if b.get("emd"):
        why.append(f"{b['emd']} city EMD on page one")
    if b.get("pseo"):
        why.append(f"{b['pseo']} programmatic subdomain(s)")
    if b.get("dedicated", 0) >= 2:
        why.append(f"{b['dedicated']} dedicated {o['niche'].lower()} pages")
    if b.get("pack_median_reviews", 0) >= 500:
        why.append(f"map pack at {b['pack_median_reviews']} reviews")
    if why:
        return "STOP", why
    vol = o.get("volume")
    if b.get("dedicated", 0) == 1:
        why.append("1 dedicated page already")
    if b.get("pack_median_reviews", 0) >= 200:
        why.append(f"map pack at {b['pack_median_reviews']} reviews")
    if o["serp_score"] < GO_SCORE:
        why.append(f"SERP {o['serp_score']} < {GO_SCORE}")
    if vol is None:
        why.append("search volume not measured")
    elif vol < GO_VOLUME:
        why.append(f"only {vol} searches/mo")
    if why:
        return "WATCH", why
    return "GO", [f"SERP {o['serp_score']}, 0 dedicated, {vol}/mo"]


_RANK = {"STOP": 0, "WATCH": 1, "GO": 2}


def city_verdicts(scored):
    """Roll the per-query verdicts up to one line per city (worst query wins)."""
    cities = {}
    for o in scored:
        o["verdict"], o["why"] = verdict(o)
        k = (o["city"], o["state"])
        c = cities.get(k)
        if c is None:
            cities[k] = c = {
                "city": o["city"], "state": o["state"], "county": o["county"],
                "population": o["population"], "niche": o["niche"],
                "payout": o["payout"], "volume": o.get("volume"),
                "bundle_value": o["bundle_value"], "verdict": "GO", "why": [],
                "queries": [], "best_value": 0,
            }
        c["queries"].append({"query": o["query"], "serp_score": o["serp_score"],
                             "verdict": o["verdict"]})
        c["best_value"] = max(c["best_value"], o.get("value") or 0)
        if _RANK[o["verdict"]] < _RANK[c["verdict"]]:
            c["verdict"], c["why"] = o["verdict"], [f"`{o['query']}`: " + "; ".join(o["why"])]
        elif o["verdict"] == c["verdict"] and o["verdict"] != "GO":
            c["why"].append(f"`{o['query']}`: " + "; ".join(o["why"]))
        elif o["verdict"] == "GO" and not c["why"]:
            c["why"] = o["why"]
    out = list(cities.values())
    out.sort(key=lambda c: (-_RANK[c["verdict"]], -c["best_value"], -c["payout"]))
    return out


# ══════════════════════════════════════════════════════════════════
# STAGE 5b — launch plan (the handoff to the website builder)
# ══════════════════════════════════════════════════════════════════
# A GO row is worth nothing until it is a site. The path from here is always
# the same three forms, and every value in them is already known at this
# point — so the scan fills them in rather than leaving them to be retyped
# (and mistyped: a sub-service as primary_service measures the wrong demand,
# a city-scoped target_location misses every neighbouring town).
#
#   1. keyword tool · Mode 5 Area Plan   → areas + real keywords (free)
#   2. website builder · Mode 5          → the state site, one page per area
#   3. website builder · Mode 2 (later)  → service pages under the best hubs,
#                                          only once GSC shows impressions
TRADE_WORD = {
    "Plumbing": "Plumber", "HVAC": "HVAC", "Electrical": "Electrician",
    "Roofing": "Roofer", "Pest Control": "Pest Control", "Garage Door": "Garage Door",
    "Water Damage": "Water Damage", "Tree Services": "Tree Service",
}


def launch_plan(city_rows):
    plans = []
    by_state = {}
    for c in city_rows:
        if c["verdict"] in ("GO", "WATCH"):
            by_state.setdefault((c["state"], c["niche"]), []).append(c)
    for (st, niche), rows in by_state.items():
        go = [r for r in rows if r["verdict"] == "GO"]
        if not go:
            continue
        state_name = STATE_NAMES.get(st, st)
        term = BROAD.get(niche, niche.lower())
        trade = TRADE_WORD.get(niche, niche)
        names = [r["city"] for r in go] + [r["city"] for r in rows if r["verdict"] == "WATCH"]
        # One city on its own is an area page on a state site, not a site: a
        # single-town domain has nowhere to grow when the next open town turns
        # up one county over. Three or more open towns is the Arizona shape.
        shape = ("state site — Mode 5 area pages (the arizonahomeservicepros.com pattern)"
                 if len(names) >= 3 else
                 f"add {', '.join(names)} as area page(s) on a {state_name} state site")
        plans.append({
            "state": st, "state_name": state_name, "niche": niche,
            "go_cities": [r["city"] for r in go],
            "watch_cities": [r["city"] for r in rows if r["verdict"] == "WATCH"],
            "monthly_searches": sum((r["volume"] or 0) for r in rows),
            "best_payout": max(r["payout"] for r in rows),
            "shape": shape,
            "manual_check": [
                "https://www.google.com/search?" + urllib.parse.urlencode(
                    {"q": f"{term} {r['city']} {st}"}) for r in go[:5]],
            "forms": {
                "1_keyword_tool_mode5_area_plan": {
                    "business_name": f"{state_name} {trade} Pros",
                    "niche_description": f"{niche.lower()} referral service connecting homeowners with licensed local pros",
                    "target_location": f"{state_name}, United States",
                    "primary_service": term,
                    "min_area_volume": "20",
                    "max_areas": "",
                    "extra_areas": ", ".join(names),
                },
                "2_builder_mode5": {
                    "mode": "5",
                    "business_name": f"{state_name} {trade} Pros",
                    "industry": trade.lower() if trade != "HVAC" else "hvac",
                    "main_service": trade,
                    # The call-earning services, in earning order (SUB_SERVICES)
                    "sub_services": ", ".join(x.title() for x in SUB_SERVICES.get(niche, [])[:8]),
                    "city": state_name,
                    "country": "United States",
                    "phone": "<LeadSmart tracking number>",
                    "domain": "<new domain>",
                    "extras": {
                        "pseo_plan_url": "<raw .mode5.json link from step 3>",
                        "site_profile": "pay_per_call",
                        "footer_credit": "no",
                        "footer_sitemap_link": "no",
                    },
                },
            },
        })
    plans.sort(key=lambda p: (-len(p["go_cities"]), -p["monthly_searches"]))
    return plans


# ══════════════════════════════════════════════════════════════════
# STAGE 5 — output
# ══════════════════════════════════════════════════════════════════
def write(meta, cands, scored, pricing=None):
    city_rows = city_verdicts(scored)
    plans = launch_plan(city_rows)
    n_by = {v: sum(1 for c in city_rows if c["verdict"] == v) for v in ("GO", "WATCH", "STOP")}
    untested = [c for c in cands if not c.get("_scanned")]
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
        "serp_credits":     serp_client.stats(),
        "verdict_counts":   n_by,
        "cities":           city_rows,
        "launch_plan":      plans,
        "opportunities":    scored[:200],
        "top_candidates_unscanned": [
            {**{k: c[k] for k in ("city", "state", "county", "pop", "zips",
                                  "top_niche", "top_payout", "bundle_value", "niche_list")},
             "volume": c.get("volume")}
            for c in untested[:200]
        ],
    }
    with open("opportunities.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    with open("launch_plan.json", "w", encoding="utf-8") as f:
        json.dump(plans, f, indent=2)
    try:
        write_html(payload, scored, untested)
    except Exception as e:  # the report is a view; it must never fail the run
        print(f"   ⚠️ html report skipped: {e}")

    with open("opportunities.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "verdict", "why", "value", "volume", "opportunity", "serp_score", "payout", "pricing",
                    "bundle_value", "niche", "sub_service", "city", "state",
                    "county", "population", "zips", "dedicated", "emd", "pseo",
                    "national", "other_local", "directory", "pack_size",
                    "pack_median_reviews", "query", "occupants"])
        for i, o in enumerate(scored[:200], 1):
            b = o["serp_breakdown"]
            w.writerow([i, o.get("verdict"), "; ".join(o.get("why") or []),
                        o.get("value"), o.get("volume"), o["opportunity"], o["serp_score"], o["payout"],
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
        f"- **{len(cands):,}** candidate cities · **{len(scored)}** SERP-scored · "
        f"{serp_client.summary_line()}",
        f"- Verdict by city: **{n_by['GO']} GO** · {n_by['WATCH']} WATCH · {n_by['STOP']} STOP",
        "",
    ]
    if city_rows:
        lines += ["## Verdict by city", "",
                  "Judged on the city's **worst** scored query — one open sub-service "
                  "under a taken head term is not an open market.", "",
                  "| Verdict | City | Niche | Payout | Searches/mo | Why |",
                  "|---|---|---|---|---|---|"]
        _open = [c for c in city_rows if c["verdict"] != "STOP"]
        if not _open:
            lines.append("| — | *every scanned city is STOP* | | | | |")
        for c in _open[:25]:
            lines.append(f"| **{c['verdict']}** | {c['city']}, {c['state']} | {c['niche']} "
                         f"| ${c['payout']:.2f} | {c['volume'] if c['volume'] is not None else '?'} "
                         f"| {'<br>'.join(c['why'][:3])} |")
        stops = [c for c in city_rows if c["verdict"] == "STOP"]
        if stops:
            lines += ["", f"<details><summary>{len(stops)} STOP cities</summary>", "",
                      "| City | Why |", "|---|---|"]
            for c in stops[:60]:
                lines.append(f"| {c['city']}, {c['state']} | {c['why'][0] if c['why'] else ''} |")
            lines += ["", "</details>"]
        lines.append("")
    if plans:
        lines += ["## Launch plan", "",
                  "Every value below is already filled in and is also in "
                  "`launch_plan.json`. Do the steps in order; each one is a gate.", ""]
        for pl in plans[:5]:
            f1 = pl["forms"]["1_keyword_tool_mode5_area_plan"]
            f2 = pl["forms"]["2_builder_mode5"]
            lines += [f"### {pl['state_name']} · {pl['niche']}",
                      "",
                      f"- **GO:** {', '.join(pl['go_cities'])}"
                      + (f" · WATCH: {', '.join(pl['watch_cities'])}" if pl["watch_cities"] else ""),
                      f"- {pl['monthly_searches']:,} searches/mo across these towns · best payout ${pl['best_payout']:.2f}",
                      f"- Shape: {pl['shape']}",
                      "",
                      "1. **Confirm by eye** (free, 2 minutes) — page one should hold "
                      "directories and out-of-town sites, not local pages built for the town:",
                      *[f"   - {u}" for u in pl["manual_check"]],
                      "2. **Confirm with LeadSmart** — the ZIPs are bought for this niche "
                      "at call (not CPL), the billable duration, and the hours the buyer answers.",
                      "3. **Keyword tool → Mode 5 Area Plan**",
                      "",
                      "   | Field | Value |", "   |---|---|",
                      *[f"   | {k} | `{v}` |" for k, v in f1.items() if v != ""],
                      "",
                      "4. **Website builder → Mode 5** with the `.mode5.json` link from step 3",
                      "",
                      "   | Field | Value |", "   |---|---|",
                      *[f"   | {k} | `{v}` |" for k, v in f2.items() if k != "extras"],
                      f"   | extras | `{json.dumps(f2['extras'])}` |",
                      "",
                      "5. **After 3-4 weeks in GSC** — Mode 2 service pages under the area "
                      "hubs that show impressions (the Mesa/Phoenix pattern, `m2_merge.py`).",
                      ""]
    elif scored:
        lines += ["## Launch plan", "",
                  "No city passed as GO. Nothing here is worth a domain yet — widen "
                  "`states`, lower `min_payout`, or try another niche. WATCH rows are "
                  "for a site that already exists in that state, not a new one.", ""]
    if untested and scored:
        lines += [f"## Not yet scanned ({len(untested)} cities)", "",
                  "Next run: raise `max_serp_checks` — every SERP above comes from "
                  "cache for free, so the credits go only to these.", "",
                  "| City | Niche | Payout | Searches/mo |", "|---|---|---|---|"]
        for c in untested[:15]:
            lines.append(f"| {c['city']}, {c['state']} | {c['top_niche']} | ${c['top_payout']:.2f} "
                         f"| {c.get('volume') if c.get('volume') is not None else '?'} |")
        lines.append("")
    if scored:
        lines += ["## All scored queries (top 30)", "",
                  "| # | Opp | SERP | Payout | Searches/mo | Pack | Query | Occupied by |",
                  "|---|---|---|---|---|---|---|---|"]
        for i, o in enumerate(scored[:30], 1):
            b = o["serp_breakdown"]
            occ = (f"{b['dedicated']} dedicated, {b.get('emd',0)} EMD, "
                   f"{b['pseo']} pSEO, {b.get('other_local',0)} local, "
                   f"{b['directory']} directory")
            pk = (f"{b.get('pack_size',0)}× {b.get('pack_median_reviews',0)} rev"
                  if b.get("pack_size") else "none")
            lines.append(f"| {i} | **{o['opportunity']:.0f}** | {o['serp_score']} "
                         f"| ${o['payout']:.2f} | {o.get('volume') if o.get('volume') is not None else '?'} | {pk} "
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
                  "Search volume is measured here only for the broad trade term. "
                  "The Mode 5 Area Plan in the launch plan measures every town and "
                  "keyword before a page is written."]
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
    print("   📄 opportunity_report.html · opportunities.json · opportunities.csv · "
          "opportunity_report.md · launch_plan.json")
    print(f"   🧭 {n_by['GO']} GO · {n_by['WATCH']} WATCH · {n_by['STOP']} STOP · "
          f"{len(plans)} launch plan(s)")


# ══════════════════════════════════════════════════════════════════
# STAGE 5c — the readable report (opportunity_report.html)
# ══════════════════════════════════════════════════════════════════
# The markdown is for the Actions summary. Opened anywhere else it is a wall of
# pipes and <details> tags, so the decision — which cities, why, what to do
# next — is rendered as one self-contained page: no scripts, no external
# files, opens from the downloaded artifact in any browser.
_CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#16202b;--mute:#5d6b7a;--line:#e1e5ea;
--go:#127a3e;--gobg:#e3f4ea;--watch:#8a5a00;--watchbg:#fbf0d9;--stop:#b3261e;--stopbg:#fbe5e3;--acc:#1f5fbf}
@media(prefers-color-scheme:dark){:root{--bg:#11161c;--card:#1a2129;--ink:#e6ebf0;--mute:#98a6b5;--line:#2c3643;
--go:#5fd08d;--gobg:#16301f;--watch:#f0c060;--watchbg:#352a12;--stop:#ff8a80;--stopbg:#3a1a18;--acc:#7fb0ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1060px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.15rem;margin:34px 0 10px}h3{font-size:1rem;margin:18px 0 6px}
.sub{color:var(--mute);margin:0 0 18px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.tile b{display:block;font-size:1.5rem;font-variant-numeric:tabular-nums}.tile span{color:var(--mute);font-size:.85rem}
.answer{border-left:5px solid var(--acc);padding:14px 18px;background:var(--card);border-radius:8px;font-size:1.02rem}
.funnel{display:flex;flex-wrap:wrap;gap:6px;align-items:center;color:var(--mute);font-size:.9rem}
.funnel b{color:var(--ink);font-variant-numeric:tabular-nums}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.92rem}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mute);font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}
td.n{font-variant-numeric:tabular-nums;white-space:nowrap}
.chip{display:inline-block;padding:2px 9px;border-radius:99px;font-weight:700;font-size:.78rem;letter-spacing:.03em}
.GO{color:var(--go);background:var(--gobg)}.WATCH{color:var(--watch);background:var(--watchbg)}.STOP{color:var(--stop);background:var(--stopbg)}
ul.occ{margin:4px 0 0;padding-left:18px;color:var(--mute);font-size:.85rem}
a{color:var(--acc)}code{background:var(--bg);border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-size:.88em}
.legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
.legend div{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:.9rem}
ol.steps li{margin:6px 0}.muted{color:var(--mute)}
"""


def write_html(payload, scored, untested):
    from html import escape as E
    cities = payload["cities"]
    plans = payload["launch_plan"]
    vc = payload["verdict_counts"]
    cr = payload["serp_credits"]
    f = payload["filters"]
    by_city = {}
    for o in scored:
        by_city.setdefault((o["city"], o["state"]), []).append(o)

    # The one-paragraph answer. Everything else on the page supports it.
    if vc["GO"]:
        answer = (f"<b>{vc['GO']} {'city is' if vc['GO'] == 1 else 'cities are'} open.</b> "
                  f"Check them by eye (links below), confirm the ZIPs with LeadSmart, then "
                  f"follow the launch plan — every form is already filled in.")
    elif vc["WATCH"]:
        answer = (f"<b>No city is clearly open.</b> {vc['WATCH']} are borderline (WATCH): "
                  f"worth an area page on a site you already run in that state, "
                  f"not a new domain.")
    elif cities:
        answer = ("<b>Every city scanned is taken.</b> Local companies already have "
                  "pages built for these towns. Nothing here is worth a domain — "
                  "scan the untested cities below, or another niche or state.")
    else:
        answer = ("<b>Nothing was SERP-checked.</b> Either the filters left no city, "
                  "or no SerpApi key/credits were available. The funnel below shows where "
                  "the cities went.")

    fun = []
    for k in ("coverage rows", "rows after payout/pop filter", "candidate cities",
              "cities with enough searches"):
        if k in _FUNNEL:
            fun.append(f"<span><b>{_FUNNEL[k]:,}</b> {E(k)}</span>")
    fun.append(f"<span><b>{len(cities)}</b> cities SERP-checked</span>")
    fun.append(f"<span><b>{vc['GO']}</b> GO</span>")
    dropped = _FUNNEL.get("economics dropped") or {}

    h = ["<!doctype html><html lang='en'><head><meta charset='utf-8'>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         f"<title>Opportunity Scan {E(str(payload.get('dataset_date') or ''))}</title>",
         f"<style>{_CSS}</style></head><body><main>",
         "<h1>Opportunity scan</h1>",
         f"<p class='sub'>{E(', '.join(f['niches']) if isinstance(f['niches'], list) else 'All niches')} · "
         f"{E(', '.join(f['states']) if isinstance(f['states'], list) else 'all states')} · "
         f"{E(f['payout_type'])} payout ≥ ${f['min_payout']:g} · "
         f"population {f['population'][0]:,}–{f['population'][1]:,} · data {E(str(payload.get('dataset_date')))} · "
         f"run {E(payload['generated'])}</p>",
         f"<div class='answer'>{answer}</div>",
         "<h2>At a glance</h2><div class='tiles'>",
         f"<div class='tile'><b class='chip GO' style='font-size:1.3rem'>{vc['GO']}</b><span>GO — open, build here</span></div>",
         f"<div class='tile'><b class='chip WATCH' style='font-size:1.3rem'>{vc['WATCH']}</b><span>WATCH — borderline</span></div>",
         f"<div class='tile'><b class='chip STOP' style='font-size:1.3rem'>{vc['STOP']}</b><span>STOP — already taken</span></div>",
         f"<div class='tile'><b>{cr.get('spent', 0)}</b><span>SerpApi credits spent</span></div>",
         f"<div class='tile'><b>{cr.get('cached', 0)}</b><span>SERPs free from cache</span></div>",
         f"<div class='tile'><b>{len(untested)}</b><span>cities not yet checked</span></div>",
         "</div>",
         "<h2>How the cities were narrowed</h2>",
         "<div class='card'><div class='funnel'>" + " → ".join(fun) + "</div>"]
    if dropped:
        h.append("<p class='muted' style='margin:10px 0 0'>Removed as not worth a call: "
                 + ", ".join(f"{E(n)} (${v:.2f}/call)" for n, v in dropped.items()) + "</p>")
    h.append("</div>")

    # ── verdict table ───────────────────────────────────────────────────
    h.append("<h2>Every city checked</h2>")
    if cities:
        h += ["<div class='card scroll'><table><thead><tr><th>Verdict</th><th>City</th>"
              "<th>Payout</th><th>Searches/mo</th><th>Why</th><th>Who holds page one</th></tr></thead><tbody>"]
        for c in cities:
            occ = []
            for o in by_city.get((c["city"], c["state"]), []):
                for x in o["occupants"]:
                    if x["kind"] not in ("directory", "social profile", "forum"):
                        occ.append(f"{E(x['host'])} <span class='muted'>({E(x['kind'])})</span>")
            occ = list(dict.fromkeys(occ))[:6]
            why = "<br>".join(E(w.replace("`", "")) for w in c["why"][:3])
            # Link the query that decided the verdict (the worst one).
            q = min(c["queries"], key=lambda x: x["serp_score"])["query"] if c["queries"] else ""
            link = "https://www.google.com/search?" + urllib.parse.urlencode({"q": q})
            h.append(
                f"<tr><td><span class='chip {c['verdict']}'>{c['verdict']}</span></td>"
                f"<td><b>{E(c['city'])}, {E(c['state'])}</b><br><a href='{E(link)}' target='_blank' rel='noopener'>see on Google</a></td>"
                f"<td class='n'>${c['payout']:.2f}</td>"
                f"<td class='n'>{c['volume'] if c['volume'] is not None else '?'}</td>"
                f"<td>{why}</td>"
                f"<td>{'<ul class=occ><li>' + '</li><li>'.join(occ) + '</li></ul>' if occ else '<span class=muted>only directories</span>'}</td></tr>")
        h.append("</tbody></table></div>")
    else:
        h.append("<p class='muted'>No city was SERP-checked in this run.</p>")

    # ── launch plan ─────────────────────────────────────────────────────
    if plans:
        h.append("<h2>Launch plan</h2>")
        for pl in plans[:5]:
            f1 = pl["forms"]["1_keyword_tool_mode5_area_plan"]
            f2 = pl["forms"]["2_builder_mode5"]
            rows1 = "".join(f"<tr><td>{E(k)}</td><td><code>{E(str(v))}</code></td></tr>" for k, v in f1.items() if v != "")
            rows2 = "".join(f"<tr><td>{E(k)}</td><td><code>{E(json.dumps(v) if isinstance(v, dict) else str(v))}</code></td></tr>"
                            for k, v in f2.items())
            h += [f"<div class='card' style='margin-bottom:14px'><h3>{E(pl['state_name'])} · {E(pl['niche'])}</h3>",
                  f"<p><span class='chip GO'>GO</span> {E(', '.join(pl['go_cities']))}"
                  + (f" &nbsp;<span class='chip WATCH'>WATCH</span> {E(', '.join(pl['watch_cities']))}" if pl["watch_cities"] else "")
                  + f"<br><span class='muted'>{pl['monthly_searches']:,} searches/mo · best payout ${pl['best_payout']:.2f} · {E(pl['shape'])}</span></p>",
                  "<ol class='steps'>",
                  "<li><b>Look yourself</b> (free): page one should be directories and out-of-town sites, not pages built for the town. "
                  + " · ".join(f"<a href='{E(u)}' target='_blank' rel='noopener'>{E(urllib.parse.parse_qs(urllib.parse.urlparse(u).query)['q'][0])}</a>" for u in pl["manual_check"]) + "</li>",
                  "<li><b>Ask LeadSmart</b>: are these ZIPs bought for this niche on calls, what call length pays, and what hours the buyer answers.</li>",
                  f"<li><b>Keyword tool → Mode 5 Area Plan</b><div class='scroll'><table>{rows1}</table></div></li>",
                  f"<li><b>Website builder → Mode 5</b> with the <code>.mode5.json</code> link from step 3<div class='scroll'><table>{rows2}</table></div></li>",
                  "<li><b>After 3–4 weeks</b>: Mode 2 service pages under the area pages that show impressions in Search Console.</li>",
                  "</ol></div>"]

    # ── untested ────────────────────────────────────────────────────────
    if untested and cities:
        h += [f"<h2>Not checked yet ({len(untested)})</h2>",
              "<p class='muted'>Next run: raise <code>max_serp_checks</code>. Cities already checked come back free from cache, so credits go only to these.</p>",
              "<div class='card scroll'><table><thead><tr><th>City</th><th>Niche</th><th>Payout</th><th>Searches/mo</th></tr></thead><tbody>"]
        for c in untested[:25]:
            h.append(f"<tr><td>{E(c['city'])}, {E(c['state'])}</td><td>{E(c['top_niche'])}</td>"
                     f"<td class='n'>${c['top_payout']:.2f}</td><td class='n'>{c.get('volume') if c.get('volume') is not None else '?'}</td></tr>")
        h.append("</tbody></table></div>")

    h += ["<h2>What the verdicts mean</h2><div class='legend'>",
          "<div><span class='chip GO'>GO</span> Every query checked is open: no city domain, no page network, "
          f"no local company with a page for this town, SERP score ≥ {GO_SCORE}, at least {GO_VOLUME} searches a month.</div>",
          "<div><span class='chip WATCH'>WATCH</span> Close but not clean — one competitor page, a strong map pack, "
          "a low score or low/unknown searches. Fine as an extra area page, not a new domain.</div>",
          "<div><span class='chip STOP'>STOP</span> A city domain, a programmatic network, two or more local pages "
          "built for this town, or a map pack at 500+ reviews. A new site will not get past them.</div>",
          "</div>",
          "<p class='muted' style='margin-top:18px'>A city is judged on its worst query. Population figures come from the "
          "coverage feed and are often the nearest large city's, so searches/mo is the demand number to trust. "
          "Before buying a domain, LeadSmart must confirm the call length that pays and the buyer's hours — no data feed has those.</p>",
          "</main></body></html>"]
    with open("opportunity_report.html", "w", encoding="utf-8") as fh:
        fh.write("\n".join(h))


def main():
    print("\n🔍 OPPORTUNITY FINDER\n" + "=" * 55)
    meta, rows = pull_coverage()
    if not rows:
        print("❌ no coverage rows — nothing to do")
        write(meta, [], [])
        return
    pricing = price_modes(rows)
    cands   = shortlist(rows, pricing)
    cands   = demand(cands)
    scored  = scan(cands)
    write(meta, cands, scored, pricing)

    if scored:
        print("\n🏆 TOP 10")
        for i, o in enumerate(scored[:10], 1):
            print(f"  {i:2}. {o.get('verdict', '?'):5}  SERP {o['serp_score']:3}  "
                  f"${o['payout']:7.2f}  {str(o.get('volume', '?')):>5}/mo  {o['query']}")
    elif cands:
        print("\n🏆 TOP 10 CITIES (revenue side only)")
        for i, c in enumerate(cands[:10], 1):
            print(f"  {i:2}. {c['bundle_value']:6.0f}  {c['city']}, {c['state']}  "
                  f"{len(c['niche_list'])} niches  top ${c['top_payout']:.2f}")
    print()


if __name__ == "__main__":
    main()
