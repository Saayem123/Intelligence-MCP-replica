#!/usr/bin/env python3
"""Build the Explorer array (out/ex_array.js) — every real, source-LINKED row behind the dashboard.
   Pulls from own IG/FB posts, IG comments, press, competitor YouTube (with watch URLs), and Ad-Library links.
   This is what makes the dashboard fact-checkable: each row carries a clickable url + date.
   The renderEx() in the template must wrap r.txt in <a href="${r.url}"> — see README step 6."""
import re, time, json, urllib.parse, urllib.request
from lib import cfg, env, load, OUT
C = cfg(); K = env("YOUTUBE_API_KEY")

def yt(path, **p):
    p["key"] = K
    try:
        with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?"+urllib.parse.urlencode(p), timeout=25) as r:
            return json.loads(r.read())
    except Exception: return {}

def esc(s): return (s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()
NEG = ["delay","refund","worst","scam","fraud","cost issue","supply chain","complaint"]
SKIP = ["salon","nursery","meat","dental","premium name is for sale","cleaning"]
def sent(t, default="pos"):
    t = (t or "").lower()
    return "neg" if any(k in t for k in NEG) else default

own = load("own_brand.json"); press = load("press.json")
try: cm = load("own_comments.json")
except Exception: cm = {"instagram": []}
rows = []

for p in own.get("instagram", []):
    c = esc(p["caption"]); likes = max(p.get("likes", 0), 0)
    rows.append(("you", f"{C['developer']} IG", "Instagram", "org", p["url"], "", c[:90] or "[image post]", "Brand", f"{likes} likes", sent(c)))
for p in own.get("facebook", []):
    t = esc(p["text"]); likes = max(p.get("likes", 0), 0)
    rows.append(("you", f"{C['developer']} FB", "Facebook", "org", p["url"], "", t[:90] or "[post]", "Brand", f"{likes} likes", sent(t)))
seen = set()
for c in cm.get("instagram", []):
    t = esc(c["text"]); cl = re.sub(r'[^a-zA-Z ]', '', t)
    if len(cl) < 8 or t in seen or any(s in t.lower() for s in SKIP): continue
    seen.add(t); rows.append(("you", "IG comment", "Comments", "men", C["own"]["instagram_url"], "", t[:90], "Audience", "comment", sent(t)))
    if sum(1 for r in rows if r[2] == "Comments") >= 6: break
for brand, arr in press.items():
    who = "you" if (C["client"].split()[0].lower() in brand.lower() or C["developer"].lower() in brand.lower()) else "rival"
    st = set()
    for a in arr:
        ti = esc(a.get("title", ""))
        if not a.get("link") or not ti or ti[:40].lower() in st: continue
        st.add(ti[:40].lower())
        rows.append((who, esc(a.get("source") or brand.split()[0]), "News", "men", a["link"], esc(a.get("date", "")), ti[:90],
                     "District" if who == "you" else "Market", "article", sent(ti, "neu" if who == "rival" else "pos")))

def adlib(q):
    return f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={C['country']}&q=" + urllib.parse.quote(q)
rows.append(("you", C["client"].split()[0], "Meta Ads", "ad", adlib(C["meta_self_term"]), "live", "Your active Meta ads (verify live)", "Ad placement", "Ad Library", "neu"))
for comp in C["competitors"][:4]:
    rows.append(("rival", comp["name"].split()[0], "Meta Ads", "ad", adlib(comp["meta_term"]), "live", f"{comp['name']} ads (verify live)", "Ad placement", "Ad Library", "neu"))

# competitor YouTube with watch URLs
seen_q = set()
yt_targets = [("you", C["own"].get("youtube_channel_id"), C["developer"])] + [("rival", None, comp["yt_query"]) for comp in C["competitors"]]
for who, cid, q in yt_targets:
    if q in seen_q: continue
    seen_q.add(q)
    if not cid:
        # pick the highest-subscriber candidate, not the first look-alike (see 01_youtube.find_channel)
        cands = [i.get("snippet", {}).get("channelId") for i in yt("search", part="snippet", q=q, type="channel", maxResults=5).get("items", [])]
        cands = [c for c in cands if c]
        best, best_subs = None, -1
        for c in cands:
            its = yt("channels", part="statistics", id=c).get("items", [])
            subs = int(its[0]["statistics"].get("subscriberCount", 0)) if its else 0
            if subs > best_subs: best, best_subs = c, subs
        cid = best
    if not cid: continue
    up = yt("channels", part="contentDetails", id=cid).get("items", [{}])[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not up: continue
    ids = [i["contentDetails"]["videoId"] for i in yt("playlistItems", part="contentDetails", playlistId=up, maxResults=15).get("items", [])]
    for it in (yt("videos", part="snippet,statistics", id=",".join(ids)).get("items", []) if ids else []):
        v = int(it.get("statistics", {}).get("viewCount", 0))
        rows.append((who, esc(q.split()[0]), "YouTube", "org", f"https://www.youtube.com/watch?v={it['id']}",
                     it["snippet"]["publishedAt"][:10], esc(it["snippet"]["title"])[:90], "Video", f"{v:,} views", "pos" if who == "you" else "neu"))
    time.sleep(0.2)

js = "const EX=[" + "".join(
    '\n  {who:"%s",src:"%s",pl:"%s",type:"%s",url:"%s",date:"%s",txt:"%s",theme:"%s",eng:"%s",s:"%s"},' % r for r in rows) + "\n];"
(OUT / "ex_array.js").write_text(js, encoding="utf-8")
print(f"wrote out/ex_array.js — {len(rows)} source-linked rows")
