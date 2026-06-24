#!/usr/bin/env python3
"""DEEP VERIFICATION PASS — the step that separates real intel from garbage.
   1) Resolve 0-result competitors by retrying with alternate / broker terms.
   2) De-noise contaminated counts: if top_pages are non-real-estate businesses
      (salon, nursery, clinic, supermarket, portal), the raw count is FALSE — flag it.
   3) Uncap the heavy advertisers (raise maxItems) to get a truer number.
   Uses APIFY_TOKEN2 if present (so the verification re-pull doesn't exhaust token 1).
   Edit ALT_TERMS for the specific competitors you need to resolve, then re-run.
   This is deliberately a HUMAN+AGENT-IN-THE-LOOP script: read out/meta_ads.json first, decide what to re-pull."""
import json, urllib.parse, urllib.request, ssl
from lib import cfg, env, load, save, OUT
C = cfg(); T = env("APIFY_TOKEN2", required=False) or env("APIFY_TOKEN"); CO = C["country"]

# Words that mean a page is NOT a real-estate advertiser (extend per market):
NOISE = ["salon","saloon","beauty","nursery","kids","school","meat","grocery","supermarket","spinneys",
         "clinic","dental","restaurant","cafe","cleaning","laundry","portal","bayut","property finder"]

# EDIT THIS: competitors to re-resolve (name -> list of alternate search terms)
ALT_TERMS = {
    # "Peninsula Residences": ["Peninsula Business Bay", "Peninsula Select Group Dubai"],
    # "Canal Heights": ["Canal Heights Cavalli", "DAMAC Canal Heights"],
}
# EDIT THIS: heavy advertisers to re-pull uncapped (name -> term, higher cap)
UNCAP = {
    # "Bluewaters Residences": ("Bluewaters Residences Dubai", 60),
}

def meta(term, cap):
    url = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country="+CO
           +"&q="+urllib.parse.quote(term)+"&search_type=keyword_unordered&media_type=all")
    api = f"https://api.apify.com/v2/acts/apify~facebook-ads-scraper/run-sync-get-dataset-items?token={T}&timeout=200&maxItems={cap}"
    req = urllib.request.Request(api, data=json.dumps({"startUrls": [{"url": url, "method": "GET"}], "count": cap}).encode(),
                                 headers={"Content-Type": "application/json"})
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=240, context=ctx) as r: return json.load(r)

def count(term, cap):
    try: items = meta(term, cap)
    except Exception: return None, []
    if isinstance(items, dict): return None, []
    seen, active, pages = set(), 0, {}
    for a in items:
        aid = a.get("adArchiveID") or a.get("adArchiveId")
        if aid in seen: continue
        seen.add(aid)
        if a.get("isActive"): active += 1
        pg = (a.get("pageName") or "").strip(); pages[pg] = pages.get(pg, 0)+1
    return active, sorted(pages.items(), key=lambda x: -x[1])[:3]

ads = load("meta_ads.json")

# auto-flag contamination on what we already have
print("=== contamination scan (top page non-RE?) ===")
for name, v in ads.items():
    if not isinstance(v, dict) or v.get("error"): continue
    tp = v.get("top_pages") or []
    top = (tp[0][0] if tp and tp[0] else "").lower()
    if top and any(n in top for n in NOISE):
        v["contamination_flag"] = f"top page '{tp[0][0]}' looks non-RE — raw count likely INFLATED"
        print(f"  ⚠ {name}: {v['contamination_flag']}")

print("=== resolve 0-results (ALT_TERMS) ===")
for name, terms in ALT_TERMS.items():
    best, bp = 0, None
    for term in terms:
        a, pg = count(term, 30); print(f"  {name}/'{term}': {a} {pg}", flush=True)
        if a and a > best: best, bp = a, pg
    if name in ads: ads[name]["active"] = best; ads[name]["top_pages"] = bp or ads[name].get("top_pages"); ads[name]["verified"] = True

print("=== uncap heavies (UNCAP) ===")
for name, (term, cap) in UNCAP.items():
    a, pg = count(term, cap); print(f"  {name}: {a} {pg}", flush=True)
    if name in ads: ads[name]["active"] = a or ads[name]["active"]; ads[name]["top_pages"] = pg; ads[name]["verified"] = True

save("meta_ads.json", ads)
print("\nDone. Re-read out/meta_ads.json — anything with contamination_flag needs a manual real-count judgment.")
