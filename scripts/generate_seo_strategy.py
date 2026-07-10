"""
generate_seo_strategy.py  (STAGE 3-SEO — website-builder inputs generator)
---------------------------------------------------------------------------
Runs INSTEAD OF (or alongside) the Google Ads stage when research_type is
"seo" or "both". Same shared pipeline (Stage 1 pull → Stage 2.5 scoring),
different lens: SEO / content strategy for the AI website builder.

UNIVERSAL: services, ecommerce, anything — business context via env only.

WHAT IT PRODUCES (one Claude call, ~$0.15-0.30):
  website_builder_inputs.json — one block per builder mode, in the EXACT
  shape of that mode's workflow inputs:
    - mode4_cluster (PRIMARY FOCUS): main_topic + problem_clusters string +
      full cluster architecture — pillar keyword, per-cluster keyword sets,
      conversational/AI-overview/voice/local questions WITH answer angles,
      entities to mention, funnel stage. SEO-cannibalization guard: every
      keyword belongs to exactly ONE cluster (Python-enforced).
    - mode3_full_website: which services deserve pages (search-demand-backed
      services_mode3 list — no page for a service nobody searches)
    - mode2_services_hub: main_service + sub_services
    - mode5_pseo: cities detected in the data ranked by demand + query patterns
  seo_content_plan.md — human-readable content plan.

AHREFS/SEMRUSH-STYLE METRICS (Python, free — computed per keyword):
    kd_proxy (0-100)   0.6*competition_index + 0.4*bid-pressure — advertiser
                       demand is the honest difficulty signal
    funnel             TOFU / MOFU / BOFU
    ai_overview_prone  question/informational intent — likely to be answered
                       by AI Overviews; target with direct-answer content

Env: ANTHROPIC_API_KEY, BUSINESS_NAME, NICHE_DESCRIPTION, TARGET_LOCATION
Optional: CLAUDE_MODEL (claude-sonnet-5), CLAUDE_EFFORT (medium),
          MAX_SEO_CLUSTERS (8)

Input : scored_keywords.json
Output: website_builder_inputs.json, seo_content_plan.md
"""

import os
import re
import sys
import json

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

INPUT_FILE = "scored_keywords.json"
JSON_OUT = "website_builder_inputs.json"
MD_OUT = "seo_content_plan.md"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")
MAX_CLUSTERS = int(os.environ.get("MAX_SEO_CLUSTERS", "8"))

BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()


# ══════════════════════════════════════════════════════════════════════════
# Robust JSON parsing (same 4-pass repair as the ads stage)
# ══════════════════════════════════════════════════════════════════════════

def _repair_control_chars(s):
    out, in_str, esc = [], False, False
    for ch in s:
        if esc:
            out.append(ch); esc = False
        elif ch == '\\':
            out.append(ch); esc = True
        elif ch == '"':
            out.append(ch); in_str = not in_str
        elif in_str and ch == '\n':
            out.append('\\n')
        elif in_str and ch == '\r':
            out.append('\\r')
        elif in_str and ch == '\t':
            out.append('\\t')
        else:
            out.append(ch)
    return ''.join(out)


def _escape_inner_quotes(s):
    out, in_str = [], False
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if not in_str:
            if ch == '"':
                in_str = True
            out.append(ch)
        else:
            if ch == '\\' and i + 1 < n:
                out.append(ch); out.append(s[i + 1]); i += 1
            elif ch == '"':
                j = i + 1
                while j < n and s[j] in ' \t\r\n':
                    j += 1
                if j >= n or s[j] in ',}]:':
                    in_str = False
                    out.append(ch)
                else:
                    out.append('\\"')
            else:
                out.append(ch)
        i += 1
    return ''.join(out)


def parse_json_robust(text):
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find('{'), text.rfind('}') + 1
    if start == -1 or end == 0:
        raise json.JSONDecodeError("no JSON object found", text, 0)
    text = text[start:end]
    for fixer in (lambda t: t,
                  _repair_control_chars,
                  lambda t: _escape_inner_quotes(_repair_control_chars(t)),
                  lambda t: re.sub(r',\s*([}\]])', r'\1',
                                   _escape_inner_quotes(_repair_control_chars(t)))):
        try:
            return json.loads(fixer(text))
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("unrecoverable JSON", text, 0)


# ══════════════════════════════════════════════════════════════════════════
# Ahrefs-style metrics (Python — free, deterministic)
# ══════════════════════════════════════════════════════════════════════════

BOFU_TOKENS = {"price", "prices", "cost", "quote", "hire", "book", "buy", "order",
               "near", "emergency", "urgent", "installation", "install", "repair",
               "service", "services", "company", "contractor", "cheap", "affordable"}
MOFU_TOKENS = {"best", "top", "vs", "compare", "comparison", "review", "reviews",
               "companies", "brands", "rated", "recommended"}


def tokens_of(s):
    return re.findall(r"[^\W_]+", str(s).lower(), re.UNICODE)


def enrich(k):
    """Attach kd_proxy / funnel / ai_overview_prone to a scored keyword."""
    comp = k.get("competition_index") or 0
    bid = float(k.get("high_top_bid") or 0)
    k["kd_proxy"] = round(min(100, 0.6 * comp + 0.4 * min(100, bid * 20)))
    toks = set(tokens_of(k["keyword"]))
    intent = k.get("intent", "")
    if intent in ("question", "informational"):
        k["funnel"] = "TOFU"
    elif toks & BOFU_TOKENS or intent == "transactional":
        k["funnel"] = "BOFU"
    elif toks & MOFU_TOKENS:
        k["funnel"] = "MOFU"
    else:
        k["funnel"] = "MOFU"
    k["ai_overview_prone"] = intent in ("question", "informational") or "voice" in k.get("flags", [])
    return k


# ══════════════════════════════════════════════════════════════════════════
# Prompt
# ══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""You are a senior SEO content strategist and information
architect for an AI website builder. You receive pre-scored keyword data
(real Google Keyword Planner numbers with kd (difficulty proxy 0-100) and
funnel stage). You serve ANY business type — services, ecommerce, B2B —
never assume an industry beyond the given context.

Your outputs feed FOUR website-generator modes. Return ONLY a JSON object:

{{
  "mode4_cluster": {{
    "main_topic": "the pillar topic (drives the pillar page)",
    "pillar_keyword_id": 12,
    "clusters": [
      {{
        "cluster_name": "short problem/topic name",
        "primary_keyword_id": 5,
        "keyword_ids": [5, 8, 13],
        "funnel": "TOFU|MOFU|BOFU",
        "questions": [
          {{"q": "a real conversational question a customer asks (AI-overview / voice style)",
            "answer_angle": "one sentence: exactly how the content should answer to win the snippet/AI overview",
            "type": "conversational|voice|paa|local"}}
        ],
        "entities_to_mention": ["specific entities/terms/standards the content must mention for topical authority"]
      }}
    ]
  }},
  "mode3_full_website": {{
    "industry_label": "2-4 words for the site generator",
    "services": ["Title Case Service Page Names, demand-backed"]
  }},
  "mode2_services_hub": {{
    "main_service": "the umbrella service",
    "sub_services": ["6-10 Title Case sub services"]
  }},
  "mode5_pseo": {{
    "cities_in_data": [{{"city": "name", "keyword_ids": [..]}}],
    "recommended_city_targets": ["cities worth pSEO pages, best first"],
    "notes": "1-2 sentences on the local landscape"
  }},
  "excluded_ids": [4],
  "notes": "2-3 sentences: overall SEO strategy rationale"
}}

HARD RULES:
1. MODE 4 IS THE PRIORITY. 3-{MAX_CLUSTERS} clusters — the COUNT COMES FROM
   THE DATA (distinct problems/subtopics actually visible in the keywords).
   Never pad. main_topic = the highest-combined-volume theme.
2. SEO CANNIBALIZATION GUARD: every keyword id in AT MOST one cluster.
   Cluster themes must be mutually exclusive — one search query should map
   to exactly one page. primary_keyword_id is that page's #1 target and
   must appear in its keyword_ids.
3. QUESTIONS (your unique value): 4-8 per cluster. NEW text — the way real
   customers phrase it to Google/AI assistants ("how much does X cost in
   {TARGET_LOCATION or 'the area'}", "which X is best for..."). Cover:
   conversational, voice, PAA-style, and local variants. Each question gets
   an answer_angle telling the content writer HOW to win the AI overview /
   featured snippet (lead with the number, give the range, name the
   standard, etc.).
4. mode3 services: ONLY services with visible search demand in the data —
   if nobody searches it, it doesn't get a page. Order by demand.
5. mode5: detect city/area names present in the keywords (any language).
   If none beyond the target location, say so in notes.
6. EXCLUDE ids that are pure junk/competitor brands/irrelevant.
7. Reference provided keywords ONLY by numeric id. Questions/services/names
   are new text — write them fully.
8. Match the searchers' language(s): if keywords are Arabic/mixed, questions
   and services must cover those languages too.
9. cluster_name: plain text ONLY — NEVER use commas, colons, pipes or
   slashes inside a cluster name (they break the downstream page parser).
   Keep each name under 60 characters.
10. NO cluster may have the same name/theme as main_topic — the pillar page
   already covers it. Clusters are its DISTINCT subtopics only.
"""


def build_user_prompt(keywords):
    lines = []
    for k in keywords:
        flags = ",".join(k.get("flags", [])) or "-"
        lines.append(
            f"{k['id']}|{k['keyword']}|vol:{k['avg_monthly_searches']}"
            f"|kd:{k['kd_proxy']}|{k['funnel']}"
            f"|{k.get('trend', 'UNKNOWN')}|{k.get('intent', '?')}|{flags}"
        )
    header = (
        f"BUSINESS: {BUSINESS_NAME or '(not provided)'}\n"
        f"NICHE: {NICHE_DESCRIPTION or '(infer from keywords)'}\n"
        f"TARGET LOCATION: {TARGET_LOCATION or '(not local)'}\n\n"
        f"KEYWORDS ({len(lines)} rows — format: id|keyword|volume|kd|funnel|trend|intent|flags):\n"
    )
    return header + "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# Post-validation
# ══════════════════════════════════════════════════════════════════════════

def expand_kw(k):
    return {
        "keyword": k["keyword"],
        "volume": k["avg_monthly_searches"],
        "kd": k["kd_proxy"],
        # Ahrefs/SEMrush-style extras: CPC shows commercial value of ranking,
        # peak_months drives seasonal content scheduling.
        "cpc_low": k.get("low_top_bid", 0),
        "cpc_high": k.get("high_top_bid", 0),
        "funnel": k["funnel"],
        "intent": k.get("intent", ""),
        "trend": k.get("trend", ""),
        "peak_months": k.get("peak_months", ""),
        "ai_overview_prone": k["ai_overview_prone"],
        "flags": k.get("flags", []),
    }


def _safe_page_name(s):
    """Cluster names travel inside a comma-separated 'Topic :: a, b, c'
    string that Mode 4 splits on commas — a comma (or ::/|) INSIDE a name
    used to shatter it into bogus half-name pages. Strip those chars.
    Matching downstream is unaffected: it normalizes to a-z0-9 anyway."""
    s = str(s).replace("::", " ").replace("|", " ").replace(",", " ")
    return re.sub(r"\s+", " ", s).strip()


def _norm_name(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def validate(raw, by_id):
    m4 = raw.get("mode4_cluster") or {}
    seen = set()
    clusters = []
    for c in (m4.get("clusters") or [])[:MAX_CLUSTERS]:
        ids = []
        for i in c.get("keyword_ids", []):
            try:
                i = int(i)
            except (TypeError, ValueError):
                continue
            if i in by_id and i not in seen:  # cannibalization guard
                ids.append(i); seen.add(i)
        if not ids:
            continue
        try:
            prim = int(c.get("primary_keyword_id"))
        except (TypeError, ValueError):
            prim = ids[0]
        if prim not in ids:
            prim = ids[0]
        questions = []
        for q in c.get("questions", [])[:8]:
            if q.get("q"):
                questions.append({
                    "q": str(q["q"]).strip(),
                    "answer_angle": str(q.get("answer_angle", "")).strip(),
                    "type": q.get("type", "conversational"),
                })
        clusters.append({
            "cluster_name": str(c.get("cluster_name", "Cluster")).strip()[:80],
            "funnel": c.get("funnel", "MOFU"),
            "primary_keyword": expand_kw(by_id[prim]),
            "keywords": [expand_kw(by_id[i]) for i in ids],
            "total_volume": sum(by_id[i]["avg_monthly_searches"] for i in ids),
            "questions": questions,
            "entities_to_mention": [str(e).strip() for e in c.get("entities_to_mention", []) if str(e).strip()],
        })

    try:
        pillar_id = int(m4.get("pillar_keyword_id"))
    except (TypeError, ValueError):
        pillar_id = None
    pillar = expand_kw(by_id[pillar_id]) if pillar_id in by_id else None

    # Highest-opportunity clusters first — the builder generates pages in
    # this order, so the money pages exist even if a run stops early.
    clusters.sort(key=lambda c: -c["total_volume"])

    main_topic = str(m4.get("main_topic", "")).strip()

    # Page list for Mode 4's "Topic :: page1, page2" parser. Names are
    # comma-sanitized, and a cluster that duplicates main_topic gets no
    # separate page (the pillar targets that query — two pages competing
    # for one query is self-cannibalization). Its questions still ride in
    # clusters[] where the builder's pillar generator can pick them up.
    page_names = []
    for c in clusters:
        n = _safe_page_name(c["cluster_name"])
        if n and _norm_name(n) != _norm_name(main_topic):
            page_names.append(n)
    if not page_names:
        page_names = [_safe_page_name(c["cluster_name"]) for c in clusters
                      if _safe_page_name(c["cluster_name"])]
    page_names = list(dict.fromkeys(page_names))

    mode4 = {
        "workflow_inputs": {
            "main_topic": main_topic,
            "problem_clusters": f"{main_topic or 'Guide'} :: " + ", ".join(page_names),
        },
        "pillar_keyword": pillar,
        "clusters": clusters,
    }

    m3 = raw.get("mode3_full_website") or {}
    services = [str(s).strip() for s in m3.get("services", []) if str(s).strip()]
    mode3 = {
        "workflow_inputs": {
            "industry": str(m3.get("industry_label", NICHE_DESCRIPTION[:40])).strip(),
            "services_mode3": ", ".join(services),
        },
        "services": services,
    }

    m2 = raw.get("mode2_services_hub") or {}
    subs = [str(s).strip() for s in m2.get("sub_services", []) if str(s).strip()][:10]
    mode2 = {
        "workflow_inputs": {
            "main_service": str(m2.get("main_service", "")).strip(),
            "sub_services": ", ".join(subs),
        },
    }

    m5 = raw.get("mode5_pseo") or {}
    cities = []
    for c in m5.get("cities_in_data", []):
        ids = [int(i) for i in c.get("keyword_ids", [])
               if str(i).lstrip("-").isdigit() and int(i) in by_id]
        if c.get("city"):
            cities.append({
                "city": str(c["city"]).strip(),
                "keywords": [expand_kw(by_id[i]) for i in ids],
                "total_volume": sum(by_id[i]["avg_monthly_searches"] for i in ids),
            })
    cities.sort(key=lambda c: -c["total_volume"])
    mode5 = {
        "cities_in_data": cities,
        "recommended_city_targets": [str(x).strip() for x in m5.get("recommended_city_targets", [])],
        "notes": str(m5.get("notes", "")).strip(),
    }

    return mode4, mode3, mode2, mode5


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is missing.")
        sys.exit(1)
    if not os.path.exists(INPUT_FILE):
        print(f"❌ {INPUT_FILE} not found — run score_keywords.py first.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # SEO wants EVERYTHING the ads run rejects: questions and informational
    # keywords are content gold. Take kept_for_ai + all question/informational.
    keywords = [enrich(k) for k in data["keywords"]
                if k.get("kept_for_ai")
                or k.get("intent") in ("question", "informational")]
    by_id = {k["id"]: k for k in keywords}

    print(f"SEO strategy: {len(keywords)} keywords "
          f"(incl. {sum(1 for k in keywords if k['funnel'] == 'TOFU')} TOFU / "
          f"{sum(1 for k in keywords if k['ai_overview_prone'])} AI-overview-prone) → {MODEL} (effort={EFFORT})")

    client = anthropic.Anthropic()
    user_prompt = build_user_prompt(keywords)
    raw = None
    text = ""
    last_err = ""
    for attempt in range(2):
        _p = user_prompt if attempt == 0 else user_prompt + \
            "\n\nIMPORTANT: your previous response was not valid JSON. Return ONLY the JSON object."
        with client.messages.stream(
            model=MODEL,
            max_tokens=28000,
            output_config={"effort": EFFORT},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _p}],
        ) as stream:
            response = stream.get_final_message()
        text = "".join(b.text for b in response.content if b.type == "text")
        if not text.strip():
            print(f"⚠️ Attempt {attempt + 1}: empty text (stop_reason={response.stop_reason}); retrying...")
            continue
        try:
            raw = parse_json_robust(text)
            break
        except json.JSONDecodeError as e:
            last_err = str(e)
            print(f"⚠️ Attempt {attempt + 1}: JSON parse failed ({e})")

    if raw is None:
        with open("seo_strategy_raw.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"❌ Could not get valid JSON: {last_err}. Raw saved.")
        sys.exit(1)

    mode4, mode3, mode2, mode5 = validate(raw, by_id)

    out = {
        "business": {"name": BUSINESS_NAME, "niche": NICHE_DESCRIPTION,
                     "location": TARGET_LOCATION},
        "model_used": MODEL,
        "notes": str(raw.get("notes", "")).strip(),
        "mode4_cluster": mode4,
        "mode3_full_website": mode3,
        "mode2_services_hub": mode2,
        "mode5_pseo": mode5,
        # Ahrefs-style flat metrics table (every keyword, sorted by volume)
        "keyword_metrics": sorted(
            (expand_kw(k) for k in keywords),
            key=lambda x: -x["volume"]),
    }
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # ── Markdown content plan ──
    md = [f"# SEO Content Plan — {BUSINESS_NAME or 'Untitled'}\n"]
    if NICHE_DESCRIPTION:
        md.append(f"*{NICHE_DESCRIPTION}* — {TARGET_LOCATION}\n")
    md.append(f"## 🏛️ Mode 4 — Cluster Architecture (PRIMARY)")
    md.append(f"**main_topic:** `{mode4['workflow_inputs']['main_topic']}`")
    md.append(f"**problem_clusters:** `{mode4['workflow_inputs']['problem_clusters']}`")
    if mode4["pillar_keyword"]:
        p = mode4["pillar_keyword"]
        md.append(f"**Pillar keyword:** {p['keyword']} ({p['volume']}/mo, KD {p['kd']})")
    md.append("")
    for c in mode4["clusters"]:
        md.append(f"### 📄 {c['cluster_name']}  `{c['funnel']}`")
        md.append(f"- Primary: **{c['primary_keyword']['keyword']}** "
                  f"({c['primary_keyword']['volume']}/mo, KD {c['primary_keyword']['kd']}) "
                  f"| cluster volume: {c['total_volume']}/mo | {len(c['keywords'])} keywords")
        md.append(f"- Keywords: " + ", ".join(k["keyword"] for k in c["keywords"]))
        if c["questions"]:
            md.append(f"- Questions to answer (AI-overview targets):")
            for q in c["questions"]:
                md.append(f"    - **{q['q']}** `{q['type']}` — _{q['answer_angle']}_")
        if c["entities_to_mention"]:
            md.append(f"- Entities: " + ", ".join(c["entities_to_mention"]))
        md.append("")
    md.append("## 🌐 Mode 3 — Full Website Services (demand-backed)")
    md.append(f"`services_mode3` = {mode3['workflow_inputs']['services_mode3']}\n")
    md.append("## 🗂️ Mode 2 — Services Hub")
    md.append(f"main_service: **{mode2['workflow_inputs']['main_service']}** | "
              f"sub_services: {mode2['workflow_inputs']['sub_services']}\n")
    md.append("## 🏙️ Mode 5 — pSEO Cities")
    if mode5["cities_in_data"]:
        for c in mode5["cities_in_data"]:
            md.append(f"- **{c['city']}** — {c['total_volume']}/mo across {len(c['keywords'])} keywords")
    md.append(f"Recommended targets: {', '.join(mode5['recommended_city_targets']) or '—'}")
    if mode5["notes"]:
        md.append(f"_{mode5['notes']}_\n")
    if out["notes"]:
        md.append(f"**Strategy notes:** {out['notes']}")
    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    usage = getattr(response, "usage", None)
    if usage:
        cost = usage.input_tokens * 3 / 1e6 + usage.output_tokens * 15 / 1e6
        print(f"   Tokens: {usage.input_tokens} in / {usage.output_tokens} out ≈ ${cost:.3f} this run")
    nq = sum(len(c["questions"]) for c in mode4["clusters"])
    print(f"✅ Mode4: {len(mode4['clusters'])} clusters, {nq} AI-overview questions | "
          f"Mode3: {len(mode3['services'])} services | Mode5: {len(mode5['cities_in_data'])} cities")
    print(f"✅ Saved: {JSON_OUT}, {MD_OUT}")


if __name__ == "__main__":
    main()
