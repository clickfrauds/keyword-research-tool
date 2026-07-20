/**
 * 🛡️ NEGATIVE GUARD v2 — Best Glass Partition Dubai (Dubai, United Arab Emirates)
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
    "glass partitions dubai"
  ];
  var DATE_RANGE = "TODAY";        // TODAY | YESTERDAY | LAST_7_DAYS
  var MIN_IMPRESSIONS = 0;
  var DRY_RUN = true;              // ⚠️ pehle 2-3 din TRUE rakhein — sirf log karega.
                                   // Log theek lagay to false kar dein.
  var PROTECT_CONVERTERS = true;   // conversion wali term kabhi ban nahi hogi
  var ALLOW_SHORT_PRODUCT = true;  // "kitchen cabinets" type <=3-word product query allow

  var FORBIDDEN_LOCATIONS = [
    "abu dhabi", "ajman", "al ain", "bahrain", "doha", "fujairah",
    "jeddah", "ksa", "kuwait", "manama", "muscat", "oman",
    "qatar", "rak", "ras al khaimah", "riyadh", "saudi arabia", "sharjah",
    "uaq", "umm al quwain"
  ];

  var EDU_CAREER = [
    "10mm vs 12mm glass difference", "academy", "aluminium door sizes standard", "aluminium fabrication training",
    "aluminium fitter course", "aluminium grades for doors", "apprenticeship", "balustrade height regulation dubai",
    "business kaise", "career", "careers", "catalogue",
    "certificate", "certification", "course", "courses",
    "cv", "datasheet", "define", "definition",
    "diagram", "diploma", "diploma in glass and glazing", "dukan kaise",
    "glass fabricator salary", "glass installer training dubai", "glass partition course", "glass partition materials list",
    "glass partition specification", "glass railing height standard", "glass thickness for railing", "glass thickness for shower partition",
    "glazier course dubai", "glazier salary dubai", "hiring", "how do",
    "how does", "how to become", "how to become glass fabricator", "in hindi",
    "in urdu", "institute", "internship", "interview questions",
    "items list", "job", "jobs", "ka kaam",
    "ka kam", "kaise bane", "kaise khole", "kaise seekhe",
    "kaise sikhe", "kitne prakar", "kitne type", "kitni salary",
    "kya hai", "kya hota hai", "material list", "meaning in",
    "meaning of", "mechanism of", "name list", "pergola design ideas",
    "recruitment", "resume", "salaries", "salary",
    "schematic", "shop kaise", "shower glass thickness guide", "size chart",
    "standard height", "tempered glass vs toughened glass", "tool name", "tools list",
    "tools name", "training", "translate", "types of",
    "types of aluminium doors", "types of glass partitions", "types of glass railing", "types of pergola",
    "vacancies", "vacancy", "wage", "wages",
    "what happens", "what is"
  ];

  var INFO_DIY = [
    "difference between", "diy", "diy aluminium door installation", "do it yourself",
    "ghar par kaise", "glass partition cleaning solution", "how to", "how to adjust shower door",
    "how to clean shower glass partition", "how to fix glass partition at home", "how to install glass railing diy", "how to measure for glass partition",
    "how to polish glass railing", "how to remove hard water stains from glass", "how to remove scratches from glass", "how to seal shower glass partition",
    "how to tighten glass door hinge diy", "instructions", "khud banana", "khud lagana",
    "khud se", "ki setting", "manual", "shower glass partition maintenance tips",
    "tutorial", "what causes", "wikipedia", "youtube"
  ];

  var FORBIDDEN_WORDS = [
    "ac repair", "amazon", "aquarium glass", "auction", "b2b", "buy online",
    "car glass", "careers", "carpenter", "curtain wall", "distributor", "dubizzle",
    "ebay", "electrician", "eyeglasses", "false ceiling", "flooring", "for rent",
    "franchise", "glass art", "glass bottle", "glass cutting machine price", "glass factory", "glass painting",
    "glass recycling", "glass table price online", "gypsum partition", "hiring", "internship", "job vacancy",
    "jobs", "ka dam", "ka price", "khareedna", "kharidna", "ki qeemat",
    "kitchen cabinet", "kitna hai", "kitne ka", "manufacturer directory", "marketplace", "mirror shop near me",
    "mobile screen", "olx", "painting contractor", "phone glass", "photo frame glass", "plumber",
    "rent", "rental", "salary", "sasta", "scrap glass", "second hand",
    "spare parts", "stained glass", "sunglasses", "supplier list", "tender", "tiling",
    "training course", "upvc windows", "used", "wardrobe", "warranty claim", "wholesale",
    "windshield", "wooden partition"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "banister", "cabin", "cubicle", "door", "frame", "handrail",
    "panels", "pergola", "railing"
  ];

  var SAFE_ROOTS = [
    "10mm shower glass partition price dubai", "12mm glass railing price", "acoustic glass office partitions", "aluminium and glass works dubai",
    "aluminium balcony balustrades", "aluminium door fabrication dubai", "aluminium door installation dubai", "aluminium door manufacturer dubai",
    "aluminium door price in dubai", "aluminium door repair dubai", "aluminium door supplier dubai", "aluminium doors and windows manufacturers in dubai",
    "aluminium doors dubai", "aluminium doors in dubai", "aluminium glass balcony", "aluminium glass balcony railing",
    "aluminium glass office partition", "aluminium glass partition price dubai", "aluminium glass railing for balcony", "aluminium office partitioning",
    "aluminium pergola contractor dubai", "aluminium pergola dubai", "aluminium pergola for villa dubai", "aluminium pergola installation dubai",
    "aluminium pergola price dubai", "aluminium pergola suppliers in dubai", "aluminium sliding door price dubai", "aluminum doors dubai",
    "aluminum doors in dubai", "aluminum glass railing price per foot", "aluminum pergola dubai", "aluminum pergola manufacturers in dubai",
    "balconies and balustrades", "balcony balustrade", "balcony glass balustrade price", "balcony glass balustrade price dubai",
    "balcony glass fencing cost dubai", "balcony handrail glass", "balcony handrail with glass", "balcony railings with glass",
    "balcony toughened glass price", "baluster glass", "balustrade capping", "balustrade glass railing",
    "balustrade installation", "balustrade on balcony", "balustrades prices", "balustrading",
    "bathroom cabin glass", "bathroom glass cabin", "bathroom glass divider price", "bathroom glass door partition",
    "bathroom glass partition door", "bathroom glass partition installation dubai", "bathroom glass partition online", "bathroom glass partition wall",
    "bathroom interior design with glass partition", "bathroom partition glass door", "bathroom shower divider", "bathroom shower glass partition price",
    "bathroom shower separator", "bathroom toughened glass partition", "bathtub glass partition dubai", "bathtub glass partition installation",
    "best aluminium door company dubai", "best glass handrail company dubai", "best office partition company dubai", "best shower glass partition company dubai",
    "black frame shower cubicle", "black glass handrail", "black glass railing", "black railing with glass",
    "capping balustrade", "channel fixed glass balustrade", "cost of balcony glass panels", "cost of glass partition walls",
    "cost of shower glass partition", "curved glass balcony", "curved glass balustrade", "curved office partitions",
    "custom glass balustrade dubai", "custom glass stair railings", "custom shower cubicle", "decking handrail glass",
    "demountable partitions systems", "desk glass partition", "double glazed office partitions", "exterior glass guardrails",
    "external balustrade", "fixed glass tub panel", "folding office partitions", "frameless balcony glass railing dubai",
    "frameless balustrades", "frameless glass balustrade price dubai", "frameless glass shower cubicle", "frameless office glass partition dubai",
    "frameless shower cubicle", "frameless shower screen dubai", "frameless staircase glass railing dubai", "frosted glass balcony railing",
    "frosted glass fence panels", "frosted glass shower partition", "frosted shower cubicle", "full height glazed partition",
    "garden balustrade glass", "garden glass balustrade", "glass and metal railing", "glass and steel balcony",
    "glass balconies near me", "glass balcony balustrade", "glass balcony handrail", "glass balcony installation",
    "glass balcony railing", "glass balustrade contractor dubai", "glass balustrade door", "glass balustrade fabrication dubai",
    "glass balustrade fitting dubai", "glass balustrade for decking", "glass balustrade in garden", "glass balustrade installation company dubai",
    "glass balustrade on balcony", "glass balustrade railing", "glass balustrade supplier dubai", "glass balustrade with stainless steel posts",
    "glass banister cost", "glass bannister cost", "glass cubicle partitions", "glass cubicles",
    "glass cubicles for office", "glass deck", "glass deck railing", "glass desk partitions",
    "glass door partition in bathroom", "glass for balcony railing", "glass for handrail", "glass for stairs price",
    "glass handrail", "glass handrail balcony", "glass handrail cost", "glass handrail for balcony",
    "glass handrail installation", "glass handrail installation dubai", "glass handrail panels", "glass handrail thickness",
    "glass handrails for stairs", "glass holding channel", "glass office cubicles", "glass office dividers",
    "glass office fronts", "glass office partitions cost", "glass office partitions near me", "glass panel railing",
    "glass parapet", "glass partition between toilet and shower", "glass partition company in dubai", "glass partition company near me",
    "glass partition contractor dubai", "glass partition dubai", "glass partition fabrication dubai", "glass partition fitting dubai",
    "glass partition for office cabin", "glass partition for shower area", "glass partition home office", "glass partition installation company near me",
    "glass partition installation dubai", "glass partition office cost", "glass partition shower area", "glass partition wall bathroom",
    "glass partition walls for offices near me", "glass pool fence top rail", "glass railing around pool", "glass railing balustrade",
    "glass railing black", "glass railing components", "glass railing design for stairs price", "glass railing door",
    "glass railing fabrication dubai", "glass railing for balcony near me", "glass railing for stairs near me", "glass railing for stairs price",
    "glass railing for terrace", "glass railing garden", "glass railing hardware supplier dubai", "glass railing in staircase",
    "glass railing manufacturer dubai", "glass railing on balcony", "glass railing pool", "glass railing rooftop",
    "glass railing stairs outdoor", "glass railing stairs price", "glass railing supplier dubai", "glass railing terrace",
    "glass railings for staircase", "glass ramp railing", "glass shower door partition", "glass shower enclosure cost dubai",
    "glass shower partition installers near me", "glass stair banister", "glass stair handrail", "glass stair railing",
    "glass stair railing cost", "glass stair railing installation", "glass stair railing near me", "glass stair railing price",
    "glass staircase installation", "glass staircase installation near me", "glass staircase price", "glass staircase railing contractor dubai",
    "glass staircase railing cost", "glass staircase railing installation near me", "glass stairs cost", "glass steel staircase",
    "glass terrace railing", "glass toilet cubicle", "glass with wood railing", "glass wood staircase",
    "glass wood staircase railing", "glazed railing", "glazing balustrade", "glazing rail",
    "grey tinted glass balustrade", "half wall partition glass bathroom", "handrail on glass", "handrail with glass",
    "handrail with glass panels", "home office glass partition", "install shower cabin", "interior glass office partitions",
    "interior glass partitions", "internal balustrade", "juliet balcony glass balustrade", "juliet balcony glass railing",
    "juliette balustrade", "led glass balustrade", "led glass railing", "metal and glass balcony",
    "metal and glass railing", "metal glass railing", "metal railing with glass", "modern glass railing stairs",
    "modern glass stairs", "modern shower cabins", "modern stairs with glass railing", "motorized pergola dubai",
    "oak and glass banister", "oak banister with glass", "oak glass banister", "oak glass handrail",
    "oak handrail for glass", "oak handrail with glass", "office aluminium glass partition", "office cabin glass partition",
    "office cabin glass partition price", "office glass partition dubai", "office glass partition installation dubai", "office glass partition price per sqft dubai",
    "office partition dubai", "office partition supplier dubai", "office room glass partition wall", "office wall partition",
    "outdoor aluminium pergola design dubai", "outdoor balcony glass railing", "outdoor glass balcony", "outdoor glass railing installation dubai",
    "ozone shower partition", "pergola contractor dubai", "pergola supplier near me dubai", "pool glass fencing dubai",
    "pool glass railing", "portable office wall dividers", "portable office wall partitions", "railing for glass panels",
    "railing glass balcony", "ready made office partitions", "ready shower cabin", "rooftop glass railing",
    "rooftop glass railing installation dubai", "safety balustrade", "same day glass partition service", "seamless glass deck railing",
    "shower area glass partition", "shower cabin black frame", "shower cabin enclosure", "shower cabin supplier dubai",
    "shower cubicle black frame", "shower cubicle enclosure", "shower cubicle glass door", "shower glass partition cost",
    "shower glass partition dubai", "shower glass partition dubai price", "shower glass partition fitting dubai", "shower glass partition in dubai",
    "shower glass partition installation", "shower glass partition near me", "shower partition", "shower partition near me",
    "single glazed partitioning", "sliding shower cubicle", "soundproof glass partition dubai office", "spigot glass railing supplier dubai",
    "spigot railing system", "ss and glass railing", "ss railing with glass", "ss with glass railing",
    "stainless and glass balustrade", "stainless glass balustrade", "stainless steel and glass balustrade", "stainless steel glass balustrade",
    "stainless steel glass handrail dubai", "stair glass handrail", "stair glass handrail design", "stair glass railing price",
    "stair steel railing design with glass", "staircase glass handrail", "staircase glass handrail dubai", "staircase glass railing",
    "staircase glass railing company dubai", "staircase glass railing price dubai", "staircase glass railing supplier dubai", "staircase railing wood and glass",
    "staircase railings with glass", "staircase steel with glass", "staircase toughened glass", "staircase with wood and glass",
    "staircase wood & glass railing", "staircase wood and glass", "staircase wood glass", "steel and glass staircase",
    "steel glass balcony", "steel glass staircase", "structural glass railing dubai", "tempered glass balustrade",
    "tempered glass bathroom partition", "terrace glass railing", "terrace glass railing dubai", "terrace with glass railing",
    "toilet glass partition price", "toughened glass for balcony", "toughened glass for balcony price", "toughened glass for bathroom partition",
    "toughened glass for railing price", "toughened glass partition in bathroom", "toughened glass railing price", "urgent glass repair dubai",
    "vertical flat bar balustrade", "villa balcony glass railing dubai", "washroom glass partition dubai", "wood and glass balcony",
    "wood and glass railing", "wood and glass staircase", "wood and glass staircase railing", "wood glass railing",
    "wood glass staircase railing", "wood indoor glass railing"
  ];

  var PRODUCTS = [
    "aluco panel", "aluminium", "aluminum", "balcony", "balustrade", "balustrades",
    "banister", "bathroom", "black", "cabin", "cost", "cubicle",
    "cubicles", "curved", "deck", "door", "doors", "dorma fittings",
    "enclosure", "fabrication", "fitting", "frame", "frameless", "frosted",
    "garden", "geze door closer", "glass", "glazed", "guardian glass", "hafele fittings",
    "handrail", "interior", "kingspan", "metal", "modern", "office",
    "outdoor", "panels", "partition", "partitions", "pergola", "pool",
    "price", "railing", "railings", "rooftop", "saint gobain glass", "shower",
    "stainless", "stair", "staircase", "stairs", "steel", "supplier",
    "terrace", "toilet", "toughened", "wall", "wood"
  ];

  var ACTIONS = [
    "24 hour", "24/7", "24hr", "amc", "bespoke", "book",
    "booking", "build", "builder", "builders", "call", "certified",
    "change", "changing", "check", "clean", "cleaner", "cleaning",
    "companies", "company", "contact", "contract", "contractor", "custom",
    "customize", "deep cleaning", "design", "designer", "diagnose", "emergency",
    "expert", "fabricate", "fast", "fix", "fixed", "fixes",
    "fixing", "help", "hire", "in my area", "inspect", "inspection",
    "install", "installation", "installing", "installs", "licensed", "local",
    "made to measure", "made to order", "maintain", "maintenance", "maker", "makers",
    "making", "measure", "near me", "nearby", "now", "number",
    "professional", "quick", "quotation", "quote", "quotes", "relocate",
    "relocation", "removal", "remove", "renovate", "repair", "repairing",
    "repairs", "replace", "replacement", "replacing", "same day", "service",
    "services", "servicing", "solution", "specialist", "supply", "tailor made",
    "technician", "today", "trusted", "upgrade", "urgent", "wash",
    "washing", "whatsapp"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "build", "builder", "clean", "cleaning",
    "custom", "customize", "design", "designer", "detect", "detection",
    "fabricate", "fabrication", "fitted", "fix", "fixed", "fixes",
    "fixing", "inspect", "inspection", "install", "installation", "installing",
    "installs", "made to measure", "made to order", "maintain", "maintenance", "maker",
    "making", "measure", "mount", "mounting", "quote", "refurbish",
    "remodel", "remodeling", "renovate", "renovation", "repair", "repairing",
    "repairs", "replace", "replacement", "replacing", "restoration", "restore",
    "service", "services", "servicing", "supply", "tailor made", "unblock",
    "unclog", "upgrade", "wash", "washing"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "aluminium door lock broken", "aluminium door not closing", "aluminium door stuck", "aluminium pergola leaking",
    "bathroom glass partition leaking water", "blockage", "blocked", "broke",
    "broken", "broken glass railing fix", "burst", "clogged",
    "corroded", "crack", "cracked", "damage",
    "damaged", "dripping", "fault", "faulty",
    "glass balustrade repair", "glass door hinge broken", "glass handrail wobbly", "glass partition broken",
    "glass partition crack repair", "glass partition hinge loose", "glass partition installation quote", "glass railing loose",
    "glass replacement needed", "issue", "issues", "jammed",
    "kharab", "leakage", "leaking", "leaky",
    "low pressure", "need glass partition urgently", "noise", "noisy",
    "not turning on", "not working", "office partition damaged", "overflow",
    "overflowing", "overheating", "problem", "problems",
    "rusted", "short circuit", "shower cabin water leakage", "shower door glass fell",
    "shower door not closing", "shower glass leaking", "shower glass partition repair", "shower glass seal broken",
    "slow", "smell", "smells", "smelly",
    "stopped working", "stuck", "tripping", "vibrating",
    "weak", "won't work", "wont turn", "wont work"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "balcony", "balustrade", "office", "partition", "railing", "shower"
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
