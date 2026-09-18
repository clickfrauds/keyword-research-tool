"""
serp_client.py — one SerpApi door for every script in this repo.

Four workflows spend SerpApi credits (Opportunity Finder, Difficulty, SERP
Shape, Mode 3 Site Plan's duplicate check) and each used to call the API on
its own. On a 250-search plan that meant:

  * the same query paid for twice — re-running a finder with a higher cap
    re-bought every SERP the first run had already read, and a Difficulty
    check on a city the finder had just scanned bought it a third time;
  * no idea of the balance until a run ran dry halfway through.

So every script goes through here:

  fetch(params)      cached GET. A fresh copy on disk costs nothing; only a
                     miss spends a credit. Failures are never cached.
  searches_left()    the account balance. SerpApi's account endpoint is free
                     and does not count against the plan.
  stats()            credits spent vs. served from cache, for the run log.

The cache lives in .serp_cache/ and the workflows carry it between runs with
actions/cache, so it is shared by all four workflows. Results in a local SERP
move slowly; SERP_CACHE_DAYS (default 30) is how old a copy may be before it
is bought again, and 0 turns the cache off.
"""

import gzip
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

CACHE_DIR = os.environ.get("SERP_CACHE_DIR", ".serp_cache")
CACHE_DAYS = float(os.environ.get("SERP_CACHE_DAYS", "30") or 0)

_STATS = {"spent": 0, "cached": 0, "failed": 0}


def _key(params):
    # The api key is not part of what was asked, and must never be written
    # to disk, so it stays out of both the hash and the stored copy.
    clean = {k: str(v) for k, v in params.items() if k != "api_key"}
    return hashlib.sha1(json.dumps(clean, sort_keys=True).encode("utf-8")).hexdigest(), clean


def _path(h):
    return os.path.join(CACHE_DIR, h[:2], h + ".json.gz")


def _read(h):
    if CACHE_DAYS <= 0:
        return None
    p = _path(h)
    try:
        if time.time() - os.path.getmtime(p) > CACHE_DAYS * 86400:
            return None
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f).get("data")
    except Exception:
        return None


def _write(h, clean, data):
    if CACHE_DAYS <= 0:
        return
    try:
        os.makedirs(os.path.dirname(_path(h)), exist_ok=True)
        with gzip.open(_path(h), "wt", encoding="utf-8") as f:
            json.dump({"params": clean, "saved": time.strftime("%Y-%m-%d"), "data": data}, f)
    except Exception:
        pass  # a cache that cannot be written is only a missed saving


def fetch(params, timeout=40):
    """(data, error, from_cache). `params` must carry api_key for a live call.

    Error text is SerpApi's own message where there is one — "HTTP 400" alone
    never said which parameter was rejected.
    """
    h, clean = _key(params)
    cached = _read(h)
    if cached is not None:
        _STATS["cached"] += 1
        return cached, None, True
    if not params.get("api_key"):
        return None, "no SERPAPI_API_KEY", False
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8", "replace")).get("error", "")
        except Exception:
            pass
        _STATS["failed"] += 1
        return None, f"HTTP {e.code} — {detail or 'no detail returned'}", False
    except Exception as e:
        _STATS["failed"] += 1
        return None, str(e)[:120], False
    if data.get("error"):
        _STATS["failed"] += 1
        return None, f"SerpApi: {data['error']}", False
    _STATS["spent"] += 1
    _write(h, clean, data)
    return data, None, False


def searches_left(api_key=None):
    """Searches remaining on the account, or None when it cannot be read.

    None means "unknown", never "zero" — a failed balance check must not
    stop a run that would otherwise have worked.
    """
    key = api_key or os.environ.get("SERPAPI_API_KEY", "").strip()
    if not key:
        return None
    try:
        url = "https://serpapi.com/account.json?" + urllib.parse.urlencode({"api_key": key})
        with urllib.request.urlopen(url, timeout=20) as r:
            acct = json.loads(r.read().decode("utf-8", "replace"))
        for k in ("total_searches_left", "plan_searches_left"):
            if acct.get(k) is not None:
                return int(acct[k])
    except Exception:
        pass
    return None


def stats():
    return dict(_STATS)


def summary_line():
    s = _STATS
    return (f"SerpApi: {s['spent']} credit(s) spent · {s['cached']} served free from cache"
            + (f" · {s['failed']} failed" if s["failed"] else ""))
