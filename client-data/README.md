# Client Data — SEO run outputs

**AUTO LINK (naya, recommended):** ab manual commit ki zaroorat NAHI. Har SEO
run apna `website_builder_inputs.json` khud `results-data` branch par push
karta hai aur form ke result page par **"Mode 4 SEO data link"** copy-paste
field mein raw link de deta hai:

```
https://raw.githubusercontent.com/clickfrauds/keyword-research-tool/results-data/results/<request-id>.seo.json
```

Wahi link website builder ke Mode 4 **SEO data URL** field mein paste karein.
(Builder normal GitHub page links, repo file paths aur inline JSON bhi accept
karta hai.)

---

**Manual/archive option (purana tariqa, ab bhi chalta hai):** kisi client ka
JSON lambi muddat ke liye yahan commit karein:

```
client-data/<client-slug>.json     e.g. dubai-tank-cleaners.json
```

- File GitHub par kholo → "Raw" button → wahi URL copy karo.
- Naya SEO run karo to file yahan replace/commit karo — history git mein rehti hai.
- Example entry: `dubai-tank-cleaners.json` (live tank-cleaning run, 8 clusters / 37 questions).
