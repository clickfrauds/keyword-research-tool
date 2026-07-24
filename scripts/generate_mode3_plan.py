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
from generate_seo_strategy import parse_json_robust, enrich, expand_kw

JSON_OUT = "website_builder_inputs.json"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")
BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()
MAX_KW_PER_CAT = int(os.environ.get("MAX_KEYWORDS_PER_CATEGORY", "120"))

SERVICES = [s.strip() for s in os.environ.get("SERVICES_MODE3", "").split(",") if s.strip()]

ADS_SEED_LIMIT = 20          # GenerateKeywordIdeas hard limit: 20 seed keywords/request
ADS_CALL_DELAY = 1.5         # polite pacing between Ads API calls (seconds)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


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

RETURN JSON ONLY:
{{"categories": [{{"name": "Category Name", "description": "1 sentence",
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
    return cats


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
    for i in range(0, len(seeds), ADS_SEED_LIMIT):
        chunk = seeds[i:i + ADS_SEED_LIMIT]
        try:
            rows.extend(ads_fetch_ideas(ads_client, chunk, location_id, language_id))
        except Exception as e:
            print(f"⚠️ Ads call failed for '{category['name']}' chunk {i // ADS_SEED_LIMIT + 1}: "
                  f"{str(e)[:120]} — continuing")
        time.sleep(ADS_CALL_DELAY)
    out, local_seen = [], set()
    for r in sorted(rows, key=lambda r: -r["avg_monthly_searches"]):
        key = _norm(r["keyword"])
        if key and key not in local_seen and key not in global_seen:
            local_seen.add(key)
            out.append(r)
    global_seen.update(local_seen)
    return out[:MAX_KW_PER_CAT]


# ══════════════════════════════════════════════════════════════════════════
# Stage D — per-category Claude assignment (keywords → service pages)
# ══════════════════════════════════════════════════════════════════════════

ASSIGN_SYSTEM = """You are a senior SEO strategist. You assign real
Google Keyword Planner keywords to the service pages of one website
category. Output must be valid JSON only."""


def assign_keywords(client, category, keywords):
    by_id = {}
    lines = []
    for idx, k in enumerate(keywords, 1):
        k = enrich(dict(k, id=idx))
        by_id[idx] = k
        lines.append(f"{idx}|{k['keyword']}|vol:{k['avg_monthly_searches']}"
                     f"|kd:{k['kd_proxy']}|{k['funnel']}|{k.get('trend', '?')}")

    prompt = f"""CATEGORY: {category['name']}
LOCATION: {TARGET_LOCATION or '(not local)'}
SERVICE PAGES in this category (one page each — copy names EXACTLY):
{chr(10).join('- ' + s for s in category['services'])}

KEYWORDS ({len(lines)} rows — id|keyword|volume|kd|funnel|trend):
{chr(10).join(lines)}

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
5. "name" must be a CHARACTER-FOR-CHARACTER copy of a service page name.
6. A page with no matching keywords still appears (empty keyword_ids).
""" + (f"""7. LANGUAGE: write every `q`, `answer_angle` and `entities_to_mention`
   value in {CONTENT_LANG_NAME} (real {CONTENT_LANG_NAME} customer phrasing).
   Do NOT translate the page `name` (copy it exactly) or the JSON keys.
""" if CONTENT_LANG_NAME else "") + """
RETURN JSON ONLY:
{{"services": [{{"name": "exact page name", "primary_keyword_id": 1,
  "keyword_ids": [1, 2], "questions": [{{"q": "...", "answer_angle": "...",
  "type": "conversational|voice|paa|local"}}],
  "entities_to_mention": ["..."]}}], "excluded_ids": [3]}}"""

    raw = claude_json(client, ASSIGN_SYSTEM, prompt)
    by_norm = {_norm(s): s for s in category["services"]}
    seen_ids = set()
    services_out = {s: None for s in category["services"]}
    for svc in raw.get("services", []):
        real_name = by_norm.get(_norm(svc.get("name", "")))
        if not real_name or services_out.get(real_name):
            continue
        ids = []
        for i in svc.get("keyword_ids", []):
            try:
                i = int(i)
            except (TypeError, ValueError):
                continue
            if i in by_id and i not in seen_ids:
                ids.append(i)
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
        }
    # Pages Claude skipped still exist — the builder falls back to its
    # own guessed keywords for them (volume 0 = visible in the report).
    return [services_out[s] or {"name": s, "primary_keyword": None, "keywords": [],
                                "total_volume": 0, "questions": [], "entities_to_mention": []}
            for s in category["services"]]


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
    categories = group_services(claude, SERVICES)
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

    out = {
        "business": {"name": BUSINESS_NAME, "niche": NICHE_DESCRIPTION,
                     "location": TARGET_LOCATION},
        "model_used": MODEL,
        # The website builder reads this to auto-match its own language, so you
        # only pick the language ONCE (here). Blank = English.
        "language": CONTENT_LANGUAGE or "",
        "mode3_site_plan": {
            "industry_label": NICHE_DESCRIPTION[:40],
            "categories": plan_categories,
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
