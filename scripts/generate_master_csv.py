"""
generate_master_csv.py  (FINAL STAGE — the one-import Editor CSV)
----------------------------------------------------------------------
User request (Jul 2026): "at the end of the tool run give me ONE finished
CSV I import into Google Ads Editor and my complete campaign is built" —
no more juggling 4 separate files in the right order.

Mirrors Google Ads Editor's own multi-record export format: one file, a
superset header, and the Editor infers each row's record type from which
columns are populated:

  campaign row   → Campaign settings baked in the way the user builds
                   campaigns manually: Search only, Google partners OFF,
                   Manual CPC (Enhanced CPC disabled), Paused.
  ad group rows  → Standard type, Enabled, group-median default Max CPC.
  keyword rows   → positives with per-keyword suggested Max CPC.
  negative rows  → ad-group-level Negative Phrase (incl. negatives for
                   the client's existing groups in existing-account mode).
  RSA rows       → read from rsa_editor.csv (Stage 3.8) if present.
  location rows  → read from locations_editor.csv (Stage 3.9) if present,
                   including Claude's bid-tier modifiers (premium +25%,
                   labour/fraud-prone -90%).
  audience rows  → read from audience_plan.json (Stage 3.7) if present:
                   positive (Audience + Bid Modifier + Flexible Reach) and
                   excluded (Negative Audience) — targeting-tool proven cols.

The individual per-type files still ship alongside — this file is the
"just import it" path. Campaigns arrive Paused; budget defaults to
DAILY_BUDGET (account currency) and should be reviewed before enabling.
Excluded locations and excluded audiences ride the same file via the
documented "Type" column (Negative / Campaign negative — answer/57747).
The ONLY thing not in this file is the negative-guard Ads Script
(paste manually in Google Ads → Tools → Scripts).

Env: DAILY_BUDGET (optional, default 1000)
Input : keyword_strategy.json, rsa_editor.csv?, locations_editor.csv?
Output: google_ads_master.csv
"""

import os
import sys
import csv
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STRATEGY = "keyword_strategy.json"
RSA_CSV = "rsa_editor.csv"
LOC_CSV = "locations_editor.csv"
AUD_JSON = "audience_plan.json"
OUT = "google_ads_master.csv"

DAILY_BUDGET = os.environ.get("DAILY_BUDGET", "1000").strip()

N_HEADLINES, N_DESCRIPTIONS = 15, 4

# Superset header — column names exactly as Google Ads Editor recognizes
# them in its own CSV round-trip. Order: campaign cols → ad group cols →
# keyword cols → location cols → ad cols → status.
HEADER = (
    ["Campaign", "Campaign Type", "Networks", "Budget", "Budget type",
     "Bid Strategy Type", "Enhanced CPC", "Final URL suffix", "Campaign Status",
     "Ad Group", "Ad Group Type", "Ad Group Status", "Max CPC",
     "Keyword", "Criterion Type", "ID", "Location", "Bid Modifier",
     "Audience", "Flexible Reach", "Type", "Ad type"]
    + [c for i in range(1, N_HEADLINES + 1)
       for c in (f"Headline {i}", f"Headline {i} position")]
    + [f"Description {j}" for j in range(1, N_DESCRIPTIONS + 1)]
    + ["Path 1", "Path 2", "Final URL", "Status", "Comment"]
)
IDX = {c: i for i, c in enumerate(HEADER)}


def blank_row():
    return [""] * len(HEADER)


def set_cells(row, **cells):
    for col, val in cells.items():
        row[IDX[col.replace("_", " ")]] = val
    return row


def main():
    if not os.path.exists(STRATEGY):
        print(f"⚠️ {STRATEGY} not found — skipping master CSV (non-fatal).")
        return
    with open(STRATEGY, encoding="utf-8") as f:
        strategy = json.load(f)
    groups = strategy.get("ad_groups") or []
    campaigns = [c.get("name") for c in (strategy.get("campaigns") or []) if c.get("name")]
    if not campaigns:
        campaigns = sorted({g.get("campaign") for g in groups if g.get("campaign")})
    if not campaigns or not groups:
        print("⚠️ No campaigns/ad groups in strategy — skipping master CSV.")
        return

    rows = []

    # 1) campaign rows — the settings the user otherwise builds by hand
    for camp in campaigns:
        rows.append(set_cells(
            blank_row(), Campaign=camp, **{
                "Campaign Type": "Search",
                "Networks": "Google search",          # partners OFF
                "Budget": DAILY_BUDGET, "Budget type": "Daily",
                "Bid Strategy Type": "Manual CPC",
                "Enhanced CPC": "Disabled",
                # landing-page DKI: every click carries its bid keyword so the
                # Mode 1 pages' ?kw= H1 message-match swap works automatically
                "Final URL suffix": "kw={keyword}",
                "Campaign Status": "Paused",
            }))

    ctype = {"phrase": "Phrase", "exact": "Exact"}
    for g in groups:
        camp, name = g.get("campaign", campaigns[0]), g.get("name", "Ad Group")
        mt = ctype.get(g.get("match_type"), "Phrase")
        bids = sorted(k["suggested_bid"] for k in g.get("keywords", [])
                      if k.get("suggested_bid"))
        median = bids[len(bids) // 2] if bids else ""

        # 2) ad group row (default bid = group median)
        rows.append(set_cells(
            blank_row(), Campaign=camp, **{
                "Ad Group": name, "Ad Group Type": "Standard",
                "Ad Group Status": "Enabled", "Max CPC": median,
            }))
        # 3) positive keywords (+ intent expansions on the median bid)
        for k in g.get("keywords", []):
            rows.append(set_cells(
                blank_row(), Campaign=camp, **{
                    "Ad Group": name, "Keyword": k.get("keyword", ""),
                    "Criterion Type": mt,
                    "Max CPC": k.get("suggested_bid") or median,
                }))
        for e in g.get("intent_expansion_keywords", []):
            rows.append(set_cells(
                blank_row(), Campaign=camp, **{
                    "Ad Group": name, "Keyword": e,
                    "Criterion Type": "Phrase", "Max CPC": median,
                }))
        # 4) ad-group-level negatives
        for n in g.get("negative_keywords", []):
            rows.append(set_cells(
                blank_row(), Campaign=camp, **{
                    "Ad Group": name, "Keyword": n,
                    "Criterion Type": "Negative Phrase",
                }))

    # negatives for the client's EXISTING ad groups (existing-account mode)
    for gname, terms in (strategy.get("negatives_for_existing_groups") or {}).items():
        for t in terms:
            rows.append(set_cells(
                blank_row(), Campaign=campaigns[0], **{
                    "Ad Group": gname, "Keyword": t,
                    "Criterion Type": "Negative Phrase",
                }))

    # 5) RSA rows — pass through from Stage 3.8's Editor-format CSV
    n_rsa = 0
    if os.path.exists(RSA_CSV):
        with open(RSA_CSV, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                row = blank_row()
                for col, val in r.items():
                    if col in IDX and val:
                        row[IDX[col]] = val
                row[IDX["Status"]] = "Enabled"
                rows.append(row)
                n_rsa += 1

    # 6) location rows — pass through from Stage 3.9 (incl. Claude bid tiers:
    # premium areas +%, labour/fraud-prone areas -90%)
    n_loc = 0
    if os.path.exists(LOC_CSV):
        with open(LOC_CSV, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if not r.get("ID"):
                    continue
                rows.append(set_cells(
                    blank_row(), Campaign=r.get("Campaign", campaigns[0]),
                    **{"ID": r["ID"], "Location": r.get("Location", ""),
                       "Bid Modifier": r.get("Bid Modifier", "")}))
                n_loc += 1

    # 6b) NEGATIVE location rows — the Editor-documented way (answer/57747):
    # same Location columns + Type="Negative" marks the row as an excluded
    # location. (A separate "Negative Audience"-style column is silently
    # ignored; pasting into the normal Locations grid TARGETS them — user
    # hit both failure modes Jul 2026.)
    n_loc_neg = 0
    if os.path.exists("locations_negative.csv"):
        with open("locations_negative.csv", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if not r.get("ID"):
                    continue
                rows.append(set_cells(
                    blank_row(), Campaign=r.get("Campaign", campaigns[0]),
                    **{"ID": r["ID"], "Location": r.get("Location", ""),
                       "Type": "Negative"}))
                n_loc_neg += 1

    # 7) audience rows — from Stage 3.7's structured plan. ALL positives go
    # at CAMPAIGN level: Google forbids positive segments on both an ad
    # group and its parent campaign, and mixed levels red-error the whole
    # import (user hit this Jul 2026). Excluded audiences ride the same
    # file with Type="Campaign negative" (the documented Editor mechanism).
    n_aud = n_aud_neg = 0
    if os.path.exists(AUD_JSON):
        with open(AUD_JSON, encoding="utf-8") as f:
            plan = json.load(f)
        camp_set = set(campaigns)
        seen_aud = set()
        for a in plan.get("positive", []):
            name = a.get("name", "")
            if not name or name.lower() in seen_aud:
                continue
            seen_aud.add(name.lower())
            camp = a.get("campaign") if a.get("campaign") in camp_set else campaigns[0]
            rows.append(set_cells(
                blank_row(), Campaign=camp,
                **{"Audience": name,
                   "Bid Modifier": f"{a['bid_adjustment']}%" if a.get("bid_adjustment") else "",
                   "Flexible Reach": "Audience segments" if a.get("mode") == "targeting" else "",
                   "Comment": f"{a.get('type', '')} | {a.get('mode', '')} | {a.get('reason', '')}"}))
            n_aud += 1
        for a in plan.get("negative", []):
            name = a.get("name", "")
            if not name or ("neg:" + name.lower()) in seen_aud:
                continue
            seen_aud.add("neg:" + name.lower())
            camp = a.get("campaign") if a.get("campaign") in camp_set else campaigns[0]
            rows.append(set_cells(
                blank_row(), Campaign=camp,
                **{"Audience": name, "Type": "Campaign negative",
                   "Comment": f"{a.get('type', '')} | {a.get('reason', '')}"}))
            n_aud_neg += 1

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)

    n_kw = sum(len(g.get("keywords", [])) + len(g.get("intent_expansion_keywords", []))
               for g in groups)
    n_neg = sum(len(g.get("negative_keywords", [])) for g in groups)
    print(f"✅ Master CSV: {len(campaigns)} campaign | {len(groups)} ad groups | "
          f"{n_kw} keywords | {n_neg} negatives | {n_rsa} RSAs | {n_loc} locations | "
          f"{n_aud}+/{n_aud_neg}− audiences | {n_loc_neg} negative locations "
          f"→ {OUT} (one Editor import, campaigns Paused, Manual CPC, partners off)")


if __name__ == "__main__":
    main()
