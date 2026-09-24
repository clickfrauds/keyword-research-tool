"""build_town_index.py — one ranked table of every town LeadSmart buys.

WHY THIS EXISTS
  The EMD finder answers "in THIS state, which domains are free". It cannot
  answer "where in the country should I look at all", and that is the question
  that actually picks a site. Doing it by hand meant 51 runs.

  Everything needed is already in the coverage feed: payout, population, ZIP
  count and coordinates, per town per niche. This walks all 51 state shards
  once, works out each town's distance to the nearest of the 90 metros
  find_opportunities knows, and writes a compact index the /towns page filters
  and ranks in the browser.

  No Google Ads, no SerpApi, no key of any kind. The feed is static JSON.

WHY THE METRO DISTANCE IS THE COLUMN THAT MATTERS
  Measured on the four live sites: Clovis 201 miles from Albuquerque, Bullhead
  City 80 from Las Vegas, Lawton 78 from Oklahoma City — all three earn.
  Torrance is 16 from Los Angeles, and its page one carries seven established
  firms, an EMD someone already owns and a competing lead-gen site.

SIZE
  Only towns with coordinates and a population the band could ever want are
  kept, so the file stays a couple of MB and loads in one request.

Run: python scripts/build_town_index.py  (writes data/town_index.json)
"""
import json
import math
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FEED = "https://leadsmart-coverage.netlify.app/api/state"
OUT = os.path.join(HERE, "..", "data", "town_index.json")
FUNC = os.path.join(HERE, "..", "functions", "coverage-cities.js")

# Only towns that could ever be a candidate. A 300-person ZIP has no search
# volume; a 400k city is where the agencies are.
MIN_POP = int(os.environ.get("INDEX_MIN_POP", "3000") or 3000)
MAX_POP = int(os.environ.get("INDEX_MAX_POP", "250000") or 250000)

STATES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI "
          "MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT "
          "VT VA WA WV WI WY DC").split()


def load_metros():
    """The same 90 metros the coverage function uses — read from it, so the
    two can never drift apart."""
    src = open(FUNC, encoding="utf-8").read()
    block = src.split("const US_METROS = [")[1].split("];")[0]
    return [(m[0], float(m[1]), float(m[2]))
            for m in re.findall(r'\["([^"]+)",(-?[\d.]+),(-?[\d.]+)\]', block)]


def miles(a_lat, a_lng, b_lat, b_lng):
    R, rad = 3958.8, math.pi / 180
    d_lat, d_lng = (b_lat - a_lat) * rad, (b_lng - a_lng) * rad
    s = (math.sin(d_lat / 2) ** 2 +
         math.cos(a_lat * rad) * math.cos(b_lat * rad) * math.sin(d_lng / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(s))


def fetch(state, tries=3):
    url = f"{FEED}/{state}.json"
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.load(urllib.request.urlopen(req, timeout=120))
        except Exception as e:
            if n == tries - 1:
                print(f"   !! {state}: {str(e)[:70]}")
                return None
            time.sleep(3)


def main():
    metros = load_metros()
    print(f"metros: {len(metros)}")
    rows, skipped_no_geo = [], 0

    for st in STATES:
        shard = fetch(st)
        if not shard or not shard.get("rows"):
            continue
        city, niche = shard.get("city", []), shard.get("niche", [])
        # (town, niche) -> payout, zips, and the town's own coordinates
        agg, where, pop_of = {}, {}, {}
        for r in shard["rows"]:
            try:
                town, nk = city[r[0]], niche[r[2]]
            except (IndexError, TypeError):
                continue
            pop_of[town] = max(pop_of.get(town, 0), int(r[5] or 0))
            if r[7] and town not in where:
                where[town] = (float(r[7]), float(r[8] or 0))
            e = agg.setdefault((town, nk), {"pay": 0.0, "zips": set()})
            e["pay"] = max(e["pay"], float(r[4] or 0))
            e["zips"].add(r[1])

        dist = {}
        for town, (la, ln) in where.items():
            best = min(((n, miles(la, ln, mla, mln)) for n, mla, mln in metros),
                       key=lambda x: x[1])
            dist[town] = (best[0], round(best[1]))

        kept = 0
        for (town, nk), e in agg.items():
            pop = pop_of.get(town, 0)
            if not (MIN_POP <= pop <= MAX_POP):
                continue
            if town not in dist:
                skipped_no_geo += 1
                continue
            metro, md = dist[town]
            rows.append([st, town, nk, pop, round(e["pay"], 2), len(e["zips"]),
                         md, metro])
            kept += 1
        print(f"{st}  {kept:5d} town-niche rows")

    rows.sort(key=lambda r: (-r[4], r[6]))
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "source": "leadsmart-coverage.netlify.app + the 90 metros in coverage-cities.js",
        "filters": {"min_pop": MIN_POP, "max_pop": MAX_POP},
        "columns": ["state", "town", "niche", "pop", "payout", "zips",
                    "metro_miles", "metro"],
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    size = os.path.getsize(OUT)
    print(f"\nwrote {OUT}  ({len(rows):,} rows, {size/1048576:.1f} MB)")
    print(f"towns without coordinates in the feed, skipped: {skipped_no_geo:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
