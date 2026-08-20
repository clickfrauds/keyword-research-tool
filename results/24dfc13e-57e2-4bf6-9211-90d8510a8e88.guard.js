/**
 * 🛡️ NEGATIVE GUARD v2 — Seoblogy (N/A)
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
    "Website Build Services"
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
    "academy", "adwords exam study guide", "apprenticeship", "business kaise",
    "career", "careers", "catalogue", "certificate",
    "certification", "course", "courses", "cv",
    "datasheet", "define", "definition", "diagram",
    "difference between seo and sem", "digital marketing degree", "digital marketing internship", "diploma",
    "dukan kaise", "google ads campaign types explained", "google ads certification exam", "google ads certification free",
    "google ads exam answers", "google ads exam questions and answers", "google ads skillshop", "hiring",
    "how do", "how does", "how to become", "how to become a ppc manager",
    "in hindi", "in urdu", "institute", "internship",
    "interview questions", "items list", "job", "jobs",
    "ka kaam", "ka kam", "kaise bane", "kaise khole",
    "kaise seekhe", "kaise sikhe", "keyword research course", "kitne prakar",
    "kitne type", "kitni salary", "kya hai", "kya hota hai",
    "learn google ads", "material list", "meaning in", "meaning of",
    "mechanism of", "name list", "ppc manager salary", "ppc specialist job description",
    "ppc training", "recruitment", "resume", "salaries",
    "salary", "schematic", "sem vs ppc course", "seo analyst job description",
    "seo course online", "seo specialist salary", "seo training free", "seo tutorial for beginners",
    "shop kaise", "size chart", "standard height", "tool name",
    "tools list", "tools name", "training", "translate",
    "types of", "types of keyword research", "types of ppc campaigns", "vacancies",
    "vacancy", "wage", "wages", "web developer salary",
    "what happens", "what is", "what is quality score google ads"
  ];

  var INFO_DIY = [
    "difference between", "diy", "diy seo checklist", "do it yourself",
    "ghar par kaise", "how to", "how to build a website for free", "how to check backlinks free",
    "how to check google ads quality score", "how to do keyword research yourself", "how to do on page seo", "how to fix google ads disapproval",
    "how to improve website speed", "how to lower google ads cost", "how to optimize google business profile", "how to reduce cost per click",
    "how to run google ads myself", "how to set up google ads account", "how to target keywords for seo", "how to write meta description",
    "instructions", "khud banana", "khud lagana", "khud se",
    "ki setting", "manual", "tutorial", "what causes",
    "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "buy", "canva", "career", "careers", "cheap hosting", "clickfunnels",
    "clipart", "cpanel", "cv", "distributor", "domain registration", "duda",
    "email hosting", "employment", "fiverr", "for sale", "free download", "free template",
    "freelance jobs", "godaddy", "google ads certification", "hiring", "hosting plans", "internship",
    "job", "jobs", "ka dam", "ka price", "khareedna", "kharidna",
    "ki qeemat", "kitna hai", "kitne ka", "logo design free", "logo maker", "manufacturer",
    "rent", "rental", "resume", "salaries", "salary", "sasta",
    "seo certification", "seo course", "shopify", "squarespace", "supplier", "upwork",
    "used", "web hosting", "webflow", "weebly", "wholesale", "wix",
    "wordpress plugin free", "wordpress theme free"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "app", "builder", "domain", "hosting", "plugin", "site",
    "sites", "software", "template", "theme", "tool"
  ];

  var SAFE_ROOTS = [
    "admin google ads", "adword agency", "adwords advertising agency", "adwords agency",
    "affordable web design agency", "affordable website designers", "ai ppc management", "analysis and keyword research",
    "audience manager google ads", "audience manager in google ads", "backlink building service", "best corporate web design",
    "best it company website design", "best ppc agency for local business", "best seo site builder", "best site builder for seo",
    "best web builder for seo", "best web design agencies near me", "best web design agency near me", "best website builder for seo",
    "best website development company near me", "boca web agency", "bright local serp", "business listing sites for seo",
    "business web design services", "business website design near me", "business website design services", "business website development company",
    "business website development services", "canterbury website design & seo", "canterbury website design and seo", "coffee shop web design",
    "contractor website services", "conversion rate optimization service", "cost to build a business website", "custom website for plumbers",
    "dental google adwords agency", "design static website", "ecommerce ppc management", "electrical services website",
    "enterprise ppc management", "fast loading website for small business", "free google small business advertising", "global google ads agency",
    "google ads admin", "google ads agency for small business near me", "google ads audience manager", "google ads audit",
    "google ads audit service", "google ads budget management", "google ads for local business", "google ads for pest control",
    "google ads for small business", "google ads local business", "google ads management", "google ads management cost",
    "google ads management for lawyers", "google ads management for small business", "google ads management gold coast", "google ads management near me",
    "google ads management pricing", "google ads management pricing packages", "google ads management services", "google ads management services near me",
    "google ads marketing agency near me", "google ads setup and management cost", "google advertising for small business", "google advertising manager",
    "google business profile optimization", "google free advertising for small business", "google local ads services", "google local business ad",
    "google local business advertising", "google local rank tracker", "google shopping ads management services", "google shopping management agency",
    "hire google ads expert", "hire website designer for small business", "how much does seo cost for small business", "hvac google ads",
    "hvac ppc management", "keyword analysis research", "keyword research analysis", "keyword research and analysis for seo",
    "keyword research and analysis in seo", "keyword research search engine optimization", "keyword research service quote", "keyword services",
    "landing page design service", "local business ads google", "local business google ads", "local business seo",
    "local business seo ranking service", "local keyword research", "local search sites", "local search websites",
    "local seo for multiple locations", "local seo keyword research", "local seo optimisation", "local seo package pricing",
    "local seo services", "localized keyword research", "monthly google ads management fee", "near web development company",
    "online website development company", "pay per click management near me", "pest control google ads", "phoenix ppc management",
    "phoenix web design agency", "ppc ads services", "ppc advertising services", "ppc agency near me",
    "ppc audit", "ppc management near me", "ppc management quote", "ppc management service",
    "ppc research", "professional web design agency", "professional website design agency", "real estate web development company",
    "real estate website development company", "research in seo", "research keywords seo", "research ppc",
    "search engine marketing agency", "search engine optimization keyword analysis", "search engine optimization keyword research", "search engine optimization keyword tool",
    "search term research", "secure website no wordpress plugins", "sem agency", "seo analysis for keyword",
    "seo and design", "seo and keyword research", "seo audit", "seo audit for small business website",
    "seo business listing sites", "seo content for service business website", "seo content writing service", "seo design",
    "seo for multiple locations", "seo for web developers", "seo friendly website builder pricing", "seo in design",
    "seo keyword analysis", "seo keyword competition analysis", "seo keyword research", "seo keyword search",
    "seo keyword tool", "seo keyword tracker", "seo research", "seo web company",
    "seo website build cost", "seo website company", "service business website design", "site development companies",
    "small business marketing agency", "small business web builder", "small business web design near me", "small business website design cost",
    "small business website design near me", "small business website designer near me", "static page design", "static web page design",
    "static website builder for contractors", "static website design", "the best web design agency near me", "top google ads agency",
    "top rated web design agency", "top web design agencies", "top website design agencies", "web developer and seo",
    "website audit", "website builder for small business", "website creator for small business", "website design and development company near me",
    "website design and seo near me", "website design company for electricians", "website design for service business", "website design for small business near me",
    "website design quote for service business", "website directories seo", "website maintenance service", "website maker for small business",
    "website making company near me", "website optimization near me", "website redesign service", "website seo companies near me",
    "website seo near me"
  ];

  var PRODUCTS = [
    "advertising", "adwords", "agencies", "agency", "analysis", "audience",
    "business", "cost", "development", "engine", "google", "keyword",
    "management", "manager", "optimization", "pricing", "research", "search",
    "site", "sites", "small", "static", "website"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "audit", "bespoke",
    "book", "booking", "boost visibility", "build", "builder", "builders",
    "call", "certified", "change", "changing", "check", "clean",
    "cleaner", "cleaning", "companies", "company", "contact", "contract",
    "contractor", "custom", "deep cleaning", "design", "designer", "diagnose",
    "emergency", "expert", "fast", "fix", "fixed", "fixes",
    "fixing", "generate leads", "help", "hire", "improve rankings", "in my area",
    "increase traffic", "inspect", "inspection", "install", "installation", "installing",
    "installs", "licensed", "local", "made to measure", "made to order", "maintain",
    "maintenance", "maker", "makers", "making", "manage", "near me",
    "nearby", "now", "number", "optimize", "professional", "quick",
    "quotation", "quote", "quotes", "relocate", "relocation", "removal",
    "remove", "repair", "repairing", "repairs", "replace", "replacement",
    "replacing", "run campaign", "same day", "service", "services", "servicing",
    "set up", "solution", "specialist", "tailor made", "technician", "today",
    "track conversions", "trusted", "urgent", "wash", "washing", "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "audit", "bespoke", "boost visibility", "build", "builder",
    "clean", "cleaning", "custom", "design", "designer", "detect",
    "detection", "fabrication", "fitted", "fix", "fixed", "fixes",
    "fixing", "generate leads", "improve rankings", "increase traffic", "inspect", "inspection",
    "install", "installation", "installing", "installs", "made to measure", "made to order",
    "maintain", "maintenance", "maker", "making", "manage", "mount",
    "mounting", "optimize", "refurbish", "remodel", "remodeling", "renovate",
    "renovation", "repair", "repairing", "repairs", "replace", "replacement",
    "replacing", "restoration", "restore", "run campaign", "service", "services",
    "servicing", "set up", "tailor made", "track conversions", "unblock", "unclog",
    "wash", "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "account disapproved google ads", "ads budget wasted", "ads getting disapproved", "ads suspended",
    "blockage", "blocked", "broke", "broken",
    "burst", "campaign underperforming", "clogged", "conversion rate too low",
    "corroded", "crack", "cracked", "ctr too low",
    "damage", "damaged", "dripping", "fault",
    "faulty", "google ads not converting", "google business profile not showing", "high cost per click",
    "issue", "issues", "jammed", "keyword not ranking",
    "kharab", "landing page not converting", "leakage", "leaking",
    "leaky", "low click through rate", "low google ranking", "low impression share",
    "low pressure", "low quality score", "no leads from ads", "no traffic to website",
    "noise", "noisy", "not turning on", "not working",
    "overflow", "overflowing", "overheating", "poor ad performance",
    "problem", "problems", "rusted", "seo dropped rankings",
    "seo not working", "short circuit", "site not indexed", "site not showing on google",
    "slow", "smell", "smells", "smelly",
    "stopped working", "stuck", "tripping", "vibrating",
    "wasted ad spend", "weak", "website not ranking", "website outdated",
    "website too slow", "won't work", "wont turn", "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "business", "google", "keyword", "management", "research", "website"
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
