#!/usr/bin/env python3
"""Meta Ad Library (self + competitors) + own IG/FB posts + followers + comments.  Output: out/meta_ads.json, out/own_brand.json, out/own_followers.json, out/own_comments.json
   COUNTRY-AWARE: uses config.country (AE/IN). CAP keeps spend low (~$0.0058/ad).
   Dedup by adArchiveID, count isActive. Captures platforms + format + CTA inline (for the ad-type table).
   ⚠ Raw page counts are NOISY: in Dubai especially, project names = place names, so the Ad Library
     returns nurseries/salons/supermarkets/portals using that location. ALWAYS inspect top_pages and run 04_verify.py."""
import os, json, time, urllib.parse, urllib.request, ssl
from lib import cfg, env, save, OUT, tag_themes
from apify_client import ApifyClient
C = cfg(); T = env("APIFY_TOKEN"); CAP = C.get("apify_cap", 30); CO = C["country"]
client = ApifyClient(T)

def meta(term):
    url = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country="+CO
           +"&q="+urllib.parse.quote(term)+"&search_type=keyword_unordered&media_type=all")
    api = f"https://api.apify.com/v2/acts/apify~facebook-ads-scraper/run-sync-get-dataset-items?token={T}&timeout=200&maxItems={CAP}"
    req = urllib.request.Request(api, data=json.dumps({"startUrls": [{"url": url, "method": "GET"}], "count": CAP}).encode(),
                                 headers={"Content-Type": "application/json"})
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=240, context=ctx) as r: return json.load(r)

def snaptext(s):
    if not isinstance(s, dict): return ""
    p = []; b = s.get("body")
    if isinstance(b, dict): p.append(b.get("text","") or "")
    elif isinstance(b, str): p.append(b)
    for k in ("title","linkDescription","caption","pageName"):
        if isinstance(s.get(k), str): p.append(s[k])
    return " ".join(x for x in p if x)[:600]
def fmt(s):
    if not isinstance(s, dict): return "?"
    if s.get("videos"): return "Video"
    c = s.get("cards") or []
    return "Carousel/DCO" if len(c) > 1 else ("Image" if (s.get("images") or c) else "?")
def cta(s):
    if not isinstance(s, dict): return ""
    c = s.get("ctaText") or s.get("cta_text") or s.get("ctaType") or ""
    cs = s.get("cards") or []
    return c or ((cs[0].get("ctaText") or cs[0].get("cta_text") or "") if cs else "")

def fld(o, a, b=None):
    if isinstance(o, dict): return o.get(b or a) or o.get(a)
    return getattr(o, a, None) or (getattr(o, b, None) if b else None)
def run_actor(actor, inp, mem=1024, label=""):
    try:
        r = client.actor(actor).start(run_input=inp, memory_mbytes=mem); rid = fld(r, "id"); dl = time.time()+240; st = fld(r, "status")
        while st in ("READY","RUNNING") and time.time() < dl: time.sleep(8); r = client.run(rid).get(); st = fld(r, "status")
        ds = fld(r, "default_dataset_id", "defaultDatasetId"); items = list(client.dataset(ds).iterate_items()) if ds else []
        print(f"  {label}: {st} -> {len(items)}", flush=True); return items
    except Exception as e:
        print(f"  {label}: ERR {type(e).__name__} {str(e)[:70]}", flush=True); return []

# --- Meta Ad Library: self + competitors ---
ads = {}
targets = [("__SELF__", C["meta_self_term"])] + [(c["name"], c["meta_term"]) for c in C["competitors"]]
print(f"META country={CO} cap={CAP}", flush=True)
for name, term in targets:
    label = f"{C['client']} (YOU)" if name == "__SELF__" else name
    try: items = meta(term)
    except Exception as e: print(f"  ! {label}: {type(e).__name__}"); ads[label] = {"error": str(e)[:70]}; continue
    if isinstance(items, dict): ads[label] = {"error": str(items)[:70]}; continue
    seen, active, pages, th, samp, plat, fmts, ctas = set(), 0, {}, {}, [], set(), {}, {}
    for a in items:
        aid = a.get("adArchiveID") or a.get("adArchiveId")
        if aid in seen: continue
        seen.add(aid)
        if a.get("isActive"): active += 1
        pg = (a.get("pageName") or "").strip(); pages[pg] = pages.get(pg, 0)+1
        for pp in (a.get("publisherPlatform") or []): plat.add(pp)
        sn = a.get("snapshot"); f = fmt(sn); fmts[f] = fmts.get(f, 0)+1
        c = cta(sn)
        if c: ctas[c] = ctas.get(c, 0)+1
        txt = snaptext(sn) or pg
        for t in tag_themes(txt): th[t] = th.get(t, 0)+1
        if len(samp) < 3 and txt: samp.append(txt[:160])
    ads[label] = {"unique": len(seen), "active": active,
                  "top_pages": sorted(pages.items(), key=lambda x: -x[1])[:3], "themes": th, "samples": samp,
                  "platforms": sorted(plat), "format": max(fmts, key=fmts.get) if fmts else "?",
                  "cta": max(ctas, key=ctas.get) if ctas else ""}
    save("meta_ads.json", ads)
    print(f"· {label:26} active={active} top={ads[label]['top_pages'][:1]} plat={len(plat)} cta='{ads[label]['cta']}'", flush=True)

# --- own IG/FB posts, followers, comments ---
own = {"instagram": [], "facebook": []}
for r in run_actor("apify/instagram-scraper", {"directUrls": [C["own"]["instagram_url"]], "resultsType": "posts", "resultsLimit": 22, "addParentData": True}, label="ig"):
    if r.get("url"): own["instagram"].append({"caption": (r.get("caption") or "")[:600], "likes": max(r.get("likesCount") or 0, 0), "comments": max(r.get("commentsCount") or 0, 0), "ts": r.get("timestamp"), "url": r["url"]})
if C["own"].get("facebook_url"):
    for r in run_actor("apify/facebook-posts-scraper", {"startUrls": [{"url": C["own"]["facebook_url"]}], "resultsLimit": 22}, label="fb"):
        u = r.get("url") or r.get("postUrl")
        if u: own["facebook"].append({"text": (r.get("text") or r.get("message") or "")[:600], "likes": max(r.get("likes") or 0, 0), "comments": max(r.get("comments") or 0, 0), "ts": r.get("time") or r.get("date"), "url": u})
save("own_brand.json", own)

fol = {}
for it in run_actor("apify/instagram-scraper", {"directUrls": [C["own"]["instagram_url"]], "resultsType": "details"}, mem=512, label="followers"):
    fol = {"followers": it.get("followersCount"), "posts_total": it.get("postsCount"), "name": it.get("fullName")}; print("  followers:", fol, flush=True)
save("own_followers.json", fol)

ig_urls = [p["url"] for p in sorted(own["instagram"], key=lambda p: p["likes"]+p["comments"], reverse=True) if p.get("comments", 0) > 0][:10]
cm = {"instagram": []}
for r in run_actor("apify/instagram-comment-scraper", {"directUrls": ig_urls, "resultsLimit": 8}, mem=512, label="ig-cmts"):
    cm["instagram"].append({"text": (r.get("text") or "")[:240], "owner": r.get("ownerUsername")})
save("own_comments.json", cm)
print(f"\nDONE meta={len(ads)} IG={len(own['instagram'])} FB={len(own['facebook'])} comments={len(cm['instagram'])}")
