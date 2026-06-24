#!/usr/bin/env python3
"""Press/news + LinkedIn + market trends (Serper) and keyword CPC (seodata).
   Outputs: out/press.json, out/trends.json, out/cpc.json
   seodata rate-limits hard on the anonymous tier — the loop retries; partial results are normal.
   The most load-bearing CPC is usually the DISTRICT/area term (high volume, low competition) — make sure it lands."""
import json, time, urllib.request, urllib.parse
from lib import cfg, env, save, OUT
C = cfg(); SK = env("SERPER_API_KEY")
GL = C["country"].lower()        # ae / in
CC = C["country"].lower()

def serper(ep, q, num=8):
    req = urllib.request.Request("https://google.serper.dev/"+ep,
        data=json.dumps({"q": q, "gl": GL, "hl": "en", "num": num}).encode(),
        headers={"X-API-KEY": SK, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r: return json.loads(r.read())
    except Exception as e:
        print(f"  ! {ep} {q[:24]}: {type(e).__name__}"); return {}

# --- press ---
news = {}
for b in C["press_brands"]:
    j = serper("news", b, 8); time.sleep(0.3)
    news[b] = [{"title": o.get("title",""), "link": o.get("link",""), "source": o.get("source",""),
                "snippet": o.get("snippet","")[:280], "date": o.get("date","")} for o in j.get("news", [])]
    print(f"news {b[:40]:40} {len(news[b])}", flush=True)
save("press.json", news)

# --- trends ---
trends = {}
for key, q in C.get("trend_queries", {}).items():
    j = serper("news", q, 6); time.sleep(0.3)
    trends[key] = [{"title": o.get("title",""), "source": o.get("source",""), "date": o.get("date",""),
                    "snippet": o.get("snippet","")[:220]} for o in j.get("news", [])]
    print(f"trend {key:14} {len(trends[key])}", flush=True)
save("trends.json", trends)

# --- CPC (seodata) ---
cpc = []
print(f"\nCPC (seodata country={CC}) — USD; multiply by {C['usd_to_currency']} for {C['currency']}", flush=True)
print(f"{'KEYWORD':34}{'VOL':>9}{'CPC$':>7}{'COMP':>6}")
for k in C["cpc_keywords"]:
    enc = urllib.parse.quote(k); row = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"https://app.seodata.dev/v1/keyword?q={enc}&country={CC}", timeout=25) as r:
                d = json.loads(r.read())
            if "volume" in d:
                row = d; print(f"{d.get('keyword','?')[:34]:34}{d.get('volume',0):>9}{str(d.get('cpc',0)):>7}{str(d.get('competition',0)):>6}"); break
        except Exception: pass
        time.sleep(1.5)
    cpc.append(row or {"keyword": k, "volume": None, "note": "rate-limited / no data"})
    time.sleep(0.6)
save("cpc.json", cpc)
