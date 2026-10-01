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

    def test_no_plan_is_the_old_behaviour(self):
        import importlib
        import generate_ads_script as gas
        gas = importlib.reload(gas)
        self.assertEqual(gas.plan_block_lists(), ([], []))


if __name__ == "__main__":
    unittest.main()
