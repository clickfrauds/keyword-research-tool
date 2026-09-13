#!/usr/bin/env python3
"""How hard is this page to win — five levels, not a yes/no.

A verdict was the wrong shape for the answer. WINNABLE came back 20 times out
of 20 because a contractor ranking on "plumber phoenix" is the definition of
that result, not an opening. MAP PACK then came back 20 times out of 20 because
every local query has a pack. Both readings were true and neither helped: a
signal that never varies carries no information.

What varies is how strong the incumbents are, and that is measurable from the
same SerpApi response already being paid for:

  map pack reviews      12 reviews is a one-van operation; 800 is an
                        institution with a marketing budget
  homepage or inner     three homepages in the top 3 means competing with
                        whole businesses; an inner page or a blog post there
                        means the slot is held by A PAGE, and a page can be
                        beaten by a better page
  exact-match domain    plumberphoenix.com holds an advantage that cannot be
                        outwritten
  directories           Yelp and Angi are not beatable and not leavable
  national franchise    Roto-Rooter has a national link profile
  forum result          Google is choosing discussion over pages

Each is a few points. The total lands in one of five bands, and the band says
what kind of effort the page needs rather than whether to try.

    python scripts/difficulty.py "plumber goodyear" "slab leak repair cost"
    python scripts/difficulty.py --file queries.txt

One SerpApi credit per query, same as serp_shape.
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ.get("SERPAPI_API_KEY", "")
GL = os.environ.get("SERP_GL", "us")

#: Directories and social profiles. Present on nearly every local SERP, and a
#: slot they hold is a slot nobody can take from them.
DIRECTORY = (
    "yelp.", "angi.com", "angieslist", "thumbtack", "homeadvisor", "porch.com",
    "houzz.", "bbb.org", "nextdoor.", "mapquest", "yellowpages", "manta.com",
    "facebook.", "instagram.", "x.com", "twitter.", "linkedin.", "tiktok.",
    "bark.com", "networx", "buildzoom", "expertise.com", "trustpilot",
)

#: Forums. Google putting these first means it wants discussion, not a page.
FORUM = ("reddit.", "quora.", "city-data", "justanswer", "answers.",
         "stackexchange", "houzz.com/discussions")

#: National chains and franchises. Their rankings rest on a link profile no
#: new site can assemble.
NATIONAL = (
    "rotorooter", "roto-rooter", "mrrooter", "benjaminfranklinplumbing",
    "arsrescuerooter", "rescuerooter", "servpro", "zoomdrain", "milestone",
    "leafhome", "americanleakdetection", "homeserve", "punctualplumber",
    "onehourair", "aireserv", "mrhandyman", "neighborly",
)

#: Sites that hold a page on a dataset nobody can reproduce.
AGGREGATOR = ("homewyse", "homeguide", "fixr.com", "costhelper", "thervo",
              "remodelingcalculator", "improvenet")

LEVELS = [
    (20, "1 VERY EASY", "a new site can take this in a few months"),
    (40, "2 EASY", "reachable with good content and some patience"),
    (60, "3 MEDIUM", "needs real content depth, probably a year"),
    (80, "4 TOUGH", "needs links and budget, not just pages"),
    (999, "5 TOUGHEST", "not worth starting without both"),
]


def serp(query):
    q = urllib.parse.urlencode({
        "engine": "google", "q": query, "gl": GL, "hl": "en", "num": "20",
        "api_key": KEY,
    })
    try:
        with urllib.request.urlopen(f"https://serpapi.com/search?{q}",
                                    timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8", "replace")).get("error", "")
        except Exception:
            pass
        return None, f"HTTP {e.code} {detail}"[:120]
    except Exception as e:
        return None, str(e)[:120]


def _host(url):
    return (urllib.parse.urlparse(url or "").netloc or "").replace("www.", "").lower()


def _is_home(url):
    """A result pointing at the site root is a whole business competing here.
    A result with a path is a PAGE, and a page can be beaten by a better one.
    """
    path = urllib.parse.urlparse(url or "").path.strip("/")
    return path == "" or path in ("index.html", "home")


def _emd(host, query):
    """Does the domain contain the query's own words? plumberphoenix.com on
    "plumber phoenix" starts ahead of anything that can be written."""
    words = [w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 3]
    stem = host.split(".")[0].replace("-", "")
    return sum(1 for w in words if w in stem) >= 2


def _places(data):
    lr = data.get("local_results")
    if isinstance(lr, dict):
        return lr.get("places") or []
    return lr or []


def difficulty(data, query):
    """Points, the reasons for them, and the band they land in."""
    organic = (data.get("organic_results") or [])[:10]
    top3 = organic[:3]
    places = _places(data)
    score, why = 0, []

    # ── the map pack ──────────────────────────────────────────────────────
    revs = [int(p.get("reviews") or 0) for p in places]
    if places:
        med = int(statistics.median(revs)) if revs else 0
        if med >= 400:
            score += 25; why.append(f"map pack median {med} reviews")
        elif med >= 150:
            score += 17; why.append(f"map pack median {med} reviews")
        elif med >= 50:
            score += 10; why.append(f"map pack median {med} reviews")
        elif med > 0:
            score += 4; why.append(f"map pack only {med} reviews - thin")
        else:
            score += 6; why.append("map pack present, review counts unknown")

    # ── homepages vs pages ────────────────────────────────────────────────
    # An inner page only counts as beatable when a page could actually beat
    # it. reddit.com/r/phoenix/comments/... and a Yelp search URL are inner
    # pages and neither can be outranked by writing something better, so they
    # were handing "plumber phoenix" a discount it has not earned.
    def _beatable(r):
        h = _host(r.get("link"))
        return not any(d in h for d in DIRECTORY + FORUM + NATIONAL + AGGREGATOR)

    homes = sum(1 for r in top3 if _is_home(r.get("link")))
    inner = sum(1 for r in top3
                if not _is_home(r.get("link")) and _beatable(r))
    held = len(top3) - homes - inner        # directories, forums, nationals
    if homes == 3:
        score += 15; why.append("top 3 are all homepages")
    if held:
        # Counted separately from the credit below, not instead of it. A top 3
        # of one directory and two real pages is both harder AND softer than
        # one of three homepages, and the score should say both.
        score += held * 6
        why.append(f"{held} of the top 3 cannot be outranked by writing")
    if inner >= 2:
        score -= 12; why.append(f"{inner} of the top 3 are beatable pages")
    elif inner == 1:
        score -= 5; why.append("one beatable page in the top 3")

    # ── exact-match domains ───────────────────────────────────────────────
    emds = [_host(r.get("link")) for r in top3 if _emd(_host(r.get("link")), query)]
    if emds:
        score += 14; why.append(f"exact-match domain: {emds[0]}")

    # ── who else is holding slots ─────────────────────────────────────────
    hosts = [_host(r.get("link")) for r in organic]
    ndir = sum(1 for h in hosts if any(d in h for d in DIRECTORY))
    nnat = sum(1 for h in hosts if any(d in h for d in NATIONAL))
    nfor = sum(1 for h in hosts if any(d in h for d in FORUM))
    nagg = sum(1 for h in hosts if any(d in h for d in AGGREGATOR))

    if ndir:
        score += min(ndir * 3, 15); why.append(f"{ndir} directory results")
    if nnat:
        score += min(nnat * 5, 12); why.append(f"{nnat} national franchise")
    if nagg:
        score += min(nagg * 4, 10); why.append(f"{nagg} price aggregator")
    if any(any(d in _host(r.get("link")) for d in FORUM) for r in top3):
        score += 10; why.append("a forum thread is in the top 3")
    elif nfor:
        score += 3; why.append(f"{nfor} forum results lower down")

    if data.get("ads"):
        score += 4; why.append("paid ads on top")

    score = max(0, min(100, score))
    for cap, name, meaning in LEVELS:
        if score <= cap:
            return {"query": query, "score": score, "level": name,
                    "meaning": meaning, "why": "; ".join(why),
                    "map_pack": len(places),
                    "pack_reviews": int(statistics.median(revs)) if revs else 0,
                    "homepages_top3": homes, "inner_top3": inner,
                    "directories": ndir, "national": nnat, "forums": nfor,
                    "top3": " · ".join(_host(r.get("link")) or "?" for r in top3)}


def split_queries(text):
    parts = re.split(r"[;\n|]+", text or "")
    return [p.strip() for p in parts if p.strip()]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="*")
    ap.add_argument("--file", help="one query per line, or separated by ;")
    a = ap.parse_args()

    qs = list(a.queries)
    if a.file and os.path.isfile(a.file):
        qs += split_queries(open(a.file, encoding="utf-8").read())
    qs = [q for q in dict.fromkeys(q.strip() for q in qs if q.strip())]
    if not qs:
        sys.exit("no queries")
    if not KEY:
        sys.exit("SERPAPI_API_KEY is not set")

    print(f"\n{len(qs)} queries · gl={GL} · {len(qs)} SerpApi credit(s)\n")
    rows = []
    for i, q in enumerate(qs, 1):
        data, err = serp(q)
        if err:
            print(f"{i:3}. ERROR  {q[:46]:48} {err[:44]}")
            rows.append({"query": q, "level": "ERROR", "why": err[:90]})
            continue
        d = difficulty(data, q)
        rows.append(d)
        print(f"{i:3}. {d['level']:12} {d['score']:>3}  {q[:40]:42} {d['top3'][:44]}")

    # columns from every row: an ERROR row has fewer keys, and taking them
    # from rows[0] is how this crashed when the first query failed.
    fields, seen = [], set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k); fields.append(k)
    with open("difficulty.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, restval="",
                           extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

    order = {name: i for i, (_, name, _) in enumerate(LEVELS)}
    ranked = sorted([r for r in rows if r.get("level") != "ERROR"],
                    key=lambda r: r["score"])
    with open("difficulty.md", "w", encoding="utf-8") as fh:
        fh.write("# How hard is each page\n\n")
        fh.write("Five bands, easiest first. The band says what kind of effort "
                 "the page needs.\n\n")
        fh.write("| level | score | query | why | top 3 |\n|---|---|---|---|---|\n")
        for r in ranked:
            fh.write(f"| {r['level']} | {r['score']} | {r['query']} | "
                     f"{r['why']} | {r['top3']} |\n")
        fh.write("\n## What the bands mean\n\n")
        for _, name, meaning in LEVELS:
            n = sum(1 for r in ranked if r["level"] == name)
            fh.write(f"- **{name}** ({n}) - {meaning}\n")

    errs = [r for r in rows if r.get("level") == "ERROR"]
    if errs:
        print(f"\n   {len(errs)} of {len(rows)} failed.")
        if len(errs) == len(rows):
            print("   All of them - that is usually the SerpApi quota.")
            print(f"   First error: {errs[0].get('why','')[:70]}")

    print()
    for _, name, meaning in LEVELS:
        n = sum(1 for r in ranked if r["level"] == name)
        if n:
            print(f"   {name:12} {n:>3}  {meaning}")
    print("\ndifficulty.csv · difficulty.md")


if __name__ == "__main__":
    main()
