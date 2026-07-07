"""
filter_and_cluster.py  (UNIVERSAL / niche-agnostic version)
--------------------------------------------------------------
STAGE 2 of the pipeline (runs after keyword_research.py).

Now carries trend (GROWING/DECLINING/SEASONAL/STABLE) and peak_months
through from the updated keyword_research.py output.
Falls back gracefully if old-format files (without trend columns) are used.
"""

import sys
import re
import json
from collections import defaultdict

INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "keyword_data_output.txt"
OUTPUT_FILE = "clustered_keywords.json"

GENERIC_STOPWORDS = {
    "a", "an", "the", "in", "of", "and", "&", "to", "is", "my", "for",
    "on", "at", "with", "near", "me",
}


def parse_input(path):
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
        keyword    = parts[0]
        searches   = parts[1]
        competition= parts[2]
        # NEW: pick up trend + peak_months if present (cols 3 & 4)
        trend = parts[3].strip().upper() if len(parts) > 3 else "UNKNOWN"
        peak  = parts[4].strip()         if len(parts) > 4 else ""
        try:
            searches = int(str(searches).replace(",", ""))
        except ValueError:
            continue
        rows.append((keyword.strip().lower(), searches, competition.strip().upper(), trend, peak))
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
    """Collapses word-order / stopword variants. Keeps trend+peak from the
    highest-volume representative of each signature."""
    seen = {}
    for keyword, searches, competition, trend, peak in rows:
        tokens = normalize_tokens(keyword)
        sig = tuple(sorted(set(tokens)))
        if not sig:
            continue
        if sig not in seen or searches > seen[sig][1]:
            seen[sig] = (keyword, searches, competition, tokens, trend, peak)
    return list(seen.values())


def cluster_keywords(deduped):
    clusters = defaultdict(list)
    for keyword, searches, competition, tokens, trend, peak in deduped:
        unique_tokens = sorted(set(tokens))
        key_tokens = sorted(unique_tokens, key=len, reverse=True)[:2] if unique_tokens else ["misc"]
        cluster_key = " ".join(sorted(key_tokens))
        clusters[cluster_key].append({
            "keyword": keyword,
            "avg_monthly_searches": searches,
            "competition": competition,
            "trend": trend,
            "peak_months": peak,
        })
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
        top = items[0]
        output_clusters.append({
            "cluster_topic": cluster_key,
            "keyword_count": len(items),
            "top_keyword": top["keyword"],
            "top_keyword_volume": top["avg_monthly_searches"],
            "volume_tier": volume_tier(top["avg_monthly_searches"]),
            "trend": top["trend"],
            "peak_months": top["peak_months"],
            "sample_keywords": items[:8],
        })

    output_clusters.sort(key=lambda c: -c["top_keyword_volume"])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "total_raw_keywords": len(rows),
            "total_deduped_keywords": len(deduped),
            "total_clusters": len(output_clusters),
            "clusters": output_clusters,
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ Done. Clustered summary saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
