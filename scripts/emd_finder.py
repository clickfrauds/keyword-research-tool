"""
emd_finder.py — city x service exact-match-domain finder
========================================================

The question: in THIS state, for THESE towns and THESE services, which
"{city}{service}.com" names are still unregistered, are searched at least 100
times a month by people in that town, and sit on a page one a new site can
enter?

    STAGE 1  coverage   free   LeadSmart feed: which chosen towns the buyer
                               actually pays for, and at what payout
    STAGE 2  geo        free   each town -> its own Google geo target (City,
                               in the right state). Never falls back to the
                               state or the US.
    STAGE 3  matrix     free   town x service -> "{city} {service}" and
                               "{service} {city}", one Keyword Planner request
                               per town, measured in THAT town
    STAGE 4  domain     free   {city}{service}.com, city first, exact, checked
                               against Verisign RDAP for every pair >= MIN_VOLUME
    STAGE 5  SERP       paid   page one for the free names, best first, scored
                               and judged by the same rules find_opportunities
                               uses (EMD/pSEO on page one, dedicated pages,
                               local firms, map-pack depth). Capped by
                               MAX_SERP_CHECKS and by the account balance.

WHY PER-TOWN GEO
  city_service_volume.py and find_opportunities.py measure a whole run in one
  geo — the state, or the United States when none is given. That answers "how
  many people in Arizona type 'plumber bullhead city'", which is not the
  question. Measured in the town itself, Bullhead City read 320, not the
  state-geo 880; Clovis NM read 480 for its "nm" form. The number that pays is
  the local one, so every town gets its own geo target and its own request.

WHY RDAP AND NOT A NAMECHEAP SCRAPE
  Verisign runs .com and has no premium tier for it: an unregistered .com is
  sold by every registrar at its standard price (Namecheap: $11.28 first year
  at the time of writing). A .com that Namecheap lists at a higher "premium"
  price is an aftermarket name someone already owns, and RDAP reports it as
  taken. So "free" here means "registrable at the standard price" without
  logging in anywhere or scraping a registrar that blocks bots.

API SAFETY
  Planner: one request per town (every service batched), paced 2 s, one
  patient retry after 30 s on a refusal — the 429 find_opportunities met when
  it asked for 20 states back to back. Towns are capped at MAX_CITIES.
  SerpApi: the balance is read first (free); the scan spends at most
  min(MAX_SERP_CHECKS, balance - SERP_RESERVE), and anything read in the last
  30 days comes from the shared cache for free.
"""

import os
import re
import csv
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import find_opportunities as FO          # noqa: E402  coverage, RDAP, SERP, verdicts
import city_service_volume as CSV        # noqa: E402  Keyword Planner client
import serp_client                       # noqa: E402

STATE = (os.environ.get("STATE") or "").strip().upper()
NICHE = (os.environ.get("NICHE") or "").strip()
CITIES_IN = os.environ.get("CITIES") or ""
SERVICES_IN = os.environ.get("SERVICES") or ""
MIN_VOLUME = int(os.environ.get("MIN_VOLUME", "100") or 100)
MAX_SERP_CHECKS = int(os.environ.get("MAX_SERP_CHECKS", "0") or 0)
SERP_RESERVE = int(os.environ.get("SERP_RESERVE", "10") or 0)
MAX_CITIES = int(os.environ.get("MAX_CITIES", "60") or 60)
MAX_SERVICES = int(os.environ.get("MAX_SERVICES", "40") or 40)
REQUEST_ID = (os.environ.get("REQUEST_ID") or "").strip() or "emd-local"

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICES_FILE = os.path.join(HERE, "..", "data", "leadsmart_campaigns.json")


def split_list(text):
    return [p.strip() for p in re.split(r"[,\n]", text or "") if p.strip()]


def norm(s):
    """Loose name key: 'St. George' == 'Saint George' == 'saint george'."""
    s = s.lower().replace("&", "and")
    s = re.sub(r"\bst\.?\s", "saint ", s + " ").strip()
    return re.sub(r"[^a-z0-9]", "", s)


def slug(s):
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))


# ── STAGE 1: coverage ────────────────────────────────────────────────────
def coverage(state, feed_niche):
    """{norm(city): {...}} for every town in `state` the coverage feed knows.

    The union, not the towns carrying `feed_niche`. The feed says where bids
    are live at this moment; the campaigns on the account are sold Nationwide,
    and New Mexico lists 16 towns under Electrical against 359 in total. So a
    town without a live bid is reported, not dropped — `bids` carries that
    distinction and the payout columns stay empty for it.
    """
    shard = FO.j(f"{FO.BASE}/api/state/{state}.json")
    if not shard or not shard.get("rows"):
        return {}
    city, nich, ptype = shard.get("city", []), shard.get("niche", []), shard.get("ptype", [])
    out = {}
    for r in shard["rows"]:
        try:
            name = city[r[0]]
            this_niche = nich[r[2]]
        except (IndexError, TypeError):
            continue
        k = norm(name)
        e = out.setdefault(k, {"city": name, "pop": 0, "zips": 0, "payout": 0.0,
                               "bids": False, "ptypes": set()})
        e["pop"] = max(e["pop"], int(r[5] or 0))
        # With no feed niche, the town is listed but nothing is attributed to
        # it: summing every niche would hand a dentist campaign the pest
        # control rate.
        if not feed_niche or this_niche != feed_niche:
            continue
        e["bids"] = True
        e["zips"] += 1
        e["payout"] = max(e["payout"], float(r[4] or 0))
        e["ptypes"].add(ptype[r[3]] if 0 <= r[3] < len(ptype) else "")
    for e in out.values():
        e["ptypes"] = "/".join(sorted(p for p in e["ptypes"] if p))
    return out


# ── STAGE 2: strict per-town geo ─────────────────────────────────────────
def ads_client():
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        return None
    try:
        return GoogleAdsClient.load_from_env()
    except Exception as e:
        print(f"   Ads client failed: {str(e)[:120]}")
        return None


def town_geo(client, town, state):
    """(geo_id, canonical_name) for a City in the right state, or (None, why).

    CSV.resolve_geo takes the FIRST suggestion. For a name shared across
    states that is a coin toss: "Clovis" came back as Clovis, California and
    the plan was written on California's volumes. Here a suggestion counts only
    if it is a City and its canonical name is this town in this state.
    """
    state_name = FO.STATE_NAMES.get(state, state)
    try:
        svc = client.get_service("GeoTargetConstantService")
        req = client.get_type("SuggestGeoTargetConstantsRequest")
        req.locale = "en"
        req.country_code = "US"
        req.location_names.names.append(f"{town}, {state_name}")
        seen = []
        for sug in svc.suggest_geo_target_constants(request=req).geo_target_constant_suggestions:
            g = sug.geo_target_constant
            parts = [p.strip() for p in g.canonical_name.split(",")]
            seen.append(f"{g.canonical_name} ({g.target_type})")
            if (len(parts) >= 2 and g.target_type == "City"
                    and norm(parts[0]) == norm(town)
                    and norm(parts[1]) == norm(state_name)):
                return str(g.id), g.canonical_name
        return None, "no City match; Google offered: " + ("; ".join(seen[:3]) or "nothing")
    except Exception as e:
        return None, f"geo lookup failed: {str(e)[:100]}"


# ── STAGE 3: the matrix, measured per town ───────────────────────────────
def measure(town, services, geo_id):
    """{service: volume} for one town, or None if the Planner refused twice."""
    queries = []
    for s in services:
        queries += [f"{town} {s}".lower(), f"{s} {town}".lower()]
    vol = CSV.volumes(queries, geo_id)
    if vol is None:
        print(f"   ⏳ {town}: Planner refused — waiting 30s and asking once more")
        time.sleep(30)
        vol = CSV.volumes(queries, geo_id)
    if vol is None:
        return None
    return {s: max(vol.get(f"{town} {s}".lower(), 0), vol.get(f"{s} {town}".lower(), 0))
            for s in services}


# ── STAGE 5: SERP post-mortem ────────────────────────────────────────────
def postmortem(rows):
    """Score page one for the free names, best first, within the budget."""
    if MAX_SERP_CHECKS <= 0:
        print("   MAX_SERP_CHECKS = 0 — SERP stage skipped (free run)")
        return 0
    if not FO.SERP_KEY:
        print("   no SERPAPI_API_KEY — SERP stage skipped")
        return 0
    budget = MAX_SERP_CHECKS
    left = serp_client.searches_left(FO.SERP_KEY)
    if left is not None:
        usable = max(0, left - SERP_RESERVE)
        print(f"   💳 SerpApi balance {left} · reserve {SERP_RESERVE} · usable {usable}")
        budget = min(budget, usable)
    todo = [r for r in rows if r["emd"] == "free"]
    todo.sort(key=lambda r: -(r["volume"] * (r["payout"] or 1)))
    checked = 0
    for r in todo:
        if serp_client.stats()["spent"] >= budget:
            print(f"   ⏹️ credit cap {budget} reached — {len(todo) - checked} name(s) left unjudged")
            break
        state_name = FO.STATE_NAMES.get(r["state"], r["state"])
        query = f"{r['service']} {r['city']} {r['state']}"
        loc = f"{r['city']}, {state_name}, United States"
        data = FO.serp(query, loc)
        res = FO.score_serp(data, r["service"], r["city"])
        checked += 1
        if not res:
            r["verdict"], r["why"] = "UNREAD", ["page one could not be read"]
            continue
        sc, tally, occ = res
        o = {"serp_breakdown": tally, "niche": NICHE, "serp_score": sc,
             "volume": r["volume"], "city": r["city"]}
        label, why = FO.verdict(o)
        r.update({"serp_query": query, "serp_score": sc, "verdict": label, "why": why,
                  "occupants": occ[:6] if isinstance(occ, list) else occ})
    return checked


# ── output ───────────────────────────────────────────────────────────────
def write(meta, rows, unresolved, not_bought):
    passed = [r for r in rows if r["volume"] >= MIN_VOLUME]
    free = [r for r in passed if r["emd"] == "free"]
    json.dump({"meta": meta, "rows": rows, "unresolved_towns": unresolved,
               "towns_without_buyer": not_bought},
              open("emd_matrix.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    cols = ["city", "state", "service", "volume", "domain", "emd", "payout", "bids", "pop",
            "zips", "verdict", "serp_score", "why", "geo_name"]
    with open("emd_matrix.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in sorted(rows, key=lambda r: (-r["volume"], r["city"])):
            w.writerow([("; ".join(r.get(c) or []) if c == "why" else r.get(c, "")) for c in cols])

    # The same numbers as a grid: one row per town, one column per service,
    # which is how the cross matrix is read by eye. The cell is the volume,
    # with a * when the exact .com is still free and >= MIN_VOLUME.
    services_out = list(dict.fromkeys(r["service"] for r in rows))
    cell = {(r["city"], r["service"]): r for r in rows}
    towns_out = sorted({r["city"] for r in rows},
                       key=lambda c: -max((cell[(c, s)]["volume"]
                                           for s in services_out if (c, s) in cell),
                                          default=0))
    with open("emd_grid.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["town", "population", "payout", "live bid"] + services_out)
        for c in towns_out:
            any_row = next((cell[(c, s)] for s in services_out if (c, s) in cell), {})
            line = [c, any_row.get("pop", ""), any_row.get("payout", ""),
                    "yes" if any_row.get("bids") else "no"]
            for s in services_out:
                r = cell.get((c, s))
                if not r:
                    line.append("")
                    continue
                mark = "*" if (r["emd"] == "free" and r["volume"] >= MIN_VOLUME) else ""
                line.append(f"{r['volume']}{mark}")
            w.writerow(line)

    L = [f"# EMD finder — {NICHE}, {FO.STATE_NAMES.get(STATE, STATE)}", "",
         f"- Request `{REQUEST_ID}` · coverage dataset {meta.get('dataset')}",
         f"- {meta['towns_in']} town(s) in · {meta['towns_measured']} measured in their own geo "
         f"· {len(meta['services'])} service(s) · {meta['pairs']} town x service pair(s)",
         f"- **{len(passed)}** pair(s) at ≥ {MIN_VOLUME} searches/mo · **{len(free)}** with the "
         f"exact .com still unregistered · {meta['serp_checked']} page one(s) read",
         "",
         "Volume is measured in each town's own Google geo target, not the state or the US. "
         "\"Free\" is Verisign's own registry answer: an unregistered .com sells at the "
         "registrar's standard price (Namecheap $11.28), and a name Namecheap shows at a "
         "premium price is already owned, so it reads as taken here.", ""]
    go = [r for r in free if r.get("verdict") == "GO"]
    if go:
        L += ["## GO", "", "| Domain | Searches/mo | Payout | Page one |", "|---|---|---|---|"]
        for r in sorted(go, key=lambda r: -r["volume"]):
            L.append(f"| **{r['domain']}** | {r['volume']} | ${r['payout']:.2f} | "
                     f"{'; '.join(r.get('why') or [])} |")
        L.append("")
    if free:
        L += ["## Free exact-match names at ≥ %d/mo" % MIN_VOLUME, "",
              "| Domain | Town | Service | Searches/mo | Payout | Verdict | Why |",
              "|---|---|---|---|---|---|---|"]
        for r in sorted(free, key=lambda r: -r["volume"]):
            L.append(f"| {r['domain']} | {r['city']} | {r['service']} | {r['volume']} | "
                     f"${r['payout']:.2f} | {r.get('verdict') or 'not read'} | "
                     f"{'; '.join(r.get('why') or [])} |")
        L.append("")
    taken = [r for r in passed if r["emd"] != "free"]
    if taken:
        L += ["## Enough searches, name already taken", "",
              ", ".join(f"{r['domain']} ({r['volume']})" for r in
                        sorted(taken, key=lambda r: -r["volume"])), ""]
    if unresolved:
        L += ["## Towns not measured", ""] + [f"- {t}: {why}" for t, why in unresolved] + [""]
    if not_bought:
        L += ["## Towns where LeadSmart does not buy " + NICHE, "",
              ", ".join(not_bought), ""]
    open("emd_report.md", "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L[:12]))


def main():
    print(f"── EMD finder · {NICHE} · {STATE} · request {REQUEST_ID} ──")
    if not STATE or not NICHE:
        print("❌ STATE and NICHE are required")
        return 1
    catalogue = json.load(open(SERVICES_FILE, encoding="utf-8"))["campaigns"]
    if NICHE not in catalogue:
        print(f"❌ unknown campaign {NICHE!r}. Known: {', '.join(catalogue)}")
        return 1
    campaign = catalogue[NICHE]
    feed_niche = campaign.get("feed_niche")
    services = split_list(SERVICES_IN) or campaign["services"]
    services = list(dict.fromkeys(s.lower() for s in services))[:MAX_SERVICES]
    print(f"   offer: {campaign.get('offer_title', '')} "
          f"({campaign.get('payout_type', '?')}, {campaign.get('status', '?')})")

    print("── STAGE 1: LeadSmart coverage ─────────────────────────")
    meta_feed = FO.j(f"{FO.BASE}/api/meta.json") or {}
    cov = coverage(STATE, feed_niche)
    live = sum(1 for e in cov.values() if e["bids"])
    print(f"   {len(cov)} town(s) in {STATE}; {live} with a live "
          f"{feed_niche or NICHE} bid today")
    towns = split_list(CITIES_IN)
    if not towns:
        # Auto-pick prefers towns with a live bid, then the rest by population.
        towns = [e["city"] for e in sorted(cov.values(),
                                           key=lambda e: (not e["bids"], -e["pop"]))]
    towns = list(dict.fromkeys(towns))[:MAX_CITIES]
    no_bid = [t for t in towns if not (cov.get(norm(t)) or {}).get("bids")]
    if no_bid:
        print(f"   {len(no_bid)} town(s) measured without a live bid "
              f"(the campaign is nationwide): " + ", ".join(no_bid[:10]))

    print("── STAGE 2+3: per-town geo and volume ──────────────────")
    client = ads_client()
    rows, unresolved, measured = [], [], 0
    if client is None:
        unresolved = [(t, "no Google Ads credentials") for t in towns]
    for n, town in enumerate(towns):
        if client is None:
            break
        geo_id, geo_name = town_geo(client, town, STATE)
        if geo_id is None:
            unresolved.append((town, geo_name))
            print(f"   ⚠️ {town}: {geo_name}")
            continue
        if n:
            time.sleep(2)
        vols = measure(town, services, geo_id)
        if vols is None:
            unresolved.append((town, "Keyword Planner refused twice"))
            continue
        measured += 1
        # A town typed by hand need not be in the feed at all, so this reads
        # through a default rather than indexing.
        c = cov.get(norm(town)) or {"payout": 0.0, "pop": 0, "zips": 0,
                                    "bids": False, "ptypes": ""}
        for s in services:
            rows.append({"city": town, "state": STATE, "service": s, "volume": vols.get(s, 0),
                         "domain": f"{slug(town)}{slug(s)}.com", "emd": None,
                         "payout": c["payout"], "pop": c["pop"], "zips": c["zips"],
                         "bids": c["bids"], "ptype": c["ptypes"],
                         "geo_id": geo_id, "geo_name": geo_name,
                         "verdict": None, "why": None})
        top = sorted(vols.items(), key=lambda kv: -kv[1])[:3]
        print(f"   {town} [{geo_name}] · " + ", ".join(f"{s} {v}" for s, v in top))

    print("── STAGE 4: exact-match .com, RDAP ─────────────────────")
    for r in rows:
        if r["volume"] >= MIN_VOLUME:
            r["emd"] = FO._rdap(r["domain"])
            time.sleep(0.3)
    free = [r for r in rows if r["emd"] == "free"]
    print(f"   {sum(1 for r in rows if r['volume'] >= MIN_VOLUME)} pair(s) at ≥ {MIN_VOLUME} · "
          f"{len(free)} free")

    print("── STAGE 5: SERP post-mortem ───────────────────────────")
    checked = postmortem(rows)

    meta = {"request_id": REQUEST_ID, "state": STATE, "niche": NICHE,
            "services": services, "towns_in": len(towns) + len(not_bought),
            "towns_measured": measured, "pairs": len(rows), "min_volume": MIN_VOLUME,
            "serp_checked": checked, "dataset": meta_feed.get("data_date"),
            "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
    write(meta, rows, unresolved, not_bought)
    return 0


if __name__ == "__main__":
    sys.exit(main())
