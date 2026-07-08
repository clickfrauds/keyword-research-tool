# Manual Keyword Refinement Prompt (zero API cost)

Jab aap API use nahi karna chahte, ye prompt **claude.ai** (ya Claude app) par
paste karein aur neeche apna keyword data laga dein. Ye bilkul wahi kaam karega
jo pipeline ka Stage 3 karta hai — ad group themes, zero cannibalization.

**Data kahan se aayega:** Google Ads Keyword Planner se export, ya is tool ka
`keyword_data_output.txt` — dono chalega. Har line par: keyword, monthly
searches, competition (LOW/MEDIUM/HIGH). Trend/CPC ho to aur behtar.

---

## COPY BELOW THIS LINE ⬇️

You are a senior Google Ads account strategist. Below is real keyword data
from Google Ads Keyword Planner for my business.

MY BUSINESS: [business name]
NICHE: [what the business does, e.g. "custom furniture and carpentry — wardrobes, kitchen cabinets, TV units"]
TARGET LOCATION: [e.g. Dubai, UAE]

Your ONLY job: organise the commercially viable keywords into tightly-themed
Google Ads ad groups with ZERO cannibalization. Do NOT write ads, FAQs or
content.

HARD RULES:
1. Between 1 and 7 ad groups. The COUNT MUST COME FROM THE DATA: one group
   per genuinely distinct commercial theme. If the data only supports 3
   themes, give me 3 groups. Never pad with thin groups, never split one
   theme into two.
2. ZERO CANNIBALIZATION:
   - Every keyword appears in AT MOST one group.
   - Group themes must be mutually exclusive — a real search query should
     match exactly one group, never two.
   - For every group, give me negative keywords = the distinctive core terms
     of the OTHER groups (negative-keyword siloing), so Google can never
     serve two of my groups against the same query.
3. EXCLUDE keywords that are: informational/question queries (list them
   separately as "SEO content keywords" — they are blog/FAQ material, not
   ads material), irrelevant to my business, or competitor brand names.
4. Separately list: voice-search style questions, and local-intent keywords
   ("near me" / location-specific).
5. Prioritize by the actual volume and competition numbers — low-competition
   keywords with decent volume and buying intent are the best opportunities.

FORMAT YOUR ANSWER AS:

### Ad Group 1: [name] (priority: high/medium/low, match type: phrase/exact)
Theme: [one sentence — the single user intent]
Keywords: [list with volume next to each]
Negative keywords: [list]

...same for each group...

### Excluded — SEO content keywords (not for ads)
### Voice-search questions
### Local-intent keywords
### Strategy notes (2-3 sentences)

MY KEYWORD DATA:
[YAHAN APNA DATA PASTE KAREIN — keyword, searches, competition per line]

## COPY ABOVE THIS LINE ⬆️
