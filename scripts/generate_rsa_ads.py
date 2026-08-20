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
from urllib.parse import urlparse

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
# Google Ads requires an http(s) scheme on Final URLs — a bare domain from
# the form ("appliancerepairsabudhabi.com") gets rejected at import/review.
if WEBSITE_URL and not re.match(r"^https?://", WEBSITE_URL, re.IGNORECASE):
    WEBSITE_URL = "https://" + WEBSITE_URL

# Content language (Jul 2026): the SYSTEM prompt already says "write in the
# language of the keywords", but a group with few/short keywords can slip into
# English. When LANGUAGE is set explicitly we name the language so every RSA
# asset is unambiguously in it. Blank/"en" = unchanged.
# Every code the form and the workflow accept. A code missing here produced ad
# copy with NO language instruction at all — Claude then guessed from the
# keywords, so a Czech or Thai run could come back with English headlines.
_RSA_LANG_NAMES = {
    "en": "English", "ar": "Arabic", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "nl": "Dutch",
    "ru": "Russian", "tr": "Turkish", "hi": "Hindi", "ur": "Urdu",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "pl": "Polish",
    "cs": "Czech", "el": "Greek", "hu": "Hungarian", "id": "Indonesian",
    "ro": "Romanian", "sv": "Swedish", "th": "Thai", "vi": "Vietnamese",
}
_rsa_lang = os.environ.get("LANGUAGE", "").strip().lower()
_rsa_lang = {"no": "", "english": "en", "spanish": "es", "french": "fr",
             "german": "de", "arabic": "ar"}.get(_rsa_lang, _rsa_lang)
RSA_LANG_NAME = _RSA_LANG_NAMES.get(_rsa_lang, "") if _rsa_lang != "en" else ""

INPUT_JSON = "keyword_strategy.json"
OUT_JSON = "rsa_ads.json"
OUT_CSV = "rsa_editor.csv"
OUT_MD = "rsa_ads.md"

H_MAX, D_MAX, PATH_MAX = 30, 90, 15

# Google halves every text limit for double-width scripts: a Chinese, Japanese
# or Korean headline gets 15 characters, not 30, and a description 45. The
# limits were flat here, so a zh/ja/ko run wrote assets up to twice the legal
# length and Google rejected them at import or push — after the Claude spend,
# with nothing usable to show for it. Arabic, Urdu, Hindi, Thai and Greek are
# NOT double-width; they keep the full 30/90.
_DOUBLE_WIDTH = {"zh", "ja", "ko"}


def limits_for(lang_code):
    """(headline, description, path) limits for one ad group's language."""
    if str(lang_code or "").strip().lower() in _DOUBLE_WIDTH:
        return 15, 45, 7
    return H_MAX, D_MAX, PATH_MAX
N_HEADLINES, N_DESCRIPTIONS = 15, 4
MIN_KEYWORD_HEADLINES = 7

# Acronyms that may legitimately appear in caps
CAPS_OK = {"PPC", "USA", "UAE", "UK", "AI", "SEO", "CPC", "ROI", "RSA",
           "HVAC", "LLC", "CRM", "API", "IP", "VPN", "GPS", "TV", "AC",
           "FAQ", "B2B", "B2C", "CEO", "IT", "HR", "3D", "24", "7",
           "LG", "GE", "AEG", "IFB", "TCL", "LED", "LCD", "CCTV", "RO",
           "UPS", "PVC", "DIY", "KSA", "GCC"}

# Tokens safe to force into caps wherever they appear ("Lg Fridge Repair" →
# "LG Fridge Repair"). Deliberately EXCLUDES ambiguous acronyms that are
# also English words in Title Case (It, Hr, Ai...) — only unambiguous
# brand/tech tokens go here.
FORCE_CAPS = {"lg": "LG", "ge": "GE", "aeg": "AEG", "ifb": "IFB",
              "tcl": "TCL", "hvac": "HVAC", "cctv": "CCTV", "led": "LED",
              "lcd": "LCD", "uae": "UAE", "usa": "USA", "ksa": "KSA",
              "gcc": "GCC", "ac": "AC", "diy": "DIY", "upvc": "UPVC"}

BANNED_PHRASES = [
    "click here", "click now", "tap here",
    "#1", "no. 1", "no.1", "number one", "number 1",
    "best in the world", "world's best", "worlds best",
    "guaranteed #", "100% guaranteed",
]

# Agency-grade quality floor: assets with these template-filler patterns are
# dropped (the keyword-coverage top-up then fills the slot with a clean
# keyword headline). "Rough copy" complaint, Jul 2026.
WEAK_FILLER = [
    " woes", "say goodbye", "look no further", "hassle-free", "hassle free",
    "got you covered", "made easy", "trusted partner", "one stop", "one-stop",
    "stress-free", "stress free", "worry-free", "worry free", "we care",
    "look further", "dream come true",
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
    # brand/tech casing: "Lg" / "lg" -> "LG" wherever it appears
    def _brand(m):
        return FORCE_CAPS[m.group(0).lower()]
    s = re.sub(r"\b(" + "|".join(FORCE_CAPS) + r")\b", _brand, s, flags=re.IGNORECASE)
    return s.strip()


def violates_policy(s):
    low = s.lower()
    if any(p in low for p in BANNED_PHRASES):
        return "banned phrase"
    if any(p in low for p in WEAK_FILLER):
        return "weak template filler"
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


def make_paths(slug, path_max=PATH_MAX):
    parts = [p for p in re.split(r"[^a-z0-9]+", str(slug).lower()) if p]
    p1, p2 = "", ""
    for part in parts:
        cand = (p1 + "-" + part).strip("-")
        if len(cand) <= path_max:
            p1 = cand
        elif not p2:
            p2 = part[:path_max]
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
9. Brand names keep their OFFICIAL casing: LG, Bosch, Siemens, GE,
   Samsung — never "Lg" or "bosch".

CRAFT BAR — write like a top agency's senior copywriter, not a template:
- Specifics beat adjectives: "Fixed In One Visit" beats "Fast Service";
  a real process detail ("Free Diagnosis Before Repair") beats "Quality
  Service You Can Trust".
- BANNED filler patterns (auto-reject): "No More X Woes", "Say Goodbye
  To X", "X Made Easy", "Look No Further", "Your Trusted Partner",
  "We've Got You Covered", "Hassle-Free X", "Your X Solution".
- USE THE SPACE: headlines should mostly run 24-30 characters and
  descriptions 78-90 — short assets waste auction real estate.
- Name the TARGET MARKET location in 2-3 headlines and at least 2
  descriptions — local searchers click local ads.
- The HIGHEST-VOLUME keywords deserve the most natural, closest-to-verbatim
  headlines: match the exact words people type, then add one click trigger
  (today / near you / cost / same day).

HEADLINE MIX (exactly 15):
- 5 keyword-led: the target keyword itself, naturally phrased, clickable
  (these carry the Quality Score message match)
- 3 benefit-led: the concrete outcome the buyer gets
- 3 call-to-action: specific action + value ("Get Your Free Audit Today")
- 2 trust/proof: specifics beat adjectives ("Setup In Under 5 Minutes")
- 2 offer/price-angle: honest, no fake discounts

DESCRIPTION MIX (exactly 4, each a complete thought with its own CTA,
each using words from the actual keywords so the ad bolds on the query):
1. keyword + core benefit + CTA
2. differentiator (what competitors do not offer)
3. objection-killer (risk, effort, price doubt)
4. urgency or social proof, honest only

Output ONLY valid JSON:
{{"headlines": ["...", 15 items], "descriptions": ["...", 4 items]}}"""

if RSA_LANG_NAME:
    SYSTEM += (f"\n\nHARD LANGUAGE RULE: write EVERY headline and description in "
               f"{RSA_LANG_NAME}. Character limits (30/90) still apply to the "
               f"{RSA_LANG_NAME} text. Brand names keep official casing.")


_SCRIPT_LANG = [("ar", "Arabic", r"[؀-ۿ]"), ("hi", "Hindi", r"[ऀ-ॿ]"),
                ("ru", "Russian", r"[Ѐ-ӿ]"), ("zh", "Chinese", r"[一-鿿]")]


def group_language(group):
    """(code, language name) for THIS ad group — its own `language` field when
    the strategy carries one, else detected from its keywords.

    RSA_LANG_NAME is the RUN-WIDE language, so a mixed Arabic+English account
    run on the English default handed the Arabic ad groups ENGLISH ad copy:
    Arabic keywords with English headlines cannot serve and destroy Quality
    Score. Ad copy follows the ad group, never the run."""
    code = str(group.get("language") or "").strip().lower()
    if code and code != "en":
        return code, _RSA_LANG_NAMES.get(code, code)
    if code == "en":
        return "en", RSA_LANG_NAME or ""
    blob = " ".join([str(group.get("name", "")), str(group.get("theme", ""))]
                    + [str(k.get("keyword", "")) for k in (group.get("keywords") or [])])
    for c, name, pattern in _SCRIPT_LANG:
        if re.search(pattern, blob):
            return c, name
    return "en", RSA_LANG_NAME or ""


# Where does the website builder publish this language — /{lang}/ or the domain
# root? The builder's own `lang_url_prefix` config defaults to "yes" (the folder),
# so that is the default here too. Set LANG_URL_PREFIX=no ONLY when the builder
# was run with lang_url_prefix=no; the two MUST agree or the ads 404.
_LANG_AT_ROOT = os.environ.get("LANG_URL_PREFIX", "yes").strip().lower() in (
    "no", "false", "0", "root")


def lang_url_prefix(lang_code):
    """The website builder publishes non-English content under /{lang}/
    (lang_mode folder). An Arabic ad group whose Final URL skipped that folder
    pointed at a 404 while the real page sat at /ar/{slug}/.

    The prefix used to be dropped whenever the ad group's language equalled the
    run-wide LANGUAGE — which is true of EVERY single-language campaign, the
    normal case. A full Arabic run therefore pointed every ad and sitelink at
    /{slug}/ while the builder published /ar/{slug}/, so the whole campaign
    served 404s. The run-wide language says nothing about where the pages live;
    only the builder's lang_url_prefix does, so that is what decides now.
    """
    code = (lang_code or "en").strip().lower()
    if not code or code == "en" or _LANG_AT_ROOT:
        return ""
    return f"/{code}"


def ask_claude(client, group, kw_lines, retry_note="", page=None,
               h_max=H_MAX, d_max=D_MAX):
    _code, _lang_name = group_language(group)
    # The per-group rule rides in the USER message so the cached SYSTEM prompt
    # stays byte-identical across ad groups (prompt-cache discount preserved).
    lang_rule = (f"\nLANGUAGE FOR THIS AD GROUP: write EVERY headline and description in "
                 f"{_lang_name}. Its keywords are in {_lang_name}, so an ad in any other "
                 f"language cannot serve for them. The 30/90 character limits are counted "
                 f"in {_lang_name} characters.\n" if _lang_name else "")
    # FIXED PAGES MODE: the landing page already exists and we have read it,
    # so the ad can be written in the page's own words. That is the whole
    # Quality Score argument — Ad Relevance and Landing Page Experience both
    # improve when the ad promises what the page actually says, instead of
    # what a slug suggested it might say.
    page_block = ""
    if page and (page.get("h1") or page.get("h2")):
        _h2 = " | ".join((page.get("h2") or [])[:8])
        _h3 = " | ".join((page.get("h3") or [])[:8])
        page_block = f"""
THE LANDING PAGE THIS AD SENDS PEOPLE TO (already live — read it and match it):
  URL: {page.get('final_url', '')}
  H1: {page.get('h1', '')}
  H2s: {_h2 or '(none)'}
  H3s: {_h3 or '(none)'}
  Sells: {page.get('service_name', '')}
Write copy the page can back up. Promise nothing that is not on that page —
a headline the page does not deliver is a bounced click and a bad Landing
Page Experience score. Where the page names a real offer, guarantee or
credential, put it in a headline.
"""

    # Stated only when it differs from the cached SYSTEM prompt's 30/90, so an
    # ordinary run keeps its prompt-cache discount.
    limit_rule = ("" if (h_max, d_max) == (H_MAX, D_MAX) else
                  f"\nCHARACTER LIMITS FOR THIS AD GROUP: headlines {h_max} "
                  f"characters, descriptions {d_max} — NOT 30/90. Google halves "
                  f"every text limit for this script. Count each character.\n")

    user = f"""AD GROUP: {group['name']}
THEME (the single user intent): {group.get('theme', '')}
{lang_rule}{limit_rule}{page_block}TARGET KEYWORDS (with monthly volume):
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


def validate_and_repair(raw, group_keywords, h_max=H_MAX, d_max=D_MAX):
    """Clean every asset, drop invalid ones, report what survived.

    h_max/d_max come from the ad group's own language, because a mixed
    account can hold a Japanese group beside an English one and they do not
    share a character limit."""
    kw_token_sets = [tokens_of(k) for k in group_keywords]

    headlines, seen = [], set()
    for h in (raw.get("headlines") or []):
        h = clean_text(h, is_headline=True)
        if not h or len(h) > h_max or violates_policy(h):
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
        if not d or len(d) > d_max or violates_policy(d):
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
    # FIXED PAGES MODE: the page is already live and its URL is carried on the
    # strategy verbatim. Rebuilding it from a slug is exactly the invention
    # that produced ads pointing at pages nobody had built — so when a page
    # brings its own final_url, that URL is used and nothing recomputes it.
    url_by_group = {}
    page_by_group = {}
    for lp in (strategy.get("landing_pages") or []):
        for g in (lp.get("ad_groups_covered") or []):
            slug_by_group[g] = lp.get("url_slug", "")
            page_by_group[g] = lp
            if lp.get("final_url"):
                url_by_group[g] = lp["final_url"]

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

        # This group's own limits — halved for Chinese, Japanese and Korean.
        _h_max, _d_max, _path_max = limits_for(group_language(group)[0])

        headlines, descriptions = [], []
        for attempt in (1, 2):
            note = "" if attempt == 1 else (
                f"\nPREVIOUS ATTEMPT FAILED VALIDATION — you returned "
                f"{len(headlines)} valid headlines / {len(descriptions)} valid "
                f"descriptions. Keep every headline UNDER {_h_max} characters "
                f"and every description UNDER {_d_max} characters. Recount each one.")
            try:
                raw = ask_claude(client, group, kw_lines, note,
                                 page=page_by_group.get(group["name"]),
                                 h_max=_h_max, d_max=_d_max)
            except Exception as e:
                print(f"   ⚠️ Claude call failed for '{group['name']}': {e}")
                raw = {}
            headlines, descriptions = validate_and_repair(raw, kws, _h_max, _d_max)
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
        _fixed = url_by_group.get(group["name"], "")
        if _fixed:
            # A live URL: no language folder, no slug arithmetic. The path
            # crumbs still come from the URL's own last segment so the display
            # path matches where the click actually lands.
            final_url = _fixed
            _seg = [x for x in urlparse(_fixed).path.split("/") if x]
            p1, p2 = make_paths(_seg[-1] if _seg else group["name"], _path_max)
        else:
            _g_code, _ = group_language(group)
            _pfx = lang_url_prefix(_g_code)
            final_url = f"{base}{_pfx}/{slug}/" if slug else f"{base}{_pfx}/"
            p1, p2 = make_paths(slug or group["name"], _path_max)
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
