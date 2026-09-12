#!/usr/bin/env python3
"""
opportunity_score.py — one table, one number, GO or NO-GO.

Three things have to be true before an article is worth writing, and until now
they lived in three different places:

    how many people search it     Google Ads Keyword Planner   (free)
    what a call is worth          call data x the payout feed  (free)
    whether a page can rank       serp_shape                   (1 credit each)

    score = monthly searches  x  revenue per call  x  winnable

Any of the three at zero makes the whole thing zero, which is the point. A wide
open SERP on a $4.88 niche is not an opportunity. Neither is a $220 payout
behind a wall of YouTube, nor a perfect query nobody types.

The credits are spent LAST and only on survivors. Volume and revenue are free,
so they rank the field first; the SERP check then runs on the best N. That is
why --max-serp defaults to 30 rather than the length of the candidate list —
the first version of this idea burned a quota answering questions about
services that pay $6 a call.

Inputs it reads:
    data/call_intel/specifics.csv     587 services, calls and paid share
    leadsmart-coverage.netlify.app    median payout per niche   (live)

Usage
    python scripts/opportunity_score.py --niche plumbing --max-serp 30
    python scripts/opportunity_score.py --niche hvac --max-serp 40 --min-volume 100
"""

import argparse
import collections
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALL_INTEL = os.path.join(HERE, "data", "call_intel")
#: Roughly how many ZIP codes the US has. Only used to turn an offer's ZIP
#: count into a share, so precision here does not matter much.
US_ZIPS = 41700

COVERAGE = os.environ.get("COVERAGE_BASE",
                          "https://leadsmart-coverage.netlify.app").rstrip("/")
SERP_KEY = os.environ.get("SERPAPI_API_KEY", "").strip()

# The call feed and the payout feed name the same trades differently.
NICHE_ALIAS = {
    "plumbing": "Plumbing", "hvac": "HVAC", "roofing": "Roofing",
    "electrical": "Electrical", "pest control": "Pest Control",
    "water damage": "Water Damage", "gutters": "Gutters",
    "painting": "Painting", "tree services": "Tree Services",
    "appliance repair": "Appliance", "garage door": "Garage Door",
    "lawncare & landscaping": "Landscaping",
}

# A taxonomy label is not a search. "faucet / valve / fixture repair" is how the
# dashboard files a call; "faucet repair cost" is what a person types. These
# turn one into the other, and the shapes are the ones that survived a SERP
# check rather than the ones that sounded right.
# Two of these were written while the only niche was plumbing, and both carry
# that assumption into every other one: "when to call a plumber for mice
# control" and "mice control vs replacement" are not questions anyone asks.
# Two of five shapes wasted, and each would have spent a SerpApi credit proving
# it. The trade name and the last shape now come from the niche.
SHAPES = [
    "{s} cost",
    "how much does {s} cost",
    "signs you need {s}",
    "when to call {pro} for {s}",
]

#: What the caller would call the person they need. Falls back to "pro", which
#: is clumsy but never wrong.
TRADE_PRO = {
    "plumbing": "plumber",
    "hvac": "hvac technician",
    "roofing": "roofer",
    "electrical": "electrician",
    "pest control": "exterminator",
    "tree services": "tree service",
    "appliance repair": "appliance repair technician",
    "gutters": "gutter company",
    "water damage": "water damage company",
    "painting": "painter",
    "window repair": "window repair company",
    "garage door": "garage door company",
    "pool services": "pool service",
    "lawncare & landscaping": "landscaper",
    "carpet & rug cleaning": "carpet cleaner",
    "remodeling": "contractor",
    "cleaning services": "cleaning service",
    "handyman & structural": "handyman",
}

#: The fifth shape, per niche. Repair-or-replace only makes sense where there
#: is a unit to replace; for pest control the same intent is removal, and for a
#: service that is performed rather than installed it is frequency.
LAST_SHAPE = {
    "pest control": "how to get rid of {bare}",
    "tree services": "when to remove {bare}",
    "lawncare & landscaping": "how often {s}",
    "cleaning services": "how often {s}",
    "carpet & rug cleaning": "how often {s}",
    "painting": "how often {s}",
}
DEFAULT_LAST_SHAPE = "{s} vs replacement"


#: Words a service name ends in that describe the work, not the thing. "how to
#: get rid of mice control" is not a query; "how to get rid of mice" is. Only
#: trimmed for shapes that ask about the problem itself.
_WORK_TAIL = ("control", "removal", "treatment", "extermination", "exterminating",
              "service", "services", "cleaning", "repair", "inspection")


#: Already plural, so adding an s makes a word nobody types.
_ALREADY_PLURAL = {"mice", "lice", "geese", "deer", "fish", "silverfish",
                   "termites", "ants", "roaches", "wasps", "fleas", "bees"}


def bare_subject(service):
    """The thing itself, plural, with the word for the work taken off the end.

    "how to get rid of mice control" is not a query and neither is "how to get
    rid of bed bug" — that shape always asks about more than one.
    """
    words = service.split()
    while len(words) > 1 and words[-1].lower() in _WORK_TAIL:
        words.pop()
    if words:
        last = words[-1].lower()
        if not last.endswith("s") and last not in _ALREADY_PLURAL:
            # -ch/-sh/-x/-z take -es: "cockroachs" is not a word.
            words[-1] = last + ("es" if last.endswith(("ch", "sh", "x", "z"))
                                else "s")
    return " ".join(words)


def _article(word):
    """a/an. "a exterminator" and "a hvac technician" both read as typos, and a
    query with a typo in it is not the query anyone searched."""
    return "an" if word[:1].lower() in "aeiou" or word[:4].lower() == "hvac" else "a"


def niche_shapes(niche):
    """SHAPES with the niche's own trade name and closing question.

    Returns format strings taking {s}; a shape needing the bare subject takes
    {bare} as well, so the caller passes both.
    """
    pro = TRADE_PRO.get(niche.lower(), "pro")
    last = LAST_SHAPE.get(niche.lower(), DEFAULT_LAST_SHAPE)
    out = [sh.replace("{pro}", f"{_article(pro)} {pro}") for sh in SHAPES]
    return out + [last]

# With --geo. The nationwide shapes above are the default because ZIP routing
# means content does not have to name a place to earn from it, and the openings
# found so far are informational. But "slab leak repair cost arizona" was the
# strongest candidate of the last batch and no shape above can produce it — a
# state-qualified query is a different, usually thinner, SERP and deserves to
# be asked about rather than assumed closed.
GEO_SHAPES = [
    "{s} {geo}",
    "{s} cost {geo}",
    "{s} near me {geo}",
]


def clean_service(name):
    """'faucet / valve / fixture repair' -> 'faucet repair'.

    The call log writes alternatives with slashes, and the head noun sits at
    the very end: in 'irrigation / sprinkler leak' only the last segment
    carries 'leak'. Keeping just the first segment is what turned that into
    the base 'irrigation', and 'kitchen / bathroom drain' into 'kitchen' —
    which is how a run spent credits ranking 'irrigation cost' and
    'kitchen cost'. Take the first alternative and give it the head noun back.
    """
    s = re.sub(r"\s+", " ", re.split(r"\s*\(", name.lower())[0]).strip()
    parts = [p.strip() for p in s.split("/") if p.strip()]
    if len(parts) < 2:
        return s
    head = parts[-1].split()[1:]          # last segment minus its own modifier
    return " ".join([parts[0]] + head).strip()


def load_specifics(niche):
    """Rows for one niche, with the same service counted once.

    The call log writes a service however the agent typed it, so "AC repair",
    "ac repair" and "ac repair (needs freon)" are three rows for one thing.
    clean_service() collapses them to the same query anyway, and the caller
    keeps whichever row claims the higher revenue — so the 10-call row at 100%
    paid displaced the 41-call row at 76%, and the payout for the niche's
    biggest service came from a quarter of its calls.

    It is worse elsewhere: tree removal's 195 calls at 71% lost to a 2-call row
    at 100%, and refrigerator repair's 129 calls to another 2-call row. Rates
    off two calls are noise, and they were setting the revenue that decides
    both the $15 gate and the ranking.

    Merging on the same key clean_service() uses, weighting the rates by calls,
    makes the rate come from every call recorded for that service.
    """
    p = os.path.join(CALL_INTEL, "specifics.csv")
    if not os.path.isfile(p):
        sys.exit(f"missing {p} — run extract_call_intel.js first")

    groups = collections.OrderedDict()
    with open(p, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["niche"].lower() != niche.lower():
                continue
            calls = int(r["calls"] or 0)
            key = clean_service(r["specific_service"])
            g = groups.get(key)
            if g is None:
                g = groups[key] = {**r, "calls": 0, "_paid": 0.0, "_urg": 0.0,
                                   "_names": []}
            g["calls"] += calls
            g["_paid"] += calls * int(r["paid_pct"] or 0)
            g["_urg"] += calls * int(r.get("urgent_pct") or 0)
            g["_names"].append(r["specific_service"])

    out = []
    for g in groups.values():
        n = g["calls"] or 1
        g["paid_pct"] = round(g["_paid"] / n)
        g["urgent_pct"] = round(g["_urg"] / n)
        # Report the longest spelling — it reads best in the results table.
        g["specific_service"] = max(g.pop("_names"), key=len)
        g.pop("_paid"); g.pop("_urg")
        out.append(g)
    return out


def median_payout(niche, ptype="Call"):
    """Median, not top_payout. The best ZIP in the country is not the payout —
    reading it that way put Plumbing at $221.95 when its median is $34.38."""
    try:
        with urllib.request.urlopen(
                f"{COVERAGE}/api/niche_summary.json", timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"   coverage feed unreachable ({e}) — revenue falls back to 1.0")
        return None
    want = NICHE_ALIAS.get(niche.lower(), niche.title())
    for n in data.get("niches", []):
        if n["niche"].lower() == want.lower() and n["payout_type"] == ptype:
            return float(n["median"])
    return None


def all_payouts(ptype="Call"):
    """Every niche's payout row from the coverage feed, keyed by lower name."""
    try:
        with urllib.request.urlopen(
                f"{COVERAGE}/api/niche_summary.json", timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        sys.exit(f"coverage feed unreachable ({e})")
    return {n["niche"].lower(): n for n in data.get("niches", [])
            if n["payout_type"] == ptype}


def rank_niches(min_calls, min_revenue, ptype="Call"):
    """Which niche to build next.

    Everything else in this file answers "what should I write inside a niche".
    Nothing answered "which niche", and the answer is not the obvious one: the
    two niches with the most recorded calls pay the least per call, so the call
    log alone points straight at the worst two.
    """
    pay = all_payouts(ptype)
    rows = []
    with open(os.path.join(CALL_INTEL, "niches.csv"), encoding="utf-8") as fh:
        niches = list(csv.DictReader(fh))

    usable = collections.Counter()
    with open(os.path.join(CALL_INTEL, "specifics.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if int(r["calls"] or 0) >= min_calls:
                usable[r["niche"]] += 1

    for r in niches:
        name = r["niche"]
        row = pay.get(NICHE_ALIAS.get(name.lower(), name).lower()) or pay.get(name.lower())
        if not row:
            continue
        med = float(row["median"])
        paid = int(r["paid_pct"] or 0)
        # Coverage is the third multiplier and the one that is easy to miss.
        # An offer only buys calls from ZIPs it covers; a caller from anywhere
        # else is worth nothing, however good the payout and the paid rate.
        # Plumbing covers ~25,000 of ~41,700 US ZIPs, so ~40% of callers have
        # no buyer at all — and HVAC, which looks like the best niche on payout
        # alone, covers 53%.
        cov = int(row.get("zips") or 0) / US_ZIPS
        eff = med * paid / 100 * cov
        mx = float(row["max"] or 0)
        rows.append({
            "niche": name, "calls": int(r["calls"] or 0),
            "services": usable[name], "payout": med, "paid_pct": paid,
            "coverage": cov, "per_call": eff,
            "spread": (mx / med) if med else 0,
        })

    rows.sort(key=lambda x: -x["per_call"])

    print(f"\n── which niche to build next · {ptype} payouts ──\n")
    print(f"{'niche':22s} {'calls':>6s} {'svcs':>5s} {'payout':>8s} "
          f"{'paid':>5s} {'zips':>5s} {'$/call':>8s} {'geo':>6s}")
    print("-" * 80)
    for x in rows:
        note = ""
        if x["per_call"] < min_revenue:
            note = f"  under ${min_revenue:.0f} — skip"
        elif x["services"] < 8:
            note = "  thin data"
        print(f"{x['niche'][:21]:22s} {x['calls']:>6d} {x['services']:>5d} "
              f"${x['payout']:>7.2f} {x['paid_pct']:>4d}% {x['coverage']:>4.0%} "
              f"${x['per_call']:>7.2f} {x['spread']:>5.1f}x{note}")

    ready = [x for x in rows if x["per_call"] >= min_revenue and x["services"] >= 8]
    print()
    if ready:
        print("Enough data and enough money, best first:")
        for x in ready:
            print(f"   {x['niche']} — ${x['per_call']:.2f}/call, "
                  f"{x['coverage']:.0%} of ZIPs, {x['services']} services, "
                  f"{x['calls']} calls")
        print(f"\n   Next: --niche \"{ready[0]['niche']}\"")
    else:
        print("   Nothing clears both bars. Lower --min-calls, or collect more"
              " call data before committing to a niche.")

    print("\n   $/call = payout x paid rate x ZIP coverage. An offer only buys"
          " calls from ZIPs it")
    print("   covers, so a caller from anywhere else earns nothing whatever the"
          " payout is.")
    print("\n   geo column = best ZIP / median. Above ~2x the payout depends"
          " heavily on where")
    print("   the caller is, so check the coverage map before choosing a metro."
          " At 1.0x")
    print("   every ZIP pays the same and location does not affect revenue at"
          " all.")
    return rows



def geo_target_id(client, name):
    """Ask Google for the id rather than hardcoding one. A wrong constant does
    not error — it silently returns volumes for the wrong place."""
    try:
        svc = client.get_service("GeoTargetConstantService")
        req = client.get_type("SuggestGeoTargetConstantsRequest")
        req.locale = "en"
        req.country_code = "US"
        req.location_names.names.append(name)
        for s in svc.suggest_geo_target_constants(request=req).geo_target_constant_suggestions:
            g = s.geo_target_constant
            if g.target_type in ("State", "Province", "City", "Country"):
                print(f"   geo: {g.canonical_name} ({g.target_type})")
                return g.resource_name.split("/")[-1]
    except Exception as e:
        print(f"   geo lookup failed ({str(e)[:60]}) — using United States")
    return None


def keyword_volumes(queries, geo_name=None):
    """Monthly searches from the Ads Keyword Planner. Free, but it needs the
    five GOOGLE_ADS_* secrets; without them every query scores volume 0 and the
    run still finishes, ranked on revenue alone."""
    # Digits only. keyword_research.py has stripped dashes since it was
    # written; this script only stripped whitespace, so a secret stored as
    # 123-456-7890 went into the request verbatim. The library validates
    # login_customer_id and would have raised on a dashed one, but the
    # request's customer_id gets no such check — it just becomes a customer
    # Google cannot resolve, and the API answers PERMISSION_DENIED rather
    # than saying the id is malformed.
    cust = re.sub(r"\D", "", os.environ.get("GOOGLE_ADS_CUSTOMER_ID", ""))
    if not cust:
        print("   no GOOGLE_ADS_CUSTOMER_ID")
        return None
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        print("   google-ads not installed")
        return None

    def attempt(with_login):
        env_key = "GOOGLE_ADS_LOGIN_CUSTOMER_ID"
        saved = os.environ.pop(env_key, None) if not with_login else None
        try:
            # No version pin. requirements.txt asks for google-ads unpinned,
            # so CI installs the current release and Google retires old API
            # versions — v18 was gone, which is how a whole run came back with
            # zero volumes. Every other script here lets the library pick.
            client = GoogleAdsClient.load_from_env()
            geo_id = geo_target_id(client, geo_name) if geo_name else None
            svc = client.get_service("KeywordPlanIdeaService")
            req = client.get_type("GenerateKeywordHistoricalMetricsRequest")
            req.customer_id = cust
            req.keywords.extend(queries[:10000])
            req.language = "languageConstants/1000"          # English
            req.geo_target_constants.append(
                f"geoTargetConstants/{geo_id or 2840}")      # 2840 = US
            resp = svc.generate_keyword_historical_metrics(request=req)
            out = {}
            for r in resp.results:
                m = r.keyword_metrics
                out[r.text.lower()] = int(m.avg_monthly_searches or 0) if m else 0
            return out, None
        except Exception as e:
            return None, str(e)
        finally:
            if saved is not None:
                os.environ[env_key] = saved

    login = re.sub(r"\D", "", os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""))

    # Try with the manager id, then without. The two Ads calls that already
    # work in this repo — keyword_pipeline's planner steps and
    # keyword_research_workflow — pass GOOGLE_ADS_CUSTOMER_ID and no manager
    # id at all, while this workflow passed both. A manager id that does not
    # actually sit above the account fails exactly the same way a genuinely
    # missing permission does, so the message cannot tell them apart. Ads
    # calls are free; asking twice costs nothing and settles it.
    out, err = attempt(with_login=bool(login))
    if out is None and login and ("PERMISSION_DENIED" in err
                                  or "doesn't have permission" in err):
        print("   denied with the manager id — retrying without it")
        out, err2 = attempt(with_login=False)
        if out is not None:
            print("   worked without it. GOOGLE_ADS_LOGIN_CUSTOMER_ID does not"
                  " manage this account — drop it from the workflow.")
            return out
        err = err2
    if out is not None:
        return out

    print(f"   Ads Planner failed ({err[:90]})")
    if "PERMISSION_DENIED" in err or "doesn't have permission" in err:
        print(f"   customer id: {len(cust)} digits · "
              f"login customer id: {len(login) or 'not set'} digits")
        print("   Both must be 10 digits. GOOGLE_ADS_CUSTOMER_ID is the "
              "account the keywords are pulled for;")
        print("   GOOGLE_ADS_LOGIN_CUSTOMER_ID is the manager (MCC) above it, "
              "and is required only when they differ.")
        print("   Neither combination was accepted, so check in the Ads UI "
              "that this account exists and is not itself a manager —")
        print("   the Keyword Planner cannot be queried on a manager account.")
    return None


def serp_verdict(query):
    """Delegates to serp_shape so there is one definition of 'winnable'."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "serp_shape", os.path.join(HERE, "scripts", "serp_shape.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data, err = mod.serp(query)
    if err:
        return {"verdict": "ERROR", "why": err[:70], "top3": ""}
    return mod.shape(data)


WINNABLE = {"WINNABLE": 1.0, "MIXED": 0.4, "BIG BRAND": 0.15,
            "CROWDED": 0.1, "FORUM WALL": 0.0, "VIDEO WALL": 0.0,
            # Listed rather than left to the .get() default, so that an
            # unknown verdict scoring 0 stays a bug and not a silent policy.
            "BRAND WALL": 0.0}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--niche", default="plumbing")
    ap.add_argument("--max-serp", type=int, default=30,
                    help="SerpApi credits to spend, on the best candidates only")
    ap.add_argument("--min-calls", type=int, default=8,
                    help="ignore services below this many recorded calls")
    ap.add_argument("--min-volume", type=int, default=0)
    ap.add_argument("--rank-niches", action="store_true",
                    help="rank every niche in the call data by what a call is "
                         "actually worth, and stop. Spends no SerpApi credits.")
    ap.add_argument("--min-revenue", type=float, default=15.0,
                    help="drop services paying less than this per call. The "
                         "plumbing run put sump pump at $7.35 in the GO list "
                         "twice; an article earning a fifth of the median is "
                         "not worth the same week of work.")
    ap.add_argument("--min-write-volume", type=int, default=100,
                    help="a GO needs at least this many monthly searches. "
                         "Ranking #1 on 20 a month is not an outcome.")
    ap.add_argument("--no-volume", action="store_true",
                    help="score on revenue x winnable when the Planner is "
                         "unavailable. The ranking is much weaker — the paid "
                         "step then picks near-arbitrarily.")
    ap.add_argument("--geo", default="",
                    help="state or city to qualify queries with, e.g. Arizona. "
                         "Empty = nationwide informational queries")
    ap.add_argument("--ptype", default="Call")
    a = ap.parse_args()

    # Before the run header: --rank-niches answers a different question
    # and spends no credits, so announcing a niche and a credit budget
    # first is just noise.
    if a.rank_niches:
        rank_niches(a.min_calls, a.min_revenue, a.ptype)
        return

    where = a.geo or "nationwide"
    print(f"\n── {a.niche} · {where} · max {a.max_serp} SerpApi credits ──\n")


    spec = [s for s in load_specifics(a.niche) if s["calls"] >= a.min_calls]
    if not spec:
        sys.exit(f"no services for '{a.niche}' with >= {a.min_calls} calls")
    print(f"1. services          {len(spec)} with >= {a.min_calls} calls")

    med = median_payout(a.niche, a.ptype)
    print(f"2. median payout     ${med:.2f}" if med else "2. median payout     unknown")

    cands = {}
    skipped_cheap = []
    for s in spec:
        base = clean_service(s["specific_service"])
        if len(base) < 4:
            continue
        rev = (med or 1.0) * s["paid_pct"] / 100
        # Dropped here rather than at the end, so a service this cheap never
        # reaches the paid step. Sump pump converts at 22% of the median and
        # took two SerpApi credits in the plumbing run to be recommended twice
        # at $7.35 a call.
        if rev < a.min_revenue:
            skipped_cheap.append((s["specific_service"], rev))
            continue
        shapes = niche_shapes(a.niche)
        if a.geo:
            shapes += [g.replace("{geo}", a.geo.lower()) for g in GEO_SHAPES]
        for shape in shapes:
            q = shape.format(s=base, bare=bare_subject(base))
            if len(q.split()) > 9:
                continue
            prev = cands.get(q)
            if not prev or rev > prev["revenue"]:
                cands[q] = {"query": q, "service": s["specific_service"],
                            "calls": s["calls"], "paid_pct": s["paid_pct"],
                            "urgent_pct": s["urgent_pct"], "revenue": rev}
    if skipped_cheap:
        worst = sorted(skipped_cheap, key=lambda t: t[1])
        print(f"   {len(skipped_cheap)} service(s) under ${a.min_revenue:.0f}/call "
              f"left out, e.g. {worst[0][0]} at ${worst[0][1]:.2f}")
    print(f"3. query candidates  {len(cands)}")

    vols = keyword_volumes(list(cands), a.geo or None)
    if vols is None:
        # Stop here. Volume is what orders the list, and the payout is nearly
        # flat across one niche, so without it "the top 30" is just the first
        # 30 in dict order — which is how a run spent 30 credits on "irrigation
        # cost" and "kitchen cost". A failed lookup must cost nothing.
        print("\n   volumes could not be read — stopping before the paid step.")
        print("   Without volume the ranking is arbitrary and the credits are"
              " wasted on whichever candidates happen to come first.")
        print("   Pass --no-volume to score on revenue x winnable alone.")
        if not a.no_volume:
            return
        vols = {}
    for q, c in cands.items():
        c["volume"] = vols.get(q.lower(), 0)
    have_vol = sum(1 for c in cands.values() if c["volume"])
    print(f"4. with volume       {have_vol}/{len(cands)}")
    if not have_vol and not a.no_volume:
        print("\n   every candidate came back at 0 searches — stopping.")
        print("   That is the Planner answering, not failing, but a field of"
              " zeros ranks no better than a failure. Widen --niche or --geo,")
        print("   or pass --no-volume to score without it.")
        return

    # Rank on the free signals, then spend credits on the top of that list.
    rank = sorted(cands.values(),
                  key=lambda c: -((c["volume"] or 1) * c["revenue"]))
    rank = [c for c in rank if c["volume"] >= a.min_volume] or rank
    checked = rank[:a.max_serp]
    print(f"5. SERP checking     {len(checked)} (of {len(rank)})\n")

    if not SERP_KEY:
        print("   no SERPAPI_API_KEY — stopping before the paid step")
        checked = []

    for i, c in enumerate(checked, 1):
        v = serp_verdict(c["query"])
        c.update(verdict=v["verdict"], why=v.get("why", ""), top3=v.get("top3", ""))
        c["score"] = round((c["volume"] or 1) * c["revenue"]
                           * WINNABLE.get(v["verdict"], 0))
        mark = "GO " if c["score"] > 0 and v["verdict"] in ("WINNABLE", "MIXED") else "no "
        print(f"{i:3}. {mark} {c['query'][:44]:46}{c['volume']:>6}"
              f"  ${c['revenue']:>5.2f}  {v['verdict']:11}{c['score']:>7}")

    # Volume floor as well as a verdict. The plumbing run marked GO on
    # "signs you need drain cleaning" at 20 searches a month and "faucet repair
    # cost" at 30 — winnable, and worth almost nothing won.
    go = sorted([c for c in checked if c.get("score", 0) > 0
                 and c.get("verdict") in ("WINNABLE", "MIXED")
                 and c["volume"] >= a.min_write_volume],
                key=lambda c: -c["score"])
    thin = [c for c in checked
            if c.get("verdict") in ("WINNABLE", "MIXED")
            and c["volume"] < a.min_write_volume]
    if thin:
        print(f"\n   {len(thin)} winnable but under {a.min_write_volume} "
              f"searches/mo, not listed as GO: "
              + ", ".join(f"{c['query']} ({c['volume']})" for c in thin[:4]))

    cols = ["query", "service", "volume", "revenue", "score", "verdict", "why",
            "calls", "paid_pct", "urgent_pct", "top3"]
    with open("opportunity_score.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(checked, key=lambda c: -c.get("score", 0)))

    with open("opportunity_score.md", "w", encoding="utf-8") as fh:
        fh.write(f"# Opportunity score — {a.niche}\n\n")
        fh.write(f"`score = monthly searches x revenue per call x winnable`. "
                 f"Median payout ${med:.2f}. {len(checked)} credits spent.\n\n")
        fh.write("| | Query | Vol | $/call | SERP | Score | Top 3 |\n"
                 "|---|---|---|---|---|---|---|\n")
        for c in sorted(checked, key=lambda c: -c.get("score", 0)):
            mark = "GO" if c in go else ""
            fh.write(f"| {mark} | {c['query']} | {c['volume']} | "
                     f"${c['revenue']:.2f} | {c.get('verdict','')} | "
                     f"{c.get('score',0)} | {c.get('top3','')} |\n")
        fh.write(f"\n**{len(go)} of {len(checked)}** are worth writing.\n")
        if go:
            fh.write("\n## Write these\n\n")
            for c in go:
                fh.write(f"- **{c['query']}** — {c['volume']}/mo, "
                         f"${c['revenue']:.2f} a call, {c['calls']} recorded "
                         f"calls at {c['paid_pct']}% paid\n")

    print(f"\n{len(go)} GO of {len(checked)} checked · "
          f"opportunity_score.csv · opportunity_score.md")


if __name__ == "__main__":
    main()
