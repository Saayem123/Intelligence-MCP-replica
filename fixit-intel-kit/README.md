# Fixit Competitive-Intelligence Kit

Reproduce the Fixit real-estate competitive-intelligence dashboards (Pulse · Competition · Strategy · Explorer)
for any developer/project, in any market, with **real scraped data + a deep-verification pass + evidence-based recommendations.**

Built for a workflow where **Claude Code does the orchestration** (recon, verification judgment, dashboard
filling) and these scripts do the deterministic scraping. You can also run the scripts by hand.

---

## What you get
- 5 config-driven Python scrapers (`scripts/`) — YouTube, press/CPC, Meta Ad Library + own socials, verification, Explorer builder.
- The four-box dashboard template (`templates/dashboard_template.html`).
- `METHODOLOGY.md` — the judgment that makes the numbers trustworthy (provenance, verification, contamination).
- `CLAUDE.md` — paste-able instructions so your own Claude Code agent runs the whole thing.
- `examples/` — a real filled data-sheet from a completed build (Creek Bay / Emaar).

---

## One-time setup
1. **Python** ≥ 3.10. `pip install -r requirements.txt` (apify-client, python-dotenv). Node.js for `node --check`.
2. **Keys** — copy `.env.template` → `.env`, fill in. See that file for where to get each (Apify, YouTube Data API v3, Serper, seodata). Total cost per client run ≈ **$1** (Apify); everything else is free-tier.
3. **Config** — copy `config.example.json` → `config.json`, edit for your client:
   - `client`, `project`, `developer`, `country` (`AE` Dubai / `IN` India), `currency`, `usd_to_currency` (AED 3.67, INR 83.5)
   - `own` handles — **set `is_corporate_handle: true` if the client's social handles are group-level** (cover many projects), not project-specific. This changes how you read organic data.
   - `competitors[]` — name, developer, `meta_term` (search string), `yt_query` (channel search)
   - `cpc_keywords`, `press_brands`, `trend_queries`

---

## Run order
```bash
cd fixit-intel-kit
python scripts/01_youtube.py        # → out/yt.json        (free)
python scripts/02_press_cpc.py      # → out/press,trends,cpc.json   (free; seodata may rate-limit — that's ok)
python scripts/03_apify.py          # → out/meta_ads.json + own_brand/followers/comments.json  (~$1)
#  ↑ READ out/meta_ads.json NOW. Look at top_pages on every competitor.
python scripts/04_verify.py         # auto-flags contamination; edit ALT_TERMS / UNCAP, re-run to resolve 0s & uncap heavies
python scripts/05_build_explorer.py # → out/ex_array.js    (free)
```

## Then build the dashboard (Claude Code does this best — see CLAUDE.md)
4. Write a `FILL_SHEET.md` from `out/*.json` with **provenance tags** (🟢 measured / 🟡 inferred / 🟠 judged / 🔵 modeled / ⚠️ caveat). See `examples/`.
5. Copy `templates/dashboard_template.html` → `fixit_<client>.html`.
6. Fill the four intelligence views + Explorer (Pulse KPIs/channels/signals, Competition `COMP` object + heat arrays + ad-type + search battleground, Strategy params/playbook/`RECS`, paste `out/ex_array.js` into `EX`). Make `renderEx()` wrap content in a clickable `<a href="${r.url}">` so every row is verifiable.
7. Global cleanup: swap any template demo tokens (currency, geography, placeholder rival names) for your market.
8. **Validate:** `node --check` the embedded JS; check `<div>`/`</div>` balance; sweep for leftover wrong-market tokens; render via `python -m http.server` and confirm no console errors.

---

## Cost & limits
- Apify: free tier ~$5/mo credit per account, ~$0.0058/ad. A 11-target run at `apify_cap: 30` ≈ **$0.90**. Keep `APIFY_TOKEN2` for the verification re-pull.
- YouTube Data API: free, 10k units/day (plenty).
- Serper: 2,500 free queries on signup.
- seodata: anonymous tier rate-limits fast; register (free, 500/mo). Get the **district/area term** above all — it's the load-bearing one.

See `METHODOLOGY.md` before your first run — the verification pass and contamination handling are what make this trustworthy rather than plausible-but-wrong.
