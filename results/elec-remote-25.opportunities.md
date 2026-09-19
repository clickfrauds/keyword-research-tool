# Opportunity scan

- Dataset **2026-09-18** · scanned 2026-09-19
- Filters: `Call` · payout ≥ **$25** · population **8,000–150,000** · niches **Electrical**
- **36** candidate cities · **33** SERP-scored · SerpApi: 25 credit(s) spent · 10 served free from cache
- Verdict by city: **1 GO** · 5 WATCH · 27 STOP

## Verdict by city

Judged on the city's **worst** scored query — one open sub-service under a taken head term is not an open market.

Gates, in order: **Payout · Economics · Demand · SERP · Coverage · EMD** (✅ pass · 🟡 borderline · ❌ fail · ❔ unknown).

| Verdict | Gates | City | Niche | Payout | Searches/mo | Nearest metro | Why |
|---|---|---|---|---|---|---|---|
| **GO** | ✅✅✅🟡✅✅ | Lawton, OK | Electrical | $60.50 | 210 | 78 mi · Oklahoma City, OK | GO with EMD: lawtonelectrical.com is free<br>`electrician Lawton OK`: 1 dedicated page already |
| **WATCH** | ✅✅🟡🟡🟡✅ | Stillwater, OK | Electrical | $60.50 | 90 | 52 mi · Oklahoma City, OK | `electrician Stillwater OK`: 2 small local pages, weak map pack (<100 reviews); SERP 35 < 60; only 90 searches/mo |
| **WATCH** | ✅✅✅🟡🟡✅ | Rome, GA | Electrical | $29.93 | 110 | 55 mi · Chattanooga, TN | only 1 of 5 ZIPs bought |
| **WATCH** | ✅✅🟡🟡✅✅ | Richland, WA | Electrical | $63.00 | 50 | 130 mi · Spokane, WA | `electrician Richland WA`: 3 small local pages, weak map pack (<100 reviews); SERP 35 < 60; only 50 searches/mo |
| **WATCH** | ✅✅🟡🟡✅✅ | Salisbury, MD | Electrical | $40.95 | 70 | 84 mi · Baltimore, MD | `electrician Salisbury MD`: 2 small local pages, weak map pack (<100 reviews); SERP 35 < 60; only 70 searches/mo |
| **WATCH** | ✅✅🟡🟡✅✅ | Atascadero, CA | Electrical | $42.88 | 50 | 94 mi · Bakersfield, CA | `electrician Atascadero CA`: 3 small local pages, weak map pack (<100 reviews); SERP 35 < 60; only 50 searches/mo |

<details><summary>27 STOP cities</summary>

| City | Why |
|---|---|
| Yakima, WA | `electrician Yakima WA`: 2 dedicated electrical pages |
| Jacksonville, NC | `electrician Jacksonville NC`: 5 local electrical firms on page one |
| Longview, TX | `electrician Longview TX`: 1 city EMD on page one |
| Ormond Beach, FL | `electrician Ormond Beach FL`: 5 local electrical firms on page one |
| Corvallis, OR | `electrician Corvallis OR`: 4 dedicated electrical pages |
| Boynton Beach, FL | `electrician Boynton Beach FL`: 4 dedicated electrical pages |
| Santa Maria, CA | `electrician Santa Maria CA`: 4 dedicated electrical pages |
| Owensboro, KY | `electrician Owensboro KY`: 1 city EMD on page one |
| Athens, GA | `electrician Athens GA`: 1 city EMD on page one; 3 dedicated electrical pages |
| Monterey, CA | `electrician Monterey CA`: 5 dedicated electrical pages |
| Santa Fe, NM | `electrician Santa Fe NM`: 1 city EMD on page one; 2 dedicated electrical pages |
| Palm Coast, FL | `electrician Palm Coast FL`: 5 dedicated electrical pages |
| Walla Walla, WA | `electrician Walla Walla WA`: 4 dedicated electrical pages |
| Winchester, VA | `electrician Winchester VA`: 4 dedicated electrical pages |
| Auburn, AL | `electrician Auburn AL`: 5 local electrical firms on page one |
| Nacogdoches, TX | `electrician Nacogdoches TX`: 3 dedicated electrical pages |
| Concord, NH | `electrician Concord NH`: 4 dedicated electrical pages |
| Ocean City, NJ | `electrician Ocean City NJ`: 5 dedicated electrical pages |
| Leland, NC | `electrician Leland NC`: 5 dedicated electrical pages |
| Conway, SC | `electrician Conway SC`: 1 city EMD on page one; 3 dedicated electrical pages |
| Cedar City, UT | `electrician Cedar City UT`: 6 dedicated electrical pages |
| Dover, DE | `electrician Dover DE`: 1 city EMD on page one; 5 dedicated electrical pages |
| Henderson, KY | `electrician Henderson KY`: 1 city EMD on page one; 5 dedicated electrical pages |
| Redmond, OR | `electrician Redmond OR`: 1 city EMD on page one; 7 dedicated electrical pages |
| Lincoln City, OR | `electrician Lincoln City OR`: 2 city EMD on page one; 5 dedicated electrical pages |
| Mansfield, OH | `electrician Mansfield OH`: 1 city EMD on page one; 5 dedicated electrical pages |
| Dover, NH | `electrician Dover NH`: 7 dedicated electrical pages |

</details>

## Launch plan

Every value below is already filled in and is also in `launch_plan.json`. Do the steps in order; each one is a gate.

### Lawton, OK · Electrical

- **GO:** Lawton · WATCH: Stillwater
- 210 searches/mo across these towns · best payout $60.50
- Shape: city site for Lawton (the lawtonelectricians.com pattern); Stillwater can be added later as area pages

1. **Confirm by eye** (free, 2 minutes) — page one should hold directories and out-of-town sites, not local pages built for the town:
   - https://www.google.com/search?q=electrician+Lawton+OK
2. **Confirm with LeadSmart** — the ZIPs are bought for this niche at call (not CPL), the billable duration, and the hours the buyer answers.
3. **Keyword tool → Mode 3 Site Plan** — the services list starts with the head term: the order here is the site's order

   | Field | Value |
   |---|---|
   | business_name | `Lawton Electricians` |
   | niche_description | `electrical referral service connecting homeowners with licensed local pros` |
   | target_location | `Lawton, Oklahoma, United States` |
   | services_mode3 | `Electrician, Outlet Repair, House Rewiring, Light Fixture Installation, Electrical Panel Repair, Ev Charger Installation, Partial Power Outage, Range Wiring` |
   | serp_dedupe | `auto` |

4. **Website builder → Mode 3** — paste the plan's .seo.json link from the step above into extras

   | Field | Value |
   |---|---|
   | mode | `3` |
   | business_name | `Lawton Electricians` |
   | industry | `electrician` |
   | main_service | `Electrician` |
   | sub_services | `Electrician, Outlet Repair, House Rewiring, Light Fixture Installation, Electrical Panel Repair, Ev Charger Installation, Partial Power Outage, Range Wiring` |
   | city | `Lawton` |
   | country | `United States` |
   | phone | `<LeadSmart tracking number>` |
   | domain | `lawtonelectrical.com (free when scanned -- buy it before building)` |
   | extras | `{"seo_inputs_url": "<raw .seo.json link from the step above>", "site_profile": "pay_per_call", "footer_credit": "no", "footer_sitemap_link": "no"}` |

5. **Later** — After 1–2 months in Search Console: Mode 6 local articles on the queries that show impressions.

## Not yet scanned (1 cities)

Next run: raise `max_serp_checks` — every SERP above comes from cache for free, so the credits go only to these.

| City | Niche | Payout | Searches/mo |
|---|---|---|---|
| Rochester, NH | Electrical | $26.25 | 50 |

## All scored queries (top 30)

| # | Opp | SERP | Payout | Searches/mo | Pack | Query | Occupied by |
|---|---|---|---|---|---|---|---|
| 1 | **54** | 90 | $60.50 | 210 | 3× 35 rev | `electrician Lawton OK` | 1 dedicated, 0 EMD, 0 pSEO, 1 local, 7 directory |
| 2 | **19** | 35 | $55.00 | 320 | 3× 135 rev | `electrician Yakima WA` | 2 dedicated, 0 EMD, 0 pSEO, 3 local, 4 directory |
| 3 | **20** | 72 | $28.35 | 260 | 3× 172 rev | `electrician Jacksonville NC` | 1 dedicated, 0 EMD, 0 pSEO, 4 local, 4 directory |
| 4 | **11** | 25 | $45.33 | 260 | 3× 59 rev | `electrician Longview TX` | 3 dedicated, 1 EMD, 0 pSEO, 2 local, 4 directory |
| 5 | **20** | 35 | $56.70 | 140 | 3× 28 rev | `electrician Ormond Beach FL` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 6 | **15** | 35 | $42.52 | 170 | 3× 40 rev | `electrician Corvallis OR` | 4 dedicated, 0 EMD, 0 pSEO, 0 local, 4 directory |
| 7 | **12** | 24 | $50.75 | 170 | 4× 429 rev | `electrician Boynton Beach FL` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 8 | **15** | 34 | $42.88 | 140 | 3× 127 rev | `electrician Santa Maria CA` | 4 dedicated, 0 EMD, 0 pSEO, 0 local, 5 directory |
| 9 | **21** | 35 | $60.50 | 90 | 3× 79 rev | `electrician Stillwater OK` | 2 dedicated, 0 EMD, 0 pSEO, 2 local, 5 directory |
| 10 | **7** | 25 | $28.35 | 260 | 3× 25 rev | `electrician Owensboro KY` | 3 dedicated, 1 EMD, 0 pSEO, 2 local, 4 directory |
| 11 | **7** | 25 | $28.35 | 210 | 3× 260 rev | `electrician Athens GA` | 3 dedicated, 1 EMD, 0 pSEO, 1 local, 3 directory |
| 12 | **9** | 18 | $52.50 | 140 | 3× 16 rev | `electrician Monterey CA` | 5 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 13 | **6** | 25 | $25.20 | 210 | 3× 225 rev | `electrician Santa Fe NM` | 2 dedicated, 1 EMD, 0 pSEO, 1 local, 5 directory |
| 14 | **6** | 16 | $34.58 | 210 | 3× 186 rev | `electrician Palm Coast FL` | 5 dedicated, 0 EMD, 0 pSEO, 0 local, 5 directory |
| 15 | **10** | 35 | $29.93 | 110 | 3× 64 rev | `electrician Rome GA` | 2 dedicated, 0 EMD, 0 pSEO, 2 local, 5 directory |
| 16 | **22** | 35 | $63.00 | 50 | 3× 66 rev | `electrician Richland WA` | 3 dedicated, 0 EMD, 0 pSEO, 1 local, 5 directory |
| 17 | **22** | 35 | $63.00 | 50 | 3× 57 rev | `electrician Walla Walla WA` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 18 | **8** | 26 | $30.24 | 140 | 3× 129 rev | `electrician Winchester VA` | 4 dedicated, 0 EMD, 0 pSEO, 2 local, 3 directory |
| 19 | **14** | 35 | $40.95 | 70 | 3× 46 rev | `electrician Salisbury MD` | 2 dedicated, 0 EMD, 0 pSEO, 2 local, 5 directory |
| 20 | **10** | 35 | $28.30 | 90 | 3× 27 rev | `electrician Auburn AL` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 21 | **12** | 35 | $34.65 | 70 | 3× 287 rev | `electrician Nacogdoches TX` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 22 | **15** | 35 | $42.88 | 50 | 3× 32 rev | `electrician Atascadero CA` | 3 dedicated, 0 EMD, 0 pSEO, 0 local, 6 directory |
| 23 | **9** | 30 | $28.66 | 70 | 3× 101 rev | `electrician Concord NH` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 24 | **9** | 32 | $28.35 | 50 | none | `electrician Ocean City NJ` | 5 dedicated, 0 EMD, 0 pSEO, 0 local, 4 directory |
| 25 | **6** | 18 | $31.50 | 50 | 3× 33 rev | `electrician Leland NC` | 5 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 26 | **4** | 14 | $25.52 | 70 | 3× 261 rev | `electrician Conway SC` | 3 dedicated, 1 EMD, 0 pSEO, 3 local, 3 directory |
| 27 | **1** | 4 | $28.35 | 90 | 3× 28 rev | `electrician Cedar City UT` | 6 dedicated, 0 EMD, 0 pSEO, 0 local, 3 directory |
| 28 | **1** | 2 | $35.52 | 70 | 3× 58 rev | `electrician Dover DE` | 5 dedicated, 1 EMD, 0 pSEO, 0 local, 4 directory |
| 29 | **1** | 2 | $28.35 | 50 | 3× 9 rev | `electrician Henderson KY` | 5 dedicated, 1 EMD, 0 pSEO, 0 local, 4 directory |
| 30 | **0** | 0 | $28.35 | 210 | 3× 37 rev | `electrician Mansfield OH` | 5 dedicated, 1 EMD, 0 pSEO, 1 local, 3 directory |

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
