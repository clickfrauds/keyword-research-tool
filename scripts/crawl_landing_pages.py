"""
crawl_landing_pages.py  (STAGE 0-CRAWL — existing pages become the plan)
----------------------------------------------------------------------
For clients whose landing pages already exist. Reads their URLs, pulls the
real content off each one, and turns it into the seed keywords the normal
pipeline starts from — plus a fixed page→ad-group map so nothing downstream
ever invents a slug for a page that is already live.

WHERE THIS SITS
    URLs -> crawl -> seeds -> [Claude expands] -> Keyword Planner (real
    volumes) -> the existing pipeline, completely unchanged.

  Only the very front of the pipeline is new. The strategy is still built
  from Google's own volume, CPC and competition data — the crawl replaces
  the human typing seed keywords in, nothing more. Deriving a strategy from
  page text instead of from Planner data would be a downgrade, and that is
  explicitly not what happens here.

WHY IT MATTERS
  A campaign built this way cannot produce "Destination not working": the
  URLs came from pages that were already serving, so there is no window
  where an ad points at a page that has not been built. It also fixes the
  count — as many ad groups as there are pages, never an ad group whose
  page does not exist.

WHAT COMES OUT
  landing_pages_source.json  one entry per page: the exact URL (never a
        rebuilt slug), service name, the real H1/H2/H3s so the RSA writer
        can match the page's own words, in-page #anchors, and seeds.
  page_improvements.json     pages too thin to convert, with what to add.
        Feed it to the website builder: the content changes, the URL does
        not, so nothing in the campaign has to move.
  The combined seed list, ready for SEED_KEYWORDS.

Env : LANDING_URLS (comma/newline separated) or landing_urls.txt
      CRAWL_MAX_PAGES (default 25)
      BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION, LANGUAGE (context)
      ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_EFFORT_CRAWL (default low)
Output: landing_pages_source.json, page_improvements.json
"""

import os
import re
import sys
import json
import html
from urllib.parse import urlparse, urljoin

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
EFFORT = os.environ.get("CLAUDE_EFFORT_CRAWL", "low")

BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()
# "no" is the form's legacy sentinel for "no language chosen" = English, NOT
# Norwegian. Every other stage maps it away; without this the crawl would tell
# Claude "the page is in 'no'" on every single English run and ask for
# Norwegian seed keywords.
LANGUAGE = os.environ.get("LANGUAGE", "").strip().lower()
if LANGUAGE in ("no", "none", "default", "english"):
    LANGUAGE = "en"
LANGUAGE = LANGUAGE or "en"

MAX_PAGES = int(os.environ.get("CRAWL_MAX_PAGES", "25") or 25)

SOURCE_FILE = "landing_pages_source.json"
IMPROVE_FILE = "page_improvements.json"

# Under this many words a page is too thin to earn a decent Landing Page
# Experience score, whatever else is on it.
THIN_WORDS = 300


def read_urls():
    raw = os.environ.get("LANDING_URLS", "")
    if not raw and os.path.exists("landing_urls.txt"):
        with open("landing_urls.txt", encoding="utf-8") as f:
            raw = f.read()
    parts = re.split(r"[,\n\r]+", raw)
    urls, seen = [], set()
    for p in parts:
        u = p.strip()
        if not u:
            continue
        if not re.match(r"^https?://", u, re.I):
            u = "https://" + u
        # Same page twice would become two ad groups competing for the same
        # keywords on the same URL.
        key = u.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        urls.append(u)
    return urls[:MAX_PAGES]


def strip_tags(fragment):
    t = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", fragment)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def fetch(url, timeout=20):
    import urllib.request
    import urllib.error

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AdsPageReader/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.getcode() != 200:
                return None, f"HTTP {r.getcode()}"
            charset = r.headers.get_content_charset() or "utf-8"
            return r.read(600_000).decode(charset, "replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, f"unreachable ({str(e)[:70]})"


def extract(url, body):
    """The parts of a page that decide what its ad should say."""
    def all_of(tag):
        return [strip_tags(m) for m in
                re.findall(rf"(?is)<{tag}[^>]*>(.*?)</{tag}>", body)]

    title = ""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
    if m:
        title = strip_tags(m.group(1))[:200]

    desc = ""
    m = re.search(r'(?is)<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']', body)
    if m:
        desc = html.unescape(m.group(1)).strip()[:300]

    h1 = all_of("h1")
    h2 = [h for h in all_of("h2") if h][:15]
    h3 = [h for h in all_of("h3") if h][:20]

    # In-page anchors decide whether sitelinks can point INTO this page or
    # have to point at the client's other pages instead.
    anchors = re.findall(r'(?is)<(?:section|div|h2|h3)[^>]+id=["\']([\w\-]+)["\']', body)
    anchors = [a for a in dict.fromkeys(anchors) if len(a) > 2][:12]

    text = strip_tags(body)
    phones = re.findall(r'(?i)href=["\']tel:([^"\']+)["\']', body)

    return {
        "url": url,
        "title": title,
        "meta_description": desc,
        "h1": h1[0] if h1 else "",
        "h2": h2,
        "h3": h3,
        "anchors": anchors,
        "has_form": bool(re.search(r"(?is)<form\b", body)),
        "has_phone": bool(phones),
        "word_count": len(text.split()),
        "text_sample": text[:4000],
    }


SYSTEM = """You read one landing page and report what it actually sells, so a
Google Ads campaign can be built around it.

Two things matter and they are different:

SEED KEYWORDS are the input to Google's Keyword Planner. They must be the
plain, searchable service terms a customer would type — "ac repair", "split
ac servicing", "emergency ac fix". NOT the page's marketing phrases, NOT the
brand name, NOT long sentences. 5-10 of them, lowercase, 2-4 words each.
Real volume data gets pulled for these afterwards, so a made-up phrase
nobody searches is worse than useless — it returns nothing and the page ends
up with no keywords at all.

CONTENT VERDICT judges whether this page can convert paid traffic and earn a
decent Landing Page Experience score. Be honest and specific. A page that is
a hero image and a phone number is "thin" no matter how pretty it is.

Return ONLY this JSON:
{
  "service_name": "the one service this page sells, title case",
  "seed_keywords": ["lowercase service term", "..."],
  "sub_services": ["Up To Six", "Title Case", "Sub Services"],
  "theme": "one sentence: the single customer intent this page serves",
  "verdict": "strong" | "thin" | "weak",
  "issues": ["what is missing or hurting conversion, one per item"],
  "improvements": ["a concrete addition, phrased as an instruction"]
}

verdict rules:
  strong - enough real copy, clear offer, trust signals, obvious next step
  thin   - too little content to rank or convince
  weak   - has content but no clear offer, no proof, or no call to action
If the page is strong, "issues" and "improvements" may be empty lists."""


def ask_claude(client, page):
    ctx = []
    if BUSINESS_NAME:
        ctx.append(f"BUSINESS: {BUSINESS_NAME}")
    if NICHE_DESCRIPTION:
        ctx.append(f"NICHE: {NICHE_DESCRIPTION}")
    if TARGET_LOCATION:
        ctx.append(f"LOCATION: {TARGET_LOCATION}")
    if LANGUAGE and LANGUAGE != "en":
        ctx.append(f"The page is in '{LANGUAGE}' — write seed keywords in that "
                   f"language, because that is what its customers search in.")

    user = f"""{chr(10).join(ctx)}

URL: {page['url']}
TITLE: {page['title']}
META DESCRIPTION: {page['meta_description']}
H1: {page['h1']}
H2s: {' | '.join(page['h2']) or '(none)'}
H3s: {' | '.join(page['h3']) or '(none)'}
WORD COUNT: {page['word_count']}
HAS FORM: {page['has_form']}   HAS PHONE LINK: {page['has_phone']}

PAGE TEXT:
{page['text_sample']}

Report the JSON now."""

    with client.messages.stream(
        model=MODEL,
        max_tokens=2000,
        output_config={"effort": EFFORT},
        system=[{"type": "text", "text": SYSTEM,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()
    text = "".join(b.text for b in resp.content if b.type == "text")
    u = resp.usage
    cost = u.input_tokens * 3 / 1e6 + u.output_tokens * 15 / 1e6
    print(f"   Claude: {u.input_tokens} in / {u.output_tokens} out ≈ ${cost:.3f}")
    return robust_json(text)


def robust_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I | re.S)
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def ad_group_name(service, url):
    name = (service or "").strip()
    if not name:
        seg = [s for s in urlparse(url).path.split("/") if s]
        name = (seg[-1] if seg else "Home").replace("-", " ").title()
    return name[:120]


def main():
    urls = read_urls()
    if not urls:
        print("❌ No URLs. Set LANDING_URLS (comma or newline separated) or "
              "create landing_urls.txt.")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is missing.")
        sys.exit(1)

    print(f"Reading {len(urls)} landing page(s)...")
    client = anthropic.Anthropic()

    pages, improvements, all_seeds, failed = [], [], [], []
    used_names = set()

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")
        body, final = fetch(url)
        if body is None:
            print(f"   ❌ {final}")
            failed.append({"url": url, "reason": final})
            continue
        if final != url:
            # The campaign must point at where the page actually lives, or
            # every ad inherits a redirect Google may read as a mismatch.
            print(f"   ↪ redirects to {final} — using that")
            url = final

        page = extract(url, body)
        print(f"   {page['word_count']} words | {len(page['h2'])} H2 | "
              f"{len(page['anchors'])} anchors | form={page['has_form']}")

        info = ask_claude(client, page)
        seeds = [str(s).strip().lower() for s in (info.get("seed_keywords") or [])
                 if str(s).strip()]
        seeds = [s for s in seeds if 1 <= len(s.split()) <= 6][:10]
        if not seeds:
            print("   ⚠️ No usable seed keywords — page skipped.")
            failed.append({"url": url, "reason": "no seed keywords"})
            continue

        name = ad_group_name(info.get("service_name"), url)
        # Two pages selling the same thing would collide into one ad group
        # and the second page would silently lose its ads.
        base, n = name, 2
        while name in used_names:
            name = f"{base} {n}"
            n += 1
        used_names.add(name)

        verdict = str(info.get("verdict", "")).strip().lower()
        if verdict not in ("strong", "thin", "weak"):
            verdict = "thin" if page["word_count"] < THIN_WORDS else "strong"
        # The model can be generous; the word count is not a matter of opinion.
        if page["word_count"] < THIN_WORDS and verdict == "strong":
            verdict = "thin"

        pages.append({
            "url": url,
            "final_url": url,
            "ad_group": name,
            "service_name": str(info.get("service_name", name)).strip(),
            "theme": str(info.get("theme", "")).strip(),
            "sub_services": [str(s).strip() for s in (info.get("sub_services") or [])
                             if str(s).strip()][:6],
            "seed_keywords": seeds,
            "title": page["title"],
            "h1": page["h1"],
            "h2": page["h2"],
            "h3": page["h3"],
            "anchors": page["anchors"],
            "word_count": page["word_count"],
            "has_form": page["has_form"],
            "has_phone": page["has_phone"],
            "verdict": verdict,
        })
        all_seeds.extend(seeds)
        print(f"   → '{name}' | {len(seeds)} seeds | verdict: {verdict}")

        if verdict != "strong":
            improvements.append({
                "url": url,
                "page_name": str(info.get("service_name", name)).strip(),
                "verdict": verdict,
                "word_count": page["word_count"],
                "issues": [str(x).strip() for x in (info.get("issues") or []) if str(x).strip()],
                "improvements": [str(x).strip() for x in (info.get("improvements") or [])
                                 if str(x).strip()],
                "keep_url": True,
            })

    if not pages:
        print("\n❌ No usable pages — nothing written.")
        sys.exit(1)

    # ── sitelinks: anchors if the page has them, otherwise its siblings ──
    # A sitelink pointing at #section on a page with no such section lands
    # the visitor at the top of the page they were already on. Cross-linking
    # to the client's other pages is both valid and a better user path.
    for p in pages:
        if p["anchors"]:
            p["sitelink_mode"] = "anchors"
            p["sitelink_targets"] = [f"{p['url'].rstrip('/')}/#{a}" for a in p["anchors"][:4]]
        else:
            others = [q for q in pages if q["url"] != p["url"]][:4]
            p["sitelink_mode"] = "cross_page"
            p["sitelink_targets"] = [q["url"] for q in others]
            p["sitelink_labels"] = [q["service_name"][:25] for q in others]

    seeds_dedup = sorted(dict.fromkeys(all_seeds))

    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "mode": "existing_pages",
            "pages": pages,
            "failed": failed,
            "seed_keywords": seeds_dedup,
        }, f, indent=2, ensure_ascii=False)

    if improvements:
        with open(IMPROVE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "note": ("Content only — every URL stays exactly as it is, so "
                         "nothing in the campaign has to move."),
                "pages": improvements,
            }, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"✅ {len(pages)} page(s) → {len(pages)} ad group(s)")
    if failed:
        print(f"⚠️ {len(failed)} URL(s) unusable:")
        for f_ in failed:
            print(f"     {f_['url']} — {f_['reason']}")
    weak = [p for p in pages if p["verdict"] != "strong"]
    if weak:
        print(f"📝 {len(weak)} page(s) need content work → {IMPROVE_FILE}")
        for p in weak:
            print(f"     {p['verdict']:<6} {p['url']} ({p['word_count']} words)")
    print(f"→ {SOURCE_FILE}")
    print("\nSEED_KEYWORDS for the next stage:")
    print("  " + ",".join(seeds_dedup))
    print("\nNext: keyword_research.py pulls the real Planner volumes for these.")


if __name__ == "__main__":
    main()
