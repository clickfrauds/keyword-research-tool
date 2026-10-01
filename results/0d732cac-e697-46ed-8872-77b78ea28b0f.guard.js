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
    "Washer Dryer Repair Dubai - Search"
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
  var ALLOW_SHORT_PRODUCT = false;  // <=3-word bare product query allowed?
                                   // true for makers/installers ("kitchen cabinets"),
                                   // false for repair/maintenance ("samsung fridge" is a shopper)

  var FORBIDDEN_LOCATIONS = [
    "abu dhabi", "ajman", "al ain", "australia", "bahrain", "canada",
    "doha", "emirate of umm al quwain", "fujairah", "india", "jeddah", "khor fakkan",
    "ksa", "kuwait", "london", "manama", "muscat", "oman",
    "pakistan", "qatar", "rak", "ras al khaimah", "riyadh", "saudi",
    "sharjah", "uaq", "umm al quwain", "أبوظبي", "ابوظبي", "الشارقة",
    "العين", "شارق", "عجمان"
  ];

  var EDU_CAREER = [
    "academy", "appliance repair apprenticeship dubai", "appliance repair course dubai", "appliance repair tools list",
    "appliance technician salary dubai", "apprenticeship", "business kaise", "career",
    "careers", "catalogue", "certificate", "certification",
    "compressor types explained", "course", "courses", "cv",
    "datasheet", "define", "definition", "diagram",
    "diploma", "dishwasher pump specifications", "dryer repair certification", "dukan kaise",
    "hiring", "how do", "how does", "how to become",
    "how to become appliance technician", "hvac technician course", "in hindi", "in urdu",
    "institute", "internship", "interview questions", "items list",
    "job", "jobs", "ka kaam", "ka kam",
    "kaise bane", "kaise khole", "kaise seekhe", "kaise sikhe",
    "kitne prakar", "kitne type", "kitni salary", "kya hai",
    "kya hota hai", "material list", "meaning in", "meaning of",
    "mechanism of", "multimeter for appliance repair", "name list", "recruitment",
    "refrigerant gas types", "resume", "salaries", "salary",
    "schematic", "shop kaise", "size chart", "standard height",
    "technician training institute uae", "tool name", "tools list", "tools name",
    "training", "translate", "types of", "types of washing machine motors",
    "vacancies", "vacancy", "wage", "wages",
    "washer dryer parts diagram", "washing machine belt size guide", "washing machine repair training", "what happens",
    "what is", "أنواع الغسالات", "دورة تصليح أجهزة كهربائية", "راتب فني صيانة",
    "كيف تصبح فني غسالات", "مواصفات الثلاجة"
  ];

  var INFO_DIY = [
    "difference between", "dishwasher symbols meaning", "diy", "do it yourself",
    "dryer not spinning diy", "e1 error code", "error code dishwasher", "error code washing machine",
    "f21 error samsung washer", "fridge settings guide", "fridge temperature settings", "ghar par kaise",
    "how to", "how to clean dryer filter", "how to descale dishwasher", "instructions",
    "khud banana", "khud lagana", "khud se", "ki setting",
    "manual", "reset fridge thermostat", "reset washing machine", "troubleshoot dryer no heat",
    "tutorial", "washing machine manual pdf", "washing machine settings explained", "what causes",
    "wikipedia", "youtube", "تصفير الثلاجة", "طريقة تنظيف الغسالة",
    "كود خطأ الغسالة"
  ];

  var FORBIDDEN_WORDS = [
    "a/c", "ac", "ac repair", "air conditioner", "air conditioner repair", "air conditioning",
    "aircon", "airtasker", "amazon", "angi", "angie s list", "angies list",
    "auto repair", "b2b", "best brand", "bulk order", "buy", "car fridge",
    "car refrigerator", "car repair", "car service", "career", "careers", "carpenter",
    "carpenters", "carpentry", "checkatrade", "compare brands", "coupon", "discount code",
    "distributor", "dryer vent", "dryer vents", "dubizzle", "duct cleaning", "ebay",
    "electrician", "electricians", "exterminator", "for sale", "franchise", "ge appliances",
    "general electric", "general maintenance", "haier", "hair dryer", "hair dryers", "hair straightener",
    "hairdryer", "handyman", "hipages", "hiring", "home advisor", "homeadvisor",
    "hoover", "housejoy", "hvac", "insurance claim", "job", "jobs",
    "justdial", "justlife", "ka dam", "ka price", "khareedna", "kharidna",
    "ki qeemat", "kitna hai", "kitne ka", "lg service center", "locksmith", "locksmiths",
    "manufacturer", "matic", "mechanic shop", "midea", "mr right", "mybuilder",
    "nextdoor", "noon", "oneflare", "painter", "painters", "parts dealer",
    "parts shop", "pest control", "plumber", "plumbers", "plumbing", "price list",
    "rated people", "recruitment", "rent", "rental", "retail store", "roofer",
    "roofers", "roofing", "salary", "sale", "sasta", "second hand",
    "service market", "servicemarket", "siemens", "spare part", "spare parts", "sulekha",
    "supplier", "taskrabbit", "thumbtack", "urban company", "urbanclap", "used",
    "vacancies", "vacancy", "vent cleaning", "warranty claim", "whirlpool", "wholesale",
    "yelp", "zimmber", "تكييف", "ثلاج سيار", "ثلاجات السيارات", "ثلاجة سيارة",
    "دهان", "سباك", "سباكة", "كهربائي", "مكافح حشر", "مكافحة حشرات",
    "مكيف", "مكيفات", "نجار"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "cooler", "door", "dryer", "freezer", "fridge", "machine",
    "screen", "seal", "washer", "wine"
  ];

  var SAFE_ROOTS = [
    "24 hour appliance repair", "24 hour led tv repair", "24 hour tv repair", "appliance repair bosch dishwasher",
    "appliance repair home visit", "appliance repair samsung dryer", "appliance repair service dubai", "bosch dishwasher fix",
    "bosch service washing machine", "bosch washer dryer repair", "broken dishwasher", "broken dryer",
    "broken refrigerator", "broken washing machine", "cof tv repair", "cracked led screen",
    "dishwasher fixer near me", "dishwasher machine repair near me", "dishwasher maintenance", "dishwasher mechanic",
    "dishwasher repair", "dishwasher service", "dishwasher specialist", "dishwasher tech",
    "dishwasher technician", "doorstep appliance repair dubai", "dryer and washer repair near me", "dryer appliance repair near me",
    "dryer fixer", "dryer machine service", "dryer maintenance", "dryer mechanic",
    "dryer repair", "dryer service", "dryer service near me", "dryer technician near me",
    "dryer washer repair near me", "emergency appliance repair dubai", "emergency led tv repair", "emergency tv repair",
    "fast appliance repair dubai", "fix bosch washing machine", "fix dishwasher", "fix dishwasher near me",
    "fix dryer machine near me", "fix dryer near me", "fix freezer", "fix fridge door seal",
    "fix fridge near me", "fix laundry machine", "fix leaking dishwasher", "fix led tv",
    "fix led tv screen", "fix my dishwasher", "fix my dryer", "fix my dryer near me",
    "fix my fridge", "fix my fridge freezer", "fix my fridge near me", "fix my led tv",
    "fix my refrigerator", "fix my washer", "fix my washing machine", "fix my wine cooler",
    "fix refrigerator", "fix samsung washing machine", "fix tumble dryer near me", "fix washing machine",
    "fix wine cooler", "fix wine fridge", "fixing dishwasher near me", "fixing dryers near me",
    "fixing led tv screen", "freezer door repair", "freezer repair", "fridge door repair",
    "fridge fixer near me", "fridge maintenance", "fridge mechanic near me", "fridge repair",
    "fridge repair and service", "fridge seal repair", "fridge service and repair", "fridge service near me",
    "fridge service repair", "fridge servicing near me", "fridge technician", "home appliance technician dubai",
    "laundry machine maintenance", "laundry machine repair", "laundry machine service near me", "laundry machine technician",
    "led for tv repair", "led repair tv", "led screen repair", "led tv broken",
    "led tv display repair", "led tv fix screen", "led tv repair", "led tv repair near me",
    "led tv repair open now", "led tv repair shop near me", "led tv screen damage repair", "led tv screen repair",
    "lg dryer fix", "lg led tv repair dubai", "lg tv repair dubai", "lg washing machine dryer repair",
    "local dishwasher repairman", "near me freezer repair", "refrig repair", "refrigerator maintenance",
    "refrigerator mechanic near me", "refrigerator repair", "refrigerator service near me", "refrigerator technician",
    "repair dishwasher dubai", "repair dryer dubai", "repair freezer near me", "repair fridge dubai",
    "repair led tv dubai", "repair led tv near me", "repair my dishwasher", "repair my dryer",
    "repair my fridge", "repair my led tv", "repair my refrigerator", "repair my tumble dryer",
    "repair my tv", "repair my washer", "repair my washing machine", "repair refrigerator dubai",
    "repair tumble dryer dubai", "repair tv dubai", "repair tv led", "repair tv led screen",
    "repair wash machine near me", "repair washer and dryer near me", "repair washer dubai", "repair washing machine dubai",
    "same day appliance repair", "same day led tv repair", "same day tv repair", "samsung dryer fix",
    "samsung led tv repair dubai", "samsung tv repair dubai", "samsung washer fix", "seal fridge repair",
    "service dryer near me", "sony led tv repair dubai", "tumble dryer technician near me", "tv led display repair",
    "tv led repair", "tv led repair near me", "tv led screen repair", "tv repair at home",
    "tv repair led screen", "tv repair near me", "tv repair near me open now", "tv repair open now",
    "tv screen led repair", "tv screen repair near me", "tv technician near me", "urgent fridge repair",
    "washer and dryer repair near me", "washer broken", "washer dryer repair cost", "washer dryer repair dubai",
    "washer dryer repair near me", "washer fixer", "washer maintenance near me", "washer repair",
    "washer technician", "washing machine door broken", "washing machine door repair", "washing machine drum broken",
    "washing machine drum repair", "washing machine machine repair", "washing machine maintenance", "washing machine mechanic near me",
    "washing machine repair", "washing machine repair in", "washing machine repair near me", "washing machine service",
    "washing machine technician", "washing washing machine repair", "who can repair my dishwasher", "who can repair my dryer",
    "who can repair my fridge", "who can repair my led tv", "who can repair my refrigerator", "who can repair my tumble dryer",
    "who can repair my tv", "who can repair my washer", "who can repair my washing machine", "who can repair my wine cooler",
    "wine chiller repair", "wine cooler repair", "wine fridge broken", "wine fridge repair",
    "إصلاح تلفزيونات", "اصلاح الثلاجات", "اصلاح الثلاجة", "اصلاح الغسالات الاتوماتيك",
    "اصلاح الغسالة", "اصلاح تلفزيون سامسونج", "اصلاح ثلاجات", "اصلاح ثلاجة سامسونج",
    "اصلاح غسالات", "اصلاح غسالة lg", "اصلاح غسالة ال جي", "اصلاح غسالة الملابس",
    "اصلاح غسالة صحون", "اصلاح كروت الغسالات", "اقرب محل تصليح تلفزيونات", "اماكن تصليح تلفزيونات",
    "تصليح التلفزيون البلازما", "تصليح التلفزيون في البيت", "تصليح الثلاجات في المنزل", "تصليح الريموت التلفزيون",
    "تصليح الشاشات التلفزيون", "تصليح الغسالة", "تصليح باب غسالة اتوماتيك", "تصليح تلفزيون",
    "تصليح تلفزيونات سامسونج", "تصليح تلفزيونات في المنزل", "تصليح ثلاجات", "تصليح ثلاجات دبي",
    "تصليح ثلاجة lg", "تصليح ثلاجة ال جي", "تصليح ثلاجة سريع دبي", "تصليح ثلاجة في المنزل",
    "تصليح ثلاجه", "تصليح شاشات تلفزيون", "تصليح شاشة تلفزيون", "تصليح غسالات",
    "تصليح غسالات صحون", "تصليح غسالة سامسونج اتوماتيك", "تصليح غسالة سريع دبي", "تصليح غسالة صحون اريستون",
    "تصليح غسالة صحون سريع", "تصليح غسالة صحون في المنزل", "تصليح غسالة صحون قريب مني", "تصليح غسالة في المنزل",
    "تصليح غسالة ملابس", "تصليح فريزر الثلاجة", "تصليح كمبروسر ثلاجة", "تصليح نشافات",
    "تصليح نشافة الغسالة", "تصليح نشافة دبي", "تصليح نشافة في المنزل", "تصليح نشافة ملابس",
    "تصليح نشافه غساله", "صيانة اجهزة كهربائية دبي", "صيانة الثلاجات المنزلية", "صيانة تلفزيون",
    "صيانة تلفزيونات بالمنزل", "صيانة تلفزيونات قريب مني", "صيانة ثلاجات", "صيانة غسالات",
    "صيانة غسالات دبي", "صيانة غسالات صحون", "صيانة غسالة صحون دبي", "صيانة نشافات",
    "فنى ثلاجات", "فني تبريد ثلاجات", "فني تصليح غسالة صحون", "فني تلفزيون",
    "فني تلفزيون قريب مني", "فني تلفزيونات دبي", "فني غسالات", "فني غسالات دبي",
    "فني غسالات صحون", "فني غسالات صحون قريب مني", "فني غسالة صحون دبي", "فني نشافات",
    "فني نشافات قريب مني", "محل تصليح التلفزيون", "محل صيانة تلفزيونات", "مصلح تلفزيونات",
    "مصلح ثلاجات", "مصلح غسالات"
  ];

  var PRODUCTS = [
    "appliance", "bosch", "broken", "cooler", "daewoo", "dishwasher",
    "door", "dryer", "electrolux", "fixer", "freezer", "fridge",
    "general electric", "haier", "hoover", "laundry", "lg", "machine",
    "mechanic", "midea", "open", "panasonic", "refrigerator", "samsung",
    "screen", "seal", "sharp", "siemens", "toshiba", "tumble",
    "washer", "whirlpool", "wine", "التلفزيون", "الثلاجات", "الغسالة",
    "المنزل", "تلفزيون", "تلفزيونات", "ثلاجات", "ثلاجة", "سامسونج",
    "سريع", "صحون", "غسالات", "غسالة", "مصلح", "نشافات",
    "نشافة"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "bespoke", "book",
    "booking", "build", "builder", "builders", "calibrate", "call",
    "certified", "change", "changing", "check", "clean", "cleaner",
    "cleaning", "companies", "company", "contact", "contract", "contractor",
    "custom", "deep cleaning", "descale", "design", "designer", "diagnose",
    "emergency", "expert", "fast", "fix", "fixed", "fixes",
    "fixing", "help", "hire", "in my area", "inspect", "inspection",
    "install", "installation", "installing", "installs", "licensed", "local",
    "made to measure", "made to order", "maintain", "maintenance", "maker", "makers",
    "making", "near me", "nearby", "now", "number", "professional",
    "quick", "quotation", "quote", "quotes", "relocate", "relocation",
    "removal", "remove", "repair", "repairing", "repairs", "replace",
    "replace seal", "replacement", "replacing", "same day", "service", "services",
    "servicing", "solution", "specialist", "tailor made", "technician", "today",
    "troubleshoot", "trusted", "unclog", "urgent", "wash", "washing",
    "whatsapp", "اصلاح", "تبديل", "تركيب", "تصليح", "تعبئة",
    "تنظيف", "خدمة", "شركة", "صيانة", "طوارئ", "فني",
    "فنيين", "قريب", "مركز"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "build", "builder", "calibrate", "clean",
    "cleaning", "custom", "descale", "design", "designer", "detect",
    "detection", "diagnose", "fabrication", "fitted", "fix", "fixed",
    "fixes", "fixing", "inspect", "inspection", "install", "installation",
    "installing", "installs", "made to measure", "made to order", "maintain", "maintenance",
    "maker", "making", "mount", "mounting", "refurbish", "remodel",
    "remodeling", "renovate", "renovation", "repair", "repairing", "repairs",
    "replace", "replace seal", "replacement", "replacing", "restoration", "restore",
    "service", "services", "servicing", "tailor made", "troubleshoot", "unblock",
    "unclog", "wash", "washing", "اصلاح", "تبديل", "تركيب",
    "تصليح", "تعبئة", "تنظيف", "صيانة"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "blockage", "blocked", "broke", "broken",
    "burning smell", "burst", "clogged", "corroded",
    "crack", "cracked", "damage", "damaged",
    "door not closing", "door seal broken", "dripping", "error code showing",
    "fault", "faulty", "ice buildup", "issue",
    "issues", "jammed", "kharab", "leakage",
    "leaking", "leaking water", "leaky", "low pressure",
    "making grinding noise", "making noise", "noise", "noisy",
    "not cooling", "not draining", "not draining water", "not drying clothes",
    "not heating", "not spinning", "not starting", "not turning on",
    "not working", "overflow", "overflowing", "overheating",
    "problem", "problems", "rusted", "short circuit",
    "slow", "smell", "smells", "smelly",
    "stopped working", "stuck", "stuck on cycle", "tripping",
    "tripping breaker", "vibrating", "vibrating loudly", "water coming out",
    "weak", "won't turn on", "won't work", "wont turn",
    "wont work", "الثلاجة لا تبرد", "النشافة لا تجفف", "تسريب مياه من الغسالة",
    "صوت غريب من الغسالة", "غسالة لا تعمل"
  ];
  // Symptom-only rule (Sep 2026): "fridge not cooling", "washing machine not
  // spinning" with NO hire word are people fixing it themselves. Blocked,
  // unless a hard fault says they need a technician ("drum broken").
  var HIRE_WORDS = [
    "at home", "book", "call", "center", "centre", "company",
    "emergency", "engineer", "expert", "hire", "mechanic", "near me",
    "nearby", "now", "open", "same day", "service", "services",
    "shop", "specialist", "technician", "today", "urgent", "اصلاح",
    "تصليح", "رقم", "شركة", "صيانة", "طوارئ", "عاجل",
    "فني", "فنيين", "في المنزل", "قريب", "مركز"
  ];
  var HARD_FAULTS = [
    "broke", "broken", "burned", "burnt", "burst", "cracked",
    "damaged", "dead", "failed", "flooding", "shock", "smoke",
    "sparking", "tripping", "خربان", "خربانة", "محروق", "محروقة",
    "معطل", "معطلة", "مكسور", "مكسورة"
  ];
  // People you hire, any trade: a bare (typo'd) search for one is a lead.
  var PROVIDERS = [
    "builder", "carpenter", "cleaner", "contractor", "electrician", "exterminator",
    "fitter", "gardener", "glazier", "handyman", "installer", "landscaper",
    "locksmith", "mason", "mechanic", "mover", "movers", "painter",
    "plumber", "roofer", "tailor", "technician", "tiler", "upholsterer",
    "welder", "حداد", "دهان", "سباك", "فني", "كهربائي",
    "مصلح", "نجار"
  ];
  var SYMPTOM_RE = /(^|\s)(not|wont|won't|doesnt|doesn't|stopped|error|code|[a-z]{1,2}\d{1,3}|لا|ما|عطل)(\s|$)/;
  var PRICE_RE = /(^|\s)(price|prices|cost|costs|rate|rates|cheap|cheapest|سعر|اسعار|أسعار|كم)(\s|$)/;
  function isHireOrFault(t) { return !!(matchFuzzy(t, HIRE_WORDS) || matchStrict(t, HARD_FAULTS)); }
  // "washingmachine repair" -> "washing machine repair": glued spellings of
  // our own multi-word products and bid keywords are leads, not junk.
  var GLUE = {};
  PRODUCTS.concat(SAFE_ROOTS).forEach(function (p) {
    p.split(/\s+/).forEach(function (w, i, a) {
      if (i < a.length - 1) GLUE[w + a[i + 1]] = w + " " + a[i + 1];
    });
  });
  // Arabic normaliser (same rules as the keyword tool): one form per word,
  // so "ثلاجة", "الثلاجة", "ثلاجات" all read as the same product.
  function arNorm(w) {
    w = w.replace(/[\u064B-\u0652\u0640]/g, "").replace(/[أإآ]/g, "ا").replace(/ى/g, "ي");
    if (w.length <= 3) return w;
    var pres = ["وال", "بال", "فال", "كال", "لل", "ال"];
    for (var i = 0; i < pres.length; i++) {
      if (w.indexOf(pres[i]) === 0 && w.length - pres[i].length >= 3) { w = w.slice(pres[i].length); break; }
    }
    var sufs = ["ات", "ة", "ه"];
    for (var j = 0; j < sufs.length; j++) {
      var s = sufs[j];
      if (w.slice(-s.length) === s && w.length - s.length >= 3) { w = w.slice(0, -s.length); break; }
    }
    return w;
  }
  function arText(t) {
    return String(t).split(/\s+/).map(function (w) {
      return /[\u0600-\u06FF]/.test(w) ? arNorm(w) : w;
    }).join(" ");
  }
  function arList(l) { return l.map(arText); }
  SAFE_ROOTS = arList(SAFE_ROOTS); PRODUCTS = arList(PRODUCTS); ACTIONS = arList(ACTIONS);
  STRONG_ACTIONS = arList(STRONG_ACTIONS); PROBLEMS = arList(PROBLEMS);
  HIRE_WORDS = arList(HIRE_WORDS); HARD_FAULTS = arList(HARD_FAULTS);
  FORBIDDEN_WORDS = arList(FORBIDDEN_WORDS); EDU_CAREER = arList(EDU_CAREER);
  INFO_DIY = arList(INFO_DIY); CONTEXT_WORDS = arList(CONTEXT_WORDS);
  FORBIDDEN_LOCATIONS = arList(FORBIDDEN_LOCATIONS);

  function stripPhrases(t, list) {
    var out = " " + t + " ";
    list.slice().sort(function (a, b) { return b.length - a.length; }).forEach(function (p) {
      if (p.indexOf(" ") !== -1 || p.length >= 4) out = out.split(" " + p + " ").join(" ");
    });
    return out.replace(/\s+/g, " ").trim();
  }
  function normalizeGlued(t) {
    return t.split(/\s+/).map(function (w) { return GLUE[w] || w; }).join(" ");
  }

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "dishwasher", "fridge", "machine", "refrigerator", "screen", "washer"
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
    var term = normalizeGlued(arText(rawTerm.toLowerCase().trim()));
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
    // Action words are read from the term WITHOUT our product names: in
    // "washing machine not spinning" the "washing" is the product, not a
    // wash service, and it was passing symptom queries as service intent.
    var termNoProd = stripPhrases(term, PRODUCTS);
    var actionHit = matchFuzzy(termNoProd, ACTIONS);
    var problemHit = matchFuzzy(term, PROBLEMS);
    var strongHit = matchFuzzy(termNoProd, STRONG_ACTIONS);
    // The PERSON you hire is a service signal of its own: "plumber ballard",
    // "plumber seattle cost" are buyers with no repair verb in them. Read on
    // the raw term — for a trade, "plumber" is also one of the PRODUCTS that
    // termNoProd strips out.
    var providerHit = matchFuzzy(term, PROVIDERS);
    var serviceSignal = !!(fuzzyRootHit || safeHit || problemHit || strongHit || providerHit);

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
            } else if (!actionHit && !strongHit && !providerHit && !isHireOrFault(term)
                       && PRICE_RE.test(term)) {
              // 4️⃣a product price, no service word ("fridge price")
              reason = "Product price, no service word";
            } else if ((problemHit || SYMPTOM_RE.test(term)) && !actionHit && !strongHit && !providerHit
                       && !matchFuzzy(term, HIRE_WORDS) && !matchStrict(term, HARD_FAULTS)
                       && !safeHit) {
              // 4️⃣b symptom only — research, not a hire
              reason = "Symptom only, no hire word (DIY/info): [" + problemHit + "]";
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
              // ... but only when the root is the PERSON you hire ("plumbr
              // dubai") or the business makes the product. For a repair
              // business a bare product root is a shopper: "samsung fridge".
              else if (fuzzyRootHit && !safeHit && splitTokens(term).length <= 2
                       && (ALLOW_SHORT_PRODUCT || matchFuzzy(fuzzyRootHit, PROVIDERS))) {
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
                if (prod && (actionHit || problemHit || providerHit)) {
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
