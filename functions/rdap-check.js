// functions/rdap-check.js  (Cloudflare Pages Functions)
//
// POST { domains: ["duncanelectricians.com", ...] }
//   -> { results: { "duncanelectricians.com": "free" | "taken" | "unknown" } }
//
// Verisign runs .com and answers 404 for a name nobody has registered, 200
// for one somebody has. That is the registry's own answer, free, and it needs
// no key and no account — which is why this exists instead of scraping a
// registrar. A .com has no premium tier, so "free" means registrable at the
// standard price (Namecheap: $11.28 at the time of writing), and a name a
// registrar shows at a "premium" price is an aftermarket name someone already
// owns, which reads as taken here.
//
// Answers are cached at the edge for a day: a domain's registration status
// does not move hour to hour, and the cache keeps the request count off
// Verisign when the same shortlist is checked twice.

const RDAP = "https://rdap.verisign.com/com/v1/domain/";
const MAX_DOMAINS = 120;      // one screen of candidates
const CONCURRENCY = 6;        // polite: Verisign is a free public service

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

function clean(name) {
  const d = String(name || "").trim().toLowerCase();
  // Only .com, only the characters a hostname may carry. Anything else is a
  // typo, and asking Verisign about it just spends a request.
  return /^[a-z0-9][a-z0-9-]{0,62}\.com$/.test(d) ? d : null;
}

async function lookup(domain, cache, ctx) {
  const key = new Request("https://rdap-cache.local/" + domain);
  const hit = await cache.match(key);
  if (hit) return (await hit.json()).status;

  let status = "unknown";
  try {
    const r = await fetch(RDAP + domain, {
      headers: { "Accept": "application/rdap+json", "User-Agent": "keyword-research-tool" },
      cf: { cacheTtl: 86400, cacheEverything: true },
    });
    if (r.status === 404) status = "free";
    else if (r.ok) status = "taken";
    // Anything else (429, 5xx) stays "unknown" and is never cached, so a
    // throttled answer is not mistaken for a verdict.
  } catch (e) {
    status = "unknown";
  }

  if (status !== "unknown") {
    const body = JSON.stringify({ status });
    ctx.waitUntil(cache.put(key, new Response(body, {
      headers: { "Content-Type": "application/json", "Cache-Control": "max-age=86400" },
    })));
  }
  return status;
}

export async function onRequestPost({ request, waitUntil }) {
  let body;
  try {
    body = await request.json();
  } catch (e) {
    return json({ error: "send JSON: { domains: [...] }" }, 400);
  }

  const seen = {};
  const domains = [];
  for (const raw of (body.domains || [])) {
    const d = clean(raw);
    if (d && !seen[d]) { seen[d] = 1; domains.push(d); }
    if (domains.length >= MAX_DOMAINS) break;
  }
  if (!domains.length) return json({ error: "no valid .com domains in the request" }, 400);

  const cache = caches.default;
  const results = {};
  const ctx = { waitUntil };
  let next = 0;
  async function worker() {
    while (next < domains.length) {
      const d = domains[next++];
      results[d] = await lookup(d, cache, ctx);
    }
  }
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, domains.length) }, worker));

  const free = Object.values(results).filter((v) => v === "free").length;
  return json({ checked: domains.length, free, results });
}
