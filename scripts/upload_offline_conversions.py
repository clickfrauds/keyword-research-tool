"""
upload_offline_conversions.py  (STAGE 9 — offline conversion upload)
----------------------------------------------------------------------
Sends the leads that turned into paying work back to Google Ads, against
the exact ad click that produced them, carrying what the job was worth.

WHY THIS EXISTS
  Everything upstream of here optimises for the wrong thing. The three
  website conversion actions — phone click, WhatsApp click, form submit —
  can only report that somebody made contact. They cannot tell a
  time-waster from a five-thousand-dirham job, so Smart Bidding spends
  the budget chasing whoever is cheapest to make click, which is very
  often the customer nobody wants.

  A gclid is the thread back to the click. The middleware stores it with
  the lead, a person marks the outcome on /leads, and this script closes
  the loop: click X became a job worth Y. From then on bidding is chasing
  revenue instead of form fills.

WHAT IT WILL NOT TOUCH
  - The three website conversion actions. They stay exactly as they are
    and keep firing. This script creates and uses a SEPARATE action of
    type UPLOAD_CLICKS, because a webpage action physically cannot
    receive an upload.
  - Bidding. The new action is created with primary_for_goal FALSE, so
    nothing about how the account spends money changes on the day it
    appears. Promoting it is a decision with real consequences and it is
    made by a person, in the UI, once the numbers look right.
  - The Supabase `conversions` table. That is the FRAUD system's trust
    anchor. The only table behind this script is `leads`, reached through
    the admin endpoint — never with the service role key on the runner.

WHY IT CANNOT BATCH CLIENTS TOGETHER
  Google matches a gclid inside the account that served the click. Ten
  clients are ten accounts, so ten separate uploads — one run for you,
  ten conversations with Google. Mixing them would simply be rejected.

DOUBLE-COUNTING
  A conversion sent twice inflates the account permanently and there is
  no undo. Two guards: only rows with uploaded_at IS NULL are fetched,
  and a row is stamped only after Google accepts it. A crash between the
  two leaves the row unstamped, so it is retried — sending late is
  recoverable, sending twice is not.

SAFETY MODEL
  UPLOAD_MODE=validate (default): Google checks every conversion and
    reports what would fail, creating nothing and stamping nothing.
  UPLOAD_MODE=live: uploads, then stamps what Google accepted.

Env : ADMIN_API_URL + LEADS_API_URL + ADMIN_PASSWORD (the leads endpoint),
      CLIENT_TOKEN ("all" or comma-separated), UPLOAD_MODE (validate|live),
      OFFLINE_ACTION_NAME (default "Job (offline)"),
      MAX_AGE_DAYS (default 90 — Google's ceiling),
      GOOGLE_ADS_* client env vars, GOOGLE_ADS_LOGIN_CUSTOMER_ID (MCC)
Output: offline_conversions.json (+ log lines)
"""

import os
import sys
import json
import time
import datetime as dt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ADMIN_API_URL = os.environ.get("ADMIN_API_URL", "").strip().rstrip("/")
LEADS_API_URL = os.environ.get("LEADS_API_URL", "").strip().rstrip("/")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

CLIENT_TOKEN = os.environ.get("CLIENT_TOKEN", "all").strip()
CLIENT_TOKENS = [t.strip() for t in CLIENT_TOKEN.split(",") if t.strip()]
ALL_CLIENTS = CLIENT_TOKEN.lower() in ("all", "*")

UPLOAD_MODE = os.environ.get("UPLOAD_MODE", "validate").strip().lower()
LIVE = UPLOAD_MODE == "live"

OFFLINE_ACTION_NAME = os.environ.get("OFFLINE_ACTION_NAME", "").strip() or "Job (offline)"

# Google rejects a conversion whose click is older than the action's
# click-through window, and 90 days is the widest that window goes.
try:
    MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "") or 90)
except ValueError:
    MAX_AGE_DAYS = 90
MAX_AGE_DAYS = max(1, min(MAX_AGE_DAYS, 90))

# The API's documented ceiling for one upload request.
CHUNK = 2000

OUTPUT_FILE = "offline_conversions.json"

_LOG = []


def log(msg):
    print(msg, flush=True)
    _LOG.append(msg)


# Cloudflare's Browser Integrity Check refuses a request whose headers do not
# look like a browser's — a 403 raised before the function ever runs, so the
# password is never even examined. urllib sends no User-Agent by default.
_API_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


# Cloudflare rate limits /api/*: a second call a couple of seconds after the
# first comes back 429 with Retry-After: 10. A run covering several clients
# makes one call per client, so it will meet that limit. Waiting is the whole
# fix — but it has to be automatic, because the call that matters most is the
# stamp, and by then Google already holds the conversions.
RATE_LIMIT_TRIES = 6


def _open(req, what):
    import urllib.error
    import urllib.request

    for attempt in range(1, RATE_LIMIT_TRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == RATE_LIMIT_TRIES:
                raise
            # Cloudflare says how long it wants; trust it, and add a second so
            # a clock that rounds down does not send us straight back into it.
            try:
                wait = int(e.headers.get("Retry-After", "") or 10)
            except (TypeError, ValueError):
                wait = 10
            wait = min(max(wait, 1) + 1, 60)
            log(f"   ⏳ rate limited on {what} — waiting {wait}s "
                f"(attempt {attempt} of {RATE_LIMIT_TRIES})")
            time.sleep(wait)

    raise RuntimeError("unreachable")


def _get(url):
    import urllib.request
    req = urllib.request.Request(url, headers=_API_HEADERS)
    return _open(req, "read")


def _post(url, payload):
    import urllib.request
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=dict(_API_HEADERS, **{"Content-Type": "application/json"}),
        method="POST",
    )
    return _open(req, "write")


def fetch_clients():
    """Every client_keys row, through the admin endpoint.

    Read there and never straight from Supabase: a direct call would need the
    service role key on whatever machine runs this, and that key can read and
    rewrite every table the fraud system depends on.
    """
    import urllib.parse
    try:
        url = f"{ADMIN_API_URL}?password={urllib.parse.quote(ADMIN_PASSWORD)}"
        payload = _get(url)
    except Exception as e:
        log(f"❌ Could not read the client list ({str(e)[:100]}).")
        if "403" in str(e):
            log("   A 403 here is Cloudflare, not the password. Add a WAF skip "
                "rule for /api/* so server-to-server calls get through.")
        return []
    return payload.get("clients") or []


def fetch_pending():
    """Jobs waiting to be sent, newest last so a truncated run is contiguous."""
    import urllib.parse
    try:
        url = (f"{LEADS_API_URL}?password={urllib.parse.quote(ADMIN_PASSWORD)}"
               f"&pending=1&limit=500")
        payload = _get(url)
    except Exception as e:
        log(f"❌ Could not read pending leads ({str(e)[:100]}).")
        return []
    return payload.get("leads") or []


def stamp_uploaded(ids):
    """Record that Google took these. Only ever called after it did."""
    if not ids:
        return 0
    try:
        res = _post(LEADS_API_URL,
                    {"password": ADMIN_PASSWORD, "mark_uploaded": True, "ids": ids})
        return int(res.get("stamped") or 0)
    except Exception as e:
        # This is the dangerous failure: Google has the conversions but the
        # rows still look pending, so the next run would send them again.
        log(f"❌ UPLOADED BUT NOT STAMPED — {str(e)[:100]}")
        log(f"   Ids Google accepted: {ids}")
        log("   Do NOT re-run until these are stamped, or they will be counted "
            "twice. In Supabase: UPDATE leads SET uploaded_at = now() "
            f"WHERE id IN ({','.join(str(i) for i in ids)});")
        return -1


def parse_created(iso):
    """Supabase timestamptz -> aware datetime, or None."""
    if not iso:
        return None
    txt = str(iso).strip().replace("Z", "+00:00")
    # Postgres emits more than six fractional digits; datetime accepts six.
    if "." in txt:
        head, _, tail = txt.partition(".")
        digits = "".join(c for c in tail if c.isdigit())[:6]
        rest = tail[len(digits):] if not tail[:1].isdigit() else tail.lstrip("0123456789")
        txt = f"{head}.{digits or '0'}{rest}"
    try:
        d = dt.datetime.fromisoformat(txt)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def conversion_time(d):
    """Google's required shape: 'yyyy-MM-dd HH:mm:ss+HH:MM'."""
    d = d.astimezone(dt.timezone.utc)
    return d.strftime("%Y-%m-%d %H:%M:%S+00:00")


def ensure_action(client, ca_svc, ga_svc, customer_id):
    """Find, or create, the account's UPLOAD_CLICKS action.

    Matching is by exact name. Two actions with the same purpose would split
    the history and give Smart Bidding half a picture of the same thing.
    """
    safe = OFFLINE_ACTION_NAME.replace("'", "\\'")
    query = f"""
        SELECT conversion_action.resource_name,
               conversion_action.name,
               conversion_action.type,
               conversion_action.status
        FROM conversion_action
        WHERE conversion_action.name = '{safe}'
    """
    try:
        for row in ga_svc.search(customer_id=customer_id, query=query):
            ca = row.conversion_action
            if ca.type_.name != "UPLOAD_CLICKS":
                log(f"   ❌ '{OFFLINE_ACTION_NAME}' exists but is {ca.type_.name}, "
                    "not UPLOAD_CLICKS. A webpage action cannot receive uploads.")
                log("      Rename the existing one, or set OFFLINE_ACTION_NAME "
                    "to something else.")
                return None
            log(f"   ↳ using existing action ({ca.status.name})")
            return ca.resource_name
    except Exception as e:
        log(f"   ⚠️ Could not look up conversion actions: {str(e)[:120]}")
        return None

    if not LIVE:
        log(f"   ↳ would create '{OFFLINE_ACTION_NAME}' (validate mode)")
        return None

    op = client.get_type("ConversionActionOperation")
    ca = op.create
    ca.name = OFFLINE_ACTION_NAME
    ca.type_ = client.enums.ConversionActionTypeEnum.UPLOAD_CLICKS
    # "Became a customer" is exactly what a marked job is, and the category is
    # what Google's own lead-funnel reporting groups on.
    ca.category = client.enums.ConversionActionCategoryEnum.CONVERTED_LEAD
    ca.status = client.enums.ConversionActionStatusEnum.ENABLED
    # One job per click. A repeat customer's second job belongs to whatever
    # click brought them back, not to the first one.
    ca.counting_type = client.enums.ConversionActionCountingTypeEnum.ONE_PER_CLICK
    # The widest window Google allows, so a job closed two months after the
    # click still counts. Service work often takes that long to sign.
    ca.click_through_lookback_window_days = 90
    # Every upload carries its own money, so there is no default to fall back on.
    ca.value_settings.always_use_default_value = False
    # Created deliberately NOT primary: appearing in an account should never
    # change what that account spends. Promotion is a human decision.
    try:
        ca.primary_for_goal = False
    except AttributeError:
        pass

    try:
        res = ca_svc.mutate_conversion_actions(customer_id=customer_id, operations=[op])
        rn = res.results[0].resource_name
        log(f"   ✅ created '{OFFLINE_ACTION_NAME}' (not primary — promote it yourself)")
        return rn
    except Exception as e:
        log(f"   ❌ Could not create the action: {str(e)[:200]}")
        return None


def upload_for_client(client, row, leads, GoogleAdsException):
    """One client, one account, one conversation with Google."""
    name = row.get("website_name") or row.get("client_token")
    customer_id = "".join(c for c in str(row.get("customer_id") or "") if c.isdigit())

    log("")
    log(f"── {name} ({len(leads)} pending)")

    if not customer_id:
        log("   ⏭️  no customer_id on the client row — nothing to upload into")
        return {"client": name, "skipped": "no customer_id", "sent": 0}

    ga_svc = client.get_service("GoogleAdsService")
    ca_svc = client.get_service("ConversionActionService")

    action = ensure_action(client, ca_svc, ga_svc, customer_id)
    if not action:
        return {"client": name, "skipped": "no conversion action", "sent": 0}

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MAX_AGE_DAYS)

    conversions, ids, too_old, bad = [], [], [], []
    for lead in leads:
        created = parse_created(lead.get("created_at"))
        if not created:
            bad.append((lead.get("id"), "unreadable timestamp"))
            continue
        if created < cutoff:
            # Past the window there is no click left to attach to. Say so
            # rather than letting Google reject it every month forever.
            too_old.append(lead.get("id"))
            continue
        try:
            value = float(lead.get("value") or 0)
        except (TypeError, ValueError):
            value = 0.0
        if value <= 0:
            bad.append((lead.get("id"), "no value"))
            continue

        cc = client.get_type("ClickConversion")
        cc.gclid = str(lead.get("gclid") or "").strip()
        cc.conversion_action = action
        cc.conversion_date_time = conversion_time(created)
        cc.conversion_value = value
        cc.currency_code = (lead.get("currency") or "AED").strip().upper()[:3]
        # The lead's row id, so a retry Google has already seen is recognised
        # as the same conversion rather than a second one.
        cc.order_id = f"lead-{lead.get('id')}"
        conversions.append(cc)
        ids.append(int(lead["id"]))

    if too_old:
        log(f"   ⚠️ {len(too_old)} past {MAX_AGE_DAYS} days — the click is gone, "
            "these can never be uploaded")
    for lid, why in bad:
        log(f"   ⚠️ lead {lid} skipped: {why}")

    if not conversions:
        log("   nothing uploadable")
        return {"client": name, "sent": 0, "too_old": len(too_old), "skipped_rows": len(bad)}

    sent, failures = 0, []
    svc = client.get_service("ConversionUploadService")

    for start in range(0, len(conversions), CHUNK):
        batch = conversions[start:start + CHUNK]
        batch_ids = ids[start:start + CHUNK]

        req = client.get_type("UploadClickConversionsRequest")
        req.customer_id = customer_id
        req.conversions.extend(batch)
        # Per-row errors instead of losing the whole batch to one bad gclid.
        req.partial_failure = True
        req.validate_only = not LIVE

        try:
            res = svc.upload_click_conversions(request=req)
        except GoogleAdsException as e:
            log(f"   ❌ upload refused: {e.error.code().name}")
            for err in e.failure.errors[:5]:
                log(f"      {err.message}")
            failures.append(str(e.error.code().name))
            continue

        # partial_failure_error carries one entry per rejected row; the
        # results list has a blank entry where a row failed.
        ok_ids = []
        for i, result in enumerate(res.results):
            if getattr(result, "gclid", "") or getattr(result, "conversion_action", ""):
                ok_ids.append(batch_ids[i])

        if res.partial_failure_error and res.partial_failure_error.message:
            log(f"   ⚠️ some rows rejected: {res.partial_failure_error.message[:200]}")

        sent += len(ok_ids)

        if LIVE and ok_ids:
            stamped = stamp_uploaded(ok_ids)
            if stamped < 0:
                return {"client": name, "sent": sent, "error": "stamp failed"}
            log(f"   ✅ {len(ok_ids)} uploaded and stamped")
        elif not LIVE:
            log(f"   ✓ {len(batch)} would upload cleanly (validate mode — "
                "nothing sent, nothing stamped)")

    return {
        "client": name,
        "customer_id": customer_id,
        "sent": sent,
        "too_old": len(too_old),
        "skipped_rows": len(bad),
        "failures": failures,
    }


def main():
    if not (ADMIN_API_URL and LEADS_API_URL and ADMIN_PASSWORD):
        log("❌ ADMIN_API_URL, LEADS_API_URL and ADMIN_PASSWORD are all required.")
        sys.exit(1)

    log("=" * 62)
    log(f"OFFLINE CONVERSION UPLOAD — mode: {UPLOAD_MODE.upper()}")
    if not LIVE:
        log("Nothing will be sent. Set UPLOAD_MODE=live once this looks right.")
    log("=" * 62)

    pending = fetch_pending()
    if not pending:
        log("No jobs waiting. Mark some on /leads first.")
        json.dump({"mode": UPLOAD_MODE, "clients": [], "log": _LOG},
                  open(OUTPUT_FILE, "w", encoding="utf-8"), indent=2)
        return

    by_token = {}
    for lead in pending:
        by_token.setdefault(lead.get("client_token"), []).append(lead)
    log(f"{len(pending)} job(s) waiting across {len(by_token)} client(s).")

    rows = {c.get("client_token"): c for c in fetch_clients()}
    if not rows:
        log("❌ No client rows — cannot tell which account each lead belongs to.")
        sys.exit(1)

    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException

    try:
        client = GoogleAdsClient.load_from_env()
    except Exception as e:
        log(f"❌ Google Ads credentials not usable: {str(e)[:200]}")
        sys.exit(1)

    results = []
    halted = False
    for token, leads in by_token.items():
        if not ALL_CLIENTS and token not in CLIENT_TOKENS:
            continue
        row = rows.get(token)
        if not row:
            log("")
            log(f"── {token}: no client row — skipped")
            results.append({"client": token, "skipped": "unknown client", "sent": 0})
            continue

        # Cheaper than being told to wait: leave a gap between clients so the
        # rate limit is not tripped in the first place.
        if results:
            time.sleep(3)

        outcome = upload_for_client(client, row, leads, GoogleAdsException)
        results.append(outcome)

        # Whatever stopped the stamp — the endpoint, the network, Cloudflare —
        # is almost certainly still broken for the next client too. Carrying on
        # would upload another account's conversions and leave those unstamped
        # as well, turning one recoverable mess into several.
        if outcome.get("error") == "stamp failed":
            log("")
            log("⛔ Stopping here. Every client after this one is untouched.")
            halted = True
            break

    total = sum(r.get("sent") or 0 for r in results)
    log("")
    log("=" * 62)
    if halted:
        log(f"HALTED after {total} conversion(s) reached Google.")
        log("Stamp the ids listed above before running this again.")
    elif LIVE:
        log(f"Uploaded {total} conversion(s) across {len(results)} client(s).")
        log("Google takes up to 3 hours to show these in the account.")
    else:
        log(f"{total} conversion(s) would upload. Re-run with UPLOAD_MODE=live.")
    log("=" * 62)

    json.dump({"mode": UPLOAD_MODE, "clients": results, "log": _LOG},
              open(OUTPUT_FILE, "w", encoding="utf-8"), indent=2)
    log(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
