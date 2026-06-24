# Extraction Stack — what each source actually is

| Need | Tool | What it really is | Cost |
|---|---|---|---|
| Competitor **paid ads** (count, pages, platforms, format, CTA, creative text) | **Apify actor `apify/facebook-ads-scraper`** | Scrapes the public **Meta Ad Library**. Run-sync endpoint returns dataset items. **No separate Meta token** — your Apify token covers it. | ~$0.0058/ad |
| Own **Instagram posts / followers / comments** | `apify/instagram-scraper`, `apify/instagram-comment-scraper` | IG profile/post/details + comments | Apify credit |
| Own **Facebook posts** | `apify/facebook-posts-scraper` | FB page posts | Apify credit |
| (optional) **Reddit** chatter | `trudax/reddit-scraper-lite` | Subreddit/keyword posts | Apify credit |
| **YouTube** subs/views/engagement | **YouTube Data API v3** (`search`,`channels`,`playlistItems`,`videos`) | Official Google API. Use **median** views. | Free (10k units/day) |
| **News / PR / LinkedIn / trends** | **Serper.dev** (`/news`, `/search`) | Google results via API (header `X-API-KEY`) | 2,500 free, then paid |
| **Keyword volume + CPC** | **seodata.dev** `GET /v1/keyword?q=&country=ae` | Returns volume, cpc (USD), competition | Free tier (register for 500/mo) |
| **Sentiment + theme scoring** | **Claude analyst judgment** | Not a library — read the text and score it | — |

## Important honesty note on "Google ads"
There is **no public API that scrapes Google's live ad auction** (CPC/spend is private). What this kit calls the
"Google / search" layer is built from:
- **seodata.dev** — keyword search **volume + market CPC estimate** (not a competitor's actual spend), and
- **Serper.dev** — who ranks/appears for a term.
So "search battleground" = *market* CPC and volume, not a rival's real bid. Label it that way.

## Meta Ad Library call (the load-bearing one)
```
POST https://api.apify.com/v2/acts/apify~facebook-ads-scraper/run-sync-get-dataset-items?token=<APIFY_TOKEN>&maxItems=<CAP>
body: {"startUrls":[{"url":
  "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=<XX>&q=<PROJECT>&search_type=keyword_unordered&media_type=all",
  "method":"GET"}],"count":<CAP>}
```
- `country=AE` Dubai / `IN` India (etc.). Returns `adArchiveID`, `pageName`, `publisherPlatform`, `snapshot` (body/cards/cta/videos/images), `isActive`.
- **Dedup by `adArchiveID`. Count `isActive`. Inspect `pageName` (`top_pages`) for contamination.**

## apify-client gotcha
`client.actor(...).start()` and `client.run(id).get()` return **objects, not dicts** — access via `getattr`
(see the `fld()` helper in `03_apify.py`). The run-sync HTTP endpoint (used for Meta) returns plain JSON.
