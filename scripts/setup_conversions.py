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
      PRIMARY_CONVERSIONS (which actions feed bidding; default
        "phone,form" — add whatsapp where it is the main channel),
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
# One token, several comma-separated, or "all" for every active client.
# Seventeen clients meant seventeen workflow runs — twice, counting the check
# pass — which is the sort of chore that never gets finished.
CLIENT_TOKEN = os.environ.get("CLIENT_TOKEN", "").strip()
CLIENT_TOKENS = [t.strip() for t in CLIENT_TOKEN.split(",") if t.strip()]
ALL_CLIENTS = CLIENT_TOKEN.strip().lower() in ("all", "*")

# Every client's results end up here; the file holds a list for a batch run
# and a single object for one client, so nothing that read it before breaks.
ALL_RESULTS = []

OUTPUT_FILE = "conversion_actions.json"

# name -> (column on client_keys, Ads category, primary?, value env var)
#
# PRIMARY vs SECONDARY decides what bidding optimises for. Only primary
# actions feed it.
#
# The default keeps phone and form primary and WhatsApp secondary, because a
# tap on a WhatsApp button opens the app with a prefilled message and the
# person still has to send it — plenty never do. But that reasoning is
# regional, not universal: across the Gulf and South Asia WhatsApp is often
# the main way customers make contact, and treating the client's busiest
# channel as secondary teaches bidding to ignore it.
#
# So it is a setting, not a verdict. PRIMARY_CONVERSIONS lists the actions
# that should count for bidding, e.g. "phone,whatsapp,form" for a client
# whose leads mostly arrive on WhatsApp.
# `or` not a .get default: the workflow passes an empty string when the field
# is cleared, and .get only falls back when the variable is absent entirely.
# Empty here would mean no primary conversion at all, and bidding would have
# nothing to optimise for.
_PRIMARY = {k.strip().lower() for k in
            (os.environ.get("PRIMARY_CONVERSIONS", "").strip() or "phone,form").split(",")
            if k.strip()}

ACTIONS = {
    "Phone Call Click": {
        "column":   "label_phone",
        "category": "PHONE_CALL_LEAD",
        "key":      "phone",
        "value_env": "CONV_VALUE_PHONE",
    },
    "WhatsApp Click": {
        "column":   "label_whatsapp",
        "category": "CONTACT",
        "key":      "whatsapp",
        "value_env": "CONV_VALUE_WA",
    },
    "Form Submit": {
        "column":   "label_form",
        "category": "SUBMIT_LEAD_FORM",
        "key":      "form",
        "value_env": "CONV_VALUE_FORM",
    },
}
for _spec in ACTIONS.values():
    _spec["primary"] = _spec["key"] in _PRIMARY

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


# Cloudflare sits in front of the admin endpoint and its Browser Integrity
# Check rejects a request whose headers do not look like a browser's —
# error 1010, a 403 raised before the function ever runs, so the password is
# never even examined. urllib sends no User-Agent at all by default, which is
# exactly the shape it refuses.
_API_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_clients():
    """Every client_keys row, through the admin endpoint.

    Read there and never straight from Supabase: a direct call would need the
    service role key on whatever machine runs this, and that key can read and
    rewrite every table the fraud system depends on.
    """
    if not (ADMIN_API_URL and ADMIN_PASSWORD):
        return []

    import urllib.request
    import urllib.parse

    try:
        url = f"{ADMIN_API_URL}?password={urllib.parse.quote(ADMIN_PASSWORD)}"
        req = urllib.request.Request(url, headers=_API_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log(f"⚠️ Could not read the client list ({str(e)[:80]}).")
        if "403" in str(e):
            log("   A 403 here is Cloudflare, not the password — the request "
                "was refused before the endpoint ran. Add a WAF skip rule for "
                "/api/* so server-to-server calls get through.")
        return []

    if payload.get("notice"):
        log(f"⚠️ {payload['notice']}")
    return payload.get("clients") or []


def select_clients():
    """The rows this run should work through."""
    rows = fetch_clients()

    if ALL_CLIENTS:
        # active only: an inactive client is one whose tracking is switched
        # off, and creating conversion actions for it would be pure noise.
        picked = [c for c in rows if c.get("active")]
        log(f"Selected ALL active clients: {len(picked)} of {len(rows)}")
        return picked

    if CLIENT_TOKENS:
        by_token = {c.get("client_token"): c for c in rows}
        picked, missing = [], []
        for t in CLIENT_TOKENS:
            if t in by_token:
                picked.append(by_token[t])
            else:
                missing.append(t)
        if missing:
            log(f"⚠️ Not found in the client list: {', '.join(missing)}")
        # Setting PUSH_CUSTOMER_ID as well as a token used to be the way to
        # write one account's labels onto another client's row. The row is the
        # authority, so a disagreement is refused rather than silently resolved.
        if PUSH_CUSTOMER_ID and len(picked) == 1:
            resolve_account(picked[0])
        elif PUSH_CUSTOMER_ID and len(picked) > 1:
            log("⚠️ PUSH_CUSTOMER_ID ignored — several clients selected, and "
                "each one's account comes off its own row.")
        return picked

    # No token at all: the old single-account path, for a one-off run against
    # an account that has no client row yet.
    if PUSH_CUSTOMER_ID:
        return [{"website_name": f"account {PUSH_CUSTOMER_ID}",
                 "customer_id": PUSH_CUSTOMER_ID, "client_token": None}]
    return []


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
        return row_cid

    return PUSH_CUSTOMER_ID


def write_back(results, row):
    """Put the labels on the client_keys row, through the admin endpoint.

    Returns True only if the row actually took them. The caller used to
    announce "labels written" whichever way this went, so a client whose row
    received nothing still got a green tick in the summary — and the labels
    were only missed later, when the generated middleware came out with an
    empty AW id.
    """
    import time
    import urllib.request
    import urllib.error

    if not (ADMIN_API_URL and ADMIN_PASSWORD and (row or {}).get("client_token")):
        log("ℹ️ ADMIN_API_URL / ADMIN_PASSWORD / CLIENT_TOKEN not all set — "
            "labels not written back. Paste them into the admin page by hand, "
            "or set the three and re-run.")
        return False

    if not row:
        log("⚠️ no client row — nothing written back.")
        return False

    payload = {
        "password": ADMIN_PASSWORD,
        "client_token": row["client_token"],
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
    # Cloudflare rate limits /api/*. The client list was read a few seconds
    # ago and this is the second call — measured live, two seconds apart earns
    # a 429 and five seconds apart does not, which is exactly where this lands.
    # Waiting is the whole fix, and it has to be automatic: by the time this
    # runs the actions exist in Google and only the row is missing.
    for attempt in range(1, 6):
        try:
            req = urllib.request.Request(
                ADMIN_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers=dict(_API_HEADERS, **{"Content-Type": "application/json"}),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                r.read()
            log(f"✅ Labels written to client_keys row '{row.get('website_name')}'.")
            log("   Admin page ab ye 4 fields khud bhar lega — middleware generate kar lein.")
            return True
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 5:
                try:
                    wait = int(e.headers.get("Retry-After", "") or 10)
                except (TypeError, ValueError):
                    wait = 10
                wait = min(max(wait, 1) + 1, 60)
                log(f"   ⏳ rate limited writing the row — waiting {wait}s "
                    f"(attempt {attempt} of 5)")
                time.sleep(wait)
                continue
            body = e.read().decode("utf-8", "replace")[:200]
            log(f"⚠️ Write-back failed ({e.code}): {body}")
            return False
        except Exception as e:
            log(f"⚠️ Write-back failed: {str(e)[:120]}")
            return False

    return False


def run_one(client, svc, ca_svc, row, validate, GoogleAdsException):
    """One client: create what is missing, read the labels, write them back.

    Returns a short status string for the run summary. Never raises — one
    client's Ads account being misconfigured must not stop the other sixteen.
    """
    global PUSH_CUSTOMER_ID
    name = (row or {}).get("website_name", "?")
    PUSH_CUSTOMER_ID = "".join(c for c in str((row or {}).get("customer_id") or "")
                               if c.isdigit())
    if not PUSH_CUSTOMER_ID:
        log(f"⚠️ {name}: no customer_id on the client row — skipped.")
        return "no customer_id"

    log("")
    log(f"── {name}  (account {PUSH_CUSTOMER_ID}) " + "─" * 20)

    try:
        existing = fetch_actions(svc, list(ACTIONS.keys()))
    except Exception as e:
        log(f"❌ {name}: could not read conversion actions — {str(e)[:100]}")
        return "read failed"

    for n in existing:
        log(f"   already exists: {n}")
    missing = [n for n in ACTIONS if n not in existing]

    if missing:
        ops = [build_create_op(client, n, ACTIONS[n]) for n in missing]
        try:
            # validate_only lives on the request message, not on the method:
            # mutate_conversion_actions() only takes request / customer_id /
            # operations, so passing it as a keyword raises TypeError before a
            # single call reaches Google.
            req = client.get_type("MutateConversionActionsRequest")
            req.customer_id = PUSH_CUSTOMER_ID
            req.operations.extend(ops)
            req.validate_only = validate
            ca_svc.mutate_conversion_actions(request=req)
        except GoogleAdsException as e:
            for err in e.failure.errors[:5]:
                log(f"❌ {name}: {err.message}")
            return "rejected by Google"
        except Exception as e:
            log(f"❌ {name}: {str(e)[:120]}")
            return "failed"

        if validate:
            log(f"✅ VALIDATE ok — would create {len(missing)}: " + ", ".join(missing))
        else:
            log(f"✅ Created {len(missing)}: " + ", ".join(missing))
            existing = fetch_actions(svc, list(ACTIONS.keys()))
    else:
        log("✅ All three already present — nothing to create.")

    results = {"customer_id": PUSH_CUSTOMER_ID, "website_name": name,
               "aw_id": None, "actions": {}}
    for n, spec in ACTIONS.items():
        info = existing.get(n)
        if not info:
            results["actions"][n] = {"column": spec["column"], "label": None}
            continue
        aw_id, label = parse_label(info["snippets"])
        if aw_id:
            results["aw_id"] = aw_id
        results["actions"][n] = {"column": spec["column"], "id": info["id"],
                                 "label": label, "primary": spec["primary"]}

    log(f"   AW id: {results['aw_id'] or '(not available yet)'}")
    for n, spec in ACTIONS.items():
        log(f"   {spec['column']:<16} {results['actions'][n].get('label') or '(none yet)'}")

    # A label is minted BY the conversion action existing. In check mode none
    # were created, so blank labels here are the mode working, not a failure —
    # but they look identical to one, which is why this line exists.
    if validate and missing:
        log("")
        log("   ℹ️  Labels are blank because this was a CHECK run — nothing was")
        log("      created, so Google has no tag to give a label to. Re-run with")
        log("      mode: create to actually make the actions and mint them.")

    ALL_RESULTS.append(results)

    if results["aw_id"] and all(results["actions"][n].get("label") for n in ACTIONS):
        if validate:
            return "validated"
        if write_back(results, row):
            return "labels written"
        # Google has the actions and the labels; the row does not. Nothing
        # needs creating again — say so, and say where the labels are, because
        # the artifact has them and they can be pasted in by hand.
        log("")
        log("   ⚠️  The actions and labels exist in Google, but the client row")
        log("      did not take them. Nothing needs creating again. Either")
        log("      re-run this (it will find what it made and retry the row),")
        log("      or copy the four values out of conversion_actions.json into")
        log("      the admin page by hand.")
        return "row not updated"
    if validate:
        return "validated"
    return "labels not minted yet"


def main():
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException

    validate = CONV_MODE != "live"

    # Which clients this run covers. One token, several, or every active
    # client — 17 clients was 34 separate workflow runs otherwise, which is
    # the kind of chore nobody finishes.
    rows = select_clients()
    if not rows:
        print("❌ No client selected. Set CLIENT_TOKEN to a token, a comma-separated "
              "list, or 'all'; or set PUSH_CUSTOMER_ID for a one-off account.")
        sys.exit(1)

    log(f"# Google Ads conversion setup — {len(rows)} client(s)")
    log(f"Mode: {'VALIDATE (nothing created)' if validate else 'LIVE'}")
    log("Primary (feeds bidding): "
        + ", ".join(sorted(k for k, v in ACTIONS.items() if v["primary"]) or ["(none)"])
        + " | Secondary: "
        + ", ".join(sorted(k for k, v in ACTIONS.items() if not v["primary"]) or ["(none)"]))
    if not any(v["primary"] for v in ACTIONS.values()):
        log("⚠️ No primary conversion — bidding would have nothing to optimise "
            "for. Set PRIMARY_CONVERSIONS, e.g. phone,whatsapp,form")

    client = GoogleAdsClient.load_from_env()
    svc = client.get_service("GoogleAdsService")
    ca_svc = client.get_service("ConversionActionService")

    summary = []
    for row in rows:
        try:
            status = run_one(client, svc, ca_svc, row, validate, GoogleAdsException)
        except Exception as e:
            status = f"error: {str(e)[:60]}"
            log(f"❌ {row.get('website_name','?')}: {status}")
        summary.append((row.get("website_name", "?"), status))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(ALL_RESULTS if len(ALL_RESULTS) != 1 else ALL_RESULTS[0],
                  f, indent=2, ensure_ascii=False)

    log("")
    log("=" * 60)
    log(f"SUMMARY — {len(summary)} client(s)")
    log("=" * 60)
    for name, status in summary:
        mark = "✅" if status in ("labels written", "validated") else "⚠️"
        log(f"  {mark} {name:<32} {status}")
    log(f"→ {OUTPUT_FILE}")

    if validate:
        log("")
        log("ℹ️  CHECK RUN — nothing was created and no labels were minted.")
        log("   That is what check mode is for: it proves Google would accept")
        log("   these actions before any are made. The labels the middleware")
        log("   needs only exist once the actions do.")
        log("   NEXT: run this again with mode: create.")

    if any(st == "labels not minted yet" for _, st in summary):
        log("")
        log("⚠️  Some actions were created but Google had not attached their tag")
        log("   snippets yet. Nothing is wrong and nothing needs creating again —")
        log("   re-run in create mode in a few minutes and it will find what it")
        log("   made and read the labels off it.")

    log("")
    log("⚠️ Ab Google Ads me purani GA4-imported conversions ko Remove ya "
        "Secondary kar dein — warna har lead do baar ginegi. GA4 ka Ads se "
        "LINK rehne dein; sirf IMPORT band karna hai.")


if __name__ == "__main__":
    main()
