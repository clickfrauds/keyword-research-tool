"""
generate_rsa_ads.py  (STAGE 3.8 — RSA ad copy, Editor paste-ready)
--------------------------------------------------------------------
Runs after analyze_with_claude.py. Takes keyword_strategy.json and writes,
for EVERY ad group, one complete Responsive Search Ad:

    15 headlines     <= 30 chars  (HARD-validated in Python, not trusted
     4 descriptions  <= 90 chars   to the model)
     2 display paths <= 15 chars

GOOGLE ADS POLICY GUARDRAILS (enforced by code, every violation is
auto-repaired or the item is regenerated):
    - no emojis / symbols / decorative unicode anywhere
    - no exclamation mark in ANY headline; max one per description,
      and at most one description may use one
    - no repeated punctuation (!!, ??, ...) and no gimmicky spacing
    - no ALL-CAPS words (acronyms like PPC/USA/AI are allowed)
    - no phone numbers inside ad text (policy: use call assets instead)
    - no "click here" style CTAs (disapproved editorial style)
    - no unverifiable superlatives ("#1", "best in the world")
    - all 15 headlines must be mutually distinct (Editor rejects dupes)

KEYWORD COVERAGE: at least 7 of the 15 headlines must contain a target
keyword (or a close token variant) from THIS ad group — message match is
what buys the Quality Score. Checked in code, topped up deterministically
from the keyword list itself if the model under-delivers.

LANDING PAGES: the strategy's landing_pages[] block maps every ad group
to its dedicated page slug (one page per ad group — never the homepage;
message match dies on a generic page). Final URL =
    {WEBSITE_URL}/{url_slug}/
If WEBSITE_URL isn't provided the CSV ships a clearly-marked placeholder
so nothing broken can be imported silently.

PINNING (kept minimal, per Google's own guidance):
    - the 3 strongest keyword headlines  -> pinned position 1
      (one of them always shows first = the ad always leads with
       the thing the person searched)
    - 1 CTA headline                     -> pinned position 3
    - everything else floats free for the ad-strength algorithm

Outputs:
    rsa_ads.json        full structured output
    rsa_editor.csv      Google Ads Editor import (Responsive search ad)
    rsa_ads.md          human-readable review sheet

Env vars: ANTHROPIC_API_KEY, BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION
Optional: WEBSITE_URL (e.g. https://clickadsprotector.com),
          CLAUDE_MODEL (default claude-sonnet-5), CLAUDE_EFFORT_RSA (low)
Input : keyword_strategy.json
Output: rsa_ads.json, rsa_editor.csv, rsa_ads.md
"""

import os
import re
import sys
import csv
import json
import unicodedata

# Windows local runs: cp1252 console can't print the emoji in our log lines
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
EFFORT = os.environ.get("CLAUDE_EFFORT_RSA", "low")
BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()
WEBSITE_URL = os.environ.get("WEBSITE_URL", "").strip().rstrip("/")

INPUT_JSON = "keyword_strategy.json"
OUT_JSON = "rsa_ads.json"
OUT_CSV = "rsa_editor.csv"
OUT_MD = "rsa_ads.md"

H_MAX, D_MAX, PATH_MAX = 30, 90, 15
N_HEADLINES, N_DESCRIPTIONS = 15, 4
MIN_KEYWORD_HEADLINES = 7

# Acronyms that may legitimately appear in caps
CAPS_OK = {"PPC", "USA", "UAE", "UK", "AI", "SEO", "CPC", "ROI", "RSA",
           "HVAC", "LLC", "CRM", "API", "IP", "VPN", "GPS", "TV", "AC",
           "FAQ", "B2B", "B2C", "CEO", "IT", "HR", "3D", "24", "7"}

BANNED_PHRASES = [
    "click here", "click now", "tap here",
    "#1", "no. 1", "no.1", "number one", "number 1",
    "best in the world", "world's best", "worlds best",
    "guaranteed #", "100% guaranteed",
]

PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
REPEAT_PUNCT_RE = re.compile(r"([!?.,])\1+")


def robust_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0) if m else text)


def strip_emoji_symbols(s):
    """Remove emojis and decorative symbols. Currency ($) survives; letters
    in any script survive (Arabic RSA runs stay intact)."""
    out = []
    for ch in str(s):
        cat = unicodedata.category(ch)
        if cat in ("So", "Sk", "Cs", "Co", "Cn"):   # symbols/emoji/surrogates
            continue
        if ch in "™®©•★☆✓✔✗➤→←↑↓":
            continue
        out.append(ch)
    return "".join(out)


def clean_text(s, is_headline):
    s = strip_emoji_symbols(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = REPEAT_PUNCT_RE.sub(r"\1", s)
    if is_headline:
        s = s.replace("!", "")            # policy: no exclamation in headlines
    s = s.strip(" -–—|,")
    # de-shout: ALL-CAPS words -> Title Case (acronym allowlist survives)
    def _fix(m):
        w = m.group(0)
        return w if w in CAPS_OK else w.title()
    s = re.sub(r"\b[A-Z]{2,}\b", _fix, s)
    return s.strip()


def violates_policy(s):
    low = s.lower()
    if any(p in low for p in BANNED_PHRASES):
        return "banned phrase"
    if PHONE_RE.search(s):
        return "phone number in text"
    return None


def tokens_of(s):
    return set(re.findall(r"[^\W_]+", str(s).lower(), re.UNICODE))


def headline_has_keyword(headline, kw_token_sets):
    h = tokens_of(headline)
    for kw_toks in kw_token_sets:
        core = kw_toks - {"the", "a", "an", "for", "in", "of", "and", "to", "my"}
        if not core:
            continue
        # Long keywords ("google ads management for small business", 5 core
        # tokens) can never fit near-complete inside a 30-char headline —
        # the old all-but-one rule marked every headline unmatched (the
        # "0 keyword-matched" run). Half the core tokens (min 2) is a real
        # message match at headline length.
        need = len(core) if len(core) <= 2 else max(2, (len(core) + 1) // 2)
        if len(core & h) >= need:
            return True
    return False


def title_case_keyword(kw):
    """Keyword -> clickable Title Case headline, hard-capped at 30 chars."""
    words = str(kw).strip().split()
    small = {"and", "or", "for", "in", "of", "the", "a", "an", "to", "on"}
    tc = []
    for i, w in enumerate(words):
        wu = w.upper()
        if wu in CAPS_OK:
            tc.append(wu)
        elif w.lower() in small and i not in (0, len(words) - 1):
            tc.append(w.lower())
        else:
            tc.append(w.capitalize())
    out = " ".join(tc)
    while len(out) > H_MAX and len(tc) > 1:
        tc.pop()
        out = " ".join(tc)
    return out[:H_MAX].strip()


def make_paths(slug):
    parts = [p for p in re.split(r"[^a-z0-9]+", str(slug).lower()) if p]
    p1, p2 = "", ""
    for part in parts:
        cand = (p1 + "-" + part).strip("-")
        if len(cand) <= PATH_MAX:
            p1 = cand
        elif not p2:
            p2 = part[:PATH_MAX]
        else:
            break
    return p1[:PATH_MAX], p2[:PATH_MAX]


SYSTEM = f"""You are a senior Google Ads copywriter. You write Responsive Search Ad
assets that pass Google Ads editorial policy on the first review.

BUSINESS: {BUSINESS_NAME}
WHAT IT DOES: {NICHE_DESCRIPTION}
TARGET MARKET: {TARGET_LOCATION}

ABSOLUTE RULES (violations get your output discarded):
1. Headlines: HARD LIMIT 30 characters INCLUDING SPACES. Count every character.
2. Descriptions: HARD LIMIT 90 characters including spaces.
3. NO emojis, NO symbols, NO exclamation marks in headlines. At most ONE
   exclamation mark total across all four descriptions.
4. NO all-caps words (acronyms like PPC, AI, SEO are fine).
5. NO phone numbers, NO "click here", NO unverifiable superlatives
   (never "#1", "best in the world"). "Trusted", "rated", "proven" are fine.
6. Title Case For Headlines. Sentence case for descriptions.
7. All 15 headlines must be clearly different from each other — different
   angles, not the same sentence reworded.
8. Write in the LANGUAGE of the keywords you are given.

HEADLINE MIX (exactly 15):
- 5 keyword-led: the target keyword itself, naturally phrased, clickable
  (these carry the Quality Score message match)
- 3 benefit-led: the outcome the buyer gets
- 3 call-to-action: specific action + value ("Get Your Free Audit Today")
- 2 trust/proof: specifics beat adjectives ("Setup In Under 5 Minutes")
- 2 offer/price-angle: honest, no fake discounts

DESCRIPTION MIX (exactly 4, each a complete thought with its own CTA):
1. keyword + core benefit + CTA
2. differentiator (what competitors do not offer)
3. objection-killer (risk, effort, price doubt)
4. urgency or social proof, honest only

Output ONLY valid JSON:
{{"headlines": ["...", 15 items], "descriptions": ["...", 4 items]}}"""


def ask_claude(client, group, kw_lines, retry_note=""):
    user = f"""AD GROUP: {group['name']}
THEME (the single user intent): {group.get('theme', '')}
TARGET KEYWORDS (with monthly volume):
{kw_lines}
{retry_note}
Write the RSA JSON now."""
    with client.messages.stream(
        model=MODEL,
        max_tokens=3000,
        output_config={"effort": EFFORT},
        system=[{"type": "text", "text": SYSTEM,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()
    text = "".join(b.text for b in resp.content if b.type == "text")
    u = resp.usage
    cost = u.input_tokens * 3 / 1e6 + u.output_tokens * 15 / 1e6
    print(f"   Claude RSA [{group['name']}]: {u.input_tokens} in / {u.output_tokens} out ≈ ${cost:.3f}")
    return robust_json(text)


def validate_and_repair(raw, group_keywords):
    """Clean every asset, drop invalid ones, report what survived."""
    kw_token_sets = [tokens_of(k) for k in group_keywords]

    headlines, seen = [], set()
    for h in (raw.get("headlines") or []):
        h = clean_text(h, is_headline=True)
        if not h or len(h) > H_MAX or violates_policy(h):
            continue
        key = h.lower()
        if key in seen:
            continue
        seen.add(key)
        headlines.append(h)

    # keyword coverage top-up: deterministic Title-Case keyword headlines
    def coverage():
        return sum(1 for h in headlines if headline_has_keyword(h, kw_token_sets))
    for kw in group_keywords:
        if len(headlines) >= N_HEADLINES and coverage() >= MIN_KEYWORD_HEADLINES:
            break
        cand = title_case_keyword(kw)
        if not cand or cand.lower() in seen or len(cand) > H_MAX:
            continue
        if len(headlines) < N_HEADLINES:
            headlines.append(cand)
            seen.add(cand.lower())
        elif coverage() < MIN_KEYWORD_HEADLINES:
            # Already 15 headlines but under-covered: REPLACE the last
            # non-keyword headline instead of appending — appended items
            # were silently trimmed by the [:15] cut, which is exactly how
            # a "15 headlines (0 keyword-matched)" ad shipped.
            for i in range(len(headlines) - 1, -1, -1):
                if not headline_has_keyword(headlines[i], kw_token_sets):
                    seen.discard(headlines[i].lower())
                    headlines[i] = cand
                    seen.add(cand.lower())
                    break

    descriptions, dseen, bang_used = [], set(), False
    for d in (raw.get("descriptions") or []):
        d = clean_text(d, is_headline=False)
        if d.count("!") > 1:
            d = d.replace("!", ".", d.count("!") - 1)
        if "!" in d:
            if bang_used:
                d = d.replace("!", ".")
            else:
                bang_used = True
        if not d or len(d) > D_MAX or violates_policy(d):
            continue
        if d.lower() in dseen:
            continue
        dseen.add(d.lower())
        descriptions.append(d)

    return headlines[:N_HEADLINES], descriptions[:N_DESCRIPTIONS]


def pin_plan(headlines, group_keywords):
    """Return {index: position} — 3 keyword headlines pinned to 1, one CTA to 3."""
    kw_token_sets = [tokens_of(k) for k in group_keywords]
    pins, kw_pinned = {}, 0
    for i, h in enumerate(headlines):
        if kw_pinned < 3 and headline_has_keyword(h, kw_token_sets):
            pins[i] = 1
            kw_pinned += 1
    cta_words = {"get", "start", "book", "try", "protect", "stop", "claim", "request"}
    for i, h in enumerate(headlines):
        if i in pins:
            continue
        if tokens_of(h) & cta_words:
            pins[i] = 3
            break
    return pins


def main():
    if not os.path.exists(INPUT_JSON):
        print(f"❌ {INPUT_JSON} not found — run analyze_with_claude.py first.")
        sys.exit(1)
    with open(INPUT_JSON, encoding="utf-8") as f:
        strategy = json.load(f)

    ad_groups = strategy.get("ad_groups") or []
    if not ad_groups:
        print("⚠️ No ad groups in strategy — nothing to write ads for.")
        sys.exit(0)

    # ad group -> landing page slug (one dedicated page per group; the
    # homepage is never a PPC landing page — message match dies there)
    slug_by_group = {}
    for lp in (strategy.get("landing_pages") or []):
        for g in (lp.get("ad_groups_covered") or []):
            slug_by_group[g] = lp.get("url_slug", "")

    base = WEBSITE_URL or "https://REPLACE-WITH-YOUR-DOMAIN.com"
    client = anthropic.Anthropic()
    results = []

    for group in ad_groups:
        kws = [k["keyword"] for k in (group.get("keywords") or [])]
        kws += group.get("intent_expansion_keywords") or []
        if not kws:
            continue
        top = group.get("keywords") or []
        kw_lines = "\n".join(
            f"- {k['keyword']} ({k.get('avg_monthly_searches', 0)}/mo)"
            for k in top[:15]
        )
        for extra in (group.get("intent_expansion_keywords") or [])[:8]:
            kw_lines += f"\n- {extra} (intent expansion)"

        headlines, descriptions = [], []
        for attempt in (1, 2):
            note = "" if attempt == 1 else (
                f"\nPREVIOUS ATTEMPT FAILED VALIDATION — you returned "
                f"{len(headlines)} valid headlines / {len(descriptions)} valid "
                f"descriptions. Keep every headline UNDER 30 characters and "
                f"every description UNDER 90 characters. Recount each one.")
            try:
                raw = ask_claude(client, group, kw_lines, note)
            except Exception as e:
                print(f"   ⚠️ Claude call failed for '{group['name']}': {e}")
                raw = {}
            headlines, descriptions = validate_and_repair(raw, kws)
            if len(headlines) >= N_HEADLINES and len(descriptions) >= N_DESCRIPTIONS:
                break

        # deterministic floor — the CSV must always import cleanly
        i = 0
        while len(headlines) < N_HEADLINES and i < len(kws):
            cand = title_case_keyword(kws[i])
            if cand and cand.lower() not in {h.lower() for h in headlines}:
                headlines.append(cand)
            i += 1
        while len(descriptions) < N_DESCRIPTIONS:
            fillers = [
                f"Professional {NICHE_DESCRIPTION[:40].lower().rstrip('.')} you can rely on. Get a free quote today.",
                f"Trusted by businesses across {TARGET_LOCATION[:30]}. Fast setup and clear pricing.",
                "No long-term contract. Cancel anytime. See results from the first week.",
                "Talk to a specialist today and get a plan built around your goals.",
            ]
            d = clean_text(fillers[len(descriptions) % 4], is_headline=False)[:D_MAX]
            if d.lower() in {x.lower() for x in descriptions}:
                break
            descriptions.append(d)

        slug = slug_by_group.get(group["name"], "")
        final_url = f"{base}/{slug}/" if slug else f"{base}/"
        p1, p2 = make_paths(slug or group["name"])
        pins = pin_plan(headlines, kws)

        cov = sum(1 for h in headlines
                  if headline_has_keyword(h, [tokens_of(k) for k in kws]))
        print(f"✅ {group['name']}: {len(headlines)} headlines "
              f"({cov} keyword-matched), {len(descriptions)} descriptions, "
              f"URL {final_url}")

        results.append({
            "campaign": group.get("campaign", ""),
            "ad_group": group["name"],
            "final_url": final_url,
            "path1": p1, "path2": p2,
            "headlines": headlines,
            "pins": {str(k): v for k, v in pins.items()},
            "descriptions": descriptions,
        })

    # ── rsa_ads.json ──
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"business": strategy.get("business", {}),
                   "website_url": base, "ads": results}, f,
                  indent=2, ensure_ascii=False)

    # ── Google Ads Editor CSV ──
    header = ["Campaign", "Ad Group", "Ad type"]
    for n in range(1, N_HEADLINES + 1):
        header += [f"Headline {n}", f"Headline {n} position"]
    for n in range(1, N_DESCRIPTIONS + 1):
        header += [f"Description {n}"]
    header += ["Path 1", "Path 2", "Final URL"]

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for ad in results:
            row = [ad["campaign"], ad["ad_group"], "Responsive search ad"]
            for n in range(N_HEADLINES):
                h = ad["headlines"][n] if n < len(ad["headlines"]) else ""
                pos = ad["pins"].get(str(n), "")
                row += [h, pos]
            for n in range(N_DESCRIPTIONS):
                row += [ad["descriptions"][n] if n < len(ad["descriptions"]) else ""]
            row += [ad["path1"], ad["path2"], ad["final_url"]]
            w.writerow(row)

    # ── review sheet ──
    lines = [f"# RSA Ad Copy — {BUSINESS_NAME}", ""]
    if not WEBSITE_URL:
        lines += ["> ⚠️ WEBSITE_URL was not set — Final URLs contain a "
                  "placeholder domain. Fix before importing.", ""]
    lines += ["> Google Ads me **Final URL suffix** account/campaign level par "
              "set karein: `kw={keyword}` — landing pages ki dynamic headline "
              "isi se chalti hai.", ""]
    for ad in results:
        lines.append(f"## {ad['campaign']} → {ad['ad_group']}")
        lines.append(f"Final URL: `{ad['final_url']}` | Paths: "
                     f"`/{ad['path1']}/{ad['path2']}`")
        lines.append("")
        lines.append("| # | Headline | chars | pin |")
        lines.append("|---|----------|-------|-----|")
        for i, h in enumerate(ad["headlines"]):
            pin = ad["pins"].get(str(i), "")
            lines.append(f"| {i+1} | {h} | {len(h)} | {pin} |")
        lines.append("")
        for i, d in enumerate(ad["descriptions"], 1):
            lines.append(f"- **D{i}** ({len(d)}): {d}")
        lines.append("")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n✅ Saved: {OUT_JSON}, {OUT_CSV} (Editor import), {OUT_MD}")


if __name__ == "__main__":
    main()
