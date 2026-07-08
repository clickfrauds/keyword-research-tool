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

def main():
    # Graceful failure instead of a traceback when Stage 3 didn't produce output
    if not os.path.exists(STRATEGY_FILE):
        print(f"❌ {STRATEGY_FILE} not found — Stage 3 (analyze_with_claude.py) "
              f"failed or was skipped. Fix that stage first; skipping report generation.")
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
