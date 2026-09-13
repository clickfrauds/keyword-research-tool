#!/usr/bin/env python3
"""
serp_shape.py — will a written article rank for this query, or is the page
already a wall of something an article cannot beat?

This is the check that was being done by hand, one query at a time, about
twenty-five times in an afternoon. It is also the check that was skipped
before writing the first thirteen articles on arizonahomeservicepros.com —
ten of them target SERPs held by YouTube and Reddit, which no amount of
writing wins.

What it looks for is not "difficulty". It is WHO is already there, because
that answers a different and more useful question: has a site like this one
already earned a place on this page?

  LOCAL BUSINESS BLOG at the top   a contractor's own blog post ranking here
                                   is proof the slot is winnable
  VIDEO WALL                       YouTube above the fold — Google has decided
                                   this query is answered by showing, not
                                   telling, and text will not displace it
  FORUM WALL                       Reddit / Quora / Stack Exchange — the query
                                   wants strangers' experiences
  BIG BRAND                        manufacturers (Rheem, Aquasana), nationals
                                   (Roto-Rooter), publishers (Forbes, Angi),
                                   insurers. Beatable in theory, not by a
                                   three-week-old domain
  DIRECTORY                        Yelp, BBB, Thumbtack, MapQuest

Usage
  SERPAPI_API_KEY=... python scripts/serp_shape.py "query one" "query two"
  SERPAPI_API_KEY=... python scripts/serp_shape.py --file queries.txt

One SerpApi credit per query. Writes serp_shape.csv and serp_shape.md.
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ.get("SERPAPI_API_KEY", "").strip()
GL = os.environ.get("SERP_GL", "us")
GOOGLE_DOMAIN = os.environ.get("SERP_GOOGLE_DOMAIN", "google.com")

# Hosts whose presence says something about the page, grouped by what they say.
FORUMS = ("reddit.com", "quora.com", "stackexchange.com", "answers.com",
          "houzz.com/discussions", "city-data.com", "justanswer.com",
          "facebook.com", "diychatroom.com", "terrylove.com")
VIDEO = ("youtube.com", "youtu.be", "tiktok.com", "vimeo.com")
DIRECTORY = ("yelp.com", "bbb.org", "thumbtack.com", "angi.com", "angieslist.com",
             "homeadvisor.com", "mapquest.com", "yellowpages.com", "porch.com",
             "nextdoor.com", "manta.com", "bark.com", "houzz.com")
# Brands an article on a new domain is not going to outrank for an
# informational query, whatever it says.
BIGBRAND = ("rheem.com", "aosmith.com", "bradfordwhite.com", "navien.com",
            "rinnai.com", "aquasana.com", "culligan.com", "kohler.com",
            "moen.com", "delta.com", "homedepot.com", "lowes.com",
            "rotorooter.com", "mrrooter.com", "benjaminfranklinplumbing.com",
            "rescuerooter.com", "americanleakdetection.com", "arsrescuerooter.com",
            "forbes.com", "nytimes.com", "bobvila.com", "thisoldhouse.com",
            "familyhandyman.com", "hgtv.com", "consumerreports.org",
            "allstate.com", "statefarm.com", "progressive.com", "geico.com",
            "rocketmortgage.com", "epa.gov", "energy.gov")


# A contractor's own site is the signal worth having: if one has earned a top
# spot, a site like this one can. Testing for trade words in the domain finds
# them; the alternative — "anything not on a blocklist" — counted Hawaii's
# Department of Water Supply and California Water Service as proof that
# "how to tell if a water leak is inside or outside" was winnable.
TRADE_WORDS = ("plumb", "rooter", "drain", "sewer", "septic", "hvac", "heating",
               "cooling", "airconditioning", "restoration", "leakdetection",
               "waterheater", "repipe", "pipe", "mechanical", "contracting")

# Utilities, government and product manufacturers rank on authority a new site
# cannot borrow. Their presence is not evidence of an opening.
INSTITUTIONAL = ("water.com", "dws.", "waterdistrict", "waterauthority",
                 "wateragency", "waterworks.", "publicworks", "utilities.",
                 "firstalert", "petersenproducts", "bmagmeter", "watts.com",
                 "pentair", "zurn.com", "sensus.com", "badgermeter")


# "independent site" was doing too much work. It meant "a site I could not
# name", and the WINNABLE rules read it as "a small site like mine, so the slot
# is reachable". Checked against the domains that actually came back in the
# plumbing run, it was holding merriam-webster.com, servpro.com, homewyse.com,
# thermomate.com, rinnai.us and menards.com — a dictionary, a national
# franchise, a cost aggregator, two manufacturers and a retailer. None of them
# is evidence that a new site can rank; every one of them is evidence it
# cannot.
MANUFACTURER = ("rinnai", "navien", "noritz", "rheem", "bradfordwhite", "aosmith",
                "stiebel", "eemax", "takagi", "thermomate", "moen", "delta",
                "kohler", "americanstandard", "pfister", "insinkerator",
                "zoeller", "libertypumps", "wayne", "ridgid", "culligan",
                "pelicanwater", "springwell", "aquasana", "kinetico")

# A price/estimate database. They rank on a dataset nobody can reproduce.
AGGREGATOR = ("homewyse", "homeguide", "fixr", "homeadvisor", "costhelper",
              "improvenet", "manta", "porch.com", "buildzoom", "houzz",
              "remodelingcalculator", "thervo")

# A franchise with hundreds of locations is not a local contractor, whatever
# its domain says. Checked before TRADE_WORDS, which would call every one of
# these a contractor on the strength of "rooter" or "plumbing".
FRANCHISE = ("rotorooter", "mrrooter", "benjaminfranklinplumbing", "rescuerooter",
             "arsrescuerooter", "servpro", "roto-rooter", "mrhandyman",
             "onehourair", "aireserv", "punctualplumber", "zoomdrain",
             "wind riverenvironmental", "milestone", "leaf home", "leafhome")

# Reference works and encyclopaedias. merriam-webster.com came back at #1 for
# "how much does drain snaking cost", which says the query is being read as a
# definition, not a price.
REFERENCE = ("merriam-webster", "wikipedia", "britannica", "dictionary.com",
             "thefreedictionary", "collinsdictionary", "vocabulary.com")


def classify_host(host):
    h = host.lower()
    h = h[4:] if h.startswith("www.") else h
    for group, name in ((VIDEO, "video"), (FORUMS, "forum"),
                        (DIRECTORY, "directory"), (BIGBRAND, "big brand")):
        if any(d in h for d in group):
            return name
    if h.endswith((".gov", ".edu", ".mil")) or ".gov." in h or ".edu." in h:
        return "institutional"
    if any(d in h for d in INSTITUTIONAL):
        return "institutional"
    if any(d in h for d in REFERENCE):
        return "reference"
    if any(d in h for d in FRANCHISE):
        return "franchise"
    if any(d in h for d in AGGREGATOR):
        return "aggregator"
    if any(d in h for d in MANUFACTURER):
        return "manufacturer"
    if any(w in h for w in TRADE_WORDS):
        return "local contractor"
    return "independent site"


def serp(query):
    q = urllib.parse.urlencode({
        "engine": "google", "q": query, "gl": GL,
        "google_domain": GOOGLE_DOMAIN, "hl": "en", "num": "20",
        "api_key": KEY,
    })
    try:
        with urllib.request.urlopen(f"https://serpapi.com/search?{q}", timeout=40) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8", "replace")).get("error", "")
        except Exception:
            pass
        return None, f"HTTP {e.code} {detail}".strip()
    except Exception as e:
        return None, str(e)[:120]
    if data.get("error"):
        return None, data["error"]
    return data, None


def shape(data):
    """Read the page the way a person would: what is at the top, and who owns it."""
    organic = data.get("organic_results") or []
    top = organic[:10]

    kinds = [classify_host(urllib.parse.urlparse(r.get("link", "")).netloc) for r in top]
    counts = {k: kinds.count(k) for k in set(kinds)}

    # Blocks Google puts ABOVE the organic list decide whether an article is
    # even seen. inline_videos/short_videos sitting first is the strongest
    # signal there is that this query is not answered by text.
    has_video_block = bool(data.get("inline_videos") or data.get("short_videos"))
    has_discussions = bool(data.get("discussions_and_forums"))

    # The map pack. Three businesses and a map, above every organic result,
    # and this classifier was not looking at it at all -- which is why 20 of
    # 20 "plumber <city>" queries came back WINNABLE. On a query like that a
    # contractor in the top three is not an opening, it is the definition of
    # the result: of course plumbers rank for "plumber phoenix".
    #
    # It matters more here than for most sites. A pay-per-call referral
    # service has no premises, so it cannot be in the pack at all, and
    # inventing an address to get in is the exact thing that got a previous
    # site's Google profile flagged. Whatever the pack takes is off the table.
    n_local = len(data.get("local_results", {}).get("places", [])
                  if isinstance(data.get("local_results"), dict)
                  else data.get("local_results") or [])
    has_ads = bool(data.get("ads") or data.get("shopping_results"))

    first_trade = next((i for i, k in enumerate(kinds)
                        if k == "local contractor"), None)
    first_independent = next((i for i, k in enumerate(kinds)
                              if k in ("local contractor", "independent site")), None)
    trade = kinds.count("local contractor")

    video = counts.get("video", 0)
    forum = counts.get("forum", 0)
    indie = counts.get("independent site", 0)
    brand = counts.get("big brand", 0)

    # Sites that hold a page on something a new site cannot assemble: a product
    # line, a price database nobody else has, a national footprint, a
    # dictionary entry. Counted across the top 3, because that is the band
    # being competed for.
    walled = sum(1 for k in kinds[:3]
                 if k in ("manufacturer", "aggregator", "franchise",
                          "reference", "directory", "institutional"))

    # A map pack means the first screen belongs to businesses with premises.
    # Judged before everything else, because on these queries the organic list
    # is what is left over rather than what is being competed for.
    if n_local >= 3:
        directory = sum(1 for k in kinds[:5] if k in ("directory", "forum"))
        if directory >= 3:
            verdict, why = "MAP PACK + DIRECTORIES", (
                f"{n_local} in the map pack, and {directory} of the top 5 "
                "organic are directories")
        else:
            verdict, why = "MAP PACK", (
                f"{n_local} businesses above organic"
                + (", ads too" if has_ads else ""))
        return {
            "verdict": verdict, "why": why,
            "map_pack": n_local,
        "video_block": int(has_video_block), "forums_block": int(has_discussions),
            "map_pack": n_local,
            "big_brand": brand, "independent": indie, "contractor": trade,
            "walled_top3": walled,
            "top3": " \u00b7 ".join(
                (urllib.parse.urlparse(r.get("link", "")).netloc or "?").replace("www.", "")
                for r in top[:3]),
        }

    # Checked before the walls on purpose. "slab leak repair cost arizona" has
    # asapplumbingaz.com and thearizonaplumber.net in the first two places and
    # a video block further down; reading the block first threw away the best
    # opening in the batch.
    # Before anything else. "tankless water heater cost" came back WINNABLE on
    # a top 3 of manufacturers — 33,100 searches a month, and not one slot a
    # plumbing site could take. Two of these in the first three places means
    # Google is answering with the product, the database or the brand, and a
    # contractor further down is the exception that proves it.
    if walled >= 2:
        verdict, why = "BRAND WALL", (
            f"{walled} of the top 3 are manufacturers, aggregators, franchises "
            "or reference sites")
    elif first_trade is not None and first_trade <= 2:
        verdict, why = "WINNABLE", (f"a contractor's site at #{first_trade + 1}"
                                    + (f", {trade} in the top 10" if trade > 1 else ""))
    elif has_video_block and video + forum >= 2:
        verdict, why = "VIDEO WALL", "video block on top, and video/forum below it"
    elif forum >= 3 or (has_discussions and forum >= 2):
        verdict, why = "FORUM WALL", f"{forum} forum results in the top 10"
    elif first_independent is not None and first_independent <= 1 and trade:
        # Position beats count. One contractor's blog at #1 is the strongest
        # evidence there is that this slot is reachable — requiring a second
        # one called "tree roots in sewer line signs" CROWDED when a local
        # plumber held the top spot outright.
        verdict, why = "WINNABLE", f"an independent site at #{first_independent + 1}"
    elif first_independent is not None and first_independent <= 3 and indie >= 2:
        verdict, why = "WINNABLE", (f"independent sites from #{first_independent + 1}, "
                                    f"{indie} in the top 10")
    elif brand >= 3:
        verdict, why = "BIG BRAND", f"{brand} national/manufacturer results"
    elif indie >= 2:
        verdict, why = "MIXED", f"{indie} independent sites, but none in the top 3"
    else:
        verdict, why = "CROWDED", "no independent site with a clear position"

    return {
        "verdict": verdict, "why": why,
        "video": video, "forum": forum, "directory": counts.get("directory", 0),
        "big_brand": brand, "independent": indie, "contractor": trade,
        "walled_top3": walled,
        "institutional": kinds.count("institutional"),
        "video_block": int(has_video_block), "forums_block": int(has_discussions),
        # Joined with a middle dot, not a pipe: this string is printed
        # straight into a markdown table, where "|" opens a new cell. Every
        # row of the plumbing summary showed only its #1 result — #2 and #3
        # were parsed as extra columns and dropped, which are exactly the two
        # the verdict turns on.
        "top3": " · ".join(
            (urllib.parse.urlparse(r.get("link", "")).netloc or "?").replace("www.", "")
            for r in top[:3]),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="*")
    ap.add_argument("--file", help="one query per line")
    a = ap.parse_args()

    def split_queries(text):
        """Accept newlines, semicolons or pipes between queries.

        GitHub renders a workflow_dispatch `type: string` input as a
        single-line box, so ten pasted lines arrive as one long line. The
        first run spent a credit searching that whole list as one query and
        reported it, reasonably enough, as a VIDEO WALL. Any of the three
        separators now works, so a list the browser has flattened onto one
        line still splits correctly.
        """
        parts = re.split(r"[\n;|]+", text)
        return [p.strip() for p in parts
                if p.strip() and not p.lstrip().startswith("#")]

    qs = []
    for raw in a.queries:
        qs += split_queries(raw)
    if a.file:
        with open(a.file, encoding="utf-8") as fh:
            qs += split_queries(fh.read())
    qs = [q for i, q in enumerate(qs) if q not in qs[:i]]

    # A query nobody would type is almost always several run together.
    runaway = [q for q in qs if len(q.split()) > 12]
    if runaway:
        print("WARNING: these look like several queries run together \u2014 "
              "separate them with ; or one per line:")
        for q in runaway:
            print(f"         {q[:86]}")
        print()
    if not qs:
        ap.error("give at least one query, or --file")
    if not KEY:
        print("❌ SERPAPI_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    print(f"🔎 {len(qs)} quer{'y' if len(qs) == 1 else 'ies'} · gl={GL} "
          f"· {len(qs)} SerpApi credit(s)\n")

    rows = []
    for i, q in enumerate(qs, 1):
        data, err = serp(q)
        if err:
            print(f"{i:3}. ⚠️  {q[:56]:58} {err[:44]}")
            rows.append({"query": q, "verdict": "ERROR", "why": err[:80]})
            continue
        s = shape(data)
        mark = {"WINNABLE": "✅", "MIXED": "🟡", "BIG BRAND": "🟠",
                "FORUM WALL": "❌", "VIDEO WALL": "❌", "CROWDED": "❌"}[s["verdict"]]
        print(f"{i:3}. {mark} {s['verdict']:11} {q[:46]:48} {s['top3'][:52]}")
        rows.append({"query": q, **s})

    with open("serp_shape.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    win = [r for r in rows if r.get("verdict") in ("WINNABLE", "MIXED")]
    with open("serp_shape.md", "w", encoding="utf-8") as fh:
        fh.write("# SERP shape\n\nWho already holds each page, and whether a "
                 "written article has room on it.\n\n")
        fh.write("| | Query | Verdict | Why | Top 3 |\n|---|---|---|---|---|\n")
        for r in rows:
            mark = {"WINNABLE": "✅", "MIXED": "🟡", "BIG BRAND": "🟠",
                    "FORUM WALL": "❌", "VIDEO WALL": "❌", "CROWDED": "❌",
                    "ERROR": "⚠️"}.get(r.get("verdict"), "")
            fh.write(f"| {mark} | {r['query']} | {r.get('verdict','')} | "
                     f"{r.get('why','')} | {r.get('top3','')} |\n")
        fh.write(f"\n**{len(win)} of {len(rows)}** have room for an article.\n")

    print(f"\n✅ {len(win)}/{len(rows)} worth writing · serp_shape.csv · serp_shape.md")


if __name__ == "__main__":
    main()
