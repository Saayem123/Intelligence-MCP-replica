#!/usr/bin/env python3
"""Own channel + competitor-developer YouTube. FREE (YouTube Data API v3).
   Output: out/yt.json  ·  Uses MEDIAN views (not mean — outliers/promoted videos skew the mean).
   NOTE: if own.is_corporate_handle is true, the own channel is group-level, NOT project-specific. Flag it downstream."""
import time, urllib.request, urllib.parse, statistics
from lib import cfg, env, save, OUT
C = cfg(); K = env("YOUTUBE_API_KEY")

def api(path, **p):
    p["key"] = K
    u = f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode(p)
    for a in range(3):
        try:
            with urllib.request.urlopen(u, timeout=25) as r: return __import__("json").loads(r.read())
        except Exception:
            if a == 2: return {}
            time.sleep(1.2)

def channel_meta(cid):
    its = api("channels", part="snippet,statistics,contentDetails", id=cid).get("items", [])
    if not its: return None
    it = its[0]
    return {"channelId": cid, "title": it["snippet"]["title"],
            "subs": int(it["statistics"].get("subscriberCount", 0)),
            "videoCount": int(it["statistics"].get("videoCount", 0)),
            "uploads": it["contentDetails"]["relatedPlaylists"].get("uploads")}

def find_channel(q):
    # The first search hit is often a tiny look-alike (e.g. "DLF Limited" → 193 subs,
    # not DLF's real channel). Pull a few candidates and keep the one with the most subs —
    # official developer channels dominate their own name.
    its = api("search", part="snippet", q=q, type="channel", maxResults=5).get("items", [])
    cands = [i["snippet"]["channelId"] for i in its]
    if not cands: return None
    best, best_subs = cands[0], -1
    for cid in cands:
        m = channel_meta(cid)
        if m and m["subs"] > best_subs: best, best_subs = cid, m["subs"]
    return best

def recent(uploads, n=25):
    ids = [i["contentDetails"]["videoId"] for i in api("playlistItems", part="contentDetails", playlistId=uploads, maxResults=n).get("items", [])]
    if not ids: return []
    out = []
    for it in api("videos", part="snippet,statistics", id=",".join(ids[:50])).get("items", []):
        st = it.get("statistics", {})
        out.append({"id": it["id"], "title": it["snippet"]["title"], "published": it["snippet"]["publishedAt"],
                    "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)), "comments": int(st.get("commentCount", 0))})
    return out

def summarize(vids):
    views = [v["views"] for v in vids]
    ers = [(v["likes"]+v["comments"])/v["views"] for v in vids if v["views"] > 0]
    return {"n": len(vids), "median_views": int(statistics.median(views)) if views else 0,
            "mean_views": int(statistics.mean(views)) if views else 0,
            "median_eng_pct": round(statistics.median(ers)*100, 2) if ers else 0}

res = {}
own = C["own"]
cid = own.get("youtube_channel_id") or find_channel(own.get("youtube_query_fallback", C["developer"]))
if cid:
    m = channel_meta(cid)
    if m:
        v = recent(m["uploads"]); res[f"{C['developer']} (own)"] = {"channel": m, "videos": v, "summary": summarize(v),
            "is_corporate": own.get("is_corporate_handle", False)}
        print(f"OWN {C['developer']} | subs {m['subs']:,} | {summarize(v)}", flush=True)

seen_q = set()
for comp in C["competitors"]:
    q = comp["yt_query"]
    if q in seen_q: continue          # multiple projects share one developer channel
    seen_q.add(q)
    cid = find_channel(q)
    if not cid: print(f"· {comp['developer']}: no channel"); continue
    m = channel_meta(cid)
    if not m or not m.get("uploads"): print(f"· {comp['developer']}: no uploads"); continue
    v = recent(m["uploads"]); res[comp["developer"]] = {"channel": m, "videos": v, "summary": summarize(v)}
    print(f"· {comp['developer']:18} -> {m['title'][:22]:22} subs {m['subs']:>9,} | {summarize(v)}", flush=True)
    time.sleep(0.3)

save("yt.json", res)
