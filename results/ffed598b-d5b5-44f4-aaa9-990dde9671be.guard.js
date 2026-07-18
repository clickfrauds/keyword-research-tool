/**
 * 🛡️ NEGATIVE GUARD v2 — Electrician Near Dubai (Dubai, United Arab Emirates)
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
    "core electrician services"
  ];
  var DATE_RANGE = "TODAY";        // TODAY | YESTERDAY | LAST_7_DAYS
  var MIN_IMPRESSIONS = 0;
  var DRY_RUN = true;              // ⚠️ pehle 2-3 din TRUE rakhein — sirf log karega.
                                   // Log theek lagay to false kar dein.
  var PROTECT_CONVERTERS = true;   // conversion wali term kabhi ban nahi hogi
  var ALLOW_SHORT_PRODUCT = true;  // "kitchen cabinets" type <=3-word product query allow

  var FORBIDDEN_LOCATIONS = [
    "abu dhabi", "abudhabi", "ajman", "al ain", "bahrain", "doha",
    "fujairah", "kuwait", "muscat", "oman", "qatar", "rak",
    "ras al khaimah", "riyadh", "sharja", "sharjah", "umm al quwain"
  ];

  var EDU_CAREER = [
    "academy", "amp rating chart", "apprenticeship", "bijli mistri course",
    "business kaise", "cable size calculator", "career", "careers",
    "catalogue", "certificate", "certification", "course",
    "courses", "cv", "datasheet", "define",
    "definition", "dewa approved electrician course", "diagram", "diploma",
    "diploma in electrical engineering", "dukan kaise", "electrical engineering degree", "electrical wiring diagram pdf",
    "electrician apprenticeship uae", "electrician certification uae", "electrician course dubai", "electrician job vacancy dubai",
    "electrician ka course", "electrician ki salary", "electrician license uae exam", "electrician salary dubai",
    "electrician tool kit list", "electrician training dubai", "hiring", "how do",
    "how does", "how to become", "how to become an electrician", "in hindi",
    "in urdu", "institute", "internship", "interview questions",
    "items list", "iti electrician course", "job", "jobs",
    "ka kaam", "ka kam", "kaise bane", "kaise khole",
    "kaise seekhe", "kaise sikhe", "kitne prakar", "kitne type",
    "kitni salary", "kya hai", "kya hota hai", "material list",
    "mcb vs rccb", "meaning in", "meaning of", "mechanism of",
    "name list", "recruitment", "resume", "salaries",
    "salary", "schematic", "shop kaise", "size chart",
    "standard height", "tool name", "tools list", "tools name",
    "trade test electrician", "training", "translate", "types of",
    "types of circuit breakers", "types of db boards", "vacancies", "vacancy",
    "voltage types uae", "wage", "wages", "what happens",
    "what is", "what is a db board", "wire gauge chart"
  ];

  var INFO_DIY = [
    "db board wiring diagram", "difference between", "diy", "do it yourself",
    "electrical safety tips at home", "electrical wiring color code", "ghar par kaise", "how to",
    "how to change a plug socket", "how to check for electrical fault", "how to fix a short circuit", "how to fix flickering lights",
    "how to install a socket", "how to install ev charger at home diy", "how to reset circuit breaker", "how to reset tripped fuse",
    "how to test a fuse", "how to wire a switch", "instructions", "khud banana",
    "khud lagana", "khud se", "ki setting", "manual",
    "mcb tripping reason", "tutorial", "what causes", "why does my breaker keep tripping",
    "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "ac repair", "air conditioning", "al fahim electric", "apprentice electrician", "b2b electrical", "buy electrical items",
    "cable shop dubai", "career", "carpenter", "cctv installation", "cleaning company", "dewa jobs",
    "electrical company for sale", "electrical distributor uae", "electrical engineering degree", "electrical equipment supplier", "electrical exam uae", "electrical franchise",
    "electrical items for sale", "electrical parts shop", "electrical shop near me", "electrical supplier dubai", "electrical tools shop", "electrician certificate",
    "electrician course", "electrician recruitment", "electrician salary dubai", "electrician training", "electrician vacancy", "etisalat",
    "generator rental", "handyman jobs", "hiring electricians", "hvac", "internship electrician", "job vacancy",
    "jobs near me", "ka dam", "ka price", "khareedna", "kharidna", "ki qeemat",
    "kitna hai", "kitne ka", "manufacturer electrical uae", "painter", "painting", "pest control",
    "plumber", "plumbing", "rent electrical tools", "roshan electrician", "salary", "sasta",
    "smart home company", "solar panel installer", "spare parts dubai", "used electrical equipment", "wholesale electrical supplies", "wire shop"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "board", "breaker", "cable", "charger", "fuse", "plug",
    "socket", "switch", "wire"
  ];

  var SAFE_ROOTS = [
    "24 7 electrician near me", "24 7 emergency electrician near me", "24 electrician near me", "24 hour electrical service near me",
    "24 hour electrician dubai", "24 hour electrician dubai cost", "24 hour electrician near me", "24 hr electrical services near me",
    "24 hrs electrician near me", "24hr electrician near me", "24hrs electrician near me", "24x7 electrician near me",
    "best electrical services in dubai", "best electrician dubai", "best emergency electricians near me", "book electrician dubai",
    "british electrician dubai", "cheap electrician dubai", "circuit breaker repair dubai", "db board installation dubai",
    "db board repair dubai", "distribution board replacement dubai", "dubai electrician company", "electric car charger fitting dubai",
    "electrical contracting companies in dubai", "electrical contractors in dubai", "electrical emergency service near me", "electrical fault finding dubai",
    "electrical maintenance company in dubai", "electrical maintenance dubai", "electrical repair dubai", "electrical technician dubai",
    "electrical work in dubai", "electrical work services in dubai", "electrician 24 7 near me", "electrician 24 hour near me",
    "electrician available now dubai", "electrician call out dubai", "electrician company in dubai", "electrician cost dubai",
    "electrician dubai", "electrician dubai marina", "electrician emergency near me", "electrician near me",
    "electrician price dubai", "electrician quote dubai", "electrician required in dubai", "electrician service dubai",
    "electrician services in dubai", "emergency electrical service near me", "emergency electrician call out dubai", "emergency electrician dubai",
    "emergency electrician dubai marina", "emergency electrician near me", "emergency electrician near me now", "emergency electrician service near me",
    "emergency electricians in my area", "ev charger installation company dubai", "ev charger installation cost dubai", "ev charger installation dubai",
    "ev charger installation price dubai", "ev charging point installer dubai", "fast electrician dubai", "fault finding dubai",
    "fixing a short circuit", "fuse box repair dubai", "hire electrician dubai", "home ev charger installation dubai",
    "licensed electrician dubai", "night electrician dubai", "office electrician dubai", "power outage electrician dubai",
    "power tripping repair dubai", "residential electrician dubai", "same day electrician dubai", "same day electrician near me",
    "short circuit repair dubai", "socket installation dubai", "switch installation dubai", "tesla charger installation dubai",
    "urgent electrical repair dubai", "urgent electrician dubai", "urgent electrician near me", "villa electrician dubai",
    "weekend electrician dubai", "wiring services dubai"
  ];

  var PRODUCTS = [
    "board", "charger", "circuit", "cost", "db board", "distribution board",
    "electrical", "electrician", "fuse box", "mcb", "rccb", "tesla charger"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "bespoke", "book",
    "booking", "build", "builder", "builders", "call", "call out",
    "certified", "change", "changing", "check", "clean", "cleaner",
    "cleaning", "companies", "company", "contact", "contract", "contractor",
    "custom", "deep cleaning", "design", "designer", "diagnose", "emergency",
    "expert", "fast", "fix", "fixed", "fixes", "fixing",
    "help", "hire", "in my area", "inspect", "inspection", "install",
    "installation", "installing", "installs", "licensed", "local", "made to measure",
    "made to order", "maintain", "maintenance", "maker", "makers", "making",
    "near me", "nearby", "now", "number", "professional", "quick",
    "quotation", "quote", "quotes", "relocate", "relocation", "removal",
    "remove", "repair", "repairing", "repairs", "replace", "replacement",
    "replacing", "rewire", "same day", "service", "services", "servicing",
    "solution", "specialist", "tailor made", "technician", "today", "troubleshoot",
    "trusted", "upgrade", "urgent", "wash", "washing", "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "build", "builder", "call out", "clean",
    "cleaning", "custom", "design", "designer", "detect", "detection",
    "fabrication", "fitted", "fix", "fixed", "fixes", "fixing",
    "inspect", "inspection", "install", "installation", "installing", "installs",
    "made to measure", "made to order", "maintain", "maintenance", "maker", "making",
    "mount", "mounting", "refurbish", "remodel", "remodeling", "renovate",
    "renovation", "repair", "repairing", "repairs", "replace", "replacement",
    "replacing", "restoration", "restore", "rewire", "service", "services",
    "servicing", "tailor made", "troubleshoot", "unblock", "unclog", "upgrade",
    "wash", "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "blockage", "blocked", "breaker tripped repeatedly", "broke",
    "broken", "burning smell from socket", "burst", "charger not charging car",
    "circuit breaker keeps tripping", "clogged", "corroded", "crack",
    "cracked", "damage", "damaged", "db board sparking",
    "distribution board fault", "dripping", "electric shock from switch", "electricity keeps cutting off",
    "ev charger not working", "fault", "faulty", "fuse box burning smell",
    "issue", "issues", "jammed", "kharab",
    "leakage", "leaking", "leaky", "lights flickering",
    "lights not turning on", "low pressure", "no electricity in office", "no power in house",
    "noise", "noisy", "not turning on", "not working",
    "overflow", "overflowing", "overheating", "power fluctuation",
    "power outage", "power tripping", "problem", "problems",
    "rusted", "short circuit", "slow", "smell",
    "smells", "smelly", "socket burnt", "socket not working",
    "sparking wires", "stopped working", "stuck", "sudden power loss",
    "switch not working", "switch sparking", "tripping", "vibrating",
    "weak", "wires exposed", "won't work", "wont turn",
    "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "charger", "circuit", "electrical", "electrician", "electricians", "marina"
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
