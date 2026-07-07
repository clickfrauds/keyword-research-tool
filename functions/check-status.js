// functions/check-status.js  (Cloudflare Pages Functions)
//
// The frontend polls this every few seconds after submitting the form.
// It reads results/{request_id}.html straight from the "results-data"
// branch via the GitHub Contents API — works whether the repo is public
// or private, since it always sends the token.
//
// Required Cloudflare Pages environment variables (same GITHUB_* values as
// trigger-research.js — this one only needs "Contents: read"):
//   GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO
//   GITHUB_RESULTS_BRANCH   optional, defaults to "results-data"

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const request_id = url.searchParams.get("request_id");

  if (!request_id) {
    return new Response(JSON.stringify({ error: "request_id query param is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const GITHUB_TOKEN = env.GITHUB_TOKEN;
  const GITHUB_OWNER = env.GITHUB_OWNER;
  const GITHUB_REPO = env.GITHUB_REPO;
  const BRANCH = env.GITHUB_RESULTS_BRANCH || "results-data";

  if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO) {
    return new Response(JSON.stringify({ error: "Server is missing GitHub configuration" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  const contentsUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/results/${request_id}.html?ref=${BRANCH}`;

  const ghResponse = await fetch(contentsUrl, {
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      // application/vnd.github.raw makes GitHub return the plain file
      // content directly, instead of a JSON envelope with base64 inside it.
      Accept: "application/vnd.github.raw",
    },
  });

  if (ghResponse.status === 404) {
    return new Response(JSON.stringify({ status: "pending" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (ghResponse.status !== 200) {
    const errText = await ghResponse.text();
    return new Response(JSON.stringify({ status: "error", detail: errText }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  const htmlContent = await ghResponse.text();

  return new Response(JSON.stringify({ status: "ready", html: htmlContent }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
