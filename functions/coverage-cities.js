// functions/coverage-cities.js  (Cloudflare Pages Functions)
//
// GET /coverage-cities?state=NM&niche=Plumbing
//
// The towns in one state where LeadSmart buys one niche, largest first, with
// the population, ZIP count and best payout for each. The EMD finder form
// fills its town list from this, so every town offered is a town with a buyer.
//
// Server-side because the coverage feed sends no CORS header: a browser on
// this site cannot read it directly. Cached at the edge for an hour; the feed
// itself only changes once a day.

const FEED = "https://leadsmart-coverage.netlify.app/api/state/";

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=3600" },
  });
}

export async function onRequestGet({ request }) {
  const url = new URL(request.url);
  const state = (url.searchParams.get("state") || "").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 2);
  const niche = String(url.searchParams.get("niche") || "").slice(0, 60);
  if (state.length !== 2 || !niche) {
    return json({ error: "state (two letters) and niche are required" }, 400);
  }

  let shard;
  try {
    const r = await fetch(FEED + state + ".json", { cf: { cacheTtl: 3600, cacheEverything: true } });
    if (!r.ok) return json({ error: `coverage feed answered ${r.status} for ${state}` }, 502);
    shard = await r.json();
  } catch (e) {
    return json({ error: "coverage feed unreachable" }, 502);
  }

  const city = shard.city || [], nich = shard.niche || [], ptype = shard.ptype || [];
  const byTown = {};
  for (const row of shard.rows || []) {
    if (nich[row[2]] !== niche) continue;
    const name = city[row[0]];
    if (!name) continue;
    const e = byTown[name] || (byTown[name] = { city: name, pop: 0, zips: 0, payout: 0, ptypes: {} });
    e.zips += 1;
    e.pop = Math.max(e.pop, Number(row[5]) || 0);
    e.payout = Math.max(e.payout, Number(row[4]) || 0);
    const pt = ptype[row[3]];
    if (pt) e.ptypes[pt] = true;
  }
  const cities = Object.values(byTown)
    .map((e) => ({ city: e.city, pop: e.pop, zips: e.zips,
                   payout: Math.round(e.payout * 100) / 100,
                   ptypes: Object.keys(e.ptypes).sort().join("/") }))
    .sort((a, b) => b.pop - a.pop);

  return json({ state, niche, count: cities.length, cities });
}
