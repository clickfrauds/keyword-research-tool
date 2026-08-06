"""
generate_mode3_plan.py — MODE 3 SITE PLAN (full-website keyword wiring)
------------------------------------------------------------------------
A dedicated pipeline mode for the AI website builder's MODE 3 (full
website: categories → service pages). You paste the SAME comma-separated
services you would give the builder; this script returns one JSON link
the builder consumes via its optional `seo_inputs_url` field.

Stage flow (one script, one workflow run):
  A. Claude groups the services into categories — same pattern the
     builder's own Mode 3 uses (≤10 categories, EVERY service placed,
     service names copied character-for-character so the builder's
     name-matching never breaks).
  B. Per category: Google Ads GenerateKeywordIdeas with that category's
     services as seeds, chunked to the API's 20-seed hard limit.
     Per-category batching keeps attribution (this call's ideas belong
     to this category) and keeps idea relevance tight.
  C. Python scoring (kd proxy / funnel) + volume filter — free, no API.
  D. Per category: Claude assigns keywords to each service page
     (primary keyword + supporting keywords + real PAA-style questions
     with answer angles), cannibalization-guarded: every keyword id
     lands on at most ONE page across the whole site.

OUTPUT: website_builder_inputs.json containing a "mode3_site_plan" block.
push_results.py publishes it as  results/{REQUEST_ID}.seo.json  — paste
that raw link into the builder's seo_inputs_url field (Mode 3). Leave
the field empty and the builder behaves exactly as before (guessed
keywords) — this data is a pure optional upgrade.

Required env vars:
    SERVICES_MODE3        comma-separated service list (the builder input)
    ANTHROPIC_API_KEY
    GOOGLE_ADS_*          same five secrets keyword_research.py uses
Optional env vars:
    BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION,
    LOCATION_ID, LANGUAGE_ID, CLAUDE_MODEL, CLAUDE_EFFORT,
    MAX_KEYWORDS_PER_CATEGORY (default 120)
"""

import os
import re
import sys
import json
import time

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

# Reuse the battle-tested pieces from the existing stages — no logic forks.
from keyword_research import (
    classify_trend, peak_months, detect_language_id, resolve_location_id,
    resolve_language_from_code,
)

# Content language (Jul 2026): same LANGUAGE code the website builder uses, so
# the Mode 3 plan's questions/answer-angles/entities come back in that language
# and the Planner pulls the right-language data. Blank = unchanged behavior.
CONTENT_LANGUAGE = os.environ.get("LANGUAGE", "").strip().lower()
_M3_LANG_NAMES = {
    "en": "English", "ar": "Arabic", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "nl": "Dutch",
    "ru": "Russian", "tr": "Turkish", "hi": "Hindi", "ur": "Urdu",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "pl": "Polish",
    "sv": "Swedish", "id": "Indonesian", "th": "Thai", "vi": "Vietnamese",
    "el": "Greek", "ro": "Romanian", "cs": "Czech", "hu": "Hungarian",
}
CONTENT_LANGUAGE = {"no": "", "english": "en", "spanish": "es", "french": "fr",
                    "german": "de", "arabic": "ar"}.get(CONTENT_LANGUAGE, CONTENT_LANGUAGE)
CONTENT_LANG_NAME = _M3_LANG_NAMES.get(CONTENT_LANGUAGE, "") if CONTENT_LANGUAGE != "en" else ""
from generate_seo_strategy import parse_json_robust, enrich, expand_kw, is_long_tail
# Stage 1.6 — same query-network module the cluster pipeline uses, so a Mode 3
# site plan and a Mode 4 cluster plan are built from the same kind of data.
from expand_autocomplete import expand_queries, fetch_historical_metrics, resolve_gl
# Intent + local/voice/urgent flags. Stage 2.5 sets these in the cluster
# pipeline, but Mode 3 never runs that stage, so every keyword reached the
# builder with intent="" — which collapsed to funnel MOFU for ALL of them.
# The builder tiers a page's keywords by exactly these fields, so its
# high-intent tier was falling back to raw volume order and its local tier to
# an invented "24/7 {service} {city}" string. classify() carries Arabic
# vocabularies as well as English, so this works for both sides of the run.
from score_keywords import classify as classify_intent

JSON_OUT = "website_builder_inputs.json"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")
BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()
MAX_KW_PER_CAT = int(os.environ.get("MAX_KEYWORDS_PER_CATEGORY", "120"))

# Arabic keyboards produce ، (U+060C), not the ASCII comma, and Arabic text
# pasted from a document carries it through. Splitting on "," alone turned a
# whole Arabic service list into ONE service — the run then built a single
# page named after the entire list. Accept both, plus semicolons.
_LIST_SEP = re.compile("[,،؛;\n]+")


def split_list(raw):
    return [s.strip() for s in _LIST_SEP.split(str(raw or "")) if s.strip()]


SERVICES = split_list(os.environ.get("SERVICES_MODE3", ""))

ADS_SEED_LIMIT = 20          # GenerateKeywordIdeas hard limit: 20 seed keywords/request
ADS_CALL_DELAY = 1.5         # polite pacing between Ads API calls (seconds)

# Autocomplete queries kept per category, on top of the Planner slice. Set
# AC_QUERIES_PER_CATEGORY=0 to turn the whole Stage 1.6 pass off for Mode 3.
AC_PER_CAT = int(os.environ.get("AC_QUERIES_PER_CATEGORY", "40"))
_AC_GL = resolve_gl() if AC_PER_CAT > 0 else None   # one geo lookup per run
_AC_QUESTION = re.compile(
    r"^(how|what|why|when|which|where|who|is|are|do|does|can)\b", re.I)
# Filled once in main() by local_place_terms(); empty = bare seeds skipped.
_AC_CITY_TERM = ""
_AC_EXCLUDE = []


def _norm(s):
    """Match key for a service name or keyword — UNICODE, not ASCII.

    [^a-z0-9] deletes every non-Latin character, so all six Arabic services in
    the Riyadh run normalised to the SAME empty string. The damage compounded
    through the whole pipeline:
      * Stage A's by_norm held one entry → 5 of 6 services "dropped" and
        force-added round-robin into a single category;
      * fetch_category_keywords guards with `if key and ...`, and "" is falsy,
        so EVERY Arabic Planner keyword was silently discarded — the run kept
        only the autocomplete queries;
      * assign_keywords resolved every page name to the same entry, so one
        page got all the keywords and the other five got nothing.
    The build reported success throughout, and the one page that did get data
    ("عزل حمامات بالرياض") was handed "ترميم منازل" keywords.
    """
    return re.sub(r"[\W_]+", "", str(s).lower())


_AR_TRANSLIT = {
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ب": "b", "ت": "t", "ث": "th",
    "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z",
    "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a",
    "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "و": "w", "ي": "y", "ى": "a", "ة": "a", "ء": "", "ؤ": "u",
    "ئ": "i", "َ": "", "ُ": "", "ِ": "", "ّ": "", "ْ": "", "ً": "", "ٌ": "", "ٍ": "",
}


def _clean_slug(candidate, fallback_name):
    """ASCII URL slug. Prefers the model's ENGLISH slug; romanises the page
    name only as a last resort.

    The producer owns the slug so that the Mode 3 page, the builder's output
    path and any later Mode 5 area page all read ONE value instead of each
    deriving their own and disagreeing."""
    s = re.sub(r"[^a-z0-9]+", "-", str(candidate or "").lower()).strip("-")
    if len(s) >= 3:
        return s[:70]
    romanised = "".join(_AR_TRANSLIT.get(c, c) for c in str(fallback_name).lower())
    romanised = re.sub(r"[^a-z0-9]+", "-", romanised).strip("-")
    return (romanised or "page")[:70]


def _validate_outline(raw, page_ids, by_id):
    """Keep only headings whose keyword ids belong to THIS page, each id used
    once. A heading that claims another page's keyword is how a plan starts
    cannibalising itself."""
    out, used = [], set()
    for h in (raw or [])[:8]:
        if not isinstance(h, dict):
            continue
        text = str(h.get("h2", "")).strip()
        if not text:
            continue
        ids = []
        for i in h.get("keyword_ids", []):
            try:
                i = int(i)
            except (TypeError, ValueError):
                continue
            if i in page_ids and i not in used:
                ids.append(i)
                used.add(i)
        out.append({
            "h2": text[:120],
            "keywords": [by_id[i]["keyword"] for i in ids],
            "entities": [str(e).strip() for e in (h.get("entities") or [])
                         if str(e).strip()][:4],
        })
    return out


def _kw_signature(q):
    """Token signature for near-duplicate collapse, script-agnostic.

    Arabic writes the same query many ways: hamza (أ/ا), ta-marbuta (ة/ه),
    alef-maqsura (ى/ي), and the fused prefixes بـ/الـ. English has word order
    and plurals. All of those are the SAME query to Google."""
    q = str(q).lower()
    q = re.sub(r"[أإآ]", "ا", q)
    q = re.sub(r"ة", "ه", q)
    q = re.sub(r"ى", "ي", q)
    toks = []
    for t in re.findall(r"[^\W_]+", q, re.UNICODE):
        t = re.sub(r"^(بال|وال|فال|كال|لل|ال)", "", t)
        t = re.sub(r"(?<=[a-z]{4})s$", "", t)      # English plural
        if t and t not in {"في", "من", "مع", "the", "a", "an", "in", "of", "for"}:
            toks.append(t)
    return tuple(sorted(set(toks)))


def dedupe_keywords(rows):
    """Collapse spelling / word-order / prefix variants into one entry.

    Measured on the Riyadh leak-detection page: 97 keywords carried only 73
    distinct queries, and six of them were the same phrase written six ways
    ("كشف تسربات المياه بالرياض" / "... الرياض" / "... في الرياض" ...). Sending
    all 97 to the assignment prompt wastes the model's attention on
    orthography and pushes genuinely different angles — "مجانا", "أسعار",
    "حل ارتفاع فاتورة المياه" — down out of view.

    The highest-volume spelling represents the group; the rest ride along as
    `variants` so nothing is lost and the writer can still use them."""
    groups = {}
    for r in sorted(rows, key=lambda r: -(r.get("avg_monthly_searches") or 0)):
        groups.setdefault(_kw_signature(r["keyword"]), []).append(r)
    out = []
    for items in groups.values():
        keep = dict(items[0])
        if len(items) > 1:
            keep["variants"] = [i["keyword"] for i in items[1:]]
        out.append(keep)
    out.sort(key=lambda r: -(r.get("avg_monthly_searches") or 0))
    return out


def claude_json(client, system_prompt, user_prompt):
    """One Claude call with a strict-JSON retry, parsed via the shared
    4-pass robust parser."""
    text = ""
    for attempt in range(2):
        p = user_prompt if attempt == 0 else user_prompt + \
            "\n\nIMPORTANT: your previous response was not valid JSON. Return ONLY the JSON object."
        with client.messages.stream(
            model=MODEL,
            max_tokens=16000,
            output_config={"effort": EFFORT},
            system=system_prompt,
            messages=[{"role": "user", "content": p}],
        ) as stream:
            response = stream.get_final_message()
        text = "".join(b.text for b in response.content if b.type == "text")
        try:
            return parse_json_robust(text)
        except json.JSONDecodeError as e:
            print(f"⚠️ Claude JSON parse failed (attempt {attempt + 1}): {e}")
    raise RuntimeError("Claude did not return valid JSON after 2 attempts")


# ══════════════════════════════════════════════════════════════════════════
# Stage A — group services into categories (builder-compatible pattern)
# ══════════════════════════════════════════════════════════════════════════

GROUPING_SYSTEM = """You are a Website Information Architect for a service
business site. Output must be valid JSON only."""


# central_entity/source_context are prose the builder puts in front of the
# writer on EVERY page, so they must be in the site's language — unlike the
# category names, which stay English because they become URL segments.
_CE_LANG_RULE = (f"""
7. LANGUAGE: write central_entity and source_context in {CONTENT_LANG_NAME}
   (they are shown to the content writer for every page of a
   {CONTENT_LANG_NAME} site). Category names stay ENGLISH — they become URLs."""
                 if CONTENT_LANG_NAME else "")


def local_place_terms(client):
    """(target city term, other-city blocklist) in the SITE'S language.

    Needed because a bare seed reaches a different query space than a
    city-qualified one — measured on the Riyadh services, 51 queries vs 106
    with only 8 in common, and the bare form is the only route to the
    vocabulary that matters (materials grp/cmb, brands سيكا/فالكون, types
    اسمنتي/امريكي). The catch is that the bare form also drags in other cities
    (37 of 106). The geo dataset carries English names only, so it cannot
    filter Arabic — or Turkish, or Hindi — drift; the model can, in one small
    call. Fail-open: no terms means bare seeds are simply not probed."""
    if not TARGET_LOCATION:
        return "", []
    try:
        raw = claude_json(client, "Return valid JSON only.", f"""TARGET LOCATION: {TARGET_LOCATION}
SITE LANGUAGE: {CONTENT_LANG_NAME or 'English'}

Return, in the SITE LANGUAGE exactly as locals type them into Google:
1. "city_term": the target city's name. Bare name only — no preposition,
   no article, no country. RETURN AN EMPTY STRING if the target is a whole
   country, a region, or anything with no single city: a national site wants
   every city's queries, so filtering them out would delete the demand it
   exists to serve.
2. "other_cities": 25-40 OTHER cities and major regions of the SAME country
   that people search service keywords for. These are used to DROP
   suggestions belonging to other cities, so include the spellings that
   actually appear in search — with and without attached prepositions or
   articles where both are common, and common misspellings. NEVER include
   the target city or any district inside it.

JSON: {{"city_term": "...", "other_cities": ["...", "..."]}}""")
        city = str(raw.get("city_term", "")).strip()
        others = [str(t).strip() for t in (raw.get("other_cities") or [])
                  if str(t).strip()]
        # A blocklist entry that matches the target city would delete the very
        # queries we want.
        others = [t for t in others if city and city.lower() not in t.lower()][:60]
        if city and others:
            print(f"   🗺️ place filter: city '{city}', {len(others)} other-city terms")
        elif not city:
            # Country/region target: the seeds carry no city, so they are
            # already the bare form and there is nothing to strip — and every
            # city's queries are in scope, so nothing should be excluded.
            print("   🗺️ national target — no city filter (all cities in scope)")
        return city, others
    except Exception as e:
        print(f"   ℹ️ place-term lookup failed ({str(e)[:60]}) — bare seeds skipped")
        return "", []


def extract_area_targets(client, plan_categories, city_term):
    """Area/district demand hiding inside the service pages' keyword sets.

    A page like "كشف تسربات المياه بالرياض" came back with 97 keywords, and 17
    of them were district queries — شمال الرياض, العليا, الملز, لبن — worth
    2,220/mo between them. They can never rank on that one page; each is its
    own pSEO page. Buried in a keyword list nobody reads, that demand was
    simply lost.

    These are NOT turned into Mode 3 pages. Mode 5 has a dedicated pipeline
    for area research, and its `extra_areas` input exists for exactly this
    case: areas people search that the geo dataset does not list. So this
    hands the names over and stops there.

    Fail-open: no areas, or a failed call, means the plan is unchanged."""
    if not city_term:
        return []
    cand = []
    for c in plan_categories:
        for s in c["services"]:
            for k in s.get("keywords", []):
                q = k.get("keyword", "")
                # City mentioned AND something beyond the service+city wording
                if city_term in q and _norm(q) != _norm(s["name"]):
                    cand.append((q, k.get("volume", 0), s["name"]))
    if not cand:
        return []
    cand.sort(key=lambda x: -x[1])
    lines = "\n".join(f"{q} | {v}/mo | page: {p}" for q, v, p in cand[:120])
    try:
        raw = claude_json(client, "Return valid JSON only.", f"""CITY: {city_term}

Keywords from this site's pages that mention the city:
{lines}

Some of these name a DISTRICT, NEIGHBOURHOOD or COMPASS AREA of the city
(for example a quadrant like "north {city_term}", or a named district).
Others are just the plain city keyword with no area in them.

Return ONLY the ones that name an area. For each, give the area name exactly
as people type it, the total monthly volume of its keywords, and the service
page the demand belongs to.

Ignore any area belonging to a DIFFERENT city. Ignore plain city keywords.

JSON: {{"areas": [{{"area": "...", "volume": 0, "service": "exact page name",
"keywords": ["..."]}}]}}""")
        out = []
        for a in (raw.get("areas") or []):
            name = str(a.get("area", "")).strip()
            if not name or _norm(name) == _norm(city_term):
                continue
            out.append({
                "area": name,
                "volume": int(a.get("volume") or 0),
                "service": str(a.get("service", "")).strip(),
                "keywords": [str(k).strip() for k in (a.get("keywords") or []) if str(k).strip()],
            })
        out.sort(key=lambda a: -a["volume"])
        if out:
            print(f"   📍 {len(out)} area(s) with real demand → Mode 5 handover "
                  f"({sum(a['volume'] for a in out):,}/mo total)")
        return out[:60]
    except Exception as e:
        print(f"   ℹ️ area extraction skipped ({str(e)[:60]}) — plan unchanged")
        return []


def group_services(client, services):
    prompt = f"""Organize this service list into a logical category hierarchy
for a website (main categories → service pages).

BUSINESS: {BUSINESS_NAME or '(not provided)'}
NICHE: {NICHE_DESCRIPTION or '(infer from services)'}
LOCATION: {TARGET_LOCATION or '(not local)'}

SERVICES ({len(services)}):
{chr(10).join('- ' + s for s in services)}

RULES:
1. Category count follows input size: 1-10 services = 1-2 categories,
   11-30 = 3-5, 31-60 = 6-8, 60+ = up to 10. NEVER more than 10.
2. Category names in ENGLISH, plain text, no commas/colons/pipes, <60 chars.
3. Place EVERY service in exactly one category.
4. CRITICAL: copy each service name CHARACTER-FOR-CHARACTER from the input.
   Never rephrase, translate, or retitle a service.
5. central_entity: the ONE thing this whole site is about — the noun every
   page ultimately describes ("air conditioning", "roof", "dental implant").
   Not the company name, not a service name. Every page on the site is an
   attribute or sub-topic of it.
6. source_context: one sentence on WHO is publishing and WHY they are
   credible on that entity — the site's angle. Two sites covering the same
   entity differ by this, and it is what keeps 100 pages reading as one site
   instead of 100 unrelated pages.{_CE_LANG_RULE}

RETURN JSON ONLY:
{{"central_entity": "the one noun the site is about",
  "source_context": "one sentence: who publishes this and why they are credible",
  "categories": [{{"name": "Category Name", "description": "1 sentence",
  "services": ["exact service name", "..."]}}]}}"""
    raw = claude_json(client, GROUPING_SYSTEM, prompt)
    cats = []
    placed = set()
    by_norm = {_norm(s): s for s in services}
    for c in (raw.get("categories") or [])[:10]:
        name = re.sub(r"\s+", " ", str(c.get("name", "")).replace(",", " ")
                      .replace("::", " ").replace("|", " ")).strip()[:60]
        svc_list = []
        for s in c.get("services", []):
            hit = by_norm.get(_norm(s))
            if hit and hit not in placed:
                svc_list.append(hit)
                placed.add(hit)
        if name and svc_list:
            cats.append({"name": name,
                         "description": str(c.get("description", "")).strip()[:200],
                         "services": svc_list})
    # Safety net — force any dropped service back in, round-robin
    missing = [s for s in services if s not in placed]
    if missing:
        if not cats:
            cats = [{"name": "General Services", "description": "", "services": []}]
        print(f"⚠️ Grouping dropped {len(missing)} service(s) — forcing back in.")
        for i, s in enumerate(missing):
            cats[i % len(cats)]["services"].append(s)
    return cats, {
        "central_entity": str(raw.get("central_entity", "")).strip()[:120],
        "source_context": str(raw.get("source_context", "")).strip()[:400],
    }


# ══════════════════════════════════════════════════════════════════════════
# Stage B — per-category Google Ads pull (chunked to the 20-seed limit)
# ══════════════════════════════════════════════════════════════════════════

def ads_fetch_ideas(client, seeds, location_id, language_id):
    """One GenerateKeywordIdeas call → list of scored keyword dicts."""
    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
    request.language = f"languageConstants/{language_id}"
    if location_id:
        request.geo_target_constants.append(f"geoTargetConstants/{location_id}")
    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    request.keyword_seed.keywords.extend(seeds)
    request.historical_metrics_options.include_average_cpc = True

    response = client.get_service("KeywordPlanIdeaService").generate_keyword_ideas(request=request)
    rows = []
    for idea in response:
        m = idea.keyword_idea_metrics
        vol = m.avg_monthly_searches or 0
        if vol <= 0:
            continue
        monthly = list(m.monthly_search_volumes)
        monthly.sort(key=lambda x: (x.year, x.month))
        rows.append({
            "keyword": idea.text,
            "avg_monthly_searches": vol,
            "competition": m.competition.name if m.competition else "UNKNOWN",
            "competition_index": m.competition_index or 0,
            "low_top_bid": round((m.low_top_of_page_bid_micros or 0) / 1_000_000, 2),
            "high_top_bid": round((m.high_top_of_page_bid_micros or 0) / 1_000_000, 2),
            "trend": classify_trend([x.monthly_searches for x in monthly]),
            "peak_months": peak_months(monthly),
        })
    return rows


def fetch_category_keywords(ads_client, category, location_id, language_id, global_seen):
    """All Ads ideas for one category (seeds chunked), deduped locally AND
    against keywords already claimed by earlier categories (site-level
    cannibalization guard, layer 1)."""
    seeds = category["services"]
    rows = []
    # LANGUAGE PER SEED SCRIPT, not per run. keyword_research.py learned this
    # in July: a run-wide language sends every seed to the Planner under one
    # filter, so in a mixed list the minority script comes back nearly empty.
    # This script never got the fix. A seed written in Arabic or Devanagari is
    # unambiguous, so its own script decides; Latin-script seeds keep the
    # run-wide code, because es/fr/de cannot be told apart by script.
    by_lang = {}
    for s in seeds:
        script_lang, _why = detect_language_id([s])
        if language_id and script_lang != "1000" and script_lang != language_id:
            seed_lang = script_lang
        else:
            seed_lang = language_id or script_lang
        by_lang.setdefault(seed_lang, []).append(s)
    if len(by_lang) > 1:
        print(f"   🔤 mixed scripts in '{category['name']}': "
              + ", ".join(f"{len(v)} seed(s) as {k}" for k, v in by_lang.items()))
    for seed_lang, lang_seeds in by_lang.items():
        for i in range(0, len(lang_seeds), ADS_SEED_LIMIT):
            chunk = lang_seeds[i:i + ADS_SEED_LIMIT]
            try:
                rows.extend(ads_fetch_ideas(ads_client, chunk, location_id, seed_lang))
            except Exception as e:
                print(f"⚠️ Ads call failed for '{category['name']}' chunk "
                      f"{i // ADS_SEED_LIMIT + 1} [{seed_lang}]: "
                      f"{str(e)[:120]} — continuing")
            time.sleep(ADS_CALL_DELAY)
    for r in rows:
        r.setdefault("source", "planner")
        r["intent"], r["flags"] = classify_intent(r["keyword"])
    out, local_seen = [], set()
    for r in sorted(rows, key=lambda r: -r["avg_monthly_searches"]):
        key = _norm(r["keyword"])
        if key and key not in local_seen and key not in global_seen:
            local_seen.add(key)
            out.append(r)
    out = out[:MAX_KW_PER_CAT]

    # ── Stage 1.6 query network (Google Autocomplete) ─────────────────────
    # Planner only reports queries it has advertiser data for, which on a
    # 100-page build leaves most service pages with a handful of head terms
    # and no long tail at all. Autocomplete returns queries out of Google's
    # own logs, so the pages get real customer phrasing to answer.
    # Depth 1 here on purpose: a 10-category run would pay depth 2 ten times.
    # Kept OUTSIDE the MAX_KW_PER_CAT slice above — a zero-volume question
    # sorts last by volume and would always be the first thing cut, which is
    # exactly the material we are trying to keep.
    if AC_PER_CAT > 0:
        try:
            ac_queries, _ = expand_queries(
                seeds, hl=(CONTENT_LANGUAGE or "en")[:5], gl=_AC_GL,
                depth=1, max_queries=AC_PER_CAT * 4, verbose=False,
                city_term=_AC_CITY_TERM, exclude_terms=_AC_EXCLUDE)
            fresh = [q for q in ac_queries
                     if _norm(q) not in local_seen and _norm(q) not in global_seen]
            if fresh:
                metrics = fetch_historical_metrics(fresh, verbose=False)
                extra = []
                for q in fresh:
                    row = metrics.get(q)
                    if row:
                        row["source"] = "autocomplete"
                    else:
                        row = {"keyword": q, "avg_monthly_searches": 0,
                               "competition": "UNKNOWN", "competition_index": 0,
                               "low_top_bid": 0.0, "high_top_bid": 0.0,
                               "trend": "UNKNOWN", "peak_months": "",
                               "source": "autocomplete"}
                    row["intent"], row["flags"] = classify_intent(row["keyword"])
                    extra.append(row)
                # Question-shaped first (FAQ/heading fodder is the point of
                # this pass), then by volume.
                extra.sort(key=lambda r: (
                    0 if _AC_QUESTION.match(r["keyword"]) else 1,
                    -r["avg_monthly_searches"]))
                extra = extra[:AC_PER_CAT]
                for r in extra:
                    local_seen.add(_norm(r["keyword"]))
                out.extend(extra)
                _with_vol = sum(1 for r in extra if r["avg_monthly_searches"] > 0)
                print(f"   🌐 +{len(extra)} autocomplete queries for "
                      f"'{category['name']}' ({_with_vol} with volume)")
        except Exception as e:
            print(f"   ℹ️ Autocomplete expansion skipped for "
                  f"'{category['name']}' ({str(e)[:70]}) — Planner data stands")

    global_seen.update(local_seen)
    # Collapse spelling/word-order variants LAST, so the cap above still
    # measured real coverage but the assignment prompt sees distinct queries.
    before = len(out)
    out = dedupe_keywords(out)
    if before != len(out):
        print(f"   🧹 {before} -> {len(out)} distinct queries "
              f"({before - len(out)} spelling/word-order variants merged)")
    return out


# ══════════════════════════════════════════════════════════════════════════
# Stage D — per-category Claude assignment (keywords → service pages)
# ══════════════════════════════════════════════════════════════════════════

ASSIGN_SYSTEM = """You are a senior SEO strategist. You assign real
Google Keyword Planner keywords to the service pages of one website
category. Output must be valid JSON only."""


def assign_keywords(client, category, keywords):
    by_id = {}
    lines = []
    tail_lines = []
    for idx, k in enumerate(keywords, 1):
        k = enrich(dict(k, id=idx))
        by_id[idx] = k
        if is_long_tail(k):
            # No volume figure exists, so the metric columns would all read 0
            # and the model would rank it as dead. It isn't — see is_long_tail.
            tail_lines.append(f"{idx}|{k['keyword']}")
        else:
            # intent + flags were computed and then never shown to the model.
            # Without them it cannot tell a "near me" query from a plain one,
            # or a spoken-style question from a typed keyword — so local and
            # voice demand had no way of shaping the outline.
            _flags = ",".join(k.get("flags", [])) or "-"
            lines.append(f"{idx}|{k['keyword']}|vol:{k['avg_monthly_searches']}"
                         f"|kd:{k['kd_proxy']}|{k['funnel']}|{k.get('trend', '?')}"
                         f"|{k.get('intent', '?')}|{_flags}")

    prompt = f"""CATEGORY: {category['name']}
LOCATION: {TARGET_LOCATION or '(not local)'}
SERVICE PAGES in this category (one page each — copy names EXACTLY):
{chr(10).join('- ' + s for s in category['services'])}

KEYWORDS ({len(lines)} rows — id|keyword|volume|kd|funnel|trend|intent|flags).
`flags` marks demand you must not lose: `local` = the searcher wants a
provider near them or in a named area, `voice` = phrased the way people speak
to an assistant, `urgent` = needs it today:
{chr(10).join(lines)}
{f'''
LONG-TAIL QUERIES ({len(tail_lines)} rows — id|query). Real queries from Google
Autocomplete that Keyword Planner has no advertiser data for, so no volume
figure exists. NOT page targets — assign each to the ONE page that should
answer it in its FAQs and headings, via long_tail_ids:
{chr(10).join(tail_lines)}
''' if tail_lines else ''}
TASK: assign keywords to the service page they belong on.
RULES:
1. Every keyword id on AT MOST one page (one query = one page, no
   cannibalization). Irrelevant/junk/competitor-brand ids → excluded_ids.
2. primary_keyword_id = that page's single #1 target (highest-value
   relevant keyword) and must appear in its keyword_ids.
3. questions: 3-6 per service — REAL phrasing customers type into
   Google/AI assistants about THAT service{' in ' + TARGET_LOCATION if TARGET_LOCATION else ''}
   (cost, timeframe, troubleshooting). Each gets an answer_angle: one
   sentence on HOW the content should answer to win the snippet.
4. entities_to_mention: 3-6 specific terms/parts/standards per service
   for topical authority.
4a. h2_outline: the page's BODY SKELETON — 5-8 H2 sections, in reading order.
   This is where the page's keyword coverage actually lives. Rules:
   - Each H2 is CONVERSION-SHAPED: written the way a buyer thinks, not a
     category label. "كم تكلفة كشف التسربات في الرياض؟" not "الأسعار";
     "How Much Does Leak Detection Cost?" not "Pricing". A heading that
     answers a real worry earns the scroll and can win a snippet on its own.
   - keyword_ids: which of THIS page's keywords that section is written to
     satisfy. Spread them — the whole point is that a keyword nobody could
     fit in the title still gets a home. Every id may appear in one H2 only.
   - entities: 2-4 specific terms/materials/standards/brands that belong in
     THAT section — not the page's generic entity list repeated.
   - Do NOT restate the attributes' benefit cards; those are short trust
     blocks elsewhere on the page. H2 sections are the body prose.
   - LOCAL: if ANY keyword carries the `local` flag, or names an area or
     "near me", one H2 must serve that intent directly — coverage of the
     service area, response time to named areas, whether the price changes by
     distance. Local demand is the highest-converting traffic a service page
     gets and it was being folded into generic sections.
   - VOICE: if any keyword carries the `voice` flag, or the long-tail list
     holds spoken-style questions, one H2 must be phrased as a FULL SPOKEN
     QUESTION, exactly as someone would say it out loud — "هل يمكن كشف
     التسرب بدون تكسير؟", "Can you find a leak without breaking the floor?"
     Assistants read back the passage that matches the spoken phrasing, so
     the heading has to sound spoken, not typed.
   - URGENT: if any keyword carries the `urgent` flag, one H2 covers same-day
     or emergency availability.
   - Order by what a buyer needs first, ending with the section that leads
     naturally into the call to action.
4b. attributes: the ANGLES this page must cover to be complete. A page that
   answers "what it is" but never "what it costs" or "how long it takes" is
   thin no matter how many words it has, and a searcher goes back to Google.
   Return 4-7 per service, EACH one chosen because the keywords or questions
   above show demand for it — never a generic checklist. Use these names
   where they fit: cost, timeline, process, comparison, requirement, problem,
   maintenance, warranty, local. Each gets a `covers` line: one sentence on
   what the page must actually say to satisfy it. ORDER THEM by how much
   demand the data shows — the builder writes them in the order you give.
5. "name" must be a CHARACTER-FOR-CHARACTER copy of a service page name.
4c. internal_links: 2-4 OTHER page names from the list above that a reader of
   this page would genuinely want next — a shared job, the step before or
   after, the thing they must choose between. Not "everything in the
   category". The builder anchors each link on the TARGET page's primary
   keyword, so choosing the right target is the whole decision here. Never
   link a page to itself.
5b. url_slug: the page's URL, in ENGLISH, lowercase a-z 0-9 and hyphens only,
   3-6 words. Translate the MEANING of the service into English — never
   transliterate ("كشف تسربات المياه بالرياض" → "water-leak-detection-riyadh",
   NOT "kshf-tsrbat-almyah"). A romanised slug reads as nonsense to Arabic and
   English speakers alike, while an English one stays readable in a WhatsApp
   share, a backlink and an analytics report. Unique across every page.
6. A page with no matching keywords still appears (empty keyword_ids).
7. long_tail_ids (only if a LONG-TAIL list appears above): same one-id-one-page
   rule. Never use one as primary_keyword_id — it carries no volume, so it
   cannot justify targeting a page. Skip any that fit no page.
""" + (f"""8. LANGUAGE: write every `q`, `answer_angle` and `entities_to_mention`
   value in {CONTENT_LANG_NAME} (real {CONTENT_LANG_NAME} customer phrasing).
   Do NOT translate the page `name` (copy it exactly) or the JSON keys.
""" if CONTENT_LANG_NAME else "") + """
RETURN JSON ONLY:
{{"services": [{{"name": "exact page name", "url_slug": "english-words-only",
  "primary_keyword_id": 1,
  "keyword_ids": [1, 2], "long_tail_ids": [31, 44],
  "questions": [{{"q": "...", "answer_angle": "...",
  "type": "conversational|voice|paa|local"}}],
  "h2_outline": [{{"h2": "conversion-shaped heading in the site language",
    "keyword_ids": [5, 12], "entities": ["..."]}}],
  "internal_links": ["exact name of a RELATED page in this category"],
  "attributes": [{{"attribute": "cost", "covers": "one sentence on what this page must say"}}],
  "entities_to_mention": ["..."]}}], "excluded_ids": [3]}}"""

    raw = claude_json(client, ASSIGN_SYSTEM, prompt)
    by_norm = {_norm(s): s for s in category["services"]}
    seen_ids = set()
    services_out = {s: None for s in category["services"]}
    for svc in raw.get("services", []):
        real_name = by_norm.get(_norm(svc.get("name", "")))
        if not real_name or services_out.get(real_name):
            continue
        ids, tail_ids = [], []
        for i in svc.get("keyword_ids", []):
            try:
                i = int(i)
            except (TypeError, ValueError):
                continue
            if i in by_id and i not in seen_ids:
                # Same rule as the cluster pipeline: a Stage 1.6 autocomplete
                # query with no Planner volume is heading/FAQ wording, never a
                # page's target keyword. Demote it rather than lose it.
                (tail_ids if is_long_tail(by_id[i]) else ids).append(i)
                seen_ids.add(i)
        for i in svc.get("long_tail_ids", []):
            try:
                i = int(i)
            except (TypeError, ValueError):
                continue
            if i in by_id and i not in seen_ids and is_long_tail(by_id[i]):
                tail_ids.append(i)
                seen_ids.add(i)
        try:
            prim = int(svc.get("primary_keyword_id"))
        except (TypeError, ValueError):
            prim = ids[0] if ids else None
        if prim not in ids:
            prim = ids[0] if ids else None
        questions = [{"q": str(q["q"]).strip(),
                      "answer_angle": str(q.get("answer_angle", "")).strip(),
                      "type": q.get("type", "conversational")}
                     for q in svc.get("questions", [])[:6] if q.get("q")]
        services_out[real_name] = {
            "name": real_name,
            "primary_keyword": expand_kw(by_id[prim]) if prim else None,
            "keywords": [expand_kw(by_id[i]) for i in ids],
            "total_volume": sum(by_id[i]["avg_monthly_searches"] for i in ids),
            "questions": questions,
            "entities_to_mention": [str(e).strip() for e in
                                    svc.get("entities_to_mention", []) if str(e).strip()],
            "long_tail": [by_id[i]["keyword"] for i in tail_ids],
            # English URL. Falls back to a romanised slug only if the model
            # skipped it — a readable English path is the whole point, but a
            # page must never end up without one.
            "url_slug": _clean_slug(svc.get("url_slug"), real_name),
            # Body skeleton. Each H2 owns a slice of the page's keywords, so a
            # query that could never fit the title still has a home — the
            # Riyadh leak page had 73 distinct queries and only the top few
            # could reach the title/intro. ids are validated against THIS
            # page's own set and used once, so a heading cannot claim a
            # keyword that belongs to another section or another page.
            "h2_outline": _validate_outline(svc.get("h2_outline"), ids, by_id),
            # Related pages by MEANING. The builder used to pick link targets
            # mechanically — same-category siblings plus two from each other
            # category — so a Google Ads page linked to whatever happened to
            # sit first elsewhere. Names are validated against the real page
            # list below, and self-links dropped.
            "internal_links": [str(x).strip() for x in
                               (svc.get("internal_links") or [])[:4]
                               if str(x).strip()],
            # Coverage contract for this page, in demand order. The builder
            # turns each into a section, so this is also what makes the page
            # grow when the data justifies it instead of staying a fixed size.
            "attributes": [
                {"attribute": str(a.get("attribute", "")).strip()[:40],
                 "covers": str(a.get("covers", "")).strip()[:300]}
                for a in (svc.get("attributes") or [])[:7]
                if str(a.get("attribute", "")).strip()],
        }
    # Pages Claude skipped still exist — the builder falls back to its
    # own guessed keywords for them (volume 0 = visible in the report).
    return [services_out[s] or {"name": s, "primary_keyword": None, "keywords": [],
                                "total_volume": 0, "questions": [],
                                "entities_to_mention": [], "long_tail": [],
                                "attributes": [], "h2_outline": [],
                                "url_slug": _clean_slug("", s)}
            for s in category["services"]]



# ══════════════════════════════════════════════════════════════════════════
# SERP merge guard + core/outer + publish order
# ══════════════════════════════════════════════════════════════════════════

SERP_GROUP_OVERLAP = int(os.environ.get("SERP_GROUP_OVERLAP", "4"))
SERP_MAX_QUERIES = int(os.environ.get("SERP_MAX_QUERIES", "60"))


def _serp_urls(keyword, gl, hl, num=10):
    """Top organic URLs for one query. Same SerpApi key Mode 6 already uses,
    and only the result URLs — no page fetching, so no scraping credits."""
    key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if not key:
        return None
    try:
        import urllib.parse, urllib.request
        q = urllib.parse.urlencode({"engine": "google", "q": keyword,
                                    "num": num, "gl": gl or "us",
                                    "hl": hl or "en", "api_key": key})
        with urllib.request.urlopen(f"https://serpapi.com/search?{q}", timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        out = []
        for res in (data.get("organic_results") or [])[:num]:
            u = str(res.get("link") or "")
            if u.startswith("http") and "google." not in u:
                out.append(u.split("?")[0].rstrip("/").lower())
        return out
    except Exception:
        return None


def assign_serp_groups(plan_categories, gl, hl):
    """Group pages whose primary keywords return the SAME SERP.

    The one Koray check the data alone cannot make. Keyword ids being
    mutually exclusive stops two pages sharing a KEYWORD; it says nothing
    about two pages chasing the same RESULT SET. The roofing plan split
    "roofing seo company" and "roofing seo services" into separate pages —
    different strings, one SERP, so the two pages would only have competed
    with each other.

    One search per page (1 SerpApi credit each), URLs only. Pages sharing
    SERP_GROUP_OVERLAP of the top ten get the same serp_group_id and every
    page after the first in a group is flagged serp_merge_into. Nothing is
    deleted — the call is the user's.

    No key, or any failure, leaves every page ungrouped."""
    pages = [s for c in plan_categories for s in c["services"]
             if (s.get("primary_keyword") or {}).get("keyword")]
    if not pages or not os.environ.get("SERPAPI_API_KEY", "").strip():
        return 0
    pages = sorted(pages, key=lambda s: -(s.get("total_volume") or 0))[:SERP_MAX_QUERIES]
    print(f"\n🔍 SERP merge guard — {len(pages)} queries "
          f"({len(pages)} SerpApi credits)...")
    serps = {}
    for s in pages:
        kw = s["primary_keyword"]["keyword"]
        urls = _serp_urls(kw, gl, hl)
        if urls:
            serps[s["name"]] = set(urls)
        time.sleep(1.2)
    if len(serps) < 2:
        print("   ℹ️ not enough SERP data — pages left ungrouped")
        return 0
    groups, gid = {}, 0
    for s in pages:
        name = s["name"]
        if name not in serps or name in groups:
            continue
        gid += 1
        groups[name] = gid
        s["serp_group_id"] = gid
        for other in pages:
            o = other["name"]
            if o == name or o in groups or o not in serps:
                continue
            if len(serps[name] & serps[o]) >= SERP_GROUP_OVERLAP:
                groups[o] = gid
                other["serp_group_id"] = gid
                other["serp_merge_into"] = name
                print(f"   ⚠️  '{o}' shares "
                      f"{len(serps[name] & serps[o])}/10 results with '{name}' "
                      f"— same SERP, consider ONE page")
    merged = sum(1 for s in pages if s.get("serp_merge_into"))
    print(f"   ✅ {gid} distinct SERPs across {len(serps)} pages"
          + (f" | {merged} merge candidate(s)" if merged else " | no overlap"))
    return merged


def assign_sections(plan_categories):
    """core = the page that earns; outer = the page that supports it.

    Derived, not asked for: a page whose primary keyword is transactional or
    BOFU is what a buyer lands on ready to hire — core. Informational/TOFU
    pages exist to build authority and hand it to core through their links.

    publish_order is the build order: core first, highest demand first. Even
    when everything ships the same day, generating the money pages first
    means a run that dies halfway still leaves the pages that matter."""
    pages = [s for c in plan_categories for s in c["services"]]
    for s in pages:
        pk = s.get("primary_keyword") or {}
        s["section"] = ("core" if (pk.get("intent") in ("transactional", "commercial")
                                   or pk.get("funnel") == "BOFU") else "outer")
    order = sorted(pages, key=lambda s: (0 if s["section"] == "core" else 1,
                                         -(s.get("total_volume") or 0)))
    for i, s in enumerate(order, 1):
        s["publish_order"] = i
    n_core = sum(1 for s in pages if s["section"] == "core")
    print(f"   🎯 {n_core} core / {len(pages) - n_core} outer pages "
          f"(core generates first)")


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def main():
    # Windows console guard (same as score_keywords.py): emoji prints crash
    # on cp1252 terminals. Actions/Linux unaffected.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except Exception:
            pass

    if not SERVICES:
        print("❌ SERVICES_MODE3 is empty — paste the same comma-separated "
              "service list you give the website builder's Mode 3.")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is missing.")
        sys.exit(1)

    from google.ads.googleads.client import GoogleAdsClient
    ads_client = GoogleAdsClient.load_from_env()
    claude = anthropic.Anthropic()

    location_id = resolve_location_id(ads_client)
    # Precedence: explicit numeric LANGUAGE_ID > LANGUAGE code (API-resolved) >
    # per-seed script detect (unchanged). Blank LANGUAGE = old behavior.
    language_id, lang_label = detect_language_id(SERVICES)
    if os.environ.get("LANGUAGE_ID", "").strip():
        language_id, lang_label = os.environ["LANGUAGE_ID"].strip(), "explicit LANGUAGE_ID"
    elif CONTENT_LANGUAGE:
        _rid = resolve_language_from_code(ads_client, CONTENT_LANGUAGE)
        if _rid:
            language_id, lang_label = _rid, f"'{CONTENT_LANGUAGE}' (code)"
    print(f"🗣️ Language: {lang_label}"
          + (f" | output in {CONTENT_LANG_NAME}" if CONTENT_LANG_NAME else ""))

    print(f"\n🗂️ Stage A — grouping {len(SERVICES)} services into categories...")
    if AC_PER_CAT > 0:
        globals()["_AC_CITY_TERM"], globals()["_AC_EXCLUDE"] = local_place_terms(claude)

    categories, site_context = group_services(claude, SERVICES)
    if site_context.get("central_entity"):
        print(f"   🎯 central entity: {site_context['central_entity']}")
    print(f"   ✅ {len(categories)} categories: " +
          ", ".join(f"{c['name']} ({len(c['services'])})" for c in categories))

    plan_categories = []
    global_seen = set()
    for cat in categories:
        print(f"\n📡 Stage B — Google Ads pull for '{cat['name']}' "
              f"({len(cat['services'])} seeds, {(len(cat['services']) - 1) // ADS_SEED_LIMIT + 1} call(s))...")
        keywords = fetch_category_keywords(ads_client, cat, location_id, language_id, global_seen)
        print(f"   ✅ {len(keywords)} unique keywords with volume")

        if keywords:
            print(f"🧠 Stage D — assigning keywords to {len(cat['services'])} pages...")
            services = assign_keywords(claude, cat, keywords)
        else:
            services = [{"name": s, "primary_keyword": None, "keywords": [],
                         "total_volume": 0, "questions": [], "entities_to_mention": []}
                        for s in cat["services"]]

        services.sort(key=lambda s: -s["total_volume"])
        plan_categories.append({
            "name": cat["name"],
            "description": cat["description"],
            "total_volume": sum(s["total_volume"] for s in services),
            "services": services,
        })

    # Demand-first ordering: highest-volume categories/pages generate first
    plan_categories.sort(key=lambda c: -c["total_volume"])
    all_services_ordered = [s["name"] for c in plan_categories for s in c["services"]]

    assign_sections(plan_categories)
    assign_serp_groups(plan_categories, _AC_GL, CONTENT_LANGUAGE or "en")

    # Areas hiding in the pages' keyword sets → Mode 5, not Mode 3 pages.
    areas = extract_area_targets(claude, plan_categories, _AC_CITY_TERM)
    top_service = (max((s for c in plan_categories for s in c["services"]),
                       key=lambda s: s.get("total_volume") or 0)["name"]
                   if plan_categories else "")

    out = {
        "business": {"name": BUSINESS_NAME, "niche": NICHE_DESCRIPTION,
                     "location": TARGET_LOCATION},
        "model_used": MODEL,
        # The website builder reads this to auto-match its own language, so you
        # only pick the language ONCE (here). Blank = English.
        "language": CONTENT_LANGUAGE or "",
        "mode3_site_plan": {
            "industry_label": NICHE_DESCRIPTION[:40],
            # Site-wide framing. The builder puts these in front of the writer
            # on EVERY page, which is what stops 100 pages reading as 100
            # unrelated pages — each one is visibly about the same entity,
            # published by the same source.
            "central_entity": site_context.get("central_entity", ""),
            "source_context": site_context.get("source_context", ""),
            "categories": plan_categories,
            # Real, volume-backed areas. The builder shows these under "Areas
            # We Serve" instead of the neighbourhood list it used to invent
            # with an AI call. Text only — Mode 5 picks one of five slug
            # patterns per city, so Mode 3 cannot predict an area page's URL
            # and linking before Mode 5 has run would only ship 404s.
            "areas_served": areas,
            # Paste-ready inputs for the dedicated Mode 5 area pipeline. Its
            # `extra_areas` field exists for areas people search that the geo
            # dataset does not carry — which is exactly what these are.
            "mode5_handover": {
                "target_location": TARGET_LOCATION,
                "primary_service": top_service,
                "extra_areas": ", ".join(a["area"] for a in areas),
                "language": CONTENT_LANGUAGE or "",
            },
            "workflow_inputs": {
                "services_mode3": ", ".join(all_services_ordered),
            },
        },
    }
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    total_kw = sum(len(s["keywords"]) for c in plan_categories for s in c["services"])
    total_q = sum(len(s["questions"]) for c in plan_categories for s in c["services"])
    no_demand = [s["name"] for c in plan_categories for s in c["services"] if s["total_volume"] == 0]
    print(f"\n✅ Mode 3 site plan: {len(plan_categories)} categories, "
          f"{len(all_services_ordered)} pages, {total_kw} keywords, {total_q} questions")
    if no_demand:
        print(f"ℹ️ {len(no_demand)} service(s) had NO measurable search volume "
              f"(builder will use its own guessed keywords for these):")
        for s in no_demand:
            print(f"   - {s}")
    print(f"✅ Saved: {JSON_OUT} — push_results.py will publish the raw link.")


if __name__ == "__main__":
    main()
