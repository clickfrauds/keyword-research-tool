# Call Intelligence + LeadSmart coverage — captured 2026-09-09

Two feeds that between them answer "which niche, and where", captured so
`find_opportunities.py` and any future niche hunt read measured numbers instead
of plausible-sounding ones.

Neither is in the repo's normal pipeline — both live behind a login or a
targeting app, so they are snapshotted here rather than fetched at runtime.

## Where each came from

| File | Source |
|---|---|
| `niches.csv`, `subs.csv` | `ranklocal.cc/api/call-intel` — the mentor's Call Intelligence dashboard. 20 niches, 91 sub-services, 574 specific services, ~5,000 recorded calls |
| `coverage_*.json` | `leadsmart-coverage.netlify.app/api/*` — which is the **Ringba bid feed**: LeadSmart's welcome email points at `affiliate-bid-coverage.leadsmartinc.com` for "Ringba probable bid range", and the app's own meta names that as its source |
| `plumbing_shortlist.csv` | derived — top 120 non-California plumbing Call cities in the 8k–120k band |
| `az_plumbing_zips.csv` | derived — all 437 Arizona plumbing Call ZIPs with payout |

LeadSmart's email calls the coverage app *"just a targeting tool and is not
100% accurate; bids can change within the day"*. Treat these as a dated
snapshot, not live truth.

## The two findings that changed decisions

**1. `top_payout` is not the payout.** It is the single best ZIP in the
country. Plumbing's is $221.95; its median is $34.38 — a 6x gap that pointed
at the wrong niche. `coverage_niche_summary.json` carries min/avg/median/max;
use the median.

**2. Call volume and revenue run opposite.** The three highest-volume niches
in the whole feed are the three worst payers:

| niche | calls | median payout | paid% | revenue/call |
|---|---|---|---|---|
| Appliance | 1,148 | $6.88 | 71 | **$4.88** |
| Pest Control | 1,115 | $42.50 | 51 | $21.68 |
| Tree Services | 1,056 | $9.63 | 69 | **$6.64** |
| **Plumbing** | 1,064 | $34.38 | 79 | **$27.16** |
| **HVAC** | 274 | $38.06 | 72 | **$27.40** |
| **Roofing** | 159 | $41.25 | 61 | **$25.16** |

Both are encoded in `scripts/find_opportunities.py` as `NICHE_ECONOMICS` and
the `MIN_REV_PER_CALL` gate.

## Column notes

`niches.csv` — `paid_pct` is the share of that niche's calls that actually
paid; `booked_pct` the share marked booked; `urgent_pct` the share whose
urgency was not "routine". Plumbing's 45% urgent is the highest in the feed,
which matters on a duration-billed offer.

`subs.csv` — same three, per sub-service. This is the layer that shows which
services inside a niche earn: plumbing's `sewer & septic` pays on 95% of calls
while `sump & ejector pumps` pays on 18% of 11.

## The phrase layer

`phrases.csv` is all 5,831 recorded calls — the exact wording, with `urgency`,
`outcome` and `paid` on each one. 67% of them paid; 30% were not routine.

This is the layer article topics should be written from. Batch 1 on
arizonahomeservicepros.com was written from my paraphrase of these instead,
and 10 of its 13 titles turned out to target SERPs that are walls of YouTube
and Reddit — the topics were plausible, but nobody had checked what the
callers actually say or what already ranks for it.

`specifics.csv` sits between subs and phrases: 587 specific services with the
same three percentages, which is where "sewer backup pays on 100% of 19 calls"
and "sump pumps pay on 18% of 11" become visible.

Recapture with `extract_call_intel.js` when the numbers age — the dashboard is
the only source and it is behind a login.
