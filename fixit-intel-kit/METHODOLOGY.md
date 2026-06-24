# Methodology — what makes the numbers trustworthy

The scrapers are the easy part. The value is in **judgment**: only filling the three intelligence views
(Pulse, Competition, Strategy) + Explorer with **fresh, real, last-30-day data**, never carrying forward old
values, and **verifying every load-bearing fact** before it drives a recommendation.

## 1. Provenance — tag every number
Mark each figure so the reader knows how solid it is:
- 🟢 **measured** — directly scraped (ad counts, followers, video views, CPC volume)
- 🟡 **inferred** — derived from measured data (objective from CTA+format)
- 🟠 **judged** — Claude analyst judgment (sentiment, theme scoring)
- 🔵 **modeled** — estimated/extrapolated (reach from followers)
- ⚠️ **caveat** — known contamination or low confidence
- 🔷 **corporate** — organic data from a group-level handle, NOT the specific project

If you can't tag it, you can't ship it. Don't fabricate; if a value isn't measurable, say so.

## 2. The deep-verification pass (`04_verify.py`) — non-negotiable
Raw Meta Ad Library counts are **noisy**. Always:
- **De-noise by `top_pages`.** A high count whose top page is a *salon / nursery / clinic / supermarket / portal*
  is FALSE. The keyword matched an unrelated local business, not a property advertiser.
- **Resolve 0-results.** A competitor showing 0 ads usually just didn't match the term — retry with the
  developer name, the sub-community, or a known broker page. (e.g. "Greenville" 0 → "Emaar South" 39.)
- **Uncap the heavy advertisers.** If one target hits the cap, re-pull at a higher `maxItems` for a true number.

### Dubai-specific gotcha (country=AE)
Project names = place names, so the Ad Library is heavily contaminated. **Verified real examples:**
- "Tilal Al Ghaf" raw 59 → ~12 real (rest were **nurseries**)
- "Dubai Hills" raw 80 → mostly **Bayut/portal resale listings**, not the developer
- "Town Square" raw 1 → a **Spinneys supermarket**
- "The Crest" raw 12 → ~0–2 real (top pages were **a salon, a kids store, a meat shop**)

Without the verification pass you will name the wrong "heaviest advertiser." With it, you catch the truth.

## 3. Read counts in context — don't over-interpret a low number
Some segments are **brand/PR-driven, not Meta-ad-driven**. Ultra-luxury branded towers sell via record-sale PR
and brokers, not lead-gen ads — so 5 ads can be *tier-normal*, not "under-marketing." Check the whole field
before calling a number a problem. The lever there is brand + district search + investor framing, not ad volume.

## 4. Stats hygiene
- YouTube: use **median** views, never mean — one promoted/viral video blows up the average.
- Engagement %: (likes+comments)/views or /followers, per channel; compare like-for-like.
- Dedup Meta ads by `adArchiveID`; count only `isActive`.
- Sentiment: read the actual captions/comments and score them — don't assume positive.

## 5. The corporate-handle problem
When the client is a big developer, its IG/YouTube are **group-level** (cover dozens of projects). Decide the
focal with the client:
- **Project-only** — scope ads/press/search to the project; flag organic as corporate (🔷), since no
  project-specific channel exists.
- **Brand-level** — benchmark the whole developer.
Either way, never present corporate organic as if it were the project's.

## 6. Recommendations = evidence + win-metric (not sentiment guesses)
Each recommendation carries:
- **EVIDENCE** — the measured signals behind it (e.g. "135K/mo district search at comp 0.12; brand term = 0")
- **signal count** — how many independent data points align
- **confidence %**
- **WIN metric** — what success looks like (rank #1, qualified leads, sentiment hold)
- **kill/scale rule** — when to cut or double down

A recommendation that doesn't cite measured evidence doesn't ship.

## 7. Explorer = the proof layer
Every claim on the first three screens must be checkable in Explorer: real captions/headlines verbatim +
**clickable source links** (IG/FB permalinks, news URLs, YouTube watch links, Ad-Library links). Build it with
`05_build_explorer.py` and make `renderEx()` render each row's `url` as an `<a href>`.
