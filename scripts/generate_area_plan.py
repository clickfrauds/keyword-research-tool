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

Which areas a city HAS comes from the worldwide Google Ads geo target database
(clickadsprotector.com/geo, 246 countries) — the very same source the Ads
locations mode targets with, so every area here is a place Google recognises.
Whether an area is really IN the city is settled by OpenStreetMap geometry, not
by a model's opinion: see _keep_inside_city.

Env : GOOGLE_ADS_* (same secrets Stage 1 uses), BUSINESS_NAME,
      NICHE_DESCRIPTION, TARGET_LOCATION (a CITY — that is what returns
      sub-areas), PRIMARY_SERVICE, MIN_AREA_VOLUME (default 20),
      MAX_AREAS (blank = the whole city), LANGUAGE / LANGUAGE_ID,
      ANTHROPIC_API_KEY (only for provinces with more areas than
      GEO_VERIFY_MAX, to shortlist before the boundary check)
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
# Comma-separated area names to measure on top of whatever the geo database has —
# for districts Google cannot target but people still search ("Deira").
EXTRA_AREAS       = os.environ.get("EXTRA_AREAS", "").strip()
OUT_FILE          = "area_plan.json"

# Planner's lowest reported bucket IS 10 — there is no 1..9. A run of 402
# keywords had 336 sitting at exactly 10, i.e. "somewhere between 1 and 10".
# 20 is the first number that means measurable demand, so that is the default
# for deciding an area deserves its own page.
MIN_AREA_VOLUME = int(os.environ.get("MIN_AREA_VOLUME", "20") or 20)
# 0 / blank = every area of the city, which is the only sensible default: a cap
# does not mean "the 60 most important areas", it means "the first 60 in the geo
# file's own arbitrary order". A Dubai run capped at 60 silently left Al Mizhar,
# Al Warqa, Muhaisnah and 40 others UNMEASURED — indistinguishable, in the
# output, from areas that were measured and found empty. At 3s pacing the full
# 103 takes ~5 minutes against a 45-minute timeout, so there was nothing to save.
MAX_AREAS       = int(os.environ.get("MAX_AREAS", "0") or 0)
CALL_DELAY      = float(os.environ.get("ADS_CALL_DELAY", "3") or 3)


def names_area(k_norm, a_norm, other_areas=()):
    """Is the area named as a PLACE in this keyword, or is the word just part
    of the product?

    A plain substring test credited Dubai's "Front" district with 490/mo from
    'lg front load washer repair' — a machine type, not a location. Real local
    intent puts the place at the end ('...repair al quoz') or behind a
    preposition ('...repair in al quoz'). Anything else is a coincidence.

    The trailing-word match ('al quoz' also answering to 'quoz') is dropped when
    that word is another area's whole name: otherwise "Palm Jumeirah" would
    quietly collect every search for plain "Jumeirah", and two pages would be
    built on one area's demand.
    """
    tail = " ".join(a_norm.split()[1:])
    if tail and tail in other_areas:
        tail = ""
    for name in (a_norm, tail):
        if not name:
            continue
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", k_norm):
            before, after = k_norm[:m.start()].split(), k_norm[m.end():].split()
            if not after:                                  # at the end
                return True
            if before and before[-1] in ("in", "near", "at", "around", "of"):
                return True
    return False


# Google models a city's parts in three different shapes, and which one you get
# depends on the country:
#   parent = the city      Dubai:     "Al Quoz,Dubai,United Arab Emirates"
#   parent = the country   Singapore: "Jurong West,Singapore"          (city-state)
#   parent = the province  Karachi:   "Gulshan-e-Iqbal,Sindh,Pakistan" (no city!)
# The first two can be read straight off the canonical path. The third cannot —
# the data does not record which city a Sindh neighbourhood belongs to.
CONTAINER_TYPES = {"Province", "County", "State", "Region", "Territory", "Governorate",
                   "Prefecture", "Department", "Division", "Municipality", "City Region"}
AREA_TYPES = {"Neighborhood", "District", "Borough", "Suburb", "City",
              "Municipality", "Post town", "Ward", "City Region"}
# Fewer linked areas than this means the country uses the province shape.
DIRECT_AREAS_FLOOR = 15
# OpenStreetMap asks for at most 1 request/second, so this is how many province
# candidates can be boundary-checked inside a CI run (~3 min). Above it, Claude
# proposes a shortlist first and the boundary check still has the final word.
GEO_VERIFY_MAX = int(os.environ.get("GEO_VERIFY_MAX", "150") or 150)
# Postal Code ("washing machine repair SW1A 1AA") and TV Region are real geo
# targets that nobody searches by name, so they never earn a page.


def _nrm(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def _reply_text(msg):
    """The text of a Claude reply.

    content[0] is not reliably the answer: when the model thinks first, the
    first block is a ThinkingBlock with no .text, and reading it raised
    "'ThinkingBlock' object has no attribute 'text'" — which silently cost a
    whole run its district lookup. Take the first block that actually carries
    text, whatever position it is in.
    """
    for block in getattr(msg, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            return text.strip()
    return ""


def _areas_under(geo, containers, city_n):
    """Every area whose canonical path passes through one of `containers`."""
    out, seen = [], set()
    for g in geo:
        if g.get("t") not in AREA_TYPES:
            continue
        name = str(g.get("n", "")).strip()
        n = _nrm(name)
        # The city itself is never one of its own areas: that page would compete
        # with the site's homepage and main service page for a single term.
        if not name or n == city_n or n in seen:
            continue
        parents = {_nrm(p) for p in str(g.get("c", "")).split(",")[1:]}
        if parents & containers:
            seen.add(n)
            out.append(name)
    return out


def _nominatim(query, limit=1):
    """OpenStreetMap lookup. English results so the caller can read them."""
    import urllib.request
    import urllib.parse
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": limit, "accept-language": "en"})
    req = urllib.request.Request(url, headers={"User-Agent": "keyword-research-tool/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _city_osm(city, country):
    """The city's OSM identity: its administrative relation (for exact
    containment) and its bounding box (for the cheaper fallback)."""
    try:
        results = _nominatim(f"{city}, {country}", limit=5)
    except Exception as ex:
        print(f"   ⚠️ Could not look up {city} on OpenStreetMap: {str(ex)[:70]}")
        return None, None
    area_id, box = None, None
    for r in results:
        if box is None and r.get("boundingbox"):
            s, n, w, e = (float(x) for x in r["boundingbox"])
            box = (s, n, w, e)
        if area_id is None and r.get("osm_type") == "relation":
            # Overpass addresses a boundary relation as 3600000000 + its id
            area_id = 3600000000 + int(r["osm_id"])
        if area_id and box:
            break
    return area_id, box


def _areas_inside_boundary(area_id):
    """Every place OSM records INSIDE the city's administrative boundary, in one
    request. Far better than geocoding candidates one at a time — it asks the
    question the right way round — but Overpass is a shared free service that
    answers 429/504 under load, so the caller must be able to live without it.
    """
    import urllib.request
    import urllib.parse
    query = (f'[out:json][timeout:90];area({area_id})->.a;'
             f'node["place"~"^(suburb|neighbourhood|quarter|city_district|borough)$"]'
             f'(area.a);out tags;')
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                "https://overpass-api.de/api/interpreter",
                data=urllib.parse.urlencode({"data": query}).encode(),
                headers={"User-Agent": "keyword-research-tool/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return {_nrm(e["tags"]["name"]) for e in data.get("elements", [])
                    if e.get("tags", {}).get("name")}
        except Exception as ex:
            print(f"      OpenStreetMap boundary query attempt {attempt}/3: {str(ex)[:46]}")
            time.sleep(6 * attempt)
    return set()


def _shortlist(names, city, country, limit):
    """Too many candidates to geocode one by one — let Claude propose which are
    plausibly in the city. Only a proposal: every name it returns is still
    verified against the city's real boundary afterwards."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"   ⚠️ {len(names)} candidates is too many to geocode and "
              f"ANTHROPIC_API_KEY is not set to narrow them first.")
        return []
    try:
        import anthropic
        prompt = (
            f"Below are geo areas from the province containing {city}, {country}.\n"
            f"List the ones that are neighbourhoods, districts, boroughs or suburbs "
            f"OF {city} itself — not other cities in the province, not rural areas.\n\n"
            + "\n".join("- " + n for n in names)
            + "\n\nReply with a JSON array of the exact names, nothing else."
        )
        msg = anthropic.Anthropic().messages.create(
            model="claude-sonnet-5", max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        m = re.search(r"\[.*\]", _reply_text(msg), re.S)
        keep = set(json.loads(m.group(0))) if m else set()
        out = [n for n in names if n in keep][:limit]
        print(f"   ↳ narrowed {len(names)} province areas to {len(out)} candidates "
              f"for boundary checking")
        return out
    except Exception as e:
        print(f"   ⚠️ Could not narrow the province's areas: {str(e)[:90]}")
        return []


def _keep_inside_city(names, city, country):
    """Which of a province's areas actually lie in this city?

    Google's data cannot answer this — "Gulshan-e-Iqbal,Sindh,Pakistan" records
    the province and stops, and its Parent ID would say Sindh too, because the
    canonical path IS the parent chain. So the question is settled the same way
    Mode 5 settles coordinates: OpenStreetMap geometry, not a model's opinion.

    Two ways, and which is better depends on how many candidates there are:

      Geocoding each candidate and testing it against the city's box is the
      ACCURATE method — Nominatim's search absorbs the naming differences between
      the two datasets ("North Nazimabad Town" vs "North Nazimabad"). It is also
      rate-limited to 1/sec, so it only fits when the province is small.

      Asking OSM what lies inside the city's administrative boundary is the
      SCALABLE method: one request for any size of province. But it can only
      match the two datasets by name, and names disagree often enough that on
      Sindh it recognised 5 of 102 areas where geocoding found 62. Matching more
      loosely was tried and is not an option — subset matching handed Karachi
      "Sukkur" and "Hyderabad", and London "Manchester".

    So: geocode when the province is small enough to afford it, use the boundary
    when it is not, and let Claude shortlist only if neither is available.
    """
    if not names:
        return []
    area_id, box = _city_osm(city, country)

    # Big province — per-area geocoding would take an hour. One boundary query.
    if len(names) > GEO_VERIFY_MAX and area_id:
        inside_names = _areas_inside_boundary(area_id)
        if inside_names:
            kept = [n for n in names if _nrm(n) in inside_names]
            print(f"   📐 {len(names)} candidates is too many to geocode; OSM lists "
                  f"{len(inside_names)} places inside {city}'s boundary and {len(kept)} "
                  f"of the Google areas are among them")
            if kept:
                return kept

    if not box:
        print(f"   ⚠️ Without {city}'s boundary these areas cannot be verified, and "
              f"guessing would build pages for other cities.")
        return []
    south, north, west, east = box
    print(f"   📐 Geocoding {len(names)} candidates against {city}'s box: "
          f"lat {south:.3f}..{north:.3f}, lon {west:.3f}..{east:.3f}")

    # Nominatim's usage policy is 1 request/second, so a 3000-name province is
    # not geocodable inside a CI run. Shortlist first, then verify.
    if len(names) > GEO_VERIFY_MAX:
        names = _shortlist(names, city, country, GEO_VERIFY_MAX)

    inside, rejected = [], 0
    for n in names:
        time.sleep(1.2)                        # OSM asks for max 1 req/sec
        try:
            d = _nominatim(f"{n}, {country}")
            if not d:
                rejected += 1
                continue
            lat, lon = float(d[0]["lat"]), float(d[0]["lon"])
            if south <= lat <= north and west <= lon <= east:
                inside.append(n)
            else:
                rejected += 1
        except Exception:
            rejected += 1
    if rejected:
        print(f"   ↳ {rejected} area(s) fell outside {city}'s boundary (or could not be "
              f"located) and were dropped")
    return inside


def _wellknown_districts(city, country, already):
    """The city's famous districts that are NOT Google Ads geo targets.

    Google's own geotargets file (273,666 rows, verified against it directly)
    lists 291 places for the UAE and does not contain Deira, Bur Dubai, Al
    Karama, Satwa, JLT, Discovery Gardens or Downtown Dubai — some of the
    densest neighbourhoods in the city. OSM's suburb tagging there is mostly
    Arabic-script and covers small compounds, so it does not fill the gap
    either.

    But being un-targetable does not make a place un-searchable: people do type
    "washing machine repair deira". Seeding only from geo targets meant those
    names were never ASKED about, and a plan then showed them as absent rather
    than unmeasured. So the names are proposed here and the Planner still
    decides — a name with no volume earns no page, exactly like a geo target
    with no volume.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"   ⚠️ ANTHROPIC_API_KEY not set, so {city}'s districts that Google cannot "
              f"target were not looked up. List them in EXTRA_AREAS instead.")
        return []
    try:
        import anthropic
        have = ", ".join(sorted(already)[:150])
        prompt = (
            f"Name the districts of {city}, {country} that residents would type when "
            f"searching for a local home service.\n\n"
            "Cover ALL of these, and do not skip a category:\n"
            "  - the affluent residential communities and villa districts\n"
            "  - the towered/apartment communities where most tenants live\n"
            "  - the central business and downtown districts\n"
            "  - the older, dense, working-class neighbourhoods\n"
            "  - large master-planned or gated developments\n\n"
            "The high-end and the working-class areas matter equally here: an "
            "affluent district converts at a higher value, a dense one has more "
            "households. Aim for 40-60 names, ordered with the best-known first.\n\n"
            f"EXCLUDE these, already covered, and anything that is the same place "
            f"under another spelling:\n{have}\n\n"
            "Reply with a JSON array of names only, no commentary. Use the common "
            "English spelling a person would type into Google."
        )
        msg = anthropic.Anthropic().messages.create(
            model="claude-sonnet-5", max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        m = re.search(r"\[.*\]", _reply_text(msg), re.S)
        if not m:
            print(f"   ⚠️ No district list came back for {city} — measuring the geo areas only.")
            return []
        seen = {_nrm(a) for a in already}
        out = []
        for n in json.loads(m.group(0)):
            n = str(n).strip()
            if n and _nrm(n) not in seen:
                seen.add(_nrm(n))
                out.append(n)
        if not out:
            print(f"   ℹ️ Every district named for {city} was already in the geo list.")
        return out
    except Exception as e:
        print(f"   ⚠️ Could not look up {city}'s other districts: {str(e)[:80]}")
        return []


def _plus_districts(geo_names, city, country):
    """Geo-target areas plus the city's other well-known districts, and any the
    user typed in EXTRA_AREAS. Order matters only for logging — every name is
    measured the same way."""
    manual = [a.strip() for a in EXTRA_AREAS.split(",") if a.strip()]
    have = {_nrm(n) for n in geo_names}
    manual = [m for m in manual if _nrm(m) not in have]
    if manual:
        print(f"   ➕ {len(manual)} area(s) you listed: {', '.join(manual[:8])}")
        have |= {_nrm(m) for m in manual}
    extra = _wellknown_districts(city, country, geo_names + manual)
    if extra:
        print(f"   ➕ {len(extra)} district(s) that are not Google geo targets but are "
              f"searched by name: {', '.join(extra[:8])}"
              + (" …" if len(extra) > 8 else ""))
    total = geo_names + manual + extra
    if len(total) != len(geo_names):
        print(f"   ℹ️ {len(total)} areas to measure "
              f"({len(geo_names)} targetable + {len(manual) + len(extra)} name-only). "
              f"None becomes a page without its own volume.")
    return total


def resolve_areas():
    """Every area of TARGET_LOCATION's city worth asking the Planner about.

    Two sources, because neither is complete on its own:
      - Google Ads geo targets (the same source the Ads locations mode targets
        with) — every one of these is a place Google can target
      - the city's well-known districts, which are often missing from that list
        entirely; they cannot be TARGETED but they are certainly SEARCHED

    Demand decides in both cases. Nothing here becomes a page without its own
    measured volume.
    """
    try:
        from generate_locations import fetch_json, resolve_country, GEO_BASE
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
        country_name = next((e.get("name", "") for e in index if e.get("cc") == cc), cc)
        geo = fetch_json(f"{GEO_BASE}/{cc}.json")

        # A city-state ("Singapore, Singapore") leaves no city text once the
        # country alias is stripped — its areas hang off the country row.
        city_n = _nrm(city) or _nrm(country_name)
        city_label = (city or country_name).title()

        # Containers = the city, plus anything shaped like a bigger version of it
        # ("Greater London", "City of London", "London Borough of Ealing").
        containers = {city_n}
        for g in geo:
            if g.get("t") in CONTAINER_TYPES:
                n = _nrm(g.get("n", ""))
                if n and re.search(rf"(^| ){re.escape(city_n)}( |$)", n):
                    containers.add(n)

        names = _areas_under(geo, containers, city_n)
        # A handful of hits is not a real enumeration, it is a near-miss: Toronto
        # returns exactly one ("York") and London ten, because most of their
        # districts are recorded against the province instead. Any city worth
        # doing pSEO for has more parts than this, so below the floor the
        # canonical path is not the answer — try the province route and merge.
        if len(names) >= DIRECT_AREAS_FLOOR:
            print(f"📍 {city_label}: {len(names)} Google Ads geo areas under "
                  f"{', '.join(sorted(containers)[:3])}")
            return _plus_districts(names, city_label, country_name)
        if names:
            print(f"ℹ️ Only {len(names)} area(s) hang off {city_label} directly "
                  f"({', '.join(names)}) — checking the province too.")

        # Third shape: little or nothing hangs off the city. Fall back to its
        # province and ask which of those areas are actually in the city.
        # The city's province. Toronto's own row reads
        # "Toronto,Toronto,Ontario,Canada", so parts[1] is not reliably the
        # province — take the first parent that is neither the city again nor the
        # country.
        prov = ""
        prov_names = {_nrm(g.get("n", "")) for g in geo if g.get("t") in CONTAINER_TYPES}
        for g in geo:
            if _nrm(g.get("n", "")) == city_n and g.get("t") in ("City", "Municipality", "District"):
                parts = [p.strip() for p in str(g.get("c", "")).split(",")]
                for p in parts[1:-1]:
                    if _nrm(p) != city_n and _nrm(p) in prov_names:
                        prov = p
                        break
            if prov:
                break
        if not prov:
            if names:
                print(f"📍 {city_label}: {len(names)} Google Ads geo areas")
                return _plus_districts(names, city_label, country_name)
            print(f"ℹ️ Google's geo data for {country_name} records no areas under "
                  f"{city_label}, and no province to fall back to — going on the "
                  f"city's district names alone.")
            return _plus_districts([], city_label, country_name)
        print(f"ℹ️ {country_name}'s geo data hangs areas off the province, not the city — "
              f"reading {prov} and narrowing it to {city_label}.")
        candidates = [c for c in _areas_under(geo, {_nrm(prov)}, city_n) if c not in names]
        inside = _keep_inside_city(candidates, city_label, country_name)
        # Areas linked directly to the city are certain; the province ones passed
        # a judgement call. Keep both, certain first.
        merged = names + [n for n in inside if n not in names]
        print(f"📍 {city_label}: {len(merged)} areas "
              f"({len(names)} linked to the city, {len(inside)} of {prov}'s "
              f"{len(candidates)} identified as being in it)")
        return _plus_districts(merged, city_label, country_name)
    except Exception as e:
        print(f"❌ Could not resolve areas for '{TARGET_LOCATION}': {str(e)[:120]}")
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
    if MAX_AREAS and len(areas) > MAX_AREAS:
        print(f"⚠️ {len(areas)} areas found but MAX_AREAS caps this run at {MAX_AREAS}. "
              f"The other {len(areas) - MAX_AREAS} will be UNMEASURED, not proven empty "
              f"— clear MAX_AREAS to cover the whole city.")
        areas = areas[:MAX_AREAS]
    else:
        print(f"ℹ️ Researching all {len(areas)} areas "
              f"(~{int(len(areas) * CALL_DELAY / 60) + 1} min).")

    print(f"🔎 Service: '{PRIMARY_SERVICE}' | keeping areas with >= {MIN_AREA_VOLUME}/mo")

    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    try:
        from google.api_core.exceptions import ResourceExhausted
    except ImportError:
        class ResourceExhausted(Exception):
            pass

    # An EMPTY login-customer-id is worse than none: the client still sends the
    # header and Google rejects every request with "User doesn't have permission
    # to access customer" — which is exactly how this workflow's first run failed
    # 60 times. Dropping it when blank lets the same workflow serve both a direct
    # account and a client account under an MCC, where the header is required.
    if not os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip():
        os.environ.pop("GOOGLE_ADS_LOGIN_CUSTOMER_ID", None)
    else:
        print(f"   🔑 Using manager account "
              f"{os.environ['GOOGLE_ADS_LOGIN_CUSTOMER_ID']} to reach {CUSTOMER_ID}")

    client = GoogleAdsClient.load_from_env()
    svc = client.get_service("KeywordPlanIdeaService")

    def drop_manager_and_retry():
        """Rebuild the client without the manager header.

        Research and campaign pushes need opposite things from this secret. A
        push into a client account REQUIRES the manager id; research only needs
        an account the OAuth user can reach, and naming a manager that does not
        hold this customer makes Google refuse every request. Deleting the
        secret to fix research would then break the push, so instead the run
        falls back by itself and the secret stays correct for the push.
        """
        nonlocal client, svc
        os.environ.pop("GOOGLE_ADS_LOGIN_CUSTOMER_ID", None)
        client = GoogleAdsClient.load_from_env()
        svc = client.get_service("KeywordPlanIdeaService")

    # Planner language ids. Anything not listed researches in English.
    LANG_IDS = {"en": "1000", "ar": "1019", "hi": "1023", "es": "1003", "fr": "1002",
                "de": "1001", "tr": "1037", "ur": "1041", "ru": "1031", "zh": "1017"}
    lang_code = LANGUAGE if LANGUAGE in LANG_IDS else ""
    if LANGUAGE and not lang_code:
        # "no" is a real ISO code (Norwegian). Someone answering the form's
        # language field with "no" meaning "none" would otherwise stamp the plan
        # with a language the site is not in, so an unrecognised code is dropped
        # rather than carried forward.
        print(f"   ⚠️ language '{LANGUAGE}' not recognised — researching in English "
              f"and leaving the plan's language blank. Use one of: "
              f"{', '.join(sorted(LANG_IDS))}.")
    lang_id = LANGUAGE_ID or LANG_IDS.get(lang_code, "1000")

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

    # every area's own name, so one area cannot claim another's searches
    area_names_norm = {re.sub(r"[^a-z0-9 ]", "", a.lower()) for a in areas}
    results, skipped, api_errors = [], [], []
    quota_hit = False
    manager_dropped = False
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
                err = e.failure.errors[0]
                msg = err.message
                # Daily quota gone (QuotaError.RESOURCE_EXHAUSTED). Every
                # remaining area would fail the same way, so stop rather than
                # firing another hundred doomed requests — and keep what we
                # already measured instead of throwing the run away.
                # The manager named in GOOGLE_ADS_LOGIN_CUSTOMER_ID does not hold
                # this customer. Research does not need a manager at all, so drop
                # the header and try again rather than failing 108 times — the
                # secret stays intact for the campaign push, which does need it.
                if ("permission to access customer" in msg
                        and not manager_dropped
                        and os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip()):
                    mgr = os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]
                    print(f"   ↩️ Manager {mgr} does not manage customer {CUSTOMER_ID} — "
                          f"retrying with direct access.")
                    print(f"      (the secret is left alone: a campaign push into a "
                          f"client account still needs it)")
                    drop_manager_and_retry()
                    manager_dropped = True
                    continue
                if "RESOURCE_EXHAUSTED" in str(err.error_code) or "quota" in msg.lower():
                    print(f"   🛑 [{i}/{len(areas)}] daily API quota exhausted — stopping here.")
                    quota_hit = True
                    break
                print(f"   ⚠️ [{i}/{len(areas)}] {area}: {msg[:70]}")
                api_errors.append(msg)
                break
        if quota_hit:
            unmeasured = areas[i - 1:]
            print(f"   ↳ {len(results)} areas measured before the limit; "
                  f"{len(unmeasured)} not reached ({', '.join(unmeasured[:4])}…).")
            print("   ↳ The plan below is real but PARTIAL — re-run tomorrow, or "
                  "lower MAX_AREAS, to cover the rest.")
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
            if not names_area(k_norm, a_norm, area_names_norm):
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
    if quota_hit and not results:
        print("\n❌ The daily Google Ads API quota was already exhausted — not one "
              "area could be measured, so there is no plan to write.")
        print("   Re-run tomorrow, or check today's usage in the Ads UI: "
              "Tools & Settings → Setup → API Center.")
        sys.exit(1)
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
        "language": lang_code,
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
            "partial": quota_hit,
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
