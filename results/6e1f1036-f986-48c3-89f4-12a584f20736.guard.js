/**
 * 🛡️ NEGATIVE GUARD v2 — سباك أكوا دبي (Dubai, United Arab Emirates)
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
    "خدمات السباكة الطارئة وتسليك المجاري - دبي"
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
    "jeddah", "kuwait", "oman", "ras al khaimah", "saudi arabia", "sharjah",
    "umm al quwain", "أبو ظبي", "ابوظبي", "البحرين", "الرياض", "السعودية",
    "الشارقة", "العراق", "العين", "الفجيرة", "الكويت", "ام القيوين",
    "راس الخيمة", "عجمان", "عمان", "قطر"
  ];

  var EDU_CAREER = [
    "academy", "apprenticeship", "business kaise", "career",
    "careers", "catalogue", "certificate", "certification",
    "course", "courses", "cv", "datasheet",
    "define", "definition", "diagram", "diploma",
    "dukan kaise", "hiring", "how do", "how does",
    "how to become", "how to become a plumber", "in hindi", "in urdu",
    "institute", "internship", "interview questions", "items list",
    "job", "jobs", "ka kaam", "ka kam",
    "kaise bane", "kaise khole", "kaise seekhe", "kaise sikhe",
    "kitne prakar", "kitne type", "kitni salary", "kya hai",
    "kya hota hai", "material list", "meaning in", "meaning of",
    "mechanism of", "name list", "pipe size guide", "plumber salary dubai",
    "plumber training uae", "plumbing course dubai", "plumbing tools list", "recruitment",
    "resume", "salaries", "salary", "schematic",
    "shop kaise", "size chart", "standard height", "tool name",
    "tools list", "tools name", "training", "translate",
    "types of", "types of drain pipes", "vacancies", "vacancy",
    "wage", "wages", "water heater types", "what happens",
    "what is", "احتراف السباكة", "اداة تسليك المجاري اسمها", "اساسيات السباكة",
    "اسعار دبلوم سباكة", "اسم جهاز كشف تسريب المياه", "انواع سخانات المياه", "انواع مضخات المياه",
    "انواع مواسير الصرف الصحي", "تعلم السباكة", "دورة سباكة", "راتب سباك في دبي",
    "كورس سباكة", "كيف تصبح سباك", "مقاس خرطوم تسليك المجاري", "مقاسات مواسير الصرف"
  ];

  var INFO_DIY = [
    "difference between", "diy", "diy pipe leak fix", "do it yourself",
    "drain cleaning diy", "ghar par kaise", "how to", "how to unclog drain yourself",
    "instructions", "khud banana", "khud lagana", "khud se",
    "ki setting", "manual", "reset water heater", "tutorial",
    "water heater error code", "water pressure troubleshooting", "what causes", "wikipedia",
    "youtube", "اسباب ضعف ضغط المياه", "اعادة ضبط سخان المياه", "خطوات تسليك الحوض بنفسك",
    "رمز خطأ سخان المياه", "طريقة تسليك المجاري بالمنزل", "كيف تصلح تسريب المياه بنفسك", "كيف تنظف مضخة المياه"
  ];

  var FORBIDDEN_WORDS = [
    "ac repair", "apartment for rent", "apartment for sale", "buy online", "career", "carpenter",
    "distributor", "electrician", "furniture moving", "hiring", "jobs", "ka dam",
    "ka price", "khareedna", "kharidna", "ki qeemat", "kitna hai", "kitne ka",
    "manufacturer", "painter", "pest control", "real estate", "salary", "sasta",
    "second hand", "spare parts", "training course", "used pump for sale", "wholesale", "اشتري",
    "الوميتال", "بلاط", "بيع", "تأجير شقق", "تخفيض", "تدريب",
    "تسريب غاز", "تصميم ديكور", "تكييف", "تنظيف منازل", "توزيع", "توظيف",
    "جملة", "دهان", "دورات", "دورة", "راتب", "رخام",
    "زجاج", "سعر الجملة", "شراء", "شقق للبيع", "صيانة سيارات", "عقار",
    "قطع غيار", "قطع غيار سباكة", "كهربائي", "كورس", "للبيع", "مرتب",
    "مستعمل", "مصنع", "مقاول عام", "مكافحة حشرات", "مكيفات", "موزع",
    "نجار", "نقل عفش", "وظائف", "وظيفة", "وكيل"
  ];

  // Ambiguous words: product-shopping UNLESS a service signal appears too
  var CONTEXT_WORDS = [
    "بالوعة", "حوض", "خرطوم", "خزان", "سخان", "صنبور",
    "فلتر", "مضخة", "مواسير"
  ];

  var SAFE_ROOTS = [
    "24 hour plumber dubai", "best plumber dubai", "drain cleaning dubai", "emergency plumber dubai",
    "plumber near me dubai", "pump maintenance dubai", "water heater repair dubai", "احتاج سباك",
    "اسعار السباكة في دبي", "اسعار تسليك المجاري", "اسعار تسليك المجاري في دبي", "اسعار تصليح سخان الماء",
    "اسعار شفط الصرف الصحي دبي", "اصلاح سخانات الماء", "اصلاح مضخة الماء", "افضل سباك دبي",
    "افضل سباك في دبي", "افضل شركة تسليك مجاري دبي", "اقرب سباك", "اقوى مسلك بواليع",
    "البالوعات افضل مسلك مجاري", "انسداد الصرف الصحي", "انسداد المجاري في المطبخ", "انسداد بالوعة الحمام",
    "انسداد مواسير الصرف الصحي", "بلمبر", "بلومبير", "تركيب سخان مياه دبي",
    "تركيب مضخة مياه دبي", "تسليك البانيو", "تسليك بالوعات", "تسليك بالوعة",
    "تسليك بالوعة المطبخ الارضية", "تسليك بلاعات المطبخ", "تسليك بلاليع", "تسليك مجاري",
    "تسليك مجاري الصرف الصحي", "تسليك مجاري المطبخ", "تسليك مجاري بالضغط دبي", "تسليك مجاري بدون حفر دبي",
    "تسليك مجاري دبي رخيص", "تسليك مجاري طارئ", "تسليك مجاري طوارئ دبي", "تسليك مغسلة المطبخ",
    "تسليك مواسير", "تسليك مواسير الصرف", "تسليك مواسير الصرف الصحي", "تصليح تسريب مياه دبي",
    "تصليح مضخة مياه دبي", "تكلفة تصليح تسريب المياه", "تكلفة سباكة الحمام", "تنظيف البالوعات من الروائح",
    "تنظيف الصرف الصحي", "تنظيف المجاري", "تنظيف المجاري المسدودة", "تنظيف المجاري المنزلية",
    "تنظيف المجاري من الروائح", "تنظيف انابيب الصرف الصحي", "تنظيف بالوعات الصرف الصحي", "تنظيف صرف صحي دبي",
    "تنظيف مجاري", "تنظيف مجاري الحمام", "تنظيف مجاري الحمامات", "تنظيف مجاري الصرف الصحي",
    "تنظيف مجاري المطبخ", "تنظيف مجاري المنزل", "تنظيف مواسير الصرف", "تنكر سحب مجاري",
    "تنكر سحب مياه المجاري", "تنكر شفط مجاري", "تنكر شفط مجاري دبي", "خدمة سباك سريع دبي",
    "خدمة سباكة منزلية دبي", "خدمة شفط بيارات منازل دبي", "رقم تنكر شفط دبي", "رقم سباك",
    "رقم سباك في دبي", "رقم شركة تسليك مجاري دبي", "رقم شفط مجاري", "سباك",
    "سباك 24 ساعة", "سباك 24 ساعة دبي", "سباك بالساعة دبي", "سباك بالقرب مني",
    "سباك جميع مناطق دبي", "سباك حمام", "سباك حمامات", "سباك دبي رخيص",
    "سباك شاطر", "سباك صحي", "سباك طارئ دبي", "سباك طوارئ دبي",
    "سباك قريب مني دبي", "سباك كهرباء", "سباك مجاري", "سباك ممتاز",
    "سباك منازل دبي 24 ساعة", "سباكه الحمام", "سحب صرف صحي دبي", "سيارة تسليك المجاري",
    "سيارة سحب المجاري", "شركات سحب المجاري", "شركة انسداد المجاري", "شركة تسليك مجاري",
    "شركة تسليك مجاري في دبي", "شركة تنظيف الصرف الصحي", "شركة تنظيف المجاري", "شركة تنظيف خزانات صرف صحي دبي",
    "شركة سباكة", "شركة شفط بيارات دبي", "شركة فتح المجاري", "شركة لفتح المجاري",
    "شفط بواليع", "شفط مجاري", "صيانة المجاري", "صيانة سخانات دبي",
    "صيانة سخانات مياه دبي", "صيانة مضخات منازل دبي", "صيانة مضخات مياه دبي", "عامل سباك",
    "عايز سباك", "فتح المواسير المسدودة", "فتح مجاري الصرف الصحي", "فتح مجاري المطبخ",
    "فني صيانة سخانات دبي", "فني مضخات مياه دبي طوارئ", "لتسليك مواسير الصرف", "لفتح المجاري",
    "ماسورة مجاري", "مسلك بواليع", "معالجة انسداد المجاري", "مواسير مجاري"
  ];

  var PRODUCTS = [
    "اسعار", "افضل", "الحمام", "الصحي", "الصرف", "الماء",
    "المجاري", "المطبخ", "انسداد", "بالوعة", "بواليع", "تسليك",
    "تصليح", "تنظيف", "تنكر", "سباك", "سخانات", "شركة",
    "صيانة", "طوارئ", "مجاري", "مسلك", "مضخة", "منازل",
    "مواسير", "مياه"
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
    "washing", "whatsapp", "استبدال", "تركيب", "تصليح", "تنظيف",
    "تنكر شفط", "صيانة", "فحص", "فك وتركيب", "كشف تسرب", "معالجة انسداد"
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
    "unblock", "unclog", "wash", "washing", "استبدال", "تركيب",
    "تصليح", "تنظيف", "تنكر شفط", "صيانة", "فحص", "فك وتركيب",
    "كشف تسرب", "معالجة انسداد"
  ];

  // Problem-state phrases = service intent ("toilet not flushing")
  var PROBLEMS = [
    "blockage", "blocked", "broke", "broken",
    "burst", "clogged", "corroded", "crack",
    "cracked", "damage", "damaged", "dripping",
    "fault", "faulty", "issue", "issues",
    "jammed", "kharab", "leakage", "leaking",
    "leaky", "low pressure", "noise", "noisy",
    "not turning on", "not working", "overflow", "overflowing",
    "overheating", "problem", "problems", "rusted",
    "short circuit", "slow", "smell", "smells",
    "smelly", "stopped working", "stuck", "tripping",
    "vibrating", "weak", "won't work", "wont turn",
    "wont work", "الحمام مسدود", "الحوض مسدود", "السباكة معطلة",
    "السخان لا يعمل", "الصرف مسدود", "المجاري مسدودة", "المرحاض مسدود",
    "المضخة لا تعمل", "المياه لا تنزل", "انسداد المجاري", "تسرب من الصنبور",
    "تسرب مياه من الجدار", "تسريب من السخان", "تسريب مياه", "تسريب مياه تحت الحوض",
    "رائحة كريهة من الصرف", "صوت غريب من المضخة", "ضعف ضغط المياه", "لا يوجد ماء ساخن",
    "ماء يتسرب من السقف"
  ];

  // Head service tokens — 1-edit misspellings of these are KEPT as leads
  var FUZZY_ROOTS = [
    "الحمام", "المجاري", "المطبخ", "انسداد", "سخانات", "مواسير"
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
