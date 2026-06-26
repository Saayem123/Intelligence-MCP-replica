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
warnings = []   # non-fatal blockers (e.g. low credit) surfaced in the summary

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

# --- Apify (key validity + REMAINING CREDIT — this is the paid one that runs out) ---
print("\n[ Apify ]")
try:
    token  = env("APIFY_TOKEN")
    token2 = os.getenv("APIFY_TOKEN2")
    d = get(f"https://api.apify.com/v2/users/me?token={token}")
    u = d.get("data", {})
    print(f"  {PASS} Token valid — user: {u.get('username','?')} | plan: {u.get('plan',{}).get('id','?')}")
    # remaining monthly credit — a full ~7-target run at cap 30 costs ≈ $0.90
    lim = get(f"https://api.apify.com/v2/users/me/limits?token={token}").get("data", {})
    used = lim.get("current", {}).get("monthlyUsageUsd")
    cap  = lim.get("limits", {}).get("maxMonthlyUsageUsd")
    if used is not None and cap is not None:
        left = cap - used
        mark = PASS if left >= 1.0 else WARN
        print(f"  {mark} Credit: ${used:.2f} used of ${cap:.2f} → ${left:.2f} left "
              f"({'enough for a full run' if left >= 1.0 else 'LOW — a full run (~$0.90) may not finish'})")
        if left < 1.0:
            warnings.append(f"Apify credit low (${left:.2f} left) — top up or use a fresh token before 03_apify.py")
    if token2 and token2 == token:
        print(f"  {WARN} APIFY_TOKEN2 == APIFY_TOKEN — no real backup; the verification re-pull shares the same budget")
    elif not token2:
        print(f"  {WARN} APIFY_TOKEN2 not set — no backup token for the verification re-pull")
    results["apify"] = True
except Exception as e:
    print(f"  {FAIL} {e}")
    results["apify"] = False

# --- seodata (API key) ---
print("\n[ seodata.dev — keyword CPC ]")
try:
    import urllib.error
    sd_key = os.getenv("SEODATA_API_KEY", "")
    hdrs = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    if sd_key:
        hdrs["X-API-Key"] = sd_key
    req_sd = urllib.request.Request(
        "https://app.seodata.dev/v1/keyword?q=dubai+real+estate&country=ae", headers=hdrs)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req_sd, timeout=10, context=ctx) as r:
        d = json.loads(r.read())
    if d.get("volume") is not None:
        print(f"  {PASS} Key valid — volume: {d['volume']}, CPC: ${d.get('cpc','?')}")
    else:
        print(f"  {WARN} Reachable but no data returned")
    results["seodata"] = True
except urllib.error.HTTPError as e:
    if e.code == 403:
        print(f"  {FAIL} 403 — SEODATA_API_KEY missing or invalid in .env")
    else:
        print(f"  {FAIL} HTTP {e.code}")
    results["seodata"] = False
except Exception as e:
    print(f"  {FAIL} {e}")
    results["seodata"] = False

# --- Summary ---
print("\n─────────────────────────────────")
ok     = sum(1 for v in results.values() if v is True)
failed = [k for k, v in results.items() if v is False]
total  = len(results)
print(f"  {ok}/{total} APIs working")
for w in warnings:
    print(f"  {WARN} {w}")
if failed:
    print(f"  {FAIL} Fix these before running: {', '.join(failed)}\n")
elif warnings:
    print(f"  {WARN} Keys all valid, but resolve the warning(s) above before a full run\n")
else:
    print(f"  {PASS} All good — ready to run the full pipeline\n")
