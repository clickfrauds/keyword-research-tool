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
    LOCATION_ID     (default 2784 = United Arab Emirates)
    LANGUAGE_ID     (default 1000 = English, 1019 = Arabic)

OUTPUT:
    keyword_data_output.txt
    Columns: keyword | avg_monthly_searches | competition | trend | peak_months
    Sorted by search volume (highest first).
"""

import os
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

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
LOCATION_ID = os.environ.get("LOCATION_ID", "2784")   # UAE
LANGUAGE_ID = os.environ.get("LANGUAGE_ID", "1000")   # English
OUTPUT_FILE  = "keyword_data_output.txt"

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# ============================================================
# TREND HELPERS — pure math, no domain knowledge
# ============================================================

def classify_trend(monthly_volumes):
    """
    Takes a list of up to 12 monthly search volumes (oldest → newest)
    and returns one of: GROWING / DECLINING / SEASONAL / STABLE

    Logic:
      - SEASONAL : max month is >= 2.5x the min month (big spike exists)
      - GROWING  : last 3 months average > first 3 months average by 20%+
      - DECLINING: first 3 months average > last 3 months average by 20%+
      - STABLE   : everything else
    """
    vols = [v for v in monthly_volumes if v is not None and v > 0]
    if len(vols) < 3:
        return "UNKNOWN"

    max_v = max(vols)
    min_v = min(vols)

    # Seasonal: huge peak relative to trough
    if min_v > 0 and max_v / min_v >= 2.5:
        return "SEASONAL"

    # Need at least 6 months for growing/declining detection
    if len(vols) >= 6:
        first_avg = sum(vols[:3]) / 3
        last_avg  = sum(vols[-3:]) / 3
        if first_avg > 0:
            change = (last_avg - first_avg) / first_avg
            if change >= 0.20:
                return "GROWING"
            if change <= -0.20:
                return "DECLINING"

    return "STABLE"


def peak_months(monthly_volumes):
    """
    Returns the names of months whose volume is >= 80% of the max volume.
    E.g. for AC repair in UAE, summer months will dominate.
    Returns empty string if no meaningful data.
    """
    vols = monthly_volumes  # list of 12 values, some may be None
    if not vols:
        return ""

    clean = [(i, v) for i, v in enumerate(vols) if v is not None and v > 0]
    if not clean:
        return ""

    max_v = max(v for _, v in clean)
    peaks = [MONTH_NAMES[i] for i, v in clean if v >= 0.80 * max_v]
    return "/".join(peaks)


# ============================================================
# MAIN
# ============================================================

def main():
    if not CUSTOMER_ID:
        print("❌ GOOGLE_ADS_CUSTOMER_ID is missing — check your secrets.")
        return

    client = GoogleAdsClient.load_from_env()
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = CUSTOMER_ID
    request.language = f"languageConstants/{LANGUAGE_ID}"
    request.geo_target_constants.append(f"geoTargetConstants/{LOCATION_ID}")
    request.keyword_plan_network = (
        client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    )
    request.keyword_seed.keywords.extend(SEED_KEYWORDS)

    # ── Ask for historical monthly breakdown + CPC ─────────────────────────
    # include_adult_keywords defaults to False — fine to leave unset.
    # historical_metrics_options lets us request the month-by-month breakdown.
    # (with GOOGLE_ADS_USE_PROTO_PLUS=true, nested message fields are set
    # directly — no .CopyFrom() needed/available on proto-plus objects)
    # CPC + competition_index now ENABLED — the scoring stage (Stage 2.5)
    # uses them to rank keywords from a real Google Ads bidding perspective.
    request.historical_metrics_options.include_average_cpc = True
    # ──────────────────────────────────────────────────────────────────────

    try:
        response = keyword_plan_idea_service.generate_keyword_ideas(
            request=request
        )
    except GoogleAdsException as ex:
        print("Google Ads API error:")
        for error in ex.failure.errors:
            print(f"  - {error.message}")
        return

    rows = []
    for idea in response:
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
        peak       = peak_months(monthly_vols)
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
