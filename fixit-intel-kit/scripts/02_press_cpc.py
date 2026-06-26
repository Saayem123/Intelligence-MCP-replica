#!/usr/bin/env python3
"""Press/news + LinkedIn + market trends (Serper) and keyword CPC (seodata).
   Outputs: out/press.json, out/trends.json, out/cpc.json
   seodata rate-limits hard on the anonymous tier — the loop retries; partial results are normal.
   The most load-bearing CPC is usually the DISTRICT/area term (high volume, low competition) — make sure it lands."""
import json, time, urllib.request, urllib.parse
from lib import cfg, env, save, OUT
C = cfg(); SK = env("SERPER_API_KEY")
SD = env("SEODATA_API_KEY", required=False)   # optional — register free at seodata.dev
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
import urllib.error
for k in C["cpc_keywords"]:
    enc = urllib.parse.quote(k); row = None
    # seodata rate-limits in bursts: back off exponentially and honor Retry-After on 429,
    # otherwise we drop keywords that actually have data. 5 tries, 2→4→8→16s.
    for attempt in range(5):
        try:
            hdrs = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            if SD:
                hdrs["X-API-Key"] = SD
            req_cpc = urllib.request.Request(
                f"https://app.seodata.dev/v1/keyword?q={enc}&country={CC}", headers=hdrs)
            with urllib.request.urlopen(req_cpc, timeout=25) as r:
                d = json.loads(r.read())
            if "volume" in d:
                row = d; print(f"{d.get('keyword','?')[:34]:34}{d.get('volume',0):>9}{str(d.get('cpc',0)):>7}{str(d.get('competition',0)):>6}"); break
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"  ! seodata 403 — check SEODATA_API_KEY in .env"); break
            if e.code == 429:                       # rate limited — wait the server-advised time
                wait = int(e.headers.get("Retry-After") or 0) or (2 ** (attempt + 1))
                time.sleep(min(wait, 20)); continue
        except Exception: pass
        time.sleep(2 ** (attempt + 1))              # 2,4,8,16s exponential backoff
    if row is None:
        print(f"  ! {k[:34]:34} seodata-unavailable (rate-limited after retries)")
    cpc.append(row or {"keyword": k, "volume": None, "note": "seodata-unavailable"})
    time.sleep(1.2)                                 # gentler spacing between keywords
save("cpc.json", cpc)
