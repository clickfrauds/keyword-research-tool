/*
 * extract_call_intel.js — recapture the Call Intelligence dataset.
 *
 * The dashboard has no JSON API. /api/call-intel is a full HTML page that the
 * app loads in an iframe, and the whole dataset sits in one ~756 KB inline
 * script as `const D = {...}`, never on `window`. So it cannot be fetched —
 * it has to be parsed out of the page that renders it.
 *
 * HOW TO RUN
 *   1. Log in at ranklocal.cc, then open  https://ranklocal.cc/api/call-intel
 *      directly (the page itself, not the dashboard that frames it).
 *   2. Open DevTools -> Console, paste this whole file, press Enter.
 *   3. Three CSVs download: niches, sub-services, specific services.
 *      Set DUMP_PHRASES = true below for the phrase level as well (large).
 *
 * Shape of D.taxo:
 *   [ { niche, count, subs:[ { name, count,
 *       specifics:[ { name, count,
 *         items:[ { phrase, urgency, outcome, paid } ] } ] } ] } ]
 */

const DUMP_PHRASES = false;   // true = also dump every recorded call phrase

(function () {
  const src = [...document.querySelectorAll('script')]
    .map(s => s.textContent || '')
    .sort((a, b) => b.length - a.length)[0] || '';

  // Walk the literal rather than regexing it — the phrases contain braces,
  // quotes and apostrophes, and a lazy match stops at the first one of them.
  function grab(name) {
    const m = new RegExp('(?:const|let|var|window\\.)\\s*' + name + '\\s*=\\s*').exec(src);
    if (!m) return null;
    let i = m.index + m[0].length;
    const open = src[i];
    if (open !== '[' && open !== '{') return null;
    const close = open === '[' ? ']' : '}';
    let depth = 0, inStr = false, q = '', esc = false;
    for (let j = i; j < src.length; j++) {
      const c = src[j];
      if (inStr) {
        if (esc) esc = false;
        else if (c === '\\') esc = true;
        else if (c === q) inStr = false;
        continue;
      }
      if (c === '"' || c === "'" || c === '`') { inStr = true; q = c; continue; }
      if (c === open) depth++;
      else if (c === close) { depth--; if (depth === 0) return src.slice(i, j + 1); }
    }
    return null;
  }

  const raw = grab('D');
  if (!raw) { console.error('D not found — is this /api/call-intel itself?'); return; }
  const T = JSON.parse(raw).taxo;
  console.log('niches:', T.length);

  const pct = (n, d) => (d ? Math.round(n * 100 / d) : 0);
  const stats = items => {
    let i = 0, p = 0, b = 0, u = 0;
    for (const it of items) {
      i++;
      if (it.paid) p++;
      if (it.outcome === 'booked') b++;
      if (it.urgency && it.urgency !== 'routine') u++;
    }
    return [pct(p, i), pct(b, i), pct(u, i)];
  };

  const esc = v => {
    const s = String(v == null ? '' : v);
    return /[",\n|]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };

  const save = (name, header, rows) => {
    const csv = [header, ...rows].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = name;
    a.click();
    console.log(name, rows.length, 'rows');
  };

  const nicheRows = [], subRows = [], specRows = [], phraseRows = [];
  for (const n of T) {
    const all = [];
    for (const s of n.subs) for (const x of s.specifics) all.push(...x.items);
    nicheRows.push([n.niche, n.count, n.subs.length,
                    n.subs.reduce((a, s) => a + s.specifics.length, 0),
                    ...stats(all)].map(esc).join('|'));

    for (const s of n.subs) {
      const si = [];
      for (const x of s.specifics) si.push(...x.items);
      subRows.push([n.niche, s.name, s.count, ...stats(si)].map(esc).join('|'));

      for (const x of s.specifics) {
        specRows.push([n.niche, s.name, x.name, x.count, ...stats(x.items)].map(esc).join('|'));
        if (DUMP_PHRASES) {
          for (const it of x.items) {
            phraseRows.push([n.niche, s.name, x.name, it.phrase,
                             it.urgency, it.outcome, it.paid ? 1 : 0].map(esc).join('|'));
          }
        }
      }
    }
  }

  save('niches.csv', 'niche|calls|subs|specifics|paid_pct|booked_pct|urgent_pct', nicheRows);
  save('subs.csv', 'niche|sub_service|calls|paid_pct|booked_pct|urgent_pct', subRows);
  save('specifics.csv', 'niche|sub_service|specific_service|calls|paid_pct|booked_pct|urgent_pct', specRows);
  if (DUMP_PHRASES) {
    save('phrases.csv', 'niche|sub_service|specific_service|phrase|urgency|outcome|paid', phraseRows);
  }
})();
