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
# ORDER MATTERS: check-status.js treats "{id}.html exists" as the run being
# READY, and probes every other link at that same instant. The html must
# therefore be pushed LAST — pushing it first (the old order) opened a race
# where the frontend showed the report but the seo.json/csv/js links were
# still seconds away from existing, so they stayed hidden forever.
FILES_TO_PUSH = [
    ("keyword_strategy_targets.csv", "csv"),
    ("keyword_strategy.json", "json"),
    # Mode 4 feed: publishing this here means the raw link auto-generates —
    # no more manual artifact-download + client-data commit. The frontend
    # shows the link (via check-status.js) the moment the run is ready.
    ("website_builder_inputs.json", "seo.json"),
    # Google Ads deliverables: paste-ready Editor CSV + the negative-guard
    # Ads Script — downloadable straight from the result page, no GitHub
    # artifact digging needed.
    # THE one-import file: campaign settings + ad groups + keywords +
    # negatives + RSAs + locations in a single Editor import.
    ("google_ads_master.csv", "master.csv"),
    ("google_ads_editor.csv", "editor.csv"),
    # Negatives SPLIT into their own file (Jul 2026): the Editor's Keywords
    # grid imported mixed-file Negative Phrase rows as POSITIVE keywords.
    # Paste this one into the "Keywords, Negative" section separately.
    ("google_ads_editor_negatives.csv", "negatives.csv"),
    ("negative_guard_script.js", "guard.js"),
    # Stage 3.7: niche-matched audience plan (positive + negative segments,
    # Editor paste-ready) — downloadable straight from the result page.
    ("audiences_editor.csv", "audiences.csv"),
    # Same split as the keywords file: negative audiences in their own file
    # so a mixed paste can't import them as positives.
    ("audiences_editor_negatives.csv", "audiences_negatives.csv"),
    # Stage 3.8: RSA ad copy — 15 headlines + 4 descriptions per ad group,
    # policy-validated, Google Ads Editor import format.
    ("rsa_editor.csv", "rsa.csv"),
    # Stage 3.9: location targeting rows (real geo target ids) per campaign.
    ("locations_editor.csv", "locations.csv"),
    # LAST on purpose — the readiness marker (see note above).
    ("keyword_strategy_report.html", "html"),
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

    # Mode 3 runs produce ONLY website_builder_inputs.json — no report html.
    # But the frontend's check-status.js uses "{id}.html exists" as its READY
    # signal, so without one the form would poll forever. Publish a tiny stub
    # report that simply presents the seo.json link (still pushed last, after
    # the seo.json itself, to keep the readiness contract).
    if (not os.path.exists("keyword_strategy_report.html")
            and os.path.exists("website_builder_inputs.json")):
        raw_link = (f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}"
                    f"/{RESULTS_BRANCH}/results/{REQUEST_ID}.seo.json")
        stub = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mode 3 Site Plan — ready</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f6f5f2;color:#14181c;
margin:0;padding:40px 20px}}.card{{max-width:640px;margin:0 auto;background:#fdfcfa;border:1px solid #dcdad3;
border-radius:10px;padding:28px}}h1{{font-size:20px;margin:0 0 10px}}p{{font-size:14px;color:#6b6560;line-height:1.6}}
code{{display:block;background:#eef2f1;border:1px solid #dcdad3;border-radius:6px;padding:12px;
font-size:12px;word-break:break-all;margin-top:14px}}</style></head><body>
<div class="card"><h1>✅ Mode 3 Site Plan is ready</h1>
<p>Copy the JSON link below (also shown above this report) and paste it into the
website builder's <strong>seo_inputs_url</strong> field when running <strong>Mode 3</strong>.
Every service page will then use real Google Ads search volumes, assigned keywords
and PAA questions instead of AI guesses.</p>
<code>{raw_link}</code></div></body></html>"""
        with open("mode3_stub_report.html", "w", encoding="utf-8") as f:
            f.write(stub)
        push_file("mode3_stub_report.html", "html")

    if os.path.exists("website_builder_inputs.json"):
        raw_link = (f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}"
                    f"/{RESULTS_BRANCH}/results/{REQUEST_ID}.seo.json")
        print("")
        print("🔗 SEO data link — website builder ke 'SEO data URL' field mein paste karein (Mode 3 ya Mode 4, dono cards mein field hai):")
        print(f"   {raw_link}")


if __name__ == "__main__":
    main()
