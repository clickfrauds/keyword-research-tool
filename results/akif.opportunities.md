# Opportunity scan

- Dataset **2026-09-18** · scanned 2026-09-19
- Filters: `Call` · payout ≥ **$45** · population **8,000–150,000** · niches **Electrical**
- **11** candidate cities · **10** SERP-scored · SerpApi: 5 credit(s) spent · 6 served free from cache
- Verdict by city: **0 GO** · 2 WATCH · 8 STOP

## Verdict by city

Judged on the city's **worst** scored query — one open sub-service under a taken head term is not an open market.

Gates, in order: **Payout · Economics · Demand · SERP · Coverage** (✅ pass · 🟡 borderline · ❌ fail · ❔ unknown).

| Verdict | Gates | City | Niche | Payout | Searches/mo | Nearest metro | Why |
|---|---|---|---|---|---|---|---|
| **WATCH** | ✅✅✅🟡✅ | Lawton, OK | Electrical | $60.50 | 210 | 78 mi · Oklahoma City, OK | `electrician Lawton OK`: 1 dedicated page already |
| **WATCH** | ✅✅🟡🟡🟡 | Stillwater, OK | Electrical | $60.50 | 90 | 52 mi · Oklahoma City, OK | `electrician Stillwater OK`: 2 small local pages, weak map pack (<100 reviews); SERP 35 < 60; only 90 searches/mo |

<details><summary>8 STOP cities</summary>

| City | Why |
|---|---|
| Yakima, WA | `electrician Yakima WA`: 2 dedicated electrical pages |
| Longview, TX | `electrician Longview TX`: 1 city EMD on page one; 3 dedicated electrical pages |
| Ormond Beach, FL | `electrician Ormond Beach FL`: 3 dedicated electrical pages |
| Boynton Beach, FL | `electrician Boynton Beach FL`: 4 dedicated electrical pages |
| Sebring, FL | `electrician Sebring FL`: 3 dedicated electrical pages |
| Monterey, CA | `electrician Monterey CA`: 5 dedicated electrical pages |
| Richland, WA | `electrician Richland WA`: 3 dedicated electrical pages |
| Walla Walla, WA | `electrician Walla Walla WA`: 4 dedicated electrical pages |

</details>

## Launch plan

No city passed as GO. Nothing here is worth a domain yet — widen `states`, lower `min_payout`, or try another niche. WATCH rows are for a site that already exists in that state, not a new one.

## All scored queries (top 30)

| # | Opp | SERP | Payout | Searches/mo | Pack | Query | Occupied by |
|---|---|---|---|---|---|---|---|
| 1 | **54** | 90 | $60.50 | 210 | 3× 35 rev | `electrician Lawton OK` | 1 dedicated, 0 EMD, 0 pSEO, 1 local, 7 directory |
| 2 | **19** | 35 | $55.00 | 320 | 3× 135 rev | `electrician Yakima WA` | 2 dedicated, 0 EMD, 0 pSEO, 3 local, 4 directory |
| 3 | **11** | 25 | $45.33 | 260 | 3× 59 rev | `electrician Longview TX` | 3 dedicated, 1 EMD, 0 pSEO, 2 local, 4 directory |
| 4 | **20** | 35 | $56.70 | 140 | 3× 28 rev | `electrician Ormond Beach FL` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 5 | **12** | 24 | $50.75 | 170 | 4× 429 rev | `electrician Boynton Beach FL` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 6 | **21** | 35 | $60.50 | 90 | 3× 79 rev | `electrician Stillwater OK` | 2 dedicated, 0 EMD, 0 pSEO, 2 local, 5 directory |
| 7 | **16** | 35 | $46.20 | 90 | 3× 77 rev | `electrician Sebring FL` | 3 dedicated, 0 EMD, 0 pSEO, 0 local, 6 directory |
| 8 | **9** | 18 | $52.50 | 140 | 3× 16 rev | `electrician Monterey CA` | 5 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 9 | **22** | 35 | $63.00 | 50 | 3× 66 rev | `electrician Richland WA` | 3 dedicated, 0 EMD, 0 pSEO, 1 local, 5 directory |
| 10 | **22** | 35 | $63.00 | 50 | 3× 57 rev | `electrician Walla Walla WA` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |

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
