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

  // Existing-pages runs supply URLs instead of seeds: the seeds are read off
  // the pages themselves in Stage 0-CRAWL, so requiring them here would force
  // the operator to invent the very thing the crawl exists to work out.
  const landing_urls = String(body.landing_urls || "").trim();

  if (!business_name || !niche_description || !target_location ||
      (!seed_keywords && !landing_urls)) {
    return new Response(
      JSON.stringify({
        error: "business_name, niche_description and target_location are required, "
             + "plus either seed_keywords or landing_urls",
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

  // mode3 = the dedicated "Mode 3 Site Plan" workflow: the keywords box
  // carries the comma-separated SERVICES list (same list the builder gets),
  // and the run publishes {id}.seo.json with the mode3_site_plan block plus
  // a stub html so the same polling flow works. Everything else goes to the
  // normal keyword pipeline.
  const isMode3 = body.research_type === "mode3";
  // mode5 = the dedicated pSEO area-research workflow: one Planner request per real
  // geo area of the city, so each area page is built on its own measured
  // demand instead of whatever the seed run happened to return.
  const isMode5 = body.research_type === "mode5";
  const workflowFile = isMode3 ? "mode3_plan.yml"
                     : isMode5 ? "mode5_areas.yml"
                     : "keyword_pipeline.yml";
  const dispatchUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${workflowFile}/dispatches`;

  // Content language CODE (es/fr/de/ar/...). "no"/blank = English (unchanged).
  // Whitelisted so a junk value can't reach the workflow.
  const LANG_CODES = ["no", "en", "ar", "es", "fr", "de", "it", "pt", "nl",
                      "tr", "ru", "ur", "hi", "zh", "ja", "ko", "pl", "sv",
                      "id", "th", "vi", "el", "ro", "cs", "hu"];
  const language = LANG_CODES.includes(String(body.language || "").toLowerCase())
    ? String(body.language).toLowerCase() : "no";

  const inputs = isMode5
    ? {
        business_name: String(business_name).slice(0, 200),
        niche_description: String(niche_description).slice(0, 500),
        target_location: String(target_location).slice(0, 200),
        // the ONE service these area pages sell; falls back to the first seed
        primary_service: String(body.primary_service || seed_keywords)
                           .split(",")[0].trim().slice(0, 120),
        min_area_volume: String(body.min_area_volume || "20").slice(0, 5),
        // blank = the whole city. Defaulting to 60 here silently left 43 of
        // Dubai's 103 areas unmeasured, and the plan gave no sign of it.
        max_areas: String(body.max_areas || "").slice(0, 4),
        // districts that are not Google geo targets but are searched by name
        extra_areas: String(body.extra_areas || "").slice(0, 900),
        language,
        request_id,
      }
    : isMode3
    ? {
        business_name: String(business_name).slice(0, 200),
        niche_description: String(niche_description).slice(0, 500),
        target_location: String(target_location).slice(0, 200),
        services_mode3: String(seed_keywords).slice(0, 4000),
        language,
        request_id,
      }
    : {
        business_name: String(business_name).slice(0, 200),
        niche_description: String(niche_description).slice(0, 500),
        target_location: String(target_location).slice(0, 200),
        seed_keywords: String(seed_keywords || "").slice(0, 1000),
        // Live pages the campaign must be built around. Present = Stage
        // 0-CRAWL runs and its seeds replace seed_keywords downstream.
        landing_urls: landing_urls.slice(0, 4000),
        language,
        // Deliverable selector: google_ads | seo | both
        research_type: ["google_ads", "seo", "both"].includes(body.research_type)
          ? body.research_type : "google_ads",
        // Existing Account Mode (optional) — incremental ad groups into a live campaign
        existing_campaign: String(body.existing_campaign || "").slice(0, 200),
        existing_ad_groups: String(body.existing_ad_groups || "").slice(0, 1000),
        max_ad_groups: String(body.max_ad_groups || "").slice(0, 3),
        // Stage 3.8 RSA ads: Final URLs = website_url + landing-page slug
        website_url: String(body.website_url || "").slice(0, 300),
        // Does the site publish this language under /{lang}/ ? The website
        // builder's default is yes (/ar/slug/), so anything but an explicit
        // "no" keeps the folder — a wrong guess here 404s every ad.
        lang_url_prefix: body.lang_url_prefix === "no" ? "no" : "yes",
        // Manual bid-tier overrides for the Locations stage. These beat the
        // model's own call, so a good area can be protected from a wrong -90%.
        premium_areas: String(body.premium_areas || "").slice(0, 600),
        low_areas: String(body.low_areas || "").slice(0, 600),
        // Stage 4-PUSH: direct API push (digits-only id; blank = CSV-only)
        push_customer_id: String(body.push_customer_id || "").replace(/\D/g, "").slice(0, 12),
        push_mode: body.push_mode === "live" ? "live" : "validate",
        // Two-phase push. auto holds the ads back whenever a landing page is
        // not serving yet, which is what stops Google disapproving them as
        // "Destination not working"; creative attaches them on a later run.
        push_phase: ["auto", "structure", "creative"].includes(body.push_phase)
          ? body.push_phase : "auto",
        // Enabling starts spend, so it is never inferred — only an explicit
        // yes turns the campaign on.
        enable_campaign: body.enable_campaign === "yes" ? "yes" : "no",
        request_id,
      };

  const ghResponse = await fetch(dispatchUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "keyword-research-tool",
    },
    body: JSON.stringify({ ref: BRANCH, inputs }),
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
