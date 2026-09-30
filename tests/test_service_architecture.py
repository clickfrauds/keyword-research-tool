"""Stage 2.7 (service_architecture.py) + its Google Ads twin (the silo router).

Offline. Runs Stage 2.7 on the real Planner rows of the 28-Sep-2026 Dubai
appliance runs, then holds the JS router to 100% agreement with Python on
every one of those rows plus hand-written EN/AR edge cases.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "dubai_appliance_sep2026.json")
sys.path.insert(0, SCRIPTS)

SEEDS = ("Washing machine repair, Dryer repair, Dishwasher repair, Refrigerator repair, "
         "Fridge repair, Wine chiller repair, LED TV repair, تصليح غسالات, تصليح ثلاجات")

# Arabic rows the English runs never had, so the Arabic services get groups.
ARABIC_ROWS = [("تصليح غسالات دبي", 880), ("تصليح غسالات", 720), ("صيانة غسالات", 390),
               ("تصليح غسالة سامسونج", 170), ("تصليح غسالات ال جي", 140),
               ("فني غسالات قريب مني", 90), ("تصليح ثلاجات دبي", 590), ("تصليح ثلاجات", 480),
               ("صيانة ثلاجات", 260), ("تصليح ثلاجة سامسونج", 110), ("فني ثلاجات", 70),
               ("ثلاجة لا تبرد", 320), ("تصليح ثلاجة لا تبرد", 90), ("غسالة لا تعصر", 210)]

EDGE_CASES = [
    # the GPT-review bugs
    "electrical wiring repair", "carpenter reviews", "manual gearbox repair",
    "fridge board repair", "fridge repair today", "fridge repair near me",
    # modifiers are not a layer; emergency is (only when 24/7)
    "emergency fridge repair", "24 hour washing machine repair", "24/7 dryer repair",
    "fridge repair open now", "who can fix my washing machine", "repair my fridge",
    "washing machine repair at home", "same day dishwasher repair dubai",
    # brand beats problem
    "samsung washing machine not spinning repair", "lg fridge compressor repair",
    "fisher paykel dishwasher repair", "general electric fridge repair", "super general fridge repair",
    # symptoms / faults / codes
    "fridge not cooling", "washing machine not spinning", "dishwasher e24",
    "washing machine drum broken", "fridge compressor dead", "fridge leaking repair",
    "washing machine error code e20 repair", "led tv backlight repair", "tv screen cracked",
    # junk
    "washing machine price", "buy fridge dubai", "fridge repair jobs", "washing machine manual",
    "fridge parts", "second hand fridge", "used washing machine", "fridge repair sharjah",
    "how to fix washing machine", "washing machine repair course", "samsung fridge",
    "washing machine reviews", "fridge repair cost", "cheap washing machine repair",
    # typos, glued words, plurals, word order
    "washingmachine repair", "fridgerepair", "refrigirator repair", "washing machne repair",
    "dishwashers repair", "refrigerators repair dubai", "repair washing machines",
    "wine fridge repair", "wine cooler repairs", "washer dryer repair", "dish washer repair",
    "clothes dryer repair near me", "tumble dryer fixing",
    # other trades / no service
    "plumber dubai", "ac repair dubai", "car repair", "", "   ", "repair",
    # Arabic
    "تصليح غسالات قريب مني", "تصليح الغسالات دبي", "صيانة الثلاجات", "فني ثلاجات قريب مني",
    "تصليح ثلاجة سامسونج لا تبرد", "غسالة لا تعمل", "الثلاجة لا تبرد", "سعر غسالة",
    "غسالات مستعملة للبيع", "تصليح غسالات الشارقة", "تصليح غسالات طوارئ", "تصليح غسالات 24 ساعة",
    "كيف اصلح الغسالة", "تصليح غسالة بوش", "ثلاجة مكسورة", "وظائف فني غسالات",
    "تصليح غسالة في المنزل", "شركة تصليح ثلاجات",
]

NODE_HARNESS = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const qs = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const mod = new Function(src + '\nreturn {classify: classify, ownerOf: ownerOf, SERVICES: SERVICES};')();
const out = qs.map(q => {
  const c = mod.classify(q);
  return [c[0] < 0 ? null : mod.SERVICES[c[0]].name, c[1], mod.ownerOf(q)];
});
fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""


def run_stage(workdir, env_extra):
    with open(FIXTURE, encoding="utf-8") as f:
        data = json.load(f)
    rows = data["keywords"]
    for kw, vol in ARABIC_ROWS:
        rows.append({"id": len(rows) + 1, "keyword": kw, "avg_monthly_searches": vol,
                     "competition_index": 20, "low_top_bid": 900.0, "high_top_bid": 2400.0,
                     "intent": "transactional", "kept_for_ai": True})
    with open(os.path.join(workdir, "scored_keywords.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    env = dict(os.environ, SEED_KEYWORDS=SEEDS, TARGET_LOCATION="Dubai, United Arab Emirates",
               NICHE_DESCRIPTION="Home Appliance Repair Services", PYTHONIOENCODING="utf-8",
               **env_extra)
    for k in ("OPEN_24_7", "SYMPTOM_TEST", "DAILY_BUDGET", "AVG_CPC", "SERVICES_JSON"):
        if k not in env_extra:
            env.pop(k, None)
    res = subprocess.run([sys.executable, os.path.join(SCRIPTS, "service_architecture.py")],
                         cwd=workdir, env=env, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        raise AssertionError(res.stdout + res.stderr)
    with open(os.path.join(workdir, "ad_group_plan.json"), encoding="utf-8") as f:
        return json.load(f), [r["keyword"] for r in data["keywords"]]


class Classifier(unittest.TestCase):
    """The rules themselves, on the module's defaults (24/7 off, symptom test on)."""

    @classmethod
    def setUpClass(cls):
        import importlib
        for k in ("OPEN_24_7", "SYMPTOM_TEST", "EXTRA_JUNK", "NEGATIVE_ALLOW"):
            os.environ.pop(k, None)
        os.environ["TARGET_LOCATION"] = "Dubai, United Arab Emirates"
        import service_architecture as vtsa
        cls.v = importlib.reload(vtsa)
        cls.svcs = cls.v.build_services(["fridge repair", "washing machine repair"])
        cls.v._build_normaliser(cls.svcs)

    def layer(self, kw):
        i, layer = self.v.classify(kw, self.svcs)
        return layer

    def test_gpt_review_junk_bugs(self):
        for kw in ("electrical wiring repair", "carpenter reviews", "manual gearbox repair",
                   "plumber dubai", "washing machine parts replacement"):
            self.assertIsNone(self.v.junk_reason(kw), kw)
        for kw in ("washing machine manual", "fridge parts", "washing machine price",
                   "washing machine reviews", "wiring diagram", "fridge repair jobs"):
            self.assertIsNotNone(self.v.junk_reason(kw), kw)

    def test_modifiers_are_not_a_layer(self):
        for kw in ("fridge repair near me", "fridge repair today", "who can fix my fridge",
                   "fridge repair open now", "emergency fridge repair"):
            self.assertEqual(self.layer(kw), "core", kw)

    def test_precedence_brand_over_problem(self):
        self.assertEqual(self.layer("samsung fridge not cooling repair"), "brand")
        self.assertEqual(self.layer("fridge board repair"), "problem")
        self.assertEqual(self.layer("fridge compressor dead"), "problem")

    def test_symptom_only_is_a_test_layer(self):
        self.assertEqual(self.layer("fridge not cooling"), "symptom")
        self.assertEqual(self.layer("fridge not cooling repair"), "problem")

    def test_typo_fix_towards_own_vocabulary(self):
        self.assertEqual(self.v.toks("refrigirator repir machne"),
                         ["refrigerator", "repair", "machine"])
        self.assertEqual(self.v.toks("bridge"), ["bridge"])   # never becomes "fridge"


class Structure(unittest.TestCase):
    def test_real_run_structure(self):
        with tempfile.TemporaryDirectory() as d:
            plan, _ = run_stage(d, {"DAILY_BUDGET": "150000", "OPEN_24_7": "on"})
        names = {g["name"] for g in plan["ad_groups"]}
        services = {g["service"] for g in plan["ad_groups"]}
        # every seed service that has demand gets at least its core group —
        # the old model path merged 7 services into 4 groups and lost LED TV
        for svc in ("Washing Machine", "Dryer", "Dishwasher", "Refrigerator", "Wine Chiller",
                    "LED TV"):
            self.assertIn(svc, services)
        self.assertIn("Washing Machine Repair - Brands", names)
        for g in plan["ad_groups"]:
            self.assertEqual(g["match_type"], "exact" if g["layer"] == "symptom" else "phrase")
            if g["layer"] == "symptom":
                self.assertEqual(g["bid_multiplier"], 0.6)
        self.assertNotIn("fallback_legacy", plan)
        self.assertIn("classifier", plan)

    def test_small_budget_folds_groups(self):
        with tempfile.TemporaryDirectory() as d:
            plan, _ = run_stage(d, {"DAILY_BUDGET": "39960"})
        # 39,960 PKR at ~2,500 CPC is ~16 clicks a day: one group per service
        per = {}
        for g in plan["ad_groups"]:
            per[g["service"]] = per.get(g["service"], 0) + 1
        self.assertLessEqual(len(plan["ad_groups"]), max(len(per), 39960 // 2500 // 3))

    def test_needs_service_map_stops_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(AssertionError) as cm:
                run_stage(d, {"SERVICES_JSON": json.dumps(
                    [{"name": "Wine Chiller", "aliases": ["wine chiller", "wine cooler"]}])})
            self.assertIn("NEEDS_SERVICE_MAP", str(cm.exception))


@unittest.skipUnless(shutil.which("node"), "node not installed")
class RouterParity(unittest.TestCase):
    def check(self, env_extra):
        import importlib
        with tempfile.TemporaryDirectory() as d:
            plan, planner_kws = run_stage(d, env_extra)
            import service_architecture as vtsa
            vtsa = importlib.reload(vtsa)
            vtsa.restore_classifier(plan["classifier"])
            import generate_silo_router as gsr
            gsr = importlib.reload(gsr)
            js, _, _ = gsr.build_js(plan, "Test")
            services = plan["services"]
            groups = {f'{g["service"]}|{g["layer"]}': g["name"] for g in plan["ad_groups"]}
            queries = list(dict.fromkeys(planner_kws + EDGE_CASES))
            self.assertGreaterEqual(len(queries), 200)
            py = []
            for q in queries:
                i, layer = vtsa.classify(q, services)
                py.append([None if i is None else services[i]["name"], layer,
                           vtsa.owner_of(q, services, groups)])
            paths = {n: os.path.join(d, n) for n in ("r.js", "q.json", "h.js", "o.json")}
            with open(paths["r.js"], "w", encoding="utf-8") as f:
                f.write(js)
            with open(paths["q.json"], "w", encoding="utf-8") as f:
                json.dump(queries, f, ensure_ascii=False)
            with open(paths["h.js"], "w", encoding="utf-8") as f:
                f.write(NODE_HARNESS)
            subprocess.run(["node", paths["h.js"], paths["r.js"], paths["q.json"], paths["o.json"]],
                           check=True)
            with open(paths["o.json"], encoding="utf-8") as f:
                js_out = json.load(f)
        diffs = [(q, p, j) for q, p, j in zip(queries, py, js_out) if p != j]
        self.assertEqual(diffs, [], f"{len(diffs)} of {len(queries)} differ, e.g. {diffs[:5]}")
        # the test must exercise every layer, not just core
        layers = {p[1] for p in py}
        self.assertTrue({"brand", "problem", "core", "symptom", None} <= layers, layers)
        return layers

    def test_parity_defaults(self):
        self.check({"DAILY_BUDGET": "39960"})

    def test_parity_open_24_7(self):
        layers = self.check({"DAILY_BUDGET": "150000", "OPEN_24_7": "on"})
        self.assertIn("emergency", layers)


if __name__ == "__main__":
    unittest.main()
