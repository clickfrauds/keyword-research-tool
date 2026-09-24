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

// The same 90 metros find_opportunities.py uses. A town's distance to the
// nearest one is the single best free filter: every scan so far found the
// suburbs inside 50 miles already taken. Coordinates ride in the feed rows
// (lat = row[7], lng = row[8]), so this costs nothing extra.
const US_METROS = [
  ["New York, NY",40.71,-74.01],["Los Angeles, CA",34.05,-118.24],["Chicago, IL",41.88,-87.63],
  ["Dallas, TX",32.78,-96.8],["Fort Worth, TX",32.76,-97.33],["Houston, TX",29.76,-95.37],
  ["Washington, DC",38.91,-77.04],["Philadelphia, PA",39.95,-75.17],["Miami, FL",25.76,-80.19],
  ["Atlanta, GA",33.75,-84.39],["Boston, MA",42.36,-71.06],["Phoenix, AZ",33.45,-112.07],
  ["San Francisco, CA",37.77,-122.42],["San Jose, CA",37.34,-121.89],
  ["Riverside, CA",33.95,-117.4],["Detroit, MI",42.33,-83.05],["Seattle, WA",47.61,-122.33],
  ["Minneapolis, MN",44.98,-93.27],["San Diego, CA",32.72,-117.16],["Tampa, FL",27.95,-82.46],
  ["Denver, CO",39.74,-104.99],["Baltimore, MD",39.29,-76.61],["St. Louis, MO",38.63,-90.2],
  ["Orlando, FL",28.54,-81.38],["Charlotte, NC",35.23,-80.84],["San Antonio, TX",29.42,-98.49],
  ["Portland, OR",45.52,-122.68],["Sacramento, CA",38.58,-121.49],
  ["Pittsburgh, PA",40.44,-80.0],["Austin, TX",30.27,-97.74],["Las Vegas, NV",36.17,-115.14],
  ["Cincinnati, OH",39.1,-84.51],["Kansas City, MO",39.1,-94.58],["Columbus, OH",39.96,-83.0],
  ["Indianapolis, IN",39.77,-86.16],["Cleveland, OH",41.5,-81.69],
  ["Nashville, TN",36.16,-86.78],["Virginia Beach, VA",36.85,-75.98],
  ["Providence, RI",41.82,-71.41],["Jacksonville, FL",30.33,-81.66],
  ["Milwaukee, WI",43.04,-87.91],["Raleigh, NC",35.78,-78.64],
  ["Oklahoma City, OK",35.47,-97.52],["Memphis, TN",35.15,-90.05],["Richmond, VA",37.54,-77.44],
  ["Louisville, KY",38.25,-85.76],["New Orleans, LA",29.95,-90.07],
  ["Salt Lake City, UT",40.76,-111.89],["Hartford, CT",41.77,-72.67],
  ["Buffalo, NY",42.89,-78.88],["Birmingham, AL",33.52,-86.8],["Rochester, NY",43.16,-77.61],
  ["Grand Rapids, MI",42.96,-85.67],["Tucson, AZ",32.22,-110.97],["Tulsa, OK",36.15,-95.99],
  ["Fresno, CA",36.74,-119.79],["Omaha, NE",41.26,-95.93],["Albuquerque, NM",35.08,-106.65],
  ["El Paso, TX",31.76,-106.49],["Wichita, KS",37.69,-97.34],["Jackson, MS",32.3,-90.18],
  ["Little Rock, AR",34.75,-92.29],["Baton Rouge, LA",30.45,-91.19],
  ["Knoxville, TN",35.96,-83.92],["Chattanooga, TN",35.05,-85.31],["Columbia, SC",34.0,-81.03],
  ["Greenville, SC",34.85,-82.4],["Charleston, SC",32.78,-79.93],
  ["Des Moines, IA",41.59,-93.62],["Madison, WI",43.07,-89.4],["Boise, ID",43.62,-116.2],
  ["Spokane, WA",47.66,-117.43],["Albany, NY",42.65,-73.76],["Syracuse, NY",43.05,-76.15],
  ["Allentown, PA",40.6,-75.47],["Harrisburg, PA",40.27,-76.88],["Dayton, OH",39.76,-84.19],
  ["Toledo, OH",41.65,-83.54],["Akron, OH",41.08,-81.52],["Lexington, KY",38.04,-84.5],
  ["Greensboro, NC",36.07,-79.79],["Mobile, AL",30.69,-88.04],["Huntsville, AL",34.73,-86.59],
  ["Montgomery, AL",32.38,-86.3],["Shreveport, LA",32.53,-93.75],["Pensacola, FL",30.42,-87.22],
  ["Fort Myers, FL",26.64,-81.87],["Lakeland, FL",28.04,-81.95],
  ["Colorado Springs, CO",38.83,-104.82],["Bakersfield, CA",35.37,-119.02]
];

function miles(aLat, aLng, bLat, bLng) {
  const R = 3958.8, toRad = Math.PI / 180;
  const dLat = (bLat - aLat) * toRad, dLng = (bLng - aLng) * toRad;
  const s = Math.sin(dLat / 2) ** 2 +
            Math.cos(aLat * toRad) * Math.cos(bLat * toRad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

function nearestMetro(lat, lng) {
  if (!isFinite(lat) || !isFinite(lng) || (!lat && !lng)) return { metro: null, metro_miles: null };
  let best = null;
  for (const [name, mLat, mLng] of US_METROS) {
    const d = miles(lat, lng, mLat, mLng);
    if (!best || d < best[1]) best = [name, d];
  }
  return best ? { metro: best[0], metro_miles: Math.round(best[1]) } : { metro: null, metro_miles: null };
}

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
    const e = byTown[name] || (byTown[name] = { city: name, pop: 0, zips: 0, payout: 0,
                                                bids: false, lat: 0, lng: 0,
                                                zipSet: {}, ptypes: {} });
    e.pop = Math.max(e.pop, Number(row[5]) || 0);
    if (!e.lat && !e.lng) { e.lat = Number(row[7]) || 0; e.lng = Number(row[8]) || 0; }
    // With no niche asked about, the town is still listed but nothing is
    // attributed to it: summing every niche's payout would show a dentist
    // campaign the pest control rate.
    if (!want || nich[row[2]] !== want) continue;
    e.bids = true;
    // Count ZIPs, not rows: a town sold on both Call and CPL carries two rows
    // per ZIP, and Torrance was reporting 20 ZIPs against its real 10.
    e.zipSet[row[1]] = true;
    e.payout = Math.max(e.payout, Number(row[4]) || 0);
    const pt = ptype[row[3]];
    if (pt) e.ptypes[pt] = true;
  }
  const cities = Object.values(byTown)
    .map((e) => ({ city: e.city, pop: e.pop, zips: Object.keys(e.zipSet).length, bids: e.bids,
                   payout: Math.round(e.payout * 100) / 100,
                   ...nearestMetro(e.lat, e.lng),
                   ptypes: Object.keys(e.ptypes).sort().join("/") }))
    .sort((a, b) => b.pop - a.pop);

  return json({ state, feed_niche: want || null, count: cities.length,
                with_bids: cities.filter((c) => c.bids).length, cities });
}
