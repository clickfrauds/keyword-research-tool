"""
analyze_with_claude.py  (v2 — ID-based ad grouping, cost-optimized)
--------------------------------------------------------------------
STAGE 3 of the pipeline (runs after score_keywords.py).

WHAT CHANGED vs v1 (and why v1 wasted money):
  v1 sent 80 full clusters and asked Claude for targets + ad groups +
  15-25 FAQs + 15-25 PAA + content briefs in ONE response. That needs
  12-15K output tokens but max_tokens was 8000 → the JSON was truncated
  mid-string on EVERY run ("Unterminated string"), the retry repeated the
  identical call, and ~$1 died for zero output.

  v2 principles:
  - Python (score_keywords.py) already did intent/local/voice/scoring for free.
  - Claude does ONLY what needs language understanding: semantic ad-group
    theming with zero cannibalization.
  - Claude returns keyword IDs, never the keyword text back → output is
    ~1-2K tokens → truncation impossible, cost ~$0.03-0.05 per run on
    Sonnet (20-30 runs per dollar).
  - Content generation (FAQs, briefs, ad copy) is intentionally REMOVED —
    that lives in the website-builder side, separately.

Required env vars:
    ANTHROPIC_API_KEY
    BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION  (business context)

Optional env vars:
    CLAUDE_MODEL     (default: claude-sonnet-5)
    MAX_AD_GROUPS    (default: 7 — Claude may return FEWER if the data
                      only supports fewer distinct themes; never more)

Input : scored_keywords.json
Output: keyword_strategy.json, keyword_strategy.md
"""

import os
import sys
import json
import re

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

INPUT_FILE = "scored_keywords.json"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_AD_GROUPS = int(os.environ.get("MAX_AD_GROUPS", "7"))

BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()


# ══════════════════════════════════════════════════════════════════════════
# Robust JSON parsing (ported from the website-builder's battle-tested code)
# ══════════════════════════════════════════════════════════════════════════

def _repair_control_chars(s):
    out, in_str, esc = [], False, False
    for ch in s:
        if esc:
            out.append(ch); esc = False
        elif ch == '\\':
            out.append(ch); esc = True
        elif ch == '"':
            out.append(ch); in_str = not in_str
        elif in_str and ch == '\n':
            out.append('\\n')
        elif in_str and ch == '\r':
            out.append('\\r')
        elif in_str and ch == '\t':
            out.append('\\t')
        else:
            out.append(ch)
    return ''.join(out)


def _escape_inner_quotes(s):
    out, in_str = [], False
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if not in_str:
            if ch == '"':
                in_str = True
            out.append(ch)
        else:
            if ch == '\\' and i + 1 < n:
                out.append(ch); out.append(s[i + 1]); i += 1
            elif ch == '"':
                j = i + 1
                while j < n and s[j] in ' \t\r\n':
                    j += 1
                if j >= n or s[j] in ',}]:':
                    in_str = False
                    out.append(ch)
                else:
                    out.append('\\"')
            else:
                out.append(ch)
        i += 1
    return ''.join(out)


def parse_json_robust(text):
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find('{'), text.rfind('}') + 1
    if start == -1 or end == 0:
        raise json.JSONDecodeError("no JSON object found", text, 0)
    text = text[start:end]
    for fixer in (lambda t: t,
                  _repair_control_chars,
                  lambda t: _escape_inner_quotes(_repair_control_chars(t)),
                  lambda t: re.sub(r',\s*([}\]])', r'\1',
                                   _escape_inner_quotes(_repair_control_chars(t)))):
        try:
            return json.loads(fixer(text))
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("unrecoverable JSON", text, 0)


# ══════════════════════════════════════════════════════════════════════════
# Prompt
# ══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""You are a senior Google Ads account strategist. You receive
pre-scored keyword data (real Google Ads Keyword Planner numbers, already
deduped, intent-classified and opportunity-scored by an upstream system).

Your ONLY job: organise the commercially viable keywords into tightly-themed
ad groups with ZERO cannibalization. You do NOT write ads, FAQs or content.

Return ONLY a valid JSON object, no markdown fences, exactly this shape:
{{
  "ad_groups": [
    {{
      "name": "short ad group name",
      "theme": "one sentence: the single user intent this group targets",
      "match_type": "phrase|exact",
      "priority": "high|medium|low",
      "keyword_ids": [1, 2, 3],
      "negative_keywords": ["term", "term"]
    }}
  ],
  "excluded_ids": [4, 5],
  "notes": "2-3 sentences max: overall strategy rationale"
}}

HARD RULES:
1. Between 1 and {MAX_AD_GROUPS} ad groups. The COUNT MUST COME FROM THE DATA:
   one group per genuinely distinct commercial theme you can see in the
   keywords. If the data only supports 3 themes, return 3 groups. NEVER pad
   with thin groups, NEVER split one theme into two groups.
2. ZERO CANNIBALIZATION:
   - Every keyword id appears in AT MOST one group.
   - Group themes must be mutually exclusive — a real search query should
     match exactly one group's theme, never two.
   - negative_keywords for each group = the distinctive core terms of the
     OTHER groups (classic negative-keyword siloing), so Google cannot
     serve two of your groups against the same query.
3. EXCLUDE (put in excluded_ids) ids that are: informational/question
   queries (they are SEO content material, not paid-ads material),
   irrelevant to this business, or branded terms of competitors.
4. Reference keywords ONLY by their numeric id. Never echo keyword text.
5. Use the provided scores/volumes/competition to set priority: the group
   holding the best opportunity keywords is "high".
"""


def build_user_prompt(data):
    kept = [k for k in data["keywords"] if k.get("kept_for_ai")]
    lines = []
    for k in kept:
        flags = ",".join(k.get("flags", [])) or "-"
        cpc = f"{k.get('low_top_bid', 0)}-{k.get('high_top_bid', 0)}"
        lines.append(
            f"{k['id']}|{k['keyword']}|vol:{k['avg_monthly_searches']}"
            f"|comp:{k.get('competition_index', 0)}|cpc:{cpc}"
            f"|{k.get('trend', 'UNKNOWN')}|{k.get('intent', '?')}|{flags}|score:{k.get('score', 0)}"
        )
    header = (
        f"BUSINESS: {BUSINESS_NAME or '(not provided)'}\n"
        f"NICHE: {NICHE_DESCRIPTION or '(infer from keywords)'}\n"
        f"LOCATION: {TARGET_LOCATION or '(not local)'}\n\n"
        f"KEYWORDS ({len(kept)} rows — format: id|keyword|volume|competition_index"
        f"|cpc_range|trend|intent|flags|opportunity_score):\n"
    )
    return header + "\n".join(lines), kept


# ══════════════════════════════════════════════════════════════════════════
# Post-validation — Python enforces what the prompt requests
# ══════════════════════════════════════════════════════════════════════════

def validate_strategy(raw, kept):
    by_id = {k["id"]: k for k in kept}
    seen_ids = set()
    groups = []

    for g in raw.get("ad_groups", [])[:MAX_AD_GROUPS]:
        ids = []
        for i in g.get("keyword_ids", []):
            try:
                i = int(i)
            except (TypeError, ValueError):
                continue
            if i in by_id and i not in seen_ids:   # unknown/duplicate ids dropped
                ids.append(i)
                seen_ids.add(i)
        if not ids:
            continue
        kws = [by_id[i] for i in ids]
        groups.append({
            "name": str(g.get("name", "Ad Group")).strip()[:60],
            "theme": str(g.get("theme", "")).strip(),
            "match_type": g.get("match_type", "phrase"),
            "priority": g.get("priority", "medium"),
            "negative_keywords": [str(n).strip().lower() for n in g.get("negative_keywords", []) if str(n).strip()],
            "keywords": [
                {
                    "keyword": k["keyword"],
                    "variants": k.get("variants", []),
                    "avg_monthly_searches": k["avg_monthly_searches"],
                    "competition": k.get("competition", ""),
                    "competition_index": k.get("competition_index", 0),
                    "cpc_range": f"{k.get('low_top_bid', 0)}-{k.get('high_top_bid', 0)}",
                    "trend": k.get("trend", "UNKNOWN"),
                    "peak_months": k.get("peak_months", ""),
                    "intent": k.get("intent", ""),
                    "flags": k.get("flags", []),
                    "score": k.get("score", 0),
                }
                for k in kws
            ],
            "total_volume": sum(k["avg_monthly_searches"] for k in kws),
            "avg_score": round(sum(k.get("score", 0) for k in kws) / len(kws), 1),
        })

    excluded = set()
    for i in raw.get("excluded_ids", []):
        try:
            excluded.add(int(i))
        except (TypeError, ValueError):
            pass
    unassigned = [by_id[i]["keyword"] for i in by_id
                  if i not in seen_ids and i not in excluded]

    # Cross-group overlap warning (theme words shared between group names)
    warn = []
    for a in range(len(groups)):
        for b in range(a + 1, len(groups)):
            ta = set(re.findall(r"[a-z0-9]+", groups[a]["name"].lower()))
            tb = set(re.findall(r"[a-z0-9]+", groups[b]["name"].lower()))
            shared = ta & tb - {"dubai", "repair", "service", "services", "custom", "ad", "group"}
            if len(shared) >= 2:
                warn.append(f"groups '{groups[a]['name']}' and '{groups[b]['name']}' share theme words {sorted(shared)}")

    return groups, sorted(excluded), unassigned, warn


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is missing — check your secrets.")
        sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        print(f"❌ {INPUT_FILE} not found — run score_keywords.py first.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_prompt, kept = build_user_prompt(data)
    est_in = len(SYSTEM_PROMPT + user_prompt) // 4
    print(f"Sending {len(kept)} scored keywords to {MODEL} "
          f"(~{est_in} input tokens, expected cost well under $0.10)...")

    client = anthropic.Anthropic()
    raw = None
    last_err = ""
    for attempt in range(2):
        _prompt = user_prompt
        if attempt == 1:
            _prompt += ("\n\nIMPORTANT: your previous response was not valid JSON. "
                        "Return ONLY the JSON object, nothing else.")
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,          # output is IDs + short strings — tiny
            temperature=0.2,          # deterministic grouping, not creativity
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _prompt},
                      {"role": "assistant", "content": "{"}],  # prefill forces raw JSON
        )
        text = "{" + "".join(b.text for b in response.content if b.type == "text")
        try:
            raw = parse_json_robust(text)
            break
        except json.JSONDecodeError as e:
            last_err = str(e)
            print(f"⚠️ Attempt {attempt + 1}: JSON parse failed ({e}); "
                  + ("retrying with reminder..." if attempt == 0 else "giving up."))

    if raw is None:
        with open("keyword_strategy_raw.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"❌ Could not get valid JSON: {last_err}. Raw saved for debugging.")
        sys.exit(1)

    groups, excluded_ids, unassigned, warnings = validate_strategy(raw, kept)

    # SEO material = what Claude excluded + what Python flagged as question/info
    all_kw = data["keywords"]
    seo_content = [k for k in all_kw
                   if k.get("intent") in ("question", "informational")
                   or k["id"] in excluded_ids]
    voice_qs = [k["keyword"] for k in all_kw if "voice" in k.get("flags", [])]
    local_kws = [k["keyword"] for k in all_kw
                 if "local" in k.get("flags", []) and k.get("kept_for_ai")]

    strategy = {
        "business": {"name": BUSINESS_NAME, "niche": NICHE_DESCRIPTION,
                     "location": TARGET_LOCATION},
        "model_used": MODEL,
        "ad_groups": groups,
        "notes": raw.get("notes", ""),
        "excluded_keyword_ids": excluded_ids,
        "unassigned_keywords": unassigned,
        "cannibalization_warnings": warnings,
        "seo_content_keywords": [
            {"keyword": k["keyword"], "volume": k["avg_monthly_searches"],
             "intent": k.get("intent", ""), "flags": k.get("flags", [])}
            for k in seo_content
        ],
        "voice_search_questions": voice_qs,
        "local_intent_keywords": local_kws,
        # ── legacy shape so generate_reports.py keeps working ──
        "google_ads_targets": [
            {
                "cluster_topic": g["name"],
                "recommended_keywords": [k["keyword"] for k in g["keywords"]],
                "intent": "transactional",
                "suggested_match_type": g["match_type"],
                "priority": g["priority"],
                "trend": max(set(k["trend"] for k in g["keywords"]),
                             key=[k["trend"] for k in g["keywords"]].count),
                "seasonal_schedule": next((k["peak_months"] for k in g["keywords"]
                                           if k["trend"] == "SEASONAL" and k["peak_months"]), None),
                "reasoning": g["theme"],
            }
            for g in groups
        ],
        "faqs": [], "people_also_ask": [], "content_briefs": [],
    }

    with open("keyword_strategy.json", "w", encoding="utf-8") as f:
        json.dump(strategy, f, indent=2, ensure_ascii=False)

    # ── Markdown summary ──
    md = [f"# Google Ads Keyword Strategy — {BUSINESS_NAME or 'Untitled'}\n"]
    if NICHE_DESCRIPTION:
        md.append(f"*{NICHE_DESCRIPTION}* — {TARGET_LOCATION}\n")
    md.append(f"**{len(groups)} ad groups** (data-driven count, max {MAX_AD_GROUPS})\n")
    for g in groups:
        md.append(f"## {g['name']}  `{g['priority']}` `{g['match_type']}`")
        md.append(f"_{g['theme']}_")
        md.append(f"- Total volume: {g['total_volume']}/mo | Avg opportunity score: {g['avg_score']}")
        md.append(f"- Keywords: " + ", ".join(k["keyword"] for k in g["keywords"]))
        if g["negative_keywords"]:
            md.append(f"- Negative keywords (anti-cannibalization): " + ", ".join(g["negative_keywords"]))
        md.append("")
    if strategy["notes"]:
        md.append(f"**Strategy notes:** {strategy['notes']}\n")
    if voice_qs:
        md.append("## Voice-search / question keywords (SEO content, not ads)")
        md.extend(f"- {q}" for q in voice_qs[:20])
        md.append("")
    if warnings:
        md.append("## ⚠️ Possible theme overlap")
        md.extend(f"- {w}" for w in warnings)
    with open("keyword_strategy.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    usage = getattr(response, "usage", None)
    if usage:
        cost = usage.input_tokens * 3 / 1e6 + usage.output_tokens * 15 / 1e6
        print(f"   Tokens: {usage.input_tokens} in / {usage.output_tokens} out "
              f"≈ ${cost:.3f} this run")
    print(f"✅ {len(groups)} ad groups | {len(excluded_ids)} excluded "
          f"| {len(unassigned)} unassigned | {len(warnings)} overlap warnings")
    print("✅ Saved keyword_strategy.json and keyword_strategy.md")


if __name__ == "__main__":
    main()
