"""
push_to_google_ads.py  (STAGE 4-PUSH — direct API campaign push)
----------------------------------------------------------------------
The Ads-Editor killer: everything the master CSV carries goes straight
into the target Google Ads account through the API — campaign (Search
only, partners OFF, Manual CPC, PAUSED, presence-only locations), ad
groups, keywords with bids, negatives, RSAs, locations with bid
modifiers, excluded locations, audiences included/excluded.

The manual CSV path STAYS (user requirement): this stage only runs when
PUSH_CUSTOMER_ID is set. Everything reads the same pipeline outputs the
CSV exporter reads — one data source, two delivery doors.

SAFETY MODEL
  PUSH_MODE=validate (default): the entire core mutate runs with
    validate_only=true — Google checks every operation and reports
    errors WITHOUT creating anything. Nothing in the account changes.
  PUSH_MODE=live: one ATOMIC mutate — either the whole campaign lands
    (Paused, so zero spend) or nothing does. Audiences follow as a
    second best-effort pass so an unmatched segment name can never
    sink the core campaign.

PHASES (PUSH_PHASE)
  Ads used to be disapproved as "Destination not working" because the
  Final URL is WEBSITE_URL plus a slug analyze_with_claude.py invented,
  and it was pushed whether or not a page existed there yet — the page
  only appears later, when the website builder consumes the same JSON.
  Pausing does not help; Google reviews the ads either way.

  So the run splits on "carries a URL" rather than "paused vs live":
    structure  budget, campaign, ad groups, keywords, negatives, geo,
               language, audiences. Nothing here has a Final URL, so
               there is nothing to review and nothing to disapprove.
    creative   RSAs and sitelinks, plus the optional enable. Only ever
               pushed once every page answers.

  auto (default) does both at once when the pages are already live, and
  otherwise stops after structure and says which URLs it is waiting on.
  Same command every time — run it again after the site deploys and it
  picks up where it left off. State lands in push_manifest.json.

  PREFLIGHT=off skips the page checks (a staging host unreachable from
  here but fine for Google). ENABLE_CAMPAIGN=yes turns the campaign on
  at the end of the creative phase; without it the campaign stays Paused,
  because enabling spends money and must never be a side effect.

REQUIREMENTS
  - google-ads.yaml equivalents via env (same secrets Stage 1 uses).
  - The OAuth user must have access to PUSH_CUSTOMER_ID; if it's a
    client account under your MCC, set GOOGLE_ADS_LOGIN_CUSTOMER_ID to
    the MCC id.
  - Account currency must match BID_CURRENCY (bids are sent as micros).

Env : PUSH_CUSTOMER_ID (required to run), PUSH_MODE (validate|live),
      PUSH_PHASE (auto|structure|creative), PREFLIGHT (on|off),
      ENABLE_CAMPAIGN (no|yes),
      DAILY_BUDGET (account currency, default 1000),
      GOOGLE_ADS_* client env vars, GOOGLE_ADS_LOGIN_CUSTOMER_ID (MCC)
Input : keyword_strategy.json, rsa_editor.csv?, locations_editor.csv?,
        locations_negative.csv?, audience_plan.json?
Output: google_ads_push_report.md, push_manifest.json (+ log lines)
"""

import os
import re
import sys
import csv
import json
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PUSH_CUSTOMER_ID = "".join(c for c in os.environ.get("PUSH_CUSTOMER_ID", "") if c.isdigit())
PUSH_MODE = os.environ.get("PUSH_MODE", "validate").strip().lower()

# auto      : push structure, and add the creative too if every page answers
# structure : structure only, never the ads (use while the site is being built)
# creative  : the ads/sitelinks for a campaign structure that already exists
PUSH_PHASE = os.environ.get("PUSH_PHASE", "auto").strip().lower()
# Preflight is the whole point; leave it on unless a page is genuinely
# unreachable from here but fine for Google (a firewalled staging host).
PREFLIGHT = os.environ.get("PREFLIGHT", "on").strip().lower() not in ("off", "0", "no", "false")
# Enabling spends money, so it stays opt-in even in the creative phase.
ENABLE_CAMPAIGN = os.environ.get("ENABLE_CAMPAIGN", "no").strip().lower() in ("yes", "1", "true", "on")
DAILY_BUDGET = float(os.environ.get("DAILY_BUDGET", "1000") or 1000)

STRATEGY = "keyword_strategy.json"
REPORT = "google_ads_push_report.md"

report_lines = []


def log(msg):
    print(msg)
    report_lines.append(msg)


def load_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ══════════════════════════════════════════════════════════════════════
# PREFLIGHT + PHASES
#
# The reason ads kept coming back "Destination not working": the Final URL
# is built from WEBSITE_URL plus a slug that analyze_with_claude.py invented,
# and it was pushed whether or not a page existed there yet. The page only
# appears later, when the website builder consumes the same JSON. Two systems
# agreeing by convention, with nothing checking. A paused campaign does not
# help — Google reviews the ads either way.
#
# The split is therefore NOT "paused vs live" but "carries a URL vs does not":
#
#   structure : budget, campaign, ad groups, keywords, negatives, geo,
#               language, audiences. None of it has a Final URL, so there is
#               nothing for Google to review and nothing to disapprove.
#   creative  : RSAs and sitelinks — the only things with URLs — plus the
#               optional enable. Pushed once every page answers.
#
# PUSH_PHASE=auto (default) does both in one go when the pages are already
# live, and otherwise stops after structure and says so. Same command every
# time; it just declines to push ads at pages that are not there.
# ══════════════════════════════════════════════════════════════════════

MANIFEST = "push_manifest.json"

# A page that exists but says "not found" in a 200 response is the trap that
# a plain status check walks straight into — Cloudflare Pages and most static
# hosts serve their 404 body with a 200 for unknown paths.
_SOFT_404 = ("page not found", "404 not found", "not found",
             "page doesn't exist", "page does not exist")
_MIN_BYTES = 500


def _norm_path(p):
    return (p or "/").rstrip("/") or "/"


def check_url(url, timeout=15):
    """(ok, detail). Anything but a real, on-topic 200 is a failure."""
    import urllib.request
    import urllib.error
    from urllib.parse import urlparse

    want = urlparse(url)
    req = urllib.request.Request(url, headers={
        # Some hosts serve a stripped page, or block outright, without one.
        "User-Agent": "Mozilla/5.0 (compatible; AdsPreflight/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            final = urlparse(r.geturl())
            body = r.read(200_000).decode("utf-8", "replace")
            code = r.getcode()
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"unreachable ({str(e)[:60]})"

    if code != 200:
        return False, f"HTTP {code}"

    # Redirected off the host, or collapsed onto the homepage. Google calls
    # this a destination mismatch and disapproves it just like a 404.
    if final.netloc != want.netloc:
        return False, f"redirects to another host ({final.netloc})"
    if _norm_path(final.path) != _norm_path(want.path):
        return False, f"redirects to {final.path or '/'}"

    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", body)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    title = ""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip().lower()
    if any(s in title for s in _SOFT_404):
        return False, f"soft 404 — title says '{title[:40]}'"

    if len(text) < _MIN_BYTES:
        return False, f"thin page ({len(text)} chars of text)"

    return True, f"200, {len(text)} chars"


def collect_creative_urls():
    """Every URL the creative phase would send to Google."""
    urls = set()
    for r in load_rows("rsa_editor.csv"):
        u = (r.get("Final URL") or "").strip()
        if u:
            urls.add(u)
    if os.path.exists("sitelinks.json"):
        try:
            with open("sitelinks.json", encoding="utf-8") as f:
                for s in json.load(f).get("sitelink_sets", []):
                    for l in (s.get("sitelinks") or []):
                        u = (l.get("url") or "").strip()
                        # A #anchor rides on a page that is checked anyway.
                        if u:
                            urls.add(u.split("#", 1)[0])
        except Exception as e:
            log(f"⚠️ sitelinks.json unreadable ({str(e)[:60]}) — its URLs not checked.")
    return sorted(u for u in urls if u.lower().startswith(("http://", "https://")))


def preflight(urls):
    """(live, dead[]). Every URL is reported, not just the first failure —
    one round of fixes should clear the whole list."""
    if not urls:
        return True, []
    log(f"\n## Preflight — {len(urls)} landing page(s)")
    dead = []
    for u in urls:
        ok, detail = check_url(u)
        log(f"   {'✅' if ok else '❌'} {u}  ({detail})")
        if not ok:
            dead.append((u, detail))
    return (not dead), dead


def write_manifest(phase, camp_name, urls, dead):
    data = {
        "phase": phase,
        "customer_id": PUSH_CUSTOMER_ID,
        "campaign_name": camp_name,
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "urls": urls,
        "pending": [u for u, _ in dead],
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def build_creative_ops(client, op, temp, ag_res_by_name, c_ops):
    """RSAs and sitelinks — everything that carries a Final URL.

    Pulled out of the main sequence so the same code can serve two callers:
    the combined push, where ag_res_by_name holds temp ids for ad groups
    being created in the very same mutate, and the creative phase, where it
    holds the real resource names of ad groups that already exist. The ops
    themselves are identical either way.
    """
    # ── RSAs (from Stage 3.8's Editor CSV — same data, API delivery) ────
    n_rsa = 0
    pin_enum = client.enums.ServedAssetFieldTypeEnum
    pin_map = {"1": pin_enum.HEADLINE_1, "2": pin_enum.HEADLINE_2, "3": pin_enum.HEADLINE_3}
    for r in load_rows("rsa_editor.csv"):
        ag_res = ag_res_by_name.get(r.get("Ad Group"))
        if not ag_res:
            log(f"⚠️ RSA skipped — unknown ad group '{r.get('Ad Group')}'")
            continue
        o = op()
        ad = o.ad_group_ad_operation.create
        ad.ad_group = ag_res
        ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
        rsa = ad.ad.responsive_search_ad
        for i in range(1, 16):
            h = (r.get(f"Headline {i}") or "").strip()
            if not h:
                continue
            asset = client.get_type("AdTextAsset")
            asset.text = h
            pin = (r.get(f"Headline {i} position") or "").strip()
            if pin in pin_map:
                asset.pinned_field = pin_map[pin]
            rsa.headlines.append(asset)
        for j in range(1, 5):
            d = (r.get(f"Description {j}") or "").strip()
            if d:
                asset = client.get_type("AdTextAsset")
                asset.text = d
                rsa.descriptions.append(asset)
        if r.get("Path 1"):
            rsa.path1 = r["Path 1"][:15]
        if r.get("Path 2"):
            rsa.path2 = r["Path 2"][:15]
        if r.get("Final URL"):
            ad.ad.final_urls.append(r["Final URL"])
        # Google requires >=3 headlines and >=2 descriptions on an RSA, and a
        # Final URL. One short row would fail the whole atomic push, so drop the
        # row instead and say so.
        if len(rsa.headlines) < 3 or len(rsa.descriptions) < 2 or not ad.ad.final_urls:
            log(f"⚠️ RSA skipped for '{r.get('Ad Group')}' — needs 3+ headlines, "
                f"2+ descriptions and a Final URL "
                f"(got {len(rsa.headlines)}/{len(rsa.descriptions)}"
                f"{', no URL' if not ad.ad.final_urls else ''})")
            continue
        c_ops.append(o)
        n_rsa += 1

    # ── sitelinks: one set PER AD GROUP, pointing at that page's anchors ──
    # Ad-group level so a Washing Machine group shows "Washer Repair Pricing",
    # not a campaign-wide generic "Pricing". Asset + AdGroupAsset link ride in
    # the same atomic mutate as everything else.
    n_sl = 0
    if os.path.exists("sitelinks.json"):
        with open("sitelinks.json", encoding="utf-8") as f:
            sl_data = json.load(f)
        asset_i = -1000
        for s in sl_data.get("sitelink_sets", []):
            ag_res = ag_res_by_name.get(s.get("ad_group"))
            if not ag_res:
                log(f"⚠️ Sitelinks skipped — unknown ad group '{s.get('ad_group')}'")
                continue
            for l in (s.get("sitelinks") or []):
                text = (l.get("text") or "").strip()
                d1 = (l.get("desc1") or "").strip()
                d2 = (l.get("desc2") or "").strip()
                url = (l.get("url") or "").strip()
                # Google's limits — an over-long asset fails the whole mutate.
                # Descriptions are all-or-nothing: send both lines or neither.
                if not text or not url or len(text) > 25:
                    log(f"⚠️ Sitelink dropped ({s.get('ad_group')}): "
                        f"text {len(text)}/25 chars or missing URL — '{text[:30]}'")
                    continue
                asset_res = temp(f"assets/{asset_i}")
                asset_i -= 1
                o = op()
                a = o.asset_operation.create
                a.resource_name = asset_res
                a.name = f"{s.get('ad_group','')} — {text}"[:120]
                a.sitelink_asset.link_text = text
                if len(d1) <= 35 and len(d2) <= 35 and d1 and d2:
                    a.sitelink_asset.description1 = d1
                    a.sitelink_asset.description2 = d2
                a.final_urls.append(url)
                c_ops.append(o)

                o = op()
                aga = o.ad_group_asset_operation.create
                aga.ad_group = ag_res
                aga.asset = asset_res
                aga.field_type = client.enums.AssetFieldTypeEnum.SITELINK
                c_ops.append(o)
                n_sl += 1


    return n_rsa, n_sl


def run_creative_phase(client, svc, camp_name, validate):
    """Attach the ads to a campaign that already exists.

    This is the second half of a held push: the structure went up while the
    site was still being built, the pages are live now, preflight has passed,
    and only the URL-carrying operations are left.

    Nothing is created from scratch here, so there are no temp ids — the ad
    groups are found by name in the account and the real resource names are
    handed to the same builder the combined push uses.
    """
    from google.ads.googleads.errors import GoogleAdsException

    # Resolve the campaign case-insensitively, the same way the guard script
    # does: the strategy's casing and the account's casing drift apart, and
    # GAQL's = is case-sensitive.
    camp_res = camp_id = None
    for row in svc.search(customer_id=PUSH_CUSTOMER_ID, query=(
            "SELECT campaign.resource_name, campaign.id, campaign.name, campaign.status "
            "FROM campaign WHERE campaign.status != 'REMOVED'")):
        if row.campaign.name.strip().lower() == camp_name.strip().lower():
            camp_res, camp_id = row.campaign.resource_name, row.campaign.id
            if row.campaign.name != camp_name:
                log(f"ℹ️ Campaign matched case-insensitively: '{camp_name}' -> '{row.campaign.name}'")
            camp_name = row.campaign.name
            break

    if not camp_res:
        log(f"❌ Campaign '{camp_name}' not found in account {PUSH_CUSTOMER_ID}. "
            "Run the structure phase first.")
        return

    ag_res_by_name = {}
    for row in svc.search(customer_id=PUSH_CUSTOMER_ID, query=(
            "SELECT ad_group.resource_name, ad_group.name FROM ad_group "
            f"WHERE campaign.id = {camp_id} AND ad_group.status != 'REMOVED'")):
        ag_res_by_name[row.ad_group.name] = row.ad_group.resource_name

    if not ag_res_by_name:
        log(f"❌ Campaign '{camp_name}' has no ad groups — structure phase incomplete.")
        return
    log(f"Found campaign '{camp_name}' with {len(ag_res_by_name)} ad group(s).")

    # Re-pushing the same RSAs would stack a second identical ad in every ad
    # group, and Google will happily let you: duplicate ads split impressions
    # and make the ad-strength reading meaningless.
    existing_ads = 0
    for row in svc.search(customer_id=PUSH_CUSTOMER_ID, query=(
            "SELECT ad_group_ad.ad.id FROM ad_group_ad "
            f"WHERE campaign.id = {camp_id} AND ad_group_ad.status != 'REMOVED'")):
        existing_ads += 1
    if existing_ads:
        log(f"⚠️ {existing_ads} ad(s) already live in this campaign — creative "
            "phase already ran. Nothing pushed (delete them first to re-push).")
        return

    def op():
        return client.get_type("MutateOperation")

    def temp(res_id):
        return f"customers/{PUSH_CUSTOMER_ID}/{res_id}"

    ops = []
    n_rsa, n_sl = build_creative_ops(client, op, temp, ag_res_by_name, ops)
    if not ops:
        log("⚠️ Nothing to push — no RSA rows or sitelinks found.")
        return

    log(f"Creative ops: {n_rsa} RSAs + {n_sl} sitelinks = {len(ops)}")

    req = client.get_type("MutateGoogleAdsRequest")
    req.customer_id = PUSH_CUSTOMER_ID
    req.mutate_operations.extend(ops)
    req.validate_only = validate
    req.partial_failure = False
    try:
        svc.mutate(request=req)
    except GoogleAdsException as e:
        log("❌ Google Ads API rejected the creative push:")
        for err in e.failure.errors[:20]:
            log(f"   - {err.error_code} | {err.message}")
        return

    if validate:
        log("✅ VALIDATION PASSED — the ads are valid; nothing was created. "
            "Run again with push_mode=live to attach them.")
        return

    log(f"✅ CREATIVE PUSH DONE — {n_rsa} RSAs + {n_sl} sitelinks on '{camp_name}'.")

    # Enabling starts spend, so it never happens as a side effect.
    if ENABLE_CAMPAIGN:
        try:
            from google.api_core import protobuf_helpers

            c_svc = client.get_service("CampaignService")
            c_op = client.get_type("CampaignOperation")
            c_op.update.resource_name = camp_res
            c_op.update.status = client.enums.CampaignStatusEnum.ENABLED
            # An update without a field mask is rejected; the mask has to
            # name exactly the fields that were set.
            client.copy_from(
                c_op.update_mask,
                protobuf_helpers.field_mask(None, c_op.update._pb),
            )
            c_svc.mutate_campaigns(customer_id=PUSH_CUSTOMER_ID, operations=[c_op])
            log(f"🟢 Campaign '{camp_name}' ENABLED — it is spending now.")
        except GoogleAdsException as e:
            log("⚠️ Could not enable the campaign:")
            for err in e.failure.errors[:5]:
                log(f"   - {err.message}")
    else:
        log(f"⏸️  Campaign '{camp_name}' is still PAUSED. Enable it in the UI, "
            "or re-run with enable_campaign=yes.")

    write_manifest("creative_done", camp_name, collect_creative_urls(), [])


def main():
    if not PUSH_CUSTOMER_ID:
        print("ℹ️ PUSH_CUSTOMER_ID empty — API push skipped (CSV-only run).")
        return
    if not os.path.exists(STRATEGY):
        print(f"⚠️ {STRATEGY} not found — nothing to push.")
        return

    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException

    client = GoogleAdsClient.load_from_env()
    svc = client.get_service("GoogleAdsService")

    with open(STRATEGY, encoding="utf-8") as f:
        strategy = json.load(f)
    groups = strategy.get("ad_groups") or []
    campaigns = [c.get("name") for c in (strategy.get("campaigns") or []) if c.get("name")]
    if not campaigns or not groups:
        print("⚠️ No campaign/ad groups in strategy — nothing to push.")
        return
    camp_name = campaigns[0]  # single-campaign mode is the default
    validate = PUSH_MODE != "live"

    # ── decide what this run is allowed to push ─────────────────────────
    creative_urls = collect_creative_urls()
    pages_live, dead = (True, [])
    if PREFLIGHT and creative_urls and PUSH_PHASE != "structure":
        pages_live, dead = preflight(creative_urls)
    elif not PREFLIGHT:
        log("⚠️ PREFLIGHT=off — landing pages not checked. A URL that 404s "
            "here will be disapproved by Google.")

    if PUSH_PHASE == "structure":
        push_creative = False
        log("")
        log("▶ Phase: STRUCTURE (ads held back by request)")
    elif PUSH_PHASE == "creative":
        # Its own path: the campaign already exists, so nothing is created
        # from scratch and the ad groups are looked up by name.
        if not pages_live:
            log("")
            log("❌ Creative phase blocked — these pages are not serving yet:")
            for u, why in dead:
                log(f"   {u} — {why}")
            write_manifest("structure_done", camp_name, creative_urls, dead)
            _write_report()
            return
        run_creative_phase(client, svc, camp_name, validate)
        _write_report()
        return
    else:
        push_creative = pages_live
        log("")
        if pages_live:
            log("▶ Phase: AUTO — every page answers, pushing structure + ads together")
        else:
            log(f"▶ Phase: AUTO — {len(dead)} of {len(creative_urls)} page(s) "
                "not live yet, so structure only")

    # NAME COLLISION: the mutate is atomic and partial_failure is off, so a
    # campaign whose name already exists in the account fails the ENTIRE push
    # (DUPLICATE_CAMPAIGN_NAME) — every re-run of the same client hit this.
    # Suffix a counter instead of dying.
    try:
        # compared case-insensitively: Google Ads treats "Solar Cleaning" and
        # "solar cleaning" as two campaigns, and that casing twin is exactly what
        # makes the generated Ads script fail to find the campaign later.
        existing = {row.campaign.name.strip().lower() for row in svc.search(
            customer_id=PUSH_CUSTOMER_ID,
            query="SELECT campaign.name FROM campaign "
                  "WHERE campaign.status != 'REMOVED'")}
        if camp_name.strip().lower() in existing:
            base_name, n = camp_name, 2
            while f"{base_name} v{n}".strip().lower() in existing and n < 50:
                n += 1
            camp_name = f"{base_name} v{n}"
            log(f"ℹ️ '{base_name}' already exists in the account — pushing as '{camp_name}'.")
    except Exception as _e:
        log(f"ℹ️ Could not list existing campaign names ({str(_e)[:60]}) — continuing.")

    log(f"# Google Ads API push — {camp_name}")
    log(f"Target account: {PUSH_CUSTOMER_ID} | mode: "
        f"{'VALIDATE (dry-run, nothing created)' if validate else 'LIVE (atomic, campaign lands Paused)'}")

    ops = []

    def op():
        return client.get_type("MutateOperation")

    def temp(res_id):
        return f"customers/{PUSH_CUSTOMER_ID}/{res_id}"

    # ── budget (temp -1) ────────────────────────────────────────────────
    o = op()
    b = o.campaign_budget_operation.create
    b.resource_name = temp("campaignBudgets/-1")
    b.name = f"{camp_name} budget"
    b.amount_micros = int(DAILY_BUDGET * 1_000_000)
    b.explicitly_shared = False
    ops.append(o)

    # ── campaign (temp -2): the exact settings the master CSV bakes in,
    #    PLUS presence-only location targeting (CSV can't set that) ─────
    o = op()
    c = o.campaign_operation.create
    c.resource_name = temp("campaigns/-2")
    c.name = camp_name
    c.status = client.enums.CampaignStatusEnum.PAUSED
    c.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    c.campaign_budget = temp("campaignBudgets/-1")
    c.manual_cpc.enhanced_cpc_enabled = False
    c.network_settings.target_google_search = True
    c.network_settings.target_search_network = False        # partners OFF
    c.network_settings.target_content_network = False
    c.network_settings.target_partner_search_network = False
    c.geo_target_type_setting.positive_geo_target_type = \
        client.enums.PositiveGeoTargetTypeEnum.PRESENCE      # "People in" only
    c.geo_target_type_setting.negative_geo_target_type = \
        client.enums.NegativeGeoTargetTypeEnum.PRESENCE
    # AUDIENCES = OBSERVATION, NEVER NARROWING (Jul 2026 fix): without this,
    # every positive audience criterion attaches in TARGETING mode by API
    # default — "You're showing ads only to the audiences below" — and the
    # campaign serves ONLY to those in-market/affinity segments (the
    # zero-impressions bug on the Glass Partition Dubai push). bid_only=True
    # = Observation: full reach, audiences just enable bid adjustments.
    _tr = client.get_type("TargetRestriction")
    _tr.targeting_dimension = client.enums.TargetingDimensionEnum.AUDIENCE
    _tr.bid_only = True
    c.targeting_setting.target_restrictions.append(_tr)
    # Landing-page DKI: kw={keyword} suffix campaign-wide so every RSA click
    # carries its bid keyword — the Mode 1 pages' ?kw= H1 message-match swap
    # runs on this. Was a manual step in the report; now set automatically.
    c.final_url_suffix = "kw={keyword}"
    # Required since the EU political-ads regulation (API rejects campaign
    # creation without it — hit on first live push, Jul 2026). Our campaigns
    # are local-service ads, never EU political advertising.
    try:
        c.contains_eu_political_advertising = \
            client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    except AttributeError:
        pass  # older google-ads lib without the field
    ops.append(o)

    # ── campaign language targeting ─────────────────────────────────────
    # One campaign can hold English AND Arabic ad groups — that part is
    # standard. What is NOT optional is the campaign's language criteria: they
    # filter on the user's Google interface language, so a campaign that never
    # targeted Arabic under-serves its Arabic ad groups. Target exactly the
    # languages the ad groups are actually written in.
    # Fast path for the ids we already know. A code that is NOT here used to be
    # dropped silently, and the campaign fell back to English — a Polish or Thai
    # campaign then targeted English speakers. Rather than hardcode more ids from
    # memory (a wrong id mis-targets a live campaign, which is worse than the
    # bug), unknown codes are resolved from Google itself, the same way
    # keyword_research.resolve_language_from_code does it.
    _LANG_CONSTANTS = {"en": 1000, "ar": 1019, "hi": 1023, "ur": 1056, "fr": 1002,
                       "de": 1001, "es": 1003, "it": 1004, "nl": 1010, "pt": 1014,
                       "ru": 1031, "tr": 1037, "zh": 1017, "ja": 1005, "ko": 1012}
    _GADS_LANG_CODE = {"zh": "zh_CN", "he": "iw", "nb": "no"}

    def _lang_id(code):
        """languageConstant id for an ISO code: known table first, else ask the
        API. Returns None when Google has no such language or the lookup fails,
        and the caller then skips that criterion rather than mis-targeting."""
        if code in _LANG_CONSTANTS:
            return _LANG_CONSTANTS[code]
        gcode = _GADS_LANG_CODE.get(code, code)
        try:
            q = ("SELECT language_constant.id FROM language_constant "
                 f"WHERE language_constant.code = '{gcode}'")
            for row in svc.search(customer_id=PUSH_CUSTOMER_ID, query=q):
                lid = int(row.language_constant.id)
                _LANG_CONSTANTS[code] = lid          # cache for the rest of the run
                log(f"ℹ️ Language '{code}' resolved via API → languageConstant {lid}.")
                return lid
            log(f"⚠️ Google has no language matching '{code}' — not targeted.")
        except Exception as _le:
            log(f"⚠️ Language lookup failed for '{code}' ({str(_le)[:60]}) — not targeted.")
        return None

    _langs = set()
    for g in groups:
        code = str(g.get("language") or "").strip().lower()
        if not code:
            blob = str(g.get("name", "")) + " ".join(
                str(k.get("keyword", "")) for k in (g.get("keywords") or []))
            code = "ar" if any("؀" <= ch <= "ۿ" for ch in blob) else "en"
        if code:
            _langs.add(code)
    _targeted = []
    for code in sorted(_langs or {"en"}):
        lid = _lang_id(code)
        if lid is None:
            continue
        o = op()
        cc = o.campaign_criterion_operation.create
        cc.campaign = temp("campaigns/-2")
        cc.language.language_constant = f"languageConstants/{lid}"
        ops.append(o)
        _targeted.append(code)
    # Never ship a campaign with no language criterion at all.
    if not _targeted:
        o = op()
        cc = o.campaign_criterion_operation.create
        cc.campaign = temp("campaigns/-2")
        cc.language.language_constant = "languageConstants/1000"
        ops.append(o)
        _targeted = ["en (fallback)"]
    log(f"Campaign languages targeted: {', '.join(_targeted)}")

    # ── ad groups + keywords + negatives ────────────────────────────────
    n_kw = n_neg = 0
    for gi, g in enumerate(groups):
        ag_res = temp(f"adGroups/{-10 - gi}")
        bids = sorted(k["suggested_bid"] for k in g.get("keywords", [])
                      if k.get("suggested_bid"))
        median = bids[len(bids) // 2] if bids else 0
        o = op()
        ag = o.ad_group_operation.create
        ag.resource_name = ag_res
        ag.name = g.get("name", f"Ad Group {gi+1}")
        ag.campaign = temp("campaigns/-2")
        ag.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ag.status = client.enums.AdGroupStatusEnum.ENABLED
        if median:
            ag.cpc_bid_micros = int(median * 1_000_000)
        ops.append(o)

        mt = client.enums.KeywordMatchTypeEnum.EXACT \
            if g.get("match_type") == "exact" else client.enums.KeywordMatchTypeEnum.PHRASE

        # Google rejects a keyword over 80 chars or 10 words, and rejects the
        # SAME text+match type twice in one ad group. Either one fails the whole
        # atomic push, so filter here instead of losing the campaign.
        seen_texts = set()

        def _kw_ok(text, label):
            t = " ".join(str(text or "").split())
            if not t:
                return None
            if len(t) > 80 or len(t.split()) > 10:
                log(f"⚠️ {label} skipped (Google limit: 80 chars / 10 words): {t[:60]}")
                return None
            key = t.lower()
            if key in seen_texts:
                log(f"⚠️ duplicate {label} skipped in '{g.get('name', '')}': {t[:60]}")
                return None
            seen_texts.add(key)
            return t

        for k in g.get("keywords", []):
            t = _kw_ok(k.get("keyword", ""), "keyword")
            if not t:
                continue
            o = op()
            cr = o.ad_group_criterion_operation.create
            cr.ad_group = ag_res
            cr.keyword.text = t
            cr.keyword.match_type = mt
            bid = k.get("suggested_bid") or median
            if bid:
                cr.cpc_bid_micros = int(bid * 1_000_000)
            ops.append(o)
            n_kw += 1
        for e in g.get("intent_expansion_keywords", []):
            t = _kw_ok(e, "expansion keyword")
            if not t:
                continue
            o = op()
            cr = o.ad_group_criterion_operation.create
            cr.ad_group = ag_res
            cr.keyword.text = t
            cr.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            if median:
                cr.cpc_bid_micros = int(median * 1_000_000)
            ops.append(o)
            n_kw += 1
        seen_negs = set()
        for n in g.get("negative_keywords", []):
            t = " ".join(str(n or "").split())
            if not t or len(t) > 80 or len(t.split()) > 10 or t.lower() in seen_negs:
                continue
            seen_negs.add(t.lower())
            o = op()
            cr = o.ad_group_criterion_operation.create
            cr.ad_group = ag_res
            cr.negative = True
            cr.keyword.text = t
            cr.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            ops.append(o)
            n_neg += 1

    # RSAs + sitelinks only when this run is allowed to push creative.
    # In structure phase they are held back on purpose: they are the only
    # operations with a Final URL, so holding them is what makes a push at a
    # site that is not built yet impossible to disapprove.
    n_rsa = n_sl = 0
    ag_res_by_name = {g.get("name"): temp(f"adGroups/{-10 - i}")
                      for i, g in enumerate(groups)}
    if push_creative:
        n_rsa, n_sl = build_creative_ops(client, op, temp, ag_res_by_name, ops)
    else:
        log("⏸️  Structure phase — RSAs and sitelinks held back.")

    # ── locations: targets with bid modifiers + exclusions ─────────────
    n_loc = n_loc_neg = 0
    seen_geo = set()
    for r in load_rows("locations_editor.csv"):
        gid = (r.get("ID") or "").strip()
        if not gid or gid in seen_geo:
            continue
        seen_geo.add(gid)
        o = op()
        cc = o.campaign_criterion_operation.create
        cc.campaign = temp("campaigns/-2")
        cc.location.geo_target_constant = f"geoTargetConstants/{gid}"
        mod = (r.get("Bid Modifier") or "").strip()
        if mod:
            try:
                cc.bid_modifier = 1 + float(mod) / 100   # 25 → 1.25, -90 → 0.10
            except ValueError:
                pass
        ops.append(o)
        n_loc += 1
    for r in load_rows("locations_negative.csv"):
        gid = (r.get("ID") or "").strip()
        if not gid or gid in seen_geo:
            continue
        seen_geo.add(gid)
        o = op()
        cc = o.campaign_criterion_operation.create
        cc.campaign = temp("campaigns/-2")
        cc.negative = True
        cc.location.geo_target_constant = f"geoTargetConstants/{gid}"
        ops.append(o)
        n_loc_neg += 1

    log(f"Core operations: 1 budget + 1 campaign + {len(groups)} ad groups + "
        f"{n_kw} keywords + {n_neg} negatives + {n_rsa} RSAs + "
        f"{n_sl} ad-group sitelinks + "
        f"{n_loc} locations + {n_loc_neg} excluded locations = {len(ops)}")

    # ── the atomic core mutate ──────────────────────────────────────────
    req = client.get_type("MutateGoogleAdsRequest")
    req.customer_id = PUSH_CUSTOMER_ID
    req.mutate_operations.extend(ops)
    req.validate_only = validate
    req.partial_failure = False   # all-or-nothing: no half-built campaign
    try:
        svc.mutate(request=req)
        log("✅ VALIDATION PASSED — every operation is valid; nothing was "
            "created (run again with push_mode=live to build it)." if validate
            else f"✅ LIVE PUSH DONE — campaign '{camp_name}' created PAUSED "
                 f"in account {PUSH_CUSTOMER_ID}.")
    except GoogleAdsException as e:
        log("❌ Google Ads API rejected the core push (CSV path unaffected — "
            "fix the errors below or import the master CSV):")
        for err in e.failure.errors[:20]:
            log(f"   - {err.error_code} | {err.message}"
                + (f" | at {err.location.field_path_elements}" if err.location.field_path_elements else ""))
        _write_report()
        return

    # ── what happens next ───────────────────────────────────────────────
    # A held push is only half a campaign, and the half that is missing is
    # invisible in the Ads UI — the campaign looks finished, it just has no
    # ads. Say so plainly, and leave the manifest behind so the state is on
    # disk rather than in someone's memory.
    if not validate:
        write_manifest("creative_done" if push_creative else "structure_done",
                       camp_name, creative_urls, dead)

    if not push_creative:
        log("")
        log("⏸️  HELD — the campaign structure is up, but it has NO ADS yet.")
        if dead:
            log(f"    {len(dead)} landing page(s) are not serving:")
            for u, why in dead:
                log(f"      {u} — {why}")
            log("    Build/deploy those pages, then run this stage again.")
        elif creative_urls:
            log(f"    {len(creative_urls)} landing page URL(s) were NOT checked "
                "(structure phase skips preflight).")
        else:
            log("    No landing page URLs were found — is rsa_editor.csv missing?")
        log("    The next run pushes the RSAs and sitelinks and, with "
            "enable_campaign=yes, turns the campaign on.")
    elif not validate:
        log("")
        log(f"⏸️  Campaign '{camp_name}' is PAUSED — nothing is spending. "
            "Enable it in the UI, or re-run with enable_campaign=yes.")

    # ── audiences (second pass, best-effort): resolve segment names →
    #    user_interest ids, then attach as campaign criteria ─────────────
    if os.path.exists("audience_plan.json") and not validate:
        with open("audience_plan.json", encoding="utf-8") as f:
            plan = json.load(f)
        names = ([a["name"] for a in plan.get("positive", [])]
                 + [a["name"] for a in plan.get("negative", [])])
        lookup = {}
        if names:
            quoted = ", ".join("'" + n.replace("'", "\\'") + "'" for n in set(names))
            try:
                rows = svc.search(customer_id=PUSH_CUSTOMER_ID,
                                  query="SELECT user_interest.user_interest_id, "
                                        "user_interest.name FROM user_interest "
                                        f"WHERE user_interest.name IN ({quoted})")
                for row in rows:
                    lookup[row.user_interest.name] = row.user_interest.user_interest_id
            except GoogleAdsException as e:
                log(f"⚠️ Audience name lookup failed ({e.failure.errors[0].message}) "
                    "— audiences skipped; use the audiences CSVs.")
        # need the REAL campaign resource name now
        camp_res = None
        try:
            for row in svc.search(customer_id=PUSH_CUSTOMER_ID,
                                  query="SELECT campaign.resource_name, campaign.name "
                                        "FROM campaign WHERE campaign.name = "
                                        f"'{camp_name.replace(chr(39), chr(92) + chr(39))}'"):
                camp_res = row.campaign.resource_name
        except GoogleAdsException:
            pass
        n_ok = n_skip = 0
        if camp_res:
            # (was: `a in plan["negative"]` — a dict-equality scan that
            # mislabels an audience appearing in both lists, and silently
            # depends on dict ordering. Tag each entry once instead.)
            tagged = ([(a, False) for a in plan.get("positive", [])]
                      + [(a, True) for a in plan.get("negative", [])])
            for a, is_neg in tagged:
                uid = lookup.get(a["name"])
                if not uid:
                    log(f"   ⚠️ audience not matched via API: {a['name']} "
                        f"({'exclude' if is_neg else 'include'}) — add via CSV")
                    n_skip += 1
                    continue
                o2 = client.get_type("CampaignCriterionOperation")
                cc = o2.create
                cc.campaign = camp_res
                cc.user_interest.user_interest_category = \
                    f"customers/{PUSH_CUSTOMER_ID}/userInterests/{uid}"
                if is_neg:
                    cc.negative = True
                elif a.get("bid_adjustment"):
                    cc.bid_modifier = 1 + a["bid_adjustment"] / 100
                try:
                    client.get_service("CampaignCriterionService").mutate_campaign_criteria(
                        customer_id=PUSH_CUSTOMER_ID, operations=[o2])
                    n_ok += 1
                except GoogleAdsException as e:
                    log(f"   ⚠️ audience rejected: {a['name']} — "
                        f"{e.failure.errors[0].message}")
                    n_skip += 1
        log(f"Audiences: {n_ok} attached, {n_skip} left for the CSV path.")
    elif validate:
        log("Audiences: checked in live mode only (name lookup needs the real account).")

    _write_report()


def _write_report():
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                      # never sink the pipeline
        log(f"⚠️ Push stage error (pipeline continues, CSV path unaffected): {e}")
        _write_report()
        sys.exit(0)
