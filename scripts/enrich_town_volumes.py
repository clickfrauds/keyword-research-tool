"""enrich_town_volumes.py — put the EMD keyword's own search volume in the index.

THE QUESTION THE TABLE COULD NOT ANSWER
  /towns ranks by payout and isolation and shows whether {town}{trade}.com is
  free. That is two thirds of the decision. The third is demand: how often do
  people IN that town search the term the domain is built on. Without it a
  free domain in a high-payout town still has to be measured one state at a
  time in the EMD finder before anyone can judge it.

HOW IT IS MEASURED
  Exactly the way emd_finder.py does it, and for the same reason:

  - Each town gets its OWN Google geo target, matched strictly (target_type
    City, canonical name = this town in this state). CSV.resolve_geo takes the
    first suggestion, which returned Clovis, California for Clovis, New Mexico
    and wrote a whole plan on the wrong state's numbers.
  - Both word orders are asked for ("duncan electricians" and "electricians
    duncan") and the larger is kept.
  - Every trade the town qualifies for rides in ONE batched request, so a town
    costs one geo call and one volume call whatever its niche count.

  Ads calls are free. The real limit is the 429 that arrives when requests
  come back to back, so towns are paced and a refusal is retried once, late.

RESUMABLE
  Progress is written after every town. A run that dies at town 400 picks up
  at 400 -- 1,400 API calls is not something to repeat for a timeout.

Run: python scripts/enrich_town_volumes.py
Env: MIN_PAYOUT (25) MIN_POP (10000) MAX_POP (120000) MIN_METRO_MILES (50)
     MAX_TOWNS (0 = all)  NICHES ("" = the four with a live or likely offer)
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import find_opportunities as FO          # noqa: E402  STATE_NAMES
import city_service_volume as CSV        # noqa: E402  Keyword Planner client

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "..", "data", "town_index.json")
STATE_FILE = os.path.join(HERE, "..", "data", ".volume_progress.json")

MIN_PAYOUT = float(os.environ.get("MIN_PAYOUT", "25") or 25)
MIN_POP = int(os.environ.get("MIN_POP", "10000") or 10000)
MAX_POP = int(os.environ.get("MAX_POP", "120000") or 120000)
MIN_METRO_MILES = int(os.environ.get("MIN_METRO_MILES", "50") or 50)
MAX_TOWNS = int(os.environ.get("MAX_TOWNS", "0") or 0)
PACE = float(os.environ.get("PACE_SECONDS", "2") or 2)

# Read the same probe terms the /towns button uses, so a town measured here
# and a town measured there report the same number. leadsmart_campaigns.json
# is keyed by campaign; the index is keyed by the feed's niche label, and
# feed_niche is the bridge the catalogue already carries.
def load_probe():
    try:
        cat = json.load(open(os.path.join(HERE, "..", "data",
                                          "leadsmart_campaigns.json"), encoding="utf-8"))
    except Exception as e:
        print(f"catalogue unreadable ({str(e)[:60]}) — falling back to head terms")
        return {}
    out = {}
    for _name, c in (cat.get("campaigns") or {}).items():
        fn, terms = c.get("feed_niche"), c.get("probe_terms") or []
        if fn and terms:
            out[fn] = terms
    return out


# Fallback only, for a niche the catalogue has no probe list for.
TERMS = {
    "Plumbing": "plumbers", "Electrical": "electricians", "Roofing": "roofers",
    "HVAC": "hvac", "Pest Control": "pest control", "Appliance": "appliance repair",
    "Gutters": "gutters", "Tree Services": "tree service",
    "Landscaping": "landscaping", "Garage Door": "garage door repair",
    "Painting": "painters", "Siding": "siding", "Deck": "deck builders",
    "Foundation Repair": "foundation repair", "Waterproofing": "waterproofing",
    "Bathroom Remodeling": "bathroom remodeling", "Kitchen": "kitchen remodeling",
    "Water Damage": "water damage restoration", "Mold Removal": "mold removal",
    "Fire Damage Removal": "fire damage restoration",
    "Biohazard": "biohazard cleanup", "Solar": "solar installers",
}
DEFAULT_NICHES = ["Plumbing", "Electrical", "Roofing", "HVAC"]
NICHES = [n.strip() for n in (os.environ.get("NICHES") or "").split(",") if n.strip()] \
         or DEFAULT_NICHES


def norm(s):
    s = s.lower().replace("&", "and")
    s = re.sub(r"\bst\.?\s", "saint ", s + " ").strip()
    return re.sub(r"[^a-z0-9]", "", s)


def ads_client():
    try:
        from google.ads.googleads.client import GoogleAdsClient
        return GoogleAdsClient.load_from_env()
    except Exception as e:
        print(f"Ads client failed: {str(e)[:120]}")
        return None


def town_geo(client, town, state):
    """(geo_id, canonical) for a City in the right state, or (None, why)."""
    state_name = FO.STATE_NAMES.get(state, state)
    try:
        svc = client.get_service("GeoTargetConstantService")
        req = client.get_type("SuggestGeoTargetConstantsRequest")
        req.locale = "en"
        req.country_code = "US"
        req.location_names.names.append(f"{town}, {state_name}")
        for sug in svc.suggest_geo_target_constants(request=req).geo_target_constant_suggestions:
            g = sug.geo_target_constant
            parts = [p.strip() for p in g.canonical_name.split(",")]
            if (len(parts) >= 2 and g.target_type == "City"
                    and norm(parts[0]) == norm(town)
                    and norm(parts[1]) == norm(state_name)):
                return str(g.id), g.canonical_name
        return None, "no City match in this state"
    except Exception as e:
        return None, str(e)[:90]


def load_progress():
    try:
        return json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        return {}


def main():
    idx = json.load(open(INDEX, encoding="utf-8"))
    rows = idx["rows"]
    probe = load_probe()
    print(f"probe terms for {len(probe)} niche(s) from the campaign catalogue")

    def terms_for(niche):
        return probe.get(niche) or ([TERMS[niche]] if niche in TERMS else [])

    # Which towns are worth an API call, and which trades each one needs.
    want = {}
    for r in rows:
        st, town, niche, pop, pay, _z, md = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        if niche not in NICHES or niche not in TERMS:
            continue
        if pay < MIN_PAYOUT or not (MIN_POP <= pop < MAX_POP) or md < MIN_METRO_MILES:
            continue
        want.setdefault((st, town), set()).add(niche)

    keys = sorted(want)
    if MAX_TOWNS:
        keys = keys[:MAX_TOWNS]
    done = load_progress()
    todo = [k for k in keys if f"{k[0]}|{k[1]}" not in done]
    print(f"{len(keys)} town(s) qualify · {len(done)} already measured · {len(todo)} to go")
    if not todo:
        print("nothing to measure")
    client = ads_client() if todo else None
    if todo and client is None:
        print("no Ads credentials — cannot measure")
        return 1

    for n, (st, town) in enumerate(todo, 1):
        niches = sorted(want[(st, town)])
        geo_id, why = town_geo(client, town, st)
        if geo_id is None:
            print(f"   [{n}/{len(todo)}] {town}, {st}: {why}")
            done[f"{st}|{town}"] = {"geo": None}
            json.dump(done, open(STATE_FILE, "w", encoding="utf-8"))
            time.sleep(PACE)
            continue

        queries = []
        for niche in niches:
            for t in terms_for(niche):
                queries += [f"{town} {t}".lower(), f"{t} {town}".lower()]
        vol = CSV.volumes(queries, geo_id)
        if vol is None:
            print(f"   [{n}/{len(todo)}] {town}, {st}: Planner refused — waiting 30s")
            time.sleep(30)
            vol = CSV.volumes(queries, geo_id)
        if vol is None:
            print(f"   [{n}/{len(todo)}] {town}, {st}: refused twice, skipping")
            time.sleep(PACE)
            continue

        # The town's whole demand for the trade, not one keyword: measuring
        # only the head term reported El Campo roofing as an empty market
        # because nobody types "el campo roofers", which is not the same as
        # nobody needing a roof.
        got = {}
        for niche in niches:
            got[niche] = sum(
                max(vol.get(f"{town} {t}".lower(), 0), vol.get(f"{t} {town}".lower(), 0))
                for t in terms_for(niche))
        done[f"{st}|{town}"] = {"geo": geo_id, "vol": got}
        json.dump(done, open(STATE_FILE, "w", encoding="utf-8"))
        best = max(got.items(), key=lambda kv: kv[1]) if got else ("", 0)
        print(f"   [{n}/{len(todo)}] {town}, {st} [{why}] · "
              + ", ".join(f"{k} {v}" for k, v in sorted(got.items(), key=lambda kv: -kv[1])))
        time.sleep(PACE)

    # Write the volumes back as an 9th column. A town we could not measure
    # keeps null, which the page shows as "-" rather than as a zero — "we did
    # not ask" and "nobody searches it" are not the same answer.
    measured = 0
    for r in rows:
        rec = done.get(f"{r[0]}|{r[1]}")
        v = (rec or {}).get("vol", {}).get(r[2]) if rec else None
        if len(r) < 9:
            r.append(v)
        else:
            r[8] = v
        if v is not None:
            measured += 1
    if "volume" not in idx["columns"]:
        idx["columns"].append("volume")
    idx["volume_note"] = (f"'{{town}} {{trade}}' measured in that town's own Google geo, "
                          f"both word orders, larger kept. Filters: payout >= {MIN_PAYOUT}, "
                          f"pop {MIN_POP}-{MAX_POP}, metro >= {MIN_METRO_MILES} mi.")
    idx["volume_generated"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    json.dump(idx, open(INDEX, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"\n{measured:,} row(s) now carry a volume · wrote {INDEX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
