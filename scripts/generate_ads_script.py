"""
generate_ads_script.py  (STAGE 3.6 — negative-guard Google Ads Script generator)
----------------------------------------------------------------------------------
Runs after analyze_with_claude.py. Takes keyword_strategy.json and produces
`negative_guard_script.js` — a ready-to-paste Google Ads Script that runs
hourly inside the client's account and auto-negatives irrelevant search terms.

UNIVERSAL: nothing niche-specific is hardcoded. Every list is built from the
campaign's own keyword data + one small Claude call for niche knowledge
(other trades, DIY/info intent, retail/B2B/jobs, nearby wrong locations).

WHY DATA-DRIVEN BEATS HAND-WRITTEN LISTS:
  - SAFE_ROOTS  = the actual bid keywords + intent expansions (what we WANT).
  - PRODUCTS    = distinctive tokens extracted from those keywords.
  - FORBIDDEN   = Claude's niche list, then Python REMOVES any entry that
                  collides with a bid keyword. Example: if the account has a
                  "Pricing & Quotes" ad group, "price/cost" are automatically
                  NOT forbidden — the #1 false-positive source in hand-written
                  scripts.

ENGINE (v2 — merges the tactics of the best hand-tuned cleaners):
  0. converted search terms are NEVER banned (protect what already works)
  1. forbidden locations → block
  2. education / career / tools / spec queries → block  (multi-language,
     incl. Roman-Urdu/Hindi transliterations common in GCC markets)
  3. info / DIY intent → block
  4. forbidden words → block (collision-filtered against bid keywords)
  5. context words ("fitting", "handle", "door"...) → block ONLY when no
     service signal (action / problem / service-root) appears with them
  6. fuzzy service-root typo (plamber→plumber, carpanter→carpenter) → KEEP —
     misspelled potential keywords are leads, not junk
  7. safe roots (our bid keywords + known-good phrases) → allow
  8. product + (action OR problem-signal like "leaking"/"not working") → allow
  9. short bare product query (≤3 words, e.g. "kitchen cabinets") → allow
 10. catch-all → block

  - whole-token fuzzy matching (typos, plurals stripped) — never substring,
    so "place" can NEVER hit "replacement"
  - DRY_RUN mode (default ON for the first runs)
  - negatives added as EXACT [term] (surgical); repeat forbidden roots are
    logged as phrase-negative suggestions instead of auto-phrase-banning

Env vars: ANTHROPIC_API_KEY, BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION
Optional: CLAUDE_MODEL (default claude-sonnet-5), CLAUDE_EFFORT_SCRIPT (low)

Input : keyword_strategy.json
Output: negative_guard_script.js
"""

import os
import re
import sys
import json
import csv

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

STRATEGY_FILE = "keyword_strategy.json"
OUTPUT_FILE = "negative_guard_script.js"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
EFFORT = os.environ.get("CLAUDE_EFFORT_SCRIPT", "low")
BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()

STOPWORDS = {"a", "an", "the", "in", "of", "and", "for", "to", "near", "me", "my",
             "with", "at", "on", "best", "top", "new"}

# Universal service-intent action words — apply to every service business.
# Niche-specific verbs get ADDED by Claude, never replaced.
UNIVERSAL_ACTIONS = [
    "repair", "repairs", "repairing", "fix", "fixes", "fixing", "fixed",
    "service", "services", "servicing", "maintenance", "maintain", "amc", "contract",
    "install", "installs", "installation", "installing", "replace", "replacement",
    "replacing", "change", "changing", "remove", "removal", "relocate", "relocation",
    "clean", "cleaning", "cleaner", "wash", "washing", "deep cleaning",
    "technician", "company", "companies", "professional", "specialist", "expert",
    "certified", "trusted", "licensed", "contractor",
    "custom", "bespoke", "made to measure", "made to order", "tailor made",
    "design", "designer", "build", "builder", "builders", "making", "maker", "makers",
    "emergency", "urgent", "24 hour", "24hr", "24/7", "same day", "fast", "quick",
    "now", "today", "book", "booking", "hire", "quote", "quotes", "quotation",
    "contact", "number", "whatsapp", "call",
    "check", "inspect", "inspection", "diagnose", "solution", "help",
    "refill", "recharge", "regas", "re gas", "gas filling", "gas refilling", "gas charging",
    "near me", "nearby", "local", "in my area",
    "تصليح", "اصلاح", "صيانة", "فني", "فنيين", "تركيب", "تنظيف", "تعبئة", "تبديل",
    "شركة", "خدمة", "مركز", "قريب", "طوارئ",
]

# STRONG service verbs only — used by the context-word rule. "near me" /
# "dubai" / "company" are NOT here on purpose: "bathroom fittings near me"
# is a shop-search, not a job; only a real service verb ("installation",
# "repair") turns an ambiguous product word into a lead.
UNIVERSAL_STRONG_ACTIONS = [
    "repair", "repairs", "repairing", "fix", "fixes", "fixing", "fixed",
    "install", "installs", "installation", "installing", "replace",
    "replacement", "replacing", "service", "services", "servicing",
    "maintenance", "maintain", "amc", "clean", "cleaning", "wash", "washing",
    "refill", "recharge", "regas", "re gas", "gas filling", "gas refilling", "gas charging",
    "custom", "bespoke", "made to measure", "made to order", "tailor made",
    "design", "designer", "build", "builder", "making", "maker",
    "renovation", "renovate", "remodel", "remodeling", "refurbish",
    "restore", "restoration", "unblock", "unclog", "inspect", "inspection",
    "detect", "detection", "mount", "mounting", "fitted", "fabrication",
    "تصليح", "اصلاح", "صيانة", "تركيب", "تنظيف", "تعبئة", "تبديل",
]

# ══════════════════════════════════════════════════════════════════════════
# Universal blocker/allow lists (v2) — tactics ported from the best
# hand-tuned cleaner scripts. English + Roman-Urdu/Hindi transliterations
# (common across GCC / South-Asian markets; harmless elsewhere — a term in a
# language nobody types simply never matches). All collision-filtered
# against the account's own bid keywords before use.
# ══════════════════════════════════════════════════════════════════════════

# Searcher is learning / job-hunting / spec-hunting — never a customer.
UNIVERSAL_EDU_CAREER = [
    "define", "definition", "meaning of", "what is", "mechanism of",
    "how does", "how do", "what happens", "diagram", "schematic",
    "types of", "course", "courses", "training", "academy", "institute",
    "certification", "certificate", "diploma", "how to become",
    "salary", "salaries", "wage", "wages", "career", "careers", "job",
    "jobs", "vacancy", "vacancies", "hiring", "recruitment", "cv", "resume",
    "interview questions", "apprenticeship", "internship",
    "tools name", "tool name", "tools list", "material list", "items list",
    "name list", "size chart", "standard height", "datasheet", "catalogue",
    # Roman-Urdu / Hindi
    "kaise sikhe", "kaise seekhe", "kaise bane", "kaise khole", "dukan kaise",
    "shop kaise", "business kaise", "kitni salary", "ka kaam", "ka kam",
    "kya hota hai", "kya hai", "kitne prakar", "kitne type", "meaning in",
    "in hindi", "in urdu", "translate",
    # Arabic
    "وظائف", "وظيفة", "مطلوب", "راتب", "رواتب", "دورة", "دورات", "كورس", "تعليم",
    "تدريب", "معهد", "شهادة",
]

# Searcher wants to do it themselves / just wants information. "manual" only
# as a document: "manual washing machine repair" is a buyer.
UNIVERSAL_INFO_DIY = [
    "how to", "diy", "do it yourself", "tutorial", "youtube", "user manual",
    "owners manual", "owner manual", "instruction manual", "service manual",
    "manual pdf", "pdf",
    "instructions", "difference between", "what causes", "wikipedia",
    # Roman-Urdu / Hindi DIY
    "khud se", "khud lagana", "khud banana", "ghar par kaise", "ki setting",
    # Arabic
    "كيف", "كيفية", "طريقة", "طريقه", "بنفسك", "يوتيوب", "شرح",
]

# Searcher wants the MAKER's own line, not a local business.
UNIVERSAL_FORBIDDEN = [
    "customer care", "customer service number", "helpline", "toll free",
    "complaint number", "official website", "خدمة العملاء", "الوكيل",
]

# Roman-Urdu price/shopping intent — merged into FORBIDDEN (collision-filtered).
UNIVERSAL_PRICE_SHOPPING_RU = [
    "ka dam", "ki qeemat", "kitna hai", "kitne ka", "ka price",
    "khareedna", "kharidna", "sasta",
]

# How customers describe a BROKEN state — this IS service intent even with no
# action verb ("toilet not flushing", "gate stuck"). Claude adds niche ones.
UNIVERSAL_PROBLEM_SIGNALS = [
    "not working", "not turning on", "stopped working", "wont work",
    "won't work", "wont turn", "broken", "broke", "leaking", "leaky",
    "leakage", "dripping", "burst", "clogged", "blocked", "blockage",
    "jammed", "stuck", "overflow", "overflowing", "smell", "smelly",
    "smells", "noise", "noisy", "vibrating", "slow", "weak",
    "low pressure", "tripping", "overheating", "short circuit", "rusted",
    "corroded", "damaged", "damage", "cracked", "crack", "problem",
    "problems", "issue", "issues", "fault", "faulty", "kharab",
]


def robust_json(text):
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text.strip(), flags=re.MULTILINE).strip()
    s, e = text.find("{"), text.rfind("}") + 1
    return json.loads(text[s:e])


def tokens_of(s):
    # Unicode-aware: Arabic/any-script tokens survive (old regex was ASCII-only)
    return re.findall(r"[^\W_]+", str(s).lower(), re.UNICODE)


def build_lists(strategy):
    groups = strategy.get("ad_groups", [])
    bid_keywords = []
    for g in groups:
        for k in g.get("keywords", []):
            bid_keywords.append(k["keyword"].lower())
            bid_keywords.extend(v.lower() for v in k.get("variants", []))
        bid_keywords.extend(e.lower() for e in g.get("intent_expansion_keywords", []))
    bid_keywords = sorted(set(bid_keywords))

    # Distinctive product tokens: frequent, non-action, non-stopword tokens.
    # Threshold adapts to dataset size — a small niche (few bid keywords)
    # would otherwise produce ZERO products, and then the product+action
    # rule can never allow anything: every non-safe-root term gets banned.
    freq = {}
    for kw in bid_keywords:
        for t in set(tokens_of(kw)):
            freq[t] = freq.get(t, 0) + 1
    action_tokens = {t for a in UNIVERSAL_ACTIONS for t in tokens_of(a)}
    loc_tokens = set(tokens_of(TARGET_LOCATION))
    min_freq = 3 if len(bid_keywords) >= 15 else 2
    products = sorted(t for t, c in freq.items()
                      if c >= min_freq and len(t) >= 4
                      and t not in action_tokens and t not in STOPWORDS
                      and t not in loc_tokens)

    # FUZZY SERVICE ROOTS: the head tokens of this account (plumber,
    # carpenter, perfume...) — a misspelling of one of these is a potential
    # customer, never junk ("carpanter dubai" must be KEPT). Data-derived:
    # highest-frequency long tokens that aren't actions/locations. len >= 6
    # so 1-edit fuzzy can't false-match short everyday words.
    fuzzy_roots = [t for t, c in sorted(freq.items(), key=lambda x: -x[1])
                   if len(t) >= 6 and t not in action_tokens
                   and t not in STOPWORDS and t not in loc_tokens][:6]

    return bid_keywords, products, fuzzy_roots


def ask_claude(bid_keywords, products):
    client = anthropic.Anthropic()
    prompt = f"""BUSINESS: {BUSINESS_NAME}
NICHE: {NICHE_DESCRIPTION}
TARGET LOCATION: {TARGET_LOCATION}

We are generating a Google Ads search-term cleaning script for this business.
The account bids on these keywords (sample): {json.dumps(bid_keywords[:80])}
Distinctive product tokens: {json.dumps(products[:40])}

Return ONLY JSON:
{{
  "forbidden_locations": ["..."],
  "forbidden_words": ["..."],
  "edu_career_words": ["..."],
  "info_diy_words": ["..."],
  "context_product_words": ["..."],
  "problem_signals": ["..."],
  "extra_safe_roots": ["..."],
  "extra_products": ["..."],
  "extra_actions": ["..."]
}}

LANGUAGE RULE (critical): detect every language present in the bid keywords
above (English, Arabic, Hindi/Urdu transliteration, etc.) AND the languages
customers commonly search in for this market. EVERY list below must cover ALL
of those languages — e.g. for a UAE/Saudi market include Arabic script terms
and Hinglish/Urdu transliterations alongside English.

Rules:
- forbidden_locations: cities/regions/countries NEAR the target location that
  the business does NOT serve (competing emirates/cities, neighbor countries),
  including common misspellings and local-language spellings.
  NEVER include the target location itself or its own areas/neighborhoods.
- forbidden_words: 40-80 terms that signal WRONG intent for this specific
  business: adjacent trades it does NOT do, jobs/careers/salary,
  retail/marketplace/buy/used/rent (only if the business SELLS services not
  products), spare parts, well-known competitor brand names in that market,
  B2B/wholesale/manufacturer terms.
  CRITICAL: never include any word that appears in the bid keywords above.
- edu_career_words: 15-40 NICHE-SPECIFIC learning/career/spec queries beyond
  the obvious ("how to become", "salary"): trade-school phrases, tool-name
  lookups, size/spec questions, "types of X" patterns for THIS niche, in all
  the market's languages/transliterations.
- info_diy_words: 10-25 niche DIY/informational patterns beyond generic
  "how to" (e.g. "reset", "error code", "settings" for appliance niches).
- context_product_words: 5-15 AMBIGUOUS single words that usually mean
  product-shopping in this niche UNLESS a service word appears with them
  (e.g. "fitting", "handle", "hinge", "door" for trades; "bottle", "tester"
  for perfume). The script blocks them ONLY when no service signal is present.
- problem_signals: 15-40 phrases customers of THIS niche use to describe the
  broken/needed state ("gate not closing", "water coming out", "paint
  peeling") — these count as service intent and PROTECT terms from banning.
- extra_safe_roots: 10-25 phrases customers of this business also search that
  must NEVER be banned (crossover services it likely handles, urgent
  phrasings, local-language service phrases if common in that market).
- extra_products: brand names / product nouns of this niche people include in
  service searches (e.g. appliance brands for repair niches). Empty if none.
- extra_actions: niche-specific action/intent verbs not in a generic list.
- Everything lowercase. No duplicates."""
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": EFFORT},
        system="You are a Google Ads search-term quality expert. Return only valid JSON.",
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        resp = stream.get_final_message()
    text = "".join(b.text for b in resp.content if b.type == "text")
    data = robust_json(text)
    usage = resp.usage
    cost = usage.input_tokens * 3 / 1e6 + usage.output_tokens * 15 / 1e6
    print(f"   Claude niche lists: {usage.input_tokens} in / {usage.output_tokens} out ≈ ${cost:.3f}")
    return data


def filter_forbidden(forbidden, bid_keywords, label="forbidden"):
    """Kill any block-list entry that collides with our own bid keywords —
    the #1 false-positive source. Collision = the phrase appears inside any
    bid keyword (token-wise) or shares a token with them (single-word
    entries). Applied to EVERY block list (forbidden/edu/info-diy), so an
    IELTS academy bidding on "ielts course" auto-drops "course" from the
    education blockers."""
    bid_token_set = {t for kw in bid_keywords for t in tokens_of(kw)}
    bid_text = " | ".join(bid_keywords)
    clean, dropped = [], []
    for w in forbidden:
        w = str(w).strip().lower()
        if not w:
            continue
        toks = tokens_of(w)
        if len(toks) == 1 and toks[0] in bid_token_set:
            dropped.append(w); continue
        if re.search(r"(^|[\s|])" + re.escape(w) + r"([\s|]|$)", bid_text):
            dropped.append(w); continue
        clean.append(w)
    if dropped:
        print(f"   🛡️ Dropped {len(dropped)} {label} words that collide with bid keywords: {dropped[:10]}{'...' if len(dropped) > 10 else ''}")
    return sorted(set(clean))


JS_TEMPLATE = r"""/**
 * 🛡️ NEGATIVE GUARD v2 — %%BUSINESS%% (%%LOCATION%%)
 * AUTO-GENERATED from real keyword data by the keyword-research-tool.
 * Engine: GAQL (search_term_view) | Frequency: run HOURLY
 *
 * LOGIC ORDER (first match wins):
 *   0. CONVERTED TERM (has conversions)       -> ALWAYS ALLOW (never ban a converter)
 *   1. Forbidden Location                     -> BLOCK
 *   2. Education / Career / Tools / Specs     -> BLOCK (multi-language)
 *   3. Info / DIY intent                      -> BLOCK
 *   4. Forbidden Word (typo-aware)            -> BLOCK
 *      Soft word (brand, other trade, price)
 *      with none of OUR services in the query -> BLOCK
 *      Part shopping ("replacement screen")   -> BLOCK
 *      Product price / symptom, no hire word  -> BLOCK
 *   5. Context word (product-shopping) with
 *      NO service signal in the same query    -> BLOCK
 *   6. Fuzzy service-root typo (plamber,
 *      carpanter...)                          -> ALLOW (typos are leads!)
 *   7. Safe Root (bid keywords + known-good)  -> ALLOW
 *   8. Product + (Action OR Problem signal
 *      like "leaking"/"not working")          -> ALLOW
 *   9. Short bare product query (<=3 words,
 *      e.g. "kitchen cabinets")               -> ALLOW
 *  10. Catch-all                              -> BLOCK
 *
 * MATCHING RULES:
 *   - whole tokens only: "place" can NEVER match inside "replacement"
 *   - typo tolerance: token Levenshtein <=1 (len>=5) / <=2 (len>=9)
 *   - plurals stripped: plumbers->plumber, cabinets->cabinet
 *   - negatives are added as EXACT [term] (surgical, zero collateral damage)
 *   - repeat forbidden roots are LOGGED as phrase-negative suggestions
 */

function main() {
  // ⚙️ CONFIG — sirf campaign name check karein, baqi sab data-generated hai.
  //    Case ki fikar na karein: naam account se case-insensitively match hota hai.
  var CAMPAIGN_NAMES = %%CAMPAIGNS%%;
  var DATE_RANGE = "TODAY";        // TODAY | YESTERDAY | LAST_7_DAYS
  var MIN_IMPRESSIONS = 0;
  var DRY_RUN = false;             // LIVE by default (user rule, Jul 2026):
                                   // script lagtay hi direct act kare. Safety
                                   // nets: converted terms kabhi ban nahi hote,
                                   // negatives sirf EXACT [term] hain (surgical,
                                   // koi phrase collateral nahi), aur har ban
                                   // log mein reason ke saath likha jata hai.
                                   // Audit ke liye TRUE kar ke sirf log dekh lein.
  var PROTECT_CONVERTERS = true;   // conversion wali term kabhi ban nahi hogi
  var ALLOW_SHORT_PRODUCT = %%ALLOW_SHORT_PRODUCT%%;  // <=3-word bare product query allowed?
                                   // true for makers/installers ("kitchen cabinets"),
                                   // false for repair/maintenance ("samsung fridge" is a shopper)

  var FORBIDDEN_LOCATIONS = %%FORBIDDEN_LOCATIONS%%;

  var EDU_CAREER = %%EDU_CAREER%%;

  var INFO_DIY = %%INFO_DIY%%;

  var FORBIDDEN_WORDS = %%FORBIDDEN_WORDS%%;

  // Brands, other trades, hire and price words: banned only when the term
  // names none of OUR services ("siemens" vs "siemens dishwasher repair",
  // "electrician" vs "fridge electrician near me").
  var SOFT_FORBIDDEN = %%SOFT_FORBIDDEN%%;

  // This plan's services and their synonyms, any language.
  var OWN_SERVICES = %%OWN_SERVICES%%;

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = %%CONTEXT_WORDS%%;

  var SAFE_ROOTS = %%SAFE_ROOTS%%;

  var PRODUCTS = %%PRODUCTS%%;

  var ACTIONS = %%ACTIONS%%;

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = %%STRONG_ACTIONS%%;

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = %%PROBLEMS%%;
  // Symptom-only rule (Sep 2026): "fridge not cooling", "washing machine not
  // spinning" with NO hire word are people fixing it themselves. Blocked,
  // unless a hard fault says they need a technician ("drum broken").
  var HIRE_WORDS = %%HIRE_WORDS%%;
  var HARD_FAULTS = %%HARD_FAULTS%%;
  // People you hire, any trade: a bare (typo'd) search for one is a lead.
  var PROVIDERS = %%PROVIDERS%%;
  var SYMPTOM_RE = /(^|\s)(not|wont|won't|doesnt|doesn't|stopped|error|code|[a-z]{1,2}\d{1,3}|لا|ما|عطل)(\s|$)/;
  var PRICE_RE = /(^|\s)(price|prices|cost|costs|rate|rates|cheap|cheapest|سعر|اسعار|أسعار|كم)(\s|$)/;
  function isHireOrFault(t) { return !!(matchFuzzy(t, HIRE_WORDS) || matchStrict(t, HARD_FAULTS)); }
  // "washingmachine repair" -> "washing machine repair": glued spellings of
  // our own multi-word products and bid keywords are leads, not junk.
  var GLUE = {};
  PRODUCTS.concat(SAFE_ROOTS).forEach(function (p) {
    p.split(/\s+/).forEach(function (w, i, a) {
      if (i < a.length - 1) GLUE[w + a[i + 1]] = w + " " + a[i + 1];
    });
  });
  // Arabic normaliser (same rules as the keyword tool): one form per word,
  // so "ثلاجة", "الثلاجة", "ثلاجات" all read as the same product.
  function arNorm(w) {
    w = w.replace(/[\u064B-\u0652\u0640]/g, "").replace(/[أإآ]/g, "ا").replace(/ى/g, "ي");
    if (w.length <= 3) return w;
    var pres = ["وال", "بال", "فال", "كال", "لل", "ال"];
    for (var i = 0; i < pres.length; i++) {
      if (w.indexOf(pres[i]) === 0 && w.length - pres[i].length >= 3) { w = w.slice(pres[i].length); break; }
    }
    var sufs = ["ات", "ة", "ه"];
    for (var j = 0; j < sufs.length; j++) {
      var s = sufs[j];
      if (w.slice(-s.length) === s && w.length - s.length >= 3) { w = w.slice(0, -s.length); break; }
    }
    return w;
  }
  function arText(t) {
    return String(t).split(/\s+/).map(function (w) {
      return /[\u0600-\u06FF]/.test(w) ? arNorm(w) : w;
    }).join(" ");
  }
  function arList(l) { return l.map(arText); }
  SAFE_ROOTS = arList(SAFE_ROOTS); PRODUCTS = arList(PRODUCTS); ACTIONS = arList(ACTIONS);
  STRONG_ACTIONS = arList(STRONG_ACTIONS); PROBLEMS = arList(PROBLEMS);
  HIRE_WORDS = arList(HIRE_WORDS); HARD_FAULTS = arList(HARD_FAULTS);
  FORBIDDEN_WORDS = arList(FORBIDDEN_WORDS); EDU_CAREER = arList(EDU_CAREER);
  SOFT_FORBIDDEN = arList(SOFT_FORBIDDEN); OWN_SERVICES = arList(OWN_SERVICES);
  // every single word of a product or service ("lcd screen" -> "screen"):
  // what may follow "replacement"/"spare" when someone is buying the part
  var PART_NOUNS = [];
  PRODUCTS.concat(OWN_SERVICES, CONTEXT_WORDS).forEach(function (p) {
    p.split(/\s+/).forEach(function (w) { if (w.length > 1 && PART_NOUNS.indexOf(w) < 0) PART_NOUNS.push(w); });
  });
  INFO_DIY = arList(INFO_DIY); CONTEXT_WORDS = arList(CONTEXT_WORDS);
  FORBIDDEN_LOCATIONS = arList(FORBIDDEN_LOCATIONS);

  function stripPhrases(t, list) {
    var out = " " + t + " ";
    list.slice().sort(function (a, b) { return b.length - a.length; }).forEach(function (p) {
      if (p.indexOf(" ") !== -1 || p.length >= 4) out = out.split(" " + p + " ").join(" ");
    });
    return out.replace(/\s+/g, " ").trim();
  }
  function normalizeGlued(t) {
    return t.split(/\s+/).map(function (w) { return GLUE[w] || w; }).join(" ");
  }

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = %%FUZZY_ROOTS%%;

  // ============ MATCHERS (Unicode-aware — Arabic/Hindi/any script) ============
  function esc(w) { return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  // JS \W treats Arabic letters as non-word chars, so a plain \W boundary
  // would match INSIDE Arabic words. Use Unicode letter/number classes when
  // the runtime supports them (Google Ads Scripts V8 does); fall back to \W.
  var U_BOUND = "[^\\p{L}\\p{N}_]";
  var UNICODE_OK = true;
  try { new RegExp(U_BOUND, "u"); } catch (e) { UNICODE_OK = false; }

  function boundaryRegex(word) {
    if (UNICODE_OK)
      return new RegExp("(^|" + U_BOUND + ")" + esc(word) + "($|" + U_BOUND + ")", "iu");
    return new RegExp("(^|[\\s\\W_])" + esc(word) + "([\\s\\W_]|$)", "i");
  }

  function splitTokens(text) {
    if (UNICODE_OK) {
      var m = text.match(new RegExp("[\\p{L}\\p{N}_]+", "gu"));
      return m || [];
    }
    return text.split(/[\s\W_]+/);
  }

  // whole-word/phrase boundary match — never inside another word (any script)
  function matchStrict(text, list) {
    for (var i = 0; i < list.length; i++) {
      if (boundaryRegex(list[i]).test(text)) return list[i];
    }
    return null;
  }

  function stripPlural(t) {
    if (t.length > 4 && t.slice(-3) === "ies") return t.slice(0, -3) + "y";
    if (t.length > 3 && t.slice(-2) === "es") return t.slice(0, -2);
    if (t.length > 3 && t.slice(-1) === "s") return t.slice(0, -1);
    // gerunds: "blocking"->"block", "monitoring"->"monitor" — without this a
    // STRONG_ACTIONS entry like "block" never matches the "-ing" form real
    // search terms use, and rule 5 wrongly reads "no service signal" and
    // blocks a genuine buyer query (false negative).
    if (t.length > 6 && t.slice(-3) === "ing") return t.slice(0, -3);
    return t;
  }

  function lev(a, b) {
    var m = a.length, n = b.length;
    if (Math.abs(m - n) > 2) return 99;
    var d = [];
    for (var i = 0; i <= m; i++) d[i] = [i];
    for (var j = 0; j <= n; j++) d[0][j] = j;
    for (i = 1; i <= m; i++)
      for (j = 1; j <= n; j++)
        d[i][j] = Math.min(d[i-1][j] + 1, d[i][j-1] + 1,
                           d[i-1][j-1] + (a.charAt(i-1) === b.charAt(j-1) ? 0 : 1));
    return d[m][n];
  }

  // typo-aware WHOLE-TOKEN match: plurals stripped, distance scales with length
  function matchFuzzy(text, list) {
    var hit = matchStrict(text, list);
    if (hit) return hit;
    var toks = splitTokens(text);
    for (var i = 0; i < list.length; i++) {
      var phrase = list[i];
      if (phrase.indexOf(" ") !== -1 || phrase.length < 5) continue; // fuzzy = single words only
      var base = stripPlural(phrase);
      var maxD = phrase.length >= 9 ? 2 : 1;
      for (var t = 0; t < toks.length; t++) {
        var tok = toks[t];
        if (tok.length < 4) continue;
        var tokBase = stripPlural(tok);
        if (lev(tok, phrase) <= maxD || lev(tokBase, base) <= maxD) return list[i];
      }
    }
    return null;
  }

  // misspelled head-service token anywhere in the term ("carpanter dubai")
  function hasFuzzyRoot(text) {
    var toks = splitTokens(text);
    for (var t = 0; t < toks.length; t++) {
      var tok = toks[t];
      if (tok.length < 5) continue;
      var tokBase = stripPlural(tok);
      for (var r = 0; r < FUZZY_ROOTS.length; r++) {
        var root = FUZZY_ROOTS[r];
        var maxD = root.length >= 9 ? 2 : 1;
        if (lev(tok, root) <= maxD || lev(tokBase, stripPlural(root)) <= maxD)
          return root;
      }
    }
    return null;
  }

  // ============ ENGINE ============
  Logger.log("🛡️ Negative Guard v2 starting (" + (DRY_RUN ? "DRY RUN — no changes" : "LIVE") + ")...");

  // GAQL string literal — escape quotes so a campaign name like
  // "Naseem's Solar" can never break the query syntax
  function gaqlEscape(s) { return s.replace(/\\/g, "\\\\").replace(/'/g, "\\'"); }

  // GAQL's `campaign.name IN (...)` is case-SENSITIVE, so "solar panel cleaning"
  // never matches an account campaign called "Solar Panel Cleaning". Resolve every
  // configured name against the account's own spelling first (case-insensitive,
  // trimmed) and use the account's exact string from here on.
  var resolvedCampaigns = [];
  try {
    var accountNames = {};   // lowercased -> exact name as it exists in the account
    var allRows = AdsApp.search("SELECT campaign.name FROM campaign");
    while (allRows.hasNext()) {
      var acctName = allRows.next().campaign.name;
      accountNames[acctName.toLowerCase().trim()] = acctName;
    }
    for (var cn = 0; cn < CAMPAIGN_NAMES.length; cn++) {
      var wanted = String(CAMPAIGN_NAMES[cn]).toLowerCase().trim();
      var exact = accountNames[wanted];
      if (exact) {
        if (exact !== CAMPAIGN_NAMES[cn])
          Logger.log("ℹ️ Campaign matched case-insensitively: '" + CAMPAIGN_NAMES[cn] +
                     "' -> '" + exact + "'");
        resolvedCampaigns.push(exact);
      } else {
        Logger.log("⚠️ Campaign NOT FOUND in this account: '" + CAMPAIGN_NAMES[cn] + "'");
      }
    }
  } catch (e) {
    Logger.log("⚠️ Could not list account campaigns (" + e + ") — using configured names as-is.");
    resolvedCampaigns = CAMPAIGN_NAMES.slice();
  }

  if (!resolvedCampaigns.length) {
    Logger.log("❌ None of the configured campaign names exist in this account — nothing to do. " +
               "Check CAMPAIGN_NAMES at the top of the script.");
    return;
  }

  var campaignList = resolvedCampaigns.map(function (c) { return gaqlEscape(c); }).join("','");

  var query =
    "SELECT search_term_view.search_term, metrics.impressions, metrics.clicks, " +
    "metrics.conversions, ad_group.id " +
    "FROM search_term_view " +
    "WHERE campaign.name IN ('" + campaignList + "') " +
    "AND metrics.impressions >= " + MIN_IMPRESSIONS + " " +
    "AND segments.date DURING " + DATE_RANGE;

  var rows = AdsApp.search(query);
  var banned = 0, allowed = 0, rowCount = 0;
  var forbiddenRootHits = {};
  var seen = {};

  while (rows.hasNext()) {
    rowCount++;
    var row = rows.next();
    var rawTerm = row.searchTermView.searchTerm;
    var term = normalizeGlued(arText(rawTerm.toLowerCase().trim()));
    var adGroupId = row.adGroup.id;
    var conversions = Number(row.metrics.conversions || 0);

    // in-run dedup: same term can surface for multiple ad groups/rows
    var dedupKey = adGroupId + "||" + term;
    if (seen[dedupKey]) continue;
    seen[dedupKey] = true;

    var isSafe = false, reason = "";

    // service signals computed once — reused by the context-word rule
    var fuzzyRootHit = hasFuzzyRoot(term);
    var safeHit = matchFuzzy(term, SAFE_ROOTS);
    // Action words are read from the term WITHOUT our product names: in
    // "washing machine not spinning" the "washing" is the product, not a
    // wash service, and it was passing symptom queries as service intent.
    // Our own multi-word services go first: PRODUCTS holds single tokens,
    // and "washing" is also an action word, so "washing machine price"
    // read as a wash service.
    var ownHit = matchFuzzy(term, OWN_SERVICES);
    var termNoProd = stripPhrases(stripPhrases(term, OWN_SERVICES), PRODUCTS);
    var actionHit = matchFuzzy(termNoProd, ACTIONS);
    var problemHit = matchFuzzy(term, PROBLEMS);
    var strongHit = matchFuzzy(termNoProd, STRONG_ACTIONS);
    // "replacement screen", "spare drum": a part-swap word BEFORE a product
    // names the part being bought; "screen replacement cost" is the job.
    var partShop = false;
    var tokList = splitTokens(term);
    for (var pi = 0; pi < tokList.length - 1; pi++) {
      if (/^(replacement|spare|spares)$/.test(tokList[pi]) &&
          matchStrict(tokList[pi + 1], PART_NOUNS)) partShop = true;
    }
    if (partShop && matchFuzzy(stripPhrases(termNoProd, ["replacement", "replace", "replacing", "spare", "spares"]),
                               STRONG_ACTIONS)) partShop = false;
    // The PERSON you hire is a service signal of its own: "plumber ballard",
    // "plumber seattle cost" are buyers with no repair verb in them. Read on
    // the raw term — for a trade, "plumber" is also one of the PRODUCTS that
    // termNoProd strips out.
    var providerHit = matchFuzzy(term, PROVIDERS);
    var serviceSignal = !!(fuzzyRootHit || safeHit || problemHit || strongHit || providerHit);

    // 0️⃣ converted terms are sacred
    if (PROTECT_CONVERTERS && conversions > 0) {
      isSafe = true; reason = "converted (" + conversions + ")";
    } else {
      // 1️⃣ wrong location
      var badLoc = matchStrict(term, FORBIDDEN_LOCATIONS);
      if (badLoc) {
        reason = "Forbidden Location: [" + badLoc + "]";
      } else {
        // 2️⃣ education / career / tools / specs — not a customer
        var edu = matchStrict(term, EDU_CAREER);
        if (edu) {
          reason = "Education/Career/Spec: [" + edu + "]";
        } else {
          // 3️⃣ info / DIY intent
          var diy = matchStrict(term, INFO_DIY);
          if (diy) {
            reason = "Info/DIY: [" + diy + "]";
          } else {
            // 4️⃣ forbidden words (typo-aware, whole tokens only)
            var bad = matchFuzzy(term, FORBIDDEN_WORDS);
            var softBad = bad ? null : matchFuzzy(term, SOFT_FORBIDDEN);
            if (bad) {
              reason = "Forbidden Word: [" + bad + "]";
              forbiddenRootHits[bad] = (forbiddenRootHits[bad] || 0) + 1;
            } else if (softBad && !ownHit) {
              // 4️⃣ soft word with none of our services ("siemens", "ac repair")
              reason = "Forbidden Word, no service of ours: [" + softBad + "]";
            } else if (partShop && !providerHit) {
              // 4️⃣ part shopping ("replacement screen for 55 inch tv")
              reason = "Part shopping (replacement/spare before the product)";
            } else if (!actionHit && !strongHit && !providerHit && !isHireOrFault(term)
                       && PRICE_RE.test(term)) {
              // 4️⃣a product price, no service word ("fridge price")
              reason = "Product price, no service word";
            } else if ((problemHit || SYMPTOM_RE.test(term)) && !actionHit && !strongHit && !providerHit
                       && !matchFuzzy(term, HIRE_WORDS) && !matchStrict(term, HARD_FAULTS)
                       && !safeHit) {
              // 4️⃣b symptom only — research, not a hire
              reason = "Symptom only, no hire word (DIY/info): [" + problemHit + "]";
            } else {
              // 5️⃣ ambiguous context word without any service signal
              var ctx = matchFuzzy(term, CONTEXT_WORDS);
              if (ctx && !serviceSignal) {
                reason = "Context word (shopping, no service signal): [" + ctx + "]";
              }
              // 6️⃣a misspelled head service token → a lead ONLY when it
              // comes WITH an action/problem word. A bare fuzzy hit is too
              // loose: real English words sit 1 edit from service roots
              // ("plumper"→plumber, "lending"→landing) and were getting a
              // free ALLOW here (false positive, wasted spend).
              else if (fuzzyRootHit && !safeHit && (actionHit || problemHit || strongHit)) {
                isSafe = true; reason = "fuzzy root [" + fuzzyRootHit + "] + action/problem signal";
              }
              // 6️⃣b bare typo'd service search ("plumbr", "plumbrs") —
              // 1-2 words with nothing else in them is still a lead
              // ... but only when the root is the PERSON you hire ("plumbr
              // dubai") or the business makes the product. For a repair
              // business a bare product root is a shopper: "samsung fridge".
              else if (fuzzyRootHit && !safeHit && splitTokens(term).length <= 2
                       && (ALLOW_SHORT_PRODUCT || matchFuzzy(fuzzyRootHit, PROVIDERS))) {
                isSafe = true; reason = "fuzzy root [" + fuzzyRootHit + "] (short bare query)";
              }
              // 7️⃣ safe roots (our own keywords + known-good phrases)
              else if (safeHit) {
                isSafe = true;
              } else {
                // 8️⃣ product + (action OR problem signal). A context word
                // that SURVIVED rule 5 (service signal present) counts as a
                // product too — "wooden door installation" is a job, and
                // "door" is its product.
                var prod = matchFuzzy(term, PRODUCTS) || ownHit || (ctx ? ctx : null);
                if (prod && (actionHit || problemHit || providerHit)) {
                  isSafe = true;
                }
                // 9️⃣ short bare product query ("kitchen cabinets")
                else if (prod && ALLOW_SHORT_PRODUCT && splitTokens(term).length <= 3) {
                  isSafe = true; reason = "short product query [" + prod + "]";
                }
                else if (prod) {
                  reason = "Product [" + prod + "] but NO action/problem word";
                } else {
                  reason = "No relevant product or safe root";
                }
              }
            }
          }
        }
      }
    }

    if (isSafe) { allowed++; }
    else {
      banned++;
      if (DRY_RUN) {
        Logger.log("🚫 WOULD BAN: [" + rawTerm + "] | " + reason);
      } else {
        addNegative(adGroupId, rawTerm, reason);
      }
    }
  }

  // Phrase-negative suggestions: same forbidden root hit 3+ times today
  for (var root in forbiddenRootHits) {
    if (forbiddenRootHits[root] >= 3) {
      Logger.log("💡 SUGGESTION: root '" + root + "' hit " + forbiddenRootHits[root] +
                 " times — consider a campaign-level PHRASE negative: \"" + root + "\"");
    }
  }

  if (rowCount === 0) Logger.log("⚠️ 0 search terms returned (data may not be synced yet).");
  Logger.log("✅ Done. " + rowCount + " terms | " + allowed + " allowed | " + banned +
             (DRY_RUN ? " would be banned (DRY RUN)" : " banned"));

  function addNegative(id, term, reason) {
    // Google's negative keyword limits: max 10 words / 80 chars — long
    // voice-search terms can't be exact negatives, log instead of erroring
    if (term.length > 80 || splitTokens(term).length > 10) {
      Logger.log("⚠️ SKIP (too long for an exact negative): [" + term + "] | " + reason);
      return;
    }
    try {
      var it = AdsApp.adGroups().withIds([id]).get();
      if (it.hasNext()) {
        it.next().createNegativeKeyword("[" + term + "]");  // EXACT — surgical
        Logger.log("🚫 BANNED: [" + term + "] | " + reason);
      }
    } catch (e) { Logger.log("⚠️ Add failed [" + term + "]: " + e); }
  }
}
"""


def js_list(items, per_line=6, lower=True):
    """Render a python list as a compact JS array literal.

    lower=False keeps the original casing — campaign names must go out
    verbatim, because GAQL's `campaign.name IN (...)` is case-sensitive.
    """
    if lower:
        items = sorted(set(str(i).lower().strip() for i in items if str(i).strip()))
    else:
        seen, items = set(), [str(i).strip() for i in items if str(i).strip()]
        items = [i for i in items if not (i.lower() in seen or seen.add(i.lower()))]
    if not items:
        return "[]"
    lines = []
    for i in range(0, len(items), per_line):
        # ensure_ascii=False: Arabic/Hindi entries stay readable (not \uXXXX)
        lines.append(", ".join(json.dumps(x, ensure_ascii=False) for x in items[i:i + per_line]))
    return "[\n    " + ",\n    ".join(lines) + "\n  ]"


HIRE_WORDS_JS = ["near me", "nearby", "emergency", "urgent", "company", "technician",
                 "service", "services", "call", "book",
                 "shop", "center", "centre", "today", "now", "open", "hire", "expert",
                 "specialist", "mechanic", "engineer", "at home", "same day",
                 "تصليح", "اصلاح", "صيانة", "فني", "فنيين", "شركة", "مركز", "قريب",
                 "طوارئ", "عاجل", "رقم", "في المنزل"]
HARD_FAULTS_JS = ["broken", "broke", "burst", "damaged", "dead", "cracked", "sparking",
                  "smoke", "burnt", "burned", "shock", "flooding", "failed", "tripping",
                  "مكسور", "مكسورة", "خربان", "خربانة", "محروق", "محروقة", "معطل", "معطلة"]

PROVIDERS_JS = ["plumber", "electrician", "carpenter", "handyman", "locksmith", "painter",
                "roofer", "mechanic", "technician", "cleaner", "exterminator", "gardener",
                "landscaper", "welder", "mason", "tiler", "glazier", "installer", "contractor",
                "builder", "fitter", "upholsterer", "tailor", "mover", "movers",
                "سباك", "كهربائي", "نجار", "فني", "دهان", "حداد", "مصلح"]

CAMPAIGN_NEGATIVES_CSV = "google_ads_campaign_negatives.csv"


def negatives_from_excluded(strategy, bid_keywords):
    """The account's OWN measured junk, as campaign negatives.

    analyze_with_claude.py already puts every informational/question query and
    every keyword it judged irrelevant, junk or competitor-brand for THIS
    business into `seo_content_keywords`. That list is real search demand,
    measured by the Planner, specific to this niche and this city -- a far
    better negative list than anything generic, and it was only ever used to
    fill a report.

    A negative PHRASE blocks any query containing that word sequence, so this
    is the dangerous direction and the filtering is deliberately strict. A
    candidate survives only if:

      1. it clears filter_forbidden() -- it does not appear inside any bid
         keyword. "ac repair" would otherwise wipe out the whole account.
      2. it has 3+ tokens. Two-word phrases built from this vocabulary are one
         modifier away from a term we bid on; the universal list is where short
         blunt tokens like "jobs" belong, because those are junk in any
         phrasing.
      3. it introduces at least one token the bid keywords never use. That new
         token IS the junk signal -- "how", "salary", "used", "diy". A phrase
         made entirely of our own words is our own vocabulary rearranged, and
         blocking it blocks us.

    Rule 3 is the one that matters. Without it "cost of ac repair in dubai"
    survives rules 1 and 2 and then blocks a query we are paying for.
    """
    cands = []
    for k in (strategy.get("seo_content_keywords") or []):
        kw = str(k.get("keyword", "")).strip().lower()
        if kw:
            cands.append(kw)
    junk = plan_junk_keywords()
    if junk is not None:
        # plan mode: only what Stage 2.7 excluded for a JUNK reason
        before = len(cands)
        cands = [c for c in cands if c in junk]
        if before - len(cands):
            print(f"   🛡️ Excluded-keyword negatives: {before - len(cands)} skipped — excluded "
                  "for a non-junk reason (no service match, symptom, bare product, info)")
    if not cands:
        return []
    kept = filter_forbidden(cands, list(bid_keywords) + plan_buyer_keywords(), "excluded-keyword")
    bid_tokens = {t for kw in bid_keywords for t in tokens_of(kw)}
    out, short, no_signal = [], 0, 0
    for kw in kept:
        toks = tokens_of(kw)
        if len(toks) < 3:
            short += 1
            continue
        if not (set(toks) - bid_tokens):
            no_signal += 1
            continue
        out.append(kw)
    if short or no_signal:
        print(f"   🛡️ Excluded-keyword negatives: dropped {short} too short (<3 words) "
              f"and {no_signal} built only from our own bid vocabulary")
    return sorted(set(out))


def pack_negatives(strategy, bid_keywords):
    """Deterministic niche packs (negative_packs.py): jobs/cv/salary, manual/
    pdf, second hand/used, supplier/wholesale/spare parts, retail chains —
    chosen by niche, with the niche's buyer words protected, then run through
    the same bid-keyword collision filter as everything else. Present even
    when the Claude call fails."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import negative_packs
    seeds = [s.strip() for s in os.environ.get("SEED_KEYWORDS", "").split(",") if s.strip()]
    svc = [g.get("name", "") for g in strategy.get("ad_groups", [])]
    block, _allow, packs = negative_packs.build(NICHE_DESCRIPTION, seeds + svc)
    # the wrong-job phrases (aggregators, the niche's "exclude" list) are
    # campaign negatives too, not only a Stage 2.7 selection rule
    block += negative_packs.exclusions(NICHE_DESCRIPTION, seeds + svc)
    kept = filter_forbidden(block, list(bid_keywords) + plan_buyer_keywords(), "niche-pack")
    print(f"   📦 Negative packs: universal + {packs or ['(no niche pack matched)']} "
          f"-> {len(kept)} campaign negatives after collision filter "
          f"(BUSINESS_MODEL={os.environ.get('BUSINESS_MODEL', 'service') or 'service'})")
    return kept


def write_campaign_negatives(campaigns, block_lists):
    """The same block lists, added to the account BEFORE the first click.

    The guard script is reactive by design: it reads search_term_view and
    negatives what already came through, so every junk query -- a job seeker,
    a supplier, someone after a second-hand unit -- is paid for once before it
    is stopped. Nothing recovers that spend.

    These lists are junk INTENT, not siloing, so they belong to the whole
    campaign, not to one ad group. (The ad-group negatives that
    analyze_with_claude.py writes are the opposite thing: each group gets the
    other groups' distinctive terms, so one query matches one group.)

    Claude builds them per niche and filter_forbidden() has already dropped
    anything colliding with a bid keyword, so the same guarantee that keeps the
    script from blocking real traffic applies here unchanged.

    context_product_words is deliberately excluded. Those are ambiguous single
    words -- "fitting", "handle", "door" -- and the script blocks them ONLY when
    no service signal appears with them. Flat campaign negatives have no such
    condition, so adding them would kill "door handle repair" along with "door
    handle". They stay with the script, which can tell the two apart.
    """
    rows, seen = [], set()
    for label, terms in (("packs", block_lists.get("packs") or []),
                         ("locations", block_lists.get("locations") or []),
                         ("forbidden", block_lists.get("forbidden") or []),
                         ("edu", block_lists.get("edu") or []),
                         ("info_diy", block_lists.get("info_diy") or []),
                         # Second list: this account's own measured junk demand,
                         # not a generic one. See negatives_from_excluded.
                         ("excluded", block_lists.get("excluded") or [])):
        for t in terms:
            t = str(t).strip().lower()
            if t and t not in seen:
                seen.add(t)
                rows.append(t)
    rows, dropped = campaign_negative_gate(rows)
    if dropped:
        print(f"   🛡️ Campaign-negative gate: {sum(len(x) for x in dropped.values())} phrase(s) "
              "NOT added — each would block buyers:")
        for reason, terms in sorted(dropped.items(), key=lambda x: -len(x[1])):
            print(f"      {reason}: {len(terms)} — e.g. {', '.join(terms[:5])}")
    if not rows:
        return 0
    with open(CAMPAIGN_NEGATIVES_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        # Same columns as google_ads_editor_negatives.csv; a blank Ad Group is
        # what makes the Editor read the row as campaign level.
        w.writerow(["Campaign", "Ad Group", "Keyword", "Criterion Type"])
        for c in campaigns:
            for t in rows:
                w.writerow([c, "", t, "Negative Phrase"])
    print(f"✅ {CAMPAIGN_NEGATIVES_CSV}: {len(rows)} campaign-level negatives "
          f"x {len(campaigns)} campaign(s) — blocks the junk BEFORE it is paid for. "
          f"Import into the Editor's 'Keywords, Negative' section.")
    return len(rows)


_SERVICE_SEED_RE = re.compile(
    r"\b(repair|repairs|fix|fixing|maintenance|servicing|service|cleaning|clean|unblock\w*|"
    r"pest|inspection|technician|mechanic|plumber|electrician|locksmith|"
    r"تصليح|اصلاح|صيانة|تنظيف|فني)\b", re.IGNORECASE)


def allow_short_product():
    """Rule 9 of the guard ("<= 3-word bare product query -> ALLOW") was made
    for businesses that MAKE or INSTALL the product: "kitchen cabinets" is a
    buyer. For a repair/maintenance business the same query — "samsung
    fridge", "lg washing machine" — is a shopper. Decided from the seeds and
    the niche (any business, no list of trades to keep current);
    ALLOW_SHORT_PRODUCT=on|off overrides."""
    forced = os.environ.get("ALLOW_SHORT_PRODUCT", "").strip().lower()
    if forced in ("on", "yes", "true", "1"):
        return True
    if forced in ("off", "no", "false", "0"):
        return False
    seeds = [s for s in os.environ.get("SEED_KEYWORDS", "").split(",") if s.strip()]
    text = " ".join(seeds) + " " + NICHE_DESCRIPTION
    return not _SERVICE_SEED_RE.search(text)


def plan_buyer_keywords():
    """Every Planner row Stage 2.7 filed under one of OUR services and did
    not judge junk — bid on or not. A negative must never sit inside one of
    these: run 0d732cac shipped campaign negatives "electrician", "mini
    fridge", "dish machine repair" and "led backlight repair", each of which
    blocked a buyer ("fridge electrician near me", "mini fridge repair") that
    the bid-keyword-only collision check could not see. Empty without a plan."""
    try:
        with open("ad_group_plan.json", encoding="utf-8") as f:
            plan = json.load(f)
        with open("scored_keywords.json", encoding="utf-8") as f:
            rows = json.load(f)["keywords"]
    except Exception:
        return []
    ids = {i for g in plan.get("ad_groups", [])
           for i in (g.get("all_keyword_ids") or g.get("keyword_ids") or [])}
    return sorted({str(r["keyword"]).lower() for r in rows if r.get("id") in ids})


# Stage 2.7 reasons that make an excluded keyword a NEGATIVE. "matches no
# service" is a gap in our own synonym list ("dish machine repair" is a
# dishwasher job), "symptom only" is the FAQ/test pool, "bare product" and
# "informational" are not worth bidding on but not worth blocking either.
NEGATIVE_REASONS = ("wrong location", "diy/info question", "non-service intent",
                    "product price")


def plan_junk_keywords():
    """Excluded keywords whose Stage 2.7 reason is real junk; None = no plan."""
    try:
        with open("ad_group_plan.json", encoding="utf-8") as f:
            ex = json.load(f).get("excluded")
    except Exception:
        return None
    if ex is None:
        return None
    return {str(e.get("keyword", "")).lower() for e in ex
            if str(e.get("why", "")).startswith(NEGATIVE_REASONS)}


def _plan_classifier():
    """Stage 2.7's classifier with this plan's snapshot loaded, plus the
    plan's services. (None, None) without a plan (legacy runs)."""
    try:
        with open("ad_group_plan.json", encoding="utf-8") as f:
            plan = json.load(f)
    except Exception:
        return None, None
    if not plan.get("classifier"):
        return None, None
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import service_architecture as vtsa
    try:
        vtsa.restore_classifier(plan["classifier"])
    except (KeyError, TypeError) as e:
        # an older or partial snapshot: legacy behaviour, never a crash
        print(f"   ⚠️ plan classifier snapshot incomplete ({e}) — plan-aware filters off")
        return None, None
    return vtsa, plan.get("services") or []


# Words that are junk ON THEIR OWN but a buyer's detail next to a service:
# a one-word phrase negative of these blocks "55 inch tv screen repair",
# "8 kg washing machine repair", "fridge repair reviews". The guard judges
# them per search term, with the service signal in view.
_CONTEXT_SINGLE = {"size", "kg", "inch", "inches", "capacity", "litre", "liter",
                   "review", "reviews"}
# A part-swap verb is a hire word only AFTER the thing being swapped ("55 inch
# tv screen replacement cost" — have it done). BEFORE a noun it names the part
# being bought ("replacement screen for 50 inch tv", "replace led backlight").
_PART_VERBS = {"replacement", "replace", "replacing"}
_HIRE_TAIL = {"near", "me", "estimate", "service", "services", "company", "shop", "cheap"}


def _part_swap_is_hire(words, v):
    """True when a part-swap verb is followed by nothing but price, size,
    place or near-me words ("... screen replacement price in dubai", "lcd
    screen replacement 55 inch"), or asks the price of the job ("cost of
    replacing led tv screen")."""
    price = set(v.PRICE_TOKENS)
    tail_ok = price | _HIRE_TAIL | _CONTEXT_SINGLE | v._loc_tokens() | {"in", "at", "for"}
    for i, w in enumerate(words):
        if w not in _PART_VERBS:
            continue
        if price & set(words[:i]):
            return True
        if i > 0 and all(x in tail_ok or x.isdigit() for x in words[i + 1:]):
            return True
    return False


def campaign_negative_gate(terms):
    """The last check before a phrase becomes a CAMPAIGN-level negative —
    which blocks every query containing it, for every ad group, forever.

    Run 0d732cac shipped 607 of them; 195 blocked buyers. The rule, for any
    business and any language, using the plan's own classifier:
      KEEP  a phrase that is junk by itself: jobs, courses, DIY, a wrong
            location, an aggregator, a wrong-job phrase, or another trade
            with none of our services in it ("ac repair", "plumber").
      DROP  a symptom ("samsung dryer not working" also blocks "... repair");
            a one-word size/review word; a price modifier with no product
            ("price in dubai" blocks "washing machine repair price in dubai");
            a brand with a repair word, or a bare brand ("siemens"); anything
            with a hire word (repair, fix, service, technician, تصليح, صيانة)
            and no junk signal ("fridge electrician near me", "تصليح شاشات
            تلفاز"); a part swap AFTER its part ("tv screen replacement
            cost"); a kept word that sits inside any phrase dropped above
            ("electrician" inside "fridge electrician near me").
      KEEP  a part swap BEFORE its part: "replacement screen for 50 inch tv".
    Without a plan nothing is dropped (legacy behaviour).
    -> (kept, {reason: [dropped]})"""
    v, services = _plan_classifier()
    if v is None:
        return list(terms), {}
    other = {x for fam in v._OTHER_FAMILIES for x in ({v.norm_phrase(m) for m in fam} | set(fam)) if x}
    kept, dropped = [], {}

    def _drop(reason, t):
        dropped.setdefault(reason, []).append(t)

    for t in terms:
        text = " ".join(v.toks(t))
        ts = set(text.split())
        if not ts:
            continue
        why = v.junk_reason(t) or ""
        ours = v.assign_service(t, services) is not None
        if why.startswith("symptom only"):
            _drop("symptom (also blocks the buyer version)", t)
            continue
        if len(ts) == 1 and ts & _CONTEXT_SINGLE:
            _drop("one-word size/review word", t)
            continue
        if why.startswith("product price") and not ours:
            _drop("price modifier with no product", t)
            continue
        other_trade = (not ours) and any(v.has_phrase(text, x) for x in other)
        if (why and not why.startswith("no service intent")) or other_trade:
            kept.append(t)
            continue
        hire = ts & set(v.HIRE_WORDS)
        real_hire = hire - _PART_VERBS
        if not real_hire and _part_swap_is_hire(text.split(), v):
            real_hire = hire & _PART_VERBS
        if v.brands_in(text) and (real_hire or len(ts) <= 2):
            _drop("brand", t)
            continue
        if real_hire:
            _drop("hire word, no junk signal", t)
            continue
        kept.append(t)

    # A bare word kept above still blocks every buyer phrase it sits inside:
    # "electrician" kills "fridge electrician near me" though that phrase was
    # itself dropped as a buyer. Judged against this gate's own buyer verdicts.
    buyers = [" ".join(v.toks(b)) for r in ("hire word, no junk signal", "brand")
              for b in dropped.get(r, [])]
    still = []
    for t in kept:
        text = " ".join(v.toks(t))
        if any(text != b and v.has_phrase(b, text) for b in buyers):
            _drop("sits inside a buyer phrase", t)
        else:
            still.append(t)
    return still, dropped


# Roman-Urdu PRICE words are a buyer's detail next to a service ("washing
# machine repair ka price"); the buy words beside them are not.
_SOFT_RU = {"ka dam", "ki qeemat", "kitna hai", "kitne ka", "ka price", "sasta"}


def guard_word_split(words):
    """FORBIDDEN_WORDS for the guard -> (hard, soft, own_services).

    The guard bans a search term the moment a forbidden word is in it, BEFORE
    it looks for a service. Run 0d732cac's guard banned "siemens dishwasher
    repair" (a bid keyword), "whirlpool fridge repair", "fridge electrician
    near me" and "كهربائي غسالات" that way. Split by the plan's classifier:
      hard  junk on its own — jobs, aggregators, buy/used, a wrong-job
            phrase ("hair dryer", "dryer vent"): banned in any query
      soft  a brand, another trade, a hire or provider word, a price word:
            banned only when the query names none of our services
    own_services: the plan's services and their synonyms, any language.
    Without a plan every word is hard and own_services is empty (legacy)."""
    v, services = _plan_classifier()
    if v is None:
        return list(words), [], []
    other = {x for fam in v._OTHER_FAMILIES for x in ({v.norm_phrase(m) for m in fam} | set(fam)) if x}
    soft_tokens = set(v.HIRE_WORDS) | set(v.PROVIDER_NOUNS) | set(v.PRICE_TOKENS)
    hard, soft = [], []
    for w in words:
        text = " ".join(v.toks(w))
        why = v.junk_reason(w) or ""
        real_junk = why and not why.startswith(("no service intent", "symptom only", "product price"))
        if (real_junk and w not in _SOFT_RU) or w in UNIVERSAL_FORBIDDEN:
            hard.append(w)
        elif (w in _SOFT_RU or v.brands_in(text) or set(text.split()) & soft_tokens
              or any(v.has_phrase(text, x) for x in other)):
            soft.append(w)
        else:
            hard.append(w)
    own = []
    for s in services:
        own += [a for a in [s.get("name", "")] + list(s.get("aliases") or []) if a]
    own = list(dict.fromkeys(a.lower() for a in own if not a.endswith(")")))
    return hard, soft, own


def plan_block_lists():
    """What Stage 2.7 decided is NOT this business, from its classifier
    snapshot in ad_group_plan.json: wrong locations (any country — the geo
    lookup, data-found other towns), other trades, wrong-job phrases. The
    guard enforces the same rules the selection used; without this a search
    like "dyson hair dryer repair" passed the guard on the safe root "dryer
    repair". Empty when there is no plan (legacy runs)."""
    try:
        with open("ad_group_plan.json", encoding="utf-8") as f:
            snap = json.load(f).get("classifier") or {}
    except Exception:
        return [], []
    locs = [w for w in snap.get("WRONG_LOCS", []) if " " in w or len(w) > 3]
    words = list(snap.get("JUNK_PHRASES", [])) + list(snap.get("OTHER_SERVICE_PHRASES", []))
    return list(dict.fromkeys(locs)), [w for w in dict.fromkeys(words) if len(w) > 1]


def render_script(campaigns, bid_keywords, products, fuzzy_roots, niche):
    """Merge universal + niche lists (collision-filtered) and render the JS.
    Pure function — testable without the Claude API."""
    def _lst(key):
        return [str(x).lower() for x in (niche.get(key) or [])]

    plan_locs, plan_words = plan_block_lists()
    # block lists are checked against every buyer row of the plan, not only
    # the (much shorter) bid list
    protect = list(bid_keywords) + plan_buyer_keywords()
    forbidden = filter_forbidden(
        _lst("forbidden_words") + UNIVERSAL_PRICE_SHOPPING_RU + UNIVERSAL_FORBIDDEN + plan_words,
        protect, "forbidden")
    hard_forbidden, soft_forbidden, own_services = guard_word_split(forbidden)
    edu = filter_forbidden(
        UNIVERSAL_EDU_CAREER + _lst("edu_career_words"), protect, "edu/career")
    info_diy = filter_forbidden(
        UNIVERSAL_INFO_DIY + _lst("info_diy_words"), protect, "info/DIY")
    forbidden_locations = filter_forbidden(
        list(dict.fromkeys(_lst("forbidden_locations") + plan_locs)), protect, "location")
    context_words = _lst("context_product_words")
    problems = UNIVERSAL_PROBLEM_SIGNALS + _lst("problem_signals")
    safe_roots = bid_keywords + _lst("extra_safe_roots")
    all_products = products + _lst("extra_products")
    actions = UNIVERSAL_ACTIONS + _lst("extra_actions")
    strong_actions = UNIVERSAL_STRONG_ACTIONS + _lst("extra_actions")

    js = (JS_TEMPLATE
          .replace("%%BUSINESS%%", BUSINESS_NAME or "Universal")
          .replace("%%LOCATION%%", TARGET_LOCATION or "any location")
          .replace("%%CAMPAIGNS%%", js_list(campaigns, 2, lower=False))
          .replace("%%FORBIDDEN_LOCATIONS%%", js_list(forbidden_locations))
          .replace("%%EDU_CAREER%%", js_list(edu, 4))
          .replace("%%INFO_DIY%%", js_list(info_diy, 4))
          .replace("%%FORBIDDEN_WORDS%%", js_list(hard_forbidden))
          .replace("%%SOFT_FORBIDDEN%%", js_list(soft_forbidden))
          .replace("%%OWN_SERVICES%%", js_list(own_services))
          .replace("%%CONTEXT_WORDS%%", js_list(context_words))
          .replace("%%SAFE_ROOTS%%", js_list(safe_roots, 4))
          .replace("%%PRODUCTS%%", js_list(all_products))
          .replace("%%ACTIONS%%", js_list(actions))
          .replace("%%STRONG_ACTIONS%%", js_list(strong_actions))
          .replace("%%PROBLEMS%%", js_list(problems, 4))
          .replace("%%HIRE_WORDS%%", js_list(HIRE_WORDS_JS))
          .replace("%%HARD_FAULTS%%", js_list(HARD_FAULTS_JS))
          .replace("%%PROVIDERS%%", js_list(PROVIDERS_JS))
          .replace("%%ALLOW_SHORT_PRODUCT%%", "true" if allow_short_product() else "false")
          .replace("%%FUZZY_ROOTS%%", js_list(fuzzy_roots)))

    stats = {
        "safe_roots": len(set(safe_roots)), "forbidden": len(forbidden),
        "edu": len(edu), "info_diy": len(info_diy),
        "context": len(set(context_words)), "problems": len(set(problems)),
        "locations": len(set(forbidden_locations)),
        "products": len(set(all_products)), "actions": len(set(actions)),
        "fuzzy_roots": list(fuzzy_roots),
        # The block lists themselves, so they can ALSO be added to the account
        # up front as campaign negatives instead of only being enforced by the
        # script after the click. context_words is deliberately NOT here -- see
        # write_campaign_negatives.
        "block_lists": {"forbidden": list(forbidden), "edu": list(edu),
                        "info_diy": list(info_diy),
                        "locations": list(dict.fromkeys(forbidden_locations))},
    }
    return js, stats


def main():
    if not os.path.exists(STRATEGY_FILE):
        print(f"❌ {STRATEGY_FILE} not found — run analyze_with_claude.py first.")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is missing.")
        sys.exit(1)

    with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
        strategy = json.load(f)

    bid_keywords, products, fuzzy_roots = build_lists(strategy)
    print(f"Building negative-guard script v2: {len(bid_keywords)} safe bid keywords, "
          f"{len(products)} product tokens, fuzzy roots: {fuzzy_roots}")

    niche = ask_claude(bid_keywords, products)

    campaigns = [c["name"] for c in strategy.get("campaigns", [])] or ["UPDATE_CAMPAIGN_NAME"]
    js, stats = render_script(campaigns, bid_keywords, products, fuzzy_roots, niche)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(js)

    print(f"✅ {OUTPUT_FILE}: {len(campaigns)} campaigns | {stats['safe_roots']} safe roots | "
          f"{stats['forbidden']} forbidden | {stats['edu']} edu/career | "
          f"{stats['info_diy']} info/DIY | {stats['context']} context words | "
          f"{stats['problems']} problem signals | {stats['locations']} locations | "
          f"{stats['products']} products | {stats['actions']} actions")
    print("   Paste into Google Ads > Tools > Scripts + hourly schedule — LIVE by default "
          "(DRY_RUN=false); converted terms are always protected.")

    _bl = dict(stats.get("block_lists") or {})
    _bl["excluded"] = negatives_from_excluded(strategy, bid_keywords)
    _bl["packs"] = pack_negatives(strategy, bid_keywords)
    write_campaign_negatives(campaigns, _bl)


if __name__ == "__main__":
    main()
