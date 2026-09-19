# Opportunity scan

- Dataset **2026-09-18** · scanned 2026-09-19
- Filters: `Call` · payout ≥ **$40** · population **8,000–150,000** · niches **Roofing**
- **51** candidate cities · **24** SERP-scored · SerpApi: 25 credit(s) spent · 0 served free from cache
- Verdict by city: **1 GO** · 1 WATCH · 22 STOP

## Verdict by city

Judged on the city's **worst** scored query — one open sub-service under a taken head term is not an open market.

Gates, in order: **Payout · Economics · Demand · SERP · Coverage** (✅ pass · 🟡 borderline · ❌ fail · ❔ unknown).

| Verdict | Gates | City | Niche | Payout | Searches/mo | Nearest metro | Why |
|---|---|---|---|---|---|---|---|
| **GO** | ✅✅✅✅✅ | Biloxi, MS | Roofing | $50.40 | 140 | 75 mi · New Orleans, LA | SERP 100, 0 dedicated, 140/mo |
| **WATCH** | ✅✅✅🟡✅ | Bellingham, WA | Roofing | $66.15 | 110 | 79 mi · Seattle, WA | `roofer Bellingham WA`: 2 small local pages, weak map pack (<100 reviews); SERP 35 < 60 |

<details><summary>22 STOP cities</summary>

| City | Why |
|---|---|
| Charlottesville, VA | `roofer Charlottesville VA`: 4 dedicated roofing pages |
| Topeka, KS | `roofer Topeka KS`: 3 dedicated roofing pages |
| Tyler, TX | `roofer Tyler TX`: 4 dedicated roofing pages; map pack at 517 reviews |
| Columbia, MO | `roofer Columbia MO`: 4 dedicated roofing pages |
| Middletown, NY | `roofer Middletown NY`: 3 dedicated roofing pages |
| Traverse City, MI | `roofer Traverse City MI`: 3 dedicated roofing pages |
| Bloomington, IL | `roofer Bloomington IL`: 4 dedicated roofing pages |
| Johnson City, TN | `roofer Johnson City TN`: 3 dedicated roofing pages |
| Eau Claire, WI | `roofer Eau Claire WI`: 4 dedicated roofing pages |
| Kingston, NY | `roofer Kingston NY`: 3 dedicated roofing pages |
| Greenville, NC | `roofer Greenville NC`: 4 dedicated roofing pages |
| Dothan, AL | `roofer Dothan AL`: 5 dedicated roofing pages |
| Temple, TX | `roofer Temple TX`: 5 dedicated roofing pages |
| Abilene, TX | `roofer Abilene TX`: 5 dedicated roofing pages |
| Franklin, VA | `roofer Franklin VA`: 6 dedicated roofing pages |
| Beaumont, TX | `roofer Beaumont TX`: 1 city EMD on page one; 5 dedicated roofing pages |
| Palm Coast, FL | `roofer Palm Coast FL`: 6 dedicated roofing pages |
| Madison, MS | `roofer Madison MS`: 1 city EMD on page one; 5 dedicated roofing pages |
| Winchester, VA | `roofer Winchester VA`: 1 city EMD on page one; 6 dedicated roofing pages |
| Florence, SC | `roofer Florence SC`: 1 city EMD on page one; 6 dedicated roofing pages |
| Rochester, MN | `roofer Rochester MN`: 1 city EMD on page one; 6 dedicated roofing pages |
| Harrisonburg, VA | `roofer Harrisonburg VA`: 6 dedicated roofing pages |

</details>

## Launch plan

Every value below is already filled in and is also in `launch_plan.json`. Do the steps in order; each one is a gate.

### Mississippi · Roofing

- **GO:** Biloxi
- 140 searches/mo across these towns · best payout $50.40
- Shape: add Biloxi as area page(s) on a Mississippi state site

1. **Confirm by eye** (free, 2 minutes) — page one should hold directories and out-of-town sites, not local pages built for the town:
   - https://www.google.com/search?q=roofer+Biloxi+MS
2. **Confirm with LeadSmart** — the ZIPs are bought for this niche at call (not CPL), the billable duration, and the hours the buyer answers.
3. **Keyword tool → Mode 5 Area Plan**

   | Field | Value |
   |---|---|
   | business_name | `Mississippi Roofer Pros` |
   | niche_description | `roofing referral service connecting homeowners with licensed local pros` |
   | target_location | `Mississippi, United States` |
   | primary_service | `roofer` |
   | min_area_volume | `20` |
   | extra_areas | `Biloxi` |

4. **Website builder → Mode 5** with the `.mode5.json` link from step 3

   | Field | Value |
   |---|---|
   | mode | `5` |
   | business_name | `Mississippi Roofer Pros` |
   | industry | `roofer` |
   | main_service | `Roofer` |
   | sub_services | `Roof Leak Repair, Roof Repair, Roof Replacement, Roof Inspection, Shingle Repair, Missing Shingle Repair, Tile Roof Replacement` |
   | city | `Mississippi` |
   | country | `United States` |
   | phone | `<LeadSmart tracking number>` |
   | domain | `<new domain>` |
   | extras | `{"pseo_plan_url": "<raw .mode5.json link from step 3>", "site_profile": "pay_per_call", "footer_credit": "no", "footer_sitemap_link": "no"}` |

5. **After 3-4 weeks in GSC** — Mode 2 service pages under the area hubs that show impressions (the Mesa/Phoenix pattern, `m2_merge.py`).

## Not yet scanned (26 cities)

Next run: raise `max_serp_checks` — every SERP above comes from cache for free, so the credits go only to these.

| City | Niche | Payout | Searches/mo |
|---|---|---|---|
| Jacksonville, NC | Roofing | $45.67 | 90 |
| Flagstaff, AZ | Roofing | $43.75 | 90 |
| Albany, GA | Roofing | $52.50 | 70 |
| Twin Falls, ID | Roofing | $50.51 | 70 |
| Johnstown, PA | Roofing | $48.83 | 70 |
| New Bern, NC | Roofing | $47.60 | 70 |
| Lake City, FL | Roofing | $66.50 | 50 |
| Ormond Beach, FL | Roofing | $66.50 | 50 |
| Boone, NC | Roofing | $44.00 | 70 |
| Boynton Beach, FL | Roofing | $59.85 | 50 |
| Henderson, KY | Roofing | $40.25 | 70 |
| Brunswick, GA | Roofing | $52.50 | 50 |
| Cookeville, TN | Roofing | $51.98 | 50 |
| Crossville, TN | Roofing | $51.98 | 50 |
| Gadsden, AL | Roofing | $49.00 | 50 |

## All scored queries (top 30)

| # | Opp | SERP | Payout | Searches/mo | Pack | Query | Occupied by |
|---|---|---|---|---|---|---|---|
| 1 | **50** | 100 | $50.40 | 140 | 3× 73 rev | `roofer Biloxi MS` | 0 dedicated, 0 EMD, 0 pSEO, 3 local, 5 directory |
| 2 | **15** | 35 | $43.75 | 260 | 3× 32 rev | `roofer Charlottesville VA` | 4 dedicated, 0 EMD, 0 pSEO, 2 local, 2 directory |
| 3 | **18** | 34 | $54.25 | 210 | 3× 335 rev | `roofer Topeka KS` | 3 dedicated, 0 EMD, 0 pSEO, 3 local, 3 directory |
| 4 | **9** | 22 | $41.11 | 390 | 3× 517 rev | `roofer Tyler TX` | 4 dedicated, 0 EMD, 0 pSEO, 0 local, 5 directory |
| 5 | **13** | 24 | $54.25 | 210 | 4× 410 rev | `roofer Columbia MO` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 6 | **23** | 35 | $66.15 | 110 | 3× 75 rev | `roofer Bellingham WA` | 2 dedicated, 0 EMD, 0 pSEO, 3 local, 3 directory |
| 7 | **27** | 35 | $78.38 | 90 | 4× 298 rev | `roofer Middletown NY` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 8 | **21** | 35 | $58.80 | 110 | 3× 99 rev | `roofer Traverse City MI` | 3 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 9 | **13** | 32 | $41.25 | 170 | 3× 47 rev | `roofer Bloomington IL` | 4 dedicated, 0 EMD, 0 pSEO, 2 local, 3 directory |
| 10 | **18** | 35 | $51.98 | 90 | 3× 76 rev | `roofer Johnson City TN` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 11 | **22** | 35 | $63.00 | 70 | 4× 21 rev | `roofer Eau Claire WI` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 12 | **30** | 35 | $86.78 | 50 | 3× 87 rev | `roofer Kingston NY` | 3 dedicated, 0 EMD, 0 pSEO, 2 local, 4 directory |
| 13 | **11** | 24 | $47.60 | 110 | 3× 403 rev | `roofer Greenville NC` | 4 dedicated, 0 EMD, 0 pSEO, 1 local, 4 directory |
| 14 | **9** | 18 | $50.40 | 110 | 3× 52 rev | `roofer Dothan AL` | 5 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 15 | **6** | 10 | $59.36 | 110 | 3× 209 rev | `roofer Temple TX` | 5 dedicated, 0 EMD, 0 pSEO, 0 local, 4 directory |
| 16 | **3** | 6 | $45.93 | 170 | 3× 236 rev | `roofer Abilene TX` | 5 dedicated, 0 EMD, 0 pSEO, 1 local, 3 directory |
| 17 | **2** | 4 | $42.63 | 110 | 3× 5 rev | `roofer Franklin VA` | 6 dedicated, 0 EMD, 0 pSEO, 0 local, 3 directory |
| 18 | **0** | 0 | $45.67 | 590 | 3× 29 rev | `roofer Florence SC` | 6 dedicated, 1 EMD, 0 pSEO, 0 local, 3 directory |
| 19 | **0** | 0 | $66.50 | 320 | 3× 90 rev | `roofer Palm Coast FL` | 6 dedicated, 0 EMD, 0 pSEO, 1 local, 2 directory |
| 20 | **0** | 0 | $148.75 | 110 | 3× 159 rev | `roofer Beaumont TX` | 5 dedicated, 1 EMD, 0 pSEO, 0 local, 4 directory |
| 21 | **0** | 0 | $50.40 | 140 | 3× 121 rev | `roofer Madison MS` | 5 dedicated, 1 EMD, 0 pSEO, 1 local, 3 directory |
| 22 | **0** | 0 | $40.95 | 140 | 4× 105 rev | `roofer Harrisonburg VA` | 6 dedicated, 0 EMD, 0 pSEO, 0 local, 3 directory |
| 23 | **0** | 0 | $44.10 | 110 | 3× 120 rev | `roofer Rochester MN` | 6 dedicated, 1 EMD, 0 pSEO, 0 local, 2 directory |
| 24 | **0** | 0 | $49.45 | 90 | 3× 89 rev | `roofer Winchester VA` | 6 dedicated, 1 EMD, 0 pSEO, 1 local, 2 directory |

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
