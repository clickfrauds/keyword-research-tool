// functions/coverage-cities.js  (Cloudflare Pages Functions)
//
// GET /coverage-cities?state=NM&feed_niche=Plumbing
//
// The towns in one state, largest first, with population, and — for the niche
// asked about — the ZIP count and best payout the coverage feed carries.
//
// The town list is the UNION across every niche in the shard, not the towns
// carrying that one niche. The feed is a snapshot of where bids happen to be
// live right now, while the campaigns themselves are Nationwide: New Mexico
// lists 16 towns under Electrical and 359 towns in total, and the Electrician
// campaign is sold as nationwide. Filtering by the one niche was hiding towns
// the campaign covers. `bids` says whether that niche is live in the town, so
// the form can show it without refusing the rest.
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
  // `feed_niche` is the coverage feed's own label; `niche` is accepted as the
  // older name for it. Either may be blank — then every town is returned with
  // no payout, which is what a campaign the feed does not carry needs.
  const want = String(url.searchParams.get("feed_niche") || url.searchParams.get("niche") || "").slice(0, 60);
  if (state.length !== 2) return json({ error: "state (two letters) is required" }, 400);

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
    const name = city[row[0]];
    if (!name) continue;
    const e = byTown[name] || (byTown[name] = { city: name, pop: 0, zips: 0, payout: 0, bids: false, ptypes: {} });
    e.pop = Math.max(e.pop, Number(row[5]) || 0);
    // With no niche asked about, the town is still listed but nothing is
    // attributed to it: summing every niche's payout would show a dentist
    // campaign the pest control rate.
    if (!want || nich[row[2]] !== want) continue;
    e.bids = true;
    e.zips += 1;
    e.payout = Math.max(e.payout, Number(row[4]) || 0);
    const pt = ptype[row[3]];
    if (pt) e.ptypes[pt] = true;
  }
  const cities = Object.values(byTown)
    .map((e) => ({ city: e.city, pop: e.pop, zips: e.zips, bids: e.bids,
                   payout: Math.round(e.payout * 100) / 100,
                   ptypes: Object.keys(e.ptypes).sort().join("/") }))
    .sort((a, b) => b.pop - a.pop);

  return json({ state, feed_niche: want || null, count: cities.length,
                with_bids: cities.filter((c) => c.bids).length, cities });
}
