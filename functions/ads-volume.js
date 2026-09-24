// functions/ads-volume.js  (Cloudflare Pages Functions)
//
// POST { towns: [{ state, town, terms: ["electricians", "roofers"] }, ...] }
//   -> { results: { "OK|Duncan|electricians": 140, ... }, geo: {...}, unresolved: [...] }
//
// The search volume for the EMD's own keyword, measured INSIDE the town, on
// demand from the /towns table. Same method as emd_finder.py, so the two
// cannot disagree:
//
//   - every town gets its OWN geo target, matched strictly: target_type City
//     AND canonical name = this town in this state. Taking the first
//     suggestion returned Clovis, California for Clovis, New Mexico once, and
//     a whole plan was written on the wrong state's numbers.
//   - both word orders are asked for ("duncan electricians" / "electricians
//     duncan") and the larger is kept.
//   - every term for a town rides in one request, so a town costs one geo
//     call and one volume call whatever its trade count.
//
// Google Ads calls are free. The cost here is subrequests: Cloudflare caps
// them per request, so MAX_TOWNS keeps one call well inside that and the page
// sends the rest in the next batch.
//
// SETUP — these five have to exist as environment variables on the Pages
// project (Settings -> Environment variables). Without them this returns a
// clear 503 rather than pretending:
//   GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET,
//   GOOGLE_ADS_REFRESH_TOKEN, GOOGLE_ADS_CUSTOMER_ID

const API = "https://googleads.googleapis.com/v23";
const MAX_TOWNS = 20;

const STATE_NAMES = {
  AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California",
  CO: "Colorado", CT: "Connecticut", DE: "Delaware", FL: "Florida", GA: "Georgia",
  HI: "Hawaii", ID: "Idaho", IL: "Illinois", IN: "Indiana", IA: "Iowa",
  KS: "Kansas", KY: "Kentucky", LA: "Louisiana", ME: "Maine", MD: "Maryland",
  MA: "Massachusetts", MI: "Michigan", MN: "Minnesota", MS: "Mississippi",
  MO: "Missouri", MT: "Montana", NE: "Nebraska", NV: "Nevada",
  NH: "New Hampshire", NJ: "New Jersey", NM: "New Mexico", NY: "New York",
  NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma",
  OR: "Oregon", PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina",
  SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah", VT: "Vermont",
  VA: "Virginia", WA: "Washington", WV: "West Virginia", WI: "Wisconsin",
  WY: "Wyoming", DC: "District of Columbia",
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

// "St. George" == "Saint George", and case and punctuation never matter.
function norm(s) {
  return String(s || "").toLowerCase().replace(/&/g, "and")
    .replace(/\bst\.?\s/g, "saint ").replace(/[^a-z0-9]/g, "");
}

async function accessToken(env) {
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: env.GOOGLE_ADS_CLIENT_ID,
      client_secret: env.GOOGLE_ADS_CLIENT_SECRET,
      refresh_token: env.GOOGLE_ADS_REFRESH_TOKEN,
      grant_type: "refresh_token",
    }),
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok || !d.access_token) {
    throw new Error("refresh token rejected: " + (d.error_description || d.error || r.status));
  }
  return d.access_token;
}

function headers(env, token) {
  return {
    "Authorization": "Bearer " + token,
    "developer-token": env.GOOGLE_ADS_DEVELOPER_TOKEN,
    "Content-Type": "application/json",
  };
  // No login-customer-id on purpose: find_opportunities logged "does not
  // manage this account" on every run with it set, doubling the calls.
}

async function geoFor(env, token, town, state) {
  const stateName = STATE_NAMES[state] || state;
  const r = await fetch(`${API}/geoTargetConstants:suggest`, {
    method: "POST", headers: headers(env, token),
    body: JSON.stringify({
      locale: "en", countryCode: "US",
      locationNames: { names: [`${town}, ${stateName}`] },
    }),
  });
  if (!r.ok) return { id: null, why: "geo lookup " + r.status };
  const d = await r.json();
  for (const s of (d.geoTargetConstantSuggestions || [])) {
    const g = s.geoTargetConstant || {};
    const parts = String(g.canonicalName || "").split(",").map((x) => x.trim());
    if (parts.length >= 2 && g.targetType === "CITY"
        && norm(parts[0]) === norm(town) && norm(parts[1]) === norm(stateName)) {
      // resourceName is "geoTargetConstants/1014339"
      return { id: String(g.resourceName || "").split("/").pop(), name: g.canonicalName };
    }
  }
  return { id: null, why: "no City match in " + stateName };
}

async function volumesFor(env, token, geoId, keywords) {
  const cid = String(env.GOOGLE_ADS_CUSTOMER_ID || "").replace(/\D/g, "");
  const r = await fetch(`${API}/customers/${cid}:generateKeywordHistoricalMetrics`, {
    method: "POST", headers: headers(env, token),
    body: JSON.stringify({
      keywords,
      geoTargetConstants: ["geoTargetConstants/" + geoId],
      keywordPlanNetwork: "GOOGLE_SEARCH",
    }),
  });
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error("planner " + r.status + " " + t.slice(0, 160));
  }
  const d = await r.json();
  const out = {};
  for (const row of (d.results || [])) {
    const m = row.keywordMetrics || {};
    out[String(row.text || "").toLowerCase()] = Number(m.avgMonthlySearches || 0);
  }
  return out;
}

export async function onRequestPost({ request, env }) {
  const missing = ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
                   "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN",
                   "GOOGLE_ADS_CUSTOMER_ID"].filter((k) => !env[k]);
  if (missing.length) {
    return json({ error: "Google Ads is not configured on this site. Add these as "
                       + "environment variables on the Pages project: " + missing.join(", ") }, 503);
  }

  let body;
  try { body = await request.json(); } catch (e) {
    return json({ error: "send JSON: { towns: [{state, town, terms}] }" }, 400);
  }
  const towns = (body.towns || []).slice(0, MAX_TOWNS).filter(
    (t) => t && t.state && t.town && Array.isArray(t.terms) && t.terms.length);
  if (!towns.length) return json({ error: "no towns in the request" }, 400);

  let token;
  try { token = await accessToken(env); }
  catch (e) { return json({ error: String(e.message || e) }, 502); }

  const results = {}, geo = {}, unresolved = [];
  for (const t of towns) {
    const g = await geoFor(env, token, t.town, t.state);
    if (!g.id) { unresolved.push({ town: t.town, state: t.state, why: g.why }); continue; }
    geo[t.state + "|" + t.town] = g.name;

    const kws = [];
    for (const term of t.terms) {
      kws.push(`${t.town} ${term}`.toLowerCase(), `${term} ${t.town}`.toLowerCase());
    }
    let vol;
    try { vol = await volumesFor(env, token, g.id, kws); }
    catch (e) { unresolved.push({ town: t.town, state: t.state, why: String(e.message || e) }); continue; }

    for (const term of t.terms) {
      const a = vol[`${t.town} ${term}`.toLowerCase()] || 0;
      const b = vol[`${term} ${t.town}`.toLowerCase()] || 0;
      results[`${t.state}|${t.town}|${term}`] = Math.max(a, b);
    }
  }

  return json({ measured: Object.keys(geo).length, results, geo, unresolved,
                remaining: Math.max(0, (body.towns || []).length - towns.length) });
}
