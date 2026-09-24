// functions/trigger-emd.js  (Cloudflare Pages Functions)
//
// POST from emd.html. Validates the form and starts emd_finder.yml.
// Same environment variables and the same optional access code as
// trigger-research.js; this function only needs "Actions: write".

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const clean = (s, max) => String(s || "").replace(/[\r\n]+/g, " ").trim().slice(0, max);
const intIn = (v, lo, hi, dflt) => {
  const n = parseInt(v, 10);
  return String(Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : dflt);
};

export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid JSON body" }, 400);
  }

  if (env.FORM_ACCESS_CODE && body.access_code !== env.FORM_ACCESS_CODE) {
    return json({ error: "Invalid access code" }, 401);
  }
  const { GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO } = env;
  const BRANCH = env.GITHUB_DEFAULT_BRANCH || "main";
  if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO) {
    return json({ error: "Server is missing GitHub configuration" }, 500);
  }

  const state = clean(body.state, 2).toUpperCase().replace(/[^A-Z]/g, "");
  const niche = clean(body.niche, 60);
  if (state.length !== 2 || !niche) return json({ error: "Pick a state and a niche" }, 400);

  // Commas separate the list items in the workflow input, so none may survive
  // inside an item.
  const list = (v, maxItems, maxLen) =>
    (Array.isArray(v) ? v : String(v || "").split(","))
      .map((x) => clean(x, 80).replace(/,/g, " "))
      .filter(Boolean)
      .slice(0, maxItems)
      .join(", ")
      .slice(0, maxLen);

  const cities = list(body.cities, 80, 3000);
  const services = list(body.services, 60, 3000);
  if (!services) return json({ error: "Pick at least one service" }, 400);

  const request_id = "emd-" + crypto.randomUUID().slice(0, 8);
  const inputs = {
    state,
    niche,
    cities,
    services,
    min_volume: intIn(body.min_volume, 10, 5000, 100),
    max_serp_checks: intIn(body.max_serp_checks, 0, 100, 0),
    max_cities: intIn(body.max_cities, 1, 80, 60),
    request_id,
  };

  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/emd_finder.yml/dispatches`;
  const gh = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "keyword-research-tool",
    },
    body: JSON.stringify({ ref: BRANCH, inputs }),
  });
  if (gh.status !== 204) {
    return json({ error: "GitHub Actions dispatch failed", detail: await gh.text() }, 502);
  }
  return json({ request_id });
}
