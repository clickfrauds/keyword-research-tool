// functions/emd-status.js  (Cloudflare Pages Functions)
//
// GET /emd-status?request_id=emd-xxxxxxxx
//
// emd.html polls this after starting a run. It reads
// results/{request_id}.emd.json from the results branch; until the run has
// published it, the answer is {status: "pending"}.

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export async function onRequestGet({ request, env }) {
  const rid = new URL(request.url).searchParams.get("request_id") || "";
  if (!/^emd-[a-z0-9-]{4,40}$/i.test(rid)) return json({ error: "bad request_id" }, 400);

  const { GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO } = env;
  const BRANCH = env.GITHUB_RESULTS_BRANCH || "results-data";
  if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO) {
    return json({ error: "Server is missing GitHub configuration" }, 500);
  }

  const path = `results/${rid}.emd.json`;
  const r = await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${path}?ref=${BRANCH}`,
    { headers: { Authorization: `Bearer ${GITHUB_TOKEN}`, Accept: "application/vnd.github.raw",
                 "User-Agent": "keyword-research-tool" } });
  if (r.status === 404) return json({ status: "pending" });
  if (!r.ok) return json({ error: `GitHub answered ${r.status}` }, 502);

  const raw = `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${BRANCH}/results/${rid}`;
  return json({ status: "ready", result: await r.json(),
                links: { csv: raw + ".emd.csv", grid: raw + ".emd.grid.csv",
                         md: raw + ".emd.md", json: raw + ".emd.json" } });
}
