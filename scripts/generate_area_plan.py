"""
generate_area_plan.py  (MODE 5 DELIVERABLE — area-wise keyword research)
----------------------------------------------------------------------
The shared .seo.json answers "which topics", not "which areas". Its
mode5_pseo block only ever contained the areas that happened to appear in
the seed run's keywords — a Dubai run measured 6 areas while the city has
103 real ones, and the other 97 were unknowns the builder could only guess
at. Building pages on a guess is how a site ends up with doorway pages.

This asks the question directly, one area at a time:

    for each real geo area of the target city
        GenerateKeywordIdeas(seed = "{service} {area}")
        keep it only if Google reports real demand

One request per area on purpose. A multi-seed request makes the Planner
INTERSECT the themes and return a fraction of the ideas — the same lesson
keyword_research.py learned when a 6-seed request came back with 45 ideas
and 6 separate requests returned 545.

Output: area_plan.json, published as {REQUEST_ID}.mode5.json. It carries the
same mode5_pseo.areas[] shape the website builder already reads, so Mode 5
needs no changes to consume it.

WHAT THIS FILE DOES *NOT* CARRY (by design):
  - neighbourhood/landmark/transport profiles → the builder generates those
    per area with one Claude call (place knowledge, not keyword data)
  - coordinates                               → OpenStreetMap at build time
  - header/footer/brand                       → adopted from the live site
  - internal links                            → the live site's sitemap

Env : GOOGLE_ADS_* (same secrets Stage 1 uses), ANTHROPIC_API_KEY (optional,
      for per-area angles), BUSINESS_NAME, NICHE_DESCRIPTION,
      TARGET_LOCATION (a CITY — that is what returns sub-areas),
      PRIMARY_SERVICE, MIN_AREA_VOLUME (default 20), MAX_AREAS (default 60),
      LANGUAGE / LANGUAGE_ID
Out : area_plan.json
"""

import os
import re
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BUSINESS_NAME     = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION   = os.environ.get("TARGET_LOCATION", "").strip()
PRIMARY_SERVICE   = (os.environ.get("PRIMARY_SERVICE", "").strip()
                     or NICHE_DESCRIPTION.split(",")[0].strip()
                     or "services")
CUSTOMER_ID       = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
LANGUAGE_ID       = os.environ.get("LANGUAGE_ID", "").strip()
LANGUAGE          = os.environ.get("LANGUAGE", "").strip().lower()
OUT_FILE          = "area_plan.json"

# Planner's lowest reported bucket IS 10 — there is no 1..9. A run of 402
# keywords had 336 sitting at exactly 10, i.e. "somewhere between 1 and 10".
# 20 is the first number that means measurable demand, so that is the default
# for deciding an area deserves its own page.
MIN_AREA_VOLUME = int(os.environ.get("MIN_AREA_VOLUME", "20") or 20)
MAX_AREAS       = int(os.environ.get("MAX_AREAS", "60") or 60)
CALL_DELAY      = float(os.environ.get("ADS_CALL_DELAY", "3") or 3)


def names_area(k_norm, a_norm):
    """Is the area named as a PLACE in this keyword, or is the word just part
    of the product?

    A plain substring test credited Dubai's "Front" district with 490/mo from
    'lg front load washer repair' — a machine type, not a location. Real local
    intent puts the place at the end ('...repair al quoz') or behind a
    preposition ('...repair in al quoz'). Anything else is a coincidence.
    """
    for name in (a_norm, " ".join(a_norm.split()[1:])):   # 'al quoz' / 'quoz'
        if not name:
            continue
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", k_norm):
            before, after = k_norm[:m.start()].split(), k_norm[m.end():].split()
            if not after:                                  # at the end
                return True
            if before and before[-1] in ("in", "near", "at", "around", "of"):
                return True
    return False


def resolve_areas():
    """Every real Google Ads geo area for TARGET_LOCATION (city → its
    neighbourhoods/districts; country → its cities)."""
    try:
        from generate_locations import fetch_json, resolve_country, pick_locations, GEO_BASE
        index = fetch_json(f"{GEO_BASE}/index.json")
        cc, city = resolve_country(TARGET_LOCATION, index)
        if not cc:
            # the resolver needs the country to pick the right geo file:
            # "Dubai" alone resolves to nothing, "Dubai, UAE" returns 107 areas
            if "," not in TARGET_LOCATION:
                print(f"❌ '{TARGET_LOCATION}' could not be resolved. Write the location as "
                      f"CITY, COUNTRY — e.g. '{TARGET_LOCATION}, UAE' — so the right country's "
                      f"geo list is used.")
            return []
        geo = fetch_json(f"{GEO_BASE}/{cc}.json")
        # The city itself comes back in its own area list, and it out-ranks every
        # district (Dubai: 9290/mo vs Al Qusais 270). But a "washing machine
        # repair Dubai" area page competes with the site's own homepage and main
        # service page for the same term — the one thing pSEO must not do. Areas
        # are the parts of the city, never the city.
        city_norm = re.sub(r"[^a-z]", "", (city or TARGET_LOCATION.split(",")[0]).lower())
        names, seen = [], []
        for g in pick_locations(geo, city):
            n = str(g.get("n", "")).strip()
            if n and n.lower() not in seen:
                if re.sub(r"[^a-z]", "", n.lower()) == city_norm:
                    continue
                seen.append(n.lower())
                names.append(n)
        return names
    except Exception as e:
        print(f"❌ Could not resolve areas for '{TARGET_LOCATION}': {str(e)[:100]}")
        return []


def classify_trend(vols):
    if len(vols) < 6:
        return "UNKNOWN"
    first, last = sum(vols[:3]) / 3.0, sum(vols[-3:]) / 3.0
    if first == 0:
        return "GROWING" if last else "UNKNOWN"
    ch = (last - first) / first
    if ch > 0.25:
        return "GROWING"
    if ch < -0.25:
        return "DECLINING"
    peak, avg = max(vols), sum(vols) / len(vols)
    return "SEASONAL" if avg and peak > avg * 1.8 else "STABLE"


def peak_months(monthly):
    if not monthly:
        return ""
    avg = sum(m.monthly_searches for m in monthly) / len(monthly)
    names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
             7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    return "/".join(names.get(int(m.month), "") for m in monthly
                    if m.monthly_searches > avg * 1.2)


def main():
    if not TARGET_LOCATION:
        print("❌ TARGET_LOCATION is required (use a CITY — that is what returns sub-areas).")
        sys.exit(1)

    areas = resolve_areas()
    if not areas:
        print("❌ No geo areas resolved — nothing to research.")
        sys.exit(1)
    if len(areas) > MAX_AREAS:
        print(f"ℹ️ {len(areas)} areas found — researching the first {MAX_AREAS} "
              f"(raise MAX_AREAS to cover more).")
        areas = areas[:MAX_AREAS]

    print(f"📍 {TARGET_LOCATION}: {len(areas)} real geo areas")
    print(f"🔎 Service: '{PRIMARY_SERVICE}' | keeping areas with >= {MIN_AREA_VOLUME}/mo")

    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    try:
        from google.api_core.exceptions import ResourceExhausted
    except ImportError:
        class ResourceExhausted(Exception):
            pass

    client = GoogleAdsClient.load_from_env()
    svc = client.get_service("KeywordPlanIdeaService")

    lang_id = LANGUAGE_ID or {"ar": "1019", "hi": "1023"}.get(LANGUAGE, "1000")

    # geo target for the CITY itself — every request is scoped to it, so an
    # area's volume is its share of that city's demand, not the country's
    location_id = None
    try:
        from generate_locations import fetch_json, resolve_country, GEO_BASE
        index = fetch_json(f"{GEO_BASE}/index.json")
        cc, city = resolve_country(TARGET_LOCATION, index)
        geo = fetch_json(f"{GEO_BASE}/{cc}.json") if cc else []
        want = re.sub(r"[^a-z]", "", (city or TARGET_LOCATION).lower())
        for g in geo:
            if re.sub(r"[^a-z]", "", str(g.get("n", "")).lower()) == want:
                location_id = str(g.get("id"))
                break
    except Exception:
        pass
    print(f"🌍 Geo target: {location_id or 'none (country-wide)'} | language {lang_id}")

    def ideas_for(seed):
        req = client.get_type("GenerateKeywordIdeasRequest")
        req.customer_id = CUSTOMER_ID
        req.language = f"languageConstants/{lang_id}"
        if location_id:
            req.geo_target_constants.append(f"geoTargetConstants/{location_id}")
        req.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        req.keyword_seed.keywords.extend([seed])
        req.historical_metrics_options.include_average_cpc = True
        return svc.generate_keyword_ideas(request=req)

    results, skipped, api_errors = [], [], []
    for i, area in enumerate(areas, 1):
        seed = f"{PRIMARY_SERVICE} {area}"
        resp = None
        for attempt in range(1, 4):
            try:
                resp = ideas_for(seed)
                break
            except ResourceExhausted:
                wait = 5 * attempt
                print(f"   ⏳ rate limit — waiting {wait}s ({attempt}/3)")
                time.sleep(wait)
            except GoogleAdsException as e:
                msg = e.failure.errors[0].message
                print(f"   ⚠️ [{i}/{len(areas)}] {area}: {msg[:70]}")
                api_errors.append(msg)
                break
        if resp is None:
            skipped.append(area)
            time.sleep(CALL_DELAY)
            continue

        rows, a_norm = [], re.sub(r"[^a-z0-9 ]", "", area.lower())
        for idea in resp:
            m = idea.keyword_idea_metrics
            vol = m.avg_monthly_searches or 0
            if vol <= 0:
                continue
            # only keywords that actually name THIS area — an idea list for
            # "washing machine repair al barsha" is full of city-wide terms
            k_norm = re.sub(r"[^a-z0-9 ]", "", idea.text.lower())
            if not names_area(k_norm, a_norm):
                continue
            monthly = sorted(list(m.monthly_search_volumes), key=lambda x: (x.year, x.month))
            rows.append({
                "keyword": idea.text,
                "volume": vol,
                "kd": m.competition_index or 0,
                "cpc_low": round((m.low_top_of_page_bid_micros or 0) / 1_000_000, 2),
                "cpc_high": round((m.high_top_of_page_bid_micros or 0) / 1_000_000, 2),
                "trend": classify_trend([x.monthly_searches for x in monthly]),
                "peak_months": peak_months(monthly),
            })
        rows.sort(key=lambda r: -r["volume"])
        total = sum(r["volume"] for r in rows)
        if rows and total >= MIN_AREA_VOLUME:
            results.append({"area": area, "keywords": rows[:25],
                            "total_volume": total, "primary_keyword": rows[0],
                            "demand": "measured"})
            print(f"   ✅ [{i}/{len(areas)}] {area:<28} {total:>5}/mo  «{rows[0]['keyword'][:44]}»")
        else:
            skipped.append(area)
            print(f"   ·  [{i}/{len(areas)}] {area:<28} {total or 0:>5}/mo  — below threshold")
        time.sleep(CALL_DELAY)

    # An API that rejected EVERY request is a broken run, not a city without
    # demand. The first version printed "written ✅" over 60 auth failures and
    # exited 0, which would have handed the builder an empty plan as if the
    # research had succeeded.
    if api_errors and not results:
        print(f"\n❌ Every one of the {len(api_errors)} requests was rejected by the Google Ads "
              f"API — no research happened.")
        print(f"   First error: {api_errors[0][:160]}")
        if "permission to access customer" in api_errors[0]:
            print("   This is a credentials problem, not a data problem: check "
                  "GOOGLE_ADS_CUSTOMER_ID, and set GOOGLE_ADS_LOGIN_CUSTOMER_ID only if the "
                  "account really sits under an MCC (an empty value breaks the header).")
        sys.exit(1)
    if api_errors:
        print(f"\n⚠️ {len(api_errors)} of {len(areas)} requests failed at the API — "
              f"those areas are unmeasured, not proven empty.")

    results.sort(key=lambda a: -a["total_volume"])
    print(f"\n📊 {len(results)} areas worth a page, {len(skipped)} below {MIN_AREA_VOLUME}/mo")

    out = {
        "business": {"name": BUSINESS_NAME, "niche": NICHE_DESCRIPTION,
                     "location": TARGET_LOCATION},
        "language": LANGUAGE or "",
        "primary_service": PRIMARY_SERVICE,
        "research": {
            "areas_checked": len(areas),
            "areas_kept": len(results),
            "min_volume": MIN_AREA_VOLUME,
            "note": ("Google Keyword Planner reports no value between 1 and 9 — its lowest "
                     "bucket is 10. Areas below the threshold were measured and found "
                     "without demand; building pages for them would be doorway pages."),
        },
        # the exact shape the website builder's Mode 5 already reads
        "mode5_pseo": {
            "areas": results,
            "cities_in_data": [],
            "recommended_city_targets": [TARGET_LOCATION] if results else [],
            "geo_area_candidates": areas,
            "notes": (f"{len(results)} of {len(areas)} areas in {TARGET_LOCATION} have their own "
                      f"measured demand for '{PRIMARY_SERVICE}'."),
        },
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"✅ {OUT_FILE} written — paste its published link into Mode 5's plan URL field.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Area plan failed: {e}")
        sys.exit(1)
