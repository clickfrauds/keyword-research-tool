/**
 * 🛡️ NEGATIVE GUARD v2 — Best Appliance Repairs Abu Dhabi (Abu Dhabi)
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
    "core appliance repair", "specialty appliance repair"
  ];
  var DATE_RANGE = "TODAY";        // TODAY | YESTERDAY | LAST_7_DAYS
  var MIN_IMPRESSIONS = 0;
  var DRY_RUN = true;              // ⚠️ pehle 2-3 din TRUE rakhein — sirf log karega.
                                   // Log theek lagay to false kar dein.
  var PROTECT_CONVERTERS = true;   // conversion wali term kabhi ban nahi hogi
  var ALLOW_SHORT_PRODUCT = true;  // "kitchen cabinets" type <=3-word product query allow

  var FORBIDDEN_LOCATIONS = [
    "ajman", "al ain outskirts", "dubai", "fujairah", "ras al khaimah", "sharjah",
    "umm al quwain", "الشارقة", "دبي", "عجمان"
  ];

  var EDU_CAREER = [
    "academy", "appliance repair certification", "appliance repair course abu dhabi", "appliance repair diploma",
    "appliance repair tools list", "appliance technician salary abu dhabi", "apprenticeship", "business kaise",
    "career", "careers", "catalogue", "certificate",
    "certification", "compressor hp rating guide", "cooking range gas types", "course",
    "courses", "cv", "datasheet", "define",
    "definition", "diagram", "diploma", "dishwasher motor specs",
    "dryer belt sizes", "dukan kaise", "gas stove burner types", "hiring",
    "how do", "how does", "how to become", "how to become an appliance technician",
    "hvac technician training", "in hindi", "in urdu", "institute",
    "internship", "interview questions", "items list", "job",
    "jobs", "ka kaam", "ka kam", "kaise bane",
    "kaise khole", "kaise seekhe", "kaise sikhe", "kitne prakar",
    "kitne type", "kitni salary", "kya hai", "kya hota hai",
    "material list", "meaning in", "meaning of", "mechanism of",
    "multimeter for appliance repair", "name list", "recruitment", "refrigerant types chart",
    "refrigerator compressor types", "resume", "salaries", "salary",
    "schematic", "shop kaise", "size chart", "standard height",
    "technician course dubai", "tool name", "tools list", "tools name",
    "training", "translate", "types of", "types of washing machine bearings",
    "vacancies", "vacancy", "wage", "wages",
    "washing machine motor specs", "washing machine repair training institute", "what happens", "what is",
    "دورة تصليح الأجهزة المنزلية"
  ];

  var INFO_DIY = [
    "cooking range knob settings", "difference between", "dishwasher error code", "dishwasher not draining diy",
    "diy", "do it yourself", "dryer not heating diy fix", "error code e1 washing machine",
    "fridge defrost manually", "fridge error code", "ghar par kaise", "hood filter cleaning guide",
    "how to", "how to clean dryer vent yourself", "how to fix fridge myself", "instructions",
    "khud banana", "khud lagana", "khud se", "ki setting",
    "manual", "refrigerator temperature settings", "reset dishwasher", "reset washing machine",
    "stove igniter troubleshooting", "tutorial", "washing machine drum reset", "washing machine self diagnostic",
    "washing machine settings guide", "what causes", "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "air conditioner repair", "amazon", "appliance distributor", "appliance rental", "appliance shop dubai", "appliance store",
    "buy dishwasher", "buy refrigerator", "car repair", "career", "carpenter", "cleaning company",
    "dubizzle", "electrician", "elevator repair", "furniture repair", "generator repair", "handyman",
    "hiring", "interior design", "internship", "job vacancy", "ka dam", "ka price",
    "khareedna", "kharidna", "ki qeemat", "kitchen design", "kitchen renovation", "kitna hai",
    "kitne ka", "laptop repair", "lg service center dubai", "manufacturer", "mobile repair", "noon",
    "painter", "pest control", "plumber", "recruitment", "rent appliance", "salary",
    "sasta", "second hand appliance", "solar panel", "spare parts", "tv repair", "used fridge",
    "used washing machine for sale", "whirlpool dubai", "wholesale appliance"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "bearing", "belt", "burner", "compressor", "door", "filter",
    "motor", "panel", "vent"
  ];

  var SAFE_ROOTS = [
    "24 7 fridge repair", "24 7 fridge repair near me", "24 7 refrigerator repair near me", "24 hour appliance repair abu dhabi",
    "24 hour fridge repair", "24 hour refrigerator repair", "24 hour washer and dryer repair", "24 hour washing machine repair",
    "24 hr washing machine repair", "ac and fridge repair", "ac and fridge repair near me", "ac fridge repair",
    "ac fridge repair near me", "ac fridge washing machine repair", "ac fridge washing machine repair near me", "ac refrigerator repair",
    "ac refrigerator repair near me", "appliance maintenance contract abu dhabi", "appliance repair al reem island", "appliance repair bosch dishwasher",
    "appliance repair khalifa city", "appliance repair mussafah", "appliance repair samsung dryer", "automatic gas stove repair near me",
    "automatic washing machine service", "beko washing machine repair", "beko washing machine repair near me", "best dishwasher repair company abu dhabi",
    "best dryer repair company abu dhabi", "best fridge repair company abu dhabi", "best refrigerator repair service near me", "best refrigerator service near me",
    "best stove repair company abu dhabi", "best washer dryer repair near me", "best washing machine repair company abu dhabi", "best washing machine repair service near me",
    "book dishwasher repair abu dhabi", "book dryer repair abu dhabi", "book fridge repair abu dhabi", "book gas stove repair abu dhabi",
    "book washing machine repair abu dhabi", "bosch dishwasher repair", "bosch dishwasher repair near me", "bosch dishwasher repair service",
    "bosch dishwasher service and repair", "bosch dryer repair", "bosch dryer repair near me", "bosch dryer service",
    "bosch fridge repair", "bosch fridge repair near me", "bosch fridge service", "bosch refrigerator repair",
    "bosch refrigerator repair near me", "bosch refrigerator service", "bosch refrigerator service centre", "bosch refrigerator service centre near me",
    "bosch tumble dryer repair", "bosch washer dryer repair", "bosch washer dryer service", "bosch washer repair",
    "bosch washer repair near me", "bosch washing machine repair", "bosch washing machine repair service", "broken freezer door",
    "burner stove repair", "candy refrigerator service centre near me", "cheap refrigerator repair abu dhabi", "cheap washing machine repair abu dhabi",
    "cloth dryer repair near me", "clothes dryer repair service", "clothes dryer service near me", "clothes dryer vent repair",
    "clothes washer repair", "clothes washer repair near me", "commercial dishwasher repair near me", "commercial washer repair near me",
    "cooker hood repair near me", "cooking gas stove repair near me", "cooking range maintenance", "cooking range not heating fix",
    "cooking range repair", "cooking range repair near me", "cooking range repair quote abu dhabi", "cooler repairs",
    "cost to repair fridge compressor", "cost to replace bearing in washing machine", "deep freezer repair near me", "deep freezer repair services near me",
    "dishwasher fixer near me", "dishwasher leaking repair", "dishwasher machine repair", "dishwasher machine repair near me",
    "dishwasher maintenance", "dishwasher maintenance service", "dishwasher not cleaning dishes fix", "dishwasher not draining repair",
    "dishwasher repair", "dishwasher repair and service", "dishwasher repair cost abu dhabi", "dishwasher repair near me",
    "dishwasher repair quote abu dhabi", "dishwasher repair service near me", "dishwasher repair services", "dishwasher repair shop near me",
    "dishwasher service and repair", "dishwasher specialist near me", "dishwashing machine repair near me", "dryer and washing machine repair",
    "dryer and washing machine repair near me", "dryer duct repair", "dryer duct repair near me", "dryer exhaust repair",
    "dryer fix service", "dryer maintenance near me", "dryer making noise repair", "dryer not heating repair",
    "dryer repair close to me", "dryer repair company near me", "dryer repair cost abu dhabi", "dryer repair quote abu dhabi",
    "dryer repair service", "dryer repair service near me", "dryer repair shops near me", "dryer samsung repair",
    "dryer service and repair", "dryer service near me", "dryer vent repair", "dryer vent repair near me",
    "dryer washer repair", "dryer washing machine repair", "electric range stove repair", "electric stove repairs",
    "electrolux dryer repair", "electrolux refrigerator service centre near me", "electrolux washer repair", "electrolux washing machine repair",
    "electrolux washing machine repair near me", "emergency fridge repair", "emergency fridge repair abu dhabi", "emergency refrigerator",
    "emergency refrigerator repair", "emergency washing machine repair near me", "fast appliance repair service", "fix bosch washing machine",
    "fix fridge", "fix fridge seal", "fix gas stove", "fix laundry machine",
    "fix laundry machine near me", "fix my fridge", "fix my refrigerator", "fix my washing machine",
    "fix refrigerator", "fix refrigerator seal", "fix samsung washing machine", "fix stove",
    "fix washer and dryer near me", "fix washing machine", "fix washing machine near me", "freeze repair service near me",
    "freezer and refrigerator repair", "freezer fix near me", "freezer maintenance near me", "freezer repair",
    "freezer repair service", "freezer repair service near me", "freezer technician", "freezer technician near me",
    "fridge ac repair", "fridge ac repair near me", "fridge and ac repair near me", "fridge and freezer repair",
    "fridge and washing machine repair near me", "fridge appliance repair near me", "fridge compressor repair", "fridge compressor repair cost",
    "fridge door broken", "fridge door repair near me", "fridge freezer compressor repair", "fridge freezer not cooling fix",
    "fridge freezer repairs", "fridge gasket repair", "fridge handle broken", "fridge maintenance",
    "fridge maintenance near me", "fridge maintenance service", "fridge mechanic near me", "fridge not cooling repair abu dhabi",
    "fridge pcb repair near me", "fridge refrigerator repair", "fridge repair", "fridge repair 24 7",
    "fridge repair and service", "fridge repair emergency", "fridge repair home service near me", "fridge repair man near me",
    "fridge repair mechanic near me", "fridge repair near me", "fridge repair quote abu dhabi", "fridge repair service",
    "fridge repair service near me", "fridge repair shop near me", "fridge repair technician", "fridge repair technician near me",
    "fridge service and repair", "fridge service near me", "fridge service repair", "fridge service repair near me",
    "fridge technician near me", "fridge washing machine repair near me", "fully automatic washing machine repair near me", "gas cook stove repair",
    "gas cooker repair near me", "gas cooker repair service near me", "gas cooking range repair", "gas range stove repair",
    "gas stove fix near me", "gas stove igniter repair", "gas stove leak repair near me", "gas stove maintenance near me",
    "gas stove repair", "gas stove repair at home near me", "gas stove repair centre near me", "gas stove repair cost abu dhabi",
    "gas stove repair near me", "gas stove repair nearby", "gas stove repair service near me", "ge authorized refrigerator repair near me",
    "hire dishwasher technician abu dhabi", "hire dryer technician abu dhabi", "hire refrigerator technician abu dhabi", "hire stove repair technician abu dhabi",
    "hire washing machine repair technician abu dhabi", "hisense dishwasher repair", "hisense fridge service", "hisense refrigerator repair near me",
    "hisense refrigerator service", "hisense washing machine repairs", "hitachi fridge repair near me", "hitachi washing machine repair",
    "home appliance technician abu dhabi", "home fridge repair near me", "home refrigerator repair near me", "hoover dryer repair",
    "hoover fridge repair", "in home washing machine repair", "indesit washing machine repair near me", "induction stove repairing",
    "kitchen gas stove repair near me", "kitchen hood cleaning and repair", "kitchen hood repair abu dhabi", "laundry machine repair",
    "laundry machine service near me", "laundry washer repair", "lg clothes dryer repair", "lg dishwasher repair",
    "lg dishwasher repair near me", "lg dishwasher repair service near me", "lg dryer maintenance", "lg dryer repair",
    "lg dryer repair company", "lg dryer repair near me", "lg dryer repair service", "lg dryer repair service near me",
    "lg dryer service", "lg dryer service near me", "lg freezer repair", "lg freezer repair near me",
    "lg fridge repair", "lg fridge repair near me", "lg fridge repair service", "lg fridge repair service centre",
    "lg fridge repairman", "lg fridge service", "lg fridge service repair", "lg refrigerator mechanic",
    "lg refrigerator repair", "lg refrigerator repair near me", "lg refrigerator repair service", "lg refrigerator repair service centre",
    "lg refrigerator repair service near me", "lg refrigerator service", "lg refrigerator service centre", "lg refrigerator service centre near me",
    "lg refrigerator service near me", "lg service washing machine", "lg washer and dryer repair near me", "lg washer dryer repair near me",
    "lg washer dryer service", "lg washer dryer service near me", "lg washer repair near me", "lg washer repair service near me",
    "lg washing machine & dryer repair service near me", "lg washing machine door latch broken", "lg washing machine dryer repair", "lg washing machine repair",
    "lg washing machine repair near me", "lg washing machine repair service", "lg washing machine repair service near me", "lg washing machine service near me",
    "local washer repair", "lpg gas stove repair near me", "miele fridge repair", "mini fridge repair near me",
    "motor in washing machine", "near by freeze repair", "near by fridge repair", "near by refrigerator repair",
    "near by washing machine repair", "near me fridge repair", "near me fridge repair shop", "near me gas stove repair",
    "near me refrigerator repair", "near me refrigerator repair service", "near me washing machine repair", "near washing machine repair",
    "nearby gas stove repair", "nearby washing machine repair", "nearby washing machine service", "nearest refrigerator repair",
    "on site appliance repair", "oven stove repair near me", "panasonic fridge repair near me", "panasonic refrigerator repair near me",
    "panasonic washing machine repair", "panasonic washing machine repair near me", "panasonic washing machine service near me", "range cooker repair",
    "ref repair near me", "refrig repair", "refrige repair", "refrigeration maintenance near me",
    "refrigerator and freezer repair", "refrigerator appliance repair near me", "refrigerator compressor repair cost", "refrigerator compressor repair near me",
    "refrigerator freezer repair", "refrigerator fridge repair", "refrigerator gasket repair", "refrigerator home service repair near me",
    "refrigerator ice machine repair", "refrigerator maintenance", "refrigerator maintenance near me", "refrigerator maintenance service",
    "refrigerator maintenance service near me", "refrigerator mechanic near me", "refrigerator mechanics", "refrigerator pcb repair near me",
    "refrigerator repair", "refrigerator repair 24 7", "refrigerator repair centre near me", "refrigerator repair close to me",
    "refrigerator repair cost abu dhabi", "refrigerator repair home service near me", "refrigerator repair near me", "refrigerator repair nearby",
    "refrigerator repair price abu dhabi", "refrigerator repair same day", "refrigerator repair service", "refrigerator repair service near me",
    "refrigerator repair shop near me", "refrigerator repair technician", "refrigerator service near me", "refrigerator servicing",
    "refrigerator technician near me", "repair dishwasher near me", "repair dishwasher rack", "repair for gas stove",
    "repair fridge near me", "repair gas stove near me", "repair lg washing machine near me", "repair my dishwasher",
    "repair my fridge", "repair my washing machine", "repair of refrigerator near me", "repair of washing machine near me",
    "repair refrigerator service", "repair service for dishwasher", "repair service for washer", "repair stove near me",
    "repair washer near me", "repair washing machine service", "replace washer bearing", "replace washing machine bearings",
    "same day appliance repair abu dhabi", "same day dishwasher repair", "same day fridge repair", "same day refrigerator repair",
    "same day washer repair", "same day washing machine repair", "same day washing machine repair service", "samsung automatic washing machine repair",
    "samsung clothes dryer repair", "samsung dishwasher maintenance", "samsung dishwasher repair", "samsung dryer maintenance",
    "samsung dryer repair", "samsung freezer repair", "samsung fridge fix", "samsung fridge maintenance",
    "samsung fridge repair", "samsung fridge repair near me", "samsung fridge repair service near me", "samsung fridge service",
    "samsung fridge service near me", "samsung refrig repair", "samsung refrig repair near me", "samsung refrigerator fix",
    "samsung refrigerator maintenance", "samsung refrigerator repair", "samsung refrigerator service", "samsung refrigerator service centre",
    "samsung washer fix", "samsung washer repair", "samsung washer repair service", "samsung washing machine repair",
    "samsung washing machine repair service", "samsung washing machine repairs near me", "semi automatic washing machine repair near me", "service dryer near me",
    "service repair for refrigerator", "service washing machine near me", "siemens dishwasher maintenance", "siemens dishwasher repair",
    "siemens dishwasher repair near me", "siemens fridge repair", "siemens refrigerator repair", "siemens washing machine repair",
    "siemens washing machine repair near me", "single door fridge repair", "small fridge repair near me", "stove burner repair",
    "stove burner repair near me", "stove fixer near me", "stove gas repair near me", "stove maintenance near me",
    "stove oven repair near me", "stove repair", "stove repair near me", "stove repair service near me",
    "stove repair shops near me", "stove servicing near me", "super general washing machine repair", "technician for refrigerator near me",
    "technician refrigerator repair", "teka washing machine repair", "toshiba refrigerator service centre", "toshiba washing machine repair",
    "tumble dryer not spinning fix", "urgent fridge repair", "urgent washing machine repair", "vent repair near me",
    "washer & dryer repair service", "washer & dryer repair service near me", "washer and dryer machine repair", "washer and dryer maintenance near me",
    "washer and dryer repair", "washer and dryer repair service", "washer and dryer repair service near me", "washer and dryer service near me",
    "washer dryer maintenance near me", "washer dryer repair", "washer dryer repair service", "washer dryer repair service near me",
    "washer dryer service near me", "washer fixer", "washer maintenance near me", "washer repair company",
    "washer repair near me", "washer repair near me same day", "washer repair service", "washer repair service near me",
    "washer repair shops near me", "washing machine and dryer repair", "washing machine and fridge repair near me", "washing machine bearing cost",
    "washing machine board repair", "washing machine body repair", "washing machine drum broken", "washing machine dryer repair",
    "washing machine dryer repair near me", "washing machine engineers", "washing machine leaking water repair", "washing machine lg repair near me",
    "washing machine machine repair", "washing machine machine repair near me", "washing machine maintenance near me", "washing machine maintenance service",
    "washing machine maintenance service near me", "washing machine motor repair", "washing machine motor repair cost", "washing machine not spinning repair",
    "washing machine pcb repair cost", "washing machine pcb repair near me", "washing machine repair", "washing machine repair & services",
    "washing machine repair at home", "washing machine repair company", "washing machine repair cost abu dhabi", "washing machine repair cost near me",
    "washing machine repair dryer", "washing machine repair home service", "washing machine repair home service near me", "washing machine repair near by",
    "washing machine repair near by me", "washing machine repair near me", "washing machine repair near to me", "washing machine repair price list abu dhabi",
    "washing machine repair quote abu dhabi", "washing machine repair same day", "washing machine repair service", "washing machine repair service near me",
    "washing machine repair shops", "washing machine repair shops near me", "washing machine repair technician", "washing machine repair technician near me",
    "washing machine service", "washing machine service at home", "washing machine service near", "washing machine service near me",
    "washing machine shock absorber repair", "washing machine technician abu dhabi", "washing washing machine repair", "wine cooler repair near me",
    "wine fridge repair", "wine fridge repair near me", "wine refrigerator repair", "wine refrigerator repair near me",
    "تصليح ثلاجات ابوظبي", "تصليح غسالات ابوظبي", "صيانة أجهزة منزلية ابوظبي"
  ];

  var PRODUCTS = [
    "appliance", "ariston", "automatic", "bearing", "beko", "bosch",
    "broken", "burner", "candy", "centre", "clothes", "compressor",
    "cooker", "cooking", "cost", "daewoo", "dishwasher", "door",
    "dryer", "electrolux", "fixer", "freezer", "fridge", "general electric",
    "gorenje", "haier", "hisense", "home", "laundry", "lg",
    "machine", "mechanic", "midea", "motor", "panasonic", "range",
    "refrig", "refrigerator", "samsung", "shop", "shops", "siemens",
    "smeg", "stove", "toshiba", "vent", "washer", "whirlpool",
    "wine"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "bespoke", "book",
    "book a technician", "booking", "build", "builder", "builders", "call",
    "call technician", "certified", "change", "changing", "check", "clean",
    "cleaner", "cleaning", "companies", "company", "contact", "contract",
    "contractor", "custom", "deep cleaning", "design", "designer", "diagnose",
    "emergency", "expert", "fast", "fix", "fixed", "fixes",
    "fixing", "help", "hire", "in my area", "inspect", "inspection",
    "install", "installation", "installing", "installs", "licensed", "local",
    "made to measure", "made to order", "maintain", "maintenance", "maker", "makers",
    "making", "near me", "nearby", "now", "number", "professional",
    "quick", "quotation", "quote", "quotes", "relocate", "relocation",
    "removal", "remove", "repair", "repairing", "repairs", "replace",
    "replacement", "replacing", "restore", "same day", "schedule repair", "service",
    "services", "servicing", "solution", "specialist", "tailor made", "technician",
    "today", "troubleshoot", "trusted", "urgent", "wash", "washing",
    "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "book a technician", "build", "builder", "call technician",
    "clean", "cleaning", "custom", "design", "designer", "detect",
    "detection", "diagnose", "fabrication", "fitted", "fix", "fixed",
    "fixes", "fixing", "inspect", "inspection", "install", "installation",
    "installing", "installs", "made to measure", "made to order", "maintain", "maintenance",
    "maker", "making", "mount", "mounting", "refurbish", "remodel",
    "remodeling", "renovate", "renovation", "repair", "repairing", "repairs",
    "replace", "replacement", "replacing", "restoration", "restore", "schedule repair",
    "service", "services", "servicing", "tailor made", "troubleshoot", "unblock",
    "unclog", "wash", "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "blockage", "blocked", "broke", "broken",
    "burner not lighting", "burst", "buttons not responding", "clogged",
    "compressor not running", "corroded", "crack", "cracked",
    "damage", "damaged", "door not closing", "dripping",
    "drum not turning", "error code", "fault", "faulty",
    "foul smell from fridge", "gas smell", "ice maker not working", "issue",
    "issues", "jammed", "kharab", "leakage",
    "leaking", "leaking from bottom", "leaking water", "leaky",
    "low pressure", "making noise", "noise", "noisy",
    "not cooling", "not defrosting", "not draining", "not draining water",
    "not drying clothes", "not heating", "not igniting", "not spinning",
    "not spinning properly", "not starting", "not turning on", "not working",
    "overflow", "overflowing", "overheating", "power not turning on",
    "problem", "problems", "rusted", "short circuit",
    "slow", "smell", "smells", "smelly",
    "stopped working", "stuck", "stuck door", "tripping",
    "tripping breaker", "vibrating", "vibrating loudly", "water coming out",
    "weak", "won't turn on", "won't work", "wont turn",
    "wont work"
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
