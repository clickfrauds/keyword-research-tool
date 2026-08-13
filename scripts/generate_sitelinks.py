"""
generate_sitelinks.py  (STAGE 3.85 — ad-group level sitelink assets)
----------------------------------------------------------------------
Every ad group gets its OWN sitelink set, pointing at the anchors that
already exist on that ad group's landing page:

    #services   #pricing   #reviews   #faq   #contact

Ad-group level (not campaign level) is the whole point: a Washing Machine
Repair group's sitelinks say "Washer Repair Pricing", not a generic
"Pricing" shared by every group. Same-page anchors also scroll the visitor
straight to the matching block, which is a Quality-Score relevance signal
rather than another full page load.

GOOGLE'S HARD LIMITS (validated in Python, never trusted to the model):
    link text      <= 25 characters
    description 1  <= 35 characters
    description 2  <= 35 characters
A sitelink with a description must have BOTH lines, or Google drops them.

Claude writes the copy per ad group; anything that breaks a limit or comes
back empty falls back to a deterministic template built from the ad group's
own theme, so this stage can never produce an invalid asset.

Env   : ANTHROPIC_API_KEY, WEBSITE_URL, LANGUAGE (optional), MODEL/EFFORT
Input : keyword_strategy.json  (ad groups + landing pages)
        rsa_editor.csv         (final URL already resolved per ad group)
Output: sitelinks_editor.csv   (Google Ads Editor import)
        sitelinks.json         (the API push stage reads this)
"""

import os
import re
import csv
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STRATEGY = "keyword_strategy.json"
RSA_CSV = "rsa_editor.csv"
CSV_OUT = "sitelinks_editor.csv"
JSON_OUT = "sitelinks.json"

TEXT_MAX, DESC_MAX = 25, 35

WEBSITE_URL = os.environ.get("WEBSITE_URL", "").strip().rstrip("/")
if WEBSITE_URL and not re.match(r"^https?://", WEBSITE_URL, re.I):
    WEBSITE_URL = "https://" + WEBSITE_URL

MODEL = os.environ.get("SITELINK_MODEL", os.environ.get("MODEL", "claude-sonnet-4-6"))
_LANG = os.environ.get("LANGUAGE", "").strip().lower()
_LANG_NAMES = {"ar": "Arabic", "es": "Spanish", "fr": "French", "de": "German",
               "tr": "Turkish", "ur": "Urdu", "hi": "Hindi", "ru": "Russian",
               "zh": "Chinese", "pt": "Portuguese", "it": "Italian", "nl": "Dutch"}
LANG_NAME = _LANG_NAMES.get(_LANG, "")

# The five anchors the site generator emits on every service/landing page.
ANCHORS = [
    ("services", "what the service covers"),
    ("pricing",  "price range and what drives it"),
    ("reviews",  "customer proof"),
    ("faq",      "common questions"),
    ("contact",  "the booking / quote step"),
]


def _len(s):
    return len(str(s or ""))


def _fits(text, limit):
    t = str(text or "").strip()
    return bool(t) and _len(t) <= limit


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def final_urls_by_group():
    """Ad group → Final URL. The RSA stage already resolved it; fall back to
    the landing page slug, then to the site root."""
    out = {}
    if os.path.exists(RSA_CSV):
        with open(RSA_CSV, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                ag, url = (r.get("Ad Group") or "").strip(), (r.get("Final URL") or "").strip()
                if ag and url and ag not in out:
                    out[ag] = url.rstrip("/")
    return out


def slug_for(group_name, pages):
    for p in pages or []:
        if group_name in (p.get("ad_groups_covered") or []):
            s = (p.get("url_slug") or "").strip("/")
            if s:
                return s
    return ""


# Must match generate_rsa_ads.py — the builder's lang_url_prefix defaults to the
# /{lang}/ folder, so sitelinks default to it too. Set LANG_URL_PREFIX=no only
# when the builder published at the domain root.
_LANG_AT_ROOT = os.environ.get("LANG_URL_PREFIX", "yes").strip().lower() in (
    "no", "false", "0", "root")


def lang_prefix_for(group):
    """Non-English ad groups point at /{lang}/{slug}/ — the folder the website
    builder actually publishes that language into. Only used when the RSA stage
    did not already resolve a Final URL for this group.

    `code == _LANG` used to zero the prefix, which silently dropped /ar/ from
    every sitelink on a single-language Arabic run (same bug as the RSA stage).
    Where the pages live is decided by the builder's lang_url_prefix, not by the
    run-wide language."""
    code = str(group.get("language") or "").strip().lower()
    if not code:
        code = "ar" if re.search(r"[؀-ۿ]", str(group.get("name", "")) + str(group.get("theme", ""))) else "en"
    if code in ("", "en") or _LANG_AT_ROOT:
        return ""
    return f"/{code}"


def _short_label(group_name, budget):
    """A prefix that still leaves room for the suffix word. Whole words only —
    a mid-word cut ("Washing Mach Pricing") reads like a bug in the ad."""
    name = re.sub(r"\s*(services|service)\s*$", "", str(group_name or ""), flags=re.I).strip()
    words = name.split()
    while words and len(" ".join(words)) > budget:
        words.pop()
    return " ".join(words) or (name[:budget].strip() or "Service")


# Deterministic templates per script. The English set is the default; the
# Arabic set exists because a fallback in the wrong language is worse than a
# generic one — an Arabic ad group must never show English sitelinks.
_TEMPLATES = {
    "Latin": [
        ("{s} Services",  "What the service covers",    "All brands, same-day slots"),
        ("{s} Pricing",   "Transparent price ranges",   "No hidden charges, ever"),
        ("Customer Reviews", "Real customer stories",   "Rated by local clients"),
        ("{s} FAQs",      "Costs, timing & questions",  "Repair vs replace advice"),
        ("Get a Free Quote", "Free quote before any work", "Call or WhatsApp today"),
    ],
    "Arabic": [
        ("خدمات {s}",      "ما الذي تشمله الخدمة",      "جميع الماركات، مواعيد سريعة"),
        ("أسعار {s}",      "أسعار واضحة بدون مفاجآت",    "لا رسوم خفية إطلاقاً"),
        ("آراء العملاء",   "تجارب عملاء حقيقية",        "تقييمات من عملاء المنطقة"),
        ("أسئلة شائعة",    "التكلفة والوقت والأعطال",    "تصليح أم استبدال؟"),
        ("احصل على عرض سعر", "عرض سعر مجاني قبل العمل",  "اتصل أو واتساب الآن"),
    ],
}


def script_of(text):
    t = str(text or "")
    if re.search(r"[؀-ۿ]", t):
        return "Arabic"
    return "Latin"


def fallback_set(group_name, theme, base_url):
    """Deterministic, always-valid sitelinks in the ad group's own script."""
    script = script_of(f"{group_name} {theme}")
    rows = _TEMPLATES.get(script, _TEMPLATES["Latin"])
    out = []
    for (t_tpl, d1, d2), (anchor, _why) in zip(rows, ANCHORS):
        # room for the suffix word, so the label is never cut mid-word
        budget = TEXT_MAX - (len(t_tpl.replace("{s}", "")) or 0)
        text = t_tpl.format(s=_short_label(group_name, max(budget, 6))).strip()
        out.append({
            "text": text[:TEXT_MAX],
            "desc1": d1[:DESC_MAX],
            "desc2": d2[:DESC_MAX],
            "url": f"{base_url}#{anchor}",
            "anchor": anchor,
            "source": f"fallback:{script.lower()}",
        })
    return out


SYSTEM = (
    "You write Google Ads sitelinks. You obey character limits exactly and "
    "return valid JSON only. Never use exclamation marks, ALL CAPS words, or "
    "claims you cannot prove."
)


def build_prompt(groups, urls, pages):
    lines = []
    for g in groups:
        name = g.get("name", "")
        kws = ", ".join(k.get("keyword", "") for k in (g.get("keywords") or [])[:6])
        lines.append(f'- AD GROUP: "{name}"\n  theme: {g.get("theme", "")[:160]}\n  keywords: {kws}')
    lang_rule = (f"\nWRITE EVERY STRING IN {LANG_NAME.upper()} — this account sells in "
                 f"{LANG_NAME}. Character limits still apply, counted in characters."
                 if LANG_NAME else "")
    return f"""Write one sitelink set for EACH ad group below.

Each set has exactly 5 sitelinks, in this order, matching the anchors that
already exist on the landing page:
  1. services  — what the service covers
  2. pricing   — price range / what drives cost
  3. reviews   — customer proof
  4. faq       — common questions
  5. contact   — booking or free quote

HARD LIMITS — count every character including spaces:
- "text"  (the blue link line): MAXIMUM {TEXT_MAX} characters
- "desc1" and "desc2":          MAXIMUM {DESC_MAX} characters EACH
Going one character over makes the asset invalid, so aim for {TEXT_MAX - 4}-{TEXT_MAX}
and {DESC_MAX - 5}-{DESC_MAX} and recount before you answer.

RULES:
- Make the copy specific to THAT ad group's service — "Washer Repair Pricing",
  never a generic "Pricing". The link text should read naturally next to the ad.
- desc1 and desc2 must both be present and say different things: one concrete
  detail (parts, brands, price entry point, response time), one reassurance.
- No exclamation marks, no ALL CAPS, no "best/#1/cheapest" claims.
- No phone numbers, no URLs inside the text.{lang_rule}

AD GROUPS:
{chr(10).join(lines)}

Return ONLY this JSON:
{{"sets": [{{"ad_group": "exact ad group name",
  "sitelinks": [{{"text": "...", "desc1": "...", "desc2": "..."}}, ... 5 total]}}]}}"""


def ask_claude(groups, urls, pages):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ℹ️ ANTHROPIC_API_KEY missing — deterministic sitelinks only.")
        return {}
    try:
        import anthropic
    except ImportError:
        print("ℹ️ anthropic package unavailable — deterministic sitelinks only.")
        return {}
    prompt = build_prompt(groups, urls, pages)
    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=MODEL, max_tokens=6000, system=SYSTEM,
            messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in resp.content if b.type == "text")
        m = re.search(r"\{.*\}", text, re.S)
        data = json.loads(m.group(0) if m else text)
    except Exception as e:
        print(f"⚠️ Sitelink copy call failed ({str(e)[:80]}) — deterministic fallback.")
        return {}
    out = {}
    for s in data.get("sets", []):
        name = str(s.get("ad_group", "")).strip()
        if name:
            out[name] = s.get("sitelinks", [])
    return out


def main():
    strategy = load_json(STRATEGY, {})
    groups = strategy.get("ad_groups") or []
    pages = strategy.get("landing_pages") or []
    if not groups:
        print("ℹ️ No ad groups in the strategy — sitelink stage skipped.")
        return

    urls = final_urls_by_group()
    base_site = WEBSITE_URL or "https://REPLACE-WITH-YOUR-DOMAIN.com"
    copy_by_group = ask_claude(groups, urls, pages)

    rows, payload = [], []
    n_model = n_fixed = 0
    for g in groups:
        name = g.get("name", "")
        _slug = slug_for(name, pages)
        _pfx = lang_prefix_for(g)
        base = urls.get(name) or (f"{base_site}{_pfx}/{_slug}/" if _slug else f"{base_site}{_pfx}/")
        base = base.rstrip("/")
        # an ad group with no landing page falls back to the site root — keep the
        # trailing slash so the anchor reads "https://site.com/#pricing", not
        # "https://site.com#pricing"
        if re.match(r"^https?://[^/]+$", base):
            base += "/"
        proposed = copy_by_group.get(name) or []
        fallback = fallback_set(name, g.get("theme", ""), base)

        links = []
        for i, (anchor, _why) in enumerate(ANCHORS):
            cand = proposed[i] if i < len(proposed) and isinstance(proposed[i], dict) else {}
            text, d1, d2 = (str(cand.get("text", "")).strip(),
                            str(cand.get("desc1", "")).strip(),
                            str(cand.get("desc2", "")).strip())
            # Both description lines must be valid or Google shows neither —
            # so an over-long line demotes the whole sitelink to the template.
            if _fits(text, TEXT_MAX) and _fits(d1, DESC_MAX) and _fits(d2, DESC_MAX):
                links.append({"text": text, "desc1": d1, "desc2": d2,
                              "url": f"{base}#{anchor}", "anchor": anchor, "source": "model"})
                n_model += 1
            else:
                links.append(fallback[i])
                n_fixed += 1

        payload.append({"ad_group": name, "campaign": g.get("campaign", ""),
                        "final_url_base": base, "sitelinks": links})
        for l in links:
            rows.append({
                "Campaign": g.get("campaign", ""),
                "Ad Group": name,
                "Sitelink Text": l["text"],
                "Description Line 1": l["desc1"],
                "Description Line 2": l["desc2"],
                "Final URL": l["url"],
            })

    with open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Campaign", "Ad Group", "Sitelink Text",
                                          "Description Line 1", "Description Line 2",
                                          "Final URL"])
        w.writeheader()
        w.writerows(rows)
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump({"sitelink_sets": payload}, f, indent=2, ensure_ascii=False)

    over = [r for r in rows if _len(r["Sitelink Text"]) > TEXT_MAX
            or _len(r["Description Line 1"]) > DESC_MAX
            or _len(r["Description Line 2"]) > DESC_MAX]
    print(f"✅ Sitelinks: {len(rows)} across {len(payload)} ad groups "
          f"({n_model} written by the model, {n_fixed} from the safe template)")
    print(f"   anchors: {', '.join('#' + a for a, _ in ANCHORS)}")
    print(f"   → {CSV_OUT} (Editor import) + {JSON_OUT} (API push)")
    if over:
        print(f"❌ {len(over)} rows still exceed a limit — this should be impossible; "
              f"first offender: {over[0]}")
    if not WEBSITE_URL:
        print("   ⚠️ WEBSITE_URL not set — URLs use a placeholder domain; set it "
              "before importing or pushing.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                       # never sink the pipeline
        print(f"⚠️ Sitelink stage error (pipeline continues): {e}")
        sys.exit(0)
