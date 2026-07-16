/**
 * 🛡️ NEGATIVE GUARD v2 — ClickAds Protector (United States)
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
  var CAMPAIGN_NAMES = [
    "click fraud protection", "google ads management services"
  ];
  var DATE_RANGE = "TODAY";        // TODAY | YESTERDAY | LAST_7_DAYS
  var MIN_IMPRESSIONS = 0;
  var DRY_RUN = true;              // ⚠️ pehle 2-3 din TRUE rakhein — sirf log karega.
                                   // Log theek lagay to false kar dein.
  var PROTECT_CONVERTERS = true;   // conversion wali term kabhi ban nahi hogi
  var ALLOW_SHORT_PRODUCT = true;  // "kitchen cabinets" type <=3-word product query allow

  var FORBIDDEN_LOCATIONS = [];

  var EDU_CAREER = [
    "academy", "apprenticeship", "business kaise", "career",
    "careers", "catalogue", "certificate", "certification",
    "click fraud definition", "click fraud statistics", "conversion rate optimization course", "course",
    "courses", "cro certification", "cv", "datasheet",
    "define", "definition", "diagram", "digital marketing degree",
    "diploma", "dukan kaise", "google ads api documentation", "google ads certification exam",
    "google ads exam answers", "google ads manager salary", "google ads script tutorial", "google ads scripts documentation",
    "google ads skillshop", "google ads specialist salary", "hiring", "how do",
    "how does", "how to become", "how to become a ppc specialist", "in hindi",
    "in urdu", "institute", "internship", "interview questions",
    "items list", "job", "jobs", "ka kaam",
    "ka kam", "kaise bane", "kaise khole", "kaise seekhe",
    "kaise sikhe", "kitne prakar", "kitne type", "kitni salary",
    "kya hai", "kya hota hai", "landing page design course", "learn google ads scripts",
    "material list", "meaning in", "meaning of", "mechanism of",
    "name list", "negative keyword match types explained", "ppc analyst salary", "ppc certification course",
    "ppc course", "ppc training", "recruitment", "resume",
    "salaries", "salary", "schematic", "shop kaise",
    "size chart", "standard height", "tool name", "tools list",
    "tools name", "training", "translate", "types of",
    "types of ad fraud", "types of click fraud", "vacancies", "vacancy",
    "wage", "wages", "what happens", "what is",
    "what is click fraud", "what is negative keyword"
  ];

  var INFO_DIY = [
    "difference between", "diy", "diy click fraud protection", "diy negative keyword list",
    "do it yourself", "free click fraud checker", "ghar par kaise", "google ads script examples free",
    "how to", "how to add negative keywords", "how to block fraudulent clicks", "how to build a landing page",
    "how to create landing page", "how to detect click fraud", "how to identify bot traffic", "how to install google ads script",
    "how to prevent click fraud", "how to read click fraud report", "how to set up negative keyword list", "how to stop invalid clicks",
    "how to write google ads script", "instructions", "khud banana", "khud lagana",
    "khud se", "ki setting", "manual", "tutorial",
    "what causes", "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "affiliate", "amazon ppc", "app development", "b2b leads", "billboard advertising", "bing ads",
    "buy", "career", "careers", "cheap", "cold calling service", "content writing",
    "coupon", "crack", "cv", "digital marketing course", "discount code", "distributor",
    "email marketing", "facebook ads agency", "for sale", "franchise", "free download", "google ads certification",
    "google ads exam", "graphic design", "hiring", "influencer marketing", "internship", "job",
    "jobs", "ka dam", "ka price", "khareedna", "kharidna", "ki qeemat",
    "kitna hai", "kitne ka", "lead generation company", "linkedin ads", "logo design", "manufacturer",
    "marketing agency", "nulled", "print ads", "radio ads", "reseller", "resume",
    "salary", "sasta", "seo agency", "seo course", "seo services", "social media management",
    "supplier", "telemarketing", "tiktok ads agency", "torrent", "tv ads", "used",
    "web design agency", "web hosting", "white label", "wholesale", "wholesaler", "wordpress developer"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "checker", "extension", "page", "pages", "script", "scripts",
    "software", "template", "tools", "tracker"
  ];

  var SAFE_ROOTS = [
    "account level negative keywords", "account level negative keywords google ads", "ad fraud detection software", "ad fraud detection tools",
    "ad fraud prevention", "ad fraud prevention consultant", "ad fraud protection", "ad fraud software",
    "ad fraud tools", "ad spend protection service", "add negative keywords", "add negative keywords google ads",
    "add negative keywords to all campaigns", "add negative keywords to performance max", "ads script", "advertisement click fraud detection",
    "adwords click fraud software", "adwords landing page", "adwords landing page examples", "adwords negative keyword list",
    "best click fraud prevention software", "best click fraud protection", "best click fraud protection software", "best click fraud software",
    "best google ads landing pages", "broad match negative keyword", "campaign budget protection", "click fraud detection service",
    "click fraud detection software", "click fraud detection techniques", "click fraud monitoring service", "click fraud prevention",
    "click fraud prevention software", "click fraud protection", "click fraud protection company united states", "click fraud protection cost",
    "click fraud protection for small business", "click fraud protection pricing", "click fraud protection service", "click fraud protection software",
    "click fraud software", "click fraud solutions", "click fraud tools", "competitor click fraud protection",
    "conversion rate optimization landing page service", "create landing page for google ads", "custom google ads scripts for agencies", "custom ppc landing pages united states",
    "expanded landing pages google ads", "free landing page for google ads", "google ad fraud detection", "google ad landing page",
    "google ad manager for small business", "google ad manager small business", "google ad scripts", "google ads account level negative keywords",
    "google ads account optimization negative keywords service", "google ads and landing pages", "google ads audit service", "google ads automation scripts",
    "google ads automation service cost", "google ads bid automation service", "google ads budget pacing script", "google ads click fraud protection service",
    "google ads consultant for service business", "google ads conversion script", "google ads editor negative keyword lists", "google ads expanded landing pages",
    "google ads landing page agency", "google ads landing page design pricing", "google ads landing pages", "google ads management automation pricing",
    "google ads management for local business", "google ads management for small business", "google ads management service", "google ads monthly budget script",
    "google ads negative keyword audit service", "google ads negative keywords", "google ads script", "google ads script installation service",
    "google ads script setup service", "google ads scripts", "google ads scripts consultant united states", "google ads scripts service",
    "google adwords landing page", "google adwords negative keywords", "google adwords script", "google click fraud detection",
    "google landing pages", "google negative keywords", "google remarketing script", "google shopping negative keywords",
    "google shopping scripts", "hire click fraud protection service", "hire google ads scripts expert", "hire ppc landing page designer",
    "hire ppc negative keyword expert", "invalid clicks protection google ads", "keyword negative", "landing page for google ads",
    "landing page for ppc", "landing page in google ads", "landing page optimization for google ads cost", "landing page optimization service",
    "manage my google ads account", "mobile ad fraud detection and prevention", "n gram script google ads", "negative keyword broad match",
    "negative keyword list service for agencies", "negative keyword management service", "negative keywords for google ads", "negative keywords google ads",
    "negative keywords in google ads", "negative keywords on google ads", "negative keywords shopping campaigns", "new google ads scripts",
    "ongoing negative keyword management pricing", "pmax negative keywords", "ppc agency for contractors", "ppc fraud protection",
    "ppc landing page design service", "ppc management for small business", "ppc scripts", "protect my ad budget",
    "script for google ads", "script google ads", "scripts in google ads", "smart shopping negative keywords",
    "stop click fraud now", "stop click fraud on google ads", "urgent click fraud help"
  ];

  var PRODUCTS = [
    "account", "adwords", "automation", "business", "click", "clickcease",
    "clickguard", "cost", "detection", "fraud", "fraudblocker", "gclid",
    "google", "google click id", "keyword", "keywords", "landing", "level",
    "lunio", "management", "negative", "optimization", "page", "pages",
    "prevention", "pricing", "protection", "script", "scripts", "shopping",
    "small", "software", "tools", "trafficguard"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "audit", "automate",
    "bespoke", "block", "book", "booking", "build", "builder",
    "builders", "call", "certified", "change", "changing", "check",
    "clean", "cleaner", "cleaning", "companies", "company", "contact",
    "contract", "contractor", "custom", "deep cleaning", "design", "designer",
    "detect", "diagnose", "emergency", "exclude", "expert", "fast",
    "filter", "fix", "fixed", "fixes", "fixing", "flag",
    "help", "hire", "in my area", "inspect", "inspection", "install",
    "installation", "installing", "installs", "licensed", "local", "made to measure",
    "made to order", "maintain", "maintenance", "maker", "makers", "making",
    "monitor", "near me", "nearby", "now", "number", "optimize",
    "prevent", "professional", "protect", "quick", "quotation", "quote",
    "quotes", "relocate", "relocation", "removal", "remove", "repair",
    "repairing", "repairs", "replace", "replacement", "replacing", "same day",
    "service", "services", "servicing", "solution", "specialist", "tailor made",
    "technician", "today", "trusted", "urgent", "wash", "washing",
    "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "audit", "automate", "bespoke", "block", "build",
    "builder", "clean", "cleaning", "custom", "design", "designer",
    "detect", "detection", "exclude", "fabrication", "filter", "fitted",
    "fix", "fixed", "fixes", "fixing", "flag", "inspect",
    "inspection", "install", "installation", "installing", "installs", "made to measure",
    "made to order", "maintain", "maintenance", "maker", "making", "monitor",
    "mount", "mounting", "optimize", "prevent", "protect", "refurbish",
    "remodel", "remodeling", "renovate", "renovation", "repair", "repairing",
    "repairs", "replace", "replacement", "replacing", "restoration", "restore",
    "service", "services", "servicing", "tailor made", "unblock", "unclog",
    "wash", "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "ad spend disappearing fast", "ads getting clicked but no leads", "ads not generating leads", "blockage",
    "blocked", "bots clicking my ads", "bounce rate too high on landing page", "broke",
    "broken", "budget getting drained", "burst", "campaign getting bot traffic",
    "click fraud from competitors", "clogged", "competitors clicking my ads", "corroded",
    "crack", "cracked", "ctr high but no sales", "damage",
    "damaged", "dripping", "fake clicks on my ads", "fault",
    "faulty", "fraudulent traffic on ads", "google ads account overspending", "google ads budget exhausted early",
    "high cpc no conversions", "invalid clicks google ads", "irrelevant search terms triggering ads", "issue",
    "issues", "jammed", "kharab", "landing page not converting",
    "leakage", "leaking", "leaky", "low pressure",
    "low quality traffic from ads", "noise", "noisy", "not turning on",
    "not working", "overflow", "overflowing", "overheating",
    "ppc campaign underperforming", "problem", "problems", "rusted",
    "same ip clicking ads repeatedly", "short circuit", "slow", "smell",
    "smells", "smelly", "stopped working", "stuck",
    "suspicious clicks on campaign", "too many negative keywords needed", "tripping", "vibrating",
    "wasted ad budget", "wasting ad spend", "weak", "won't work",
    "wont turn", "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "google", "keywords", "landing", "negative", "protection", "script"
  ];

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
              // 6️⃣ misspelled head service token → potential lead, KEEP
              else if (fuzzyRootHit && !safeHit) {
                isSafe = true; reason = "fuzzy root [" + fuzzyRootHit + "]";
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
