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
  var ALLOW_SHORT_PRODUCT = true;  // "kitchen cabinets" type <=3-word product query allow

  var FORBIDDEN_LOCATIONS = [
    "abu dhabi", "ajman", "al ain", "bahrain", "doha", "fujairah",
    "jeddah", "kuwait", "manama", "muscat", "oman", "qatar",
    "rak", "ras al khaimah", "riyadh", "saudi arabia", "sharjah", "umm al quwain"
  ];

  var EDU_CAREER = [
    "ac technician salary dubai", "academy", "appliance repair certification uae", "appliance repair training dubai",
    "apprenticeship", "business kaise", "career", "careers",
    "catalogue", "certificate", "certification", "compressor size chart",
    "compressor tonnage calculator", "course", "courses", "cv",
    "datasheet", "define", "definition", "diagram",
    "diploma", "dishwasher dimensions standard", "dryer belt size", "dukan kaise",
    "fridge compressor types", "hiring", "how do", "how does",
    "how to become", "how to become appliance technician", "hvac technician training dubai", "in hindi",
    "in urdu", "institute", "internship", "interview questions",
    "items list", "job", "jobs", "ka kaam",
    "ka kam", "kaise bane", "kaise khole", "kaise seekhe",
    "kaise sikhe", "kitne prakar", "kitne type", "kitni salary",
    "kya hai", "kya hota hai", "material list", "meaning in",
    "meaning of", "mechanism of", "name list", "recruitment",
    "refrigerant types explained", "refrigeration mechanic course", "refrigeration technician salary", "resume",
    "salaries", "salary", "schematic", "shop kaise",
    "size chart", "standard height", "tool name", "tools list",
    "tools name", "training", "translate", "tv panel size chart",
    "types of", "types of washing machine motors", "vacancies", "vacancy",
    "wage", "wages", "washing machine capacity guide", "washing machine drum sizes",
    "washing machine motor specs", "washing machine technician course dubai", "washing machine voltage specs", "what happens",
    "what is"
  ];

  var INFO_DIY = [
    "difference between", "dishwasher error code e1", "dishwasher not draining diy", "diy",
    "do it yourself", "fridge error code list", "fridge not cooling diy fix", "fridge thermostat setting guide",
    "ghar par kaise", "how to", "how to clean washing machine filter", "how to descale washing machine",
    "how to reset dryer", "instructions", "khud banana", "khud lagana",
    "khud se", "ki setting", "manual", "reset dishwasher settings",
    "reset lg washer error", "reset washing machine error code", "samsung fridge error code", "tutorial",
    "tv backlight test diy", "tv error code", "washing machine drain hose diy", "washing machine settings guide",
    "what causes", "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "ac duct cleaning", "ac installation", "amazon", "b2b", "bulk order", "buy",
    "career", "carpenter", "carrefour", "cleaning company", "distributor", "distributorship",
    "dubizzle", "ebay", "electrician service", "export", "for sale", "franchise",
    "furniture", "handyman dubai jobs", "hiring", "import", "internship", "job vacancy",
    "jobs", "ka dam", "ka price", "khareedna", "kharidna", "ki qeemat",
    "kitna hai", "kitne ka", "lulu", "maid service", "manufacturer", "movers and packers",
    "noon", "painter", "painting service", "parts online", "pest control", "plumber",
    "plumbing", "price list", "recruitment", "rent", "retail store", "salary",
    "sasta", "second hand", "sharaf dg", "showroom", "spare part", "spare parts",
    "supplier", "trade license", "used", "wholesale"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "board", "body", "chiller", "compressor", "cooler", "display",
    "door", "drawer", "drum", "duct"
  ];

  var SAFE_ROOTS = [
    "12v fridge repairs near me", "24 hour appliance repair dubai", "24 hour dishwasher repair", "24 hour dryer repair",
    "24 hour fridge repair", "24 hour fridge repair near me", "24 hour led tv repair", "24 hour refrigerator repair",
    "24 hour refrigerator repair near me", "24 hour tumble dryer repair", "24 hour tv repair", "24 hour washer repair",
    "24 hour washing machine repair", "24 hour wine cooler repair", "24 hr washing machine repair", "4k led tv repair",
    "55 led screen replacement", "a1 washing machine repairs", "ac and fridge repair", "ac and fridge repair near me",
    "ac and refrigeration repair near me", "ac fridge repair", "ac fridge repair near me", "ac fridge service",
    "ac fridge washing machine repair", "ac fridge washing machine repair dubai", "ac fridge washing machine repair near me", "ac refrigerator repair",
    "ac refrigerator repair near me", "ac washing machine repair", "ac washing machine repair near me", "admiral dryer repair",
    "aeg dishwasher repairs", "aeg dishwasher repairs near me", "aeg dryer repair", "aeg fridge repairs",
    "aeg tumble dryer repair", "aeg washer dryer repair", "affordable dishwasher repair near me", "affordable refrigerator repair",
    "affordable refrigerator repair near me", "affordable washing machine repair", "air conditioning and refrigeration services", "air dryer repair near me",
    "aircon and refrigeration services", "aircon and refrigeration services near me", "american fridge repairs", "appliance fridge repair",
    "appliance repair bosch dishwasher", "appliance repair center dubai", "appliance repair fridge", "appliance repair samsung dryer",
    "appliance technician dubai", "ariston dishwasher repairs", "ariston washing machine repair", "asko washer repair",
    "asko washing machine repairs", "asko washing machine repairs near me", "authorized bosch dishwasher repair", "authorized lg refrigerator repair",
    "automatic washing machine mechanic near me", "automatic washing machine repair", "automatic washing machine repair home service", "automatic washing machine repair near me",
    "automatic washing machine service", "automatic washing machine technician", "average cost of refrigerator repair", "average cost of washing machine repair",
    "average fridge repair cost", "average refrigerator repair cost", "average washer repair cost", "backlight for tv repair",
    "backlight led tv repair", "backlight repair cost tv", "backlight repair tv cost", "backlight tv repair cost",
    "backlight tv repair near me", "bar fridge repairs", "beko dishwasher repairs", "beko dishwasher repairs near me",
    "beko fridge freezer repair", "beko fridge freezer repairs", "beko fridge repairs", "beko washing machine maintenance",
    "beko washing machine repair", "beko washing machine repair cost", "beko washing machine repair near me", "beko washing machine service",
    "best bosch dishwasher repair near me", "best dishwasher repair", "best dishwasher repair near me", "best dishwasher repair services near me",
    "best fridge repair", "best fridge repair near me", "best refrigerator repair", "best refrigerator repair near me",
    "best refrigerator repair service near me", "best washing machine repair", "best washing machine repair near me", "best washing machine repair service near me",
    "best washing machine service", "best washing machine service near me", "black spot on led tv screen repair", "blomberg dishwasher repair",
    "blomberg washing machine repair", "bosch dishwasher appliance repair near me", "bosch dishwasher broken", "bosch dishwasher e09 repair",
    "bosch dishwasher e09 repair cost", "bosch dishwasher e15 repair", "bosch dishwasher fix", "bosch dishwasher maintenance",
    "bosch dishwasher repair", "bosch dishwasher repair cost", "bosch dishwasher repair dubai", "bosch dishwasher repair near me",
    "bosch dishwasher repair service", "bosch dishwasher repair service near me", "bosch dishwasher service and repair", "bosch dishwasher servicing",
    "bosch dishwasher technician", "bosch dryer drum roller replacement", "bosch dryer maintenance", "bosch dryer repair",
    "bosch dryer repair dubai", "bosch dryer repair near me", "bosch dryer service", "bosch dryer service near me",
    "bosch fridge freezer repairs", "bosch fridge repair", "bosch fridge repair near me", "bosch fridge service",
    "bosch refrigerator repair", "bosch refrigerator repair near me", "bosch refrigerator service", "bosch refrigerators repair service",
    "bosch service washing machine", "bosch tumble dryer repair", "bosch tumble dryer service", "bosch washer dryer repair",
    "bosch washer repair", "bosch washer repair dubai", "bosch washer repair near me", "bosch washing machine repair",
    "bosch washing machine repair dubai", "bosch washing machine repair service", "bosch washing machine repair service near me", "bosch washing machine repairs near me",
    "bosch washing machine service near me", "bosch washing machine technician", "bosch washing machines repair", "broken dishwasher",
    "broken display led tv", "broken dryer", "broken freezer door", "broken freezer drawer",
    "broken hair dryer", "broken lcd tv screen repair cost", "broken led tv screen repair", "broken led tv screen repair cost",
    "broken refrigerator", "broken seal washing machine", "broken washing machine", "bush washing machine repair",
    "candy dryer repair", "candy tumble dryer tripping electric", "candy washing machine repairs", "chest freezer repair near me",
    "chiller fridge repair", "cloth dryer repair", "cloth dryer repair near me", "clothes dryer maintenance",
    "clothes dryer repair", "clothes dryer repair cost", "clothes dryer repair near me dubai", "clothes dryer repair service",
    "clothes dryer service", "clothes dryer service near me", "clothes dryer vent repair", "clothes washer repair",
    "clothes washer repair near me", "clothes washing machine repair", "cof tv repair", "comenda dishwasher repairs",
    "commercial dishwasher repair", "commercial dishwasher repair near me", "commercial dishwasher service near me", "commercial washer repair",
    "commercial washer repair near me", "commercial washing machine repair", "commercial washing machine repairs near me", "cost for dishwasher repair",
    "cost of led screen replacement", "cost of led tv backlight repair", "cost of led tv screen repair", "cost of repairing led tv screen",
    "cost to fix dryer", "cost to fix led tv screen", "cost to fix refrigerator", "cost to fix washing machine",
    "cost to repair tv backlight", "cost to replace backlight on led tv", "cost to replace bearing in washing machine", "cracked led screen",
    "cracked led screen repair", "cracked led tv screen", "cracked led tv screen repair", "cracked led tv screen repair cost",
    "daewoo dishwasher repair", "daewoo fridge repair", "daewoo refrigerator repair", "daewoo washing machine repair",
    "damage led tv", "damage led tv screen", "deep freezer repair", "deep freezer repair near me",
    "deep freezer repairing", "deep freezer technician near me", "deep fridge repair near me", "dish washing machine repair near me",
    "dishwasher and washing machine repairs", "dishwasher appliance repair", "dishwasher basket repair", "dishwasher basket rust repair",
    "dishwasher commercial repair", "dishwasher fix cost", "dishwasher fixer near me", "dishwasher heating element repair",
    "dishwasher latch repair", "dishwasher leak repair", "dishwasher machine repair", "dishwasher machine repair near me",
    "dishwasher maintenance", "dishwasher maintenance near me", "dishwasher maintenance service", "dishwasher mechanic",
    "dishwasher mechanic near me", "dishwasher needs fixing", "dishwasher pcb repair", "dishwasher pump repair",
    "dishwasher repair", "dishwasher repair and service", "dishwasher repair at home", "dishwasher repair company",
    "dishwasher repair cost", "dishwasher repair fife", "dishwasher repair in my area", "dishwasher repair near me",
    "dishwasher repair near me open now", "dishwasher repair open now", "dishwasher repair person", "dishwasher repair service",
    "dishwasher repair service in my area", "dishwasher repair service near me", "dishwasher repair service near me now", "dishwasher repair shops near me",
    "dishwasher repair technician", "dishwasher rust repair", "dishwasher service", "dishwasher service and repair",
    "dishwasher service near me", "dishwasher service repair near me", "dishwasher specialist", "dishwasher specialist near me",
    "dishwasher tech", "dishwasher technician", "dishwasher technician at home dubai", "dishwasher technician near me",
    "display fridge repair near me", "domestic fridge repairs near me", "domestic refrigerator repairs near me", "doorstep repair dubai",
    "double door fridge repair", "dryer and washer repair near me", "dryer appliance repair near me", "dryer bearing replacement",
    "dryer door repair", "dryer drum felt seal replacement", "dryer drum seal replacement", "dryer drum wheel replacement",
    "dryer duct repair", "dryer duct repair near me", "dryer duct replacement", "dryer duct replacement near me",
    "dryer exhaust repair", "dryer fan replacement", "dryer fix cost", "dryer fixed near me",
    "dryer fixer", "dryer fixing service", "dryer machine fixer", "dryer machine maintenance",
    "dryer machine repair", "dryer machine repair near me", "dryer machine service", "dryer maintenance",
    "dryer maintenance near me", "dryer maintenance service", "dryer mechanic", "dryer mechanic near me",
    "dryer motor replacement", "dryer repair", "dryer repair at home", "dryer repair company near me",
    "dryer repair cost", "dryer repair man", "dryer repair near me", "dryer repair near me open now",
    "dryer repair open now", "dryer repair prices", "dryer repair service", "dryer repair service cost",
    "dryer repair service near me", "dryer repair service near me now", "dryer repair shops", "dryer repair shops near me",
    "dryer roller replacement", "dryer samsung repair", "dryer service", "dryer service near me",
    "dryer technician at home dubai", "dryer technician near me", "dryer technicians near me", "dryer thermal fuse replacement",
    "dryer timer motor replacement", "dryer vent repair", "dryer vent repair cost", "dryer vent repair near me",
    "dryer vent repair service", "dryer vent replacement near me", "dryer vent specialists", "dryer washer repair",
    "dryer washer repair near me", "dryer wheel replacement", "dyson dryer repair", "dyson hair dryer fix",
    "dyson hair dryer repair", "dyson hair dryer repair cost", "dyson hair dryer repair service", "dyson hair dryer repairs near me",
    "dyson repair hair dryer", "dyson supersonic hair dryer repair", "elba washing machine repair", "electrician for fridge repair near me",
    "electrolux dishwasher maintenance", "electrolux dishwasher repair", "electrolux dishwasher repair near me", "electrolux dishwasher repair service",
    "electrolux dryer maintenance", "electrolux dryer motor replacement cost", "electrolux dryer repair", "electrolux dryer repair near me",
    "electrolux dryer service", "electrolux fridge freezer repair", "electrolux fridge repair", "electrolux fridge repair near me",
    "electrolux fridge service", "electrolux refrigerator repair", "electrolux refrigerator repair near me", "electrolux refrigerator service",
    "electrolux washer repair", "electrolux washer repair near me", "electrolux washing machine repair", "electrolux washing machine repair near me",
    "emergency appliance repair dubai", "emergency dishwasher repair", "emergency dishwasher repair near me", "emergency dryer repair",
    "emergency freezer repair", "emergency fridge repair", "emergency fridge repair near me", "emergency led tv repair",
    "emergency refrigeration service", "emergency refrigerator", "emergency refrigerator repair", "emergency refrigerator repair near me",
    "emergency tumble dryer repair", "emergency tv repair", "emergency washer repair", "emergency washing machine repair",
    "emergency washing machine repair near me", "emergency wine cooler repair", "fagor dishwasher repair", "fagor dishwasher service",
    "fast appliance repair dubai", "fast fridge repairs", "fix backlight on tv", "fix backlight samsung tv",
    "fix bosch washing machine", "fix broken fridge shelf", "fix broken led tv screen", "fix clothes dryer",
    "fix commercial dishwasher", "fix cracked led tv screen", "fix dishwasher", "fix dishwasher heating element",
    "fix dishwasher latch", "fix dishwasher near me", "fix dishwasher pump", "fix dishwasher soap dispenser",
    "fix dryer machine", "fix dryer machine near me", "fix dryer near me", "fix dyson hair dryer",
    "fix freezer", "fix freezer seal", "fix fridge", "fix fridge compressor",
    "fix fridge door", "fix fridge door seal", "fix fridge near me", "fix fridge seal",
    "fix fridge seal with hair dryer", "fix hair dryer", "fix kenmore dishwasher", "fix laundry machine",
    "fix leaking dishwasher", "fix led screen", "fix led tv", "fix led tv backlight",
    "fix led tv cracked screen", "fix led tv screen", "fix led tv screen near me", "fix lg refrigerator",
    "fix lg washing machine", "fix mini fridge", "fix my dishwasher", "fix my dishwasher urgently",
    "fix my dryer", "fix my dryer near me", "fix my fridge", "fix my fridge freezer",
    "fix my fridge near me", "fix my refrigerator", "fix my refrigerator near me", "fix my washer",
    "fix my washing machine", "fix my washing machine near me", "fix noisy fridge", "fix refrigerator",
    "fix refrigerator compressor", "fix refrigerator door", "fix refrigerator door seal", "fix refrigerator near me",
    "fix refrigerator seal", "fix samsung refrigerator door", "fix samsung washing machine", "fix scratch on led tv screen",
    "fix tumble dryer near me", "fix washer and dryer", "fix washer and dryer near me", "fix washing machine",
    "fix washing machine door", "fix washing machine near me", "fix washing machine not spinning", "fix washing machine seal",
    "fix wine cooler", "fix wine fridge", "fixing broken led tv screen", "fixing cracked led tv screen",
    "fixing dishwasher near me", "fixing dryers near me", "fixing led tv screen", "flat screen tv repair",
    "freeze compressor repair", "freeze repair service near me", "freeze repairing shop near me", "freezer door repair",
    "freezer door repair near me", "freezer drawer repair", "freezer fix near me", "freezer gas leak repair cost",
    "freezer gasket repair", "freezer hole repair", "freezer maintenance near me", "freezer mechanic",
    "freezer mechanic near me", "freezer repair", "freezer repair service", "freezer repair service near me",
    "freezer repair shop near me", "freezer repairs near me", "freezer seal repair", "freezer technician",
    "freezer technician near me", "freon refrigerator repair", "fridge ac repair near me", "fridge and ac repair near me",
    "fridge and freezer repair", "fridge and freezer repairs near me", "fridge and washing machine repair", "fridge and washing machine repair near me",
    "fridge appliance repair", "fridge appliance repair near me", "fridge board repair", "fridge body repair",
    "fridge body repair near me", "fridge compressor repair", "fridge compressor repair cost", "fridge compressor repair near me",
    "fridge door broken", "fridge door gasket repair", "fridge door hinge broken", "fridge door hinge repair",
    "fridge door repair", "fridge door repair near me", "fridge door seal repair", "fridge electrician",
    "fridge electrician near me", "fridge engineers", "fridge experts", "fridge fixer near me",
    "fridge freezer broken", "fridge freezer fixer near me", "fridge freezer gas leak repair", "fridge freezer repair cost",
    "fridge freezer repairs", "fridge freezer repairs near me", "fridge freezer technician near me", "fridge freon leak repair",
    "fridge gas leak repair", "fridge gas leak repair cost", "fridge gasket repair", "fridge handle broken",
    "fridge handle repair", "fridge leak repair", "fridge maintenance", "fridge maintenance near me",
    "fridge maintenance service", "fridge mechanic dubai", "fridge mechanic near me", "fridge mechanic nearby",
    "fridge mechanic shop near me", "fridge mechanics", "fridge motherboard repair", "fridge refrigerator repair",
    "fridge regassing near me", "fridge repair", "fridge repair and service", "fridge repair at home",
    "fridge repair company", "fridge repair cost", "fridge repair home service near me", "fridge repair man",
    "fridge repair man near me", "fridge repair mechanic", "fridge repair mechanic near me", "fridge repair near",
    "fridge repair near by me", "fridge repair near me", "fridge repair near me open now", "fridge repair open now",
    "fridge repair person", "fridge repair service near me", "fridge repair service near me now", "fridge repair services",
    "fridge repair shop", "fridge repair shop near me", "fridge repair technician", "fridge repair technician near me",
    "fridge seal repair", "fridge seal repairs near me", "fridge service and repair", "fridge service cost",
    "fridge service near me", "fridge service repair", "fridge service repair near me", "fridge servicing near me",
    "fridge specialist", "fridge specialist near me", "fridge technician", "fridge technician near me",
    "fridge thermostat repair", "fridge washing machine repair", "fridge washing machine repair near me", "front load dryer bearing replacement",
    "front loader washer repair", "fully automatic washing machine repair", "fully automatic washing machine repair near me", "fully automatic washing machine service",
    "gaggenau dishwasher repair", "gas dryer repair near me", "gas fridge repairs", "general electric washer repair",
    "general electric washing machine repair", "glass washer repair near me", "godrej washing machine repair", "haier led tv screen replacement cost",
    "hair dryer repair", "hand dryer repair near me", "hisense dishwasher repair", "hisense fridge repairs",
    "hisense fridge repairs near me", "hisense fridge service", "hisense fridge technician", "hisense led backlight tv screen replacement",
    "hisense led screen replacement", "hisense led tv screen replacement", "hisense refrigerator repair", "hisense refrigerator repair near me",
    "hisense smart tv repair", "hisense smart tv repair shop near me", "hisense smart tv screen repair", "hisense tv backlight repair cost",
    "hisense washing machine repair near me", "hisense washing machine repairs", "hitachi fridge repair near me", "hitachi refrigerator repair near me",
    "hitachi washing machine repair", "hitachi washing machine repair near me", "home dryer repair", "home fridge repair near me",
    "home refrigerator repair", "home refrigerator repair near me", "home service appliance repair", "home service refrigerator repair",
    "home service refrigerator repair near me", "home tv repair service", "hoover dishwasher repair", "hoover dryer repair",
    "hoover fridge freezer repairs", "hoover fridge repair", "hoover tumble dryer repairs", "hoover washing machine repairs",
    "hoover washing machine repairs near me", "iffalcon tv repair", "in home washing machine repair", "indesit dishwasher repair",
    "indesit dishwasher repairs near me", "indesit fridge freezer repair", "indesit fridge repair", "indesit washer dryer repair",
    "indesit washing machine repair", "indesit washing machine repair near me", "industrial refrigeration repair near me", "industrial refrigeration services",
    "industrial washing machine repair", "kedai repair washing machine near me", "kenmore dishwasher repair", "kenwood fridge repair",
    "kenwood washing machine repair", "kitchen dishwasher repair", "lamona fridge freezer repairs", "lamona fridge repair",
    "laundry dryer repair", "laundry dryer repair near me", "laundry machine fixer", "laundry machine maintenance",
    "laundry machine repair", "laundry machine repair near me", "laundry machine repair near me dubai", "laundry machine service near me",
    "laundry machine technician", "laundry washer repair", "lcd and led tv repair", "lcd led panel repair machine price",
    "lcd panel replacement cost", "lcd panel replacement for tv", "lcd panel replacement samsung tv", "lcd screen panel replacement",
    "lcd tv cof repair", "lcd tv display repair", "lcd tv panel repair", "lcd tv repair cost",
    "lcd tv repair near me", "lcd tv repair near me home service", "lcd tv repair price", "lcd tv repair service near me",
    "lcd tv replacement screen", "lcd tv screen repair cost", "lcd tv screen repairs", "lcd tv service center near me",
    "led cracked screen repair", "led display panel repair", "led display repair machine", "led display replacement",
    "led flat screen tv repair", "led for tv repair", "led lcd panel repair service center", "led lcd tv repair",
    "led lcd tv repair near me", "led lcd tv screen replacement", "led panel repair", "led panel repair cost",
    "led panel repair machine", "led panel repair near me", "led panel replacement cost", "led repair tv",
    "led screen crack repair", "led screen damage repair", "led screen panel repair", "led screen panel replacement",
    "led screen repair", "led screen repair cost", "led screen repair near me", "led screen repair price",
    "led screen replacement", "led screen replacement cost", "led screen replacement for samsung tv", "led screen scratch repair",
    "led smart tv repair", "led smart tv repair near me", "led strip tv repair", "led television repair",
    "led tv backlight repair cost", "led tv backlight repair near me", "led tv backlight replacement", "led tv backlight replacement cost",
    "led tv backlight strip repair", "led tv backlight strip replacement", "led tv broken", "led tv broken screen",
    "led tv chip level repair", "led tv cof repair", "led tv cracked screen", "led tv cracked screen repair",
    "led tv cracked screen repair cost", "led tv display broken", "led tv display broken repair cost", "led tv display repair",
    "led tv display repair cost", "led tv display repair near me", "led tv display replacement", "led tv fix screen",
    "led tv light repair", "led tv lines on screen fix", "led tv panel repair", "led tv panel repair cost",
    "led tv panel repair near me", "led tv panel replacement", "led tv repair", "led tv repair and service",
    "led tv repair at home", "led tv repair center", "led tv repair home service", "led tv repair near me",
    "led tv repair near me home service", "led tv repair near me open now", "led tv repair open now", "led tv repair price",
    "led tv repair samsung lg tcl sony luminous solutions", "led tv repair service", "led tv repair service center", "led tv repair service near me now",
    "led tv repair shop", "led tv repair shop near me", "led tv replacement", "led tv scratch repair",
    "led tv screen damage repair", "led tv screen panel replacement", "led tv screen repair", "led tv screen repair cost",
    "led tv screen repair near me", "led tv screen repair price", "led tv screen replacement", "led tv screen replacement cost",
    "led tv screen replacement near me", "led tv screen replacement price", "led tv screen scratch repair", "led tv service center near me",
    "led tv service near me", "led tv servicing", "led tv technician near me", "lg 55 led panel replacement",
    "lg automatic washing machine repair", "lg clothes dryer repair", "lg clothes washer repair", "lg dishwasher maintenance",
    "lg dishwasher repair", "lg dishwasher repair cost", "lg dishwasher repair dubai", "lg dishwasher repair near me",
    "lg dishwasher repair service", "lg dishwasher repair service near me", "lg dishwasher technician", "lg dryer felt seal replacement",
    "lg dryer fix", "lg dryer lint trap replacement", "lg dryer maintenance", "lg dryer motherboard replacement",
    "lg dryer repair", "lg dryer repair company", "lg dryer repair dubai", "lg dryer repair near me",
    "lg dryer repair service", "lg dryer repair service near me", "lg dryer service", "lg dryer service near me",
    "lg freeze repair", "lg freeze repair near me", "lg freezer repair", "lg fridge freezer repairs",
    "lg fridge maintenance", "lg fridge mechanic", "lg fridge repair", "lg fridge repair dubai",
    "lg fridge repair near me", "lg fridge repair service", "lg fridge repair service near me", "lg fridge service",
    "lg fridge service near me", "lg fridge service repair", "lg fridge technician", "lg fridge technician near me",
    "lg lcd panel replacement", "lg led screen replacement", "lg led screen replacement price", "lg led tv backlight replacement",
    "lg led tv panel replacement cost", "lg led tv repair", "lg led tv repair dubai", "lg led tv repair near me",
    "lg led tv repair service center", "lg led tv repair service center near me", "lg led tv screen replacement cost", "lg led tv service center",
    "lg led tv service center near me", "lg oled tv cracked screen repair", "lg oled tv screen replacement", "lg refrigerator maintenance",
    "lg refrigerator mechanic near me", "lg refrigerator repair", "lg refrigerator repair dubai", "lg refrigerator repair near me",
    "lg refrigerator repair service", "lg refrigerator service", "lg refrigerator service near me", "lg refrigerator technician",
    "lg refrigerator technician near me", "lg service washing machine", "lg smart tv broken screen", "lg smart tv repair near me",
    "lg smart tv repair service near me", "lg smart tv service center", "lg smart tv service center near me", "lg tumble dryer repair dubai",
    "lg tv backlight repair cost", "lg tv backlight replacement", "lg tv backlight replacement cost", "lg tv lcd panel replacement",
    "lg tv led light replacement", "lg tv led panel replacement", "lg tv led repair", "lg tv led replacement",
    "lg tv led strip replacement", "lg tv repair dubai", "lg washer and dryer repair", "lg washer and dryer repair service",
    "lg washer authorized repair", "lg washer dryer combo repair", "lg washer dryer repair", "lg washer dryer repair near me",
    "lg washer dryer repair service near me", "lg washer repair", "lg washer repair dubai", "lg washer repair near me",
    "lg washer repair service", "lg washer repair service near me", "lg washer repairs near me", "lg washing machine board repair",
    "lg washing machine body repair", "lg washing machine door latch broken", "lg washing machine dryer repair", "lg washing machine gearbox repair",
    "lg washing machine maintenance", "lg washing machine mechanic", "lg washing machine mechanic near me", "lg washing machine motor repair",
    "lg washing machine pcb board repair", "lg washing machine pcb repair", "lg washing machine pcb repair cost", "lg washing machine repair",
    "lg washing machine repair at home", "lg washing machine repair cost", "lg washing machine repair dubai", "lg washing machine repair near me",
    "lg washing machine repair service", "lg washing machine repair service near me", "lg washing machine service near me", "lg washing machine technician",
    "lg washing machine technician near me", "lg washing machine timer repair", "local dishwasher repair", "local dishwasher repairman",
    "local freezer repair", "local fridge freezer repair", "local fridge repair", "local fridge repair near me",
    "local refrigerator repair", "local washer repair", "local washing machine repairs", "local washing machine repairs near me",
    "machine washer repair near me", "mechanic refrigeration and air conditioner", "meiko dishwasher repair", "mi led tv screen replacement",
    "mi tv backlight repair cost", "midea dishwasher repair", "midea dryer repair", "midea fridge repair",
    "midea washer repair", "midea washing machine repair", "miele dryer repair", "miele dryer repair near me",
    "miele dryer repair service", "miele dryer service", "miele dryer service near me", "miele fridge repair",
    "miele fridge service", "miele refrigerator repair", "miele tumble dryer repair", "miele tumble dryer service",
    "miele washer dryer repair", "mini fridge repair", "mini fridge repair near me", "mini refrigerator repair",
    "mobile fridge repairs near me", "mobile refrigerator repair", "mobile washer repair", "mobile washing machine repair",
    "near by freeze repair", "near by fridge repair", "near by refrigerator repair shop", "near by refrigerator service",
    "near by washing machine repair", "near fridge repair", "near me freezer repair", "near me fridge repair",
    "near me fridge repair shop", "near me refrigerator repair", "near me refrigerator repair service", "near me washing machine repair",
    "near washing machine repair", "nearby led tv repair", "nearby washing machine repair", "nearby washing machine service",
    "nearest fridge mechanic", "nearest fridge repair", "nearest fridge repair shop", "nearest led tv repair shop",
    "nearest refrigerator repair", "nearest refrigerator repair shop", "need washing machine repair", "neff dishwasher repair",
    "neff fridge freezer repairs near me", "nikai fridge repair", "oled tv repair near me", "oled tv screen replacement cost",
    "panasonic fridge repair", "panasonic fridge repair near me", "panasonic fridge service", "panasonic refrigerator repair",
    "panasonic refrigerator repair near me", "panasonic washing machine repair", "panasonic washing machine repair near me", "panasonic washing machine repair service",
    "panasonic washing machine service near me", "pcb washing machine repair", "philips hair dryer repair", "philips lcd panel replacement",
    "philips led tv backlight replacement", "philips led tv repair", "philips led tv repair near me", "philips led tv screen replacement",
    "philips led tv service center near me", "philips television service center", "philips tv backlight repair", "portable dishwasher repair",
    "portable fridge repairs", "portable washing machine repair", "quick fix appliance dubai", "refrig repair",
    "refrigeration appliance repair", "refrigeration engineers near me", "refrigerator and freezer repair", "refrigerator and washing machine repair",
    "refrigerator appliance repair", "refrigerator body repair", "refrigerator compressor repair cost", "refrigerator compressor repair near me",
    "refrigerator door gasket repair", "refrigerator door handle repair", "refrigerator door hinge repair", "refrigerator door repair",
    "refrigerator door repair near me", "refrigerator door seal repair", "refrigerator fix near me", "refrigerator freezer repair",
    "refrigerator freezer repair near me", "refrigerator freon leak repair", "refrigerator fridge repair", "refrigerator gas leak repair",
    "refrigerator gas leak repair cost", "refrigerator gasket repair", "refrigerator handle repair", "refrigerator home service repair near me",
    "refrigerator leak repair", "refrigerator maintenance", "refrigerator maintenance and repair", "refrigerator maintenance near me",
    "refrigerator maintenance service", "refrigerator maintenance service near me", "refrigerator mechanic near me", "refrigerator mechanics",
    "refrigerator repair", "refrigerator repair and services", "refrigerator repair around me", "refrigerator repair at home",
    "refrigerator repair close to me", "refrigerator repair company", "refrigerator repair company near me", "refrigerator repair cost",
    "refrigerator repair home service near me", "refrigerator repair in my area", "refrigerator repair near by me", "refrigerator repair near me",
    "refrigerator repair near me open now", "refrigerator repair nearby", "refrigerator repair open now", "refrigerator repair people",
    "refrigerator repair person", "refrigerator repair places near me", "refrigerator repair same day", "refrigerator repair service",
    "refrigerator repair service in my area", "refrigerator repair service near me", "refrigerator repair shop", "refrigerator repair shop near me",
    "refrigerator repair technician", "refrigerator repair technician near me", "refrigerator seal repair", "refrigerator service at home",
    "refrigerator service near me", "refrigerator servicing", "refrigerator specialist", "refrigerator technician",
    "refrigerator technician at home dubai", "refrigerator technician near me", "refrigerator thermostat repair", "regassing fridge near me",
    "reliable refrigeration and appliance repair", "reliable refrigerator repair", "repair backlight led tv", "repair backlight samsung tv",
    "repair broken led tv screen", "repair cracked led tv screen", "repair dishwasher dubai", "repair dishwasher near me",
    "repair dryer dubai", "repair dryer near me", "repair dyson hair dryer", "repair for washing machine near me",
    "repair freezer drawer", "repair freezer near me", "repair fridge dubai", "repair fridge freezer near me",
    "repair fridge near me", "repair led tv backlight", "repair led tv dubai", "repair led tv near me",
    "repair lg washing machine near me", "repair my dishwasher", "repair my dishwasher dubai", "repair my dryer",
    "repair my dryer dubai", "repair my freezer dubai", "repair my fridge", "repair my led tv",
    "repair my led tv dubai", "repair my refrigerator", "repair my refrigerator dubai", "repair my tumble dryer",
    "repair my tv", "repair my washer", "repair my washing machine", "repair my washing machine dubai",
    "repair my wine chiller dubai", "repair of washing machine near me", "repair pcb board washing machine", "repair refrigerator dubai",
    "repair refrigerator service", "repair samsung led tv screen", "repair scratched led tv screen", "repair service for dishwasher",
    "repair shop for refrigerator near me", "repair tumble dryer dubai", "repair tv dubai", "repair tv led",
    "repair tv led screen", "repair tv panel", "repair wash machine near me", "repair washer and dryer near me",
    "repair washer dubai", "repair washer near me", "repair washing machine dubai", "repair washing machine service",
    "repair wine cooler near me", "repairman for washing machine near me", "replace backlight on samsung tv", "replace led tv screen",
    "replace samsung washing machine door seal", "replace washer bearing", "replace washer belt", "replace washing machine bearings",
    "replace washing machine belt", "replacement led for lg tv", "replacement led for tv backlight", "rerack dishwasher repair",
    "roper washer repair", "roper washing machine repair", "same day dishwasher repair", "same day dishwasher repair dubai",
    "same day dryer repair", "same day dryer repair dubai", "same day dryer repair near me", "same day fridge repair",
    "same day fridge repair dubai", "same day led tv repair", "same day refrigerator repair", "same day repair dubai",
    "same day tumble dryer repair", "same day tv repair", "same day tv repair dubai", "same day washer repair",
    "same day washing machine repair", "same day washing machine repair dubai", "same day washing machine repair service", "same day wine cooler repair",
    "same day wine fridge repair dubai", "samsung clothes dryer repair", "samsung dishwasher fix", "samsung dishwasher maintenance",
    "samsung dishwasher repair", "samsung dishwasher repair service", "samsung dishwasher repairs near me", "samsung dishwasher service",
    "samsung dishwasher technician", "samsung double door fridge repair", "samsung dryer door seal replacement", "samsung dryer drum felt seal replacement",
    "samsung dryer drum gasket replacement", "samsung dryer fan replacement", "samsung dryer fix", "samsung dryer idler pulley replacement",
    "samsung dryer maintenance", "samsung dryer motherboard replacement", "samsung dryer motor replacement", "samsung dryer repair",
    "samsung dryer repair dubai", "samsung dryer repair near me", "samsung dryer repair service", "samsung dryer roller replacement",
    "samsung dryer service", "samsung dryer thermostat replacement", "samsung freezer repair", "samsung fridge double door repair",
    "samsung fridge fix", "samsung fridge freezer repairs", "samsung fridge maintenance", "samsung fridge mechanic near me",
    "samsung fridge motherboard repair cost", "samsung fridge repair", "samsung fridge repair cost", "samsung fridge repair dubai",
    "samsung fridge repair ireland", "samsung fridge repair near me", "samsung fridge repair service", "samsung fridge repair service near me",
    "samsung fridge service", "samsung fridge service near me", "samsung fridge service repair", "samsung fridge servicing",
    "samsung fridge technician", "samsung lcd tv repair center", "samsung lcd tv repair near me", "samsung led panel repair",
    "samsung led screen repair", "samsung led screen replacement", "samsung led screen replacement price", "samsung led tv backlight repair",
    "samsung led tv backlight repair cost", "samsung led tv backlight replacement", "samsung led tv backlight replacement cost", "samsung led tv display repair",
    "samsung led tv panel repair", "samsung led tv repair", "samsung led tv repair center", "samsung led tv repair dubai",
    "samsung led tv repair near me", "samsung led tv repair service center", "samsung led tv repair service near me", "samsung led tv screen repair",
    "samsung led tv screen replacement", "samsung led tv screen replacement cost", "samsung led tv service center", "samsung led tv service center near me",
    "samsung led tv servicing", "samsung led tv speaker replacement", "samsung led tv speaker replacement cost", "samsung qled tv repair",
    "samsung qled tv screen replacement", "samsung refrig repair", "samsung refrig repair near me", "samsung refrigerator door repair",
    "samsung refrigerator double door repair", "samsung refrigerator fix", "samsung refrigerator maintenance", "samsung refrigerator mechanic near me",
    "samsung refrigerator repair", "samsung refrigerator repair cost", "samsung refrigerator repair dubai", "samsung refrigerator repair service",
    "samsung refrigerator service", "samsung refrigerator servicing", "samsung refrigerator technician", "samsung smart tv backlight repair",
    "samsung smart tv repair", "samsung smart tv repair center", "samsung smart tv repair near me", "samsung smart tv repair shop near me",
    "samsung smart tv replacement screen", "samsung smart tv screen repair", "samsung smart tv service center", "samsung smart tv service center near me",
    "samsung tumble dryer repair", "samsung tumble dryer repair dubai", "samsung tv backlight fix", "samsung tv backlight repair cost",
    "samsung tv backlight replacement", "samsung tv backlight replacement cost", "samsung tv fix backlight", "samsung tv lcd panel replacement",
    "samsung tv led backlight repair", "samsung tv led panel replacement", "samsung tv led repair", "samsung tv led replacement",
    "samsung tv led screen replacement", "samsung tv led screen replacement cost", "samsung tv led strip replacement", "samsung tv led strip replacement cost",
    "samsung tv motherboard repair cost", "samsung tv repair dubai", "samsung tv servicing", "samsung washer and dryer maintenance service",
    "samsung washer and dryer repair", "samsung washer and dryer service", "samsung washer dryer repair", "samsung washer dryer service",
    "samsung washer fix", "samsung washer repair", "samsung washer repair dubai", "samsung washer repair service",
    "samsung washer technician", "samsung washing machine drum repair", "samsung washing machine maintenance", "samsung washing machine mechanic",
    "samsung washing machine mechanic near me", "samsung washing machine pcb board repair cost", "samsung washing machine pcb repair", "samsung washing machine pcb repair cost",
    "samsung washing machine repair", "samsung washing machine repair cost", "samsung washing machine repair dubai", "samsung washing machine repair service",
    "samsung washing machine repairs near me", "samsung washing machine technician", "sansui tv repair near me", "seal broken on washing machine",
    "seal fridge repair", "seal on washing machine broken", "semi automatic washing machine repair", "semi automatic washing machine repair near me",
    "service dryer near me", "service washing machine near me", "shaking washing machine fix", "sharp fridge repair",
    "sharp refrigerator repair", "sharp tv backlight replacement cost", "shop fridge repair near me", "side by side refrigerator repair",
    "siemens dishwasher maintenance", "siemens dishwasher repair", "siemens dishwasher repair dubai", "siemens dishwasher repair near me",
    "siemens dryer repair", "siemens fridge freezer repairs", "siemens fridge repair", "siemens fridge repair dubai",
    "siemens refrigerator repair", "siemens refrigerator repair dubai", "siemens refrigerator service", "siemens washing machine repair",
    "siemens washing machine repair near me", "singer washing machine repair", "skyworth led tv screen replacement", "small fridge repair",
    "small fridge repair near me", "small refrigerator repair", "small refrigerator repair near me", "smart led tv repair",
    "smart led tv repair near me", "smart tv backlight repair", "smeg washing machine repair", "smelly fridge fix",
    "smelly refrigerator fix", "someone to fix washing machine", "someone to fix washing machine near me", "sony bravia smart tv service center",
    "sony lcd tv repair", "sony led panel repair", "sony led panel replacement", "sony led screen replacement",
    "sony led tv backlight replacement cost", "sony led tv broken screen", "sony led tv panel repair", "sony led tv repair",
    "sony led tv repair dubai", "sony led tv repair near me", "sony led tv screen replacement", "sony led tv screen replacement cost",
    "sony led tv service center near me", "sony oled tv repair", "sony tv backlight repair cost", "sony tv led panel replacement",
    "sony tv led repair", "squeaky dryer fix", "squeaky dryer repair", "stackable washer and dryer repair",
    "super general refrigerator repair", "super general washing machine repair", "swan dishwasher repair", "tcl lcd panel replacement",
    "tcl led panel replacement", "tcl led screen replacement", "tcl led tv backlight repair", "tcl led tv panel replacement",
    "tcl led tv service center near me", "tcl smart tv repair near me", "tcl smart tv service center", "tcl tv backlight repair",
    "technician for washing machine near me", "technician refrigerator repair", "teka washing machine repair", "thermal fuse replacement dryer",
    "thomson led tv service center near me", "toshiba fridge repair", "toshiba led tv repair", "toshiba tv backlight replacement",
    "toshiba washing machine repair", "toshiba washing machine repair near me", "truck fridge repair", "truck fridge repair near me",
    "truck refrigerator repair", "tumble dryer fixer", "tumble dryer fixer near me", "tumble dryer maintenance",
    "tumble dryer repair at home", "tumble dryer repair cost", "tumble dryer repair man near me", "tumble dryer repair near me",
    "tumble dryer repair near me open now", "tumble dryer repair open now", "tumble dryer repairs", "tumble dryer repairs near me",
    "tumble dryer service", "tumble dryer service near me", "tumble dryer technician near me", "tumble dryers repairs near me",
    "tv backlight fix", "tv backlight repair", "tv backlight repair cost", "tv backlight replacement",
    "tv backlight replacement cost", "tv fixing service near me", "tv lcd led repair", "tv led backlight repair",
    "tv led backlight repair cost", "tv led display repair", "tv led light repair", "tv led panel replacement",
    "tv led repair", "tv led repair cost", "tv led repair near me", "tv led replacement cost",
    "tv led screen repair", "tv led screen replacement", "tv led screen replacement cost", "tv led strip repair",
    "tv led strip replacement", "tv repair at home", "tv repair backlight", "tv repair backlight cost",
    "tv repair led screen", "tv repair near me", "tv repair near me open now", "tv repair open now",
    "tv screen led repair", "tv technician at home dubai", "tv technician near me", "urban clap refrigerator repair",
    "urban clap refrigerator repair charges", "urban clap washing machine repair", "urban clap washing machine repair charges", "urban clap washing machine service",
    "urban company fridge repair", "urban company fridge repair charges", "urban company refrigerator repair", "urban company washing machine repair",
    "urban company washing machine service", "urban fridge repair", "urban washing machine repair", "urbanclap fridge repair",
    "urbanclap washing machine repair", "urbanclap washing machine service", "urgent fridge repair dubai", "videocon smart tv service center",
    "videocon tv repair near me", "videocon tv repairing", "videocon tv service center near me", "viking fridge repair",
    "viking refrigerator repair", "vu tv screen replacement cost", "waeco fridge repairs", "washer & dryer repair service",
    "washer & dryer repair service near me", "washer and dryer fixer", "washer and dryer fixer near me", "washer and dryer maintenance",
    "washer and dryer maintenance near me", "washer and dryer maintenance service", "washer and dryer repair", "washer and dryer repair near me",
    "washer and dryer repair service", "washer and dryer repair service near me", "washer and dryer service", "washer and dryer service near me",
    "washer appliance repair", "washer bearing repair cost", "washer broken", "washer door seal repair",
    "washer dryer combo repair", "washer dryer fixer", "washer dryer maintenance", "washer dryer maintenance near me",
    "washer dryer maintenance service", "washer dryer repair", "washer dryer repair cost", "washer dryer repair man",
    "washer dryer repair near me", "washer dryer repair service", "washer dryer repair service near me", "washer dryer service",
    "washer dryer service near me", "washer fixer", "washer fixer near me", "washer maintenance near me",
    "washer repair", "washer repair at home", "washer repair at home dubai", "washer repair company",
    "washer repair cost", "washer repair near me", "washer repair near me open now", "washer repair open now",
    "washer repair person", "washer repair service", "washer repair service near me", "washer repair shops near me",
    "washer technician", "washer technician near me", "washer timer repair", "washing dryer repair",
    "washing machine & dryer repair service", "washing machine & dryer repair service near me", "washing machine and dryer repair", "washing machine and dryer repair near me",
    "washing machine and dryer service", "washing machine and fridge repair", "washing machine and fridge repair near me", "washing machine appliance repair",
    "washing machine appliance repair near me", "washing machine board repair", "washing machine board repair cost", "washing machine body repair",
    "washing machine body repair near me", "washing machine door broken", "washing machine door repair", "washing machine door seal repair",
    "washing machine drum broken", "washing machine drum repair", "washing machine drum repair cost", "washing machine dryer motor repair",
    "washing machine dryer repair", "washing machine dryer repair near me", "washing machine dryer repair service", "washing machine dryer repair service near me",
    "washing machine electrician", "washing machine electrician near me", "washing machine engineers", "washing machine engineers near me",
    "washing machine fitter near me", "washing machine fitters near me", "washing machine fixers near me", "washing machine fridge repair",
    "washing machine lg repair near me", "washing machine machine repair", "washing machine machine repair near me", "washing machine maintenance",
    "washing machine maintenance near me", "washing machine maintenance service", "washing machine maintenance service near me", "washing machine maintenance wash",
    "washing machine mechanic", "washing machine mechanic near me", "washing machine mechanic nearby", "washing machine motor repair",
    "washing machine motor repair cost", "washing machine motor repair near me", "washing machine panel repair", "washing machine panel repair cost",
    "washing machine pcb board repair", "washing machine pcb board repair near me", "washing machine pcb repair", "washing machine pcb repair cost",
    "washing machine pcb repair near me", "washing machine repair", "washing machine repair & services", "washing machine repair around me",
    "washing machine repair at home", "washing machine repair at home near me", "washing machine repair charges", "washing machine repair company",
    "washing machine repair cost", "washing machine repair cost near me", "washing machine repair home service", "washing machine repair home service near me",
    "washing machine repair in", "washing machine repair in marina", "washing machine repair in my area", "washing machine repair in near me",
    "washing machine repair mechanic", "washing machine repair mechanic near me", "washing machine repair near by", "washing machine repair near by me",
    "washing machine repair near me", "washing machine repair near me dubai", "washing machine repair near me lg", "washing machine repair near me open now",
    "washing machine repair near to me", "washing machine repair open now", "washing machine repair people", "washing machine repair person",
    "washing machine repair person near me", "washing machine repair same day", "washing machine repair service", "washing machine repair service near me",
    "washing machine repair shops", "washing machine repair shops near me", "washing machine repair technician", "washing machine repair technician near me",
    "washing machine repair urban company", "washing machine samsung repair near me", "washing machine seal repair", "washing machine service",
    "washing machine service at home", "washing machine service near", "washing machine service near me", "washing machine servicing at home",
    "washing machine shock absorber repair", "washing machine specialist", "washing machine specialist near me", "washing machine switch repair",
    "washing machine tech", "washing machine technician", "washing machine technician near me", "washing machine technicians near me",
    "washing machine timer repair", "washing machine timer switch repair", "washing washing machine repair", "who can fix my dishwasher today",
    "who can fix my dryer today", "who can fix my fridge today", "who can fix my tv today", "who can fix my washing machine today",
    "who can fix my wine cooler today", "who can repair my dishwasher", "who can repair my dryer", "who can repair my fridge",
    "who can repair my led tv", "who can repair my refrigerator", "who can repair my tumble dryer", "who can repair my tv",
    "who can repair my washer", "who can repair my washing machine", "who can repair my wine cooler", "who fixes dishwashers near me",
    "who fixes dryers near me", "who fixes fridges near me", "who fixes washing machines near me", "who fixes wine coolers near me",
    "wine chiller repair", "wine chiller repair near me", "wine cooler repair", "wine cooler repair near me",
    "wine cooler repair near me open now", "wine cooler repair open now", "wine cooler repair service", "wine cooler repair service near me",
    "wine cooler technician at home dubai", "wine fridge broken", "wine fridge repair", "wine fridge repair near me",
    "wine fridge repair service near me now", "wine refrigerator repair", "wine refrigerator repair near me", "zanussi dishwasher repair",
    "zanussi dishwasher repair near me", "zanussi tumble dryer repair", "zanussi washer dryer repair", "أسعار تصليح شاشات تلفزيون سامسونج",
    "أسعار تصليح شاشة التلفزيون", "إصلاح تلفزيونات", "إصلاح قفل باب الغسالة الاتوماتيك", "ارقام تصليح ثلاجات",
    "ارقام تصليح شاشات تلفزيون", "ارقام تصليح غسالات", "اسعار تصليح كسر شاشة التلفزيون lg", "اصلاح الثلاجات",
    "اصلاح الثلاجة", "اصلاح الثلاجة المنزلية", "اصلاح الغسالات الاتوماتيك", "اصلاح الغسالة",
    "اصلاح الغسالة الاتوماتيك", "اصلاح تلفزيون سامسونج", "اصلاح ثلاجات", "اصلاح ثلاجة سامسونج",
    "اصلاح شاشة التلفزيون المكسورة", "اصلاح غسالات", "اصلاح غسالات اتوماتيك", "اصلاح غسالات سامسونج",
    "اصلاح غسالة lg", "اصلاح غسالة ال جي", "اصلاح غسالة الملابس", "اصلاح غسالة صحون",
    "اصلاح كارتة الغسالة الفول اتوماتيك", "اصلاح كروت الغسالات", "اقرب محل تصليح تلفزيونات", "اقرب محل تصليح ثلاجات",
    "اقرب محل تصليح شاشات تلفزيون", "اقرب محل تصليح غسالات", "اماكن تصليح تلفزيونات", "اماكن تصليح شاشات التلفزيون",
    "تصليح التلفزيون البلازما", "تصليح التلفزيون في البيت", "تصليح الثلاجات في المنزل", "تصليح الريموت التلفزيون",
    "تصليح الشاشات التلفزيون", "تصليح الغسالات الاتوماتيك", "تصليح الغسالات الاتوماتيك lg", "تصليح الغسالات الفوق اتوماتيك",
    "تصليح الغسالة", "تصليح الغسالة الاتوماتيك", "تصليح الغسالة العادية", "تصليح الغساله الاتوماتيك",
    "تصليح باب غسالة اتوماتيك", "تصليح تلفزيون", "تصليح تلفزيون 24 ساعة", "تصليح تلفزيون ال جي",
    "تصليح تلفزيون بالمنزل", "تصليح تلفزيون دبي", "تصليح تلفزيون سوني", "تصليح تلفزيون طوارئ",
    "تصليح تلفزيون قريب مني", "تصليح تلفزيون مفتوح الآن", "تصليح تلفزيونات lg", "تصليح تلفزيونات حولي",
    "تصليح تلفزيونات سامسونج", "تصليح تلفزيونات في المنزل", "تصليح ثلاجات", "تصليح ثلاجات 24 ساعة",
    "تصليح ثلاجات السيارات", "تصليح ثلاجات باكستاني", "تصليح ثلاجات بيكو", "تصليح ثلاجات دبي",
    "تصليح ثلاجات سامسونج", "تصليح ثلاجات طوارئ", "تصليح ثلاجات قريب مني", "تصليح ثلاجات مفتوح الآن",
    "تصليح ثلاجات نفس اليوم دبي", "تصليح ثلاجات وغسالات", "تصليح ثلاجة lg", "تصليح ثلاجة ال جي",
    "تصليح ثلاجه", "تصليح جميع انواع التلفزيونات", "تصليح ريموت التلفزيون", "تصليح شاشات تلفزيون",
    "تصليح شاشات تلفزيون lg", "تصليح شاشات تلفزيون ال جي", "تصليح شاشات تلفزيون سامسونج", "تصليح شاشات تلفزيون سوني",
    "تصليح شاشات تلفزيون في المنزل", "تصليح شاشات تلفزيون مكسورة", "تصليح شاشة التلفزيون البلازما", "تصليح شاشة التلفزيون المكسورة",
    "تصليح شاشة تلفزيون", "تصليح شاشة تلفزيون lcd", "تصليح شاشة تلفزيون lg", "تصليح شاشة تلفزيون tcl",
    "تصليح شاشة تلفزيون سامسونج سمارت", "تصليح شاشة تلفزيون سمارت", "تصليح غسالات", "تصليح غسالات 24 ساعة",
    "تصليح غسالات lg", "تصليح غسالات اتوماتيك", "تصليح غسالات اتوماتيك بيكو", "تصليح غسالات اتوماتيك زانوسى",
    "تصليح غسالات اتوماتيك سامسونج", "تصليح غسالات ال جي", "تصليح غسالات المنطقه العاشره", "تصليح غسالات بالمنزل",
    "تصليح غسالات حوضين", "تصليح غسالات دايو", "تصليح غسالات دبي", "تصليح غسالات سامسونج",
    "تصليح غسالات صحون", "تصليح غسالات صحون دبي", "تصليح غسالات صحون طوارئ", "تصليح غسالات صحون قريب مني",
    "تصليح غسالات طوارئ", "تصليح غسالات عادية", "تصليح غسالات فوق اتوماتيك", "تصليح غسالات في المنزل",
    "تصليح غسالات قريب مني", "تصليح غسالات مفتوح الآن", "تصليح غسالات نصف اتوماتيك", "تصليح غسالات نفس اليوم دبي",
    "تصليح غسالات هيتاشي", "تصليح غسالات وثلاجات", "تصليح غسالة اتوماتيك lg", "تصليح غسالة ال جي اتوماتيك",
    "تصليح غسالة ال جي فوق اتوماتيك", "تصليح غسالة بوش", "تصليح غسالة سامسونج اتوماتيك", "تصليح غسالة صحون اريستون",
    "تصليح غسالة صحون قريب مني", "تصليح غسالة صحون مفتوح الآن", "تصليح غسالة كوندور", "تصليح غسالة ملابس",
    "تصليح غسالة ملابس اتوماتيك", "تصليح غسالة ويرلبول", "تصليح فريزر الثلاجة", "تصليح كارتة الغسالة الاتوماتيك",
    "تصليح كمبروسر ثلاجة", "تصليح لوحات الغسالات الاتوماتيك", "تصليح مروحة الغسالة العادية", "تصليح مفتاح الغسالة الاتوماتيك",
    "تصليح نشافات", "تصليح نشافات دبي", "تصليح نشافات طوارئ", "تصليح نشافات قريب مني",
    "تصليح نشافات مفتوح الآن", "تصليح نشافات نفس اليوم دبي", "تصليح نشافة الغسالة", "تصليح نشافة الغسالة العادية",
    "تصليح نشافة ملابس", "تصليح نشافه غساله", "تكلفة تصليح شاشة تلفزيون سامسونج", "رقم تصليح تلفزيونات",
    "رقم تصليح ثلاجات", "رقم تصليح غسالات", "رقم تصليح غسالات اتوماتيك", "رقم فني تصليح غسالات دبي",
    "رقم مصلح تلفزيونات", "رقم مصلح غسالات", "سعر تصليح شاشة التلفزيون", "سعر تصليح شاشة تلفزيون tcl",
    "سعر تصليح شاشة تلفزيون سامسونج", "سعر تصليح شاشة تلفزيون سامسونج 43 بو", "شركات صيانة الثلاجات", "شركة تصليح تلفزيونات",
    "شركة تصليح ثلاجات", "شركة تصليح غسالات", "شركه تصليح الغسالات الاتوماتيك", "صيانة الثلاجات المنزلية",
    "صيانة الغسالات الفوق اتوماتيك", "صيانة الغسالة الاتوماتيك", "صيانة تلفزيون", "صيانة تلفزيونات بالمنزل",
    "صيانة ثلاجات", "صيانة ثلاجة كريازى", "صيانة غسالات", "صيانة غسالات اتوماتيك",
    "صيانة غسالات صحون", "صيانة نشافات", "عامل تصليح ثلاجات", "عامل تصليح غسالات",
    "فنى تصليح ثلاجات", "فنى تصليح غسالات", "فنى ثلاجات", "فنى غسالات اتوماتيك",
    "فني اصلاح ثلاجات", "فني تبريد ثلاجات", "فني تصليح ثلاجات", "فني تصليح شاشات تلفزيون",
    "فني تصليح غسالات", "فني تصليح غسالات اتوماتيك", "فني تصليح غسالة صحون", "فني تلفزيون",
    "فني تلفزيون في المنزل دبي", "فني تلفزيون قريب مني", "فني ثلاجات", "فني ثلاجات في المنزل دبي",
    "فني ثلاجات قريب مني", "فني صيانة غسالات", "فني صيانة غسالات اتوماتيك", "فني غسالات",
    "فني غسالات اتوماتيك", "فني غسالات صحون", "فني غسالات صحون قريب مني", "فني غسالات في المنزل دبي",
    "فني غسالات قريب مني", "فني غسالة صحون في المنزل دبي", "فني نشافات", "فني نشافات في المنزل دبي",
    "فني نشافات قريب مني", "كهربائي تصليح غسالات", "محل اصلاح تلفزيونات", "محل اصلاح ثلاجات",
    "محل تصليح التلفزيون", "محل تصليح التلفزيونات", "محل تصليح الغسالات الاتوماتيك", "محل تصليح ثلاجات",
    "محل تصليح ثلاجات وغسالات", "محل تصليح ريموت التلفزيون", "محل تصليح شاشات تلفزيون", "محل تصليح شاشات تلفزيون سامسونج",
    "محل تصليح غسالات", "محل تصليح غسالات وثلاجات", "محل صيانة تلفزيونات", "محل صيانة غسالات اتوماتيك",
    "محلات اصلاح شاشات تلفزيون", "محلات تصليح غسالات اتوماتيك", "مركز تصليح تلفزيونات", "مركز تصليح ثلاجات",
    "مركز صيانة غسالات", "مصلح تلفزيونات", "مصلح ثلاجات", "مصلح غسالات",
    "مصلح غسالات اتوماتيك", "من يصلح التلفزيون بالقرب مني", "من يصلح الثلاجات بالقرب مني", "من يصلح الغسالات بالقرب مني",
    "من يصلح النشافات بالقرب مني", "من يصلح غسالات الصحون بالقرب مني", "ورشة تصليح تلفزيونات", "ورشة تصليح ثلاجات"
  ];

  var PRODUCTS = [
    "admiral", "aeg", "affordable", "appliance", "ariston", "asko",
    "authorized", "automatic", "average", "backlight", "bearing", "beko",
    "board", "body", "bosch", "broken", "candy", "center",
    "charges", "chiller", "clap", "clothes", "commercial", "compressor",
    "cooler", "cost", "cracked", "daewoo", "damage", "dishwasher",
    "display", "door", "double", "drawer", "drum", "dryer",
    "dryers", "duct", "dyson", "electric", "electrician", "electrolux",
    "engineers", "felt", "fixer", "freeze", "freezer", "freon",
    "fridge", "fully", "gasket", "general", "general electric", "hair",
    "handle", "hinge", "hisense", "hitachi", "home", "hoover",
    "indesit", "industrial", "latch", "laundry", "leak", "lg",
    "light", "machine", "mechanic", "midea", "miele", "mini",
    "mobile", "motherboard", "motor", "nearest", "oled", "open",
    "panasonic", "panel", "person", "philips", "portable", "price",
    "refrig", "refrigeration", "refrigerator", "roller", "samsung", "scratch",
    "screen", "seal", "sharp", "shop", "shops", "siemens",
    "small", "smart", "sony", "strip", "thermostat", "timer",
    "toshiba", "truck", "tumble", "urban", "urbanclap", "vent",
    "videocon", "washer", "whirlpool", "wine", "zanussi", "اتوماتيك",
    "ارقام", "اقرب", "الآن", "الاتوماتيك", "التلفزيون", "الثلاجات",
    "الثلاجة", "العادية", "الغسالات", "الغسالة", "المنزل", "اليوم",
    "بالقرب", "بالمنزل", "تلفزيون", "تلفزيونات", "ثلاجات", "ثلاجة",
    "ساعة", "سامسونج", "شاشات", "شاشة", "صحون", "غسالات",
    "غسالة", "مصلح", "مفتوح", "ملابس", "نشافات", "نشافة",
    "يصلح"
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
    "restore", "same day", "service", "services", "servicing", "solution",
    "specialist", "tailor made", "technician", "today", "troubleshoot", "trusted",
    "urgent", "wash", "washing", "whatsapp", "اصلاح", "تبديل",
    "تركيب", "تصليح", "تعبئة", "تنظيف", "خدمة", "شركة",
    "صيانة", "طوارئ", "فني", "فنيين", "قريب", "مركز"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "build", "builder", "clean", "cleaning",
    "custom", "design", "designer", "detect", "detection", "diagnose",
    "fabrication", "fitted", "fix", "fixed", "fixes", "fixing",
    "inspect", "inspection", "install", "installation", "installing", "installs",
    "made to measure", "made to order", "maintain", "maintenance", "maker", "making",
    "mount", "mounting", "refurbish", "remodel", "remodeling", "renovate",
    "renovation", "repair", "repairing", "repairs", "replace", "replacement",
    "replacing", "restoration", "restore", "service", "services", "servicing",
    "tailor made", "troubleshoot", "unblock", "unclog", "wash", "washing",
    "اصلاح", "تبديل", "تركيب", "تصليح", "تعبئة", "تنظيف",
    "صيانة"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "blockage", "blocked", "broke", "broken",
    "burning smell", "burst", "clogged", "compressor not running",
    "corroded", "crack", "cracked", "damage",
    "damaged", "door not closing", "dripping", "error code showing",
    "fault", "faulty", "ice maker not working", "issue",
    "issues", "jammed", "kharab", "leakage",
    "leaking", "leaking from bottom", "leaking water", "leaky",
    "low pressure", "making noise", "no picture no sound", "noise",
    "noisy", "not cooling", "not draining", "not drying clothes",
    "not heating", "not spinning", "not starting", "not switching on",
    "not turning on", "not working", "overflow", "overflowing",
    "overflowing water", "overheating", "problem", "problems",
    "rusted", "screen gone black", "shaking too much", "short circuit",
    "slow", "smell", "smells", "smells bad",
    "smelly", "stopped working", "strange noise", "stuck",
    "stuck mid cycle", "tripping", "tripping fuse", "vibrating",
    "water coming out", "weak", "won't work", "wont turn",
    "wont work"
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
            } else if (!actionHit && !strongHit && !isHireOrFault(term)
                       && PRICE_RE.test(term)) {
              // 4️⃣a product price, no service word ("fridge price")
              reason = "Product price, no service word";
            } else if ((problemHit || SYMPTOM_RE.test(term)) && !actionHit && !strongHit
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
