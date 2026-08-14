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
# Google's location bid adjustment range is -90%..+900% (0.1x..10x). The push
# stage sends these as `1 + adj/100`, and the core mutate is atomic, so a single
# out-of-range value (LOW_BID_ADJ=-95 → 0.05x) fails the ENTIRE campaign push.
# Clamp here rather than let one env var sink the run.
def _clamp_adj(raw, default):
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return default
    c = max(-90, min(900, v))
    if c != v:
        print(f"⚠️ Bid adjustment {v}% is outside Google's -90..+900 range — using {c}%.")
    return c


PREMIUM_BID_ADJ = _clamp_adj(os.environ.get("PREMIUM_BID_ADJ"), 25)
LOW_BID_ADJ = _clamp_adj(os.environ.get("LOW_BID_ADJ"), -90)

# Your own knowledge beats the model's. Comma-separated area names; these are
# matched the same forgiving way the model's answers are, and they OVERRIDE
# whatever the model decided. Use PREMIUM_AREAS to protect areas that must never
# be bid down by mistake.
PREMIUM_AREAS = [s.strip() for s in
                 os.environ.get("PREMIUM_AREAS", "").split(",") if s.strip()]
LOW_AREAS = [s.strip() for s in
             os.environ.get("LOW_AREAS", "").split(",") if s.strip()]
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


def _norm_area(s):
    """Loose key for matching an AI-returned area name to a real geo name."""
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").casefold()).strip()


# Tokens that carry no place identity, so dropping them cannot change WHICH
# place is meant: Arabic/Spanish/English articles and generic area words.
_FILLER_TOKENS = {"al", "el", "la", "the", "district", "area", "region",
                  "city", "neighbourhood", "neighborhood", "zone"}


def map_tiers_to_areas(chosen, tiers, city="", cc=""):
    """{AI name: tier} → {real geo name: tier}, plus the names that matched nothing.

    The model is handed the exact geo names and asked to echo them, but it
    routinely rewrites them: "Al Satwa" → "Satwa", "AL QUOZ" → "Al Quoz",
    "Deira" → "Deira, Dubai". The CSV lookup was an exact dict hit defaulting to
    "standard", so ANY such drift silently dropped that area's modifier — the run
    still logged "9 low (-90%)" while the CSV carried nine blank Bid Modifier
    cells. That is invisible unless you diff the file by hand, and it is exactly
    the down-bid on fraud-prone areas that the whole tier system exists for.

    Matching is normalised-exact, then TOKEN-SET equality after dropping filler
    words and the target city/country ("Deira, Dubai" == "Deira"). It is NOT
    substring matching: "Jumeirah Beach" must not silently claim "Jumeirah",
    because a -90% bid on the wrong area costs real money. Anything that cannot
    be matched confidently is returned for the caller to report.
    """
    drop = set(_FILLER_TOKENS) | set(_norm_area(city).split()) | {_norm_area(cc)}
    drop.discard("")

    def key_of(s):
        toks = [t for t in _norm_area(s).split() if t not in drop]
        return " ".join(toks) or _norm_area(s)

    by_exact, by_tokens = {}, {}
    for g in chosen:
        by_exact.setdefault(_norm_area(g["n"]), []).append(g["n"])
        by_tokens.setdefault(frozenset(key_of(g["n"]).split()), []).append(g["n"])
    mapped, unmatched = {}, []
    for raw_name, tier in (tiers or {}).items():
        hits = by_exact.get(_norm_area(raw_name))
        if not hits:
            cand = by_tokens.get(frozenset(key_of(raw_name).split()))
            hits = cand if cand and len(cand) == 1 else None
        if hits:
            for n in hits:
                mapped[n] = tier
        else:
            unmatched.append(raw_name)
    return mapped, unmatched


def apply_area_overrides(chosen, tiers, reasons, city="", cc=""):
    """PREMIUM_AREAS / LOW_AREAS win over the model.

    The model's tier call is judgment, not data, and the expensive way for it to
    be wrong is marking an affluent area "low" — a deep bid cut on exactly the
    areas that convert. These lists let you pin the areas you already know,
    matched the same forgiving way the model's own answers are. They also work
    with no ANTHROPIC_API_KEY at all, as a purely manual tier list.
    """
    tiers, reasons = dict(tiers), dict(reasons)
    for names, tier in ((PREMIUM_AREAS, "premium"), (LOW_AREAS, "low")):
        if not names:
            continue
        mapped, missing = map_tiers_to_areas(
            chosen, {n: tier for n in names}, city, cc)
        for area, t in mapped.items():
            if tiers.get(area) and tiers[area] != t:
                print(f"   ✏️ Override: '{area}' {tiers[area]} → {t} (your {tier.upper()}_AREAS)")
            tiers[area] = t
            reasons[area] = "manual override"
        if missing:
            print(f"   ⚠️ {tier.upper()}_AREAS not in the targeted list "
                  f"(ignored): {', '.join(missing)}")
    return tiers, reasons


def classify_bid_tiers(chosen, cc, city, geo, index):
    """Claude judges every chosen area by wealth / commercial intent /
    fraud-risk using world knowledge (the user's Dubai playbook, any market):
      premium  → elite/business districts, villa communities → +PREMIUM_BID_ADJ%
      standard → normal residential/commercial → no modifier
      low      → labour camps, industrial zones, fraud-prone → LOW_BID_ADJ%
    Also returns negative locations: sibling regions NOT targeted (e.g.
    Dubai/Sharjah/Ajman when targeting Abu Dhabi) + common fake-click source
    countries. Fail-open: returns ({}, []) on any problem."""
    # Your own PREMIUM_AREAS / LOW_AREAS still apply when the model does not run.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ℹ️ ANTHROPIC_API_KEY not set — no model tiers/negative locations.")
        t, r = apply_area_overrides(chosen, {}, {}, city, cc)
        return t, r, []
    try:
        import anthropic
    except ImportError:
        print("ℹ️ anthropic package missing — no model tiers.")
        t, r = apply_area_overrides(chosen, {}, {}, city, cc)
        return t, r, []
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

A "low" area gets its bid cut by {abs(LOW_BID_ADJ)}%, which all but switches it
off. NEVER give "low" to an affluent, upmarket, waterfront, tourist or
central-business area — that is the single most expensive mistake here, because
it turns off the areas that actually convert. If you are not sure who lives or
works in an area, answer "standard". Reserve "low" for areas you positively
know to be labour accommodation, industrial/warehouse zones, or with a real
click-fraud reputation.

Give a SHORT reason (max 10 words) for every non-standard call, so a human can
check it before spending money. Example shape, for a Dubai campaign:
  "Palm Jumeirah": {{"tier": "premium", "why": "elite waterfront villas, high disposable income"}}
  "Al Satwa": {{"tier": "low", "why": "dense labour housing, low purchase intent"}}

TASK 2 — negative locations:
  "negative_siblings": from the sibling list ONLY, the regions most likely to
   send irrelevant clicks to this business (nearby big cities/regions that
   are NOT the target). Max 8.
  "negative_countries": 4-8 countries that are well-known fake-click/bot
   sources for {TARGET_LOCATION}-targeted campaigns, given as exact country
   names. NEVER include the target country ({cc}) or any region inside it —
   excluding the target makes the campaign serve nowhere at all.

Output ONLY JSON:
{{"tiers": {{"<area name>": {{"tier": "premium|standard|low", "why": "..."}}, ...}},
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
        # Accepts both {"area": "low"} and {"area": {"tier": "low", "why": "..."}}
        tiers, reasons = {}, {}
        for k, v in (raw.get("tiers") or {}).items():
            name = str(k).strip()
            if isinstance(v, dict):
                tier = str(v.get("tier", "")).strip().lower()
                why = str(v.get("why", "")).strip()
            else:
                tier, why = str(v).strip().lower(), ""
            if tier in ("premium", "standard", "low"):
                tiers[name] = tier
                if why:
                    reasons[name] = why
        neg_names = ([str(x).strip() for x in raw.get("negative_siblings") or []]
                     + [str(x).strip() for x in raw.get("negative_countries") or []])
        # Resolve to REAL geo names before counting, so the numbers printed here
        # are the numbers that actually reach the CSV.
        tiers, unmatched = map_tiers_to_areas(chosen, tiers, city, cc)
        reasons, _ = map_tiers_to_areas(chosen, reasons, city, cc)
        tiers, reasons = apply_area_overrides(chosen, tiers, reasons, city, cc)

        n_prem = sum(1 for v in tiers.values() if v == "premium")
        n_low = sum(1 for v in tiers.values() if v == "low")
        n_std = sum(1 for v in tiers.values() if v == "standard")
        print(f"💰 Bid tiers applied: {n_prem} premium (+{PREMIUM_BID_ADJ}%) | "
              f"{n_low} low ({LOW_BID_ADJ}%) | {n_std} standard | "
              f"{len(chosen) - len(tiers)} of {len(chosen)} areas unclassified")
        if unmatched:
            print(f"   ⚠️ {len(unmatched)} tier name(s) matched no targeted area "
                  f"(left at standard): {', '.join(unmatched[:8])}"
                  + (" …" if len(unmatched) > 8 else ""))
        # A run that switches off most of the map is far more likely to be a bad
        # classification than a real market. Say so loudly — the CSV is Paused
        # and reviewable, but this is the failure that quietly wastes a budget.
        if tiers and n_low > max(3, int(0.6 * len(chosen))):
            print(f"   🚨 {n_low} of {len(chosen)} areas marked LOW ({LOW_BID_ADJ}%). "
                  f"That is most of the map — CHECK locations.md before pushing, "
                  f"and pin the good areas with PREMIUM_AREAS if this is wrong.")
        for _n, _t in sorted(tiers.items()):
            if _t != "standard":
                print(f"      {'▲' if _t == 'premium' else '▼'} {_n}: {_t}"
                      + (f" — {reasons[_n]}" if _n in reasons else ""))
        print(f"   Negatives suggested: {neg_names}")
        return tiers, reasons, neg_names
    except Exception as e:
        print(f"⚠️ Bid-tier call failed ({e}) — falling back to your overrides only.")
        t, r = apply_area_overrides(chosen, {}, {}, city, cc)
        return t, r, []


def resolve_negative_rows(neg_names, cc, geo, index, chosen=()):
    """Map Claude's negative names to real geo rows. Sibling regions resolve
    inside the target country's file; country names resolve to that
    country's own Country row (fetched per-country, non-fatal).

    Two things are never allowed through, because either one silently kills the
    campaign rather than protecting it:
      - the TARGET COUNTRY itself. Its own Country row lives in this very geo
        file, so a model that answered "United States" on a US campaign used to
        resolve cleanly and exclude the entire target. Only the second lookup
        below was guarded (other_cc != cc); this one was not.
      - anything already being TARGETED. Targeting and excluding the same place
        is contradictory, and Google honours the exclusion.
    """
    rows, seen = [], set()
    by_name = {}
    for g in geo:
        by_name.setdefault(norm(g.get("n", "")), g)
    cc_by_name = {norm(e["name"]): e["cc"] for e in index
                  if e.get("name") and e.get("cc") and e["name"] != e["cc"]}
    target_country_keys = {norm(e["name"]) for e in index
                           if e.get("cc") == cc and e.get("name")} | {norm(cc)}
    chosen_keys = {norm(g.get("n", "")) for g in (chosen or ())}
    for name in neg_names:
        key = norm(name)
        if not key or key in seen:
            continue
        seen.add(key)
        if key in target_country_keys:
            print(f"   🛑 Refusing to exclude '{name}' — that is the TARGET "
                  f"country; the campaign would serve nowhere.")
            continue
        if key in chosen_keys:
            print(f"   🛑 Refusing to exclude '{name}' — it is in the targeted "
                  f"list for this campaign.")
            continue
        g = by_name.get(key)
        if g:
            # A Country row inside the target country's own file can only be
            # the target country itself — already refused above, but a geo
            # dataset that names it differently must not slip through here.
            if str(g.get("t", "")).lower() == "country":
                print(f"   🛑 Refusing to exclude country row '{name}' from the "
                      f"target country's own dataset.")
                continue
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

    tiers, tier_reasons, neg_names = classify_bid_tiers(chosen, cc, city, geo, index)
    # Editor CSV bulk-import format for bid adjustments (per Google's docs,
    # support.google.com/google-ads/editor/answer/30532): a PLAIN NUMBER
    # with no percent sign — "+25%" is written as 25, "-90%" as -90.
    # Both "25%" and "1.25" import as "bid adjustment is invalid"
    # (user hit both, Jul 2026).
    adj = {"premium": str(PREMIUM_BID_ADJ), "low": str(LOW_BID_ADJ)}

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
                # Comment column carries the tier AND why, so the reason for
                # every bid change is visible in the file you are about to
                # import — not buried in a log you have already scrolled past.
                note = "" if tier == "standard" else (
                    f"{tier}: {tier_reasons[g['n']]}"[:180] if g["n"] in tier_reasons
                    else tier)
                w.writerow([camp, "", "", g["id"], "", g["c"], "", "", "", "",
                            "", "", "", adj.get(tier, ""), "Paused", "", "Enabled",
                            note])

    # negative locations — separate small file: paste into the Editor's
    # "Locations, Negative" section (Make multiple changes). Not merged into
    # the master CSV because the Editor has no proven combined-import header
    # for excluded locations.
    neg_rows = resolve_negative_rows(neg_names, cc, geo, index, chosen)
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
    def _why_lines(names):
        return [f"- **{n}** — {tier_reasons[n]}" if n in tier_reasons else f"- **{n}**"
                for n in names]

    if prem:
        lines += [f"## Premium areas (+{PREMIUM_BID_ADJ}% bid)"] + _why_lines(prem) + [""]
    if low:
        lines += [f"## Low-intent/fraud-prone areas ({LOW_BID_ADJ}% bid)",
                  f"_Each of these is bid down {abs(LOW_BID_ADJ)}%. Read the reasons "
                  f"before importing — if any of them is actually a good area, set "
                  f"`PREMIUM_AREAS` for it and re-run._"] + _why_lines(low) + [""]
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
