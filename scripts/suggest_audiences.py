"""
suggest_audiences.py  (STAGE 3.7 — niche-matched Google Ads audience plan)
----------------------------------------------------------------------------
Runs after analyze_with_claude.py. Takes keyword_strategy.json + the master
Google Ads audience list (data/audiences.json — 3,500+ real segment names:
In-Market, Affinity, Topics/Verticals, App-install, New-phone) and asks
claude-sonnet-5 to pick, for THIS business:

  POSITIVE audiences — who to reach, with the level Google's own best
    practice dictates for Search campaigns:
      * default   = CAMPAIGN level, OBSERVATION mode + bid adjustment
                    (observation never restricts reach — it just lets you
                    bid up the people most likely to convert)
      * ad_group  = only when a segment maps to exactly ONE ad group's theme
      * targeting = (narrowing) recommended at most 1-2 ultra-high-intent
                    In-Market segments, and only for tight budgets/remarketing
  NEGATIVE audiences — campaign-level exclusions (job seekers, DIY,
    students, bargain hunters for premium services...).

Every returned name is validated against the master list — a hallucinated
segment name can never reach your Editor import.

The master list is sent as a CACHED system prompt (Anthropic prompt caching)
so repeat runs pay ~10% of the input cost.

Outputs:
  audiences_editor.csv           — Google Ads Editor import (positive
                                   audiences, same proven format as the
                                   ClickAds Protector targeting tool)
  audiences_editor_negatives.csv — negative audiences (separate file —
                                   the Editor can't take a mixed paste)
  audience_plan.json             — full structured plan
  audiences.md                   — human-readable summary with the strategy note

Env vars: ANTHROPIC_API_KEY, BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION
Optional: CLAUDE_MODEL (default claude-sonnet-5),
          CLAUDE_EFFORT_AUDIENCES (default low)
Input : keyword_strategy.json, data/audiences.json
Output: audiences_editor.csv, audiences_editor_negatives.csv,
        audience_plan.json, audiences.md
"""

import os
import re
import sys
import csv
import json

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

STRATEGY_FILE = "keyword_strategy.json"
AUDIENCES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "audiences.json")

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
EFFORT = os.environ.get("CLAUDE_EFFORT_AUDIENCES", "low")
BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()

# Segment types usable for Search-campaign audience targeting. Topics/
# VERTICAL_GEO and app-install lists are Display/YouTube-only — loaded but
# never offered to the model for a Search plan.
SEARCH_TYPES = ("IN_MARKET", "AFFINITY")


def robust_json(text):
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text.strip(), flags=re.MULTILINE).strip()
    s, e = text.find("{"), text.rfind("}") + 1
    return json.loads(text[s:e])


def load_master():
    with open(AUDIENCES_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    by_type = {}
    for a in raw:
        t = str(a.get("type", "")).strip().upper()
        n = str(a.get("name", "")).strip()
        if t and n:
            by_type.setdefault(t, [])
            if n not in by_type[t]:
                by_type[t].append(n)
    return by_type


def build_system(by_type):
    """Fixed system prompt carrying the full In-Market + Affinity lists —
    marked for prompt caching so the ~10k tokens are cached across runs."""
    in_market = by_type.get("IN_MARKET", [])
    affinity = by_type.get("AFFINITY", [])
    return f"""You are a senior Google Ads audience strategist for SEARCH campaigns.

Below is the COMPLETE master list of Google Ads audience segments available.
You may ONLY pick names from this list. Copy each name EXACTLY as written —
your output is machine-validated against this list and any mismatch is dropped.

IN-MARKET SEGMENTS ({len(in_market)}):
{chr(10).join(in_market)}

AFFINITY SEGMENTS ({len(affinity)}):
{chr(10).join(affinity)}

Return ONLY valid JSON (no markdown fences):
{{
  "positive": [
    {{"name": "...", "type": "IN_MARKET|AFFINITY",
      "level": "campaign|ad_group",
      "campaign": "exact campaign name from the user message",
      "ad_group": "exact ad group name (ONLY when level=ad_group, else omit)",
      "mode": "observation|targeting",
      "bid_adjustment": 15,
      "reason": "max 10 words"}}
  ],
  "negative": [
    {{"name": "...", "type": "IN_MARKET|AFFINITY",
      "campaign": "exact campaign name",
      "reason": "max 10 words why exclude"}}
  ],
  "strategy_note": "3-4 short lines of practical advice for this account"
}}

SEARCH-CAMPAIGN BEST PRACTICE (follow strictly):
1. positive: 10-15 segments. High-intent IN_MARKET first, then supporting
   AFFINITY. Order by expected conversion impact.
2. LEVEL: default is "campaign" — audiences observed campaign-wide is
   Google's recommended Search setup. Use "ad_group" ONLY when a segment
   maps to exactly ONE ad group's theme (e.g. "Home Cleaning Services"
   segment → the deep-cleaning ad group, not the whole account).
3. MODE: default "observation" (never restricts reach; enables bid
   adjustments). Recommend "targeting" (narrowing) for AT MOST 1-2
   ultra-high-intent IN_MARKET segments, and only if the niche is premium /
   budget-sensitive.
4. bid_adjustment: observation segments get +10 to +30 (%) based on intent
   strength; "targeting" rows get 0. Never negative here.
5. negative: 5-8 segments that attract WRONG clicks for this business:
   job seekers (Employment), students/education for non-education niches,
   DIY-leaning segments, bargain hunters for premium services, business
   segments for consumer services (and vice versa).
6. Never put the same segment in both positive and negative.
7. campaign / ad_group values must EXACTLY match the names in the user
   message."""


def build_user(strategy):
    campaigns = [c["name"] for c in strategy.get("campaigns", [])]
    lines = [
        f"BUSINESS: {BUSINESS_NAME or strategy.get('business', {}).get('name', '')}",
        f"NICHE: {NICHE_DESCRIPTION or strategy.get('business', {}).get('niche', '')}",
        f"TARGET LOCATION: {TARGET_LOCATION or strategy.get('business', {}).get('location', '')}",
        "",
        f"CAMPAIGNS: {json.dumps(campaigns)}",
        "",
        "AD GROUPS (name | campaign | theme | top keywords):",
    ]
    for g in strategy.get("ad_groups", []):
        kws = ", ".join(k["keyword"] for k in g.get("keywords", [])[:6])
        lines.append(f"- {g['name']} | {g['campaign']} | {g.get('theme', '')} | {kws}")
    return "\n".join(lines)


def ask_claude(system_text, user_text):
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=8000,
        output_config={"effort": EFFORT},
        system=[{"type": "text", "text": system_text,
                 "cache_control": {"type": "ephemeral"}}],  # prompt caching
        messages=[{"role": "user", "content": user_text}],
    ) as stream:
        resp = stream.get_final_message()
    text = "".join(b.text for b in resp.content if b.type == "text")
    usage = resp.usage
    cost = usage.input_tokens * 3 / 1e6 + usage.output_tokens * 15 / 1e6
    print(f"   Claude audience plan: {usage.input_tokens} in / {usage.output_tokens} out ≈ ${cost:.3f}")
    return robust_json(text)


def validate_plan(raw, by_type, strategy):
    """Machine-check every name/level/campaign the model returned."""
    lookup = {}   # casefolded name -> (canonical name, type)
    for t in SEARCH_TYPES:
        for n in by_type.get(t, []):
            lookup.setdefault(n.casefold(), (n, t))

    campaigns = [c["name"] for c in strategy.get("campaigns", [])]
    default_campaign = campaigns[0] if campaigns else (BUSINESS_NAME or "Campaign")
    camp_set = set(campaigns)
    group_names = {g["name"] for g in strategy.get("ad_groups", [])}

    positive, negative, dropped = [], [], []
    seen = set()

    for a in raw.get("positive", []) or []:
        hit = lookup.get(str(a.get("name", "")).strip().casefold())
        if not hit or hit[0] in seen:
            dropped.append(a.get("name"))
            continue
        name, atype = hit
        seen.add(name)
        level = a.get("level") if a.get("level") in ("campaign", "ad_group") else "campaign"
        ad_group = str(a.get("ad_group", "")).strip()
        if level == "ad_group" and ad_group not in group_names:
            level, ad_group = "campaign", ""   # unknown group → safe default
        if level == "campaign":
            ad_group = ""
        camp = str(a.get("campaign", "")).strip()
        if camp not in camp_set:
            camp = default_campaign
        mode = a.get("mode") if a.get("mode") in ("observation", "targeting") else "observation"
        try:
            adj = int(float(a.get("bid_adjustment", 0) or 0))
        except (TypeError, ValueError):
            adj = 0
        adj = min(max(adj, 0), 100)
        if mode == "targeting":
            adj = 0
        positive.append({"name": name, "type": atype, "level": level,
                         "campaign": camp, "ad_group": ad_group, "mode": mode,
                         "bid_adjustment": adj,
                         "reason": str(a.get("reason", "")).strip()})

    for a in raw.get("negative", []) or []:
        hit = lookup.get(str(a.get("name", "")).strip().casefold())
        if not hit or hit[0] in seen:
            dropped.append(a.get("name"))
            continue
        name, atype = hit
        seen.add(name)
        camp = str(a.get("campaign", "")).strip()
        if camp not in camp_set:
            camp = default_campaign
        negative.append({"name": name, "type": atype, "campaign": camp,
                         "reason": str(a.get("reason", "")).strip()})

    if dropped:
        print(f"   🛡️ Dropped {len(dropped)} names not in the master list / duplicates: "
              f"{[d for d in dropped if d][:6]}")
    return positive, negative, str(raw.get("strategy_note", "")).strip()


def write_editor_csv(positive, negative):
    """Google Ads Editor import files — TWO separate CSVs. Same proven column
    set as the ClickAds Protector targeting tool. Split (Jul 2026) for the
    same reason as google_ads_editor.csv (commit dc20ab3): a mixed file pasted
    in one go imports every row as the first record type, so positives and
    negatives ship as their own files, imported one at a time via
    Account → Import → Paste text (or select file)."""
    with open("audiences_editor.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Campaign", "Ad Group", "Audience", "Bid Modifier",
                    "Flexible Reach", "Comment"])
        for a in positive:
            w.writerow([
                a["campaign"], a["ad_group"], a["name"],
                f"{a['bid_adjustment']}%" if a["bid_adjustment"] else "",
                "Audience segments" if a["mode"] == "targeting" else "",
                f"{a['type']} | {a['mode']} | {a['reason']}",
            ])
    with open("audiences_editor_negatives.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Campaign", "Ad Group", "Negative Audience", "Comment"])
        for a in negative:
            w.writerow([a["campaign"], "", a["name"], f"{a['type']} | {a['reason']}"])


def write_md(positive, negative, note):
    md = [f"# 🎯 Google Ads Audience Plan — {BUSINESS_NAME or 'Untitled'}\n"]
    if NICHE_DESCRIPTION:
        md.append(f"*{NICHE_DESCRIPTION}* — {TARGET_LOCATION}\n")
    md.append("## ✅ Positive audiences (add + observe, bid up)\n")
    md.append("| Audience | Type | Level | Where | Mode | Bid adj | Why |")
    md.append("|---|---|---|---|---|---|---|")
    for a in positive:
        where = a["ad_group"] or a["campaign"]
        adj = f"+{a['bid_adjustment']}%" if a["bid_adjustment"] else "—"
        md.append(f"| {a['name']} | {a['type']} | {a['level']} | {where} "
                  f"| {a['mode']} | {adj} | {a['reason']} |")
    md.append("\n## 🚫 Negative audiences (campaign-level exclusions)\n")
    md.append("| Audience | Type | Campaign | Why |")
    md.append("|---|---|---|---|")
    for a in negative:
        md.append(f"| {a['name']} | {a['type']} | {a['campaign']} | {a['reason']} |")
    if note:
        md.append(f"\n## 💡 Strategy\n{note}\n")
    md.append("\n## 📥 How to import\n"
              "1. Google Ads Editor → Account → Import → *Paste text* (or select "
              "file) → **audiences_editor.csv** (positive audiences).\n"
              "2. Repeat with **audiences_editor_negatives.csv** (negative "
              "audiences) — a separate import, never mixed with the positives.\n"
              "3. Review, then Post. Observation rows never restrict reach — "
              "they only enable the bid adjustments.")
    with open("audiences.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is missing.")
        sys.exit(1)
    if not os.path.exists(STRATEGY_FILE):
        print(f"❌ {STRATEGY_FILE} not found — run analyze_with_claude.py first.")
        sys.exit(1)
    if not os.path.exists(AUDIENCES_FILE):
        print(f"❌ {AUDIENCES_FILE} not found — master audience list missing.")
        sys.exit(1)

    with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
        strategy = json.load(f)

    by_type = load_master()
    print(f"Master audience list: " + ", ".join(
        f"{t}: {len(v)}" for t, v in sorted(by_type.items())))

    raw = ask_claude(build_system(by_type), build_user(strategy))
    positive, negative, note = validate_plan(raw, by_type, strategy)

    if not positive:
        print("❌ No valid positive audiences returned — nothing to write.")
        sys.exit(1)

    # Google forbids positive audience segments on both an ad group and its
    # parent campaign — with single-campaign mode (the default) any ad-group
    # level entry conflicts with the campaign-level ones and red-errors the
    # Editor import. Demote everything to campaign level and dedupe.
    if os.environ.get("SINGLE_CAMPAIGN", "").strip().lower() not in ("", "false", "0", "no", "off"):
        seen_names, flat = set(), []
        for a in positive:
            if a["name"].lower() in seen_names:
                continue
            seen_names.add(a["name"].lower())
            a["ad_group"], a["level"] = "", "campaign"
            flat.append(a)
        if len(flat) != len(positive):
            print(f"   🎯 Single-campaign mode: audiences flattened to campaign level "
                  f"({len(positive)} → {len(flat)})")
        positive = flat

    write_editor_csv(positive, negative)
    write_md(positive, negative, note)
    with open("audience_plan.json", "w", encoding="utf-8") as f:
        json.dump({"positive": positive, "negative": negative,
                   "strategy_note": note}, f, indent=2, ensure_ascii=False)

    n_camp = sum(1 for a in positive if a["level"] == "campaign")
    n_ag = len(positive) - n_camp
    print(f"✅ Audience plan: {len(positive)} positive ({n_camp} campaign-level, "
          f"{n_ag} ad-group-level) | {len(negative)} negative")
    print("✅ Saved: audiences_editor.csv, audiences_editor_negatives.csv, "
          "audience_plan.json, audiences.md")


if __name__ == "__main__":
    main()
