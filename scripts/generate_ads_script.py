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

ENGINE UPGRADES vs a hand-written cleaner:
  - whole-token fuzzy matching (typos: plamber→plumber, cebints→cabinets;
    plurals stripped) — never substring, so "place" can NEVER hit "replacement"
  - converted-search-terms protection: terms with conversions are never banned
  - DRY_RUN mode (default ON for the first runs)
  - negatives added as EXACT [term] (surgical); repeat forbidden roots are
    logged as phrase-negative suggestions instead of auto-phrase-banning

Env vars: ANTHROPIC_API_KEY, BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION
Optional: CLAUDE_MODEL (default claude-sonnet-5), CLAUDE_EFFORT (default low)

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


def robust_json(text):
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text.strip(), flags=re.MULTILINE).strip()
    s, e = text.find("{"), text.rfind("}") + 1
    return json.loads(text[s:e])


def tokens_of(s):
    return re.findall(r"[a-z0-9]+", str(s).lower())


def build_lists(strategy):
    groups = strategy.get("ad_groups", [])
    bid_keywords = []
    for g in groups:
        for k in g.get("keywords", []):
            bid_keywords.append(k["keyword"].lower())
            bid_keywords.extend(v.lower() for v in k.get("variants", []))
        bid_keywords.extend(e.lower() for e in g.get("intent_expansion_keywords", []))
    bid_keywords = sorted(set(bid_keywords))

    # Distinctive product tokens: frequent, non-action, non-stopword tokens
    freq = {}
    for kw in bid_keywords:
        for t in set(tokens_of(kw)):
            freq[t] = freq.get(t, 0) + 1
    action_tokens = {t for a in UNIVERSAL_ACTIONS for t in tokens_of(a)}
    loc_tokens = set(tokens_of(TARGET_LOCATION))
    products = sorted(t for t, c in freq.items()
                      if c >= 3 and len(t) >= 4
                      and t not in action_tokens and t not in STOPWORDS
                      and t not in loc_tokens)
    return bid_keywords, products


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
  "extra_safe_roots": ["..."],
  "extra_products": ["..."],
  "extra_actions": ["..."]
}}

Rules:
- forbidden_locations: cities/regions/countries NEAR the target location that
  the business does NOT serve (competing emirates/cities, neighbor countries),
  including common misspellings and local-language spellings if relevant.
  NEVER include the target location itself or its own areas/neighborhoods.
- forbidden_words: 40-80 terms that signal WRONG intent for this specific
  business: adjacent trades it does NOT do, DIY/informational intent (how to,
  tutorial, youtube), jobs/careers/salary, retail/marketplace/buy/used/rent
  (only if the business SELLS services not products), spare parts, well-known
  competitor brand names in that market, B2B/wholesale/manufacturer terms.
  CRITICAL: never include any word that appears in the bid keywords above.
- extra_safe_roots: 10-25 phrases customers of this business also search that
  must NEVER be banned (crossover services it likely handles, urgent phrasings,
  local-language service phrases if common in that market).
- extra_products: brand names / product nouns of this niche people include in
  service searches (e.g. appliance brands for repair niches). Empty if none.
- extra_actions: niche-specific action/intent verbs not in a generic list.
- Everything lowercase. No duplicates."""
    with client.messages.stream(
        model=MODEL,
        max_tokens=12000,
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


def filter_forbidden(forbidden, bid_keywords):
    """Kill any forbidden entry that collides with our own bid keywords —
    the #1 false-positive source. Collision = the forbidden phrase appears
    inside any bid keyword (token-wise) or shares a token with them (for
    single-word entries)."""
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
        print(f"   🛡️ Dropped {len(dropped)} forbidden words that collide with bid keywords: {dropped[:10]}{'...' if len(dropped) > 10 else ''}")
    return sorted(set(clean))


JS_TEMPLATE = r"""/**
 * 🛡️ NEGATIVE GUARD — %%BUSINESS%% (%%LOCATION%%)
 * AUTO-GENERATED from real keyword data by the keyword-research-tool.
 * Engine: GAQL (search_term_view) | Frequency: run HOURLY
 *
 * LOGIC ORDER (first match wins):
 *   0. CONVERTED TERM (has conversions)      -> ALWAYS ALLOW (never ban a converter)
 *   1. Forbidden Location                    -> BLOCK
 *   2. Safe Root (our bid keywords + known-good phrases) -> ALLOW
 *   3. Forbidden Word (word-boundary + typo-aware)       -> BLOCK
 *   4. Product + Action (both required)      -> ALLOW
 *   5. Catch-all                             -> BLOCK
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

  var FORBIDDEN_LOCATIONS = %%FORBIDDEN_LOCATIONS%%;

  var SAFE_ROOTS = %%SAFE_ROOTS%%;

  var FORBIDDEN_WORDS = %%FORBIDDEN_WORDS%%;

  var PRODUCTS = %%PRODUCTS%%;

  var ACTIONS = %%ACTIONS%%;

  // ============ MATCHERS ============
  function esc(w) { return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  // whole-word/phrase boundary match — never inside another word
  function matchStrict(text, list) {
    for (var i = 0; i < list.length; i++) {
      var rx = new RegExp("(^|[\\s\\W_])" + esc(list[i]) + "([\\s\\W_]|$)", "i");
      if (rx.test(text)) return list[i];
    }
    return null;
  }

  function stripPlural(t) {
    if (t.length > 4 && t.slice(-3) === "ies") return t.slice(0, -3) + "y";
    if (t.length > 3 && t.slice(-2) === "es") return t.slice(0, -2);
    if (t.length > 3 && t.slice(-1) === "s") return t.slice(0, -1);
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
    var toks = text.split(/[\s\W_]+/);
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

  // ============ ENGINE ============
  Logger.log("🛡️ Negative Guard starting (" + (DRY_RUN ? "DRY RUN — no changes" : "LIVE") + ")...");

  var query =
    "SELECT search_term_view.search_term, metrics.impressions, metrics.clicks, " +
    "metrics.conversions, ad_group.id " +
    "FROM search_term_view " +
    "WHERE campaign.name IN ('" + CAMPAIGN_NAMES.join("','") + "') " +
    "AND metrics.impressions >= " + MIN_IMPRESSIONS + " " +
    "AND segments.date DURING " + DATE_RANGE;

  var rows = AdsApp.search(query);
  var banned = 0, allowed = 0, rowCount = 0;
  var forbiddenRootHits = {};

  while (rows.hasNext()) {
    rowCount++;
    var row = rows.next();
    var rawTerm = row.searchTermView.searchTerm;
    var term = rawTerm.toLowerCase().trim();
    var adGroupId = row.adGroup.id;
    var conversions = Number(row.metrics.conversions || 0);

    var isSafe = false, reason = "";

    // 0️⃣ converted terms are sacred
    if (PROTECT_CONVERTERS && conversions > 0) {
      isSafe = true; reason = "converted (" + conversions + ")";
    } else {
      // 1️⃣ wrong location
      var badLoc = matchStrict(term, FORBIDDEN_LOCATIONS);
      if (badLoc) {
        reason = "Forbidden Location: [" + badLoc + "]";
      } else {
        // 2️⃣ safe roots (our own keywords + known-good phrases)
        var safe = matchFuzzy(term, SAFE_ROOTS);
        if (safe) { isSafe = true; }
        else {
          // 3️⃣ forbidden words (typo-aware, whole tokens only)
          var bad = matchFuzzy(term, FORBIDDEN_WORDS);
          if (bad) {
            reason = "Forbidden Word: [" + bad + "]";
            forbiddenRootHits[bad] = (forbiddenRootHits[bad] || 0) + 1;
          } else {
            // 4️⃣ product + action
            var prod = matchFuzzy(term, PRODUCTS);
            if (prod) {
              var act = matchFuzzy(term, ACTIONS);
              if (act) { isSafe = true; }
              else { reason = "Product [" + prod + "] but NO action/intent word"; }
            } else {
              reason = "No relevant product or safe root";
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
    lines = []
    for i in range(0, len(items), per_line):
        lines.append(", ".join(json.dumps(x) for x in items[i:i + per_line]))
    return "[\n    " + ",\n    ".join(lines) + "\n  ]"


def main():
    if not os.path.exists(STRATEGY_FILE):
        print(f"❌ {STRATEGY_FILE} not found — run analyze_with_claude.py first.")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is missing.")
        sys.exit(1)

    with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
        strategy = json.load(f)

    bid_keywords, products = build_lists(strategy)
    print(f"Building negative-guard script: {len(bid_keywords)} safe bid keywords, "
          f"{len(products)} product tokens from data...")

    niche = ask_claude(bid_keywords, products)

    forbidden = filter_forbidden(niche.get("forbidden_words", []), bid_keywords)
    forbidden_locations = [str(x).lower() for x in niche.get("forbidden_locations", [])]
    safe_roots = bid_keywords + [str(x).lower() for x in niche.get("extra_safe_roots", [])]
    all_products = products + [str(x).lower() for x in niche.get("extra_products", [])]
    actions = UNIVERSAL_ACTIONS + [str(x).lower() for x in niche.get("extra_actions", [])]

    campaigns = [c["name"] for c in strategy.get("campaigns", [])] or ["UPDATE_CAMPAIGN_NAME"]

    js = (JS_TEMPLATE
          .replace("%%BUSINESS%%", BUSINESS_NAME or "Universal")
          .replace("%%LOCATION%%", TARGET_LOCATION or "any location")
          .replace("%%CAMPAIGNS%%", js_list(campaigns, 2))
          .replace("%%FORBIDDEN_LOCATIONS%%", js_list(forbidden_locations))
          .replace("%%SAFE_ROOTS%%", js_list(safe_roots, 4))
          .replace("%%FORBIDDEN_WORDS%%", js_list(forbidden))
          .replace("%%PRODUCTS%%", js_list(all_products))
          .replace("%%ACTIONS%%", js_list(actions)))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(js)

    print(f"✅ {OUTPUT_FILE}: {len(campaigns)} campaigns | {len(safe_roots)} safe roots | "
          f"{len(forbidden)} forbidden words | {len(forbidden_locations)} forbidden locations | "
          f"{len(all_products)} products | {len(actions)} actions")
    print("   Paste into Google Ads > Tools > Scripts, run DRY first, then set DRY_RUN=false + hourly schedule.")


if __name__ == "__main__":
    main()
