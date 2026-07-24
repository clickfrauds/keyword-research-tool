/**
 * 🛡️ NEGATIVE GUARD v2 — SEOBlogy (United Arab Emirates)
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
    "core ppc services - uae"
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

  var FORBIDDEN_LOCATIONS = [
    "amman", "bahrain", "beirut", "cairo", "doha", "egypt",
    "jeddah", "jordan", "ksa", "kuwait", "lebanon", "manama",
    "muscat", "oman", "qatar", "riyadh", "saudi arabia", "البحرين",
    "الدوحة", "الرياض", "القاهرة", "الكويت", "جدة", "عمان",
    "قطر", "مصر"
  ];

  var EDU_CAREER = [
    "academy", "adwords certification exam", "adwords exam questions", "apprenticeship",
    "business kaise", "campaign types explained", "career", "careers",
    "catalogue", "certificate", "certification", "course",
    "courses", "cpc meaning", "cpm vs cpc", "cv",
    "datasheet", "define", "definition", "diagram",
    "digital marketing bootcamp uae", "digital marketing diploma", "digital marketing institute uae", "diploma",
    "dukan kaise", "google ads certification", "google ads course dubai", "google ads exam answers",
    "google ads keyword planner tutorial", "google ads specialist job description", "google ads terminology glossary", "google ads training course",
    "google ads tutorial for beginners", "google skillshop", "hiring", "how do",
    "how does", "how to become", "how to become a ppc specialist", "in hindi",
    "in urdu", "institute", "internship", "interview questions",
    "items list", "job", "jobs", "ka kaam",
    "ka kam", "kaise bane", "kaise khole", "kaise seekhe",
    "kaise sikhe", "kitne prakar", "kitne type", "kitni salary",
    "kya hai", "kya hota hai", "learn google ads free", "material list",
    "meaning in", "meaning of", "mechanism of", "name list",
    "ppc analyst salary uae", "ppc internship dubai", "ppc manager salary dubai", "quality score explained",
    "recruitment", "resume", "rsa vs eta ads", "salaries",
    "salary", "schematic", "shop kaise", "size chart",
    "standard height", "tool name", "tools list", "tools name",
    "training", "translate", "types of", "types of google ads campaigns",
    "vacancies", "vacancy", "wage", "wages",
    "what happens", "what is"
  ];

  var INFO_DIY = [
    "difference between", "diy", "diy google ads setup", "do it yourself",
    "ghar par kaise", "google ads account suspended fix", "google ads conversion tracking setup guide", "google ads disapproved ad fix",
    "google ads free guide", "google ads help center", "google ads policy violation fix", "google ads support number",
    "how to bid on keywords", "how to create rsa ads", "how to improve quality score", "how to link google ads to analytics",
    "how to lower cpc google ads", "how to set up google ads myself", "how to target keywords in google ads", "how to write negative keywords",
    "instructions", "khud banana", "khud lagana", "khud se",
    "ki setting", "manual", "tutorial", "what causes",
    "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "accenture", "affiliate marketing", "app development", "b2b marketplace", "backlinks service", "billboard advertising",
    "bing ads agency", "buy now", "call center outsourcing", "career", "content writing", "copywriting service",
    "crm software", "data entry", "distributor", "domain registration", "dropshipping", "email marketing tool",
    "facebook ads agency", "facebook ads course", "for sale", "franchise", "graphic design", "graphic designer near me",
    "hosting provider", "instagram ads agency", "internship", "job", "jobs", "ka dam",
    "ka price", "khareedna", "kharidna", "ki qeemat", "kitna hai", "kitne ka",
    "link building", "logo design", "manufacturer", "ogilvy", "print advertising", "radio advertising",
    "recruitment agency", "rent", "salary", "sasta", "second hand", "seo agency",
    "seo company", "seo course", "seo services", "seo training", "shopify developer", "smm panel",
    "social media management", "software development", "staffing agency", "supplier", "tiktok ads agency", "translation service",
    "tv commercial", "used", "vacancy", "video editing service", "virtual assistant", "vpn service",
    "web design", "web development", "wholesale", "wix", "wordpress developer", "wpp"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "advertising", "agency", "campaign", "cost", "display", "management",
    "marketing", "setup", "shopping"
  ];

  var SAFE_ROOTS = [
    "ads google com local services ads", "adwords agency near me", "adwords companies", "adwords management companies",
    "adwords marketing agency", "affordable google ads management uae", "agency google adwords", "best ppc agency in dubai",
    "conversion tracking setup service", "display ads agency uae", "done for you ppc", "ecommerce ppc management uae",
    "get listed on google local services ads uae", "google ad agency", "google ad company", "google ads account audit dubai",
    "google ads account management uae", "google ads agency abu dhabi", "google ads api integration", "google ads audit and fix",
    "google ads campaign setup uae", "google ads companies", "google ads expert uae", "google ads for cleaning business",
    "google ads for construction companies", "google ads for dentists dubai", "google ads for estate agents", "google ads for hvac companies uae",
    "google ads for junk removal", "google ads for landscaping companies uae", "google ads for law firms", "google ads for logistics companies dubai",
    "google ads for moving companies", "google ads for pest control dubai", "google ads for real estate agents", "google ads for restaurants dubai",
    "google ads for salons uae", "google ads for service business", "google ads for small business uae", "google ads local",
    "google ads management company", "google ads management dubai cost", "google ads management for small business", "google ads management pricing uae",
    "google ads marketing agency near me", "google ads services agency", "google adwords advertising agency", "google adwords company",
    "google adwords management company", "google display advertising agency", "google display advertising companies", "google display network ads dubai cost",
    "google guaranteed", "google guaranteed ads", "google guaranteed application help uae", "google guaranteed badge dubai",
    "google guaranteed business", "google guaranteed cost dubai", "google guaranteed setup service dubai", "google local ad services",
    "google local ads", "google local ads pricing uae", "google local advertising", "google local leads",
    "google local search ads", "google local service", "google local service ads", "google local services ads setup dubai",
    "google local services ads verification uae", "google map ads management uae", "google maps local search ads", "google marketing firm",
    "google ppc advertising agency", "google screened businesses uae", "google shopping ads agency", "google shopping ads management dubai",
    "google shopping campaign setup dubai", "google shopping management company", "hire a google ads specialist", "hire a google adwords consultant",
    "hire adwords expert", "hire adwords professional", "hire adwords specialist", "hire dedicated adwords expert",
    "hire google ads specialist", "hire google adwords expert", "hire ppc expert dubai", "how to get google guaranteed in uae",
    "keyword research service dubai", "landing page for ads uae", "local ads in google ads", "local advertising google",
    "local google service ads", "local search ad", "local search ads on google maps", "local service ads management abu dhabi",
    "local service ads management uae", "local service google ads", "local services ads", "local services ads by google",
    "local services ads dubai cost", "local services ads for contractors dubai", "local services ads google", "monthly google ads management package uae",
    "negative keyword setup", "ppc agency for service business", "ppc agency for service businesses dubai", "ppc campaign management service uae",
    "ppc campaign setup", "ppc for interior design companies uae", "ppc management dubai", "ppc online advertising",
    "recommended google marketing companies", "retail google ads management uae", "rsa ad copywriting service", "shopping ads for online stores dubai"
  ];

  var PRODUCTS = [
    "advertising", "adwords", "agency", "business", "campaign", "cost",
    "display", "dubai", "google", "guaranteed", "management", "marketing",
    "search", "setup", "shopping"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "audit", "bespoke",
    "book", "booking", "boost", "build", "builder", "builders",
    "call", "certified", "change", "changing", "check", "clean",
    "cleaner", "cleaning", "companies", "company", "contact", "contract",
    "contractor", "custom", "deep cleaning", "design", "designer", "diagnose",
    "emergency", "expert", "fast", "fix", "fixed", "fixes",
    "fixing", "get approved", "get verified", "help", "hire", "in my area",
    "inspect", "inspection", "install", "installation", "installing", "installs",
    "integrate", "launch", "licensed", "local", "made to measure", "made to order",
    "maintain", "maintenance", "maker", "makers", "making", "manage",
    "near me", "nearby", "now", "number", "optimize", "outsource",
    "professional", "push live", "quick", "quotation", "quote", "quotes",
    "relocate", "relocation", "removal", "remove", "repair", "repairing",
    "repairs", "replace", "replacement", "replacing", "same day", "scale",
    "service", "services", "servicing", "set up", "solution", "specialist",
    "tailor made", "technician", "today", "trusted", "urgent", "verify",
    "wash", "washing", "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "audit", "bespoke", "boost", "build", "builder",
    "clean", "cleaning", "custom", "design", "designer", "detect",
    "detection", "fabrication", "fitted", "fix", "fixed", "fixes",
    "fixing", "get approved", "get verified", "inspect", "inspection", "install",
    "installation", "installing", "installs", "integrate", "launch", "made to measure",
    "made to order", "maintain", "maintenance", "maker", "making", "manage",
    "mount", "mounting", "optimize", "outsource", "push live", "refurbish",
    "remodel", "remodeling", "renovate", "renovation", "repair", "repairing",
    "repairs", "replace", "replacement", "replacing", "restoration", "restore",
    "scale", "service", "services", "servicing", "set up", "tailor made",
    "unblock", "unclog", "verify", "wash", "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "account suspended help", "ads disapproved need help", "ads getting clicks no sales", "ads not showing up",
    "ads spending too much", "blockage", "blocked", "broke",
    "broken", "burst", "campaign not generating leads", "clogged",
    "conversion rate too low", "corroded", "crack", "cracked",
    "ctr too low fix", "damage", "damaged", "dripping",
    "fault", "faulty", "google ads not converting", "high cpc no results",
    "impressions but no clicks", "issue", "issues", "jammed",
    "kharab", "landing page not converting", "leads not qualified", "leakage",
    "leaking", "leaky", "low leads from ads", "low pressure",
    "low quality score fix", "low roi on ppc", "need google guaranteed badge help", "need help managing ads account",
    "need local leads", "need more customers", "no calls from google ads", "noise",
    "noisy", "not ranking on google ads", "not turning on", "not working",
    "overflow", "overflowing", "overheating", "poor ad performance",
    "problem", "problems", "rusted", "short circuit",
    "slow", "smell", "smells", "smelly",
    "stopped working", "struggling with google ads budget", "stuck", "tripping",
    "vibrating", "wasting money on ads", "weak", "won't work",
    "wont turn", "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "advertising", "adwords", "agency", "google", "guaranteed", "management"
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
