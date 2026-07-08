// functions/trigger-research.js  (Cloudflare Pages Functions)
//
// Called when the form on the site is submitted. Generates a unique
// request_id, then asks GitHub Actions to run keyword_pipeline.yml with
// that id + the business details the person typed in.
//
// It never touches the Google Ads or Anthropic API keys — those stay
// exactly where they already are, as GitHub Secrets used only inside the
// Actions run. This function only needs permission to start that run.
//
// Required Cloudflare Pages environment variables
// (Pages project -> Settings -> Environment variables):
//   GITHUB_TOKEN            fine-grained PAT, scoped to this repo only,
//                           with "Actions: write" permission
//   GITHUB_OWNER            e.g. "naseem"
//   GITHUB_REPO             e.g. "keyword-pipeline"
//   GITHUB_DEFAULT_BRANCH   optional, defaults to "main"
//   FORM_ACCESS_CODE        optional — if set, the request body must include
//                           a matching "access_code" field (simple spam guard)

export async function onRequestPost(context) {
  const { request, env } = context;

  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const { business_name, niche_description, target_location, seed_keywords, access_code } = body;

  if (!business_name || !niche_description || !target_location || !seed_keywords) {
    return new Response(
      JSON.stringify({
        error: "business_name, niche_description, target_location and seed_keywords are all required",
      }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  const requiredCode = env.FORM_ACCESS_CODE;
  if (requiredCode && access_code !== requiredCode) {
    return new Response(JSON.stringify({ error: "Invalid access code" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const GITHUB_TOKEN = env.GITHUB_TOKEN;
  const GITHUB_OWNER = env.GITHUB_OWNER;
  const GITHUB_REPO = env.GITHUB_REPO;
  const BRANCH = env.GITHUB_DEFAULT_BRANCH || "main";

  if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO) {
    return new Response(JSON.stringify({ error: "Server is missing GitHub configuration" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  const request_id = crypto.randomUUID();
  const dispatchUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/keyword_pipeline.yml/dispatches`;

  const ghResponse = await fetch(dispatchUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "keyword-research-tool",
    },
    body: JSON.stringify({
      ref: BRANCH,
      inputs: {
        business_name: String(business_name).slice(0, 200),
        niche_description: String(niche_description).slice(0, 500),
        target_location: String(target_location).slice(0, 200),
        seed_keywords: String(seed_keywords).slice(0, 1000),
        // Existing Account Mode (optional) — incremental ad groups into a live campaign
        existing_campaign: String(body.existing_campaign || "").slice(0, 200),
        existing_ad_groups: String(body.existing_ad_groups || "").slice(0, 1000),
        max_ad_groups: String(body.max_ad_groups || "").slice(0, 3),
        request_id,
      },
    }),
  });

  // GitHub returns 204 No Content on a successful dispatch — no run id comes
  // back synchronously, which is why request_id (not a run id) is what the
  // frontend polls on.
  if (ghResponse.status !== 204) {
    const errText = await ghResponse.text();
    return new Response(
      JSON.stringify({ error: "GitHub Actions dispatch failed", detail: errText }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }

  return new Response(JSON.stringify({ request_id }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

// Cloudflare Pages automatically returns 405 for any method that has no
// matching onRequest* export (e.g. GET here), so no extra code is needed
// to reject non-POST requests — onRequestPost above already covers POST.
