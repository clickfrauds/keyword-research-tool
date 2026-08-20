"""
setup_conversions.py  (STAGE 0-CONV — Google Ads conversion actions)
----------------------------------------------------------------------
Creates the three conversion actions a lead-gen client needs — Phone Call
Click, WhatsApp Click, Form Submit — straight in the Google Ads account,
reads their tag labels back out, and hands them to the middleware
generator via the client_keys row.

WHY THIS EXISTS
  The labels used to be produced by importing GA4 events into Google Ads
  by hand, once per client. That import is not scriptable, it lags by
  hours (Smart Bidding wants fresh data), and it double-counted against
  the conversions the website builder was firing inline. Ads-native
  conversion actions ARE scriptable end to end: create here, read the
  label out of the tag snippet, store it on the client row, and the admin
  page fills the middleware fields in by itself.

  Run this BEFORE the site is built. Then the pages go live already
  carrying the exact labels the Ads account knows about, and there is no
  window where a campaign points at a page with no tracking on it.

WHAT IT WILL NOT TOUCH
  - Conversion actions it did not create. Existing ones — including the
    GA4-imported ones you are migrating away from — are left exactly as
    they are. Turn those off yourself, in the UI, once these are live.
  - The Supabase `conversions` table. That is the FRAUD system's trust
    anchor (conversion-ingest writes it, fraud_agent.py reads it to
    decide who must never be blocked). It has nothing to do with Google
    Ads bidding and this script must never write to it. The only Supabase
    table touched here is client_keys, and only its four label columns.

IDEMPOTENT
  Matching is by exact conversion action name. A second run finds what
  the first run made and re-reads the labels instead of creating twins —
  duplicate actions would split the conversion data and quietly wreck
  Smart Bidding.

SAFETY MODEL
  CONV_MODE=validate (default): Google checks every operation and reports
    errors WITHOUT creating anything. Existing actions are still read, so
    a re-run in validate mode is a safe way to recover the labels.
  CONV_MODE=live: creates whatever is missing.

Env : PUSH_CUSTOMER_ID (required), CONV_MODE (validate|live),
      GOOGLE_ADS_* client env vars, GOOGLE_ADS_LOGIN_CUSTOMER_ID (MCC),
      CONV_VALUE_PHONE / _WA / _FORM (default lead values, account
        currency; 0 = no default value),
      ADMIN_API_URL + ADMIN_PASSWORD + CLIENT_TOKEN (optional — write the
        labels back to the client_keys row through the admin endpoint)
Output: conversion_actions.json (+ log lines)
"""

import os
import re
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PUSH_CUSTOMER_ID = "".join(c for c in os.environ.get("PUSH_CUSTOMER_ID", "") if c.isdigit())
CONV_MODE = os.environ.get("CONV_MODE", "validate").strip().lower()

ADMIN_API_URL = os.environ.get("ADMIN_API_URL", "").strip().rstrip("/")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
CLIENT_TOKEN = os.environ.get("CLIENT_TOKEN", "").strip()

OUTPUT_FILE = "conversion_actions.json"

# name -> (column on client_keys, Ads category, primary?, value env var)
#
# PRIMARY vs SECONDARY matters: every primary action feeds bidding. Phone
# and form are the real leads. WhatsApp is kept secondary because it fires
# on the click, not on a reply — counting it as a primary lead would teach
# Smart Bidding to chase taps that never became conversations.
ACTIONS = {
    "Phone Call Click": {
        "column":   "label_phone",
        "category": "PHONE_CALL_LEAD",
        "primary":  True,
        "value_env": "CONV_VALUE_PHONE",
    },
    "WhatsApp Click": {
        "column":   "label_whatsapp",
        "category": "CONTACT",
        "primary":  False,
        "value_env": "CONV_VALUE_WA",
    },
    "Form Submit": {
        "column":   "label_form",
        "category": "SUBMIT_LEAD_FORM",
        "primary":  True,
        "value_env": "CONV_VALUE_FORM",
    },
}

report = []


def log(msg):
    print(msg)
    report.append(msg)


def gaql_escape(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def fetch_actions(svc, names):
    """name -> {resource_name, id, snippets[]} for the actions that exist."""
    name_list = "','".join(gaql_escape(n) for n in names)
    query = (
        "SELECT conversion_action.resource_name, conversion_action.id, "
        "conversion_action.name, conversion_action.status, "
        "conversion_action.tag_snippets "
        "FROM conversion_action "
        f"WHERE conversion_action.name IN ('{name_list}') "
        "AND conversion_action.status != 'REMOVED'"
    )
    found = {}
    for row in svc.search(customer_id=PUSH_CUSTOMER_ID, query=query):
        ca = row.conversion_action
        found[ca.name] = {
            "resource_name": ca.resource_name,
            "id": ca.id,
            "snippets": [
                (getattr(sn, "event_snippet", "") or "")
                for sn in (ca.tag_snippets or [])
            ],
        }
    return found


# The label lives nowhere else in the API — it is only ever spelled out
# inside the event snippet, as send_to: 'AW-1234567/AbC-D_xyz'. The AW id
# is the account's, so every action in the account carries the same one.
_SEND_TO = re.compile(r"AW-(\d+)/([\w\-]+)")


def parse_label(snippets):
    for sn in snippets:
        m = _SEND_TO.search(sn or "")
        if m:
            return "AW-" + m.group(1), m.group(2)
    return None, None


def build_create_op(client, name, spec):
    op = client.get_type("ConversionActionOperation")
    ca = op.create
    ca.name = name
    ca.type_ = client.enums.ConversionActionTypeEnum.WEBPAGE
    ca.category = getattr(client.enums.ConversionActionCategoryEnum, spec["category"])
    ca.status = client.enums.ConversionActionStatusEnum.ENABLED

    # ONE_PER_CLICK, not EVERY: one visitor tapping the call button four
    # times is one lead. EVERY would inflate the count and, with it, the
    # bids.
    ca.counting_type = (
        client.enums.ConversionActionCountingTypeEnum.ONE_PER_CLICK
    )

    value = 0.0
    try:
        value = float(os.environ.get(spec["value_env"], "0") or 0)
    except ValueError:
        value = 0.0
    if value > 0:
        ca.value_settings.default_value = value
        ca.value_settings.always_use_default_value = True

    # primary_for_goal survives alongside the newer campaign-level
    # conversion goals; older client libraries may not carry the field.
    try:
        ca.primary_for_goal = bool(spec["primary"])
    except AttributeError:
        pass

    return op


def fetch_client_row():
    """The client_keys row for CLIENT_TOKEN, or None.

    Read through the admin endpoint, never straight from Supabase: a direct
    call would need the service role key on whatever machine runs this, and
    that key can read and rewrite every table the fraud system depends on.
    """
    if not (ADMIN_API_URL and ADMIN_PASSWORD and CLIENT_TOKEN):
        return None

    import urllib.request
    import urllib.parse

    try:
        url = f"{ADMIN_API_URL}?password={urllib.parse.quote(ADMIN_PASSWORD)}"
        with urllib.request.urlopen(url, timeout=20) as r:
            clients = json.loads(r.read().decode("utf-8")).get("clients") or []
    except Exception as e:
        log(f"⚠️ Could not read the client list ({str(e)[:80]}).")
        return None

    return next((c for c in clients if c.get("client_token") == CLIENT_TOKEN), None)


def resolve_account(row):
    """Decide which Google Ads account to work in, and refuse if the two
    identifiers disagree.

    Two different ids meet here: customer_id names the Ads ACCOUNT the
    labels come out of, client_token names the Supabase ROW they go into.
    Both already live on the same client_keys row, so the row can settle it.

    Passing account A's PUSH_CUSTOMER_ID together with client B's
    CLIENT_TOKEN used to write A's labels onto B's row. B's middleware would
    then have carried A's AW id, and every lead B generated would have been
    reported into A's account — silently, with nothing in either account
    looking wrong. Hence: when the row knows its customer_id, it wins.
    """
    row_cid = "".join(c for c in str((row or {}).get("customer_id") or "") if c.isdigit())

    if PUSH_CUSTOMER_ID and row_cid and PUSH_CUSTOMER_ID != row_cid:
        log(f"❌ Account mismatch — refusing to run.")
        log(f"   PUSH_CUSTOMER_ID says {PUSH_CUSTOMER_ID}, but client "
            f"'{row.get('website_name')}' is on account {row_cid}.")
        log("   Fix whichever is wrong. Writing one account's labels onto "
            "another client's row would send that client's leads into the "
            "wrong Ads account.")
        sys.exit(1)

    if not PUSH_CUSTOMER_ID and row_cid:
        log(f"ℹ️ Using account {row_cid} from client row "
            f"'{row.get('website_name')}'.")
        return row_cid

    return PUSH_CUSTOMER_ID


def write_back(results, row):
    """Put the labels on the client_keys row, through the admin endpoint."""
    import urllib.request
    import urllib.error

    if not (ADMIN_API_URL and ADMIN_PASSWORD and CLIENT_TOKEN):
        log("ℹ️ ADMIN_API_URL / ADMIN_PASSWORD / CLIENT_TOKEN not all set — "
            "labels not written back. Paste them into the admin page by hand, "
            "or set the three and re-run.")
        return

    if not row:
        log(f"⚠️ client_token '{CLIENT_TOKEN}' not found in the admin list — "
            "nothing written back. Check the token.")
        return

    payload = {
        "password": ADMIN_PASSWORD,
        "client_token": CLIENT_TOKEN,
        "website_name": row.get("website_name"),
        "aw_id": results["aw_id"],
    }
    for name, spec in ACTIONS.items():
        lbl = results["actions"].get(name, {}).get("label")
        if lbl:
            payload[spec["column"]] = lbl

    # Only the label columns ride along. customer_id, campaign_id, mcc and
    # active are left out on purpose: the endpoint updates just what it is
    # given, and sending stale copies of those would be a way to overwrite
    # them — `active` in particular, which both edge functions check on
    # every single request.
    try:
        req = urllib.request.Request(
            ADMIN_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read()
        log(f"✅ Labels written to client_keys row '{row.get('website_name')}'.")
        log("   Admin page ab ye 4 fields khud bhar lega — middleware generate kar lein.")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        log(f"⚠️ Write-back failed ({e.code}): {body}")
    except Exception as e:
        log(f"⚠️ Write-back failed: {str(e)[:120]}")


def main():
    global PUSH_CUSTOMER_ID

    # The client row is read FIRST, before a single call to Google, so the
    # account can be settled (and a mismatch refused) while nothing has been
    # created yet.
    row = fetch_client_row()
    PUSH_CUSTOMER_ID = resolve_account(row)

    if not PUSH_CUSTOMER_ID:
        print("❌ No Google Ads account. Set PUSH_CUSTOMER_ID, or set "
              "CLIENT_TOKEN (with ADMIN_API_URL + ADMIN_PASSWORD) so the "
              "account can be read off the client row.")
        sys.exit(1)

    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException

    client = GoogleAdsClient.load_from_env()
    svc = client.get_service("GoogleAdsService")
    ca_svc = client.get_service("ConversionActionService")

    validate = CONV_MODE != "live"
    log(f"# Google Ads conversion setup — account {PUSH_CUSTOMER_ID}")
    log(f"Mode: {'VALIDATE (nothing created)' if validate else 'LIVE'}")

    existing = fetch_actions(svc, list(ACTIONS.keys()))
    for n in existing:
        log(f"   already exists: {n}")

    missing = [n for n in ACTIONS if n not in existing]

    if missing:
        ops = [build_create_op(client, n, ACTIONS[n]) for n in missing]
        try:
            ca_svc.mutate_conversion_actions(
                customer_id=PUSH_CUSTOMER_ID,
                operations=ops,
                validate_only=validate,
            )
        except GoogleAdsException as e:
            for err in e.failure.errors:
                log(f"❌ {err.message}")
            sys.exit(1)

        if validate:
            log(f"✅ VALIDATE ok — {len(missing)} action(s) would be created: "
                + ", ".join(missing))
            log("   Set CONV_MODE=live to actually create them.")
        else:
            log(f"✅ Created {len(missing)}: " + ", ".join(missing))
            # Re-read: labels only exist once the actions do.
            existing = fetch_actions(svc, list(ACTIONS.keys()))
    else:
        log("✅ All three conversion actions already present — nothing to create.")

    results = {"customer_id": PUSH_CUSTOMER_ID, "aw_id": None, "actions": {}}
    for name, spec in ACTIONS.items():
        info = existing.get(name)
        if not info:
            results["actions"][name] = {"column": spec["column"], "label": None}
            continue
        aw_id, label = parse_label(info["snippets"])
        if aw_id:
            results["aw_id"] = aw_id
        results["actions"][name] = {
            "column": spec["column"],
            "id": info["id"],
            "label": label,
            "primary": spec["primary"],
        }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    log("")
    log(f"AW id: {results['aw_id'] or '(not available yet)'}")
    for name, spec in ACTIONS.items():
        lbl = results["actions"][name].get("label")
        log(f"  {spec['column']:<16} {name:<18} {lbl or '(none yet)'}")
    log(f"→ {OUTPUT_FILE}")

    if results["aw_id"] and all(results["actions"][n].get("label") for n in ACTIONS):
        write_back(results, row)
    elif not validate:
        log("ℹ️ Labels not all available yet — Google can take a moment to mint "
            "the tag snippets. Re-run this script (validate mode is fine) to "
            "read them.")

    log("")
    log("⚠️ Ab Google Ads me purani GA4-imported conversions ko Remove ya "
        "Secondary kar dein — warna har lead do baar ginegi. GA4 ka Ads se "
        "LINK rehne dein; sirf IMPORT band karna hai.")


if __name__ == "__main__":
    main()
