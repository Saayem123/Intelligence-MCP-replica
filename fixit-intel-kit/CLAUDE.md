# Agent runbook — building a Fixit competitive-intelligence dashboard

You are building a competitive-marketing-intelligence dashboard for a real-estate developer/project.
Fill ONLY the three intelligence views (**Market Pulse, Competition, Strategy**) + the **Explorer** proof
layer, with **fresh, real, last-30-day scraped data**. Never fabricate. Never carry forward old/template values.
Read `METHODOLOGY.md` first — the verification pass and provenance tags are mandatory, not optional.

## Inputs you need from the user (ask if missing)
- Client developer + the specific **project** to focus on
- Social handles (IG / FB / LinkedIn / YouTube) — confirm whether they are **project-specific or corporate/group-level**
- The competitor list (project + developer for each)
- Market: country (`AE`/`IN`/…), currency
- Confirm scope: project-level vs brand-level focal (matters most when the client is a large developer)

## Step 1 — recon & config
1. Web-search the project: confirm price, unit types, size, payment plan, handover, any eligibility (e.g. Golden Visa). Web-search current press for the project, the developer, and the district.
2. Resolve the own YouTube channel id (YouTube API `search type=channel`).
3. Write `config.json` from `config.example.json`. Set `is_corporate_handle` correctly.
4. Check Apify budget: `GET https://api.apify.com/v2/users/me/limits?token=<TOKEN>`.

## Step 2 — free scrapes
`python scripts/01_youtube.py` then `python scripts/02_press_cpc.py`. Read the outputs. The **district/area
keyword** (high volume, low competition) is usually the strategic centerpiece — make sure it landed.

## Step 3 — Apify scrape
`python scripts/03_apify.py` (cap stays low to control cost). **Then READ `out/meta_ads.json` and inspect
`top_pages` for every competitor.** Note any whose top page is a non-real-estate business.

## Step 4 — DEEP VERIFICATION (the step that earns trust)
- Run `python scripts/04_verify.py` (auto-flags contamination).
- Edit its `ALT_TERMS` (to resolve 0-result competitors via developer/sub-community/broker terms) and `UNCAP`
  (to re-pull heavy advertisers at higher maxItems), then re-run. Use `APIFY_TOKEN2` if the first nears its cap.
- For any `contamination_flag`, make a judged real-count and tag it ⚠️. **In Dubai, expect heavy contamination
  (project names = place names).** Cross-check against press before trusting a count.
- Read the own IG posts + comments; score sentiment yourself (don't assume positive).

## Step 5 — write the FILL_SHEET
Write `out/FILL_SHEET.md` (see `examples/`): every value provenance-tagged, the verified SOV table, the
strategic shape, and the whitespace. This is your single source of truth for filling the dashboard.

## Step 6 — build the dashboard
1. `python scripts/05_build_explorer.py` → `out/ex_array.js`.
2. Copy `templates/dashboard_template.html` → `fixit_<client>.html`.
3. Fill the blocks. The template is a known shape — use **soft-replace Python scripts** (collect a MISS list,
   never assert-crash) rather than dozens of manual edits; it's far more context-efficient. Blocks:
   - **Pulse**: KPI cards, channel table, paid/organic split caption, the three signal lists.
   - **Competition**: the `COMP={organic:[...],paid:[...]}` object (per-developer→per-project), the 3 heat
     arrays (theme-density / platform-strength / channel-perf), an **Ad-type & placement** section (real
     platforms/CTA), the **Search battleground** rows (market CPC in your currency), Channel partners.
   - **Strategy**: `params`, the keep/leave `playbook`, and the `RECS=[...]` array in **evidence+win-metric
     format** (add `conf` and `sig` fields; render "Win: … · conf X% · N△").
   - **Explorer**: paste `out/ex_array.js` over the template's `EX=[...]`, and update `renderEx()` so each row's
     `txt` is wrapped in `<a href="${r.url}" target="_blank">…↗</a>` and shows `r.date`.
4. **Global cleanup**: swap every template demo token for your market — currency symbol, geography, placeholder
   rival names — so nothing from the sample build leaks through.

## Step 7 — validate (always)
- `node --check` the extracted `<script>` blocks → JS must parse.
- `<div>` / `</div>` counts must balance.
- Sweep for leftover wrong-market tokens (old currency, old city, old rival names) → must be zero.
- Render it: `python -m http.server 8899 --directory <dir>` and open `fixit_<client>.html`; confirm the views
  render and there are **no console errors**. (If using the Claude preview tools, set the viewport explicitly —
  it can default to a collapsed width.)

## Guardrails
- Only Pulse / Competition / Strategy / Explorer get filled. Leave other template sections as generic demo (but
  still swap their currency/geo tokens).
- Every load-bearing fact is measured or explicitly caveated. If asked "what did you fabricate?", the answer is
  "nothing — here's the provenance."
- Recommendations cite evidence + a win-metric. No sentiment guesses.
