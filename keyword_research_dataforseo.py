"""
DataForSEO Keyword Research Tool
---------------------------------
Fetches keyword ideas + search volume + competition data using DataForSEO's
Google Ads-sourced Keywords Data API (keywords_for_keywords/live endpoint).

This is a drop-in alternative to keyword_research.py (the Google Ads API
version), kept in the same repo. Use this one while waiting for Google Ads
API Basic Access approval. Output format matches keyword_research.py so the
downstream clustering step works the same either way.

Required environment variables:
  DATAFORSEO_LOGIN     - your DataForSEO account login (email)
  DATAFORSEO_PASSWORD  - your DataForSEO account password
  SEED_KEYWORDS        - comma-separated seed keywords (max 20 per request)
  LOCATION_NAME         - e.g. "United Arab Emirates" or "Dubai,United Arab Emirates"
  LANGUAGE_CODE         - e.g. "en"

Output:
  keyword_data_output.txt - keyword | avg_monthly_searches | competition
  sorted by search volume, descending.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error


API_URL = "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_keywords/live"


def get_env(name, default=None, required=True):
    val = os.environ.get(name, default)
    if required and not val:
        print(f"ERROR: missing required environment variable {name}")
        sys.exit(1)
    return val


def main():
    login = get_env("DATAFORSEO_LOGIN")
    password = get_env("DATAFORSEO_PASSWORD")
    seed_keywords_raw = get_env("SEED_KEYWORDS")
    location_name = get_env("LOCATION_NAME", default="United Arab Emirates")
    language_code = get_env("LANGUAGE_CODE", default="en")

    seed_keywords = [k.strip() for k in seed_keywords_raw.split(",") if k.strip()]
    if not seed_keywords:
        print("ERROR: SEED_KEYWORDS produced an empty list after parsing.")
        sys.exit(1)
    if len(seed_keywords) > 20:
        print(f"WARNING: {len(seed_keywords)} seed keywords given, API allows max 20. Truncating to first 20.")
        seed_keywords = seed_keywords[:20]

    credentials = f"{login}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    post_data = [
        {
            "keywords": seed_keywords,
            "location_name": location_name,
            "language_code": language_code,
        }
    ]

    request_body = json.dumps(post_data).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=request_body,
        method="POST",
        headers={
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"DataForSEO HTTP error: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"DataForSEO connection error: {e.reason}")
        sys.exit(1)

    if response_data.get("status_code") != 20000:
        print(f"DataForSEO API error: {response_data.get('status_message')}")
        print(json.dumps(response_data, indent=2))
        sys.exit(1)

    tasks = response_data.get("tasks", [])
    if not tasks:
        print("ERROR: no tasks returned in response.")
        sys.exit(1)

    task = tasks[0]
    if task.get("status_code") != 20000:
        print(f"DataForSEO task error: {task.get('status_message')}")
        sys.exit(1)

    cost = response_data.get("cost", 0)
    print(f"Request cost: ${cost}")

    results = task.get("result") or []
    if not results:
        print("No keyword results returned for the given seed keywords/location.")
        sys.exit(0)

    rows = []
    for item in results:
        keyword = item.get("keyword", "")
        search_volume = item.get("search_volume")
        competition = item.get("competition")
        if search_volume is None:
            search_volume = 0
        if competition is None:
            competition = "n/a"
        rows.append((keyword, search_volume, competition))

    rows.sort(key=lambda r: r[1], reverse=True)

    output_path = "keyword_data_output.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"{'keyword':<50} {'avg_monthly_searches':<22} {'competition'}\n")
        f.write("-" * 90 + "\n")
        for keyword, volume, competition in rows:
            f.write(f"{keyword:<50} {volume:<22} {competition}\n")

    print(f"Wrote {len(rows)} keyword rows to {output_path}")


if __name__ == "__main__":
    main()
