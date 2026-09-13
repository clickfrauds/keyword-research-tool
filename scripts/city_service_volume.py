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


def volumes(queries, geo_name=None):
    """Monthly searches for every query, in one request. None if Ads fails."""
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
                os.environ[key] = saved

    login = re.sub(r"\D", "", os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""))
    out, err = attempt(with_login=bool(login))
    # A manager id that does not sit above the account fails exactly like a
    # real missing permission; the message cannot tell them apart, and Ads
    # calls are free, so ask twice rather than guess.
    if out is None and login and ("PERMISSION_DENIED" in err
                                  or "doesn't have permission" in err):
        print("   denied with the manager id - retrying without it")
        out, err2 = attempt(with_login=False)
        if out is not None:
            print("   worked without it. GOOGLE_ADS_LOGIN_CUSTOMER_ID does not"
                  " manage this account.")
            return out
        err = err2
    if out is not None:
        return out
    print(f"   Ads Planner failed ({err[:100]})")
    return None


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
    tail = f" {a.state.strip().lower()}" if a.state.strip() else ""

    print(f"\n-- {len(cities)} cities x {len(services)} services "
          f"= {len(cities) * len(services)} queries, 1 Ads request, "
          f"0 SerpApi credits --\n")

    pairs = {}
    for c in cities:
        for s in services:
            pairs[f"{s.lower()} {c.lower()}{tail}"] = (c, s)

    vols = volumes(list(pairs), a.geo or None)
    if vols is None:
        sys.exit("\n   no volumes - nothing to report.")

    grid = {c: {} for c in cities}
    for q, (c, s) in pairs.items():
        grid[c][s] = vols.get(q, 0)

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
          f"out of {len(pairs)}.")
    if build:
        print("\nTop 30 pages to build first:")
        for c, s, v in build[:30]:
            print(f"   {v:>6d}  {s} in {c}")

    with open(os.path.join(HERE, "city_service_volume.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["city", "service", "volume", "build"])
        for c in ranked_cities:
            for s in ranked_svcs:
                v = grid[c].get(s, 0)
                w.writerow([c, s, v, "yes" if v >= a.min_volume else ""])

    with open(os.path.join(HERE, "city_service_volume.md"), "w",
              encoding="utf-8") as fh:
        fh.write(f"# City x service volume\n\n")
        fh.write(f"{len(cities)} cities, {len(services)} services, "
                 f"floor {a.min_volume}/mo. "
                 f"**{len(build)} of {len(pairs)}** pairs are worth a page.\n\n")
        fh.write("| city | " + " | ".join(ranked_svcs) + " | total |\n")
        fh.write("|" + "---|" * (len(ranked_svcs) + 2) + "\n")
        for c in ranked_cities:
            cells = []
            for s in ranked_svcs:
                v = grid[c].get(s, 0)
                cells.append(f"**{v}**" if v >= a.min_volume else str(v))
            fh.write(f"| {c} | " + " | ".join(cells) +
                     f" | {city_total[c]} |\n")
        fh.write("\nBold = clears the floor and is worth a page.\n")

    print("\ncity_service_volume.csv - city_service_volume.md")


if __name__ == "__main__":
    main()
