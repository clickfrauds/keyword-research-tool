/**
 * 🛡️ NEGATIVE GUARD v2 — Aqua Plumber Dubai Water Pump Services (Dubai, United Arab Emirates)
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
    "core plumbing & emergency services"
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
    "abu dhabi", "ajman", "al ain", "bahrain", "doha", "fujairah",
    "jeddah", "kuwait", "manama", "muscat", "oman", "qatar",
    "rak", "ras al khaimah", "riyadh", "saudi arabia", "sharjah", "umm al quwain"
  ];

  var EDU_CAREER = [
    "academy", "apprenticeship", "booster pump size guide", "business kaise",
    "career", "careers", "catalogue", "certificate",
    "certification", "course", "courses", "cv",
    "datasheet", "define", "definition", "diagram",
    "diploma", "dukan kaise", "geyser wattage guide", "hiring",
    "how do", "how does", "how to become", "how to become a plumber",
    "in hindi", "in urdu", "institute", "internship",
    "interview questions", "items list", "job", "jobs",
    "ka kaam", "ka kam", "kaise bane", "kaise khole",
    "kaise seekhe", "kaise sikhe", "kitne prakar", "kitne type",
    "kitni salary", "kya hai", "kya hota hai", "material list",
    "meaning in", "meaning of", "mechanism of", "name list",
    "pipe fitting course", "pipe size chart", "plumber apprenticeship uae", "plumber banne ka tarika",
    "plumber course dubai", "plumber ka course", "plumber salary dubai", "plumbing certification uae",
    "plumbing diploma dubai", "plumbing license dubai", "plumbing trade school", "pump ki taleem",
    "pump motor winding diagram", "pump technician training", "recruitment", "resume",
    "salaries", "salary", "schematic", "shop kaise",
    "size chart", "solar heater types", "standard height", "submersible pump specs",
    "tool name", "tools list", "tools name", "training",
    "translate", "types of", "types of water heaters", "types of water pumps",
    "vacancies", "vacancy", "wage", "wages",
    "water heater capacity guide", "water pump hp calculator", "water tank capacity guide", "what happens",
    "what is"
  ];

  var INFO_DIY = [
    "difference between", "diy", "diy leak detection", "diy pipe repair",
    "do it yourself", "drain cleaning home remedy", "geyser error code", "ghar par kaise",
    "how to", "how to bleed a pump", "how to clean drain yourself", "how to descale water heater",
    "how to fix leaking pipe diy", "how to reset booster pump", "how to unclog drain at home", "instructions",
    "khud banana", "khud lagana", "khud se", "ki setting",
    "manual", "pump not working troubleshoot", "pump pressure switch adjustment", "pump priming procedure",
    "tutorial", "water heater error code", "water heater reset button", "water heater thermostat setting",
    "water pump settings guide", "what causes", "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "ac repair", "amazon", "ariston distributor", "auction", "b2b", "buy online",
    "career", "carpenter", "carrefour", "contract bidding", "cv", "distributor",
    "dubizzle", "electrician", "for sale", "franchise", "franke", "grohe",
    "hindware", "hiring", "hvac", "import export", "installation course", "internship",
    "jaquar", "job vacancy", "jobs", "ka dam", "ka price", "khareedna",
    "kharidna", "ki qeemat", "kitna hai", "kitne ka", "kohler", "maid service",
    "manufacturer", "marketplace", "noon", "olx", "painter", "part number",
    "pest control", "pump price list", "recruitment", "rent pump", "resume", "roca",
    "salary", "sasta", "second hand", "spare parts for sale", "supplier dubai", "supply chain",
    "tender", "training center", "used pump for sale", "wholesale"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "faucet", "filter", "heater", "motor", "pipe", "pump",
    "tank", "valve"
  ];

  var SAFE_ROOTS = [
    "24 hour emergency plumbing repair", "a plumber", "a plumber near me", "affordable plumber dubai",
    "affordable plumbers near me", "ariston water heater repair dubai", "backed up sewage", "basement sump pump installation",
    "bathroom drain unblocking dubai", "bathroom pipe leak repair dubai", "best drain cleaning service dubai", "best leak detection company dubai",
    "best plumber in dubai", "best water heater company dubai", "best water pump technician dubai", "blocked drain repair cost dubai",
    "booster pump installation", "booster pump repair near me", "borewell motor repair", "borewell pump repair near me",
    "broken water pipe", "burst pipe repair", "burst water pipe", "busted water pipe",
    "ceiling water leak repair dubai", "change out water heater", "change water heater", "cheap plumbers near me",
    "circulation pump installation", "clean septic tank", "cleanout", "cleanout pipe",
    "deep well jet pump installation", "domestic pump", "drain clean out", "drain cleaning",
    "drain cleaning company dubai", "drain cleaning cost", "drain cleaning near me", "drain cleaning service",
    "drain cleaning services", "drain clearing service", "drain clearing services", "drain line cleaning",
    "drain maintenance services", "drain pipe cleaning", "drain service near me", "drain unblocking dubai",
    "drain unblocking services", "electric water heater installation dubai", "emergency drain", "emergency drain unblocking dubai",
    "emergency hot water heater repair", "emergency hot water repair", "emergency hot water replacement", "emergency hot water tank replacement",
    "emergency plumber", "emergency plumber dubai 24 hours", "emergency plumber dubai marina", "emergency plumber near me",
    "emergency plumbing repair", "emergency plumbing services", "emergency plumbing services near me", "emergency water heater installation",
    "emergency water heater repair", "emergency water heater replacement", "emergency water pump repair dubai", "emergency water pump service near me",
    "faucet installation dubai", "floor cleanout", "gas boiler installation", "gas plumber",
    "geyser repair dubai", "grease trap cleaning", "grease trap cleaning dubai", "heater contractors",
    "heater water repair", "hidden water leak detection service", "honda water pump near me", "hot water heater installation",
    "hot water installers", "hot water repair near me", "hot water tank repair near me", "hot water tank replacement cost dubai",
    "hot water technician", "hydro jet", "hydro jetting", "hydro jetting cost dubai",
    "hydro jetting dubai", "hydro jetting near me", "installing a well pump", "irrigation pump installation",
    "jetting drain lines", "jojo tank installation with pump", "jojo tank pump installation", "kitchen faucet repair",
    "kitchen sink leak repair", "kitchen sink unblocking dubai", "leak detection", "leak detection company near me",
    "leak detection specialist near me", "local plumber near me", "local plumbers", "local plumbers close to me",
    "low hot water pressure", "motor and pump repair", "motor pump repair", "my plumber",
    "near me plumber", "near me plumber service", "near plumber me", "nearest plumber",
    "pipe cleaning near me", "pipe installation", "pipe leak repair dubai", "pipe leak survey dubai",
    "pipe replacement", "plumb near me", "plumb quick", "plumber",
    "plumber dubai price list", "plumber near me", "plumber near me home service", "plumber near me near me",
    "plumber near near me", "plumber plumber near me", "plumbers close to me", "plumbers in near me",
    "plumbers near me", "plumbers near me affordable", "plumbing cleanout", "plumbing company dubai",
    "plumbing emergency service near me", "plumbing line", "plumbing maintenance contract dubai", "plumbing repair",
    "plumbing repair near me", "plumbing repair services", "plumbing repair services near me", "plumbing services",
    "plumbing services near me", "pressure pump repair dubai", "pressure pump service", "pump septic tank near me",
    "pump technician near me dubai", "recirculating pump installation", "repair plumbers near me", "repair water heater near me",
    "repair water pump near me", "replacement water heater", "same day plumber dubai", "same day plumber near me",
    "septic sewer cleaning", "septic tank clean up", "septic tank cleaning dubai", "septic tank cleaning near me",
    "septic tank cleaning services", "septic tank pumping cost dubai", "septic tank repair", "servis water heater",
    "sewage drain", "sewage pump repair dubai", "sewage tank cleaning services", "sewer cleaning company",
    "sewer cleaning services", "sewer line cleaning near me", "sewer line repair", "sewer line repair dubai",
    "sewer line unblocking dubai", "shower leak", "shower pump installation", "slab leak detection dubai",
    "slab leak repair cost", "solar heater repair near me", "solar hot water heater repair", "solar hot water repairs",
    "solar water heater repair", "solar water heater repair dubai", "solar water heater repair near me", "solar water repair",
    "solex water pump repair", "submersible motor repair", "submersible pump installation", "submersible pump motor repair",
    "submersible pump repair dubai", "submersible pump repair near me", "submersible pump repairs near me", "submersible repair",
    "submersible water pump repair", "tankless water heater repair dubai", "tap repair", "the local plumbers",
    "toilet gutter cleaning", "toilet installation cost", "toilet leak repair dubai", "toilet repair",
    "toilet repair dubai cost", "toilet repair near me", "underground pipe leak detection", "underground pipe leak detection dubai",
    "upvc clean out", "urgent plumber", "villa plumber dubai", "villa plumbing services dubai",
    "villa water leak detection dubai", "villa water pump maintenance", "villa water pump repair dubai", "water heater circuit breaker",
    "water heater dripping", "water heater emergency repair", "water heater in plumbing", "water heater installation",
    "water heater installation near me", "water heater leakage", "water heater leaking", "water heater maintenance",
    "water heater not heating fix", "water heater overflow pipe", "water heater plumbing", "water heater repair",
    "water heater repair cost dubai", "water heater repair emergency", "water heater repair near me", "water heater replacement",
    "water heater replacement near me", "water heater replacement price dubai", "water heater service", "water heater service technician",
    "water heater technician", "water heater technician dubai", "water leak detection", "water leak detection dubai cost",
    "water leak detection services near me", "water leak repair", "water leak repair cost dubai", "water leaking from water heater",
    "water motor mechanic near me", "water motor pump near me", "water motor repair", "water motor repair dubai",
    "water motor repair near me", "water pressure booster repair", "water pump installation cost dubai", "water pump maintenance contract dubai",
    "water pump motor near me", "water pump motor repair", "water pump price dubai", "water pump repair dubai",
    "water pump repair near me", "water pump replacement cost dubai", "water pump station", "water pump supply near me",
    "water pumps near me", "water tank and pump installation", "water tank cleaning dubai", "water tank leakage repair",
    "water tank pump installation", "water well pump installation", "well pump pressure switch replacement", "well pump service dubai",
    "wells service near me", "تصليح المضخة الماء", "تصليح مضخة ماء"
  ];

  var PRODUCTS = [
    "affordable", "ariston", "calpeda", "cleanout", "cost", "dab pump",
    "detection", "drain", "electric water heater", "franklin electric", "grundfos", "heater",
    "hydro", "jetting", "kirloskar pump", "leak", "line", "lorentz pump",
    "motor", "pentax pump", "pipe", "plumber", "plumbers", "plumbing",
    "pressure", "price", "pump", "rain water pump", "septic", "sewage",
    "sewer", "solar", "solar water heater", "submersible", "tank", "toilet",
    "unblocking", "villa", "water", "well", "wilo"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "bespoke", "book",
    "booking", "build", "builder", "builders", "call", "certified",
    "change", "changing", "check", "clean", "cleaner", "cleaning",
    "companies", "company", "contact", "contract", "contractor", "custom",
    "deep cleaning", "descale", "design", "designer", "detect leak", "diagnose",
    "emergency", "expert", "fast", "fix", "fixed", "fixes",
    "fixing", "flush drain", "help", "hire", "in my area", "inspect",
    "inspection", "install", "installation", "installing", "installs", "jet wash drain",
    "licensed", "local", "made to measure", "made to order", "maintain", "maintenance",
    "maker", "makers", "making", "near me", "nearby", "now",
    "number", "pressurize", "professional", "quick", "quotation", "quote",
    "quotes", "recalibrate", "recharge pump", "reline pipe", "relocate", "relocation",
    "removal", "remove", "repair", "repairing", "repairs", "repipe",
    "replace", "replacement", "replacing", "replumb", "reroute pipe", "rewire pump motor",
    "same day", "service", "services", "servicing", "solution", "specialist",
    "tailor made", "technician", "today", "trusted", "unblock", "unclog",
    "urgent", "wash", "washing", "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "build", "builder", "clean", "cleaning",
    "custom", "descale", "design", "designer", "detect", "detect leak",
    "detection", "fabrication", "fitted", "fix", "fixed", "fixes",
    "fixing", "flush drain", "inspect", "inspection", "install", "installation",
    "installing", "installs", "jet wash drain", "made to measure", "made to order", "maintain",
    "maintenance", "maker", "making", "mount", "mounting", "pressurize",
    "recalibrate", "recharge pump", "refurbish", "reline pipe", "remodel", "remodeling",
    "renovate", "renovation", "repair", "repairing", "repairs", "repipe",
    "replace", "replacement", "replacing", "replumb", "reroute pipe", "restoration",
    "restore", "rewire pump motor", "service", "services", "servicing", "tailor made",
    "unblock", "unclog", "wash", "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "bad smell from drain", "blockage", "blocked", "broke",
    "broken", "burst", "clogged", "corroded",
    "crack", "cracked", "damage", "damaged",
    "drain blocked", "drain overflowing", "drain slow", "dripping",
    "fault", "faulty", "geyser leaking", "hot water not coming",
    "issue", "issues", "jammed", "kharab",
    "leakage", "leaking", "leaky", "low pressure",
    "low water pressure", "no hot water", "no water pressure", "noise",
    "noisy", "not turning on", "not working", "overflow",
    "overflowing", "overheating", "pipe burst", "pipe corroded",
    "problem", "problems", "pump losing pressure", "pump making noise",
    "pump not starting", "pump not working", "pump tripping", "pump vibrating",
    "rusted", "sewage backup", "short circuit", "sink clogged",
    "slow", "smell", "smells", "smelly",
    "stopped working", "stuck", "toilet not flushing", "toilet overflowing",
    "tripping", "vibrating", "water coming from ceiling", "water dripping from pipe",
    "water heater leaking", "water heater making noise", "water heater not working", "water leaking",
    "water not heating", "water pooling", "water tank overflowing", "weak",
    "won't work", "wont turn", "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "detection", "heater", "plumber", "plumbers", "plumbing", "septic"
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
