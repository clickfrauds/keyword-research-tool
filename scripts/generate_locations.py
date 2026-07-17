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

BID TIERS (Jul 2026, user's Dubai playbook generalized): with ANTHROPIC_API_KEY
set, Claude classifies every chosen area by wealth/commercial intent —
premium areas (Palm Jumeirah, Business Bay class) get a POSITIVE bid
modifier, labour/fraud-prone areas (Al Satwa, Deira class) get -90%. It
also names NEGATIVE locations: the sibling regions you are NOT targeting
(Dubai/Sharjah/Ajman when the target is Abu Dhabi) plus common fake-click
source countries — written to locations_negative.csv for the Editor's
"Locations, Negative" paste. No key / any failure = plain rows, no tiers.

Env vars: TARGET_LOCATION   (required)
Optional: GEO_BASE_URL (default https://clickadsprotector.com/geo)
          MAX_LOCATION_ROWS (default 300 per campaign)
          ANTHROPIC_API_KEY (enables bid tiers + negative locations)
          BUSINESS_NAME, NICHE_DESCRIPTION (context for the tier call)
          PREMIUM_BID_ADJ (default 25), LOW_BID_ADJ (default -90)
Input : keyword_strategy.json
Output: locations_editor.csv, locations_negative.csv, locations.md
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
BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
PREMIUM_BID_ADJ = int(os.environ.get("PREMIUM_BID_ADJ", "25"))
LOW_BID_ADJ = int(os.environ.get("LOW_BID_ADJ", "-90"))
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

INPUT_JSON = "keyword_strategy.json"
OUT_CSV = "locations_editor.csv"
OUT_NEG_CSV = "locations_negative.csv"
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


def classify_bid_tiers(chosen, cc, city, geo, index):
    """Claude judges every chosen area by wealth / commercial intent /
    fraud-risk using world knowledge (the user's Dubai playbook, any market):
      premium  → elite/business districts, villa communities → +PREMIUM_BID_ADJ%
      standard → normal residential/commercial → no modifier
      low      → labour camps, industrial zones, fraud-prone → LOW_BID_ADJ%
    Also returns negative locations: sibling regions NOT targeted (e.g.
    Dubai/Sharjah/Ajman when targeting Abu Dhabi) + common fake-click source
    countries. Fail-open: returns ({}, []) on any problem."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ℹ️ ANTHROPIC_API_KEY not set — skipping bid tiers/negative locations.")
        return {}, []
    try:
        import anthropic
    except ImportError:
        print("ℹ️ anthropic package missing — skipping bid tiers.")
        return {}, []
    names = [g["n"] for g in chosen]
    # sibling candidates: same-country locations NOT already chosen (their
    # names give Claude the real list to pick negatives from)
    chosen_set = {g["n"] for g in chosen}
    siblings = sorted({g["n"] for g in geo
                       if g.get("t") in ("City", "Province") and g["n"] not in chosen_set})[:60]
    countries = sorted({e["name"] for e in index if e.get("name") and e.get("cc")
                        and e["name"] != e["cc"]})
    prompt = f"""You are a Google Ads geo-bidding strategist.

BUSINESS: {BUSINESS_NAME or '(unknown)'} — {NICHE_DESCRIPTION or '(unknown niche)'}
TARGET: {TARGET_LOCATION} (country {cc}{', focus ' + city if city else ''})

TARGETED AREAS ({len(names)}):
{json.dumps(names, ensure_ascii=False)}

NON-TARGETED SIBLING REGIONS in the same country (pick negatives ONLY from this list):
{json.dumps(siblings, ensure_ascii=False)}

TASK 1 — classify EVERY targeted area using your real-world knowledge of who
lives/works there (wealth, villas vs labour camps, business districts,
industrial zones, click-fraud reputation):
  "premium"  = affluent/elite or high-commercial-intent (bid UP)
  "standard" = normal (no change)
  "low"      = labour/industrial/low-intent or fraud-prone (bid WAY down)
Be decisive — a local media buyer knows Palm Jumeirah is premium and Al Satwa
is low. Unknown/ambiguous → "standard".

TASK 2 — negative locations:
  "negative_siblings": from the sibling list ONLY, the regions most likely to
   send irrelevant clicks to this business (nearby big cities/emirates that
   are NOT the target). Max 8.
  "negative_countries": 4-8 countries that are well-known fake-click/bot
   sources for {TARGET_LOCATION}-targeted campaigns (exact names from real
   country names, e.g. "United States", "Philippines", "Pakistan", "India",
   "Bangladesh", "Indonesia"). Never include the target country itself.

Output ONLY JSON:
{{"tiers": {{"<area name>": "premium|standard|low", ...}},
  "negative_siblings": ["..."], "negative_countries": ["..."]}}"""
    try:
        client = anthropic.Anthropic()
        with client.messages.stream(model=MODEL, max_tokens=8000,
                                    output_config={"effort": "low"},
                                    messages=[{"role": "user", "content": prompt}]) as s:
            resp = s.get_final_message()
        text = "".join(b.text for b in resp.content if b.type == "text")
        m = re.search(r"\{.*\}", text, re.DOTALL)
        raw = json.loads(m.group(0) if m else text)
        tiers = {str(k).strip(): str(v).strip().lower()
                 for k, v in (raw.get("tiers") or {}).items()
                 if str(v).strip().lower() in ("premium", "standard", "low")}
        neg_names = ([str(x).strip() for x in raw.get("negative_siblings") or []]
                     + [str(x).strip() for x in raw.get("negative_countries") or []])
        n_prem = sum(1 for v in tiers.values() if v == "premium")
        n_low = sum(1 for v in tiers.values() if v == "low")
        print(f"💰 Bid tiers: {n_prem} premium (+{PREMIUM_BID_ADJ}%) | "
              f"{n_low} low ({LOW_BID_ADJ}%) | negatives suggested: {neg_names}")
        return tiers, neg_names
    except Exception as e:
        print(f"⚠️ Bid-tier call failed ({e}) — plain locations, no modifiers.")
        return {}, []


def resolve_negative_rows(neg_names, cc, geo, index):
    """Map Claude's negative names to real geo rows. Sibling regions resolve
    inside the target country's file; country names resolve to that
    country's own Country row (fetched per-country, non-fatal)."""
    rows, seen = [], set()
    by_name = {}
    for g in geo:
        by_name.setdefault(norm(g.get("n", "")), g)
    cc_by_name = {norm(e["name"]): e["cc"] for e in index
                  if e.get("name") and e.get("cc") and e["name"] != e["cc"]}
    for name in neg_names:
        key = norm(name)
        if not key or key in seen:
            continue
        seen.add(key)
        g = by_name.get(key)
        if g:
            # prefer the Province/City row over neighborhoods with same name
            rows.append(g)
            continue
        other_cc = cc_by_name.get(key)
        if other_cc and other_cc != cc:
            try:
                other = fetch_json(f"{GEO_BASE}/{other_cc}.json")
                country_row = next((x for x in other if x.get("t") == "Country"), None)
                if country_row:
                    rows.append(country_row)
            except Exception:
                pass
    return rows


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

    tiers, neg_names = classify_bid_tiers(chosen, cc, city, geo, index)
    adj = {"premium": f"{PREMIUM_BID_ADJ}%", "low": f"{LOW_BID_ADJ}%"}

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
                tier = tiers.get(g["n"], "standard")
                w.writerow([camp, "", "", g["id"], "", g["c"], "", "", "", "",
                            "", "", "", adj.get(tier, ""), "Paused", "", "Enabled",
                            tier if tier != "standard" else ""])

    # negative locations — separate small file: paste into the Editor's
    # "Locations, Negative" section (Make multiple changes). Not merged into
    # the master CSV because the Editor has no proven combined-import header
    # for excluded locations.
    neg_rows = resolve_negative_rows(neg_names, cc, geo, index)
    if neg_rows:
        with open(OUT_NEG_CSV, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Campaign", "ID", "Location"])
            for camp in campaigns:
                for g in neg_rows:
                    w.writerow([camp, g["id"], g["c"]])

    lines = [f"# Location targeting — {TARGET_LOCATION}",
             f"Country: {cc} | matched place: {city or '(whole country)'} | "
             f"{len(chosen)} locations x {len(campaigns)} campaigns", ""]
    prem = [g["n"] for g in chosen if tiers.get(g["n"]) == "premium"]
    low = [g["n"] for g in chosen if tiers.get(g["n"]) == "low"]
    if prem:
        lines += [f"## Premium areas (+{PREMIUM_BID_ADJ}% bid)", ", ".join(prem), ""]
    if low:
        lines += [f"## Low-intent/fraud-prone areas ({LOW_BID_ADJ}% bid)", ", ".join(low), ""]
    if neg_rows:
        lines += ["## Negative locations (locations_negative.csv → Editor: "
                  "Locations, Negative)", ", ".join(g["n"] for g in neg_rows), ""]
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
          f"{len(campaigns)} campaigns → {OUT_CSV}"
          + (f" | {len(neg_rows)} negative locations → {OUT_NEG_CSV}" if neg_rows else ""))


if __name__ == "__main__":
    main()
