"""
push_results.py
----------------
STAGE 5 of the pipeline (runs after generate_reports.py).

Pushes the finished HTML + CSV + JSON to a dedicated "results-data" branch
in this same repo, using the GitHub Contents API. This is how the Netlify
form (via its check-status function) finds out a report is ready — it
polls for a file named results/{REQUEST_ID}.html on that branch.

Uses only Python's standard library (urllib) — no extra pip install needed.

ONE-TIME SETUP — run this once, locally, before your first pipeline run:

    git checkout --orphan results-data
    git reset --hard
    git commit --allow-empty -m "init results branch"
    git push origin results-data
    git checkout main

Required env vars (already provided automatically by keyword_pipeline.yml):
    GITHUB_TOKEN         -> ${{ secrets.GITHUB_TOKEN }}
    GITHUB_REPOSITORY    -> ${{ github.repository }}   (e.g. "naseem/keyword-pipeline")
    REQUEST_ID           -> the unique id for this run
Optional:
    RESULTS_BRANCH       (default: "results-data")
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
REQUEST_ID = os.environ.get("REQUEST_ID", "").strip()
RESULTS_BRANCH = os.environ.get("RESULTS_BRANCH", "results-data")

# (local_filename, extension_to_publish_as)
FILES_TO_PUSH = [
    ("keyword_strategy_report.html", "html"),
    ("keyword_strategy_targets.csv", "csv"),
    ("keyword_strategy.json", "json"),
    # Mode 4 feed: publishing this here means the raw link auto-generates —
    # no more manual artifact-download + client-data commit. The frontend
    # shows the link (via check-status.js) the moment the run is ready.
    ("website_builder_inputs.json", "seo.json"),
    # Google Ads deliverables: paste-ready Editor CSV + the negative-guard
    # Ads Script — downloadable straight from the result page, no GitHub
    # artifact digging needed.
    ("google_ads_editor.csv", "editor.csv"),
    ("negative_guard_script.js", "guard.js"),
    # Stage 3.7: niche-matched audience plan (positive + negative segments,
    # Editor paste-ready) — downloadable straight from the result page.
    ("audiences_editor.csv", "audiences.csv"),
]


def _existing_sha(url):
    """Contents API needs the current sha to UPDATE a file — without it a
    re-run with the same REQUEST_ID fails with 422."""
    req = urllib.request.Request(f"{url}?ref={RESULTS_BRANCH}")
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8")).get("sha")
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None


def push_file(local_path, remote_ext):
    if not os.path.exists(local_path):
        print(f"⚠️  Skipping {local_path} — file not found.")
        return

    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("utf-8")

    remote_path = f"results/{REQUEST_ID}.{remote_ext}"
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{remote_path}"

    payload = {
        "message": f"Add {remote_ext} result for {REQUEST_ID}",
        "content": content_b64,
        "branch": RESULTS_BRANCH,
    }
    sha = _existing_sha(url)
    if sha:
        payload["sha"] = sha
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
        print(f"✅ Pushed {remote_path} to branch '{RESULTS_BRANCH}'")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"❌ Failed to push {remote_path}: {e.code} {e.reason}")
        print(err_body)
        if e.code in (404, 422):
            print(
                f"   → Does the '{RESULTS_BRANCH}' branch exist yet? "
                "Run the ONE-TIME SETUP commands from this file's docstring "
                "once, before your first pipeline run."
            )


def main():
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        print("❌ GITHUB_TOKEN or GITHUB_REPOSITORY missing — check workflow env / permissions.")
        sys.exit(1)
    if not REQUEST_ID:
        print("❌ REQUEST_ID missing — cannot name the result file.")
        sys.exit(1)

    for local_path, ext in FILES_TO_PUSH:
        push_file(local_path, ext)

    if os.path.exists("website_builder_inputs.json"):
        raw_link = (f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}"
                    f"/{RESULTS_BRANCH}/results/{REQUEST_ID}.seo.json")
        print("")
        print("🔗 SEO data link — website builder ke 'SEO data URL' field mein paste karein (Mode 3 ya Mode 4, dono cards mein field hai):")
        print(f"   {raw_link}")


if __name__ == "__main__":
    main()
