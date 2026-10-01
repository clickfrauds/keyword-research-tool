"""The negative-guard script, run in node against a fake AdsApp: the rules
Stage 2.7 used to SELECT keywords are the rules the guard enforces on
search terms. Offline; no Claude call (the niche lists are stubbed)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

HARNESS = r"""
const fs = require('fs');
const js = fs.readFileSync(process.argv[2], 'utf8');
const terms = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const banned = [];
function rows(list) { let i = 0; return { hasNext: () => i < list.length, next: () => list[i++] }; }
let call = 0;
global.Logger = { log: () => {} };
global.AdsApp = {
  search: (q) => {
    call++;
    if (call === 1) return rows([{ campaign: { name: 'Test - Search' } }]);
    return rows(terms.map(t => ({ searchTermView: { searchTerm: t }, metrics: { conversions: 0,
                                  impressions: 1, clicks: 0 }, adGroup: { id: 1 } })));
  },
  adGroups: () => ({ withIds: () => ({ get: () => rows([{ createNegativeKeyword: (k) => banned.push(k) }]) }) })
};
new Function(js + '\nmain();')();
fs.writeFileSync(process.argv[4], JSON.stringify(banned));
"""


def render(seeds, niche, plan_classifier, bid_keywords, products, roots=("fridge", "washer")):
    import importlib
    os.environ["SEED_KEYWORDS"] = ", ".join(seeds)
    os.environ["NICHE_DESCRIPTION"] = niche
    os.environ.pop("ALLOW_SHORT_PRODUCT", None)
    import generate_ads_script as gas
    gas = importlib.reload(gas)
    with open("ad_group_plan.json", "w", encoding="utf-8") as f:
        json.dump({"classifier": plan_classifier}, f)
    js, _ = gas.render_script(["Test - Search"], bid_keywords, products, list(roots), {})
    return js


@unittest.skipUnless(shutil.which("node"), "node not installed")
class Guard(unittest.TestCase):
    def run_guard(self, js, terms):
        with tempfile.TemporaryDirectory() as d:
            p = {n: os.path.join(d, n) for n in ("g.js", "t.json", "h.js", "o.json")}
            open(p["g.js"], "w", encoding="utf-8").write(js)
            json.dump(terms, open(p["t.json"], "w", encoding="utf-8"))
            open(p["h.js"], "w", encoding="utf-8").write(HARNESS)
            subprocess.run(["node", p["h.js"], p["g.js"], p["t.json"], p["o.json"]], check=True)
            return {b.strip("[]") for b in json.load(open(p["o.json"], encoding="utf-8"))}

    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.env = dict(os.environ)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.clear(); os.environ.update(self.env)

    def test_repair_business(self):
        js = render(["fridge repair", "washing machine repair"], "Home appliance repair",
                    {"WRONG_LOCS": ["sharjah", "abu dhabi"],
                     "JUNK_PHRASES": ["hair dryer", "dryer vent", "urban company"],
                     "OTHER_SERVICE_PHRASES": ["ac", "air conditioning", "plumber"]},
                    ["fridge repair", "washing machine repair", "dryer repair"],
                    ["fridge", "washing", "machine", "dryer", "samsung", "lg"])
        self.assertIn("var ALLOW_SHORT_PRODUCT = false;", js)
        banned = self.run_guard(js, [
            "dyson hair dryer repair", "urban company fridge repair", "dryer vent repair",
            "fridge repair sharjah", "ac washing machine repair", "samsung fridge",
            "fridge repair near me", "samsung washing machine repair", "dryer repair dubai"])
        for t in ("dyson hair dryer repair", "urban company fridge repair", "dryer vent repair",
                  "fridge repair sharjah", "ac washing machine repair", "samsung fridge"):
            self.assertIn(t, banned, t)
        for t in ("fridge repair near me", "samsung washing machine repair", "dryer repair dubai"):
            self.assertNotIn(t, banned, t)

    def test_trade_business_keeps_bare_provider_searches(self):
        js = render(["plumber seattle", "drain cleaning"], "Residential plumbing company",
                    {"WRONG_LOCS": ["portland", "oregon"], "OTHER_SERVICE_PHRASES": ["electrician"]},
                    ["plumber seattle", "emergency plumber", "drain cleaning seattle"],
                    ["plumber", "drain", "seattle"], roots=("plumber",))
        banned = self.run_guard(js, ["plumbr", "plumber ballard", "plumber portland",
                                     "electrician near me", "plumber seattle cost"])
        self.assertNotIn("plumbr", banned)          # a typo'd hire is a lead
        self.assertNotIn("plumber ballard", banned)
        self.assertNotIn("plumber seattle cost", banned)
        self.assertIn("plumber portland", banned)
        self.assertIn("electrician near me", banned)

    def test_maker_business_keeps_short_product_queries(self):
        js = render(["kitchen cabinets dubai"], "Custom kitchen cabinets maker", {},
                    ["kitchen cabinets"], ["kitchen", "cabinets", "wardrobe"])
        self.assertIn("var ALLOW_SHORT_PRODUCT = true;", js)
        self.assertNotIn("wooden wardrobe", self.run_guard(js, ["wooden wardrobe"]))

    def test_negatives_never_sit_inside_a_buyer_row(self):
        """Run 0d732cac: "electrician", "mini fridge", "dish machine repair",
        "led backlight repair" became campaign negatives and blocked buyers."""
        import importlib
        import generate_ads_script as gas
        gas = importlib.reload(gas)
        rows = [("fridge repair", 1), ("fridge electrician near me", 2), ("mini fridge repair", 3),
                ("dish machine repair", 4), ("fridge repair jobs", 5), ("led backlight repair", 6)]
        json.dump({"keywords": [{"id": i, "keyword": k} for k, i in rows]},
                  open("scored_keywords.json", "w", encoding="utf-8"))
        json.dump({"ad_groups": [{"all_keyword_ids": [1, 2, 3], "keyword_ids": [1]}],
                   "excluded": [{"keyword": "fridge repair jobs", "why": "non-service intent: jobs"},
                                {"keyword": "dish machine repair", "why": "matches no service"},
                                {"keyword": "led backlight repair", "why": "matches no service"}]},
                  open("ad_group_plan.json", "w", encoding="utf-8"))
        js, stats = gas.render_script(["C"], ["fridge repair"], ["fridge"], ["fridge"],
                                      {"forbidden_words": ["electrician", "mini fridge", "jobs"]})
        forb = stats["block_lists"]["forbidden"]
        self.assertNotIn("electrician", forb)       # inside "fridge electrician near me"
        self.assertNotIn("mini fridge", forb)       # inside "mini fridge repair"
        self.assertIn("jobs", forb)
        neg = gas.negatives_from_excluded(
            {"seo_content_keywords": [{"keyword": k} for k, _ in rows[3:]]}, ["fridge repair"])
        self.assertIn("fridge repair jobs", neg)            # real junk reason
        self.assertNotIn("dish machine repair", neg)        # a synonym gap, not junk
        self.assertNotIn("led backlight repair", neg)

    def test_no_plan_is_the_old_behaviour(self):
        import importlib
        import generate_ads_script as gas
        gas = importlib.reload(gas)
        self.assertEqual(gas.plan_block_lists(), ([], []))


class CampaignNegativeGate(unittest.TestCase):
    """A campaign negative blocks every query containing it, in every ad
    group. Run 0d732cac shipped 607; these are its real false positives and
    its real junk, English and Arabic. Python only — no node needed."""

    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.env = dict(os.environ)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.clear(); os.environ.update(self.env)

    def gate(self, terms):
        import importlib
        seeds = ["Washing machine repair", "Dryer repair", "Dishwasher repair",
                 "Refrigerator repair", "LED TV repair", "تصليح غسالات", "تصليح ثلاجات",
                 "تصليح تلفزيون"]
        os.environ["NICHE_DESCRIPTION"] = "Home Appliance Repair Services"
        os.environ["SEED_KEYWORDS"] = ", ".join(seeds)
        import service_architecture as v
        v = importlib.reload(v)
        svcs = v.build_services(seeds)
        v._build_normaliser(svcs)
        snap = v.classifier_snapshot()
        snap["WRONG_LOCS"] = ["sharjah", "abu dhabi"]
        json.dump({"classifier": snap,
                   "services": [{"name": s["name"], "aliases": s["aliases"], "lang": s["lang"]}
                                for s in svcs]},
                  open("ad_group_plan.json", "w", encoding="utf-8"), ensure_ascii=False)
        import generate_ads_script as gas
        gas = importlib.reload(gas)
        kept, dropped = gas.campaign_negative_gate(terms)
        return set(kept), {t for ts in dropped.values() for t in ts}

    def test_buyers_dropped_junk_kept(self):
        buyers = ["fridge electrician near me", "تصليح شاشات تلفاز", "siemens", "inch",
                  "price in dubai", "samsung dryer not working", "dish machine repair",
                  "led backlight repair", "تصليح ديب فريزر", "washing machine breakdown",
                  "lg dryer squeaking", "55 inch screen replacement price",
                  "samsung 55 inch led tv screen replacement cost", "cost of replacing led tv screen",
                  "lcd screen replacement 55 inch",
                  # bare words that sit inside a buyer phrase above
                  "electrician", "كهربائي", "كهربائي تصليح غسالات"]
        junk = ["appliance repair course dubai", "dyson hair dryer repair",
                "dyson supersonic repair", "vent repair near me", "ac repair",
                "replacement screen for 50 inch tv", "lcd panel bonding machine",
                "plumber", "urban company fridge repair",
                "طريقة تصليح الغسالة", "fridge repair sharjah", "appliance repair apprenticeship",
                "multimeter", "compressor types explained", "led monitor repair"]
        kept, dropped = self.gate(buyers + junk)
        for t in buyers:
            self.assertIn(t, dropped, t)
        for t in junk:
            self.assertIn(t, kept, t)

    def test_no_plan_drops_nothing(self):
        import importlib
        import generate_ads_script as gas
        gas = importlib.reload(gas)
        self.assertEqual(gas.campaign_negative_gate(["siemens", "inch"]),
                         (["siemens", "inch"], {}))


if __name__ == "__main__":
    unittest.main()
