"""
analyze_with_claude.py  (UNIVERSAL / niche-agnostic version)
---------------------------------------------------------------
STAGE 3 of the pipeline (runs after filter_and_cluster.py).

This version has NO hardcoded industry (no "AC company in Dubai" baked in).
The business context comes from environment variables, so the exact same
script works for a plumber in Karachi, a SaaS product, an e-commerce store,
a dentist, anything — just change the env vars per client/run.

Claude is also asked to do the intent classification (transactional /
informational / branded) AND merge obvious synonym clusters (e.g. "ac" vs
"air conditioner", "shoes" vs "sneakers") itself, because that requires
real language understanding of the specific niche — something a fixed
Python word-list can never generalize across industries.

Required env vars:
    ANTHROPIC_API_KEY
    BUSINESS_NAME       e.g. "CoolBreeze AC Services"
    NICHE_DESCRIPTION   e.g. "AC repair, installation and maintenance company"
    TARGET_LOCATION     e.g. "Dubai, UAE"  (or "N/A" for non-local businesses)

Optional env vars:
    CLAUDE_MODEL   (default: claude-sonnet-5)
    MAX_CLUSTERS   (default: 80)

Output:
    keyword_strategy.json
    keyword_strategy.md
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

INPUT_FILE = "clustered_keywords.json"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_CLUSTERS = int(os.environ.get("MAX_CLUSTERS", "80"))

BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()

SYSTEM_PROMPT = """You are a senior SEO + Google Ads strategist working across
many different industries. You will be given:
  1. A business context (name, niche, target location)
  2. Pre-clustered keyword research data (real search volume + competition
     from Google Ads Keyword Planner) — clustered mechanically by shared
     words, WITHOUT any industry-specific logic, so some clusters may
     actually be the same real-world topic phrased differently (e.g. "ac"
     vs "air conditioner", "sneakers" vs "shoes") or may be mis-grouped.
     Use your understanding of the business's actual niche to merge or
     re-split clusters where it makes sense.

Your job:
  - Understand the business's real search intent landscape from the data
  - Classify each relevant cluster as transactional (ready to buy/hire),
    informational (researching a problem/topic, not ready to buy), or
    branded (specific product/brand names)
  - Recommend which clusters are worth bidding on in Google Ads
  - Produce genuinely useful FAQ and content ideas for the SPECIFIC niche
    given — do not default to any particular industry's typical vocabulary

Respond with ONLY valid JSON (no markdown fences, no preamble), matching
exactly this shape:

{
  "google_ads_targets": [
    {
      "cluster_topic": "...",
      "recommended_keywords": ["...", "..."],
      "intent": "transactional|informational|branded",
      "suggested_match_type": "phrase|exact|broad",
      "priority": "high|medium|low",
      "reasoning": "1-2 sentences: why this cluster is worth bidding on for THIS specific business, noting the volume/competition tradeoff"
    }
  ],
  "ad_groups": [
    {
      "ad_group_name": "...",
      "keywords": ["...", "..."],
      "suggested_headline": "...",
      "suggested_description": "..."
    }
  ],
  "faqs": [
    {
      "question": "a natural, conversational question a real customer of THIS business would type or ask",
      "answer": "a genuinely helpful, semantically rich answer (2-4 sentences), written for humans not just search engines"
    }
  ],
  "people_also_ask": [
    "question variant 1",
    "question variant 2"
  ],
  "content_briefs": [
    {
      "cluster_topic": "...",
      "content_angle": "what a blog post or landing page targeting this cluster should cover, specific to this business's niche",
      "target_intent": "transactional|informational|branded"
    }
  ]
}

Rules:
- Base every recommendation on the actual volume/competition numbers given, don't invent data.
- Merge clusters that are clearly the same real-world search intent (synonyms, plural/singular, common misspellings) before recommending them — don't treat "ac repair" and "air conditioner repair" as two separate targets.
- Prioritize clusters with real search volume and manageable competition for google_ads_targets.
- Use informational and branded clusters mainly for faqs / people_also_ask / content_briefs, not as paid ad targets, unless the business context specifically suggests otherwise.
- Write FAQs and content briefs in natural, engaging language a real customer of this specific business would find genuinely useful — not generic template text.
- Aim for 15-25 google_ads_targets, 5-10 ad_groups, 15-25 faqs, 15-25 people_also_ask, 10-15 content_briefs.
"""


def build_user_prompt(data):
    clusters = data["clusters"][:MAX_CLUSTERS]
    payload = {
        "business_context": {
            "business_name": BUSINESS_NAME or "(not provided)",
            "niche": NICHE_DESCRIPTION or "(not provided — infer from the keywords themselves)",
            "target_location": TARGET_LOCATION or "(not location-specific)",
        },
        "total_clusters_available": data["total_clusters"],
        "clusters_included_in_this_request": len(clusters),
        "clusters": clusters,
    }
    return json.dumps(payload, ensure_ascii=False)


def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def render_markdown(strategy, data):
    lines = [f"# Keyword Strategy Report — {BUSINESS_NAME or 'Untitled Business'}\n"]
    if NICHE_DESCRIPTION:
        lines.append(f"*Niche: {NICHE_DESCRIPTION}*")
    if TARGET_LOCATION:
        lines.append(f"*Location: {TARGET_LOCATION}*")
    lines.append("")

    lines.append("## 1. Google Ads Target Keywords\n")
    for t in strategy.get("google_ads_targets", []):
        lines.append(f"### {t['cluster_topic']} (priority: {t['priority']}, intent: {t.get('intent','')}, match type: {t['suggested_match_type']})")
        lines.append(f"- Keywords: {', '.join(t['recommended_keywords'])}")
        lines.append(f"- Why: {t['reasoning']}\n")

    lines.append("## 2. Suggested Ad Groups\n")
    for g in strategy.get("ad_groups", []):
        lines.append(f"### {g['ad_group_name']}")
        lines.append(f"- Keywords: {', '.join(g['keywords'])}")
        lines.append(f"- Headline: {g['suggested_headline']}")
        lines.append(f"- Description: {g['suggested_description']}\n")

    lines.append("## 3. FAQs\n")
    for f in strategy.get("faqs", []):
        lines.append(f"**Q: {f['question']}**")
        lines.append(f"A: {f['answer']}\n")

    lines.append("## 4. People Also Ask\n")
    for q in strategy.get("people_also_ask", []):
        lines.append(f"- {q}")
    lines.append("")

    lines.append("## 5. Content Briefs\n")
    for c in strategy.get("content_briefs", []):
        lines.append(f"### {c['cluster_topic']} ({c['target_intent']})")
        lines.append(f"{c['content_angle']}\n")

    return "\n".join(lines)


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is missing — check your secrets.")
        return
    if not NICHE_DESCRIPTION:
        print("⚠️  NICHE_DESCRIPTION is not set. Claude will try to infer the "
              "business type from the keywords, but results will be more "
              "accurate if you set BUSINESS_NAME / NICHE_DESCRIPTION / "
              "TARGET_LOCATION as env vars (or GitHub Secrets/Variables) "
              "for each client/run.")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    client = anthropic.Anthropic()
    user_prompt = build_user_prompt(data)

    print(f"Sending {min(MAX_CLUSTERS, data['total_clusters'])} of {data['total_clusters']} clusters to {MODEL}...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text")

    try:
        strategy = extract_json(raw_text)
    except json.JSONDecodeError as e:
        print("⚠️ Could not parse Claude's response as JSON. Saving raw output for debugging.")
        with open("keyword_strategy_raw.txt", "w", encoding="utf-8") as f:
            f.write(raw_text)
        print(f"Error: {e}")
        return

    with open("keyword_strategy.json", "w", encoding="utf-8") as f:
        json.dump(strategy, f, indent=2, ensure_ascii=False)

    with open("keyword_strategy.md", "w", encoding="utf-8") as f:
        f.write(render_markdown(strategy, data))

    print("✅ Done. Saved keyword_strategy.json and keyword_strategy.md")


if __name__ == "__main__":
    main()
