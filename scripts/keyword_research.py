"""
keyword_research.py
--------------------
Pulls real search-volume data from Google Ads Keyword Planner (via the
official Google Ads API) for a list of seed keywords + a target location.

UPDATED: Now also pulls 12-month historical data to detect:
  - GROWING   keywords (volume increasing month over month)
  - DECLINING  keywords (volume dropping — avoid bidding)
  - SEASONAL   keywords (spike in specific months)
  - STABLE     keywords (consistent volume year-round)

This version reads EVERYTHING from environment variables, so it can run
inside GitHub Actions using repository Secrets — no yaml file, no
hardcoded credentials anywhere in this file.

Required env vars (set as GitHub Secrets):
    GOOGLE_ADS_DEVELOPER_TOKEN
    GOOGLE_ADS_CLIENT_ID
    GOOGLE_ADS_CLIENT_SECRET
    GOOGLE_ADS_REFRESH_TOKEN
    GOOGLE_ADS_CUSTOMER_ID      (digits only, no dashes)

Optional env vars (have defaults):
    SEED_KEYWORDS   (comma-separated, e.g. "ac repair dubai,ac not cooling")
    TARGET_LOCATION (free text, e.g. "Dubai, UAE" / "Lahore, Pakistan" —
                     auto-resolved to a Google geo target id via the API.
                     UNIVERSAL: no country is hardcoded anywhere.)
    LOCATION_ID     (explicit override — skips auto-resolution)
    LANGUAGE_ID     (explicit override — otherwise auto-detected from the
                     seed keywords' script, e.g. Arabic seeds → Arabic)

OUTPUT:
    keyword_data_output.txt
    Columns: keyword | avg_monthly_searches | competition | trend | peak_months
    Sorted by search volume (highest first).
"""

import os
import re
import time
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.api_core.exceptions import ResourceExhausted

# ============================================================
# CONFIG — pulled from environment variables, with safe defaults
# ============================================================
CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
SEED_KEYWORDS = [
    kw.strip()
    for kw in os.environ.get(
        "SEED_KEYWORDS",
        "ac repair dubai,ac not cooling,ac service dubai,air conditioner repair",
    ).split(",")
    if kw.strip()
]
# UNIVERSAL geo/language: nothing hardcoded. Explicit ids win; otherwise the
# free-text TARGET_LOCATION is resolved via the Google Ads API and the
# language is detected from the seed keywords themselves.
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()
LOCATION_ID = os.environ.get("LOCATION_ID", "").strip()
LANGUAGE_ID = os.environ.get("LANGUAGE_ID", "").strip()
OUTPUT_FILE  = "keyword_data_output.txt"

# ============================================================
# TREND HELPERS — pure math, no domain knowledge
# ============================================================

def classify_trend(monthly_volumes):
    """
    Takes a list of up to 12 monthly search volumes (oldest → newest)
    and returns one of: GROWING / DECLINING / SEASONAL / STABLE

    GROWING/DECLINING are checked FIRST — a keyword growing steadily 2.5x
    used to be mislabeled SEASONAL just because its max/min ratio crossed
    the spike threshold. The middle-3 average must sit between the ends so
    a single seasonal spike can't fake a trend. Zero months are KEPT: a
    dead off-season is the strongest seasonal signal there is.

      - GROWING  : last-3 avg >= 1.2x first-3 avg, middle-3 in between
      - DECLINING: mirror image
      - SEASONAL : dead (0) months alongside live ones, or max >= 2.5x min
      - STABLE   : everything else
    """
    vols = [v for v in monthly_volumes if v is not None]
    nonzero = [v for v in vols if v > 0]
    if len(nonzero) < 3:
        return "UNKNOWN"

    if len(vols) >= 6:
        first_avg = sum(vols[:3]) / 3
        last_avg  = sum(vols[-3:]) / 3
        mid_start = (len(vols) - 3) // 2
        mid_avg   = sum(vols[mid_start:mid_start + 3]) / 3
        if first_avg > 0:
            if last_avg >= first_avg * 1.2 and mid_avg >= first_avg * 0.95:
                return "GROWING"
            if first_avg >= last_avg * 1.2 and mid_avg <= first_avg * 1.05:
                return "DECLINING"

    if len(vols) > len(nonzero) and max(nonzero) >= 10:
        return "SEASONAL"
    if min(nonzero) > 0 and max(nonzero) / min(nonzero) >= 2.5:
        return "SEASONAL"

    return "STABLE"


# Google Ads MonthOfYear enum name → short label. Positional lookup was wrong:
# the API's 12-month window starts wherever "12 months ago" falls (e.g. a
# Jul→Jun window), so index 0 is almost never January.
MONTH_ENUM_ABBR = {
    "JANUARY": "Jan", "FEBRUARY": "Feb", "MARCH": "Mar", "APRIL": "Apr",
    "MAY": "May", "JUNE": "Jun", "JULY": "Jul", "AUGUST": "Aug",
    "SEPTEMBER": "Sep", "OCTOBER": "Oct", "NOVEMBER": "Nov", "DECEMBER": "Dec",
}


def peak_months(monthly_data):
    """
    Returns the names of months whose volume is >= 80% of the max volume,
    using each row's OWN month enum from the API (never list position).
    Takes the sorted monthly_search_volumes objects. Empty string if no data.
    """
    clean = []
    for m in monthly_data:
        v = m.monthly_searches
        name = MONTH_ENUM_ABBR.get(getattr(m.month, "name", str(m.month)), "")
        if v and v > 0 and name:
            clean.append((name, v))
    if not clean:
        return ""

    max_v = max(v for _, v in clean)
    return "/".join(name for name, v in clean if v >= 0.80 * max_v)


# ============================================================
# UNIVERSAL GEO + LANGUAGE RESOLUTION — no market hardcoded
# ============================================================

def detect_language_id(seeds):
    """Pick the Keyword Planner language from the seeds' own script.
    Explicit LANGUAGE_ID env always wins. Extend the map as markets grow."""
    text = " ".join(seeds)
    if re.search(r"[؀-ۿ]", text):      # Arabic script
        return "1019", "Arabic (auto-detected from seeds)"
    if re.search(r"[ऀ-ॿ]", text):      # Devanagari
        return "1023", "Hindi (auto-detected from seeds)"
    return "1000", "English (default)"


def resolve_location_id(client):
    """Resolve free-text TARGET_LOCATION ('Dubai, UAE', 'Lahore', 'United
    Kingdom' — any market) to a geo target constant id via the official
    GeoTargetConstantService. Returns None → worldwide (no geo filter)."""
    if LOCATION_ID:
        print(f"🌍 Location: explicit LOCATION_ID={LOCATION_ID} (env override)")
        return LOCATION_ID
    loc = TARGET_LOCATION
    if not loc or loc.lower() in ("n/a", "na", "none", "worldwide", "global", "-"):
        print("🌍 Location: none given — pulling WORLDWIDE data.")
        return None
    try:
        svc = client.get_service("GeoTargetConstantService")
        parts = [p.strip() for p in loc.split(",") if p.strip()]
        for query in [loc] + parts:
            request = client.get_type("SuggestGeoTargetConstantsRequest")
            request.locale = "en"
            request.location_names.names.append(query)
            resp = svc.suggest_geo_target_constants(request=request)
            suggestions = list(resp.geo_target_constant_suggestions)
            if suggestions:
                geo = suggestions[0].geo_target_constant
                print(f"🌍 Location resolved: '{query}' → {geo.name}, "
                      f"{geo.country_code} (geo id {geo.id})")
                return str(geo.id)
    except Exception as e:
        print(f"⚠️ Geo lookup failed ({e}) — continuing WORLDWIDE (no geo filter).")
        return None
    print(f"⚠️ Could not resolve '{loc}' to a Google geo target — "
          f"continuing WORLDWIDE. Set LOCATION_ID env to override.")
    return None


# ============================================================
# MAIN
# ============================================================

def main():
    if not CUSTOMER_ID:
        print("❌ GOOGLE_ADS_CUSTOMER_ID is missing — check your secrets.")
        return

    client = GoogleAdsClient.load_from_env()
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

    # Universal targeting: resolve geo from the form's free-text location and
    # language from the seeds' own script — works for any market on earth.
    location_id = resolve_location_id(client)
    # Language is resolved PER SEED, not per run: one Arabic seed in a mixed
    # list used to flip the WHOLE run to Arabic, so every English seed was
    # pulled under the Arabic language filter and returned almost nothing.
    if LANGUAGE_ID:
        print(f"🗣️ Language: explicit LANGUAGE_ID={LANGUAGE_ID} (all seeds)")
    else:
        print("🗣️ Language: auto-detected per seed "
              "(mixed Arabic+English lists pull each seed in its own language)")

    def pull_ideas(seeds, language_id):
        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = CUSTOMER_ID
        request.language = f"languageConstants/{language_id}"
        if location_id:
            request.geo_target_constants.append(f"geoTargetConstants/{location_id}")
        request.keyword_plan_network = (
            client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        )
        request.keyword_seed.keywords.extend(seeds)
        # historical_metrics_options: month-by-month breakdown + CPC — the
        # scoring stage ranks from a real bidding perspective. (proto-plus:
        # nested fields set directly, no .CopyFrom())
        request.historical_metrics_options.include_average_cpc = True
        return keyword_plan_idea_service.generate_keyword_ideas(request=request)

    # ── ONE REQUEST PER SEED, merged (fix for the 45-keyword run, Jul 2026):
    # a combined multi-seed request makes Google INTERSECT the themes and
    # return a fraction of the ideas ("electrician dubai" + 5 specific seeds
    # → 45 ideas). Pulled separately, each seed brings its own full long-tail
    # (the appliance run's 5 broader seeds → 545). Same lesson as Mode 3's
    # per-category batching. 6 requests instead of 1 — nothing for the quota.
    # Basic-access accounts rate-limit this method per-minute; one fat seed
    # ("glass for railing" → 1,496 ideas) burns the allowance and the next
    # request 429s (ResourceExhausted — NOT a GoogleAdsException, so it used
    # to crash the whole run). Pace the seeds and retry with backoff.
    ideas_by_text = {}
    for i, seed in enumerate(SEED_KEYWORDS):
        if i:
            time.sleep(3)
        seed_lang = LANGUAGE_ID or detect_language_id([seed])[0]
        response = None
        for attempt in range(1, 6):
            try:
                response = pull_ideas([seed], seed_lang)
                break
            except ResourceExhausted:
                wait = 5 * attempt
                print(f"   ⏳ Rate limit on '{seed}' — waiting {wait}s (retry {attempt}/5)")
                time.sleep(wait)
            except GoogleAdsException as ex:
                print(f"⚠️ Planner error for seed '{seed}' (continuing):")
                for error in ex.failure.errors:
                    print(f"  - {error.message}")
                break
        if response is None:
            print(f"⚠️ Skipping seed '{seed}' — still failing after retries.")
            continue
        n_new = 0
        for idea in response:
            key = idea.text.lower().strip()
            if key and key not in ideas_by_text:
                ideas_by_text[key] = idea
                n_new += 1
        lang_tag = {"1000": "en", "1019": "ar", "1023": "hi"}.get(seed_lang, seed_lang)
        print(f"   🌱 '{seed}' [{lang_tag}]: +{n_new} new ideas (running total {len(ideas_by_text)})")
    if not ideas_by_text:
        print("❌ No keyword ideas returned for any seed — check seeds/geo.")
        return

    rows = []
    for idea in ideas_by_text.values():
        metrics = idea.keyword_idea_metrics

        avg_searches = metrics.avg_monthly_searches or 0
        competition  = metrics.competition.name if metrics.competition else "UNKNOWN"

        # Competition index (0-100, granular) + top-of-page bid range (micros → currency)
        comp_index = metrics.competition_index if metrics.competition_index else 0
        low_bid  = round((metrics.low_top_of_page_bid_micros  or 0) / 1_000_000, 2)
        high_bid = round((metrics.high_top_of_page_bid_micros or 0) / 1_000_000, 2)

        # ── NEW: extract 12-month breakdown ───────────────────────────────
        # monthly_search_volumes is a repeated field of MonthlySearchVolume
        # Each entry has .month (MonthOfYear enum, 1=Jan … 12=Dec) and
        # .monthly_searches (int64).  The list comes back newest-first from
        # the API, so we reverse it to get oldest→newest order for trend math.
        monthly_data = list(metrics.monthly_search_volumes)

        if monthly_data:
            # Sort by year then month (oldest first)
            monthly_data.sort(key=lambda m: (m.year, m.month))
            monthly_vols = [m.monthly_searches for m in monthly_data]
        else:
            monthly_vols = []

        trend      = classify_trend(monthly_vols)
        peak       = peak_months(monthly_data)
        # ──────────────────────────────────────────────────────────────────

        if avg_searches > 0:
            rows.append((idea.text, avg_searches, competition, trend, peak,
                         comp_index, low_bid, high_bid))

    # Sort highest volume first
    rows.sort(key=lambda r: r[1], reverse=True)

    # ── Write output ───────────────────────────────────────────────────────
    # Two extra columns vs the old format: trend | peak_months
    # filter_and_cluster.py handles these gracefully (it splits on 2+ spaces
    # and takes col[0]=keyword, col[1]=volume, col[2]=competition — the extra
    # cols are simply ignored in Stage 2, and passed through in Stage 3).
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(
            f"{'keyword':<50} {'avg_monthly_searches':>20} {'competition':>15}"
            f" {'trend':>10} {'peak_months':>20}\n"
        )
        f.write("-" * 120 + "\n")
        for keyword, searches, competition, trend, peak, *_ in rows:
            f.write(
                f"{keyword:<50} {searches:>20} {competition:>15}"
                f" {trend:>10} {peak:>20}\n"
            )

    # Structured JSON — Stage 2.5 (score_keywords.py) reads this directly;
    # no fragile column parsing, and it carries CPC/competition_index data
    # that the fixed-width txt can't hold without breaking old parsers.
    import json as _json
    with open("keyword_data_output.json", "w", encoding="utf-8") as f:
        _json.dump([
            {
                "keyword": kw, "avg_monthly_searches": vol, "competition": comp,
                "trend": trend, "peak_months": peak,
                "competition_index": ci, "low_top_bid": lo, "high_top_bid": hi,
            }
            for kw, vol, comp, trend, peak, ci, lo, hi in rows
        ], f, indent=1, ensure_ascii=False)

    print(f"✅ Done. {len(rows)} keywords saved to {OUTPUT_FILE} (+ keyword_data_output.json)")

    # Quick summary so you can see the trend breakdown at a glance
    from collections import Counter
    trend_counts = Counter(r[3] for r in rows)
    print("\nTrend summary:")
    for t, count in sorted(trend_counts.items()):
        print(f"  {t:<12} {count} keywords")


if __name__ == "__main__":
    main()
