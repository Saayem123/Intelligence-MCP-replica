"""
Run this locally to verify all API keys in .env are working.
Usage: python scripts/test_apis.py
"""
import sys, os, json, ssl, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
from lib import env

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
WARN = "\033[33m⚠\033[0m"

def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return json.loads(r.read())

def post(url, body, headers):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return json.loads(r.read())

results = {}

# --- YouTube ---
print("\n[ YouTube Data API v3 ]")
try:
    key = env("YOUTUBE_API_KEY")
    d = get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=emaar+dubai&type=channel&maxResults=1&key={key}")
    ch = d["items"][0]["snippet"]["channelTitle"] if d.get("items") else "no results"
    print(f"  {PASS} Key valid — sample channel: {ch}")
    results["youtube"] = True
except Exception as e:
    print(f"  {FAIL} {e}")
    results["youtube"] = False

# --- Serper ---
print("\n[ Serper.dev — Google News/Search ]")
try:
    key = env("SERPER_API_KEY")
    d = post("https://google.serper.dev/news", {"q": "Dubai real estate 2026", "gl": "ae", "num": 3}, {"X-API-KEY": key})
    count = len(d.get("news", []))
    print(f"  {PASS} Key valid — returned {count} news articles")
    results["serper"] = True
except Exception as e:
    print(f"  {FAIL} {e}")
    results["serper"] = False

# --- Apify ---
print("\n[ Apify ]")
try:
    token = env("APIFY_TOKEN")
    d = get(f"https://api.apify.com/v2/users/me?token={token}")
    u = d.get("data", {})
    print(f"  {PASS} Token valid — user: {u.get('username','?')} | plan: {u.get('plan',{}).get('id','?')}")
    results["apify"] = True
except Exception as e:
    print(f"  {FAIL} {e}")
    results["apify"] = False

# --- seodata (anonymous, no key) ---
print("\n[ seodata.dev — keyword CPC (anonymous) ]")
try:
    import urllib.error
    req_sd = urllib.request.Request(
        "https://app.seodata.dev/v1/keyword?q=dubai+real+estate&country=ae",
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req_sd, timeout=10, context=ctx) as r:
        d = json.loads(r.read())
    if d.get("volume") is not None:
        print(f"  {PASS} Reachable — volume: {d['volume']}, CPC: {d.get('cpc','?')}")
    else:
        print(f"  {WARN} Reachable but rate-limited — register at seodata.dev for 500/mo free quota")
    results["seodata"] = True
except urllib.error.HTTPError as e:
    if e.code == 403:
        print(f"  {WARN} 403 — anonymous tier is now blocked. Register free at https://app.seodata.dev to get 500 queries/mo")
        print(f"         CPC data will show 'unavailable' in the dashboard but all other scripts still run fine.")
    else:
        print(f"  {FAIL} HTTP {e.code}")
    results["seodata"] = "warn"
except Exception as e:
    print(f"  {FAIL} {e}")
    results["seodata"] = False

# --- Summary ---
print("\n─────────────────────────────────")
hard_ok = sum(1 for v in results.values() if v is True)
warned  = sum(1 for v in results.values() if v == "warn")
failed  = [k for k, v in results.items() if v is False]
total   = len(results)
print(f"  {hard_ok}/{total} APIs fully working  |  {warned} warning(s)")
if not failed:
    print(f"  {PASS} Ready to run the full pipeline (seodata CPC optional)\n")
else:
    print(f"  {FAIL} Fix these before running scripts: {', '.join(failed)}\n")
