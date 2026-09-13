#!/usr/bin/env python3
"""Which city, and which service in it — one table, no SerpApi credits.

The question this answers is "we have 30 cities and 33 services, where do the
first 30 pages go". Nothing in this repo answered it. mode5_areas comes
closest, but it takes ONE service and spends most of its effort discovering
neighbourhoods INSIDE a city through OpenStreetMap — the wrong half of the
work when the cities themselves are what is being compared, and it would need
one run per service.

Every "{service} {city}" pair goes to the Keyword Planner in a single
GenerateKeywordHistoricalMetrics call (it takes up to 10,000 keywords), so 30
cities by 33 services is one request and costs nothing.

    python scripts/city_service_volume.py \\
        --cities "Phoenix, Mesa, Glendale" \\
        --services "leak detection, drain cleaning" \\
        --state AZ

Writes city_service_volume.csv and .md.
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


#: Most the Planner will accept in one GenerateKeywordHistoricalMetrics call.
BATCH = 10000


def volumes(queries, geo_name=None):
    """Monthly searches for every query. None if Ads fails.

    Batched, because the request cap is 10,000 keywords and the obvious
    `queries[:10000]` drops the rest without saying so -- a 300-city run would
    have reported confidently on the first third and left the other 200 cities
    reading zero, which is indistinguishable from "no demand". Ads calls are
    free, so the only cost of another request is a second or two.
    """
    cust = re.sub(r"\D", "", os.environ.get("GOOGLE_ADS_CUSTOMER_ID", ""))
    if not cust:
        print("   no GOOGLE_ADS_CUSTOMER_ID")
        return None
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        print("   google-ads not installed")
        return None

    def attempt(with_login, chunk):
        key = "GOOGLE_ADS_LOGIN_CUSTOMER_ID"
        saved = os.environ.pop(key, None) if not with_login else None
        try:
            client = GoogleAdsClient.load_from_env()
            geo_id = None
            if geo_name:
                try:
                    svc = client.get_service("GeoTargetConstantService")
                    req = client.get_type("SuggestGeoTargetConstantsRequest")
                    req.locale = "en"
                    req.country_code = "US"
                    req.location_names.names.append(geo_name)
                    for sug in svc.suggest_geo_target_constants(
                            request=req).geo_target_constant_suggestions:
                        g = sug.geo_target_constant
                        if g.target_type in ("State", "Province", "City", "Country"):
                            print(f"   geo: {g.canonical_name}")
                            geo_id = g.resource_name.split("/")[-1]
                            break
                except Exception as e:
                    print(f"   geo lookup failed ({str(e)[:50]}) - using US")
            svc = client.get_service("KeywordPlanIdeaService")
            req = client.get_type("GenerateKeywordHistoricalMetricsRequest")
            req.customer_id = cust
            req.keywords.extend(chunk)
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
                os.environ[key] = saved

    login = re.sub(r"\D", "", os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""))
    chunks = [queries[i:i + BATCH] for i in range(0, len(queries), BATCH)]
    if len(chunks) > 1:
        print(f"   {len(queries)} queries -> {len(chunks)} requests "
              f"({BATCH} per request)")

    use_login = bool(login)
    merged = {}
    for n, chunk in enumerate(chunks, 1):
        out, err = attempt(use_login, chunk)
        # A manager id that does not sit above the account fails exactly like
        # a real missing permission; the message cannot tell them apart, and
        # Ads calls are free, so ask twice rather than guess. Only on the
        # first chunk -- after that the answer is known.
        if out is None and use_login and ("PERMISSION_DENIED" in err
                                          or "doesn't have permission" in err):
            print("   denied with the manager id - retrying without it")
            out, err2 = attempt(False, chunk)
            if out is not None:
                print("   worked without it. GOOGLE_ADS_LOGIN_CUSTOMER_ID does"
                      " not manage this account.")
                use_login = False
            else:
                err = err2
        if out is None:
            print(f"   Ads Planner failed on request {n}/{len(chunks)} "
                  f"({err[:90]})")
            # Partial data is worse than none: the missing half reads as zero
            # demand, which is a real answer this run did not earn.
            return None
        merged.update(out)
        if len(chunks) > 1:
            print(f"   request {n}/{len(chunks)} ok "
                  f"({len(merged)} of {len(queries)})")
    return merged


def split_list(text):
    return [x.strip() for x in re.split(r"[,\n;|]", text or "") if x.strip()]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cities", required=True,
                    help="comma-separated city names")
    ap.add_argument("--services", required=True,
                    help="comma-separated service names")
    ap.add_argument("--state", default="",
                    help="two-letter state appended to every query, e.g. AZ. "
                         "Callers type it, so the query should carry it.")
    ap.add_argument("--geo", default="",
                    help="geo target for the volume lookup, e.g. Arizona. "
                         "Blank = United States.")
    ap.add_argument("--min-volume", type=int, default=20,
                    help="a city/service pair below this is not worth a page")
    a = ap.parse_args()

    cities = split_list(a.cities)
    services = split_list(a.services)
    st = a.state.strip().lower()

    # Both spellings, because guessing wrong silently halves every number.
    # The first run appended "az" to all 924 queries and reported Phoenix at
    # 860 searches a month across 33 services -- far too little for a city of
    # 1.7 million, because "leak detection phoenix az" is a narrower phrase
    # than "leak detection phoenix". Asking for both costs one more request at
    # most, and the difference is itself worth knowing: it says how this
    # market actually types.
    variants = {}
    for c in cities:
        for s in services:
            plain = f"{s.lower()} {c.lower()}"
            variants[plain] = (c, s, "plain")
            if st:
                variants[f"{plain} {st}"] = (c, s, "state")

    n_pairs = len(cities) * len(services)
    print(f"\n-- {len(cities)} cities x {len(services)} services "
          f"= {n_pairs} pairs, {len(variants)} queries, "
          f"0 SerpApi credits --\n")

    vols = volumes(list(variants), a.geo or None)
    if vols is None:
        sys.exit("\n   no volumes - nothing to report.")

    grid = {c: {} for c in cities}
    shape = {c: {} for c in cities}
    won = {"plain": 0, "state": 0}
    for q, (c, s, kind) in variants.items():
        v = vols.get(q, 0)
        if v > grid[c].get(s, -1):
            grid[c][s] = v
            shape[c][s] = kind
    for c in cities:
        for s in services:
            if grid[c].get(s, 0) > 0:
                won[shape[c][s]] += 1

    if st and (won["plain"] or won["state"]):
        total = won["plain"] + won["state"]
        print(f"   query shape: '{{service}} {{city}}' wins {won['plain']}/{total}, "
              f"'... {st}' wins {won['state']}/{total}")
        if won["plain"] > won["state"] * 2:
            print(f"   -> people here mostly leave '{st}' off. "
                  f"Titles and pages should match that.")

    city_total = {c: sum(v.values()) for c, v in grid.items()}
    svc_total = {s: sum(grid[c].get(s, 0) for c in cities) for s in services}
    ranked_cities = sorted(cities, key=lambda c: -city_total[c])
    ranked_svcs = sorted(services, key=lambda s: -svc_total[s])

    # ---- city ranking -----------------------------------------------------
    print(f"{'city':22s} {'total/mo':>9s} {'pairs >= ' + str(a.min_volume):>14s}"
          f"  best service")
    print("-" * 74)
    for c in ranked_cities:
        strong = sum(1 for v in grid[c].values() if v >= a.min_volume)
        best = max(grid[c].items(), key=lambda kv: kv[1]) if grid[c] else ("", 0)
        note = "" if strong else "   <- nothing clears the floor"
        print(f"{c[:21]:22s} {city_total[c]:>9d} {strong:>14d}  "
              f"{best[0]} ({best[1]}){note}")

    # ---- service ranking --------------------------------------------------
    print(f"\n{'service':30s} {'total/mo':>9s} {'cities >= ' + str(a.min_volume):>15s}")
    print("-" * 58)
    for s in ranked_svcs:
        n = sum(1 for c in cities if grid[c].get(s, 0) >= a.min_volume)
        print(f"{s[:29]:30s} {svc_total[s]:>9d} {n:>15d}")

    # ---- what to build ----------------------------------------------------
    build = [(c, s, grid[c][s]) for c in cities for s in services
             if grid[c].get(s, 0) >= a.min_volume]
    build.sort(key=lambda t: -t[2])
    print(f"\n{len(build)} city/service pairs clear {a.min_volume}/mo "
          f"out of {n_pairs}.")
    if build:
        print("\nTop 30 pages to build first:")
        for c, s, v in build[:30]:
            print(f"   {v:>6d}  {s} in {c}")

    # Two files, because they answer different questions. The matrix is what
    # you open in a spreadsheet and read across; the page list is what you
    # work down.
    with open(os.path.join(HERE, "city_service_matrix.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        # demand_rank, not population_rank: these are ranked by searches, and
        # the two orders are not the same -- that difference is the finding.
        w.writerow(["city", "demand_rank", "total_per_mo",
                    "pairs_over_floor"] + ranked_svcs)
        for i, c in enumerate(ranked_cities, 1):
            strong = sum(1 for v in grid[c].values() if v >= a.min_volume)
            w.writerow([c, i, city_total[c], strong] +
                       [grid[c].get(s, 0) for s in ranked_svcs])
        # A totals row, so the sheet can be sorted by column without losing it
        w.writerow(["TOTAL", "", sum(city_total.values()),
                    len(build)] + [svc_total[s] for s in ranked_svcs])

    with open(os.path.join(HERE, "city_service_pages.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "city", "service", "volume", "build",
                    "suggested_url"])
        allpairs = sorted(((c, s, grid[c].get(s, 0))
                           for c in cities for s in services),
                          key=lambda t: -t[2])
        for i, (c, s, v) in enumerate(allpairs, 1):
            slug_city = re.sub(r"[^a-z0-9]+", "-", c.lower()).strip("-")
            slug_svc = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
            w.writerow([i, c, s, v, "yes" if v >= a.min_volume else "",
                        f"/{slug_city}/{slug_svc}/"])

    # A grid of 30 cities by 33 services is 35 markdown columns, which no one
    # can read and GitHub renders as a horizontal scrollbar. Past ten services
    # the same numbers go out per city instead, strongest first -- which is the
    # shape the answer is wanted in anyway: what do I build in this city.
    WIDE_MAX = 10
    with open(os.path.join(HERE, "city_service_volume.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# City x service volume\n\n")
        fh.write(f"{len(cities)} cities, {len(services)} services, "
                 f"floor {a.min_volume}/mo. "
                 f"**{len(build)} of {n_pairs}** pairs are worth a page.\n\n")

        if build:
            fh.write("## Build these first\n\n| # | page | searches/mo |\n")
            fh.write("|---|---|---|\n")
            for i, (c, s, v) in enumerate(build[:50], 1):
                fh.write(f"| {i} | {s} in {c} | {v} |\n")
            if len(build) > 50:
                fh.write(f"\n...and {len(build) - 50} more in the CSV.\n")
            fh.write("\n")

        fh.write("## Cities\n\n| city | total/mo | pairs over floor |"
                 " best service |\n|---|---|---|---|\n")
        for c in ranked_cities:
            strong = sum(1 for v in grid[c].values() if v >= a.min_volume)
            best = max(grid[c].items(), key=lambda kv: kv[1]) if grid[c] else ("", 0)
            fh.write(f"| {c} | {city_total[c]} | {strong} | "
                     f"{best[0]} ({best[1]}) |\n")

        fh.write("\n## Services\n\n| service | total/mo | cities over floor |"
                 "\n|---|---|---|\n")
        for s in ranked_svcs:
            n = sum(1 for c in cities if grid[c].get(s, 0) >= a.min_volume)
            fh.write(f"| {s} | {svc_total[s]} | {n} |\n")

        if len(services) <= WIDE_MAX:
            fh.write("\n## Full grid\n\n")
            fh.write("| city | " + " | ".join(ranked_svcs) + " | total |\n")
            fh.write("|" + "---|" * (len(ranked_svcs) + 2) + "\n")
            for c in ranked_cities:
                cells = [(f"**{grid[c].get(s, 0)}**"
                          if grid[c].get(s, 0) >= a.min_volume
                          else str(grid[c].get(s, 0))) for s in ranked_svcs]
                fh.write(f"| {c} | " + " | ".join(cells) +
                         f" | {city_total[c]} |\n")
            fh.write("\nBold = clears the floor and is worth a page.\n")
        else:
            fh.write(f"\n## Per city\n\nTop services in each city. "
                     f"The full {len(cities)}x{len(services)} grid is in the "
                     f"matrix CSV.\n\n")
            for c in ranked_cities:
                rows = sorted(grid[c].items(), key=lambda kv: -kv[1])
                over = [r for r in rows if r[1] >= a.min_volume]
                fh.write(f"**{c}** - {city_total[c]}/mo total, "
                         f"{len(over)} worth building\n\n")
                if over:
                    fh.write("  " + " · ".join(f"{s} ({v})"
                                               for s, v in over[:12]) + "\n\n")
                else:
                    fh.write(f"  nothing over {a.min_volume}/mo - "
                             f"best was {rows[0][0]} ({rows[0][1]})\n\n")

    print("\ncity_service_matrix.csv  (the grid, for a spreadsheet)")
    print("city_service_pages.csv   (every pair ranked, with its URL)")
    print("city_service_volume.md   (the summary)")


if __name__ == "__main__":
    main()
