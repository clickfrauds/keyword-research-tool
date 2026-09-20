# Opportunity scan

- Dataset **2026-09-19** · scanned 2026-09-20
- Filters: `Call` · payout ≥ **$30** · population **8,000–150,000** · niches **Plumbing**
- **59** candidate cities · **28** SERP-scored · SerpApi: 9 credit(s) spent · 22 served free from cache
- Verdict by city: **1 GO** · 0 WATCH · 27 STOP

## Verdict by city

Judged on the city's **worst** scored query — one open sub-service under a taken head term is not an open market.

Gates, in order: **Payout · Economics · Demand · SERP · Coverage · EMD** (✅ pass · 🟡 borderline · ❌ fail · ❔ unknown).

| Verdict | Gates | City | Niche | Payout | Searches/mo | Nearest metro | Why |
|---|---|---|---|---|---|---|---|
| **GO** | ✅✅✅🟡✅✅ | Bullhead City, AZ | Plumbing | $56.98 | 880 | 80 mi · Las Vegas, NV | GO with EMD: plumbersbullheadcity.com is free<br>`plumber Bullhead City AZ`: 3 small local pages, weak map pack (<100 reviews); SERP 35 < 60 |

<details><summary>27 STOP cities</summary>

| City | Why |
|---|---|
| Pocatello, ID | `plumber Pocatello ID`: 3 dedicated plumbing pages |
| Lake Havasu City, AZ | `plumber Lake Havasu City AZ`: 3 dedicated plumbing pages |
| Palm Coast, FL | `plumber Palm Coast FL`: 4 dedicated plumbing pages |
| Tyler, TX | `plumber Tyler TX`: 2 city EMD on page one; map pack at 936 reviews |
| Florence, SC | `plumber Florence SC`: 5 local plumbing firms on page one |
| Longview, TX | `plumber Longview TX`: 1 city EMD on page one; 3 dedicated plumbing pages |
| Bend, OR | `plumber Bend OR`: 1 city EMD on page one; 2 dedicated plumbing pages |
| Lompoc, CA | `plumber Lompoc CA`: 5 local plumbing firms on page one |
| Lawton, OK | `plumber Lawton OK`: 4 dedicated plumbing pages; map pack at 2200 reviews |
| Yakima, WA | `plumber Yakima WA`: 4 dedicated plumbing pages; map pack at 636 reviews |
| Greenville, NC | `plumber Greenville NC`: 4 dedicated plumbing pages |
| Lynchburg, VA | `plumber Lynchburg VA`: 4 dedicated plumbing pages |
| Ormond Beach, FL | `plumber Ormond Beach FL`: 4 dedicated plumbing pages; map pack at 647 reviews |
| Monterey, CA | `plumber Monterey CA`: 6 dedicated plumbing pages |
| Flagstaff, AZ | `plumber Flagstaff AZ`: 5 dedicated plumbing pages |
| Rochester, MN | `plumber Rochester MN`: 5 dedicated plumbing pages |
| Sierra Vista, AZ | `plumber Sierra Vista AZ`: 1 city EMD on page one; 4 dedicated plumbing pages |
| Muncie, IN | `plumber Muncie IN`: 5 dedicated plumbing pages |
| Rome, GA | `plumber Rome GA`: 1 city EMD on page one; 5 dedicated plumbing pages |
| Boynton Beach, FL | `plumber Boynton Beach FL`: 6 dedicated plumbing pages |
| Santa Maria, CA | `plumber Santa Maria CA`: 7 dedicated plumbing pages |
| Kingman, AZ | `plumber Kingman AZ`: 6 dedicated plumbing pages; map pack at 950 reviews |
| Corvallis, OR | `plumber Corvallis OR`: 1 city EMD on page one; 6 dedicated plumbing pages |
| Prescott, AZ | `plumber Prescott AZ`: 1 city EMD on page one; 6 dedicated plumbing pages |
| Wenatchee, WA | `plumber Wenatchee WA`: 3 city EMD on page one; 6 dedicated plumbing pages |
| Idaho Falls, ID | `plumber Idaho Falls ID`: 1 city EMD on page one; 5 dedicated plumbing pages |
| Grants Pass, OR | `plumber Grants Pass OR`: 1 city EMD on page one; 6 dedicated plumbing pages |

</details>

## Launch plan

Every value below is already filled in and is also in `launch_plan.json`. Do the steps in order; each one is a gate.

### Bullhead City, AZ · Plumbing

- **GO:** Bullhead City
- 880 searches/mo across these towns · best payout $56.98
- Shape: city site for Bullhead City (the lawtonelectricians.com pattern)

1. **Confirm by eye** (free, 2 minutes) — page one should hold directories and out-of-town sites, not local pages built for the town:
   - https://www.google.com/search?q=plumber+Bullhead+City+AZ
2. **Confirm with LeadSmart** — the ZIPs are bought for this niche at call (not CPL), the billable duration, and the hours the buyer answers.
3. **Keyword tool → Mode 3 Site Plan** — the services list starts with the head term: the order here is the site's order

   | Field | Value |
   |---|---|
   | business_name | `Bullhead City Plumbers` |
   | niche_description | `plumbing referral service connecting homeowners with licensed local pros` |
   | target_location | `Bullhead City, Arizona, United States` |
   | services_mode3 | `Plumber, Leak Detection, Drain Cleaning, Sewer Line Repair, Clogged Drain Repair, Water Heater Leak Repair, Faucet Repair, Slab Leak Repair, Water Line Repair, Toilet Repair, Sewer Backup Cleanup, Drain Snaking, Ceiling Leak Repair, Tankless Water Heater Repair, Water Softener Installation` |
   | serp_dedupe | `auto` |

4. **Website builder → Mode 3** — paste the plan's .seo.json link from the step above into extras

   | Field | Value |
   |---|---|
   | mode | `3` |
   | business_name | `Bullhead City Plumbers` |
   | industry | `plumber` |
   | main_service | `Plumber` |
   | sub_services | `Plumber, Leak Detection, Drain Cleaning, Sewer Line Repair, Clogged Drain Repair, Water Heater Leak Repair, Faucet Repair, Slab Leak Repair, Water Line Repair, Toilet Repair, Sewer Backup Cleanup, Drain Snaking, Ceiling Leak Repair, Tankless Water Heater Repair, Water Softener Installation` |
   | city | `Bullhead City` |
   | country | `United States` |
   | phone | `<LeadSmart tracking number>` |
   | domain | `plumbersbullheadcity.com (free when scanned -- buy it before building)` |
   | extras | `{"seo_inputs_url": "<raw .seo.json link from the step above>", "site_profile": "pay_per_call", "footer_credit": "no", "footer_sitemap_link": "no"}` |

5. **Later** — After 1–2 months in Search Console: Mode 6 local articles on the queries that show impressions.

## Not yet scanned (28 cities)

Next run: raise `max_serp_checks` — every SERP above comes from cache for free, so the credits go only to these.

| City | Niche | Payout | Searches/mo |
|---|---|---|---|
| Clovis, NM | Plumbing | $31.50 | 590 |
| Kingsport, TN | Plumbing | $31.50 | 590 |
| Bloomington, IL | Plumbing | $30.80 | 590 |
| Bowling Green, KY | Plumbing | $30.80 | 590 |
| Salisbury, MD | Plumbing | $54.25 | 320 |
| Winchester, VA | Plumbing | $44.10 | 390 |
| Kerrville, TX | Plumbing | $43.65 | 390 |
| Martinsburg, WV | Plumbing | $42.52 | 390 |
| Prescott Valley, AZ | Plumbing | $50.40 | 320 |
| Johnson City, TN | Plumbing | $31.50 | 480 |
| Farmington, NM | Plumbing | $30.80 | 480 |
| Morgantown, WV | Plumbing | $30.80 | 480 |
| Mishawaka, IN | Plumbing | $44.10 | 320 |
| Lake City, FL | Plumbing | $41.58 | 320 |
| Somerset, KY | Plumbing | $39.43 | 320 |

## All scored queries (top 30)

| # | Opp | SERP | Payout | Searches/mo | Pack | Query | Occupied by |
|---|---|---|---|---|---|---|---|
| 1 | **12** | 35 | $34.65 | 1900 | 3× 161 rev | `plumber Pocatello ID` | 3 dedicated, 0 EMD, 0 pSEO, 1 local, 5 directory |
| 2 | **20** | 35 | $56.98 | 880 | 3× 30 rev | `plumber Bullhead City AZ` | 3 dedicated, 0 EMD, 0 pSEO, 0 local, 6 directory |
| 3 | **19** | 35 | $54.39 | 880 | 3× 297 rev | `plumber Lake Havasu City AZ` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 4 | **17** | 35 | $47.25 | 590 | 3× 29 rev | `plumber Palm Coast FL` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 5 | **10** | 25 | $38.50 | 1000 | 3× 936 rev | `plumber Tyler TX` | 1 dedicated, 2 EMD, 0 pSEO, 1 local, 5 directory |
| 6 | **12** | 35 | $35.00 | 720 | 3× 49 rev | `plumber Florence SC` | 2 dedicated, 0 EMD, 0 pSEO, 3 local, 4 directory |
| 7 | **10** | 18 | $55.13 | 880 | 3× 234 rev | `plumber Longview TX` | 3 dedicated, 1 EMD, 0 pSEO, 2 local, 3 directory |
| 8 | **10** | 25 | $39.38 | 880 | 3× 284 rev | `plumber Bend OR` | 2 dedicated, 1 EMD, 0 pSEO, 2 local, 2 directory |
| 9 | **21** | 35 | $61.25 | 390 | 3× 41 rev | `plumber Lompoc CA` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 10 | **9** | 22 | $43.12 | 590 | 4× 2200 rev | `plumber Lawton OK` | 4 dedicated, 0 EMD, 0 pSEO, 0 local, 5 directory |
| 11 | **6** | 18 | $34.65 | 880 | 3× 636 rev | `plumber Yakima WA` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 12 | **9** | 20 | $44.66 | 590 | 3× 303 rev | `plumber Greenville NC` | 4 dedicated, 0 EMD, 0 pSEO, 2 local, 3 directory |
| 13 | **7** | 24 | $30.10 | 720 | 3× 283 rev | `plumber Lynchburg VA` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 14 | **8** | 18 | $44.66 | 480 | 4× 647 rev | `plumber Ormond Beach FL` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 15 | **2** | 4 | $58.27 | 1300 | 3× 90 rev | `plumber Monterey CA` | 6 dedicated, 0 EMD, 0 pSEO, 0 local, 3 directory |
| 16 | **4** | 12 | $31.50 | 720 | 3× 196 rev | `plumber Flagstaff AZ` | 5 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 17 | **3** | 10 | $30.80 | 720 | 3× 475 rev | `plumber Rochester MN` | 5 dedicated, 0 EMD, 0 pSEO, 0 local, 3 directory |
| 18 | **4** | 6 | $60.20 | 590 | 3× 122 rev | `plumber Sierra Vista AZ` | 4 dedicated, 1 EMD, 0 pSEO, 2 local, 3 directory |
| 19 | **3** | 6 | $47.25 | 480 | 3× 241 rev | `plumber Muncie IN` | 5 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 20 | **0** | 0 | $56.98 | 880 | 3× 950 rev | `plumber Kingman AZ` | 6 dedicated, 0 EMD, 0 pSEO, 0 local, 3 directory |
| 21 | **0** | 0 | $61.25 | 720 | 3× 297 rev | `plumber Santa Maria CA` | 7 dedicated, 0 EMD, 0 pSEO, 0 local, 2 directory |
| 22 | **0** | 0 | $48.16 | 720 | 3× 342 rev | `plumber Prescott AZ` | 6 dedicated, 1 EMD, 0 pSEO, 0 local, 3 directory |
| 23 | **0** | 0 | $69.30 | 480 | 3× 24 rev | `plumber Rome GA` | 5 dedicated, 1 EMD, 0 pSEO, 1 local, 2 directory |
| 24 | **0** | 0 | $64.75 | 480 | 3× 363 rev | `plumber Boynton Beach FL` | 6 dedicated, 0 EMD, 0 pSEO, 0 local, 2 directory |
| 25 | **0** | 0 | $53.55 | 480 | 3× 25 rev | `plumber Corvallis OR` | 6 dedicated, 1 EMD, 0 pSEO, 0 local, 2 directory |
| 26 | **0** | 0 | $30.80 | 720 | 3× 398 rev | `plumber Grants Pass OR` | 6 dedicated, 1 EMD, 0 pSEO, 0 local, 3 directory |
| 27 | **0** | 0 | $36.42 | 590 | 3× 233 rev | `plumber Wenatchee WA` | 6 dedicated, 3 EMD, 0 pSEO, 0 local, 3 directory |
| 28 | **0** | 0 | $34.65 | 590 | 3× 132 rev | `plumber Idaho Falls ID` | 5 dedicated, 1 EMD, 0 pSEO, 1 local, 3 directory |

### Reading a row

- **STOP** on any `EMD > 0` or `pSEO > 0` — a city exact-match domain or a programmatic network already holds that slot with authority a new domain does not have.
- **STOP** on 4+ dedicated pages, 2+ under a map pack of 100+ reviews, or 5+ local firms on page one whatever their titles say.
- **WATCH** when page one does not name the town (Google read the query as research) -- judge it on the service queries.
- **GO with EMD**: only small local pages under a weak pack, 100+ searches, and a city+trade .com still free.
- `pricing: flat` means the payout is identical nationwide, so choosing this market over another buys nothing on the revenue side; judge it on volume and competition alone.
- A pack of three businesses at 500+ reviews takes most of the clicks even when the organic SERP is open.

### Gates this scan cannot answer

Two decisions are not in any feed and must be confirmed with the network before a domain is bought:

1. **Is the offer duration-based or buyer-qualified?** Only a stated billable duration is verifiable from your own call log. "Booked appointment" is the buyer's judgement, not a number.
2. **What hours does the buyer answer?** Emergency niches earn at 2am. A 9-to-5 buyer drops exactly the traffic that converts best.

Search volume is measured here only for the broad trade term. The Mode 5 Area Plan in the launch plan measures every town and keyword before a page is written.

---
`opportunity = serp_score / 100 × bundle_value`. An open SERP on a cheap payout and a rich payout behind six dedicated pages both score low, which is the point.
