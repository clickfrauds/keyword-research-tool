"""
keyword_research.py
--------------------
Pulls real search-volume data from Google Ads Keyword Planner (via the
official Google Ads API) for a list of seed keywords + a target location.

This version reads EVERYTHING from environment variables, so it can run
inside GitHub Actions using repository Secrets — no yaml file, no
hardcoded credentials anywhere in this file.

Required env vars (set as GitHub Secrets, see workflow file):
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
A text file (keyword_data_output.txt) with:
    keyword | avg_monthly_searches | competition
sorted by search volume (highest first).
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

LOCATION_ID = os.environ.get("LOCATION_ID", "2784")  # UAE
LANGUAGE_ID = os.environ.get("LANGUAGE_ID", "1000")  # English

OUTPUT_FILE = "keyword_data_output.txt"

# ============================================================
# SCRIPT — no need to edit below this line
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
        competition = metrics.competition.name if metrics.competition else "UNKNOWN"
        rows.append((idea.text, avg_searches, competition))

    # Sort highest volume first, drop zero-volume noise
    rows = [r for r in rows if r[1] > 0]
    rows.sort(key=lambda r: r[1], reverse=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{'keyword':<50} {'avg_monthly_searches':>20} {'competition':>15}\n")
        f.write("-" * 90 + "\n")
        for keyword, searches, competition in rows:
            f.write(f"{keyword:<50} {searches:>20} {competition:>15}\n")

    print(f"✅ Done. {len(rows)} keywords with real search volume saved to {OUTPUT_FILE}")
    print("Next step: open that file, copy its contents, and paste it back to Claude")
    print("to get the problem_clusters string for Mode 4.")


if __name__ == "__main__":
    main()
