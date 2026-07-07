// netlify/functions/trigger-research.mjs
//
// Called when the form on the site is submitted. Generates a unique
// request_id, then asks GitHub Actions to run keyword_pipeline.yml with
// that id + the business details the person typed in.
//
// It never touches the Google Ads or Anthropic API keys — those stay
// exactly where they already are, as GitHub Secrets used only inside the
// Actions run. This function only needs permission to start that run.
//
// Required Netlify environment variables (Site configuration -> Environment variables):
//   GITHUB_TOKEN            fine-grained PAT, scoped to this repo only,
//                           with "Actions: write" permission
//   GITHUB_OWNER            e.g. "naseem"
//   GITHUB_REPO             e.g. "keyword-pipeline"
//   GITHUB_DEFAULT_BRANCH   optional, defaults to "main"
//   FORM_ACCESS_CODE        optional — if set, the request body must include
//                           a matching "access_code" field (simple spam guard)

export default async (req) => {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Use POST" }), { status: 405 });
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON body" }), { status: 400 });
  }

  const { business_name, niche_description, target_location, seed_keywords, access_code } = body;

  if (!business_name || !niche_description || !target_location || !seed_keywords) {
    return new Response(
      JSON.stringify({
        error: "business_name, niche_description, target_location and seed_keywords are all required",
      }),
      { status: 400 }
    );
  }

  const requiredCode = Netlify.env.get("FORM_ACCESS_CODE");
  if (requiredCode && access_code !== requiredCode) {
    return new Response(JSON.stringify({ error: "Invalid access code" }), { status: 401 });
  }

  const GITHUB_TOKEN = Netlify.env.get("GITHUB_TOKEN");
  const GITHUB_OWNER = Netlify.env.get("GITHUB_OWNER");
  const GITHUB_REPO = Netlify.env.get("GITHUB_REPO");
  const BRANCH = Netlify.env.get("GITHUB_DEFAULT_BRANCH") || "main";

  if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO) {
    return new Response(JSON.stringify({ error: "Server is missing GitHub configuration" }), { status: 500 });
  }

  const request_id = crypto.randomUUID();
  const dispatchUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/keyword_pipeline.yml/dispatches`;

  const ghResponse = await fetch(dispatchUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      ref: BRANCH,
      inputs: {
        business_name: String(business_name).slice(0, 200),
        niche_description: String(niche_description).slice(0, 500),
        target_location: String(target_location).slice(0, 200),
        seed_keywords: String(seed_keywords).slice(0, 1000),
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
      { status: 502 }
    );
  }

  return new Response(JSON.stringify({ request_id }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
};
