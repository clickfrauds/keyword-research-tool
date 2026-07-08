"""
score_keywords.py  (STAGE 2.5 — Python data refinery)
------------------------------------------------------
Runs AFTER keyword_research.py, BEFORE analyze_with_claude.py.

WHY THIS EXISTS:
The old pipeline threw 80 raw clusters at Claude and asked it to do
everything — that burned ~$1/run and the response was so big it got
truncated (invalid JSON, money wasted). Python is free: everything that
does NOT need language understanding happens here, so Claude only gets
a small, pre-scored shortlist and only has to do semantic grouping.

WHAT IT DOES (all deterministic, zero API cost):
  1. Dedupe word-order/stopword variants (keeps highest-volume phrasing)
  2. Classify intent:  transactional / commercial / informational / question
  3. Flag modifiers:   local intent, voice-search style, emergency/urgent
  4. Score every keyword 0-100 — Ahrefs/SEMrush-style opportunity score,
     built from THIS dataset's own percentiles (no hard KPI floors):
        volume percentile  ^0.6      (diminishing returns on huge volume)
        × intent multiplier          (transactional worth more for Ads)
        × trend multiplier           (GROWING boosted, DECLINING punished)
        × competition damping        (1 - 0.45*comp_index/100 — high comp
                                      still viable when volume justifies it)
  5. Keep the top slice for Claude: score >= 35th percentile of this run's
     own scores, capped at MAX_KEYWORDS_FOR_AI (default 150). The cutoff
     adapts to each niche's data — a weak niche keeps fewer keywords, a
     strong one keeps more.

INPUT : keyword_data_output.json (preferred) or keyword_data_output.txt
OUTPUT: scored_keywords.json

Optional env vars:
    MAX_KEYWORDS_FOR_AI   (default 150)
    TARGET_LOCATION       (improves local-intent detection, e.g. "dubai")
"""

import os
import re
import json
import math
import sys

INPUT_JSON = "keyword_data_output.json"
INPUT_TXT = "keyword_data_output.txt"
OUTPUT_FILE = "scored_keywords.json"

MAX_FOR_AI = int(os.environ.get("MAX_KEYWORDS_FOR_AI", "150"))
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip().lower()

# ── Intent vocabularies (generic — work across niches) ──────────────────────
TRANSACTIONAL = {
    "repair", "fix", "install", "installation", "replace", "replacement",
    "buy", "price", "prices", "cost", "cheap", "affordable", "hire",
    "service", "services", "book", "booking", "quote", "quotes", "order",
    "same", "emergency", "urgent", "maintenance", "cleaning", "custom",
    "made", "company", "contractor", "specialist", "expert", "professional",
}
COMMERCIAL = {
    "best", "top", "review", "reviews", "vs", "compare", "comparison",
    "companies", "contractors", "brands", "recommended", "rated",
}
INFORMATIONAL = {
    "how", "what", "why", "when", "where", "which", "guide", "diy",
    "ideas", "tips", "tutorial", "meaning", "types", "difference",
}
QUESTION_STARTERS = {
    "how", "what", "why", "when", "where", "which", "who",
    "can", "do", "does", "is", "are", "should", "will",
}
LOCAL_MARKERS = {"near", "nearby", "local", "me"}
URGENT_MARKERS = {"emergency", "urgent", "24", "247", "same", "now", "today"}

GENERIC_STOPWORDS = {
    "a", "an", "the", "in", "of", "and", "&", "to", "is", "my", "for",
    "on", "at", "with",
}

TREND_MULT = {
    "GROWING": 1.15, "STABLE": 1.0, "SEASONAL": 0.95,
    "UNKNOWN": 0.9, "DECLINING": 0.55,
}
COMP_FALLBACK_INDEX = {"LOW": 20, "MEDIUM": 50, "HIGH": 80, "UNKNOWN": 50}


def tokens_of(kw):
    return re.findall(r"[a-z0-9]+", kw.lower())


def classify(kw):
    """Returns (intent, flags). Intent: transactional/commercial/informational/question.
    Flags: local, voice, urgent."""
    toks = tokens_of(kw)
    tokset = set(toks)
    flags = []

    is_question = bool(toks) and toks[0] in QUESTION_STARTERS
    # voice-search style: real questions, or very long conversational phrases
    # that contain a question word somewhere ("carpenter who can fix my door")
    if is_question or (len(toks) >= 7 and tokset & QUESTION_STARTERS):
        flags.append("voice")

    loc_words = set(tokens_of(TARGET_LOCATION)) if TARGET_LOCATION else set()
    if (tokset & LOCAL_MARKERS and "near" in tokset) or (loc_words and tokset & loc_words):
        flags.append("local")
    if tokset & URGENT_MARKERS:
        flags.append("urgent")

    if is_question or (tokset & INFORMATIONAL and not tokset & TRANSACTIONAL):
        intent = "question" if is_question else "informational"
    elif tokset & TRANSACTIONAL:
        intent = "transactional"
    elif tokset & COMMERCIAL:
        intent = "commercial"
    else:
        # bare "wardrobe dubai" type queries: implicit commercial intent
        intent = "commercial"
    return intent, flags


INTENT_MULT = {
    "transactional": 1.25,
    "commercial": 1.10,
    "informational": 0.60,
    "question": 0.50,   # SEO/FAQ material, not paid-ads material
}


def load_rows():
    if os.path.exists(INPUT_JSON):
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fallback: parse the fixed-width txt (old runs / manual data)
    rows = []
    with open(INPUT_TXT, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("keyword") or line.startswith("-"):
                continue
            parts = re.split(r"\s{2,}", line.strip())
            if len(parts) < 3:
                continue
            try:
                vol = int(str(parts[1]).replace(",", ""))
            except ValueError:
                continue
            rows.append({
                "keyword": parts[0].strip().lower(),
                "avg_monthly_searches": vol,
                "competition": parts[2].strip().upper(),
                "trend": parts[3].strip().upper() if len(parts) > 3 else "UNKNOWN",
                "peak_months": parts[4].strip() if len(parts) > 4 else "",
                "competition_index": 0, "low_top_bid": 0, "high_top_bid": 0,
            })
    return rows


def dedupe(rows):
    """Word-order/stopword variants collapse into one entry; variants kept
    so the final Google Ads export can still include every phrasing."""
    seen = {}
    for r in rows:
        toks = [t for t in tokens_of(r["keyword"]) if t not in GENERIC_STOPWORDS]
        sig = tuple(sorted(set(toks)))
        if not sig:
            continue
        if sig in seen:
            keep = seen[sig]
            if r["avg_monthly_searches"] > keep["avg_monthly_searches"]:
                r["variants"] = keep.get("variants", []) + [keep["keyword"]]
                seen[sig] = r
            else:
                keep.setdefault("variants", []).append(r["keyword"])
        else:
            r.setdefault("variants", [])
            seen[sig] = r
    return list(seen.values())


def percentile_ranks(values):
    """Rank each value against the dataset itself → 0..1. Data-driven:
    no absolute thresholds, adapts to weak and strong niches alike."""
    import bisect
    s = sorted(values)
    n = len(s)
    if n == 0:
        return {}
    if n == 1:
        return {values[0]: 1.0}
    ranks = {}
    for v in values:
        lo = bisect.bisect_left(s, v)
        hi = bisect.bisect_right(s, v)
        ranks[v] = ((lo + hi) / 2) / n  # midpoint rank among sorted values
    return ranks


def main():
    rows = load_rows()
    if not rows:
        print(f"❌ No keyword data found ({INPUT_JSON} / {INPUT_TXT}). Run Stage 1 first.")
        sys.exit(1)

    print(f"Loaded {len(rows)} raw keywords.")
    rows = dedupe(rows)
    print(f"After variant dedupe: {len(rows)} unique keywords.")

    log_vols = [math.log1p(r["avg_monthly_searches"]) for r in rows]
    vol_rank = percentile_ranks(log_vols)
    max_log_vol = max(log_vols) or 1.0

    for r in rows:
        intent, flags = classify(r["keyword"])
        r["intent"] = intent
        r["flags"] = flags

        # Blend rank-percentile (adapts to dataset) with magnitude (so 3600
        # searches genuinely outweighs 40 searches, not just by one rank step)
        _lv = math.log1p(r["avg_monthly_searches"])
        vol_pct = 0.45 * vol_rank[_lv] + 0.55 * (_lv / max_log_vol)
        comp_idx = r.get("competition_index") or COMP_FALLBACK_INDEX.get(
            r.get("competition", "UNKNOWN"), 50)
        comp_mult = 1.0 - 0.45 * (comp_idx / 100.0)
        trend_mult = TREND_MULT.get(r.get("trend", "UNKNOWN"), 0.9)
        i_mult = INTENT_MULT[intent]
        if "local" in flags:
            i_mult *= 1.10   # local intent converts better for local businesses
        if "urgent" in flags:
            i_mult *= 1.08   # urgency = highest buying temperature

        r["score"] = round(100 * (vol_pct ** 0.6) * i_mult * trend_mult * comp_mult, 1)

    rows.sort(key=lambda r: -r["score"])

    # ── Data-driven cutoff: 35th percentile of this run's own scores ────────
    scores = sorted(r["score"] for r in rows)
    floor = scores[int(len(scores) * 0.35)] if len(scores) >= 10 else 0
    kept = [r for r in rows if r["score"] >= floor][:MAX_FOR_AI]
    kept_ids = set(id(r) for r in kept)

    for i, r in enumerate(rows, 1):
        r["id"] = i
        r["kept_for_ai"] = id(r) in kept_ids

    out = {
        "total_keywords": len(rows),
        "kept_for_ai": len(kept),
        "score_floor_used": floor,
        "keywords": [
            {k: r[k] for k in (
                "id", "keyword", "avg_monthly_searches", "competition",
                "competition_index", "low_top_bid", "high_top_bid",
                "trend", "peak_months", "intent", "flags", "score",
                "kept_for_ai", "variants")}
            for r in rows
        ],
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    from collections import Counter
    ic = Counter(r["intent"] for r in rows)
    print(f"✅ Scored {len(rows)} keywords → {OUTPUT_FILE}")
    print(f"   Kept for AI grouping: {len(kept)} (score floor {floor}, data-driven)")
    print("   Intent mix: " + ", ".join(f"{k}={v}" for k, v in ic.most_common()))
    print("   Flags: local=%d, voice=%d, urgent=%d" % (
        sum(1 for r in rows if "local" in r["flags"]),
        sum(1 for r in rows if "voice" in r["flags"]),
        sum(1 for r in rows if "urgent" in r["flags"])))


if __name__ == "__main__":
    main()
