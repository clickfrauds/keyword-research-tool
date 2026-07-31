/**
 * 🛡️ NEGATIVE GUARD v2 — خدمات صيانة الأجهزة دبي (Dubai, United Arab Emirates)
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
    "صيانة الغسالات والثلاجات - الخدمات الأساسية"
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
    "jeddah", "kuwait", "muscat", "ras al khaimah", "riyadh", "sharjah",
    "umm al quwain", "أبوظبي", "ابوظبي", "البحرين", "الدوحة", "الرياض",
    "الشارقة", "العين", "الفجيرة", "الكويت", "ام القيوين", "جدة",
    "رأس الخيمة", "شارجة", "عجمان", "مسقط"
  ];

  var EDU_CAREER = [
    "academy", "apprenticeship", "business kaise", "career",
    "careers", "catalogue", "certificate", "certification",
    "compressor types fridge", "course", "courses", "cv",
    "datasheet", "define", "definition", "diagram",
    "diploma", "dukan kaise", "fridge compressor types", "hiring",
    "how do", "how does", "how much does a technician earn", "how to become",
    "in hindi", "in urdu", "institute", "internship",
    "interview questions", "items list", "job", "jobs",
    "ka kaam", "ka kam", "kaise bane", "kaise khole",
    "kaise seekhe", "kaise sikhe", "kitne prakar", "kitne type",
    "kitni salary", "kya hai", "kya hota hai", "material list",
    "meaning in", "meaning of", "mechanism of", "name list",
    "recruitment", "resume", "salaries", "salary",
    "schematic", "shop kaise", "size chart", "standard height",
    "tool name", "tools list", "tools name", "training",
    "translate", "types of", "types of washing machine errors", "vacancies",
    "vacancy", "wage", "wages", "washing machine belt size",
    "washing machine motor specs", "washing machine repair course dubai", "what happens", "what is",
    "اسعار كورسات صيانة", "انواع اعطال الثلاجة", "انواع اعطال الغسالة", "تعلم صيانة الثلاجات",
    "تعلم صيانة الغسالات", "دبلوم صيانة أجهزة كهربائية", "دورة صيانة ثلاجات", "دورة صيانة غسالات",
    "دورة صيانة نشافات", "راتب فني صيانة غسالات", "شهادة فني صيانة", "كيف تصبح فني صيانة",
    "معهد صيانة أجهزة منزلية", "مقاس حزام الغسالة"
  ];

  var INFO_DIY = [
    "difference between", "diy", "do it yourself", "error code fridge",
    "error code washing machine", "fridge making noise", "ghar par kaise", "how to",
    "how to clean washing machine filter", "instructions", "khud banana", "khud lagana",
    "khud se", "ki setting", "manual", "reset fridge",
    "reset washing machine", "tutorial", "washing machine e01 error", "washing machine manual",
    "washing machine not spinning", "washing machine settings", "what causes", "why is my fridge not cooling",
    "wikipedia", "youtube", "اعادة ضبط الغسالة", "اعدادات الغسالة",
    "دليل استخدام الغسالة", "طريقة تفكيك الغسالة", "طريقة تنظيف الغسالة", "كود خطأ غسالة",
    "لماذا الثلاجة لا تبرد", "لماذا الغسالة لا تعصر"
  ];

  var FORBIDDEN_WORDS = [
    "amazon", "buy washing machine", "carpenter", "carrefour", "distributor", "electrician",
    "export", "franchise", "fridge for sale", "import", "ka dam", "ka price",
    "khareedna", "kharidna", "ki qeemat", "kitna hai", "kitne ka", "lulu",
    "manufacturer", "noon", "painter", "plumber", "rent appliance", "sasta",
    "sharaf dg", "spare parts", "training course", "used washing machine", "washing machine for sale", "wholesale",
    "استثمار", "استيراد", "امازون", "امتياز", "بيع بالجملة", "تأجير أجهزة",
    "تركيب مكيفات", "تصدير", "تصليح جوال", "تصليح موبايل", "تعليم صيانة", "توزيع",
    "توظيف", "توكيل", "ثلاجة للبيع", "جملة", "دهان", "دورة تدريبية",
    "راتب", "رواتب", "سباك", "سبير بارت", "سبيرات", "سعر غسالة جديدة",
    "شارب", "شراء غسالة", "شرف دي جي", "شركة توزيع", "صيانة سيارات", "صيانة كمبيوتر",
    "صيانة مكيفات", "غسالة للبيع", "قطع غيار", "قطع غيار ثلاجات", "قطع غيار غسالات", "كارفور",
    "كهربائي", "كورس", "لولو", "مصنع", "مصنع غسالات", "مطلوب فني",
    "معهد", "نجار", "نون", "وظائف", "وظيفة", "وكيل"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "compressor", "fridge", "washing machine", "بطارية", "ثلاجة", "غسالة",
    "مروحة", "موتور", "نشافة"
  ];

  var SAFE_ROOTS = [
    "emergency appliance repair dubai", "same day appliance repair dubai", "أفضل شركة صيانة غسالات دبي", "أفضل فني نشافات دبي",
    "إصلاح الثلاجات", "إصلاح ثقب في فريزر الثلاجة", "اصلاح الثلاجة", "اصلاح الغسالة",
    "اصلاح تايمر الغسالة العادية", "اصلاح تايمر الغسالة العادية فريش", "اصلاح ثلاجة", "اصلاح ثلاجة توشيبا",
    "اصلاح غسالات", "اصلاح غسالة lg", "اصلاح غسالة الملابس", "اصلاح غسالة صحون",
    "اصلاح كارتة الغسالة الفول اتوماتيك", "اصلاح نشافة الغسالة العادية", "افضل صيانة ثلاجات دبي", "افضل صيانة غسالات دبي",
    "تصليح اجهزة منزلية دبي", "تصليح الثلاجه", "تصليح الغسالة", "تصليح الغسالة الفوق اتوماتيك",
    "تصليح باب الغساله", "تصليح باب ثلاجة", "تصليح براد", "تصليح تايمر ثلاجة توشيبا",
    "تصليح ثلاجة", "تصليح ثلاجة اليوم دبي", "تصليح ثلاجة بيكو", "تصليح ثلاجة سامسونج دبي",
    "تصليح ثلاجة لا تبرد دبي", "تصليح جلايات الصحون", "تصليح جلايه", "تصليح غسالات اتوماتيك بيكو",
    "تصليح غسالات اتوماتيك زانوسى", "تصليح غسالات اتوماتيك سامسونج", "تصليح غسالات ال جي", "تصليح غسالات حوضين",
    "تصليح غسالات دايو", "تصليح غسالات سامسونج", "تصليح غسالة", "تصليح غسالة اتوماتيك",
    "تصليح غسالة اتوماتيك lg", "تصليح غسالة ال جي اتوماتيك", "تصليح غسالة الصحون ال جي", "تصليح غسالة اليوم دبي",
    "تصليح غسالة بوش", "تصليح غسالة سامسونج 7 كيلو", "تصليح غسالة صحون", "تصليح غسالة صحون اريستون",
    "تصليح غسالة صحون بوش دبي", "تصليح غسالة صحون في نفس اليوم", "تصليح غسالة كوندور", "تصليح غسالة ويرلبول",
    "تصليح فريزر الثلاجة", "تصليح كارتة الغسالة الاتوماتيك", "تصليح كمبروسر الثلاجه", "تصليح كمبروسر ثلاجة",
    "تصليح لوك الغسالة الاتوماتيك", "تصليح مروحة الغسالة العادية", "تصليح مفتاح الغسالة الاتوماتيك", "تصليح نشافة",
    "تصليح نشافة الغسالة العادية", "تصليح نشافة اليوم دبي", "تصليح نشافة لا تجفف دبي", "تصليح نشافة ملابس",
    "تكلفة تصليح غسالة دبي", "خدمة صيانة منزلية دبي", "رقم صيانة اجهزة منزلية", "رقم فني ثلاجات دبي",
    "رقم فني جلايات صحون دبي", "رقم فني غسالات دبي", "سعر تصليح ثلاجة دبي", "سعر تصليح غسالة صحون دبي",
    "سعر تصليح غسالة في دبي", "سعر تصليح نشافة ملابس دبي", "صيانة اجهزة كهربائية دبي", "صيانة الثلاجات توشيبا",
    "صيانة الغسالات الفوق اتوماتيك", "صيانة الغسالة الاتوماتيك", "صيانة ثلاجات منزلية دبي", "صيانة طوارئ",
    "صيانة عاجلة", "صيانة غسالات بالمنزل دبي", "صيانة غسالات منزلية دبي", "صيانة غسالة صحون دبي",
    "صيانة غسالة صحون منزلية دبي", "صيانة نشافة ملابس منزلية دبي", "فني تصليح غسالة اتوماتيك دبي", "فني تصليح غسالة صحون",
    "فني ثلاجات دبي", "فني صيانة اجهزة منزلية دبي", "فني صيانة منازل", "فني غسالة صحون دبي",
    "فني نشافات دبي", "مصلح غسالة"
  ];

  var PRODUCTS = [
    "bosch", "daewoo", "electrolux", "haier", "kenwood", "lg",
    "midea", "samsung", "toshiba", "whirlpool", "اتوماتيك", "اصلاح",
    "الاتوماتيك", "الثلاجة", "العادية", "الغسالة", "اليكترولوكس", "اليوم",
    "بوش", "تايمر", "تصليح", "توشيبا", "ثلاجات", "ثلاجة",
    "دايو", "سامسونج", "صحون", "صيانة", "غسالات", "غسالة",
    "كينوود", "ملابس", "منزلية", "ميديا", "نشافة", "هاير",
    "ويرلبول"
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
    "tailor made", "technician", "today", "trusted", "urgent", "wash",
    "washing", "whatsapp", "اصلاح", "تركيب", "تصليح", "صيانة",
    "فحص"
  ];

  // Strong service VERBS only — the context-word rule needs a real job
  // signal ("installation"/"repair"), not a location/trust word ("near me")
  var STRONG_ACTIONS = [
    "amc", "bespoke", "build", "builder", "clean", "cleaning",
    "custom", "design", "designer", "detect", "detection", "fabrication",
    "fitted", "fix", "fixed", "fixes", "fixing", "inspect",
    "inspection", "install", "installation", "installing", "installs", "made to measure",
    "made to order", "maintain", "maintenance", "maker", "making", "mount",
    "mounting", "refurbish", "remodel", "remodeling", "renovate", "renovation",
    "repair", "repairing", "repairs", "replace", "replacement", "replacing",
    "restoration", "restore", "service", "services", "servicing", "tailor made",
    "unblock", "unclog", "wash", "washing", "اصلاح", "تركيب",
    "تصليح", "صيانة", "فحص"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "blockage", "blocked", "broke", "broken",
    "burst", "clogged", "corroded", "crack",
    "cracked", "damage", "damaged", "dishwasher not working",
    "dripping", "dryer not drying", "fault", "faulty",
    "fridge compressor not working", "fridge leaking water", "fridge not cooling", "issue",
    "issues", "jammed", "kharab", "leakage",
    "leaking", "leaky", "low pressure", "noise",
    "noisy", "not turning on", "not working", "overflow",
    "overflowing", "overheating", "problem", "problems",
    "rusted", "short circuit", "slow", "smell",
    "smells", "smelly", "stopped working", "stuck",
    "tripping", "vibrating", "washing machine door not closing", "washing machine e01",
    "washing machine e02", "washing machine leaking water", "washing machine making noise", "washing machine not draining",
    "washing machine stopped suddenly", "weak", "won't work", "wont turn",
    "wont work", "الثلاجة تسرب ماء", "الثلاجة لا تبرد", "الغسالة تسرب ماء",
    "الغسالة توقفت فجأة", "الغسالة لا تصرف الماء", "الغسالة لا تعصر", "الغسالة لا تعمل",
    "النشافة لا تجفف", "النشافة لا تدور", "غسالة باب لا يقفل", "غسالة تصدر صوت",
    "غسالة صحون تسرب ماء", "غسالة صحون لا تعمل"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "اتوماتيك", "الاتوماتيك", "العادية", "الغسالة", "سامسونج", "غسالات"
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
