"""
generate_reports.py
--------------------
STAGE 4 of the pipeline (runs after analyze_with_claude.py).

Takes keyword_strategy.json (+ clustered_keywords.json for summary stats)
and renders two client-ready deliverables:

    keyword_strategy_report.html   - styled, self-contained (no external
                                      CSS/JS/fonts), safe to open directly,
                                      email as an attachment, or embed in
                                      an iframe.
    keyword_strategy_targets.csv   - the Google Ads target list, ready to
                                      open in Excel / import elsewhere.

Env vars (same ones already used in analyze_with_claude.py):
    BUSINESS_NAME
    NICHE_DESCRIPTION
    TARGET_LOCATION
"""

import os
import csv
import json
import html
from datetime import datetime, timezone

STRATEGY_FILE = "keyword_strategy.json"
CLUSTERS_FILE = "clustered_keywords.json"
HTML_OUTPUT = "keyword_strategy_report.html"
CSV_OUTPUT = "keyword_strategy_targets.csv"

BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "").strip()
NICHE_DESCRIPTION = os.environ.get("NICHE_DESCRIPTION", "").strip()
TARGET_LOCATION = os.environ.get("TARGET_LOCATION", "").strip()


# ============================================================
# small helpers
# ============================================================

def esc(value):
    """Escape a value for safe HTML embedding, treating None as empty."""
    return html.escape(str(value if value is not None else ""), quote=True)


TREND_STYLES = {
    "GROWING":   ("#0f6b3f", "#dcf2e3", "▲ Growing"),
    "DECLINING": ("#9c2b1f", "#fbe2de", "▼ Declining"),
    "SEASONAL":  ("#0b5d5a", "#e3f0ef", "◐ Seasonal"),
    "STABLE":    ("#57534e", "#ece9e4", "● Stable"),
    "UNKNOWN":   ("#78716c", "#f1efec", "? Unknown"),
}

PRIORITY_STYLES = {
    "high":   ("#92400e", "#fef0dc"),
    "medium": ("#6b5a3a", "#f2ede0"),
    "low":    ("#57534e", "#ece9e4"),
}


def trend_badge(trend):
    trend = (trend or "UNKNOWN").upper()
    color, bg, label = TREND_STYLES.get(trend, TREND_STYLES["UNKNOWN"])
    return f'<span class="badge" style="color:{color};background:{bg}">{esc(label)}</span>'


def priority_badge(priority):
    priority = (priority or "medium").lower()
    color, bg = PRIORITY_STYLES.get(priority, PRIORITY_STYLES["medium"])
    return f'<span class="badge" style="color:{color};background:{bg}">{esc(priority.upper())}</span>'


def load_json(path, required=True):
    if not os.path.exists(path):
        if required:
            raise FileNotFoundError(f"{path} not found — run the earlier pipeline stages first.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# HTML section renderers
# ============================================================

def render_ads_targets(targets):
    if not targets:
        return "<p class='empty'>No Google Ads targets generated.</p>"
    cards = []
    for t in targets:
        keywords = ", ".join(esc(k) for k in t.get("recommended_keywords") or [])
        seasonal = t.get("seasonal_schedule")
        seasonal_html = ""
        if seasonal and str(seasonal).strip().lower() not in ("", "null", "none"):
            seasonal_html = f"<div class='meta-line'>Active window: <strong>{esc(seasonal)}</strong></div>"
        cards.append(f"""
        <div class="card">
          <div class="card-head">
            <h3>{esc(t.get('cluster_topic'))}</h3>
            <div class="badges">{priority_badge(t.get('priority'))}{trend_badge(t.get('trend'))}</div>
          </div>
          <div class="meta-line">Intent: <strong>{esc(t.get('intent'))}</strong> &middot; Match type: <strong>{esc(t.get('suggested_match_type'))}</strong></div>
          <div class="meta-line">Keywords: {keywords}</div>
          {seasonal_html}
          <p class="reasoning">{esc(t.get('reasoning'))}</p>
        </div>""")
    return "\n".join(cards)


def render_ad_groups(groups):
    """Legacy v1/v2 shape only (keywords = list of strings)."""
    if not groups:
        return "<p class='empty'>No ad groups generated.</p>"
    cards = []
    for g in groups:
        keywords = ", ".join(esc(k) for k in g.get("keywords") or [])
        cards.append(f"""
        <div class="card">
          <h3>{esc(g.get('ad_group_name'))}</h3>
          <div class="meta-line">Keywords: {keywords}</div>
          <div class="ad-preview">
            <div class="ad-headline">{esc(g.get('suggested_headline'))}</div>
            <div class="ad-description">{esc(g.get('suggested_description'))}</div>
          </div>
        </div>""")
    return "\n".join(cards)


def render_v3_campaigns(strategy):
    """v3 shape: campaigns → ad groups with rich keyword dicts, expansions,
    negative-keyword siloing."""
    campaigns = strategy.get("campaigns", [])
    groups = strategy.get("ad_groups", [])
    blocks = []
    for c in campaigns:
        cgroups = [g for g in groups if g.get("campaign") == c.get("name")]
        cards = []
        for g in cgroups:
            kws = g.get("keywords") or []
            kw_html = ", ".join(
                f"{esc(k.get('keyword'))} <span class='kw-vol'>({k.get('avg_monthly_searches', 0)})</span>"
                for k in kws
            )
            exp = g.get("intent_expansion_keywords") or []
            exp_html = ""
            if exp:
                chips = "".join(f'<span class="chip">{esc(e)}</span>' for e in exp)
                exp_html = f"<div class='meta-line'>🆕 Intent expansions:</div><div class='chip-wrap'>{chips}</div>"
            neg = g.get("negative_keywords") or []
            neg_html = ""
            if neg:
                neg_html = ("<div class='meta-line neg-line'>🚫 Negatives (anti-cannibalization): "
                            + esc(", ".join(neg)) + "</div>")
            cards.append(f"""
        <div class="card">
          <div class="card-head">
            <h3>{esc(g.get('name'))}</h3>
            <div class="badges">{priority_badge(g.get('priority'))}<span class="badge intent-badge">{esc((g.get('match_type') or 'phrase').upper())}</span></div>
          </div>
          <p class="reasoning">{esc(g.get('theme'))}</p>
          <div class="meta-line">Volume: <strong>{g.get('total_volume', 0)}/mo</strong> &middot; Avg score: <strong>{g.get('avg_score', 0)}</strong> &middot; {len(kws)} keywords</div>
          <div class="meta-line">Keywords: {kw_html}</div>
          {exp_html}
          {neg_html}
        </div>""")
        blocks.append(f"""
    <div class="campaign-block">
      <div class="campaign-head">📣 Campaign: {esc(c.get('name'))} {priority_badge(c.get('priority'))}</div>
      {''.join(cards)}
    </div>""")
    return "\n".join(blocks) or "<p class='empty'>No campaigns generated.</p>"


def render_negatives_for_existing(strategy):
    nfe = strategy.get("negatives_for_existing_groups") or {}
    if not nfe:
        return ""
    rows = "".join(
        f"<div class='card'><h3>{esc(g)}</h3><div class='meta-line neg-line'>🚫 Add as negatives: {esc(', '.join(terms))}</div></div>"
        for g, terms in nfe.items()
    )
    return f"""
  <section>
    <h2>Negatives for your EXISTING ad groups (2-way siloing)</h2>
    <p class="empty">Add these as negative keywords to your live ad groups so they can't steal the new group's traffic.</p>
    {rows}
  </section>"""


def render_landing_pages(pages):
    if not pages:
        return ""
    cards = []
    for p in pages:
        subs = ", ".join(esc(s) for s in p.get("sub_services", []))
        covers = ", ".join(esc(a) for a in p.get("ad_groups_covered", []))
        cards.append(f"""
        <div class="card">
          <div class="card-head">
            <h3>{esc(p.get('page_name'))}</h3>
            <span class="badge intent-badge">/{esc(p.get('url_slug'))}/</span>
          </div>
          <div class="meta-line">Main service: <strong>{esc(p.get('service_name'))}</strong> &middot; Industry: {esc(p.get('industry'))}</div>
          <div class="meta-line">Sub-services (page sections): {subs}</div>
          <div class="meta-line">Covers ad groups: {covers}</div>
        </div>""")
    return f"""
  <section>
    <h2>Landing Pages (website generator inputs)</h2>
    {''.join(cards)}
  </section>"""


def render_faqs(faqs):
    if not faqs:
        return "<p class='empty'>No FAQs generated.</p>"
    items = []
    for f in faqs:
        items.append(f"""
        <details class="faq">
          <summary>{esc(f.get('question'))}</summary>
          <p>{esc(f.get('answer'))}</p>
        </details>""")
    return "\n".join(items)


def render_paa(paa):
    if not paa:
        return "<p class='empty'>None generated.</p>"
    chips = "".join(f'<span class="chip">{esc(q)}</span>' for q in paa)
    return f'<div class="chip-wrap">{chips}</div>'


def render_content_briefs(briefs):
    if not briefs:
        return "<p class='empty'>No content briefs generated.</p>"
    cards = []
    for c in briefs:
        cards.append(f"""
        <div class="card">
          <div class="card-head">
            <h3>{esc(c.get('cluster_topic'))}</h3>
            <span class="badge intent-badge">{esc(c.get('target_intent'))}</span>
          </div>
          <p class="reasoning">{esc(c.get('content_angle'))}</p>
        </div>""")
    return "\n".join(cards)


def stat_bar(strategy, clusters_data):
    if strategy.get("campaigns"):  # v3
        groups = strategy.get("ad_groups", [])
        stats = [
            ("Campaigns", len(strategy.get("campaigns", []))),
            ("Ad Groups", len(groups)),
            ("Keywords", sum(len(g.get("keywords") or []) for g in groups)),
            ("Intent Expansions", sum(len(g.get("intent_expansion_keywords") or []) for g in groups)),
            ("Landing Pages", len(strategy.get("landing_pages", []))),
        ]
    else:  # legacy
        stats = [
            ("Ad Targets", len(strategy.get("google_ads_targets", []))),
            ("Ad Groups", len(strategy.get("ad_groups", []))),
            ("FAQs", len(strategy.get("faqs", []))),
            ("Content Briefs", len(strategy.get("content_briefs", []))),
        ]
    if clusters_data:
        stats.insert(0, ("Keywords Analyzed", clusters_data.get("total_deduped_keywords", "—")))
    items = "".join(
        f'<div class="stat"><div class="stat-num">{esc(v)}</div><div class="stat-label">{esc(k)}</div></div>'
        for k, v in stats
    )
    return f'<div class="stat-bar">{items}</div>'


def high_priority_count(targets):
    return sum(1 for t in targets if (t.get("priority") or "").lower() == "high")


def main_sections(strategy):
    """v3 strategies render campaigns + landing pages; legacy strategies keep
    the old sections. Empty sections are hidden instead of showing 'No X'."""
    if strategy.get("campaigns"):  # ── v3 ──
        parts = [f"""
  <section>
    <h2>Campaign &amp; Ad Group Structure</h2>
    {render_v3_campaigns(strategy)}
  </section>"""]
        parts.append(render_negatives_for_existing(strategy))
        parts.append(render_landing_pages(strategy.get("landing_pages", [])))
        voice = strategy.get("voice_search_questions") or []
        if voice:
            chips = "".join(f'<span class="chip">{esc(q)}</span>' for q in voice[:20])
            parts.append(f"""
  <section>
    <h2>Voice-search / question keywords (SEO content, not ads)</h2>
    <div class="chip-wrap">{chips}</div>
  </section>""")
        notes = strategy.get("notes")
        if notes:
            parts.append(f"""
  <section>
    <h2>Strategy Notes</h2>
    <p class="reasoning">{esc(notes)}</p>
  </section>""")
        return "\n".join(p for p in parts if p)

    # ── legacy ──
    parts = [f"""
  <section>
    <h2>Google Ads Target Keywords</h2>
    {render_ads_targets(strategy.get("google_ads_targets", []))}
  </section>

  <section>
    <h2>Suggested Ad Groups</h2>
    {render_ad_groups(strategy.get("ad_groups", []))}
  </section>"""]
    if strategy.get("faqs"):
        parts.append(f"<section><h2>Frequently Asked Questions</h2>{render_faqs(strategy['faqs'])}</section>")
    if strategy.get("people_also_ask"):
        parts.append(f"<section><h2>People Also Ask</h2>{render_paa(strategy['people_also_ask'])}</section>")
    if strategy.get("content_briefs"):
        parts.append(f"<section><h2>Content Briefs</h2>{render_content_briefs(strategy['content_briefs'])}</section>")
    return "\n".join(parts)


# ============================================================
# HTML document
# ============================================================

def render_html(strategy, clusters_data):
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    subtitle_bits = [b for b in [NICHE_DESCRIPTION, TARGET_LOCATION] if b]
    subtitle = " &middot; ".join(esc(b) for b in subtitle_bits)
    targets = strategy.get("google_ads_targets", [])
    hp_count = high_priority_count(targets)

    stamp_html = ""
    if hp_count:
        stamp_html = f'<div class="stamp">{hp_count} HIGH<br>PRIORITY</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(BUSINESS_NAME or 'Keyword Strategy Report')}</title>
<style>
  :root {{
    --ink: #14181c;
    --muted: #6b6560;
    --line: #dcdad3;
    --paper: #fdfcfa;
    --bg: #f6f5f2;
    --accent: #0b5d5a;
    --accent-soft: #e3f0ef;
    --mono: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Menlo, Consolas, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: var(--sans);
    line-height: 1.55;
  }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 36px 20px 70px; }}
  header {{
    position: relative;
    border-bottom: 2px dashed var(--line);
    padding-bottom: 22px;
    margin-bottom: 30px;
  }}
  .eyebrow {{
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 8px;
  }}
  header h1 {{ font-size: 26px; margin: 0 0 6px; }}
  header .subtitle {{ color: var(--muted); font-size: 14px; }}
  header .generated {{ font-family: var(--mono); color: var(--muted); font-size: 11px; margin-top: 12px; }}
  .stamp {{
    position: absolute;
    top: 0;
    right: 0;
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    line-height: 1.3;
    text-align: center;
    color: var(--accent);
    border: 2px solid var(--accent);
    border-radius: 6px;
    padding: 6px 10px;
    transform: rotate(4deg);
  }}
  .stat-bar {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 36px; }}
  .stat {{
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 12px 16px;
    flex: 1;
    min-width: 110px;
    text-align: center;
  }}
  .stat-num {{ font-family: var(--mono); font-size: 20px; font-weight: 700; color: var(--accent); }}
  .stat-label {{ font-size: 11px; color: var(--muted); margin-top: 3px; }}
  section {{ margin-bottom: 40px; }}
  section > h2 {{
    font-family: var(--mono);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    border-bottom: 1px solid var(--line);
    padding-bottom: 9px;
    margin-bottom: 16px;
  }}
  .card {{
    background: var(--paper);
    border: 1px solid var(--line);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 16px 18px;
    margin-bottom: 12px;
  }}
  .card-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap; }}
  .card h3 {{ margin: 0; font-size: 15px; }}
  .badges {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .badge {{ font-family: var(--mono); font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; white-space: nowrap; }}
  .intent-badge {{ background: var(--accent-soft); color: var(--accent); }}
  .meta-line {{ font-size: 13px; color: var(--muted); margin-top: 7px; }}
  .reasoning {{ font-size: 14px; margin-top: 9px; margin-bottom: 0; }}
  .ad-preview {{ margin-top: 11px; background: var(--bg); border: 1px dashed var(--line); border-radius: 6px; padding: 10px 13px; }}
  .ad-headline {{ color: #1a0dab; font-size: 14px; font-weight: 600; }}
  .ad-description {{ color: #4d5156; font-size: 13px; margin-top: 3px; }}
  .faq {{ background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 11px 15px; margin-bottom: 7px; }}
  .faq summary {{ cursor: pointer; font-weight: 600; font-size: 14px; }}
  .faq summary:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
  .faq p {{ font-size: 14px; color: var(--muted); margin: 9px 0 2px; }}
  .chip-wrap {{ display: flex; flex-wrap: wrap; gap: 7px; }}
  .chip {{ background: var(--accent-soft); color: var(--accent); font-size: 12px; padding: 5px 11px; border-radius: 999px; }}
  .empty {{ color: var(--muted); font-style: italic; font-size: 14px; }}
  .campaign-block {{ margin-bottom: 26px; }}
  .campaign-head {{ font-family: var(--mono); font-size: 13px; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
  .kw-vol {{ color: var(--muted); font-size: 11px; }}
  .neg-line {{ color: #9c2b1f; }}
  footer {{ text-align: center; font-family: var(--mono); color: var(--muted); font-size: 11px; margin-top: 56px; }}
  @media (max-width: 480px) {{
    .stamp {{ position: static; display: inline-block; margin-top: 12px; transform: rotate(-1deg); }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="eyebrow">Keyword Strategy Report</div>
    <h1>{esc(BUSINESS_NAME or 'Untitled Business')}</h1>
    <div class="subtitle">{subtitle}</div>
    <div class="generated">Generated {esc(generated_at)}</div>
    {stamp_html}
  </header>

  {stat_bar(strategy, clusters_data)}

  {main_sections(strategy)}

  <footer>SEOblogy &middot; Keyword Strategy Report</footer>

</div>
</body>
</html>
"""


# ============================================================
# CSV export
# ============================================================

def write_csv(strategy):
    targets = strategy.get("google_ads_targets", [])
    with open(CSV_OUTPUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "cluster_topic", "recommended_keywords", "intent",
            "suggested_match_type", "priority", "trend",
            "seasonal_schedule", "reasoning",
        ])
        for t in targets:
            writer.writerow([
                t.get("cluster_topic", ""),
                "; ".join(t.get("recommended_keywords") or []),
                t.get("intent", ""),
                t.get("suggested_match_type", ""),
                t.get("priority", ""),
                t.get("trend", ""),
                t.get("seasonal_schedule") or "",
                t.get("reasoning", ""),
            ])


# ============================================================
# main
# ============================================================

SEO_FILE = "website_builder_inputs.json"


def render_seo_html(seo):
    """Compact self-contained report for SEO runs (research_type=seo)."""
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    m4 = seo.get("mode4_cluster", {})
    m3 = seo.get("mode3_full_website", {})
    m2 = seo.get("mode2_services_hub", {})
    m5 = seo.get("mode5_pseo", {})
    nq = sum(len(c.get("questions", [])) for c in m4.get("clusters", []))

    cluster_cards = []
    for c in m4.get("clusters", []):
        p = c.get("primary_keyword") or {}
        qs = "".join(
            f"<li><strong>{esc(q.get('q'))}</strong> "
            f"<span class='badge intent-badge'>{esc(q.get('type'))}</span>"
            f"<div class='meta-line'>{esc(q.get('answer_angle'))}</div></li>"
            for q in c.get("questions", []))
        kws = ", ".join(f"{esc(k['keyword'])} <span class='kw-vol'>({k['volume']})</span>"
                        for k in c.get("keywords", []))
        ents = ", ".join(esc(e) for e in c.get("entities_to_mention", []))
        cluster_cards.append(f"""
        <div class="card">
          <div class="card-head"><h3>{esc(c.get('cluster_name'))}</h3>
            <span class="badge intent-badge">{esc(c.get('funnel'))}</span></div>
          <div class="meta-line">Primary: <strong>{esc(p.get('keyword'))}</strong>
            ({p.get('volume', 0)}/mo, KD {p.get('kd', '—')}) &middot; cluster volume {c.get('total_volume', 0)}/mo</div>
          <div class="meta-line">Keywords: {kws}</div>
          <ul style="font-size:13px; padding-left:18px; margin:10px 0 0;">{qs}</ul>
          {f"<div class='meta-line'>Entities: {ents}</div>" if ents else ""}
        </div>""")

    cities = "".join(
        f"<div class='meta-line'>• <strong>{esc(c.get('city'))}</strong> — "
        f"{c.get('total_volume', 0)}/mo across {len(c.get('keywords', []))} keywords</div>"
        for c in m5.get("cities_in_data", []))

    services_chips = "".join(f'<span class="chip">{esc(s)}</span>' for s in m3.get("services", []))

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(BUSINESS_NAME or 'SEO Content Plan')}</title>
<style>
 body{{margin:0;background:#f6f5f2;color:#14181c;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.55}}
 .wrap{{max-width:860px;margin:0 auto;padding:36px 20px 70px}}
 h1{{font-size:24px;margin:0 0 4px}} .sub{{color:#6b6560;font-size:13px;margin-bottom:24px}}
 section{{margin-bottom:34px}} section>h2{{font-family:ui-monospace,Consolas,monospace;font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:#6b6560;border-bottom:1px solid #dcdad3;padding-bottom:8px}}
 .card{{background:#fdfcfa;border:1px solid #dcdad3;border-left:3px solid #0b5d5a;border-radius:0 8px 8px 0;padding:15px 17px;margin-bottom:12px}}
 .card h3{{margin:0;font-size:15px}} .card-head{{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}}
 .meta-line{{font-size:13px;color:#6b6560;margin-top:6px}} .kw-vol{{font-size:11px;color:#6b6560}}
 .badge{{font-family:ui-monospace,Consolas,monospace;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px}}
 .intent-badge{{background:#e3f0ef;color:#0b5d5a}}
 .chip{{display:inline-block;background:#e3f0ef;color:#0b5d5a;font-size:12px;padding:5px 11px;border-radius:999px;margin:3px 4px 0 0}}
 .stat-bar{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:30px}}
 .stat{{background:#fdfcfa;border:1px solid #dcdad3;border-radius:8px;padding:11px 15px;flex:1;min-width:105px;text-align:center}}
 .stat b{{display:block;font-family:ui-monospace,Consolas,monospace;font-size:19px;color:#0b5d5a}}
 code{{background:#e3f0ef;padding:2px 7px;border-radius:5px;font-size:12px}}
</style></head><body><div class="wrap">
 <h1>SEO Content Plan — {esc(BUSINESS_NAME or 'Untitled')}</h1>
 <div class="sub">{esc(NICHE_DESCRIPTION)} &middot; {esc(TARGET_LOCATION)} &middot; Generated {esc(generated_at)}</div>
 <div class="stat-bar">
   <div class="stat"><b>{len(m4.get('clusters', []))}</b>Clusters</div>
   <div class="stat"><b>{nq}</b>AI-Overview Questions</div>
   <div class="stat"><b>{len(m3.get('services', []))}</b>Demand-Backed Services</div>
   <div class="stat"><b>{len(m5.get('cities_in_data', []))}</b>Cities Detected</div>
 </div>
 <section><h2>Mode 4 — Cluster Architecture (primary)</h2>
   <div class="meta-line">main_topic: <code>{esc(m4.get('workflow_inputs', {}).get('main_topic'))}</code></div>
   <div class="meta-line" style="margin-bottom:12px">problem_clusters: <code>{esc(m4.get('workflow_inputs', {}).get('problem_clusters'))}</code></div>
   {''.join(cluster_cards)}
 </section>
 <section><h2>Mode 3 — Full Website Services (demand-backed)</h2><div>{services_chips}</div></section>
 <section><h2>Mode 2 — Services Hub</h2>
   <div class="meta-line">main_service: <strong>{esc(m2.get('workflow_inputs', {}).get('main_service'))}</strong></div>
   <div class="meta-line">sub_services: {esc(m2.get('workflow_inputs', {}).get('sub_services'))}</div></section>
 <section><h2>Mode 5 — pSEO Cities</h2>{cities or "<div class='meta-line'>No extra cities detected in the data.</div>"}
   <div class="meta-line">Recommended: {esc(', '.join(m5.get('recommended_city_targets', [])) or '—')}</div></section>
 {f"<section><h2>Strategy Notes</h2><div class='meta-line'>{esc(seo.get('notes'))}</div></section>" if seo.get('notes') else ""}
</div></body></html>"""


def write_seo_csv(seo):
    """Ahrefs-style keyword metrics table."""
    with open(CSV_OUTPUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "volume", "kd", "funnel", "intent",
                    "trend", "ai_overview_prone", "flags"])
        for k in seo.get("keyword_metrics", []):
            w.writerow([k.get("keyword"), k.get("volume"), k.get("kd"),
                        k.get("funnel"), k.get("intent"), k.get("trend"),
                        k.get("ai_overview_prone"), ",".join(k.get("flags", []))])


def main():
    strategy_exists = os.path.exists(STRATEGY_FILE)
    seo_exists = os.path.exists(SEO_FILE)

    if not strategy_exists and seo_exists:
        # SEO-only run (research_type=seo)
        seo = load_json(SEO_FILE, required=True)
        with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
            f.write(render_seo_html(seo))
        write_seo_csv(seo)
        print(f"✅ SEO HTML report saved to {HTML_OUTPUT}")
        print(f"✅ Keyword-metrics CSV saved to {CSV_OUTPUT}")
        return

    if not strategy_exists:
        print(f"❌ Neither {STRATEGY_FILE} nor {SEO_FILE} found — earlier stages "
              f"failed or were skipped. Fix those first; skipping report generation.")
        import sys
        sys.exit(1)

    strategy = load_json(STRATEGY_FILE, required=True)
    clusters_data = load_json(CLUSTERS_FILE, required=False)

    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(render_html(strategy, clusters_data))
    print(f"✅ HTML report saved to {HTML_OUTPUT}")

    write_csv(strategy)
    print(f"✅ CSV export saved to {CSV_OUTPUT}")


if __name__ == "__main__":
    main()
