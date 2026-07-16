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
    "near me", "nearby", "local", "in my area",
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
    "custom", "bespoke", "made to measure", "made to order", "tailor made",
    "design", "designer", "build", "builder", "making", "maker",
    "renovation", "renovate", "remodel", "remodeling", "refurbish",
    "restore", "restoration", "unblock", "unclog", "inspect", "inspection",
    "detect", "detection", "mount", "mounting", "fitted", "fabrication",
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
]

# Searcher wants to do it themselves / just wants information.
UNIVERSAL_INFO_DIY = [
    "how to", "diy", "do it yourself", "tutorial", "youtube", "manual",
    "instructions", "difference between", "what causes", "wikipedia",
    # Roman-Urdu / Hindi DIY
    "khud se", "khud lagana", "khud banana", "ghar par kaise", "ki setting",
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
  // ⚙️ CONFIG — sirf campaign name check karein, baqi sab data-generated hai
  var CAMPAIGN_NAMES = %%CAMPAIGNS%%;
  var DATE_RANGE = "TODAY";        // TODAY | YESTERDAY | LAST_7_DAYS
  var MIN_IMPRESSIONS = 0;
  var DRY_RUN = true;              // ⚠️ pehle 2-3 din TRUE rakhein — sirf log karega.
                                   // Log theek lagay to false kar dein.
  var PROTECT_CONVERTERS = true;   // conversion wali term kabhi ban nahi hogi
  var ALLOW_SHORT_PRODUCT = true;  // "kitchen cabinets" type <=3-word product query allow

  var FORBIDDEN_LOCATIONS = %%FORBIDDEN_LOCATIONS%%;

  var EDU_CAREER = %%EDU_CAREER%%;

  var INFO_DIY = %%INFO_DIY%%;

  var FORBIDDEN_WORDS = %%FORBIDDEN_WORDS%%;

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
  var campaignList = CAMPAIGN_NAMES.map(function (c) { return gaqlEscape(c); }).join("','");

  // sanity: warn about campaign names that don't exist in the account
  try {
    var found = {};
    var cRows = AdsApp.search(
      "SELECT campaign.name FROM campaign WHERE campaign.name IN ('" + campaignList + "')");
    while (cRows.hasNext()) found[cRows.next().campaign.name] = true;
    for (var cn = 0; cn < CAMPAIGN_NAMES.length; cn++) {
      if (!found[CAMPAIGN_NAMES[cn]])
        Logger.log("⚠️ Campaign NOT FOUND (check exact name): '" + CAMPAIGN_NAMES[cn] + "'");
    }
  } catch (e) { /* older runtimes — non-fatal */ }

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
    var term = rawTerm.toLowerCase().trim();
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
    var actionHit = matchFuzzy(term, ACTIONS);
    var problemHit = matchFuzzy(term, PROBLEMS);
    var strongHit = matchFuzzy(term, STRONG_ACTIONS);
    var serviceSignal = !!(fuzzyRootHit || safeHit || problemHit || strongHit);

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
            if (bad) {
              reason = "Forbidden Word: [" + bad + "]";
              forbiddenRootHits[bad] = (forbiddenRootHits[bad] || 0) + 1;
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
              else if (fuzzyRootHit && !safeHit && splitTokens(term).length <= 2) {
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
                var prod = matchFuzzy(term, PRODUCTS) || (ctx ? ctx : null);
                if (prod && (actionHit || problemHit)) {
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


def js_list(items, per_line=6):
    """Render a python list as a compact JS array literal."""
    items = sorted(set(str(i).lower().strip() for i in items if str(i).strip()))
    if not items:
        return "[]"
    lines = []
    for i in range(0, len(items), per_line):
        # ensure_ascii=False: Arabic/Hindi entries stay readable (not \uXXXX)
        lines.append(", ".join(json.dumps(x, ensure_ascii=False) for x in items[i:i + per_line]))
    return "[\n    " + ",\n    ".join(lines) + "\n  ]"


def render_script(campaigns, bid_keywords, products, fuzzy_roots, niche):
    """Merge universal + niche lists (collision-filtered) and render the JS.
    Pure function — testable without the Claude API."""
    def _lst(key):
        return [str(x).lower() for x in (niche.get(key) or [])]

    forbidden = filter_forbidden(
        _lst("forbidden_words") + UNIVERSAL_PRICE_SHOPPING_RU, bid_keywords, "forbidden")
    edu = filter_forbidden(
        UNIVERSAL_EDU_CAREER + _lst("edu_career_words"), bid_keywords, "edu/career")
    info_diy = filter_forbidden(
        UNIVERSAL_INFO_DIY + _lst("info_diy_words"), bid_keywords, "info/DIY")
    forbidden_locations = _lst("forbidden_locations")
    context_words = _lst("context_product_words")
    problems = UNIVERSAL_PROBLEM_SIGNALS + _lst("problem_signals")
    safe_roots = bid_keywords + _lst("extra_safe_roots")
    all_products = products + _lst("extra_products")
    actions = UNIVERSAL_ACTIONS + _lst("extra_actions")
    strong_actions = UNIVERSAL_STRONG_ACTIONS + _lst("extra_actions")

    js = (JS_TEMPLATE
          .replace("%%BUSINESS%%", BUSINESS_NAME or "Universal")
          .replace("%%LOCATION%%", TARGET_LOCATION or "any location")
          .replace("%%CAMPAIGNS%%", js_list(campaigns, 2))
          .replace("%%FORBIDDEN_LOCATIONS%%", js_list(forbidden_locations))
          .replace("%%EDU_CAREER%%", js_list(edu, 4))
          .replace("%%INFO_DIY%%", js_list(info_diy, 4))
          .replace("%%FORBIDDEN_WORDS%%", js_list(forbidden))
          .replace("%%CONTEXT_WORDS%%", js_list(context_words))
          .replace("%%SAFE_ROOTS%%", js_list(safe_roots, 4))
          .replace("%%PRODUCTS%%", js_list(all_products))
          .replace("%%ACTIONS%%", js_list(actions))
          .replace("%%STRONG_ACTIONS%%", js_list(strong_actions))
          .replace("%%PROBLEMS%%", js_list(problems, 4))
          .replace("%%FUZZY_ROOTS%%", js_list(fuzzy_roots)))

    stats = {
        "safe_roots": len(set(safe_roots)), "forbidden": len(forbidden),
        "edu": len(edu), "info_diy": len(info_diy),
        "context": len(set(context_words)), "problems": len(set(problems)),
        "locations": len(set(forbidden_locations)),
        "products": len(set(all_products)), "actions": len(set(actions)),
        "fuzzy_roots": list(fuzzy_roots),
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
    print("   Paste into Google Ads > Tools > Scripts, run DRY first, then set DRY_RUN=false + hourly schedule.")


if __name__ == "__main__":
    main()
