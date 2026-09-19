# Opportunity scan

- Dataset **2026-09-18** · scanned 2026-09-19
- Filters: `Call` · payout ≥ **$50** · population **8,000–150,000** · niches **Electrical**
- **11** candidate cities · **10** SERP-scored · SerpApi: 7 credit(s) spent · 4 served free from cache
- Verdict by city: **0 GO** · 3 WATCH · 7 STOP

## Verdict by city

Judged on the city's **worst** scored query — one open sub-service under a taken head term is not an open market.

| Verdict | City | Niche | Payout | Searches/mo | Why |
|---|---|---|---|---|---|
| **WATCH** | Lawton, OK | Electrical | $60.50 | 210 | `electrician Lawton OK`: 1 dedicated page already |
| **WATCH** | Stillwater, OK | Electrical | $60.50 | 90 | `electrician Stillwater OK`: 2 small local pages, weak map pack (<100 reviews); SERP 35 < 60; only 90 searches/mo |
| **WATCH** | Duncan, OK | Electrical | $60.50 | 30 | `electrician Duncan OK`: only 30 searches/mo |

<details><summary>7 STOP cities</summary>

| City | Why |
|---|---|
| Norman, OK | `electrician Norman OK`: 4 dedicated electrical pages |
| Broken Arrow, OK | `electrician Broken Arrow OK`: 3 dedicated electrical pages |
| Edmond, OK | `electrician Edmond OK`: 4 dedicated electrical pages; map pack at 816 reviews |
| Muskogee, OK | `electrician Muskogee OK`: 3 dedicated electrical pages |
| Ada, OK | `electrician Ada OK`: 1 city EMD on page one; 1 programmatic subdomain(s) |
| Mustang, OK | `electrician Mustang OK`: 5 dedicated electrical pages |
| Yukon, OK | `electrician Yukon OK`: 1 city EMD on page one; 5 dedicated electrical pages |

</details>

## Launch plan

No city passed as GO. Nothing here is worth a domain yet — widen `states`, lower `min_payout`, or try another niche. WATCH rows are for a site that already exists in that state, not a new one.

## All scored queries (top 30)

| # | Opp | SERP | Payout | Searches/mo | Pack | Query | Occupied by |
|---|---|---|---|---|---|---|---|
| 1 | **54** | 90 | $60.50 | 210 | 3× 35 rev | `electrician Lawton OK` | 1 dedicated, 0 EMD, 0 pSEO, 1 local, 7 directory |
| 2 | **21** | 35 | $60.50 | 260 | 3× 187 rev | `electrician Norman OK` | 4 dedicated, 0 EMD, 0 pSEO, 0 local, 4 directory |
| 3 | **18** | 35 | $52.45 | 170 | 3× 230 rev | `electrician Broken Arrow OK` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 4 | **8** | 14 | $60.50 | 320 | 4× 816 rev | `electrician Edmond OK` | 4 dedicated, 0 EMD, 0 pSEO, 2 local, 3 directory |
| 5 | **21** | 35 | $60.50 | 90 | 3× 79 rev | `electrician Stillwater OK` | 2 dedicated, 0 EMD, 0 pSEO, 3 local, 4 directory |
| 6 | **60** | 100 | $60.50 | 30 | 3× 25 rev | `electrician Duncan OK` | 0 dedicated, 0 EMD, 0 pSEO, 3 local, 6 directory |
| 7 | **18** | 35 | $52.45 | 90 | 3× 15 rev | `electrician Muskogee OK` | 3 dedicated, 0 EMD, 0 pSEO, 1 local, 5 directory |
| 8 | **15** | 25 | $60.50 | 40 | 3× 40 rev | `electrician Ada OK` | 2 dedicated, 1 EMD, 1 pSEO, 2 local, 6 directory |
| 9 | **13** | 22 | $60.50 | 40 | 3× 9 rev | `electrician Mustang OK` | 5 dedicated, 0 EMD, 0 pSEO, 0 local, 4 directory |
| 10 | **1** | 2 | $60.50 | 50 | 3× 12 rev | `electrician Yukon OK` | 5 dedicated, 1 EMD, 0 pSEO, 0 local, 4 directory |

### Reading a row

- **STOP** on any `EMD > 0` or `pSEO > 0` — a city exact-match domain or a programmatic network already holds that slot with authority a new domain does not have.
- **STOP** on `dedicated >= 2` — the local trades already built that page.
- `pricing: flat` means the payout is identical nationwide, so choosing this market over another buys nothing on the revenue side; judge it on volume and competition alone.
- A pack of three businesses at 500+ reviews takes most of the clicks even when the organic SERP is open.

### Gates this scan cannot answer

Two decisions are not in any feed and must be confirmed with the network before a domain is bought:

1. **Is the offer duration-based or buyer-qualified?** Only a stated billable duration is verifiable from your own call log. "Booked appointment" is the buyer's judgement, not a number.
2. **What hours does the buyer answer?** Emergency niches earn at 2am. A 9-to-5 buyer drops exactly the traffic that converts best.

Search volume is measured here only for the broad trade term. The Mode 5 Area Plan in the launch plan measures every town and keyword before a page is written.

---
`opportunity = serp_score / 100 × bundle_value`. An open SERP on a cheap payout and a rich payout behind six dedicated pages both score low, which is the point.
