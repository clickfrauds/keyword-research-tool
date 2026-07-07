"""
filter_and_cluster.py  (UNIVERSAL / niche-agnostic version)
--------------------------------------------------------------
STAGE 2 of the pipeline (runs after keyword_research.py).

This version has NO hardcoded business vocabulary (no "repair", "dubai",
"samsung" etc.). It works the same way whether the keywords are about
AC repair, running shoes, project management software, or dentists.

What it does (purely mechanical, works for any niche):
  1. Parses raw keyword_data_output.txt / .csv (keyword, avg_monthly_searches,
     competition)
  2. Deduplicates near-identical phrasings using a generic token-signature
     (same words, different order/spacing/stopwords -> treated as one)
  3. Groups keywords into topic clusters using generic token-overlap
     similarity (no synonym dictionary — that step needs real language
     understanding, which is exactly what we hand off to Claude in Stage 3)
  4. Tags volume tier (HIGH >= 1000, MEDIUM 200-999, LOW < 200) — pure math,
     no domain knowledge needed
  5. Does NOT decide "transactional vs informational vs branded" here.
     That requires actually understanding the niche and the language of the
     query, which a hardcoded word list can never do reliably across
     different industries. Claude does that classification in Stage 3,
     using the business context you provide at that step.

Output: clustered_keywords.json

Usage:
    python filter_and_cluster.py keyword_data_output.txt
"""

import sys
import re
import json
from collections import defaultdict

INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "keyword_data_output.txt"
OUTPUT_FILE = "clustered_keywords.json"

# Only truly universal, language-level stopwords/connectors — nothing
# industry-specific lives here. Safe for any niche.
GENERIC_STOPWORDS = {
    "a", "an", "the", "in", "of", "and", "&", "to", "is", "my", "for",
    "on", "at", "with", "near", "me",
}


def parse_input(path):
    """Parses either the fixed-width .txt from keyword_research.py or a
    comma-separated .csv with the same 3 columns."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("keyword") or line.startswith("---"):
            continue
        if "," in line and "\t" not in line and not re.search(r"\s{2,}", line):
            parts = [p.strip() for p in line.split(",")]
        else:
            parts = re.split(r"\s{2,}", line.strip())
        parts = [p for p in parts if p != ""]
        if len(parts) < 3:
            continue
        keyword, searches, competition = parts[0], parts[1], parts[2]
        try:
            searches = int(str(searches).replace(",", ""))
        except ValueError:
            continue
        rows.append((keyword.strip().lower(), searches, competition.strip().upper()))
    return rows


def normalize_tokens(keyword):
    tokens = re.findall(r"[a-z0-9]+", keyword.lower())
    return [t for t in tokens if t not in GENERIC_STOPWORDS]


def volume_tier(searches):
    if searches >= 1000:
        return "HIGH"
    if searches >= 200:
        return "MEDIUM"
    return "LOW"


def dedupe_by_token_signature(rows):
    """Collapses pure word-order/stopword variants into one entry
    (e.g. 'best running shoes' vs 'running shoes best' vs 'the best
    running shoes' -> same signature). Does NOT try to merge true
    synonyms (e.g. 'sneakers' vs 'shoes') — that needs real language
    understanding, which we deliberately leave to Claude in Stage 3
    rather than faking it with a hardcoded synonym dictionary."""
    seen_signatures = {}
    for keyword, searches, competition in rows:
        tokens = normalize_tokens(keyword)
        signature = tuple(sorted(set(tokens)))
        if not signature:
            continue
        if signature not in seen_signatures or searches > seen_signatures[signature][1]:
            seen_signatures[signature] = (keyword, searches, competition, tokens)
    return list(seen_signatures.values())


def cluster_keywords(deduped):
    """Groups keywords by their most distinctive shared tokens (longest
    words = usually most specific/meaningful, a generic heuristic that
    doesn't assume any industry)."""
    clusters = defaultdict(list)

    for keyword, searches, competition, tokens in deduped:
        unique_tokens = sorted(set(tokens))
        if not unique_tokens:
            key_tokens = ["misc"]
        else:
            # pick the 2 longest/most distinctive tokens as the cluster key
            key_tokens = sorted(unique_tokens, key=len, reverse=True)[:2]
        cluster_key = " ".join(sorted(key_tokens))
        clusters[cluster_key].append(
            {"keyword": keyword, "avg_monthly_searches": searches, "competition": competition}
        )

    return clusters


def main():
    rows = parse_input(INPUT_FILE)
    if not rows:
        print(f"No rows parsed from {INPUT_FILE}. Check the file format.")
        return

    print(f"Parsed {len(rows)} raw keyword rows.")

    deduped = dedupe_by_token_signature(rows)
    print(f"After dedupe: {len(deduped)} unique-phrasing keywords.")

    clusters = cluster_keywords(deduped)
    print(f"Grouped into {len(clusters)} clusters.")

    output_clusters = []
    for cluster_key, items in clusters.items():
        items.sort(key=lambda x: x["avg_monthly_searches"], reverse=True)
        output_clusters.append({
            "cluster_topic": cluster_key,
            "keyword_count": len(items),
            "top_keyword": items[0]["keyword"],
            "top_keyword_volume": items[0]["avg_monthly_searches"],
            "volume_tier": volume_tier(items[0]["avg_monthly_searches"]),
            "sample_keywords": items[:8],
        })

    # Sort purely by volume — no niche-specific priority assumptions here.
    # Claude will re-prioritize in Stage 3 once it understands the business.
    output_clusters.sort(key=lambda c: -c["top_keyword_volume"])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "total_raw_keywords": len(rows),
            "total_deduped_keywords": len(deduped),
            "total_clusters": len(output_clusters),
            "clusters": output_clusters,
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ Done. Clustered summary saved to {OUTPUT_FILE}")
    print("Next: run analyze_with_claude.py to get ad-group targets, FAQs, and PAA content.")


if __name__ == "__main__":
    main()
