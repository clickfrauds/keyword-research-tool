"""
analyze_with_claude.py  (v3 — campaigns + ad groups + landing pages + intent expansion)
----------------------------------------------------------------------------------------
STAGE 3 of the pipeline (runs after score_keywords.py).

UNIVERSAL: no industry is hardcoded anywhere. Business context comes from env
vars, so the same tool serves a carpenter, a dentist, a SaaS, an e-commerce
store — anything.

WHAT THIS STAGE PRODUCES (per run, one Claude call):
  1. CAMPAIGN STRUCTURE   — 1-3 campaigns grouping related ad groups by priority
  2. AD GROUPS            — tightly-themed, ZERO cannibalization:
                            every keyword in exactly one group (Python-enforced),
                            + negative-keyword siloing so Google can never serve
                            two of your groups against the same query
  3. INTENT EXPANSION     — per group, NEW high-buying-intent keywords the
                            Keyword Planner didn't return (cost/price/quote/
                            near-me/location variants, problem phrases)
  4. LANDING PAGE SPECS   — per campaign theme: service_name + 6 sub_services +
                            industry label + URL slug — direct inputs for the
                            Mode 1 landing engine (message match = Quality Score)
  5. FILES: keyword_strategy.json, keyword_strategy.md,
            google_ads_editor.csv (paste-ready positives) +
            google_ads_editor_negatives.csv (negatives, separate file),
            landing_pages.json (Mode 1 generator inputs)

COST DESIGN (why v1 wasted $1/run and v3 doesn't):
  Claude references keywords ONLY by numeric id — it never echoes keyword text.
  Everything deterministic (dedupe, intent classify, scoring) happened in
  Python for free in Stage 2.5. claude-sonnet-5 thinks by default and thinking
  bills as output tokens, so effort is capped (CLAUDE_EFFORT, default medium).

Required env vars:
    ANTHROPIC_API_KEY
    BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION

Optional env vars:
    CLAUDE_MODEL     (default: claude-sonnet-5)
    CLAUDE_EFFORT    (default: medium — low/medium/high)
    MAX_AD_GROUPS    (default: 10 — Claude may return FEWER; count comes
                      from the data, never padded)

Input : scored_keywords.json
Output: keyword_strategy.json, keyword_strategy.md, google_ads_editor.csv,
        google_ads_editor_negatives.csv, landing_pages.json
"""

import os
import sys
import csv
import json
import re

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

INPUT_FILE = "scored_keywords.json"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_AD_GROUPS = int(os.environ.get("MAX_AD_GROUPS", "10"))
EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")

BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()

# Content language (Jul 2026): same LANGUAGE code Stage 1 uses. When set to a
# non-English language, Claude writes all GENERATED text (group names, themes,
# landing-page names, sub_services, intent expansions, notes) in that language
# so the whole pipeline + the website builder speak one language. Blank/"en" =
# unchanged English output.
CONTENT_LANGUAGE = os.environ.get("LANGUAGE", "").strip().lower()
_LANG_NAMES = {
    "en": "English", "ar": "Arabic", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "nl": "Dutch",
    "ru": "Russian", "tr": "Turkish", "hi": "Hindi", "ur": "Urdu",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "pl": "Polish",
    "sv": "Swedish", "id": "Indonesian", "th": "Thai", "vi": "Vietnamese",
    "el": "Greek", "ro": "Romanian", "cs": "Czech", "hu": "Hungarian",
}
_LANG_ALIASES = {v.lower(): k for k, v in _LANG_NAMES.items()}
_LANG_ALIASES["no"] = ""   # legacy "no language" default → English
CONTENT_LANGUAGE = _LANG_ALIASES.get(CONTENT_LANGUAGE, CONTENT_LANGUAGE)
CONTENT_LANG_NAME = _LANG_NAMES.get(CONTENT_LANGUAGE, "")

# ── SUGGESTED BIDS ──────────────────────────────────────────────────────────
# Keyword Planner returns low/high top-of-page bids in the API ACCOUNT's
# currency (micros → units in Stage 1). BID_CURRENCY sirf label hai;
# BID_FX_RATE tab use karo jab account currency PKR na ho (e.g. account USD
# hai to BID_FX_RATE=278 se sab bids PKR mein convert ho jayengi).
BID_CURRENCY = os.environ.get("BID_CURRENCY", "PKR").strip().upper() or "PKR"
try:
    BID_FX_RATE = float(os.environ.get("BID_FX_RATE", "1") or 1)
except ValueError:
    BID_FX_RATE = 1.0
# Whole-number currencies — paisa/decimal bids make no sense in these markets
_WHOLE_UNIT_CURRENCIES = {"PKR", "INR", "JPY", "KRW", "IDR", "VND", "LKR", "BDT", "NGN"}


def _round_bid(v):
    v = v * BID_FX_RATE
    if BID_CURRENCY in _WHOLE_UNIT_CURRENCIES and v >= 5:
        return int(round(v))
    return round(v, 2)


# What a keyword is worth, on top of what it costs. The competition scale
# below says how much you must pay to appear; this says how much appearing is
# worth. They are different questions and both belong in the bid.
#   transactional  "emergency ac repair dubai" — ready to buy, pay to win it
#   commercial     "ac repair dubai"           — the normal case, no change
#   informational  research, rarely in ads at all — bid defensively
#   question       same, and usually routed to SEO instead
_INTENT_BID = {
    "transactional": 1.15,
    "commercial":    1.00,
    "informational": 0.80,
    "question":      0.75,
}

# Outlier guard. The Planner's top-of-page range is occasionally enormous for
# one keyword in a set — a broad head term, or a term some other industry bids
# hard on. Before any conversion data exists there is nothing to justify paying
# it, and one such keyword can drain a day's budget on a handful of clicks.
# Capped against the campaign's own median rather than a fixed number, so it
# travels across currencies and niches without tuning.
MAX_CPC_MULTIPLE = float(os.environ.get("MAX_CPC_MULTIPLE", "5") or 5)

# Clicks a day a new campaign should be able to buy before anyone reads a
# CPA from it. Under ten, delivery is lumpy and the data says nothing.
DAILY_CLICKS_TARGET = float(os.environ.get("DAILY_CLICKS_TARGET", "15") or 15)

# Force every ad group to one match type. Blank = the model decides per group
# under the rule in the prompt. There was no rule at all before, so the choice
# was invisible and inconsistent — one group came back exact and two phrase
# with nothing to explain why.
FORCE_MATCH_TYPE = os.environ.get("MATCH_TYPE", "").strip().lower()
if FORCE_MATCH_TYPE not in ("phrase", "exact"):
    FORCE_MATCH_TYPE = ""


def suggest_bids(low, high, comp_index=0, intent=""):
    """PRO bid formula — real Google Ads data → starting Max CPC per match type.

    Logic (top-of-page bid range = what advertisers actually pay for top slots):
      anchor = low + (high - low) * (0.35 + 0.40 * competition/100)
        → low-competition keywords anchor near 35% of the range (no need to
          overpay), cut-throat keywords anchor near 75% (must pay to play).
      then × the intent multiplier — competition sets the price of entry,
      intent sets what entry is worth.
      EXACT  = 1.00 × anchor  — tightest targeting, highest CVR → bid the most
      PHRASE = 0.85 × anchor  — some query variance → moderate discount
      BROAD  = 0.70 × anchor  — widest matching, smart-bidding explores cheap
                                queries → biggest discount
      EXACT is floored at `low` (below the first-page floor you simply don't
      serve top-of-page at all).
    Returns None when the Planner gave no bid data for this keyword.
    """
    low, high = float(low or 0), float(high or 0)
    if high <= 0 and low <= 0:
        return None
    if high <= 0:
        high = low * 2
    if low <= 0:
        low = high * 0.30
    c = min(max(float(comp_index or 0), 0), 100) / 100.0
    anchor = low + (high - low) * (0.35 + 0.40 * c)
    anchor *= _INTENT_BID.get(str(intent or "").strip().lower(), 1.00)
    return {
        "exact": max(anchor, low),
        "phrase": max(anchor * 0.85, low * 0.90),
        "broad": anchor * 0.70,
    }

# ── EXISTING ACCOUNT MODE (incremental) ─────────────────────────────────────
# Jab client ka account pehle se chal raha ho aur sirf naya ad group add karna
# ho: existing campaign ka naam + existing ad groups ki list de do. Tool phir:
#   - naye groups ko USI campaign mein rakhta hai (nayi campaign invent nahi)
#   - naye groups ko existing groups ke against negatives deta hai
#   - existing groups ke liye bhi negatives suggest karta hai (2-way siloing)
#   - MAX_AD_GROUPS ko chhota rakho (e.g. 1-2) taake over-splitting na ho
EXISTING_CAMPAIGN = os.environ.get("EXISTING_CAMPAIGN", "").strip()
EXISTING_AD_GROUPS = [g.strip() for g in os.environ.get("EXISTING_AD_GROUPS", "").split(",") if g.strip()]

# FIXED PAGES MODE — crawl_landing_pages.py has already read this client's
# live pages. The page set is then a fact, not something to design: one ad
# group per page, no more, and the URLs are the ones that already serve.
# This is what makes "Destination not working" impossible on this path —
# no slug is invented, so no ad can point at a page that was never built.
FIXED_PAGES = []
if os.path.exists("landing_pages_source.json"):
    try:
        with open("landing_pages_source.json", encoding="utf-8") as _f:
            FIXED_PAGES = (json.load(_f).get("pages") or [])
    except Exception as _e:
        print(f"⚠️ landing_pages_source.json unreadable ({str(_e)[:60]}) — "
              "continuing in normal mode.")

# Single-campaign mode (user request, Jul 2026): Ads Editor imports of a
# multi-campaign file are easy to get wrong (the second campaign's rows get
# skipped when a paste range starts mid-file), and small accounts usually
# want ONE campaign anyway for budget control. "true"/"1"/"yes" collapses
# everything into the first campaign Claude names; any other non-empty value
# is used as the campaign name itself. Downstream stages (negatives, RSA,
# audiences, locations) read keyword_strategy.json, so the override
# propagates everywhere automatically.
SINGLE_CAMPAIGN = os.environ.get("SINGLE_CAMPAIGN", "").strip()
MAX_KEYWORDS_PER_GROUP = int(os.environ.get("MAX_KEYWORDS_PER_GROUP", "40"))


# ══════════════════════════════════════════════════════════════════════════
# Robust JSON parsing (4 repair passes — battle-tested in the website builder)
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

SYSTEM_PROMPT = f"""You are a senior Google Ads account strategist AND landing
page architect. You receive pre-scored keyword data (real Google Ads Keyword
Planner numbers — already deduped, intent-classified and opportunity-scored).
You work for ANY business type — never assume an industry beyond the given
business context.

Your job has FOUR outputs (one JSON object, nothing else, no markdown fences):

{{
  "campaigns": [
    {{"name": "short campaign name", "priority": "high|medium|low"}}
  ],
  "ad_groups": [
    {{
      "name": "short ad group name",
      "campaign": "exact campaign name from above",
      "theme": "one sentence: the single user intent this group targets",
      "match_type": "phrase|exact",
      "match_type_reason": "one short clause: why this group, not the default",
      "priority": "high|medium|low",
      "bid_multiplier": 1.0,
      "keyword_ids": [1, 2, 3],
      "negative_keywords": ["term", "term"],
      "intent_expansion_keywords": ["new keyword", "new keyword"]
    }}
  ],
  "landing_pages": [
    {{
      "page_name": "short page name",
      "url_slug": "kebab-case-slug",
      "service_name": "the main service this page sells (title case)",
      "industry": "2-4 word industry label for an AI page generator",
      "sub_services": ["Six", "Title Case", "Sub Service", "Names", "Exactly", "Six"],
      "ad_groups_covered": ["ad group name", "ad group name"]
    }}
  ],
  "excluded_ids": [4, 5],
  "notes": "2-3 sentences max: overall strategy rationale"
}}

HARD RULES:
1. CAMPAIGNS: 1-3. Group related ad groups by service line and priority
   (e.g. core money-makers vs adjacent/low-volume services). Every ad group
   belongs to exactly one campaign.
2. AD GROUPS: between 1 and {MAX_AD_GROUPS}. The COUNT MUST COME FROM THE
   DATA: one group per genuinely distinct commercial theme visible in the
   keywords. If the data only supports 4 themes, return 4. NEVER pad with
   thin groups, NEVER split one theme into two.
3. MATCH TYPE — DEFAULT IS PHRASE. Justify any exception.
   This campaign launches on Manual CPC with no conversion history, so its
   first job is to find out what people actually type. Phrase does that and
   the hourly negative-guard script removes what does not belong. Exact locks
   the campaign into the keyword list you guessed today and it never
   discovers the long tail that converts.
   Use "exact" for a group ONLY when BOTH are true:
     a) its keywords carry high top-of-page bids relative to the others in
        this account — an exploratory click there is genuinely expensive; and
     b) the theme is one unambiguous purchase intent, so close variants add
        no reach worth paying for.
   Never choose exact merely because a group feels "more commercial". Put
   the reason in match_type_reason either way — "default: discovery on a new
   campaign" is a perfectly good reason for phrase.

4. ZERO CANNIBALIZATION:
   - Every keyword id appears in AT MOST one group.
   - Themes must be mutually exclusive — a real search query should match
     exactly one group, never two.
   - negative_keywords for each group = the distinctive core terms of the
     OTHER groups (negative-keyword siloing). Be thorough — this is what
     stops Google serving two of your groups against one query.
5. INTENT EXPANSION (your unique value): for each ad group, add 5-12 NEW
   keywords that real buyers of THIS business type in THIS location search
   but which are missing from the data. Use: buying modifiers (cost, price,
   quote, installation, best, hire), urgency, the target location appended
   naturally, and problem-phrases in the searcher's own words. Rules:
   - Must be NEW: never duplicate (or trivially reorder) any provided
     keyword or another expansion, in this group or any other group.
   - Must belong to THIS group's theme only (respect the siloing).
   - Lowercase, realistic search queries — no marketing copy.
6. LANDING PAGES: 3-6 pages. Each page covers 1+ ad groups whose themes fit
   ONE selling proposition (message match = Quality Score). Fields feed an
   AI landing-page generator directly:
   - service_name: what the page sells, title case.
   - sub_services: EXACTLY 6 title-case service names (become page sections).
   - industry: short label steering the generator's design/copy tone.
   - url_slug: kebab-case, keyword-rich, no location suffix.
   Every ad group must be covered by exactly one landing page.
7. EXCLUDE (excluded_ids): informational/question queries (SEO material,
   not ads), competitor brand names, DIY-intent, and anything irrelevant
   to this business.
8. Reference provided keywords ONLY by numeric id. Never echo their text.
9. Use volumes/competition/scores to set priorities: the campaign and group
   holding the best opportunity keywords is "high".
8b. BID_MULTIPLIER (per ad group, 0.8-1.3): a Python formula computes each
   keyword's starting Max CPC from its real Google cpc_range + competition.
   Your multiplier scales the whole group based on STRATEGY the formula
   can't see: money-maker/high-priority groups with strong buying intent
   → 1.1-1.3; experimental, adjacent-service or low-priority groups
   → 0.8-0.95; everything normal → 1.0.
10. SMALL DATASETS: if the keyword set is small or low-volume (niche service,
   max volume under a few hundred), that is normal — do NOT split it to look
   thorough. One tight group with strong intent expansions beats three thin
   groups. Low absolute volume is fine; relative opportunity is what matters.
"""

if EXISTING_CAMPAIGN or EXISTING_AD_GROUPS:
    SYSTEM_PROMPT += f"""
EXISTING ACCOUNT MODE — this client's Google Ads account is ALREADY RUNNING:
- Existing campaign: "{EXISTING_CAMPAIGN or '(unnamed — use a sensible name)'}"
- Existing ad groups already live: {json.dumps(EXISTING_AD_GROUPS)}

Extra rules that OVERRIDE the ones above:
A. Do NOT invent new campaigns. Return exactly one campaign named
   "{EXISTING_CAMPAIGN}" and put every new ad group in it.
B. Your new ad group themes must NOT overlap any existing ad group's theme.
   If a provided keyword actually belongs to an existing group's theme,
   EXCLUDE it (excluded_ids) — do not build a competing group around it.
C. Each new group's negative_keywords must include the distinctive core terms
   of the EXISTING groups (so the new group never steals their traffic).
D. Also return this extra top-level key:
   "negatives_for_existing_groups": {{"<existing group name>": ["term", ...]}}
   = the distinctive terms of your NEW groups, to be added as negatives to
   each existing group so they cannot cannibalize the new group either.
   Only include existing groups that actually need protection.
E. Landing pages: only for the NEW themes (1 page per new theme is typical).
"""

if FIXED_PAGES:
    _fp_lines = []
    for _p in FIXED_PAGES:
        _fp_lines.append(
            f'- AD GROUP "{_p["ad_group"]}" -> {_p["url"]}\n'
            f'    sells: {_p.get("service_name","")}\n'
            f'    page says: {_p.get("h1","")} | '
            + " | ".join((_p.get("h2") or [])[:6])
        )
    SYSTEM_PROMPT += f"""
EXISTING LANDING PAGES MODE — this client's pages are ALREADY LIVE:

{chr(10).join(_fp_lines)}

Extra rules that OVERRIDE the ones above:
A. AD GROUPS: return EXACTLY {len(FIXED_PAGES)} of them, one per page, named
   EXACTLY as listed. Not one more, not one fewer, and do not rename them.
   The page set is a fact here, not a design decision — an ad group with no
   page has nowhere to send its clicks.
B. Sort every keyword into the group whose page actually sells that thing.
   Judge by what the page says above, not by the keyword alone.
C. A keyword that no page sells goes in excluded_ids. Do NOT stretch a group
   to cover it — a click landing on a page that does not sell what was
   searched is a wasted click and a bad Landing Page Experience score.
D. Also return this extra top-level key:
   "new_page_opportunities": [
     {{"suggested_page": "what it would sell", "keyword_ids": [1, 2],
       "monthly_volume": 1234, "why": "one line"}}
   ]
   = the excluded keywords that carry real volume and would justify a NEW
   page. This is the client's growth list; do not silently discard them.
E. LANDING PAGES: skip the landing_pages array entirely. Return it empty —
   the pages already exist and their URLs must not be regenerated.
"""

if CONTENT_LANG_NAME and CONTENT_LANGUAGE != "en":
    SYSTEM_PROMPT += f"""
OUTPUT LANGUAGE — this account targets a {CONTENT_LANG_NAME}-speaking market:
- The keyword data below is ALREADY in {CONTENT_LANG_NAME}. Keep every provided
  keyword exactly as given — NEVER translate or alter a provided keyword.
- Write ALL text YOU generate in {CONTENT_LANG_NAME}: campaign names, ad group
  names, `theme` sentences, `intent_expansion_keywords` (real {CONTENT_LANG_NAME}
  search queries), `negative_keywords`, landing-page `page_name`/`service_name`/
  `sub_services`/`industry`, and `notes`.
- KEEP IN ENGLISH ASCII (do NOT translate): every JSON KEY, and each landing
  page's `url_slug` — slugs stay clean kebab-case English for tidy URLs even
  though the page sells in {CONTENT_LANG_NAME}.
"""


_SCRIPT_RANGES = [
    ("Arabic",     r"[؀-ۿݐ-ݿ]"),
    ("Devanagari", r"[ऀ-ॿ]"),
    ("Cyrillic",   r"[Ѐ-ӿ]"),
    ("CJK",        r"[一-鿿]"),
    ("Latin",      r"[A-Za-z]"),
]


_AR_TRANSLIT = {
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ب": "b", "ت": "t", "ث": "th",
    "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z",
    "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a",
    "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "و": "w", "ي": "y", "ى": "a", "ة": "a", "ء": "", "ؤ": "u",
    "ئ": "i", "َ": "", "ُ": "", "ِ": "", "ّ": "", "ْ": "", "ً": "", "ٌ": "", "ٍ": "",
}


def slugify_any(text, fallback=""):
    """URL slug that survives ANY script. The old one was
    `re.sub(r"[^a-z0-9-]", "", ...)`, which turns "إصلاح الغسالات" into "-" —
    a garbage slug that then became the RSA Final URL and every sitelink URL
    for that ad group. Arabic is transliterated so the slug still reads as the
    service; anything else falls back to the caller's English label."""
    s = str(text or "").strip().lower()
    if re.search(r"[؀-ۿ]", s):
        s = "".join(_AR_TRANSLIT.get(ch, ch) for ch in s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if not s:
        s = re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", str(fallback or "").strip().lower()))
        s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:60]


def keyword_script(text):
    """Which script is this keyword written in? Non-Latin wins when mixed —
    "تصليح غسالات dubai" is an Arabic query with a Latin place name in it."""
    t = str(text or "")
    for name, pattern in _SCRIPT_RANGES:
        if name != "Latin" and re.search(pattern, t):
            return name
    return "Latin" if re.search(r"[A-Za-z]", t) else "Other"


def script_breakdown(keywords):
    counts = {}
    for k in keywords:
        s = keyword_script(k.get("keyword", ""))
        counts[s] = counts.get(s, 0) + 1
    return counts


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
    # MIXED-SCRIPT ACCOUNTS (the Arabic+English case): with no instruction the
    # model quietly builds groups for the dominant script and leaves the rest in
    # `unassigned` — where nothing downstream picks them up, so those keywords
    # never reach the campaign. Name the split and demand coverage.
    scripts = script_breakdown(kept)
    mixed_block = ""
    if len([s for s, n in scripts.items() if n]) > 1 and "Other" not in scripts:
        parts = ", ".join(f"{n} {s}" for s, n in
                          sorted(scripts.items(), key=lambda x: -x[1]))
        mixed_block = (
            f"\n⚠️ MIXED-LANGUAGE ACCOUNT — the keyword list below is {parts}.\n"
            "- EVERY script must end up in ad groups. Do NOT drop, translate or\n"
            "  exclude a keyword because it is not in the majority language.\n"
            "- Keep scripts in SEPARATE ad groups (one language per ad group) —\n"
            "  ad copy is written per ad group and cannot be bilingual.\n"
            "- Name each non-majority group so the language is obvious, and write\n"
            "  its `theme`, `intent_expansion_keywords` and `negative_keywords` in\n"
            "  THAT group's language.\n"
        )

    header = (
        f"BUSINESS: {BUSINESS_NAME or '(not provided)'}\n"
        f"NICHE: {NICHE_DESCRIPTION or '(infer from keywords)'}\n"
        f"TARGET LOCATION: {TARGET_LOCATION or '(not local)'}\n"
        f"{mixed_block}\n"
        f"KEYWORDS ({len(kept)} rows — format: id|keyword|volume|competition_index"
        f"|cpc_range|trend|intent|flags|opportunity_score):\n"
    )
    return header + "\n".join(lines), kept


# ══════════════════════════════════════════════════════════════════════════
# Post-validation — Python enforces what the prompt requests
# ══════════════════════════════════════════════════════════════════════════

def _norm_sig(kw):
    return tuple(sorted(set(re.findall(r"[^\W_]+", str(kw).lower(), re.UNICODE))))


def _stem(t):
    """Light morphological stem so singular/plural/verb-form variants of the
    SAME theme word can never end up as that group's own negative (Jul 2026:
    the shower-partition group shipped with negative "partitions" while its
    keywords said "partition" — every plural query self-blocked; same for
    handrail/handrails, install/installers/installation). English-suffix only;
    non-Latin tokens pass through untouched."""
    if len(t) <= 3:
        return t
    # pass 1: plurals (partitions→partition, cubicles→cubicle, companies→company)
    if t.endswith("ies") and len(t) >= 6:
        t = t[:-3] + "y"
    elif (t.endswith(("ses", "xes", "zes", "ches", "shes")) and len(t) >= 6):
        t = t[:-2]          # true -es plurals: glasses→glass, boxes→box
    elif t.endswith("s") and not t.endswith("ss") and len(t) >= 5:
        t = t[:-1]          # cubicles→cubicle, doors→door
    # pass 2: derivational forms → shared root (installation/installer/
    # installing → install). Over-merging is SAFE here: a dropped negative
    # costs nothing, a self-blocking negative kills the group's serving.
    for suf in ("ation", "ing", "er"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: len(t) - len(suf)]
    return t


def validate_strategy(raw, kept):
    by_id = {k["id"]: k for k in kept}
    provided_sigs = {_norm_sig(k["keyword"]) for k in kept}
    for k in kept:
        for v in k.get("variants", []):
            provided_sigs.add(_norm_sig(v))

    if EXISTING_CAMPAIGN:
        # Incremental mode: sab kuch client ki existing campaign mein hi jata hai
        campaigns = [{"name": EXISTING_CAMPAIGN, "priority": "high"}]
    else:
        campaigns = []
        seen_camp = set()
        for c in raw.get("campaigns", [])[:3]:
            name = str(c.get("name", "")).strip()[:60]
            if name and name.lower() not in seen_camp:
                campaigns.append({"name": name, "priority": c.get("priority", "medium")})
                seen_camp.add(name.lower())
        if not campaigns:
            campaigns = [{"name": f"{BUSINESS_NAME or 'Main'} Campaign", "priority": "high"}]
    default_campaign = campaigns[0]["name"]
    camp_names = {c["name"] for c in campaigns}

    # Two-way siloing: negatives Claude suggests for the EXISTING ad groups
    negatives_for_existing = {}
    if EXISTING_AD_GROUPS:
        raw_nfe = raw.get("negatives_for_existing_groups", {}) or {}
        existing_lookup = {g.lower(): g for g in EXISTING_AD_GROUPS}
        for gname, terms in raw_nfe.items() if isinstance(raw_nfe, dict) else []:
            real = existing_lookup.get(str(gname).strip().lower())
            clean = [str(t).strip().lower() for t in (terms or []) if str(t).strip()]
            if real and clean:
                negatives_for_existing[real] = clean

    seen_ids = set()
    seen_expansion_sigs = set()
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
        # Cap keywords per ad group (user rule, Jul 2026): a tight theme
        # doesn't need more than ~40 keywords — beyond that it's usually
        # theme drift. Keep the highest-scored; the rest stay available to
        # SEO/report outputs untouched.
        if len(kws) > MAX_KEYWORDS_PER_GROUP:
            kws = sorted(kws, key=lambda k: -k.get("score", 0))[:MAX_KEYWORDS_PER_GROUP]
            ids = [k["id"] for k in kws]

        # Expansion keywords: must be genuinely NEW and unique across groups
        expansions = []
        for e in g.get("intent_expansion_keywords", []):
            e = str(e).strip().lower()
            sig = _norm_sig(e)
            if not e or not sig or sig in provided_sigs or sig in seen_expansion_sigs:
                continue
            seen_expansion_sigs.add(sig)
            expansions.append(e)

        camp = str(g.get("campaign", "")).strip()
        if camp not in camp_names:
            camp = default_campaign

        # 🛡️ SELF-BLOCK GUARD: a negative that matches this group's OWN
        # keywords/variants/expansions would stop the group from serving at
        # all. Cross-group negatives are the point (siloing) — only self-hits
        # get dropped. The prompt asks Claude not to do this, but the CSV
        # goes straight into Google Ads Editor, so Python enforces it.
        own_texts = ([k["keyword"] for k in kws]
                     + [v for k in kws for v in k.get("variants", [])]
                     + expansions)
        own_tokens = {t for txt in own_texts
                      for t in re.findall(r"[^\W_]+", str(txt).lower(), re.UNICODE)}
        # STEM-level self check (Jul 2026): "partitions" vs own "partition",
        # "handrails" vs own "handrail", "installers" vs own "installation" —
        # token-exact comparison shipped negatives that blocked the group's
        # own plural/verb-form queries.
        own_stems = {_stem(t) for t in own_tokens}
        own_blob = " | ".join(str(t).lower() for t in own_texts)
        negatives, dropped_negs = [], []
        for n in g.get("negative_keywords", []):
            n = str(n).strip().lower()
            if not n:
                continue
            n_toks = re.findall(r"[^\W_]+", n, re.UNICODE)
            if ((len(n_toks) == 1 and n_toks and _stem(n_toks[0]) in own_stems)
                    or (len(n_toks) > 1
                        and (re.search(r"(^|[\s|])" + re.escape(n) + r"([\s|]|$)", own_blob)
                             or all(_stem(t) in own_stems for t in n_toks)))):
                dropped_negs.append(n)
                continue
            negatives.append(n)
        if dropped_negs:
            print(f"   🛡️ '{str(g.get('name', '')).strip()[:40]}': dropped "
                  f"{len(dropped_negs)} self-blocking negatives: {dropped_negs[:6]}"
                  f"{'...' if len(dropped_negs) > 6 else ''}")

        # Claude's strategic bid multiplier for this group (clamped for safety)
        try:
            bid_mult = float(g.get("bid_multiplier", 1.0) or 1.0)
        except (TypeError, ValueError):
            bid_mult = 1.0
        bid_mult = min(max(bid_mult, 0.7), 1.5)
        group_match = FORCE_MATCH_TYPE or g.get("match_type", "phrase")
        if group_match not in ("phrase", "exact"):
            group_match = "phrase"

        def _kw_entry(k):
            entry = {
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
            bids = suggest_bids(k.get("low_top_bid", 0), k.get("high_top_bid", 0),
                                k.get("competition_index", 0), k.get("intent", ""))
            if bids:
                entry["suggested_bid_exact"] = _round_bid(bids["exact"] * bid_mult)
                entry["suggested_bid_phrase"] = _round_bid(bids["phrase"] * bid_mult)
                entry["suggested_bid_broad"] = _round_bid(bids["broad"] * bid_mult)
                entry["suggested_bid"] = entry.get(
                    f"suggested_bid_{group_match}", entry["suggested_bid_phrase"])
                entry["bid_currency"] = BID_CURRENCY
            return entry

        # LANGUAGE OF THIS AD GROUP, from its own keywords. Everything
        # downstream needs it: the RSA copy must be in it, the landing page
        # lives under /{lang}/, and the campaign must target it. Detecting it
        # once here beats three stages re-guessing from the group name.
        _g_script = script_breakdown([{"keyword": k["keyword"]} for k in kws] or
                                     [{"keyword": g.get("name", "")}])
        _g_lang = {"Arabic": "ar", "Devanagari": "hi", "Cyrillic": "ru",
                   "CJK": "zh"}.get(max(_g_script, key=_g_script.get) if _g_script else "Latin", "en")

        groups.append({
            "name": str(g.get("name", "Ad Group")).strip()[:60],
            "campaign": camp,
            "language": _g_lang,
            "theme": str(g.get("theme", "")).strip(),
            "match_type": group_match,
            # Kept so the report can show WHY, and so a run can be argued with.
            "match_type_reason": ("forced by MATCH_TYPE" if FORCE_MATCH_TYPE
                                  else str(g.get("match_type_reason", "")).strip()[:120]),
            "priority": g.get("priority", "medium"),
            "bid_multiplier": bid_mult,
            "bid_currency": BID_CURRENCY,
            "negative_keywords": negatives,
            "intent_expansion_keywords": expansions,
            "keywords": [_kw_entry(k) for k in kws],
            "total_volume": sum(k["avg_monthly_searches"] for k in kws),
            "avg_score": round(sum(k.get("score", 0) for k in kws) / len(kws), 1),
        })

    # 🧱 DETERMINISTIC CROSS-SILO NEGATIVES (Python-computed, not prompt-trust):
    # a token that appears in exactly ONE group's keywords/expansions is that
    # group's distinctive theme term — every OTHER group gets it as a negative,
    # so a real query can only ever match one group. Claude's negatives stay;
    # this fills whatever the prompt missed. Intent modifiers (emergency/price/
    # book...) and the target location are never used — they belong to every
    # group, blocking them would misroute genuine queries.
    _MODIFIERS = {"the", "and", "for", "with", "near", "nearby", "me", "in", "of",
                  "a", "an", "to", "best", "top", "cheap", "affordable", "price",
                  "prices", "cost", "quote", "quotes", "emergency", "urgent",
                  "hour", "same", "day", "now", "today", "book", "booking",
                  "hire", "contact", "number", "call", "whatsapp", "service",
                  "services", "company", "professional", "expert"}
    _loc_toks = set(re.findall(r"[^\W_]+", TARGET_LOCATION.lower(), re.UNICODE))

    def _group_tokens(g):
        texts = ([k["keyword"] for k in g["keywords"]]
                 + [v for k in g["keywords"] for v in k.get("variants", [])]
                 + g["intent_expansion_keywords"])
        return {t for txt in texts
                for t in re.findall(r"[^\W_]+", str(txt).lower(), re.UNICODE)
                if len(t) >= 3 and t not in _MODIFIERS and t not in _loc_toks}

    if len(groups) > 1:
        tok_sets = {g["name"]: _group_tokens(g) for g in groups}
        # Ownership at STEM level (Jul 2026): "partition" (shower group) and
        # "partitions" (office group) are the same theme word — token-exact
        # ownership called "partitions" distinctive-to-office and handed it to
        # the shower group as a negative, blocking its own plural queries.
        stem_sets = {name: {_stem(t) for t in toks} for name, toks in tok_sets.items()}
        owners = {}
        for _name, _toks in tok_sets.items():
            for _t in _toks:
                owners.setdefault(_stem(_t), set()).add(_name)
        distinctive = {name: {t for t in toks if owners[_stem(t)] == {name}}
                       for name, toks in tok_sets.items()}
        for g in groups:
            auto = sorted(
                t for t in set().union(
                    *(distinctive[o] for o in tok_sets if o != g["name"]))
                - set(g["negative_keywords"])
                if _stem(t) not in stem_sets[g["name"]])
            if auto:
                g["negative_keywords"] = g["negative_keywords"] + auto
                g["auto_silo_negatives"] = auto
        _n_auto = sum(len(g.get("auto_silo_negatives", [])) for g in groups)
        if _n_auto:
            print(f"   🧱 Cross-silo guard: {_n_auto} distinctive-token negatives "
                  f"auto-added across {len(groups)} groups")

    group_names = {g["name"] for g in groups}

    # Landing pages: validate coverage, force exactly 6 sub_services
    pages = []
    covered = set()
    _slug_seen = set()
    for _pi, p in enumerate(raw.get("landing_pages", [])[:6], 1):
        ag = [a for a in p.get("ad_groups_covered", []) if a in group_names]
        subs = [str(s).strip() for s in p.get("sub_services", []) if str(s).strip()][:6]
        if not p.get("service_name") or not subs:
            continue
        covered.update(ag)
        # slug: model value → service name → page name → numbered fallback, and
        # never a duplicate (two pages on one URL would overwrite each other)
        _slug = (slugify_any(p.get("url_slug", ""), p.get("service_name", ""))
                 or slugify_any(p.get("service_name", ""), p.get("page_name", ""))
                 or f"service-{_pi}")
        if _slug in _slug_seen:
            _slug = f"{_slug}-{_pi}"
        _slug_seen.add(_slug)
        # The page inherits the language of the ad groups it serves — Mode 1 in
        # the website builder reads this to publish it under /{lang}/ and to
        # write it in the right language instead of the run default.
        _p_langs = {g["language"] for g in groups if g["name"] in ag} or {"en"}
        pages.append({
            "page_name": str(p.get("page_name", p.get("service_name", ""))).strip()[:80],
            "url_slug": _slug,
            "language": sorted(_p_langs)[0] if len(_p_langs) == 1 else "mixed",
            "service_name": str(p.get("service_name", "")).strip(),
            "industry": str(p.get("industry", NICHE_DESCRIPTION[:40])).strip(),
            "sub_services": subs,
            "ad_groups_covered": ag,
        })
    # FIXED PAGES MODE: the pages are already live, so they replace whatever
    # the model returned rather than being described by it. Rule E asks for an
    # empty landing_pages array, but this does not depend on the model obeying.
    #
    # final_url is the point. Everything downstream builds its URL as
    # WEBSITE_URL + "/" + url_slug + "/", which is exactly the invention that
    # produced ads pointing at pages nobody had built yet. Here the URL is one
    # that already answered a request during the crawl, so it is carried
    # through untouched and nothing is allowed to rebuild it.
    if FIXED_PAGES:
        pages = []
        covered = set()
        for _p in FIXED_PAGES:
            _has_group = _p["ad_group"] in group_names
            _ag = [_p["ad_group"]] if _has_group else []
            covered.update(_ag)
            pages.append({
                "page_name": (_p.get("service_name") or _p["ad_group"])[:80],
                "url_slug": _p.get("url_slug", ""),
                "final_url": _p["final_url"],
                "language": CONTENT_LANGUAGE or "en",
                "service_name": _p.get("service_name", ""),
                "industry": NICHE_DESCRIPTION[:40],
                "sub_services": _p.get("sub_services", []),
                "ad_groups_covered": _ag,
                "anchors": _p.get("anchors", []),
                "sitelink_mode": _p.get("sitelink_mode", "cross_page"),
                "sitelink_targets": _p.get("sitelink_targets", []),
                "sitelink_labels": _p.get("sitelink_labels", []),
                "verdict": _p.get("verdict", "strong"),
                "h1": _p.get("h1", ""),
                "h2": _p.get("h2", []),
                "h3": _p.get("h3", []),
            })
        _orphan_pages = [p["ad_group"] for p in FIXED_PAGES
                         if p["ad_group"] not in group_names]
        if _orphan_pages:
            # The model was told to return exactly these ad group names. When
            # one is missing that page has no keywords, so it would sit in the
            # campaign with nothing to trigger it.
            print(f"   ⚠️ {len(_orphan_pages)} page(s) received no ad group: "
                  + ", ".join(_orphan_pages[:5]))
        print(f"   📄 Fixed pages: {len(pages)} live URL(s), "
              f"{len(covered)} matched to an ad group")

    uncovered_groups = sorted(group_names - covered)

    excluded = set()
    for i in raw.get("excluded_ids", []):
        try:
            excluded.add(int(i))
        except (TypeError, ValueError):
            pass
    unassigned = [by_id[i]["keyword"] for i in by_id
                  if i not in seen_ids and i not in excluded]

    # SCRIPT-COVERAGE GUARD: unassigned keywords are reported and then dropped —
    # nothing downstream (CSV, master CSV, API push) ever picks them up. When a
    # whole script goes unassigned that is not a judgement call, it is the
    # mixed-language failure: the Arabic half of an Arabic+English account
    # silently never reaches the campaign. Make it impossible to miss.
    _grouped_scripts = script_breakdown(
        [{"keyword": k} for g in groups for k in
         ([kw["keyword"] for kw in g.get("keywords", [])] + g.get("intent_expansion_keywords", []))])
    _input_scripts = script_breakdown([{"keyword": by_id[i]["keyword"]} for i in by_id])
    for _s, _n in sorted(_input_scripts.items(), key=lambda x: -x[1]):
        if _s in ("Other",) or _n < 3:
            continue
        if _grouped_scripts.get(_s, 0) == 0:
            _lost = [by_id[i]["keyword"] for i in by_id
                     if keyword_script(by_id[i]["keyword"]) == _s and i not in seen_ids]
            print(f"❗ {_s} KEYWORDS DROPPED: {_n} {_s}-script keywords were in the data "
                  f"but ZERO reached an ad group — they will NOT be in the campaign.")
            print(f"   examples: {', '.join(_lost[:5])}")
            print(f"   fix: re-run this stage, or set LANGUAGE to the majority market and "
                  f"run the minority language as its own campaign.")
        elif _grouped_scripts.get(_s, 0) < _n * 0.3:
            print(f"⚠️ Only {_grouped_scripts.get(_s, 0)} of {_n} {_s}-script keywords "
                  f"landed in ad groups — check `unassigned_keywords` in the strategy JSON.")

    if (SINGLE_CAMPAIGN and not EXISTING_CAMPAIGN
            and SINGLE_CAMPAIGN.lower() not in ("false", "0", "no", "off")):
        single = (campaigns[0]["name"]
                  if SINGLE_CAMPAIGN.lower() in ("true", "1", "yes")
                  else SINGLE_CAMPAIGN[:60])
        campaigns = [{"name": single, "priority": "high"}]
        for g in groups:
            g["campaign"] = single
        print(f"🎯 Single-campaign mode: all {len(groups)} ad groups under '{single}'")

    _normalize_bids(groups)
    return campaigns, groups, pages, uncovered_groups, sorted(excluded), unassigned, negatives_for_existing


def _normalize_bids(groups):
    """Two real bugs the Keyword Planner data causes (seen in the SEOBlogy UAE
    push, Jul 2026):
      1. LOW-VOLUME groups get NO top-of-page bid from the Planner → suggest_bids
         returns None → the ad group's median bid is empty → Google lands it at
         the account minimum (~PKR 1) → BELOW first-page bid → ZERO impressions.
      2. One outlier keyword ("google display advertising") comes back with a
         huge Planner bid → an ad-group default like PKR 86,129 → budget-burn.
    Fix: compute the CAMPAIGN-WIDE median from the groups that DO have bids;
    backfill every no-bid keyword with it (so every group can serve), and CAP
    any bid above a sane ceiling. Currency-agnostic — works on whatever units
    suggest_bids already produced. No-op if nothing had a bid."""
    bid_keys = ("suggested_bid", "suggested_bid_exact",
                "suggested_bid_phrase", "suggested_bid_broad")
    all_bids = sorted(k["suggested_bid"] for g in groups for k in g["keywords"]
                      if k.get("suggested_bid"))
    if not all_bids:
        print("   ⚠️ Bid guard: Planner returned NO bid data for ANY keyword — "
              "ad groups will need manual Max CPC in the account.")
        return
    n = len(all_bids)
    g_med = all_bids[n // 2]
    # Ceiling from the MEDIAN (robust to the outlier itself — a p90/max-based
    # cap fails because the outlier IS the max). 5x median allows genuinely
    # competitive keywords through while taming a 15x freak bid. Lower it with
    # MAX_CPC_MULTIPLE on a niche where one head term skews everything.
    ceiling = round(g_med * MAX_CPC_MULTIPLE, 2)
    n_fill = n_cap = 0
    for g in groups:
        for k in g["keywords"]:
            b = k.get("suggested_bid")
            if not b:
                # group/keyword had no Planner bid → campaign median so it serves
                for bk in bid_keys:
                    k[bk] = g_med
                k["bid_source"] = "campaign_median_fallback"
                n_fill += 1
            elif b > ceiling:
                for bk in bid_keys:
                    if k.get(bk) and k[bk] > ceiling:
                        k[bk] = ceiling
                k["bid_source"] = "capped_outlier"
                n_cap += 1
    if n_fill or n_cap:
        print(f"   💰 Bid guard: campaign median={g_med}, ceiling={ceiling} | "
              f"{n_fill} no-bid keywords back-filled (would have been ~min bid / "
              f"zero impressions), {n_cap} outliers capped")


def recommend_daily_budget(groups):
    """A daily budget derived from this campaign's own bids and volume.

    Every campaign used to launch on a hardcoded 1000 a day, in whatever the
    account currency happened to be. In AED that is roughly 30,000 a month on
    a campaign nobody sized — and on a small niche it is a number the search
    volume cannot spend anyway. It was a placeholder that shipped.

    The sizing question is "how many clicks a day does this need to learn?"
    Below roughly ten, delivery is lumpy and no meaningful CPA signal ever
    arrives; well above that is just spending faster before there is anything
    to optimise against. So:

        budget = median Max CPC x clicks wanted per day

    with two corrections that matter more than the headline number:

      Volume ceiling. A niche with 300 searches a month cannot produce 15
      clicks a day. Asking for them sets a budget that only ever half-spends
      and makes the campaign look under-delivering when it is simply capped by
      demand. Roughly 5% of impressions becoming clicks is the conservative
      end of a normal Search CTR, and the click target is trimmed to whatever
      that allows, never below 3.

      Top-bid floor. Google throttles delivery when the daily budget cannot
      cover more than a click or two of the most expensive keyword in the
      campaign. The floor keeps the priciest keyword servable.

    Returns None when the Planner gave no bid data at all — the caller then
    leaves the budget to be set by hand, which is the honest outcome.
    """
    bids = sorted(k["suggested_bid"] for g in groups for k in g.get("keywords", [])
                  if k.get("suggested_bid"))
    if not bids:
        return None

    median = bids[len(bids) // 2]
    top = bids[-1]
    volume = sum(k.get("avg_monthly_searches", 0) or 0
                 for g in groups for k in g.get("keywords", []))

    wanted = DAILY_CLICKS_TARGET
    if volume > 0:
        affordable = (volume / 30.0) * 0.05
        wanted = max(3.0, min(float(wanted), affordable))

    budget = median * wanted
    floor = top * 3
    budget = max(budget, floor)

    # Round to something a human would have typed: 2 significant figures up to
    # 100, then to the nearest 10. An oddly precise budget invites nobody to
    # question it, and this number is a starting point, not a measurement.
    if budget < 10:
        budget = round(budget, 1)
    elif budget < 100:
        budget = round(budget)
    else:
        budget = int(round(budget / 10.0) * 10)

    return {
        "daily_budget": budget,
        "currency": BID_CURRENCY,
        "median_bid": median,
        "top_bid": top,
        "clicks_per_day": round(wanted, 1),
        "monthly_volume": volume,
        "basis": (f"{median} {BID_CURRENCY} median Max CPC x {round(wanted, 1)} "
                  f"clicks/day"
                  + (f", raised to 3x the top bid ({top})" if floor > median * wanted else "")),
    }


# ══════════════════════════════════════════════════════════════════════════
# Output writers
# ══════════════════════════════════════════════════════════════════════════

def write_ads_editor_csv(groups, negatives_for_existing=None):
    """Google Ads Editor paste-ready CSVs — TWO separate files:

      google_ads_editor.csv            → positive keywords + intent expansions
      google_ads_editor_negatives.csv  → ad-group-level Negative Phrase rows
                                         (the anti-cannibalization layer; in
                                         existing-account mode also negatives
                                         for the client's existing ad groups)

    Why split (Jul 2026): a single mixed file silently broke — pasting it into
    the Editor's "Keywords" grid imported every row as a POSITIVE keyword
    (the grid ignores Criterion Type), and pasting into "Keywords, Negative"
    produced empty rows ("Keyword text can't be empty") because that grid's
    columns don't line up. The Editor needs positives and negatives pasted
    into their own sections, so we ship them as separate files.

    Import: Ads Editor → Account → Import → "Paste text" (or select the file) —
    once per file. Header follows the Editor's recognized column set; Criterion
    Type values Broad/Phrase/Exact/Negative Phrase map directly. utf-8-sig BOM
    so Excel and the Editor read Arabic/any-script keywords correctly.

    Max CPC = suggested starting bid in BID_CURRENCY (default PKR) — computed by the
    suggest_bids() formula from each keyword's REAL Google top-of-page bid
    range + competition index, scaled by Claude's per-group bid_multiplier.
    Intent-expansion keywords have no Planner data, so they inherit the
    MEDIAN suggested bid of their ad group. Negatives never carry a bid."""
    ctype = {"phrase": "Phrase", "exact": "Exact"}
    with open("google_ads_editor.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Campaign", "Ad Group", "Keyword", "Criterion Type", "Max CPC"])
        for g in groups:
            mt = ctype.get(g["match_type"], "Phrase")
            # group median (match-type bid) — fallback for keywords the
            # Planner returned no bid data for, and for intent expansions
            group_bids = sorted(k["suggested_bid"] for k in g["keywords"]
                                if k.get("suggested_bid"))
            median_bid = group_bids[len(group_bids) // 2] if group_bids else ""
            for k in g["keywords"]:
                w.writerow([g["campaign"], g["name"], k["keyword"], mt,
                            k.get("suggested_bid") or median_bid])
            for e in g["intent_expansion_keywords"]:
                w.writerow([g["campaign"], g["name"], e, "Phrase", median_bid])
    with open("google_ads_editor_negatives.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Campaign", "Ad Group", "Keyword", "Criterion Type"])
        for g in groups:
            for n in g["negative_keywords"]:
                w.writerow([g["campaign"], g["name"], n, "Negative Phrase"])
        for gname, terms in (negatives_for_existing or {}).items():
            for t in terms:
                w.writerow([EXISTING_CAMPAIGN or (groups[0]["campaign"] if groups else ""),
                            gname, t, "Negative Phrase"])


def write_landing_pages_json(pages, groups):
    """Mode 1 landing-engine inputs — one entry per page, ready to feed the
    website builder (service_name → main_service, sub_services list, industry)."""
    by_name = {g["name"]: g for g in groups}
    out = []
    for p in pages:
        _gs = [by_name[a] for a in p["ad_groups_covered"] if a in by_name]
        kw_count = sum(len(g["keywords"]) for g in _gs)
        vol = sum(g["total_volume"] for g in _gs)
        # THE ACTUAL BID TERMS. This function has always had them -- it counted
        # them with len() and sent the count. So the landing page was written
        # from a service name and six sub-service labels, all of them Claude's
        # paraphrase of the keywords, while the terms being paid for never
        # arrived. Quality Score's landing-page component asks whether the page
        # is relevant to THE KEYWORD, and the page could not contain what it
        # never received.
        #
        # Best first, deduped, capped -- a page covering four ad groups can
        # reach 80 terms and the builder only needs the ones worth writing to.
        _seen, _tk = set(), []
        for k in sorted((k for g in _gs for k in g["keywords"]),
                        key=lambda k: -k.get("score", 0)):
            _n = k["keyword"].strip().lower()
            if _n and _n not in _seen:
                _seen.add(_n)
                _tk.append({"keyword": k["keyword"],
                            "volume": k.get("avg_monthly_searches", 0),
                            "intent": k.get("intent", ""),
                            "cpc_range": k.get("cpc_range", ""),
                            "score": k.get("score", 0)})
        # What the ad group EXCLUDES is the other half of message match: it is
        # how the page avoids attracting the intent the campaign pays to block.
        _neg, _nseen = [], set()
        for g in _gs:
            for n in (g.get("negative_keywords") or []):
                _ns = str(n).strip().lower()
                if _ns and _ns not in _nseen:
                    _nseen.add(_ns)
                    _neg.append(str(n).strip())
        out.append({
            **p,
            "keywords_covered": kw_count,
            "monthly_volume_covered": vol,
            "target_keywords": _tk[:25],
            "negative_keywords": _neg[:20],
            "ad_group_themes": [g["theme"] for g in _gs if g.get("theme")],
            "match_types": sorted({g["match_type"] for g in _gs if g.get("match_type")}),
            "mode1_config": {
                "main_service": p["service_name"],
                "sub_services": ", ".join(p["sub_services"]),
                "industry": p["industry"],
            },
            "google_ads_tracking_tip": "Final URL suffix: kw={keyword} — enables the "
                                       "landing page's Dynamic Keyword Insertion (DKI).",
        })
    with open("landing_pages.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return out


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

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
          f"(effort={EFFORT}, ~{est_in} input tokens)...")

    client = anthropic.Anthropic()
    raw = None
    text = ""
    last_err = ""
    for attempt in range(2):
        _prompt = user_prompt
        if attempt == 1:
            _prompt += ("\n\nIMPORTANT: your previous response was not valid JSON. "
                        "Return ONLY the JSON object, nothing else.")
        # claude-sonnet-5: no temperature, no prefill; adaptive thinking is on
        # by default and bills as output tokens — effort caps that spend.
        # max_tokens generous (thinking + ids + expansions + landing pages);
        # streaming required by the SDK for outputs this large.
        with client.messages.stream(
            model=MODEL,
            max_tokens=24000,
            output_config={"effort": EFFORT},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _prompt}],
        ) as stream:
            response = stream.get_final_message()
        text = "".join(b.text for b in response.content if b.type == "text")
        if not text.strip():
            _types = [b.type for b in response.content]
            print(f"⚠️ Attempt {attempt + 1}: empty text (blocks={_types}, "
                  f"stop_reason={response.stop_reason}); retrying...")
            continue
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

    campaigns, groups, pages, uncovered, excluded_ids, unassigned, negatives_for_existing = validate_strategy(raw, kept)

    # SEO material = Claude's exclusions + Python-flagged question/informational
    all_kw = data["keywords"]
    seo_content = [k for k in all_kw
                   if k.get("intent") in ("question", "informational")
                   or k["id"] in excluded_ids]
    voice_qs = [k["keyword"] for k in all_kw if "voice" in k.get("flags", [])]
    local_kws = [k["keyword"] for k in all_kw
                 if "local" in k.get("flags", []) and k.get("kept_for_ai")]

    total_expansions = sum(len(g["intent_expansion_keywords"]) for g in groups)

    strategy = {
        "business": {"name": BUSINESS_NAME, "niche": NICHE_DESCRIPTION,
                     "location": TARGET_LOCATION},
        "model_used": MODEL,
        "campaigns": campaigns,
        "existing_account_mode": bool(EXISTING_CAMPAIGN or EXISTING_AD_GROUPS),
        "fixed_pages_mode": bool(FIXED_PAGES),
        # Sized from this campaign's own bids and volume. The push and the
        # master CSV both read it, so the number the report shows is the
        # number the account gets.
        "budget": recommend_daily_budget(groups),
        # Keywords with real volume that no existing page sells. Not an error
        # and not to be thrown away — this is the client's growth list, and it
        # is what the website builder would build next.
        "new_page_opportunities": (raw.get("new_page_opportunities") or []
                                   if FIXED_PAGES else []),
        "existing_ad_groups": EXISTING_AD_GROUPS,
        "negatives_for_existing_groups": negatives_for_existing,
        "ad_groups": groups,
        "landing_pages": pages,
        "uncovered_ad_groups": uncovered,
        "notes": raw.get("notes", ""),
        "excluded_keyword_ids": excluded_ids,
        "unassigned_keywords": unassigned,
        "seo_content_keywords": [
            {"keyword": k["keyword"], "volume": k["avg_monthly_searches"],
             "intent": k.get("intent", ""), "flags": k.get("flags", [])}
            for k in seo_content
        ],
        "voice_search_questions": voice_qs,
        "local_intent_keywords": local_kws,
        # legacy shape so generate_reports.py keeps working
        "google_ads_targets": [
            {
                "cluster_topic": g["name"],
                "recommended_keywords": [k["keyword"] for k in g["keywords"]],
                "suggested_bid_range": (
                    lambda _b: f"{min(_b)}-{max(_b)} {BID_CURRENCY}" if _b else ""
                )([k["suggested_bid"] for k in g["keywords"] if k.get("suggested_bid")]),
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

    write_ads_editor_csv(groups, negatives_for_existing)
    lp = write_landing_pages_json(pages, groups)

    # ── Markdown summary ──
    md = [f"# Google Ads Strategy — {BUSINESS_NAME or 'Untitled'}\n"]
    if NICHE_DESCRIPTION:
        md.append(f"*{NICHE_DESCRIPTION}* — {TARGET_LOCATION}\n")
    md.append(f"**{len(campaigns)} campaigns | {len(groups)} ad groups | "
              f"{sum(len(g['keywords']) for g in groups)} keywords + "
              f"{total_expansions} intent expansions | {len(pages)} landing pages**\n")
    for c in campaigns:
        md.append(f"## 📣 Campaign: {c['name']}  `{c['priority']}`")
        for g in [g for g in groups if g["campaign"] == c["name"]]:
            _mtr = g.get("match_type_reason", "")
            md.append(f"### {g['name']}  `{g['priority']}` `{g['match_type']}`")
            if _mtr:
                md.append(f"*match type: {_mtr}*")
            md.append(f"_{g['theme']}_")
            md.append(f"- Volume: {g['total_volume']}/mo | Avg score: {g['avg_score']} | {len(g['keywords'])} keywords")
            _bids = [k["suggested_bid"] for k in g["keywords"] if k.get("suggested_bid")]
            if _bids:
                md.append(f"- 💰 Suggested Max CPC ({BID_CURRENCY}, {g['match_type']}): "
                          f"{min(_bids)}–{max(_bids)} (group bid multiplier ×{g['bid_multiplier']})")
            md.append(f"- Keywords: " + ", ".join(
                          k["keyword"] + (f" [{k['suggested_bid']} {BID_CURRENCY}]"
                                          if k.get("suggested_bid") else "")
                          for k in g["keywords"][:15])
                      + (f" … +{len(g['keywords'])-15} more" if len(g["keywords"]) > 15 else ""))
            if g["intent_expansion_keywords"]:
                md.append(f"- 🆕 Intent expansions: " + ", ".join(g["intent_expansion_keywords"]))
            if g["negative_keywords"]:
                md.append(f"- 🚫 Negatives (anti-cannibalization): " + ", ".join(g["negative_keywords"]))
            md.append("")
    if negatives_for_existing:
        md.append("## 🛡️ Negatives for EXISTING ad groups (2-way anti-cannibalization)")
        md.append("_Ye terms client ke pehle se chalne wale ad groups mein NEGATIVE ke "
                  "taur par add karein taake wo naye group ki traffic na khayein:_")
        for gname, terms in negatives_for_existing.items():
            md.append(f"- **{gname}**: " + ", ".join(terms))
        md.append("")
    md.append("## 🖥️ Landing Pages (Mode 1 generator inputs)")
    for p in lp:
        md.append(f"### {p['page_name']}  →  /{p['url_slug']}/")
        md.append(f"- service_name: **{p['service_name']}** | industry: {p['industry']}")
        md.append(f"- sub_services: " + ", ".join(p["sub_services"]))
        md.append(f"- Covers: {', '.join(p['ad_groups_covered'])} "
                  f"({p['keywords_covered']} keywords, {p['monthly_volume_covered']}/mo)")
        md.append("")
    if strategy["notes"]:
        md.append(f"**Strategy notes:** {strategy['notes']}\n")
    if voice_qs:
        md.append("## Voice-search / question keywords (SEO content, not ads)")
        md.extend(f"- {q}" for q in voice_qs[:20])
    with open("keyword_strategy.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    usage = getattr(response, "usage", None)
    if usage:
        cost = usage.input_tokens * 3 / 1e6 + usage.output_tokens * 15 / 1e6
        print(f"   Tokens: {usage.input_tokens} in / {usage.output_tokens} out "
              f"≈ ${cost:.3f} this run")
    print(f"✅ {len(campaigns)} campaigns | {len(groups)} ad groups | "
          f"{total_expansions} intent expansions | {len(pages)} landing pages "
          f"| {len(excluded_ids)} excluded | {len(unassigned)} unassigned")
    if uncovered:
        print(f"⚠️ Ad groups not covered by any landing page: {uncovered}")
    print("✅ Saved: keyword_strategy.json, keyword_strategy.md, "
          "google_ads_editor.csv, google_ads_editor_negatives.csv, "
          "landing_pages.json")


if __name__ == "__main__":
    main()
