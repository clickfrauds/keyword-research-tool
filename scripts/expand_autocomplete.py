"""
Stage 1.6 — QUERY NETWORK EXPANSION  (SEO deliverables only — never the Ads run)

WHY THIS EXISTS
    Keyword Planner only surfaces queries it has advertiser data for. A real
    roofing-SEO run came back with 26 keywords for a whole website; the
    SEO strategy stage then had to invent the long tail, so every "question"
    in the plan was a model's guess rather than something a human typed.

    Google Autocomplete returns queries out of Google's own search logs. A
    suggestion existing at all is proof the query gets searched — that is the
    one thing an LLM cannot fabricate. Measured on the two runs in the repo's
    history:

        roofing SEO (B2B, narrow)  :  26 →  264 queries   (depth 2, ~4 min)
        AC repair Dubai (local)    :   3 seeds → 219 queries, 97% on-topic, 29s

    The AC run discovered "dubai marina" / "dubai hills" (real neighbourhoods
    for Mode 5) and "ac annual maintenance contract dubai" (a BOFU money term)
    — none of which Planner had returned.

WHAT IT DOES
    1. Probes autocomplete around each seed (alphabet soup + question /
       commercial prefixes + intent suffixes), optionally a second pass.
    2. Drops topic drift with an anchor-token filter derived FROM THE SEEDS —
       without it, "roofer ppc" pulls in "ppc vs ppc cement" (measured: 34%
       junk at depth 1, 50% at depth 2).
    3. Asks Planner for real metrics on the survivors via
       GenerateKeywordHistoricalMetrics (takes an explicit keyword list, unlike
       GenerateKeywordIdeas which invents its own).
    4. Merges into keyword_data_output.json in Stage 1's exact record shape, so
       Stage 2.5 scores old and new keywords identically.

    Keywords Planner has no volume for are KEPT with volume 0 and
    source="autocomplete". They are not page targets — they are FAQ/H2 fodder,
    and they are exactly the long tail AI Overviews answer.

INPUT   keyword_data_output.json   (Stage 1)
OUTPUT  keyword_data_output.json   (same file, more rows, every row tagged
                                    with `source`: "planner" | "autocomplete")

FAIL-OPEN BY DESIGN: every failure path leaves the Stage 1 file byte-for-byte
untouched and exits 0. This stage can never break a run.

Required env vars:
    SEED_KEYWORDS         same comma-separated list Stage 1 used
    GOOGLE_ADS_*          the same five secrets (only for the volume lookup;
                          without them the queries still land, at volume 0)
Optional env vars:
    TARGET_LOCATION       free text — resolves the autocomplete `gl` country
                          and the Planner geo target
    LOCATION_ID           explicit geo override (skips resolution)
    LANGUAGE / LANGUAGE_ID
    AC_DEPTH              1 or 2 (default 2). Depth 2 costs ~3 extra minutes.
    AC_MAX_SEEDS_D2       how many depth-1 queries get re-probed (default 45)
    AC_MAX_QUERIES        hard cap on new queries kept (default 600)
    AC_HIST_CHUNK         keywords per historical-metrics request (default 500)
    AC_WORKERS            parallel autocomplete requests (default 8)
"""

import os
import re
import sys
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Windows consoles default to cp1252 and die on the status emoji (same guard
# every other stage in this repo carries).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IN_OUT_FILE = "keyword_data_output.json"

ENDPOINT = "https://suggestqueries.google.com/complete/search"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SEED_KEYWORDS = [s.strip() for s in
                 os.environ.get("SEED_KEYWORDS", "").split(",") if s.strip()]
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()
LOCATION_ID = os.environ.get("LOCATION_ID", "").strip()
LANGUAGE = os.environ.get("LANGUAGE", "").strip().lower()
LANGUAGE_ID = os.environ.get("LANGUAGE_ID", "").strip()

DEPTH = int(os.environ.get("AC_DEPTH", "2"))
MAX_SEEDS_D2 = int(os.environ.get("AC_MAX_SEEDS_D2", "45"))
MAX_QUERIES = int(os.environ.get("AC_MAX_QUERIES", "600"))
HIST_CHUNK = int(os.environ.get("AC_HIST_CHUNK", "500"))
WORKERS = int(os.environ.get("AC_WORKERS", "8"))

# ── Probe vocabulary ───────────────────────────────────────────────────────
# Alphabet soup finds the tail Google itself ranks; the prefix/suffix sets
# force the informational and commercial angles a page has to cover.
ALPHA = list("abcdefghijklmnopqrstuvwxyz")
QUESTION_PREFIX = ["how", "why", "what", "when", "which", "where", "who",
                   "is", "are", "do", "does", "can"]
COMMERCIAL_PREFIX = ["best", "top", "cheap", "affordable", "cost of",
                     "price of", "hire"]
INTENT_SUFFIX = ["cost", "price", "near me", "vs", "for", "services",
                 "company", "agency", "reviews", "packages", "worth it",
                 "checklist", "examples", "guide"]

# Google now mixes Gemini-style prompts into chrome-client suggestions
# ("Recommend roofing seo company choices based on a reasonable budget").
# Those are not queries anybody types into a search box.
_ASSISTANT_PROMPT = re.compile(
    r"^(recommend|generate|write|explain|summarize|summarise|create|draft|"
    r"compare and|help me)\b", re.I)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at", "by",
    "with", "my", "your", "near", "me", "best", "top", "how", "what", "why",
    "is", "are", "do", "does", "can", "vs", "cost", "price", "services",
    "service", "company", "companies",
}


# ══════════════════════════════════════════════════════════════════════════
# Anchor-token relevance filter
# ══════════════════════════════════════════════════════════════════════════

def _tokens(s):
    return re.findall(r"[^\W_]+", str(s).lower(), re.UNICODE)


def _stem(t):
    """Crude 5-char prefix stem. Enough to tie roofing/roofers/roofer and
    maintenance/maintain together without dragging in a stemming library."""
    return t[:5]


def anchor_prefixes(seeds, coverage=0.5):
    """Stems that appear in at least `coverage` of the seeds.

    These describe what the run is ABOUT. Derived from the seeds themselves so
    the filter works for any niche in any language — nothing is hardcoded."""
    if not seeds:
        return []
    counts = {}
    for s in seeds:
        for stem in {_stem(t) for t in _tokens(s)
                     if t not in _STOPWORDS and len(t) > 1}:
            counts[stem] = counts.get(stem, 0) + 1
    need = max(1, round(coverage * len(seeds)))
    return sorted([p for p, n in counts.items() if n >= need])


def is_relevant(query, anchors):
    """A query must hit at least TWO anchor stems (or all of them, when the
    seeds only produced one). Measured on real data:

      seeds "ac repair dubai / air conditioning repair dubai / ac maintenance
      dubai" → anchors {ac, dubai, repai}. "ac maintenance dubai marina" keeps
      2 ✓, "air conditioning repair dubai marina" keeps 2 ✓ (synonym survives),
      "dubai marina restaurants" keeps 1 ✗.

    One anchor alone is too loose — that is how "is roofing a good career"
    ("roof") and "how much does seo cost" ("seo") got in during testing."""
    if not anchors:
        return True
    stems = {_stem(t) for t in _tokens(query)}
    hits = sum(1 for a in anchors if a in stems)
    return hits >= min(2, len(anchors))


def clean_suggestion(s):
    s = re.sub(r"\s+", " ", str(s)).strip().lower()
    if not (3 <= len(s) <= 80) or len(s.split()) > 10:
        return None
    if _ASSISTANT_PROMPT.match(s):
        return None
    return s


# ══════════════════════════════════════════════════════════════════════════
# Autocomplete
# ══════════════════════════════════════════════════════════════════════════

def _suggest(args):
    query, hl, gl = args
    params = {"client": "chrome", "q": query}
    if hl:
        params["hl"] = hl
    if gl:
        params["gl"] = gl
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            return data[1] if len(data) > 1 else []
        except Exception:
            if attempt == 0:
                time.sleep(1.0)
    return []


def _probes_for(seed, full=True):
    p = [seed]
    p += [f"{seed} {c}" for c in ALPHA]
    if full:
        p += [f"{q} {seed}" for q in QUESTION_PREFIX]
        p += [f"{c} {seed}" for c in COMMERCIAL_PREFIX]
        p += [f"{seed} {s}" for s in INTENT_SUFFIX]
    return p


def expand_queries(seeds, hl="en", gl=None, depth=2, max_seeds_d2=45,
                   max_queries=600, workers=8, verbose=True):
    """Seeds → a de-duplicated, drift-filtered set of real search queries.

    Importable: generate_mode3_plan.py calls this per service category so the
    100-page builds get the same query network the cluster runs do."""
    seeds = [s for s in (seeds or []) if str(s).strip()]
    if not seeds:
        return [], []

    anchors = anchor_prefixes(seeds)
    if verbose:
        print(f"   ⚓ anchor stems from seeds: {', '.join(anchors) or '(none)'}")

    def run(probe_list):
        probe_list = list(dict.fromkeys(probe_list))
        found = set()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for res in ex.map(_suggest, [(p, hl, gl) for p in probe_list]):
                for r in res:
                    c = clean_suggestion(r)
                    if c:
                        found.add(c)
        return found, len(probe_list)

    probes = []
    for s in seeds:
        probes += _probes_for(s, full=True)
    raw1, n1 = run(probes)
    keep1 = {q for q in raw1 if is_relevant(q, anchors)}
    if verbose:
        print(f"   🔎 depth 1: {n1} probes → {len(raw1)} raw, {len(keep1)} on-topic "
              f"({len(raw1) - len(keep1)} drift dropped)")

    keep = set(keep1)
    if depth >= 2 and keep1:
        # Longest queries first: they are the deepest part of the tail, so
        # re-probing them reaches further than re-probing the head terms.
        d2_seeds = sorted(keep1, key=lambda q: (-len(q.split()), q))[:max_seeds_d2]
        probes2 = []
        for s in d2_seeds:
            probes2 += _probes_for(s, full=False)   # alphabet only — cheaper
        raw2, n2 = run(probes2)
        keep2 = {q for q in raw2 if is_relevant(q, anchors)}
        new2 = keep2 - keep1
        keep |= keep2
        if verbose:
            print(f"   🔎 depth 2: {n2} probes → {len(raw2)} raw, {len(keep2)} on-topic, "
                  f"{len(new2)} new")

    # Never return the seeds themselves as discoveries.
    seed_set = {s.strip().lower() for s in seeds}
    out = sorted(keep - seed_set, key=lambda q: (len(q), q))[:max_queries]
    return out, anchors


# ══════════════════════════════════════════════════════════════════════════
# Planner volumes for an explicit keyword list
# ══════════════════════════════════════════════════════════════════════════

def fetch_historical_metrics(keywords, chunk=500, verbose=True):
    """GenerateKeywordHistoricalMetrics — unlike GenerateKeywordIdeas it scores
    the exact list you hand it. Returns {keyword: Stage-1-shaped row}.

    Any failure returns what it has so far; the caller keeps the rest at
    volume 0 rather than losing the queries."""
    out = {}
    if not keywords:
        return out
    try:
        from google.ads.googleads.client import GoogleAdsClient
        from google.ads.googleads.errors import GoogleAdsException
        from google.api_core.exceptions import ResourceExhausted
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from keyword_research import (classify_trend, peak_months,
                                      detect_language_id, resolve_location_id,
                                      resolve_language_from_code)
    except Exception as e:
        if verbose:
            print(f"   ℹ️ Google Ads client unavailable ({str(e)[:60]}) — "
                  f"queries keep volume 0")
        return out

    customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "").strip()
    if not customer_id:
        if verbose:
            print("   ℹ️ GOOGLE_ADS_CUSTOMER_ID missing — queries keep volume 0")
        return out

    try:
        client = GoogleAdsClient.load_from_env()
        service = client.get_service("KeywordPlanIdeaService")
        location_id = LOCATION_ID or resolve_location_id(client)
        if LANGUAGE_ID:
            language_id = LANGUAGE_ID
        elif LANGUAGE:
            language_id = resolve_language_from_code(client, LANGUAGE) \
                or detect_language_id(keywords[:20])[0]
        else:
            language_id = detect_language_id(keywords[:20])[0]
    except Exception as e:
        if verbose:
            print(f"   ℹ️ Planner setup failed ({str(e)[:60]}) — queries keep volume 0")
        return out

    batches = [keywords[i:i + chunk] for i in range(0, len(keywords), chunk)]
    for bi, batch in enumerate(batches, 1):
        response = None
        for attempt in range(1, 6):
            try:
                request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
                request.customer_id = customer_id
                request.keywords.extend(batch)
                request.language = f"languageConstants/{language_id}"
                if location_id:
                    request.geo_target_constants.append(
                        f"geoTargetConstants/{location_id}")
                request.keyword_plan_network = (
                    client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH)
                request.historical_metrics_options.include_average_cpc = True
                response = service.generate_keyword_historical_metrics(request=request)
                break
            except ResourceExhausted:
                wait = 5 * attempt
                if verbose:
                    print(f"   ⏳ Rate limit on batch {bi}/{len(batches)} — "
                          f"waiting {wait}s (retry {attempt}/5)")
                time.sleep(wait)
            except GoogleAdsException as ex:
                if verbose:
                    print(f"   ⚠️ Planner rejected batch {bi} (continuing):")
                    for error in ex.failure.errors[:3]:
                        print(f"      - {error.message}")
                break
            except Exception as e:
                if verbose:
                    print(f"   ⚠️ Batch {bi} failed ({str(e)[:70]}) — continuing")
                break
        if response is None:
            continue

        for result in response.results:
            metrics = getattr(result, "keyword_metrics", None)
            if metrics is None:
                continue
            monthly = list(getattr(metrics, "monthly_search_volumes", []) or [])
            monthly.sort(key=lambda m: (m.year, m.month))
            vols = [m.monthly_searches for m in monthly]
            out[result.text.lower().strip()] = {
                "keyword": result.text,
                "avg_monthly_searches": metrics.avg_monthly_searches or 0,
                "competition": (metrics.competition.name
                                if metrics.competition else "UNKNOWN"),
                "trend": classify_trend(vols),
                "peak_months": peak_months(monthly),
                "competition_index": metrics.competition_index or 0,
                "low_top_bid": round(
                    (metrics.low_top_of_page_bid_micros or 0) / 1_000_000, 2),
                "high_top_bid": round(
                    (metrics.high_top_of_page_bid_micros or 0) / 1_000_000, 2),
            }
        if verbose:
            print(f"   📊 batch {bi}/{len(batches)}: {len(batch)} sent, "
                  f"{len(out)} with metrics so far")
        if bi < len(batches):
            time.sleep(3)   # same pacing Stage 1 uses on basic access
    return out


def resolve_gl():
    """Country code for the autocomplete request, from the same geo dataset
    generate_locations.py uses. Unresolvable → None (Google geolocates the
    runner instead, which is still better than a wrong country)."""
    if not TARGET_LOCATION or TARGET_LOCATION.upper() in ("N/A", "NA"):
        return None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from generate_locations import fetch_json, resolve_country, GEO_BASE
        index = fetch_json(f"{GEO_BASE}/index.json")
        cc, _name = resolve_country(TARGET_LOCATION, index)
        return (cc or "").lower() or None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════

def main():
    if not os.path.exists(IN_OUT_FILE):
        print(f"ℹ️ {IN_OUT_FILE} not found — Stage 1 has not run. Skipping "
              f"query expansion (non-fatal).")
        return
    if not SEED_KEYWORDS:
        print("ℹ️ SEED_KEYWORDS empty — nothing to expand from. Skipping.")
        return

    try:
        with open(IN_OUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if not isinstance(existing, list):
            raise ValueError("expected a list of keyword rows")
    except Exception as e:
        print(f"⚠️ Could not read {IN_OUT_FILE} ({str(e)[:70]}) — leaving it "
              f"untouched (non-fatal).")
        return

    for row in existing:
        row.setdefault("source", "planner")
    have = {str(r.get("keyword", "")).lower().strip() for r in existing}
    print(f"🌐 Query network expansion — {len(existing)} Planner keywords in, "
          f"{len(SEED_KEYWORDS)} seeds")

    gl = resolve_gl()
    hl = (LANGUAGE or "en")[:5]
    print(f"   🌍 autocomplete locale: hl={hl}, gl={gl or '(auto)'}")

    t0 = time.time()
    try:
        queries, anchors = expand_queries(
            SEED_KEYWORDS, hl=hl, gl=gl, depth=DEPTH,
            max_seeds_d2=MAX_SEEDS_D2, max_queries=MAX_QUERIES,
            workers=WORKERS)
    except Exception as e:
        print(f"⚠️ Autocomplete expansion failed ({str(e)[:80]}) — "
              f"{IN_OUT_FILE} left untouched (non-fatal).")
        return

    new_queries = [q for q in queries if q not in have]
    print(f"   ✨ {len(new_queries)} queries Planner never returned "
          f"({time.time() - t0:.0f}s)")
    if not new_queries:
        print("✅ Nothing new to add — file unchanged.")
        return

    metrics = fetch_historical_metrics(new_queries, chunk=HIST_CHUNK)

    rows = []
    for q in new_queries:
        row = metrics.get(q)
        if row:
            row["source"] = "autocomplete"
        else:
            # No advertiser data ≠ nobody searches it. Autocomplete listing the
            # query IS the proof of demand; the SEO stage treats these as
            # FAQ/heading material rather than page targets.
            row = {
                "keyword": q, "avg_monthly_searches": 0,
                "competition": "UNKNOWN", "trend": "UNKNOWN",
                "peak_months": "", "competition_index": 0,
                "low_top_bid": 0.0, "high_top_bid": 0.0,
                "source": "autocomplete",
            }
        rows.append(row)

    with_vol = sum(1 for r in rows if r["avg_monthly_searches"] > 0)
    merged = existing + rows
    try:
        with open(IN_OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=1, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Could not write {IN_OUT_FILE} ({str(e)[:70]}) — original "
              f"data is still on disk (non-fatal).")
        return

    print(f"✅ Query network: {len(existing)} → {len(merged)} keywords "
          f"({len(rows)} new: {with_vol} with volume, "
          f"{len(rows) - with_vol} zero-volume long tail kept as FAQ fodder)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:            # last-resort guard — never break a run
        print(f"⚠️ Query expansion crashed ({str(e)[:100]}) — pipeline continues.")
