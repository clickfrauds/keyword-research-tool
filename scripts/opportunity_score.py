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
SHAPES = [
    "{s} cost",
    "how much does {s} cost",
    "signs you need {s}",
    "when to call a plumber for {s}",
    "{s} vs replacement",
]

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
    """'faucet / valve / fixture repair' -> 'faucet repair'."""
    s = name.lower()
    s = re.split(r"\s*[/(]", s)[0].strip()
    s = re.sub(r"\s+", " ", s)
    return s


def load_specifics(niche):
    p = os.path.join(CALL_INTEL, "specifics.csv")
    if not os.path.isfile(p):
        sys.exit(f"missing {p} — run extract_call_intel.js first")
    out = []
    with open(p, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["niche"].lower() != niche.lower():
                continue
            r["calls"] = int(r["calls"])
            r["paid_pct"] = int(r["paid_pct"])
            r["urgent_pct"] = int(r.get("urgent_pct") or 0)
            out.append(r)
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
    cust = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "").strip()
    if not cust:
        print("   no GOOGLE_ADS_CUSTOMER_ID")
        return None
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        print("   google-ads not installed")
        return None
    try:
        # No version pin. requirements.txt asks for google-ads unpinned, so CI
        # installs the current release, and Google retires old API versions —
        # v18 was gone, which is how a whole run came back with zero volumes.
        # Every other script in this repo lets the library pick; so does this.
        client = GoogleAdsClient.load_from_env()
        geo_id = geo_target_id(client, geo_name) if geo_name else None
        svc = client.get_service("KeywordPlanIdeaService")
        req = client.get_type("GenerateKeywordHistoricalMetricsRequest")
        req.customer_id = cust
        req.keywords.extend(queries[:10000])
        req.language = "languageConstants/1000"          # English
        req.geo_target_constants.append(
            f"geoTargetConstants/{geo_id or 2840}")      # 2840 = United States
        resp = svc.generate_keyword_historical_metrics(request=req)
        out = {}
        for r in resp.results:
            m = r.keyword_metrics
            out[r.text.lower()] = int(m.avg_monthly_searches or 0) if m else 0
        return out
    except Exception as e:
        print(f"   Ads Planner failed ({str(e)[:90]})")
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
            "CROWDED": 0.1, "FORUM WALL": 0.0, "VIDEO WALL": 0.0}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--niche", default="plumbing")
    ap.add_argument("--max-serp", type=int, default=30,
                    help="SerpApi credits to spend, on the best candidates only")
    ap.add_argument("--min-calls", type=int, default=8,
                    help="ignore services below this many recorded calls")
    ap.add_argument("--min-volume", type=int, default=0)
    ap.add_argument("--no-volume", action="store_true",
                    help="score on revenue x winnable when the Planner is "
                         "unavailable. The ranking is much weaker — the paid "
                         "step then picks near-arbitrarily.")
    ap.add_argument("--geo", default="",
                    help="state or city to qualify queries with, e.g. Arizona. "
                         "Empty = nationwide informational queries")
    ap.add_argument("--ptype", default="Call")
    a = ap.parse_args()

    where = a.geo or "nationwide"
    print(f"\n── {a.niche} · {where} · max {a.max_serp} SerpApi credits ──\n")

    spec = [s for s in load_specifics(a.niche) if s["calls"] >= a.min_calls]
    if not spec:
        sys.exit(f"no services for '{a.niche}' with >= {a.min_calls} calls")
    print(f"1. services          {len(spec)} with >= {a.min_calls} calls")

    med = median_payout(a.niche, a.ptype)
    print(f"2. median payout     ${med:.2f}" if med else "2. median payout     unknown")

    cands = {}
    for s in spec:
        base = clean_service(s["specific_service"])
        if len(base) < 4:
            continue
        rev = (med or 1.0) * s["paid_pct"] / 100
        shapes = list(SHAPES)
        if a.geo:
            shapes += [g.replace("{geo}", a.geo.lower()) for g in GEO_SHAPES]
        for shape in shapes:
            q = shape.format(s=base)
            if len(q.split()) > 9:
                continue
            prev = cands.get(q)
            if not prev or rev > prev["revenue"]:
                cands[q] = {"query": q, "service": s["specific_service"],
                            "calls": s["calls"], "paid_pct": s["paid_pct"],
                            "urgent_pct": s["urgent_pct"], "revenue": rev}
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

    go = sorted([c for c in checked if c.get("score", 0) > 0
                 and c.get("verdict") in ("WINNABLE", "MIXED")],
                key=lambda c: -c["score"])

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
