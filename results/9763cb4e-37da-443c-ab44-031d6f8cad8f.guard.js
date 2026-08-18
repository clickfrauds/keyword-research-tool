/**
 * 🛡️ NEGATIVE GUARD v2 — Dubai Water Leak Detection & Repair (Dubai, United Arab Emirates)
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
    "water leak detection dubai"
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
    "abu dabi", "abu dhabi", "ajman", "al ain", "bahrain", "doha",
    "fujairah", "kuwait", "muscat", "oman", "qatar", "ras al khaimah",
    "riyadh", "saudi arabia", "sharjah", "umm al quwain", "ابوظبي", "الشارقة",
    "شارجة", "عجمان"
  ];

  var EDU_CAREER = [
    "academy", "acoustic leak detector price", "apprenticeship", "best leak detection machine",
    "business kaise", "career", "careers", "catalogue",
    "certificate", "certification", "correlator leak detection device", "course",
    "courses", "cv", "datasheet", "define",
    "definition", "diagram", "diploma", "dukan kaise",
    "gas leak detector vs water leak detector", "hiring", "how do", "how does",
    "how to become", "how to become a leak detection technician", "in hindi", "in urdu",
    "institute", "internship", "interview questions", "items list",
    "job", "jobs", "ka kaam", "ka kam",
    "kaise bane", "kaise khole", "kaise seekhe", "kaise sikhe",
    "kitne prakar", "kitne type", "kitni salary", "kya hai",
    "kya hai leak detection", "kya hota hai", "leak detection course dubai", "leak detection equipment brands",
    "leak detection equipment for sale", "leak detection kaise hota hai", "leak detection machine specifications", "leak detection technician salary dubai",
    "leak detection tool kit", "material list", "meaning in", "meaning of",
    "mechanism of", "moisture meter types", "name list", "pipe size chart uae",
    "plumbing license uae", "plumbing trade school dubai", "pvc pipe sizes uae", "recruitment",
    "resume", "salaries", "salary", "schematic",
    "shop kaise", "size chart", "standard height", "thermal imaging camera specs",
    "tool name", "tools list", "tools name", "training",
    "translate", "types of", "types of leak detection methods", "types of water leak sensors",
    "vacancies", "vacancy", "wage", "wages",
    "water leak sensor comparison", "what happens", "what is", "أنواع أجهزة كشف تسربات المياه",
    "كيف يعمل جهاز كشف تسرب المياه", "پانی کے رساؤ کا پتہ لگانا کیسے کریں"
  ];

  var INFO_DIY = [
    "difference between", "diy", "diy leak detection", "diy slab leak fix",
    "do it yourself", "ghar par kaise", "how to", "how to check water meter for leak",
    "how to detect water leak at home", "how to find hidden water leak", "how to fix pipe leak yourself", "how to read water meter for leak",
    "how to seal pvc pipe leak diy", "how to stop pipe leak temporarily", "how to test for water leak", "instructions",
    "khud banana", "khud lagana", "khud se", "ki setting",
    "leak detection dye test", "manual", "tutorial", "water leak test method",
    "what causes", "wikipedia", "youtube", "تسرب المياه كيف تكتشفه بنفسك",
    "پانی کا رساؤ خود کیسے ٹھیک کریں"
  ];

  var FORBIDDEN_WORDS = [
    "ac repair", "b2b", "belhasa", "buy", "career", "carpenter dubai",
    "certification exam", "cleaning company dubai", "course", "distributor", "distributor uae", "drain cleaning company",
    "dubai municipality complaint", "electrician dubai", "for sale", "franchise", "generator rental", "grout cleaning",
    "handyman dubai", "hiring", "hvac repair", "interior design", "internship", "job",
    "jobs", "ka dam", "ka price", "khareedna", "kharidna", "ki qeemat",
    "kitna hai", "kitne ka", "landscaping dubai", "manufacturer", "painting services", "pest control",
    "plumber salary", "plumbing course", "price list pdf", "quotation template", "renovation company", "rent",
    "rental", "rfq", "roof repair", "roto rooter", "salary", "sasta",
    "servpro", "sewage tanker", "spare parts", "supplier", "swimming pool cleaning", "tender",
    "tile installation", "training", "used", "vacancy", "water tank cleaning dubai", "waterproofing company",
    "wholesale"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "detector", "hose", "joint", "line", "machine", "pipe",
    "pipes", "sensor", "system"
  ];

  var SAFE_ROOTS = [
    "24 hour leak repair dubai", "acoustic leak detection dubai", "affordable leak detection dubai", "bath leaking from waste pipe",
    "bathroom leak repair dubai cost", "bathroom sink drain leak", "bathroom sink leak underneath", "bathroom sink leaking drain pipe",
    "bathroom sink leaking underneath", "bathroom water leak detection", "bathtub drain pipe leaking", "bathtub pipes leaking",
    "best water leak detection company", "best water leak detection company in dubai", "boiler pipes leaking", "book water leak survey dubai",
    "broken pipe under concrete slab", "broken pipe under slab", "broken pvc pipe repair", "building water leak monitoring system dubai",
    "busted water heater", "cast iron pipe leaking", "certified leak detection technician dubai", "chilled water leak detection system",
    "commercial leak detection system installation", "concrete slab leak repair", "concrete slab leak repair cost", "concrete slab leak repair near me",
    "concrete slab water leak", "concrete slab water leak repair", "condensation pipe leaking", "copper pipe leak repair dubai",
    "copper water line repair", "cost to fix slab leak", "cracked pipe under slab", "cracked pvc pipe",
    "cracked pvc pipe repair", "detect water leaks", "detecting underground water", "detection services",
    "detector leak water", "dripping water pipe", "electronic leak detection dubai", "emergency leak detection",
    "emergency leak detection near me dubai", "emergency leak repair dubai", "emergency pipe leak repair", "emergency plumber leak dubai",
    "emergency plumbing leak repair", "emergency slab leak repair dubai", "emergency water leak detection", "find a leak",
    "find my leak", "find the leak", "fix a broken pipe", "fix a broken pvc pipe",
    "fix a cracked pipe", "fix a cracked pvc pipe", "fix a water pipe leak", "fix broken pvc pipe",
    "fix cracked pvc pipe", "fix leaky pvc joint", "fix main water line leak", "fix pinhole leak",
    "fix slab foundation", "fix slab leak", "fix water line", "fix water main leak",
    "fix water pipe leak", "fixing a cracked pvc pipe", "fixing a slab leak", "fixing cracked pvc pipe",
    "flood leak detection dubai", "foundation leak", "garden pipe leak detection", "ground water detection services",
    "hidden leak", "hose leaks at faucet", "hot water leak in slab", "hot water slab leak",
    "irrigation leak detection dubai", "joint leak", "kitchen sink leak repair company dubai", "kitchen sink leak underneath",
    "kitchen sink leaking underneath", "leak detection", "leak detection company", "leak detection company near me",
    "leak detection control panel", "leak detection cost", "leak detection price", "leak detection prices",
    "leak detection service dubai cost", "leak detection services", "leak detection specialist near me", "leak detection system cost",
    "leak detection system for villa dubai", "leak detection water meter", "leak detector for water", "leak detector service",
    "leak from washing machine hose", "leak in concrete slab", "leak in pvc joint", "leak near me",
    "leak repair without breaking tiles", "leak service", "leak specialist", "leak under bathroom sink",
    "leak under concrete floor", "leak under concrete slab", "leak under kitchen sink", "leakage checking",
    "leakage of water pipes", "leakage on wall", "leakage sensor water", "leaking cast iron pipe",
    "leaking detection company", "leaking drain pipe in wall", "leaking pvc", "leaking pvc joint",
    "leaking sewage", "leaking sink drain pipe", "leaking soil pipe", "leaking toilet inlet pipe",
    "leaky sink drain pipe", "main line leak detection", "main line leak repair", "main line water leak repair near me dubai",
    "main water line leak repair", "main water line repair cost dubai", "main water pipe repair", "metal pipe repair",
    "moisture detection dubai", "moisture leak detector", "my sink is leaking", "non invasive leak detection",
    "pinhole leak in pipe", "pinhole leak repair", "pinhole pipe leak", "pipe dripping water",
    "pipe is leaking water", "pipe leak repair cost dubai", "pipe leak repair dubai", "pipe leak repair quote dubai",
    "pipe water leakage", "plumbers slab leak repair", "plumbing in slab", "plumbing on slab foundation",
    "plumbing under slab repair", "ppr pipe leak repair", "pressurized pvc leak repair", "professional leak detection",
    "professional leak detector", "pvc leak", "pvc pipe broken", "pvc pipe leak repair near me dubai",
    "repair cracked pipe", "repair cracked pvc fitting", "repair galvanized pipe", "repair slab",
    "repair underground water line", "repair water leak in concrete slab", "repair water leak under concrete slab", "repair water pipe leak in concrete slab",
    "residential pipe leak repair dubai", "same day emergency leak repair dubai", "same day pipe leak repair dubai", "same day water leak detection dubai",
    "sensor to detect water leaks", "sensor water leak", "sensors to detect water leakage", "shower drain leaks",
    "shower drain pipe leaking", "shower leak", "shower leak repair cost dubai", "sink drain leak",
    "sink is leaking from drain", "sink leak repair dubai", "sink leaking", "sink leaking underneath",
    "sink leaks underneath", "slab leak", "slab leak cost to fix", "slab leak detection company dubai",
    "slab leak detection services", "slab leak repair", "slab leak repair cost", "slab leak repair cost dubai",
    "slab leak repair dubai", "slab leak repair dubai price", "slab leak repairs", "slab leak solutions",
    "slab leaking", "slab leaks repair", "slab plumbing", "slab plumbing leak",
    "slab repair", "slab water leak", "smart water leak detection system dubai", "soil pipe leaking",
    "stopcock leaking", "sump pump check valve leaking", "swimming pool leak detection dubai", "the sink is leaking",
    "the water pipe is leaking", "thermal leak detection dubai", "toilet base leak", "toilet leak repair near me dubai",
    "trenchless underground pipe repair dubai", "under kitchen sink leaking", "under sink leak", "under slab pipe leak repair dubai",
    "under slab plumbing repair", "under slab water leak repair", "underground galvanized pipe repair", "underground leak",
    "underground leak detection dubai", "underground leakage", "underground pipe detection", "underground pipe leak detection equipment service",
    "underground pipe leak detection services", "underground pipe repair cost", "underground water detector service", "underground water leak repair",
    "underground water leak repair company dubai", "underground water pipe leak detection dubai", "underground water tank leakage repair", "urgent pipe burst repair dubai",
    "urgent water leak repair dubai", "villa leak detection dubai", "villa slab leak repair dubai", "villa water leak detection dubai",
    "washer pipe leaking", "washing machine hose leak repair dubai", "washing machine hose leaking", "washing machine pipe leaking",
    "washing machine water hose leaking", "washing machine water pipe leaking", "water detection leak", "water detector leak",
    "water dripping from water heater overflow pipe", "water dripping pipe", "water heater leak repair dubai", "water heater leaking from overflow pipe",
    "water heater overflow pipe dripping", "water leak alarm system installation cost", "water leak company near me", "water leak detection",
    "water leak detection and repair near me", "water leak detection company dubai", "water leak detection company near me", "water leak detection dubai",
    "water leak detection dubai price", "water leak detection meter", "water leak detection near me dubai marina", "water leak detection sensor",
    "water leak detection specialist near me", "water leak detection system cost", "water leak detection system installation dubai", "water leak detection system price",
    "water leak detector", "water leak detector sensor", "water leak inspection", "water leak repair",
    "water leak repair services", "water leak sensor", "water leak sensor installation service dubai", "water leak services near me",
    "water leak specialist", "water leak specialist near me", "water leak survey dubai", "water leakage detection",
    "water leakage sensor", "water leaking from bathroom floor", "water leaking from overflow pipe on water heater", "water leaking from pipe",
    "water leaking from pipe in basement", "water leaking from water heater overflow pipe", "water leaking through walls", "water line leak",
    "water line repair service", "water line repairs", "water lines in concrete slab", "water main leak repair",
    "water main line replacement dubai", "water pipe burst repair dubai cost", "water pipe is leaking", "water pipe leak repair",
    "water pipe repair company dubai", "water sensor leak detector", "water service line repair", "water tank leak detection",
    "water tank overflow pipe", "waterline leak repair"
  ];

  var PRODUCTS = [
    "bathroom", "broken", "concrete", "cost", "cracked", "detect",
    "detection", "detector", "drain", "dripping", "find", "flir",
    "fluxus", "foundation", "from", "heater", "hose", "hydrophon",
    "joint", "kitchen", "leak", "leakage", "leaking", "leaks",
    "line", "machine", "main", "overflow", "pinhole", "pipe",
    "pipes", "plumbing", "price", "ridgid", "sensor", "sewerin",
    "shower", "sink", "slab", "system", "toilet", "trotec",
    "under", "underground", "underneath", "villa", "water"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "bespoke", "book",
    "booking", "build", "builder", "builders", "call", "certified",
    "change", "changing", "check", "clean", "cleaner", "cleaning",
    "companies", "company", "contact", "contract", "contractor", "custom",
    "deep cleaning", "design", "designer", "detect", "diagnose", "emergency",
    "expert", "fast", "fix", "fixed", "fixes", "fixing",
    "help", "hire", "in my area", "inspect", "inspection", "install",
    "installation", "installing", "installs", "isolate", "licensed", "local",
    "locate", "made to measure", "made to order", "maintain", "maintenance", "maker",
    "makers", "making", "monitor", "near me", "nearby", "now",
    "number", "patch", "pinpoint", "professional", "quick", "quotation",
    "quote", "quotes", "reline", "relocate", "relocation", "removal",
    "remove", "repair", "repairing", "repairs", "replace", "replacement",
    "replacing", "reroute", "same day", "service", "services", "servicing",
    "solution", "specialist", "survey", "tailor made", "technician", "today",
    "trace", "trusted", "urgent", "wash", "washing", "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "build", "builder", "clean", "cleaning",
    "custom", "design", "designer", "detect", "detection", "fabrication",
    "fitted", "fix", "fixed", "fixes", "fixing", "inspect",
    "inspection", "install", "installation", "installing", "installs", "isolate",
    "locate", "made to measure", "made to order", "maintain", "maintenance", "maker",
    "making", "monitor", "mount", "mounting", "patch", "pinpoint",
    "refurbish", "reline", "remodel", "remodeling", "renovate", "renovation",
    "repair", "repairing", "repairs", "replace", "replacement", "replacing",
    "reroute", "restoration", "restore", "service", "services", "servicing",
    "survey", "tailor made", "trace", "unblock", "unclog", "wash",
    "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "blockage", "blocked", "broke", "broken",
    "burst", "ceiling water stain", "clogged", "corroded",
    "crack", "cracked", "damage", "damaged",
    "damp patch on wall", "damp under carpet", "dripping", "fault",
    "faulty", "floor tiles lifting water", "foundation crack water", "garden water leak",
    "hissing sound from pipe", "issue", "issues", "jammed",
    "kharab", "leakage", "leaking", "leaking under floor",
    "leaky", "low pressure", "mold smell", "musty smell in house",
    "noise", "noisy", "not turning on", "not working",
    "overflow", "overflowing", "overheating", "pipe burst",
    "problem", "problems", "rusted", "short circuit",
    "shower leaking into wall", "sink leaking underneath", "slow", "smell",
    "smells", "smelly", "stopped working", "stuck",
    "swimming pool water loss", "toilet leaking from base", "tripping", "underground pipe burst",
    "unexplained water usage", "vibrating", "villa water leak", "wall paint bubbling water",
    "water bill suddenly high", "water coming from wall", "water dripping from ceiling", "water main burst",
    "water meter running when off", "water pooling under sink", "water pressure dropped suddenly", "water seeping from slab",
    "water seeping through floor", "weak", "wet spot on floor", "won't work",
    "wont turn", "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "concrete", "cracked", "detection", "leaking", "system", "underground"
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
