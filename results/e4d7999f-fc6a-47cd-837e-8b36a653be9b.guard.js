/**
 * 🛡️ NEGATIVE GUARD v2 — Washer Dryer Repair Dubai (Dubai, United Arab Emirates)
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
    "Washing Machine & Dryer Repair"
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
    "jeddah", "ksa", "kuwait", "muscat", "oman", "qatar",
    "rak", "ras al khaimah", "riyadh", "saudi", "sharjah", "umm al quwain"
  ];

  var EDU_CAREER = [
    "academy", "appliance repair apprenticeship", "appliance repair certification", "appliance repair course dubai",
    "appliance repair tools list", "appliance technician salary dubai", "apprenticeship", "business kaise",
    "career", "careers", "catalogue", "certificate",
    "certification", "compressor hp guide", "compressor types explained", "course",
    "courses", "cv", "datasheet", "define",
    "definition", "diagram", "diploma", "dishwasher motor specs",
    "dishwasher pump specs", "dryer belt size chart", "dryer voltage specs uae", "dukan kaise",
    "hiring", "how do", "how does", "how to become",
    "how to become appliance technician", "hvac technician course", "in hindi", "in urdu",
    "institute", "internship", "interview questions", "items list",
    "job", "jobs", "ka kaam", "ka kam",
    "kaise bane", "kaise khole", "kaise seekhe", "kaise sikhe",
    "kitne prakar", "kitne type", "kitni salary", "kya hai",
    "kya hota hai", "material list", "meaning in", "meaning of",
    "mechanism of", "multimeter for appliance repair", "name list", "recruitment",
    "refrigerant types for fridges", "refrigeration technician diploma", "refrigerator gas types", "resume",
    "salaries", "salary", "schematic", "shop kaise",
    "size chart", "standard height", "tool name", "tools list",
    "tools name", "training", "translate", "types of",
    "types of washing machine repairs", "vacancies", "vacancy", "wage",
    "wages", "washer dryer combo specs", "washing machine capacity guide", "washing machine motor rpm chart",
    "washing machine motor specs", "washing machine repair course near me", "washing machine repair syllabus", "washing machine repair training",
    "what happens", "what is"
  ];

  var INFO_DIY = [
    "difference between", "dishwasher error code", "dishwasher not draining troubleshoot", "diy",
    "do it yourself", "dryer error code", "dryer not heating troubleshoot", "dryer settings guide",
    "fridge error code", "fridge not cooling troubleshoot", "ghar par kaise", "how to",
    "how to clean washing machine filter", "how to descale dishwasher", "how to fix e3 error", "how to fix f1 error",
    "how to reset bosch washing machine", "how to reset samsung dryer", "instructions", "khud banana",
    "khud lagana", "khud se", "ki setting", "manual",
    "reset dishwasher", "reset dryer", "reset washing machine", "tutorial",
    "washing machine drum noise diagnosis", "washing machine not spinning troubleshoot", "washing machine settings guide", "what causes",
    "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "ac repair", "air conditioner repair", "amazon", "auction", "buy", "car repair",
    "career", "careers", "carpenter", "carpet cleaning", "carrefour", "certificate course",
    "cleaning company", "cleaning services", "computer repair", "curtain", "delivery service", "distributor",
    "distributorship", "dubizzle", "electrician", "for sale", "franchise", "furniture repair",
    "handyman", "hiring", "interior design", "internship", "job", "jobs",
    "ka dam", "ka price", "khareedna", "kharidna", "ki qeemat", "kitna hai",
    "kitne ka", "laptop repair", "maid service", "manufacturer", "marketplace", "mobile repair",
    "movers", "noon", "olx", "packers", "painter", "pest control",
    "plumber", "real estate", "renovation", "rent", "rental", "reseller",
    "salary", "sasta", "second hand", "sharaf dg", "sofa cleaning", "supplier",
    "training course", "tv repair", "used", "vacancy", "wholesale"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "cost", "door", "machine", "mini", "parts", "seal",
    "shop", "shops", "spare"
  ];

  var SAFE_ROOTS = [
    "24 hour appliance repair", "24 hour appliance repair dubai", "ac refrigerator repair near me", "ac washing machine repair",
    "ac washing machine repair near me", "annual maintenance contract appliance", "appliance maintenance contract dubai", "appliance repair al quoz",
    "appliance repair bosch dishwasher", "appliance repair express", "appliance repair near me", "appliance repair near me now",
    "appliance repair samsung dryer", "appliance repair whatsapp booking", "appliance technician dubai", "ariston washing machine repair",
    "beko washing machine repair near me", "beko washing machine service", "best bosch dishwasher repair near me", "best dishwasher repair services near me",
    "best refrigerator repair service near me", "best washing machine repair", "book appliance repair online", "book dishwasher repair online dubai",
    "book dryer repair online dubai", "book fridge repair online dubai", "book washing machine repair online dubai", "bosch dishwasher appliance repair near me",
    "bosch dishwasher repair", "bosch dishwasher repair near me", "bosch dishwasher repair service", "bosch dishwasher service and repair",
    "bosch dishwasher servicing", "bosch dishwasher spare parts dubai", "bosch dryer repair", "bosch dryer repair near me",
    "bosch fridge repair", "bosch fridge repair near me", "bosch fridge service center dubai", "bosch refrigerator repair near me",
    "bosch refrigerators repair service", "bosch service washing machine", "bosch tumble dryer repair", "bosch washer dryer repair",
    "bosch washer engineer dubai", "bosch washer repair", "bosch washer repair near me", "bosch washer repair quote dubai",
    "bosch washing machine repair", "bosch washing machine repairs near me", "bosch washing machines repair", "broken freezer door",
    "broken refrigerator", "broken washing machine", "cheap refrigerator repair dubai", "cheap washing machine repair dubai",
    "chest freezer repair dubai", "clothes dryer repair cost", "clothes washer repair", "clothes washer repair near me",
    "commercial dishwasher repair dubai", "commercial dishwasher repair near me", "commercial dishwasher service near me", "commercial dryer repair dubai",
    "commercial freezer repair cost dubai", "commercial refrigerator repair dubai", "cooler fix near me", "cost to fix dryer",
    "daewoo dishwasher repair", "deep freezer repair near me", "deep fridge repair near me", "dishwasher fixer near me",
    "dishwasher maintenance", "dishwasher mechanic", "dishwasher not draining repair dubai", "dishwasher repair",
    "dishwasher repair cost dubai", "dishwasher repair near me", "dishwasher repair service near me", "dishwasher service",
    "dishwasher service repair near me", "dishwasher specialist near me", "dishwasher tech", "dishwasher technician",
    "display fridge repair near me", "dryer belt replacement dubai", "dryer fix cost", "dryer machine repair",
    "dryer making noise repair dubai", "dryer repair", "dryer repair cost", "dryer repair cost dubai",
    "dryer repair jvc dubai", "dryer repair prices", "dryer repair service cost", "dryer repair service near me",
    "dryer roller replacement", "dryer samsung repair", "dryer vent repair near me", "dyson dryer repair",
    "dyson hair dryer repair", "dyson repair hair dryer", "dyson supersonic repair", "electrolux dishwasher repair near me",
    "electrolux fridge repair near me", "emergency dishwasher repair near me", "emergency fridge repair", "emergency fridge repair near me",
    "emergency refrigerator repair near me", "emergency washing machine repair", "emergency washing machine repair dubai", "fix bosch washing machine",
    "fix dishwasher near me", "fix dryer machine", "fix freezer", "fix laundry machine",
    "fix mini fridge", "fix my washing machine", "fix my washing machine near me", "fix samsung washing machine",
    "fix washing machine", "fix washing machine error code dubai", "fix washing machine near me", "freezer door repair near me",
    "freezer not freezing repair dubai", "freezer repair", "freezer repair service near me", "freezer repair shop near me",
    "freezer repairs near me", "fridge and freezer repair", "fridge compressor repair cost dubai", "fridge door broken",
    "fridge handle broken", "fridge maintenance near me", "fridge not cooling repair dubai", "fridge refrigerator repair",
    "fridge repair", "fridge repair dubai marina", "fridge repair near me", "fridge repair service near me",
    "fridge repair shop near me", "fridge repair technician near me", "fridge seal repair", "fridge service near me",
    "fridge service repair near me", "fridge servicing near me", "fridge technician near me", "genuine lg washing machine spare parts dubai",
    "genuine samsung fridge spare parts dubai", "hisense refrigerator repair near me", "hitachi fridge repair near me", "hitachi washing machine repair near me",
    "home appliance repair service", "home fridge repair near me", "home refrigerator repair near me", "in home washing machine repair",
    "indesit washer dryer repair", "indesit washing machine repair", "indesit washing machine repair near me", "industrial washing machine repair",
    "laundry machine maintenance", "laundry machine repair", "laundry machine repair near me", "laundry washer repair",
    "lg clothes dryer repair", "lg dishwasher repair", "lg dishwasher repair cost", "lg dishwasher repair near me",
    "lg dishwasher repair service near me", "lg dryer fix", "lg dryer repair", "lg dryer repair company",
    "lg dryer repair near me", "lg dryer repair service near me", "lg freeze repair near me", "lg freezer repair",
    "lg fridge authorized service dubai", "lg fridge repair", "lg fridge repair near me", "lg fridge service",
    "lg refrigerator repair", "lg refrigerator repair near me", "lg refrigerator service", "lg refrigerator service near me",
    "lg refrigerator technician dubai", "lg service washing machine", "lg washer dryer repair near me", "lg washer repair near me",
    "lg washer repair service near me", "lg washer repairs near me", "lg washing machine door latch broken", "lg washing machine dryer repair",
    "lg washing machine gearbox repair", "lg washing machine repair", "lg washing machine repair cost dubai", "lg washing machine repair near me",
    "lg washing machine repair service", "lg washing machine repair service near me", "lg washing machine service near me", "local dishwasher repair",
    "local washer repair", "midea washer repair", "midea washing machine repair", "miele dryer repair",
    "miele fridge repair", "mini fridge repair", "mini refrigerator repair", "motor in washing machine",
    "near by refrigerator repair shop", "near by washing machine repair", "near me freezer repair", "near me fridge repair",
    "near me fridge repair shop", "near me refrigerator repair", "near me refrigerator repair service", "near me washing machine repair",
    "near washing machine repair", "nearby washing machine repair", "nearest fridge repair shop", "panasonic fridge repair near me",
    "quick appliance repair dubai", "ref repair near me", "refrig repair", "refrigerant leak fix",
    "refrigerator and freezer repair", "refrigerator freezer repair", "refrigerator fridge repair", "refrigerator maintenance near me",
    "refrigerator repair", "refrigerator repair close to me", "refrigerator repair cost dubai", "refrigerator repair near me",
    "refrigerator repair places near me", "refrigerator repair service near me", "refrigerator repair shop near me", "refrigerator seal repair",
    "refrigerator service near me", "refrigerator technician", "refrigerator technician near me", "repair dishwasher near me",
    "repair dyson hair dryer", "repair for washing machine near me", "repair freezer near me", "repair fridge near me",
    "repair lg washing machine near me", "repair my dishwasher", "repair my dryer", "repair my fridge",
    "repair my washing machine", "repair of washing machine near me", "repair shop for refrigerator near me", "repair wash machine near me",
    "repair washer near me", "repair washing machine service", "repair wine cooler near me", "replace washer bearing",
    "replace washing machine bearings", "same day appliance repair dubai", "same day appliance technician dubai", "same day dishwasher fix",
    "same day dishwasher repair dubai", "same day dryer repair dubai", "same day dryer repair near me", "same day fridge repair dubai",
    "same day washing machine repair dubai", "samsung clothes dryer repair", "samsung dishwasher repair", "samsung dishwasher repairs near me",
    "samsung dryer drum felt seal replacement", "samsung dryer fix", "samsung dryer repair", "samsung dryer repair near me",
    "samsung dryer roller replacement", "samsung freezer repair", "samsung fridge fix", "samsung fridge maintenance",
    "samsung fridge mechanic near me", "samsung fridge repair", "samsung fridge repair cost dubai", "samsung fridge repair service",
    "samsung fridge repair service near me", "samsung fridge service", "samsung fridge service near me", "samsung fridge service repair",
    "samsung fridge servicing", "samsung refrig repair", "samsung refrig repair near me", "samsung refrigerator fix",
    "samsung refrigerator maintenance", "samsung refrigerator repair", "samsung refrigerator repair service", "samsung refrigerator service",
    "samsung refrigerator servicing", "samsung washer and dryer service", "samsung washer dryer service", "samsung washer fix",
    "samsung washer repair", "samsung washer repair service", "samsung washing machine authorized repair dubai", "samsung washing machine pcb repair",
    "samsung washing machine repair", "samsung washing machine repair service", "samsung washing machine technician dubai", "seal fridge repair",
    "sharp fridge repair", "sharp refrigerator repair", "shop fridge repair near me", "siemens dishwasher repair",
    "siemens dryer repair", "siemens fridge repair", "siemens refrigerator repair", "siemens refrigerator repair quote dubai",
    "siemens washing machine repair", "siemens washing machine repair near me", "siemens washing machine service center dubai", "smeg washing machine repair",
    "stackable washer and dryer repair", "technician for washing machine near me", "teka washing machine repair", "tumble dryer not heating repair dubai",
    "tumble dryer repairs", "urgent dishwasher repair", "urgent washer repair dubai today", "vent repair near me",
    "washer & dryer repair service", "washer and dryer repair service", "washer appliance repair", "washer broken",
    "washer door seal repair", "washer dryer repair cost", "washer dryer repair service", "washer fixer",
    "washer fixer near me", "washer repair", "washer repair near me", "washer repair service near me",
    "washer repair shops near me", "washer technician near me", "washing machine appliance repair", "washing machine body repair",
    "washing machine door broken", "washing machine door not locking", "washing machine door seal repair", "washing machine drum repair",
    "washing machine engineer dubai", "washing machine leaking from door repair dubai", "washing machine leaking water fix dubai", "washing machine lg repair near me",
    "washing machine machine repair", "washing machine machine repair near me", "washing machine maintenance", "washing machine maintenance wash",
    "washing machine motor replacement cost dubai", "washing machine not draining fix dubai", "washing machine not spinning repair dubai", "washing machine pcb repair cost",
    "washing machine repair", "washing machine repair at home", "washing machine repair cost near me", "washing machine repair dubai cost",
    "washing machine repair in", "washing machine repair in near me", "washing machine repair marina dubai", "washing machine repair near by",
    "washing machine repair near me", "washing machine repair near me lg", "washing machine repair near to me", "washing machine repair quote dubai",
    "washing machine repair service", "washing machine repair shops", "washing machine repair shops near me", "washing machine samsung repair near me",
    "washing machine seal repair", "washing machine service", "washing machine service dubai", "washing machine shock absorber repair",
    "washing machine technician near me", "washing machine technicians near me", "washing machine vibrating repair dubai", "washing washing machine repair",
    "weekend washing machine repair dubai", "wine chiller repair near me", "wine cooler repair near me", "wine cooler repair service",
    "wine cooler repair service near me", "wine cooler technician dubai", "wine fridge repair quote dubai", "zanussi dishwasher repair near me",
    "zanussi tumble dryer repair", "zanussi washer dryer repair"
  ];

  var PRODUCTS = [
    "appliance", "ariston", "beko", "bosch", "broken", "clothes",
    "commercial", "cooler", "cost", "daewoo", "dishwasher", "door",
    "dryer", "dyson", "fixer", "freezer", "fridge", "general electric",
    "haier", "hair", "hitachi", "home", "indesit", "laundry",
    "lg", "machine", "midea", "mini", "online", "parts",
    "refrig", "refrigerator", "samsung", "seal", "shop", "shops",
    "siemens", "spare", "tumble", "washer", "whirlpool", "wine",
    "zanussi"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "bespoke", "book",
    "booking", "build", "builder", "builders", "call", "certified",
    "change", "changing", "check", "clean", "cleaner", "cleaning",
    "companies", "company", "contact", "contract", "contractor", "custom",
    "deep cleaning", "design", "designer", "diagnose", "emergency", "expert",
    "fast", "fix", "fixed", "fixes", "fixing", "help",
    "hire", "in my area", "inspect", "inspection", "install", "installation",
    "installing", "installs", "licensed", "local", "made to measure", "made to order",
    "maintain", "maintenance", "maker", "makers", "making", "near me",
    "nearby", "now", "number", "professional", "quick", "quotation",
    "quote", "quotes", "relocate", "relocation", "removal", "remove",
    "repair", "repairing", "repairs", "replace", "replacement", "replacing",
    "same day", "service", "services", "servicing", "solution", "specialist",
    "tailor made", "technician", "today", "troubleshoot", "trusted", "urgent",
    "wash", "washing", "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "book", "build", "builder", "clean",
    "cleaning", "custom", "design", "designer", "detect", "detection",
    "diagnose", "fabrication", "fitted", "fix", "fixed", "fixes",
    "fixing", "inspect", "inspection", "install", "installation", "installing",
    "installs", "made to measure", "made to order", "maintain", "maintenance", "maker",
    "making", "mount", "mounting", "refurbish", "remodel", "remodeling",
    "renovate", "renovation", "repair", "repairing", "repairs", "replace",
    "replacement", "replacing", "restoration", "restore", "service", "services",
    "servicing", "tailor made", "troubleshoot", "unblock", "unclog", "wash",
    "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "blockage", "blocked", "broke", "broken",
    "broken belt", "burning smell", "burst", "buttons not working",
    "clogged", "compressor not working", "corroded", "crack",
    "cracked", "damage", "damaged", "dishwasher not cleaning dishes",
    "door not closing", "door seal broken", "dripping", "drum not turning",
    "dryer overheating", "error code showing", "fault", "faulty",
    "foul smell from fridge", "ice buildup", "issue", "issues",
    "jammed", "kharab", "leakage", "leaking",
    "leaking from bottom", "leaking water", "leaky", "low pressure",
    "making noise", "no power", "noise", "noisy",
    "not cooling", "not defrosting", "not draining", "not draining water",
    "not drying clothes", "not heating", "not spinning", "not turning on",
    "not working", "overflow", "overflowing", "overheating",
    "problem", "problems", "rusted", "short circuit",
    "slow", "smell", "smells", "smells burning",
    "smelly", "stopped working", "stuck", "stuck door",
    "tripping", "tripping power", "vibrating", "vibrating loudly",
    "water coming out", "weak", "won't start", "won't work",
    "wont turn", "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "dishwasher", "fridge", "machine", "refrigerator", "samsung", "washer"
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
