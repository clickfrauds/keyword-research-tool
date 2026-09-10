/**
 * 🛡️ NEGATIVE GUARD v2 — SEOblogy (N/A)
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
  // ⚙️ CONFIG — sirf campaign name check karein, baqi sab data-generated hai.
  //    Case ki fikar na karein: naam account se case-insensitively match hota hai.
  var CAMPAIGN_NAMES = [
    "White Label Automation Tools"
  ];
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
  var ALLOW_SHORT_PRODUCT = true;  // "kitchen cabinets" type <=3-word product query allow

  var FORBIDDEN_LOCATIONS = [];

  var EDU_CAREER = [
    "academy", "apprenticeship", "business kaise", "career",
    "careers", "catalogue", "certificate", "certification",
    "click fraud detection algorithm explained", "course", "courses", "cv",
    "datasheet", "define", "definition", "diagram",
    "digital agency profit margin", "diploma", "dukan kaise", "google ads certification cost",
    "google ads certification exam", "hiring", "how do", "how does",
    "how does click fraud protection work", "how does white label seo work", "how to become", "how to become a seo reseller",
    "how to start a digital agency", "in hindi", "in urdu", "institute",
    "internship", "interview questions", "items list", "jekyll vs hugo comparison",
    "job", "jobs", "ka kaam", "ka kam",
    "kaise bane", "kaise khole", "kaise seekhe", "kaise sikhe",
    "kitne prakar", "kitne type", "kitni salary", "kya hai",
    "kya hota hai", "material list", "meaning in", "meaning of",
    "mechanism of", "multilingual seo best practices", "name list", "ppc management certification",
    "recruitment", "resume", "salaries", "salary",
    "schematic", "seo reseller business model explained", "seo reseller salary", "seo reseller vs in house team",
    "shop kaise", "size chart", "standard height", "static site generator comparison",
    "tool name", "tools list", "tools name", "training",
    "translate", "types of", "types of seo reseller programs", "vacancies",
    "vacancy", "wage", "wages", "what happens",
    "what is", "what is a static site generator", "what is private label seo", "white label seo course",
    "white label vs private label seo difference"
  ];

  var INFO_DIY = [
    "difference between", "diy", "diy website builder tutorial", "do it yourself",
    "ghar par kaise", "google ads fraud settings", "google ads settings guide", "how to",
    "how to block invalid clicks in google ads", "how to build a static website", "how to check click fraud in analytics", "how to detect click fraud manually",
    "how to set up google ads campaign myself", "instructions", "jekyll tutorial", "khud banana",
    "khud lagana", "khud se", "ki setting", "manual",
    "seo reseller pricing calculator", "site builder tutorial for beginners", "static site generator tutorial", "tutorial",
    "what causes", "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "buy backlinks cheap", "buy website template", "cheap logo maker", "content writer jobs", "digital marketing degree", "domain registration cheap",
    "fiverr seo", "free website builder", "freelance web designer rates", "godaddy", "grant for small business website", "graphic design jobs",
    "hiring seo specialist", "hosting coupon", "ka dam", "ka price", "khareedna", "kharidna",
    "ki qeemat", "kitna hai", "kitne ka", "logo design free", "manufacturer", "marketing agency franchise",
    "ppc manager salary", "sasta", "seo affiliate program", "seo certification", "seo course", "seo internship",
    "seo internship remote", "seo jobs", "seo salary", "seo scam", "shopify", "social media manager jobs",
    "squarespace", "upwork seo", "used website", "web design apprenticeship", "web design jobs", "web design scholarship",
    "web developer jobs", "wholesale seo", "wordpress plugin"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "builder", "label", "management", "pricing", "program", "reseller",
    "site", "software", "static"
  ];

  var SAFE_ROOTS = [
    "ad fraud protection", "ads setup", "adword agency", "agency branded seo services",
    "agency seo fulfillment partner", "agency website builder white label", "automated google ads campaign builder", "average cost of website design for small business",
    "behind the scenes seo agency", "best click fraud protection", "best seo site builder", "best site builder for seo",
    "best web builder for seo", "best web design agencies near me", "best website builder for contractors", "best website builder for seo",
    "best white label seo companies", "best white label seo services", "click fraud detection software", "click fraud monitoring tool",
    "click fraud prevention tool", "click fraud protection", "click fraud protection for agencies", "click fraud protection for small business",
    "click fraud protection pricing", "click fraud protection software", "contractor website services", "custom small business website",
    "custom web design near me", "custom website design near me", "custom websites for small businesses", "electrical services website",
    "fast loading static website for small business", "google ads campaign setup", "google ads fulfillment for agencies", "google ads fulfillment partner",
    "google ads landing page design", "google ads management cost", "google ads management for digital agencies", "google ads management gold coast",
    "google ads management near me", "google ads management pricing", "google ads management services near me", "google ads management software for agencies",
    "google shopping ads management services", "hire white label google ads manager", "hire white label seo provider", "invalid click protection software",
    "invisible seo fulfillment", "jekyll site builder", "jekyll website builder", "local seo white label services",
    "moz local white label", "multilingual seo services", "multilingual website builder for agencies", "outsource google ads management",
    "outsource seo services white label", "outsourced seo for agencies", "ppc click fraud protection service", "private label google ads management",
    "private label seo fulfillment", "private label seo services", "protect google ads budget from bots", "reseller google ads management",
    "reseller ppc management", "seo fulfillment company", "seo reseller plan", "seo reseller plans",
    "seo reseller pricing plans", "seo reseller program", "seo reseller program for agencies", "seo reseller program for digital agencies",
    "seo reseller usa", "seo resellers program", "seo white labeling", "small business web design agency",
    "small business web design near me", "small business web development company", "small business website design agency", "small business website design near me",
    "small business website designer near me", "small business website development company", "static html website for service business", "static site builder",
    "static site builder no wordpress", "static website builder for agencies", "static website creator", "static website for agency clients",
    "static website generator", "stop invalid clicks google ads", "top website builders for small business", "web design agency for small business",
    "web design cost for small business", "web design studio near me", "website builder for agencies", "website builder for contractors and trades",
    "website builders for small business", "website creation for small business", "website creation small business", "website design and development company near me",
    "website design company near me", "website design for small business near me", "website design fulfillment service", "website fulfillment for digital agencies",
    "website static generator", "white label digital marketing fulfillment", "white label google ads management", "white label google ads management for agencies",
    "white label local seo", "white label local seo services", "white label ppc fulfillment", "white label ppc management service",
    "white label ppc reseller program", "white label seo agency partner", "white label seo companies", "white label seo fulfillment services",
    "white label seo local", "white label seo platform", "white label seo reseller program cost", "white label seo website builds",
    "white label website builds for agencies", "white label website design", "wix multilingual app"
  ];

  var PRODUCTS = [
    "agencies", "agency", "business", "click", "cost", "development",
    "digital", "fraud", "fulfillment", "google", "label", "management",
    "pricing", "program", "protection", "reseller", "site", "small",
    "software", "static", "website", "white"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "bespoke", "book",
    "booking", "build", "builder", "builders", "call", "certified",
    "change", "changing", "check", "clean", "cleaner", "cleaning",
    "companies", "company", "contact", "contract", "contractor", "custom",
    "deep cleaning", "delegate", "design", "designer", "detect", "diagnose",
    "emergency", "expert", "fast", "fix", "fixed", "fixes",
    "fixing", "fulfill", "help", "hire", "in my area", "inspect",
    "inspection", "install", "installation", "installing", "installs", "licensed",
    "local", "made to measure", "made to order", "maintain", "maintenance", "maker",
    "makers", "making", "monitor", "near me", "nearby", "now",
    "number", "outsource", "prevent", "professional", "protect", "quick",
    "quotation", "quote", "quotes", "rebrand", "reduce ad spend waste", "relocate",
    "relocation", "removal", "remove", "repair", "repairing", "repairs",
    "replace", "replacement", "replacing", "resell", "same day", "scale",
    "service", "services", "servicing", "solution", "specialist", "tailor made",
    "technician", "today", "trusted", "urgent", "wash", "washing",
    "whatsapp", "white-label"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "build", "builder", "clean", "cleaning",
    "custom", "delegate", "design", "designer", "detect", "detection",
    "fabrication", "fitted", "fix", "fixed", "fixes", "fixing",
    "fulfill", "inspect", "inspection", "install", "installation", "installing",
    "installs", "made to measure", "made to order", "maintain", "maintenance", "maker",
    "making", "monitor", "mount", "mounting", "outsource", "prevent",
    "protect", "rebrand", "reduce ad spend waste", "refurbish", "remodel", "remodeling",
    "renovate", "renovation", "repair", "repairing", "repairs", "replace",
    "replacement", "replacing", "resell", "restoration", "restore", "scale",
    "service", "services", "servicing", "tailor made", "unblock", "unclog",
    "wash", "washing", "white-label"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "agency can't keep up with client demand", "agency needs white label partner", "agency overwhelmed with seo workload", "blockage",
    "blocked", "broke", "broken", "burst",
    "click fraud draining ad budget", "client website slow to launch", "clients asking for multilingual site", "clogged",
    "corroded", "crack", "cracked", "damage",
    "damaged", "dripping", "fault", "faulty",
    "google ads account suspended for invalid clicks", "google ads budget wasted on bots", "google ads clicks not converting", "google ads costs too high with no results",
    "issue", "issues", "jammed", "kharab",
    "leakage", "leaking", "leaky", "losing clients due to seo results",
    "low pressure", "need faster website turnaround for clients", "need ppc management without hiring", "need reliable seo fulfillment partner",
    "need scalable seo delivery", "need to scale agency without hiring", "need white label solution for clients", "noise",
    "noisy", "not turning on", "not working", "overflow",
    "overflowing", "overheating", "problem", "problems",
    "rusted", "seo results not showing", "short circuit", "site not ranking for client",
    "slow", "smell", "smells", "smelly",
    "stopped working", "stuck", "tripping", "vibrating",
    "want to offer seo without hiring team", "weak", "won't work", "wont turn",
    "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "agencies", "business", "google", "management", "reseller", "website"
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
