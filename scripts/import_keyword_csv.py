"""
Stage 1-CSV — USE A KEYWORD PLANNER EXPORT INSTEAD OF PULLING

WHY THIS EXISTS
    Stage 1 asks the Planner for ideas around a few seeds. That is the right
    move for a new client, and the wrong one when you have already exported
    the data: you pay the API again, you get a slightly different set, and —
    the real cost — you lose the curation. A CSV you exported by hand is a
    keyword set you already looked at and agreed with.

    It also removes the seed guessing. The seeds stop being a brief someone
    has to invent and become "here are the queries, plan the site around
    them".

WHAT IT DOES
    Reads a Google Ads Keyword Planner CSV (the "Keyword Stats" download) and
    writes keyword_data_output.json in Stage 1's exact record shape, so every
    stage after it — 1.6 query expansion, 2.5 scoring, 3-SEO strategy — runs
    unchanged.

    Handles what Google actually exports: UTF-16 with a BOM, tab separated,
    two title rows before the header, "--" for missing values, and thousands
    separators.

INPUT   KEYWORDS_CSV_URL  (raw URL) or KEYWORDS_CSV_PATH (local file)
OUTPUT  keyword_data_output.json   — same shape keyword_research.py writes

Optional env vars:
    MIN_CSV_VOLUME   drop rows below this monthly volume (default 0 = keep all,
                     including the no-data rows: a query Google reports with no
                     volume is still a query, and Stage 1.6 treats those as
                     heading/FAQ material rather than page targets)
"""

import csv
import io
import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_FILE = "keyword_data_output.json"
CSV_URL = os.environ.get("KEYWORDS_CSV_URL", "").strip()
CSV_PATH = os.environ.get("KEYWORDS_CSV_PATH", "").strip()
MIN_VOLUME = int(os.environ.get("MIN_CSV_VOLUME", "0") or 0)

# Google's own column names. Kept as a list per field because the export's
# wording shifts between account locales and Ads versions.
COLS = {
    "keyword": ["Keyword", "Search term", "Keyword (by relevance)"],
    "volume": ["Avg. monthly searches", "Avg. monthly searches (exact match only)"],
    "competition": ["Competition"],
    "comp_index": ["Competition (indexed value)"],
    "low_bid": ["Top of page bid (low range)"],
    "high_bid": ["Top of page bid (high range)"],
    "currency": ["Currency"],
}


def _decode(raw):
    """Planner exports are UTF-16 with a BOM. Some tools re-save as UTF-8."""
    for enc in ("utf-16", "utf-8-sig", "utf-8", "cp1252"):
        try:
            text = raw.decode(enc)
            if "\t" in text or "," in text:
                return text
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def _num(v, as_float=False):
    v = str(v or "").strip().replace(",", "").replace("%", "")
    if not v or v in ("--", "-", "—"):
        return 0.0 if as_float else 0
    try:
        return float(v) if as_float else int(float(v))
    except ValueError:
        return 0.0 if as_float else 0


def _find_header(rows):
    """The export opens with a title row and a date-range row before the real
    header, and the header itself is not always row 3."""
    for i, r in enumerate(rows[:10]):
        cells = [c.strip() for c in r]
        if any(c in cells for c in COLS["keyword"]):
            return i, cells
    raise ValueError("no header row containing a Keyword column — is this a "
                     "Keyword Planner export?")


def _col(header, names):
    for n in names:
        if n in header:
            return header.index(n)
    return None


def load_rows(text):
    delim = "\t" if text.count("\t") > text.count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    hi, header = _find_header(rows)
    idx = {k: _col(header, v) for k, v in COLS.items()}
    if idx["keyword"] is None:
        raise ValueError("Keyword column not found")

    # Month columns ("Searches: Jul 2025" ...) give the trend and peak months
    # for free — the same two signals Stage 1 computes from the API response.
    months = [(i, h) for i, h in enumerate(header) if h.startswith("Searches:")]

    out, seen = [], set()
    for r in rows[hi + 1:]:
        if len(r) <= idx["keyword"]:
            continue
        kw = str(r[idx["keyword"]]).strip()
        if not kw or kw.lower() in seen:
            continue
        seen.add(kw.lower())
        vol = _num(r[idx["volume"]]) if idx["volume"] is not None and len(r) > idx["volume"] else 0
        if vol < MIN_VOLUME:
            continue
        vols = []
        for i, _h in months:
            if len(r) > i:
                vols.append(_num(r[i]))
        out.append({
            "keyword": kw,
            "avg_monthly_searches": vol,
            "competition": (str(r[idx["competition"]]).strip().upper()
                            if idx["competition"] is not None and len(r) > idx["competition"]
                            else "UNKNOWN") or "UNKNOWN",
            "competition_index": (_num(r[idx["comp_index"]])
                                  if idx["comp_index"] is not None and len(r) > idx["comp_index"] else 0),
            "low_top_bid": (_num(r[idx["low_bid"]], True)
                            if idx["low_bid"] is not None and len(r) > idx["low_bid"] else 0.0),
            "high_top_bid": (_num(r[idx["high_bid"]], True)
                             if idx["high_bid"] is not None and len(r) > idx["high_bid"] else 0.0),
            "_monthly": vols,
            "source": "planner",
        })
    return out


def attach_trend(rows):
    """classify_trend + peak_months, reusing Stage 1's own functions so a CSV
    row and an API row are scored identically downstream."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from keyword_research import classify_trend
    except Exception:
        classify_trend = None
    _M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for r in rows:
        vols = r.pop("_monthly", []) or []
        r["trend"] = classify_trend(vols) if (classify_trend and vols) else "UNKNOWN"
        if vols and max(vols) > 0:
            # The export's month columns are already in calendar order and
            # labelled, so the peak is a direct lookup — no window-offset
            # guessing of the kind that used to mislabel API data.
            top = max(vols)
            peak = [i for i, v in enumerate(vols) if v == top][:2]
            r["peak_months"] = "/".join(_M[i % 12] for i in peak)
        else:
            r["peak_months"] = ""
    return rows


def main():
    if not CSV_URL and not CSV_PATH:
        print("ℹ️ No KEYWORDS_CSV_URL / KEYWORDS_CSV_PATH — nothing to import.")
        return
    try:
        if CSV_PATH and os.path.exists(CSV_PATH):
            raw = open(CSV_PATH, "rb").read()
            src = CSV_PATH
        else:
            req = urllib.request.Request(CSV_URL, headers={"User-Agent": "keyword-tool"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            src = CSV_URL
        rows = attach_trend(load_rows(_decode(raw)))
    except Exception as e:
        print(f"❌ CSV import failed ({str(e)[:120]}).")
        sys.exit(1)

    if not rows:
        print("❌ CSV parsed but held no keyword rows.")
        sys.exit(1)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)

    with_vol = sum(1 for r in rows if r["avg_monthly_searches"] > 0)
    total = sum(r["avg_monthly_searches"] for r in rows)
    print(f"✅ Imported {len(rows)} keywords from {src[:70]}")
    print(f"   {with_vol} with volume | {len(rows) - with_vol} no-data "
          f"(kept as heading/FAQ material) | {total:,}/mo total")
    top = sorted(rows, key=lambda r: -r["avg_monthly_searches"])[:5]
    for r in top:
        print(f"   {r['avg_monthly_searches']:>7}/mo  {r['keyword']}")
    print(f"   → {OUT_FILE} — Stage 1.6 and Stage 2.5 run on this unchanged")


if __name__ == "__main__":
    main()
