"""
fix_audience_observation.py  (one-shot repair for already-pushed campaigns)
---------------------------------------------------------------------------
Old pushes attached positive audiences WITHOUT bid_only, so Google put the
whole campaign in TARGETING mode ("You're showing ads only to the audiences
below") — ads served ONLY to those segments = zero impressions.

This script updates the campaign's targeting_setting to bid_only=True
(Observation): every already-attached audience instantly flips to
Observation — full reach restored, bid adjustments kept. It also sets
final_url_suffix=kw={keyword} so the Mode 1 landing pages' ?kw= H1
message-match swap works on every click.

Usage (same GOOGLE_ADS_* env vars as the push stage):
    PUSH_CUSTOMER_ID=6329485348 CAMPAIGN_NAME="Glass Partitions Dubai" \
        python scripts/fix_audience_observation.py

Env : PUSH_CUSTOMER_ID (required), CAMPAIGN_NAME (required),
      GOOGLE_ADS_* client env vars, GOOGLE_ADS_LOGIN_CUSTOMER_ID (MCC)
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CUSTOMER_ID = "".join(c for c in os.environ.get("PUSH_CUSTOMER_ID", "") if c.isdigit())
CAMPAIGN_NAME = os.environ.get("CAMPAIGN_NAME", "").strip()


def main():
    if not CUSTOMER_ID or not CAMPAIGN_NAME:
        print("❌ Set PUSH_CUSTOMER_ID and CAMPAIGN_NAME env vars.")
        sys.exit(1)

    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    from google.api_core import protobuf_helpers

    client = GoogleAdsClient.load_from_env()
    svc = client.get_service("GoogleAdsService")

    # find the campaign by name
    safe = CAMPAIGN_NAME.replace("'", "\\'")
    camp_res = None
    for row in svc.search(customer_id=CUSTOMER_ID,
                          query="SELECT campaign.resource_name, campaign.name "
                                f"FROM campaign WHERE campaign.name = '{safe}'"):
        camp_res = row.campaign.resource_name
    if not camp_res:
        print(f"❌ Campaign '{CAMPAIGN_NAME}' not found in account {CUSTOMER_ID}.")
        sys.exit(1)
    print(f"🔎 Found: {camp_res}")

    op = client.get_type("CampaignOperation")
    c = op.update
    c.resource_name = camp_res
    tr = client.get_type("TargetRestriction")
    tr.targeting_dimension = client.enums.TargetingDimensionEnum.AUDIENCE
    tr.bid_only = True                       # Observation — reach never restricted
    c.targeting_setting.target_restrictions.append(tr)
    c.final_url_suffix = "kw={keyword}"      # landing-page DKI (?kw= H1 swap)
    op.update_mask.CopyFrom(protobuf_helpers.field_mask(None, c._pb))

    try:
        client.get_service("CampaignService").mutate_campaigns(
            customer_id=CUSTOMER_ID, operations=[op])
    except GoogleAdsException as e:
        print("❌ Update rejected:")
        for err in e.failure.errors:
            print(f"   - {err.error_code} | {err.message}")
        sys.exit(1)

    print("✅ Done: audiences are now OBSERVATION (full reach, bid adjustments "
          "kept) and final_url_suffix=kw={keyword} is set.")
    print("   Verify in the UI: Audiences page should no longer say "
          "\"You're showing ads only to the audiences below\".")


if __name__ == "__main__":
    main()
