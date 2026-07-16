"""
generate_locations.py  (STAGE 3.9 — Editor-ready location targeting)
----------------------------------------------------------------------
Takes TARGET_LOCATION (the same free text the pipeline already uses) and
produces locations_editor.csv — Google Ads Editor location rows for every
campaign in keyword_strategy.json, using REAL Google geo target ids.

DATA SOURCE: the ClickAds Protector geo dataset (geo/{CC}.json on
clickadsprotector.com — the exact same files the AI Targeting Tool uses,
so the CSV format and ids are already proven in Editor imports). Fetched
at runtime; any failure = stage skipped, never fatal.

RELEVANCE LOGIC (mirrors the targeting tool):
  - "Abu Dhabi, UAE"  -> the Abu Dhabi City + Province rows PLUS every
    location whose canonical name sits inside that province (Al Ain...).
  - "Dubai, UAE"      -> Dubai City + Dubai Province + sub-locations.
  - "United States"   -> the Country row + every State/Province row
    (city-level for a whole country would be thousands of rows; states
    is what a Search campaign actually needs — tighten later in Editor).
  - Row cap keeps the CSV Editor-friendly.

CSV FORMAT: identical header to the targeting tool's exportLocations()
(Campaign / ID / Location / ... / Campaign Status=Paused) — Editor matches
campaigns by name and creates them Paused if they don't exist yet.

Env vars: TARGET_LOCATION   (required)
Optional: GEO_BASE_URL (default https://clickadsprotector.com/geo)
          MAX_LOCATION_ROWS (default 300 per campaign)
Input : keyword_strategy.json
Output: locations_editor.csv, locations.md
"""

import os
import re
import sys
import csv
import json
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()
GEO_BASE = os.environ.get("GEO_BASE_URL", "https://clickadsprotector.com/geo").rstrip("/")
MAX_ROWS = int(os.environ.get("MAX_LOCATION_ROWS", "300"))

INPUT_JSON = "keyword_strategy.json"
OUT_CSV = "locations_editor.csv"
OUT_MD = "locations.md"

# Free-text aliases people actually type -> ISO country code
COUNTRY_ALIASES = {
    "uae": "AE", "u.a.e": "AE", "united arab emirates": "AE", "emirates": "AE",
    "usa": "US", "u.s.a": "US", "us": "US", "united states": "US",
    "united states of america": "US", "america": "US",
    "uk": "GB", "u.k": "GB", "united kingdom": "GB", "england": "GB",
    "great britain": "GB", "britain": "GB",
    "ksa": "SA", "saudi arabia": "SA", "saudi": "SA",
    "pakistan": "PK", "india": "IN", "canada": "CA", "australia": "AU",
    "qatar": "QA", "kuwait": "KW", "bahrain": "BH", "oman": "OM",
}


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "keyword-research-tool"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", "", str(s).lower()).strip()


def resolve_country(target, index):
    """Return (country_code, city_part_or_empty) from free text."""
    t = norm(target)
    name_to_cc = {norm(e.get("name", "")): e.get("cc") for e in index if e.get("cc")}

    # longest alias/name found anywhere in the text wins
    best_cc, best_len, matched = None, 0, ""
    for alias, cc in list(COUNTRY_ALIASES.items()) + [(n, c) for n, c in name_to_cc.items() if n]:
        if alias and re.search(r"(^|\s)" + re.escape(alias) + r"(\s|$)", t) and len(alias) > best_len:
            best_cc, best_len, matched = cc, len(alias), alias
    if not best_cc:
        return None, ""
    city = t.replace(matched, " ")
    city = re.sub(r"\s+", " ", city).strip(" ,")
    return best_cc, city


def pick_locations(geo, city):
    """geo = list of {id,n,c,t}. Returns the relevant subset."""
    if city:
        cn = norm(city)
        exact = [g for g in geo if norm(g.get("n", "")) == cn]
        if exact:
            # the location itself (city and/or province) + everything whose
            # canonical path passes through a matching province
            prov_names = {g["n"] for g in exact if g.get("t") == "Province"}
            inside = [g for g in geo
                      if any(("," + p + ",") in ("," + g.get("c", "") + ",")
                             for p in prov_names) and g not in exact]
            return exact + inside
        # partial fallback: any location containing the city text
        part = [g for g in geo if cn in norm(g.get("n", ""))]
        if part:
            return part
    # country-level: country row + all provinces/states
    country = [g for g in geo if g.get("t") == "Country"]
    provinces = [g for g in geo if g.get("t") in ("Province", "State", "Region",
                                                  "Governorate", "Territory")]
    return country + sorted(provinces, key=lambda g: g.get("n", ""))


def main():
    if not TARGET_LOCATION:
        print("⚠️ TARGET_LOCATION empty — skipping location targeting stage.")
        return
    if not os.path.exists(INPUT_JSON):
        print(f"⚠️ {INPUT_JSON} not found — skipping location targeting stage.")
        return
    with open(INPUT_JSON, encoding="utf-8") as f:
        strategy = json.load(f)
    campaigns = [c.get("name") for c in (strategy.get("campaigns") or []) if c.get("name")]
    if not campaigns:
        campaigns = sorted({g.get("campaign") for g in (strategy.get("ad_groups") or [])
                            if g.get("campaign")})
    if not campaigns:
        print("⚠️ No campaigns in strategy — skipping.")
        return

    try:
        index = fetch_json(f"{GEO_BASE}/index.json")
    except Exception as e:
        print(f"⚠️ Geo index fetch failed ({e}) — skipping (non-fatal).")
        return

    cc, city = resolve_country(TARGET_LOCATION, index)
    if not cc:
        print(f"⚠️ Could not map '{TARGET_LOCATION}' to a country — skipping.")
        return
    try:
        geo = fetch_json(f"{GEO_BASE}/{cc}.json")
    except Exception as e:
        print(f"⚠️ Geo data fetch failed for {cc} ({e}) — skipping (non-fatal).")
        return

    chosen = pick_locations(geo, city)[:MAX_ROWS]
    if not chosen:
        print(f"⚠️ No matching locations for '{TARGET_LOCATION}' in {cc} — skipping.")
        return

    # exact header the targeting tool already imports successfully
    header = ["Campaign", "Ad Group", "ID#Original", "ID", "Location#Original",
              "Location", "Reach", "Location groups#Original", "Location groups",
              "Radius#Original", "Radius", "Unit#Original", "Unit",
              "Bid Modifier", "Campaign Status", "Ad Group Status", "Status", "Comment"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for camp in campaigns:
            for g in chosen:
                w.writerow([camp, "", "", g["id"], "", g["c"], "", "", "", "",
                            "", "", "", "", "Paused", "", "Enabled", ""])

    lines = [f"# Location targeting — {TARGET_LOCATION}",
             f"Country: {cc} | matched place: {city or '(whole country)'} | "
             f"{len(chosen)} locations x {len(campaigns)} campaigns", ""]
    for g in chosen[:60]:
        lines.append(f"- {g['c']}  ({g.get('t','')}, id {g['id']})")
    if len(chosen) > 60:
        lines.append(f"... +{len(chosen)-60} more")
    lines += ["", "Import: Google Ads Editor → Account → Import → Paste text.",
              "Presence-only recommended: Campaign Settings → Locations → "
              "'People in or regularly in your targeted locations'."]
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ {len(chosen)} locations ({cc}, {city or 'country-level'}) x "
          f"{len(campaigns)} campaigns → {OUT_CSV}")


if __name__ == "__main__":
    main()
