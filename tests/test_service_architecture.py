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
               GEO_LOOKUP="off", **env_extra)
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
        os.environ["NICHE_DESCRIPTION"] = "Home Appliance Repair Services"
        import service_architecture as vtsa
        cls.v = importlib.reload(vtsa)
        cls.svcs = cls.v.build_services(["fridge repair", "washing machine repair"])
        cls.v._build_normaliser(cls.svcs)
        cls.v.register_other_services(cls.svcs)

    def test_run_2476776a_junk(self):
        # all of these were BID on in the 1 Oct 2026 run
        for kw in ("urbanclap washing machine repair", "dyson hair dryer repair",
                   "dryer vent repair near me",
                   "commercial washing machine repair", "industrial washing machine repair",
                   "تصليح ثلاجات السيارات"):
            self.assertIsNotNone(self.v.junk_reason(kw), kw)
        # "refrigeration" is a real word, never corrected to "refrigerator" —
        # so this one matches no service at all (it is not a fridge query)
        self.assertEqual(self.v.toks("refrigeration"), ["refrigeration"])
        self.assertIsNone(self.v.assign_service("air conditioning and refrigeration services",
                                                self.svcs))
        for kw in ("washing machine repair", "fridge repair near me", "تصليح ثلاجات",
                   # buyers run 0d732cac excluded and negated (Naseem, 1 Oct)
                   "fridge electrician near me", "electrician for fridge repair near me",
                   "32 inch led tv backlight repair cost", "8 kg washing machine repair"):
            self.assertIsNone(self.v.junk_reason(kw), kw)
        # a bare size is still shopping
        self.assertIsNotNone(self.v.junk_reason("8 kg washing machine"))

    def test_exclusions_follow_the_niche_not_the_code(self):
        import negative_packs as np
        app = np.exclusions("Home appliance repair", ["washing machine repair"])
        plumb = np.exclusions("Residential plumbing company", ["plumber"])
        self.assertIn("hair dryer", app)
        self.assertNotIn("hair dryer", plumb)
        for agg in ("urban company", "thumbtack", "checkatrade"):
            self.assertIn(agg, app)
            self.assertIn(agg, plumb)

    def test_other_trades_are_per_plan(self):
        v = self.v
        # default: naming another trade next to OUR product is still our job
        self.assertEqual(v.OTHER_SERVICE_PHRASES, [])
        self.assertIsNone(v.junk_reason("washing machine plumber"))
        self.assertIsNone(v.junk_reason("ac fridge repair"))
        self.assertIsNone(v.junk_reason("washing machine electrical fault repair"))
        # opt-in: OTHER_TRADE_JUNK=on, and a trade the plan names is never junk
        saved = dict(os.environ)
        try:
            os.environ["OTHER_TRADE_JUNK"] = "on"
            v.register_other_services(self.svcs)
            self.assertIsNotNone(v.junk_reason("washing machine plumber"))
            os.environ["NICHE_DESCRIPTION"] = "Plumbing company"
            os.environ["SEED_KEYWORDS"] = "drain unblocking, leak detection"
            svcs = v.build_services(["drain unblocking", "leak detection"])
            v.register_other_services(svcs)
            self.assertFalse(any("plumber" in p for p in v.OTHER_SERVICE_PHRASES))
            self.assertTrue(any("electrician" in p for p in v.OTHER_SERVICE_PHRASES))
        finally:
            os.environ.clear(); os.environ.update(saved)
            v.register_other_services(self.svcs)

    def test_cannibalization_one_owner_per_query(self):
        groups = [
            {"name": "Dryer", "language": "en", "match_type": "phrase",
             "keywords": ["dryer repair"], "negatives": []},
            {"name": "Washer", "language": "en", "match_type": "phrase",
             "keywords": ["washing machine repair", "washer dryer repair"], "negatives": []},
            {"name": "Washer AR", "language": "ar", "match_type": "phrase",
             "keywords": ["تصليح غسالات"], "negatives": []},
        ]
        added, unresolved = self.v.resolve_cannibalization(groups)
        # "dryer repair" reaches "washer dryer repair": the specific group owns it
        self.assertEqual(groups[0]["negatives"], ["washer dryer repair"])
        self.assertEqual(groups[1]["negatives"], [])
        self.assertEqual(unresolved, [])
        # running again adds nothing (already negated)
        self.assertEqual(self.v.resolve_cannibalization(groups)[0], [])

    def test_geo_context_any_country(self):
        import generate_locations as gl
        geo = [{"id": 1, "n": "Dubai", "c": "Dubai,United Arab Emirates", "t": "Province"},
               {"id": 2, "n": "Dubai", "c": "Dubai,Dubai,United Arab Emirates", "t": "City"},
               {"id": 3, "n": "Dubai Marina", "c": "Dubai Marina,Dubai,United Arab Emirates",
                "t": "Neighborhood"},
               {"id": 4, "n": "Sharjah", "c": "Sharjah,United Arab Emirates", "t": "Province"},
               {"id": 5, "n": "Al Nahda", "c": "Al Nahda,Sharjah,United Arab Emirates",
                "t": "Neighborhood"}]
        index = [{"name": "United Arab Emirates", "cc": "AE"}]
        old = (gl.fetch_json, self.v.TARGET_LOCATION, os.environ.get("GEO_LOOKUP"))
        try:
            gl.fetch_json = lambda url: index if url.endswith("index.json") else geo
            self.v.TARGET_LOCATION = "dubai, united arab emirates"
            os.environ["GEO_LOOKUP"] = "on"
            areas, wrong = self.v.geo_context()
        finally:
            gl.fetch_json, self.v.TARGET_LOCATION = old[0], old[1]
            if old[2] is None:
                os.environ.pop("GEO_LOOKUP", None)
            else:
                os.environ["GEO_LOOKUP"] = old[2]
        self.assertIn("dubai marina", areas)
        self.assertNotIn("al nahda", areas)          # another emirate's area
        self.assertEqual(wrong, ["sharjah"])

    def test_bid_selection(self):
        rows = [{"id": i, "keyword": k, "avg_monthly_searches": v} for i, (k, v) in enumerate([
            ("washing machine repair", 6600), ("washing machine repair near me", 880),
            ("samsung washing machine repair", 90), ("washing machines repair dubai", 10),
            ("fix washing machine", 6600), ("washer fixer", 6600), ("washer repair", 30),
            ("lg washer repair", 10), ("washing machine drum repair", 10)])]
        chosen, _ = self.v.select_bid_rows(rows)
        kws = [r["keyword"] for r in chosen]
        # reached by "washing machine repair" (phrase, plural folded)
        for k in ("washing machine repair near me", "samsung washing machine repair",
                  "washing machines repair dubai"):
            self.assertNotIn(k, kws)
        # "drum" sits INSIDE the phrase, so phrase match does not reach it
        self.assertIn("washing machine drum repair", kws)
        self.assertIn("washer repair", kws)
        # "lg washer repair" is reached by "washer repair"
        self.assertNotIn("lg washer repair", kws)
        exact, _ = self.v.select_bid_rows(rows, exact=True)
        self.assertGreater(len(exact), len(chosen))

    def layer(self, kw):
        i, layer = self.v.classify(kw, self.svcs)
        return layer

    def test_gpt_review_junk_bugs(self):
        # each keyword in ITS OWN business's plan: a carpenter query is a
        # buyer for a carpenter and someone else's job for an appliance shop
        import importlib
        cases = [("electrical wiring repair", "Electrician services", ["electrician"]),
                 ("carpenter reviews", "Carpentry services", ["carpenter"]),
                 ("manual gearbox repair", "Auto repair garage", ["gearbox repair"]),
                 ("plumber dubai", "Plumbing company", ["plumber"])]
        saved = dict(os.environ)
        try:
            for kw, niche, seeds in cases:
                os.environ["NICHE_DESCRIPTION"] = niche
                os.environ["SEED_KEYWORDS"] = ", ".join(seeds)
                v = importlib.reload(self.v)
                svcs = v.build_services(seeds)
                v._build_normaliser(svcs)
                v.register_other_services(svcs)
                self.assertIsNone(v.junk_reason(kw), f"{kw} in a '{niche}' plan")
        finally:
            os.environ.clear(); os.environ.update(saved)
            type(self).v = importlib.reload(self.v)
            type(self).v._build_normaliser(self.svcs)
            type(self).v.register_other_services(self.svcs)
        self.assertIsNone(self.v.junk_reason("washing machine parts replacement"))
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
        with open(FIXTURE, encoding="utf-8") as f:
            text = {r["id"]: r["keyword"] for r in json.load(f)["keywords"]}
        sys.path.insert(0, SCRIPTS)
        import service_architecture as vtsa
        vtsa.restore_classifier(plan["classifier"])
        for g in plan["ad_groups"]:
            self.assertEqual(g["match_type"], "exact" if g["layer"] == "symptom" else "phrase")
            if g["layer"] == "symptom":
                self.assertEqual(g["bid_multiplier"], 0.6)
            # bid list is a subset of the layer's rows, never empty
            self.assertTrue(set(g["keyword_ids"]) <= set(g["all_keyword_ids"]))
            self.assertTrue(g["keyword_ids"])
            if g["match_type"] == "phrase":
                keys = [vtsa._phrase_key(text[i]) for i in g["keyword_ids"] if i in text]
                for a in keys:
                    for b in keys:
                        if a is not b:
                            self.assertFalse(vtsa._contains(a, b) and len(b) < len(a),
                                             f"{a} is already reached by {b}")
        self.assertNotIn("fallback_legacy", plan)
        self.assertIn("classifier", plan)
        # the H1 term: no "near me", and an Arabic page carries the Arabic city
        for pg in plan["landing_pages"]:
            prim = pg["keyword_map"]["primary"]
            self.assertNotIn("near me", prim, pg["url_slug"])
            if pg["language"] == "ar":
                self.assertTrue(prim.endswith("دبي"), prim)
                self.assertNotIn("dubai", prim)
            else:
                self.assertTrue(prim.endswith("dubai"), prim)

    def test_plan_page_ids_are_unique_per_language(self):
        sys.path.insert(0, SCRIPTS)
        import importlib
        os.environ.setdefault("ANTHROPIC_API_KEY", "offline")
        import analyze_with_claude as awc
        awc = importlib.reload(awc)
        with tempfile.TemporaryDirectory() as d:
            plan, _ = run_stage(d, {"DAILY_BUDGET": "150000"})
        ids = [awc.plan_page_id(pg) for pg in plan["landing_pages"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("ar/washing-machine-repair-dubai", ids)
        self.assertIn("washing-machine-repair-dubai", ids)

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


FAKE_MODEL_RUNNER = r'''
import json, os, sys, runpy, types
import anthropic
plan = json.load(open("ad_group_plan.json", encoding="utf-8"))
rows = {r["id"]: r["keyword"] for r in json.load(open("scored_keywords.json", encoding="utf-8"))["keywords"]}
gs = plan["ad_groups"]
ans = {"ad_groups": [], "landing_pages": [], "notes": ""}
for i, g in enumerate(gs):
    c = [rows[x] for x in g.get("rescue_candidate_ids", [])]
    o = gs[(i + 1) % len(gs)].get("rescue_candidate_ids", [])
    ans["ad_groups"].append({"name": g["name"], "theme": "t", "intent_expansion_keywords": [],
                             "rescued_keywords": c[:3] + ["not a candidate at all"] + ([rows[o[0]]] if o else [])})
class M: content = [types.SimpleNamespace(type="text", text=json.dumps(ans, ensure_ascii=False))]
class S:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self): return M()
class F:
    def __init__(self, *a, **k): self.messages = types.SimpleNamespace(stream=lambda **kw: S())
anthropic.Anthropic = F
os.environ["ANTHROPIC_API_KEY"] = "offline"
sys.argv = ["x"]
runpy.run_path(os.environ["AWC_PATH"], run_name="__main__")
'''


class Rescue(unittest.TestCase):
    """The model's picks among unreached low-volume rows: only real
    candidates of THAT group are accepted."""

    def test_rescue_accepts_only_the_groups_own_candidates(self):
        try:
            import anthropic  # noqa: F401
        except Exception:
            self.skipTest("anthropic not installed")
        with tempfile.TemporaryDirectory() as d:
            plan, _ = run_stage(d, {"DAILY_BUDGET": "20000"})
            runner = os.path.join(d, "fake.py")
            with open(runner, "w", encoding="utf-8") as f:
                f.write(FAKE_MODEL_RUNNER)
            env = dict(os.environ, AWC_PATH=os.path.join(SCRIPTS, "analyze_with_claude.py"),
                       BUSINESS_NAME="Washer Dryer Repair Dubai", SEED_KEYWORDS="x",
                       NICHE_DESCRIPTION="Home Appliance Repair Services",
                       TARGET_LOCATION="Dubai, United Arab Emirates", PYTHONIOENCODING="utf-8")
            res = subprocess.run([sys.executable, runner], cwd=d, env=env, capture_output=True,
                                 text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0, res.stdout[-2000:] + res.stderr[-2000:])
            with open(os.path.join(d, "keyword_strategy.json"), encoding="utf-8") as f:
                strat = json.load(f)
            with open(os.path.join(d, "scored_keywords.json"), encoding="utf-8") as f:
                text = {r["id"]: r["keyword"] for r in json.load(f)["keywords"]}
        bid = {g["name"]: {k["keyword"] for k in g["keywords"]} for g in strat["ad_groups"]}
        added = 0
        for g in plan["ad_groups"]:
            own = {text[i] for i in g.get("rescue_candidate_ids", [])}
            got = bid.get(g["name"], set())
            self.assertNotIn("not a candidate at all", got)
            added += len(got & own)
            # another SERVICE's candidate never lands here
            foreign = {text[i] for o in plan["ad_groups"] if o["service"] != g["service"]
                       for i in o.get("rescue_candidate_ids", [])}
            self.assertFalse(got & (foreign - own), g["name"])
        self.assertGreater(added, 0)
        self.assertIn("Rescue:", res.stdout)


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
