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

REQUIREMENTS
  - google-ads.yaml equivalents via env (same secrets Stage 1 uses).
  - The OAuth user must have access to PUSH_CUSTOMER_ID; if it's a
    client account under your MCC, set GOOGLE_ADS_LOGIN_CUSTOMER_ID to
    the MCC id.
  - Account currency must match BID_CURRENCY (bids are sent as micros).

Env : PUSH_CUSTOMER_ID (required to run), PUSH_MODE (validate|live),
      DAILY_BUDGET (account currency, default 1000),
      GOOGLE_ADS_* client env vars, GOOGLE_ADS_LOGIN_CUSTOMER_ID (MCC)
Input : keyword_strategy.json, rsa_editor.csv?, locations_editor.csv?,
        locations_negative.csv?, audience_plan.json?
Output: google_ads_push_report.md (+ log lines)
"""

import os
import sys
import csv
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PUSH_CUSTOMER_ID = "".join(c for c in os.environ.get("PUSH_CUSTOMER_ID", "") if c.isdigit())
PUSH_MODE = os.environ.get("PUSH_MODE", "validate").strip().lower()
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
    # Required since the EU political-ads regulation (API rejects campaign
    # creation without it — hit on first live push, Jul 2026). Our campaigns
    # are local-service ads, never EU political advertising.
    try:
        c.contains_eu_political_advertising = \
            client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    except AttributeError:
        pass  # older google-ads lib without the field
    ops.append(o)

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
        for k in g.get("keywords", []):
            o = op()
            cr = o.ad_group_criterion_operation.create
            cr.ad_group = ag_res
            cr.keyword.text = k.get("keyword", "")
            cr.keyword.match_type = mt
            bid = k.get("suggested_bid") or median
            if bid:
                cr.cpc_bid_micros = int(bid * 1_000_000)
            ops.append(o)
            n_kw += 1
        for e in g.get("intent_expansion_keywords", []):
            o = op()
            cr = o.ad_group_criterion_operation.create
            cr.ad_group = ag_res
            cr.keyword.text = e
            cr.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            if median:
                cr.cpc_bid_micros = int(median * 1_000_000)
            ops.append(o)
            n_kw += 1
        for n in g.get("negative_keywords", []):
            o = op()
            cr = o.ad_group_criterion_operation.create
            cr.ad_group = ag_res
            cr.negative = True
            cr.keyword.text = n
            cr.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            ops.append(o)
            n_neg += 1

    # ── RSAs (from Stage 3.8's Editor CSV — same data, API delivery) ────
    n_rsa = 0
    ag_res_by_name = {g.get("name"): temp(f"adGroups/{-10 - i}")
                      for i, g in enumerate(groups)}
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
        ops.append(o)
        n_rsa += 1

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
            for a in plan.get("positive", []) + plan.get("negative", []):
                is_neg = a in plan.get("negative", [])
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
