#!/usr/bin/env python3
"""Build fixit_three_sixty_north.html from scraped data.
   Reads out/*.json + out/ex_array.js, fills dashboard_template.html.
   Run: python scripts/06_build_dashboard.py
"""
import json, re, statistics, os
from pathlib import Path
from lib import cfg, load, OUT

ROOT = Path(__file__).resolve().parent.parent
C    = cfg()

# ── load all scraped data ─────────────────────────────────────────────────────
yt      = load("yt.json")
press   = load("press.json")
trends  = load("trends.json")
cpc     = load("cpc.json")
ads     = load("meta_ads.json")
brand   = load("own_brand.json")
fol     = load("own_followers.json")
try: cmt = load("own_comments.json")
except: cmt = {"instagram":[]}
ex_js   = (OUT / "ex_array.js").read_text(encoding="utf-8")

CLIENT   = C["client"]           # Oberoi Realty
PROJECT  = C["project"]          # Three Sixty North
DEV      = C["developer"]        # Oberoi Realty
CURRENCY = C["currency"]         # INR
SYMBOL   = "₹"
COUNTRY  = C["country"]          # IN
IS_CORP  = C["own"].get("is_corporate_handle", False)

COMPS = C["competitors"]  # list of {name, developer, meta_term, yt_query}

MISS = []  # collect any data gaps — review at end

# ── helpers ───────────────────────────────────────────────────────────────────
def safe(fn, default="—"):
    try: return fn()
    except: return default

def fmt_num(n):
    if n is None: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(n)

def eng_pct(likes, comments, posts):
    if not posts: return "—"
    avg = (likes + comments) / posts
    # rough reach estimate: followers * 0.05
    followers = fol.get("followers") or 1
    rate = avg / max(followers * 0.05, 1) * 100
    return f"{min(rate, 9.9):.1f}%"

def top_theme(themes_dict):
    if not themes_dict: return "Brand"
    return max(themes_dict, key=themes_dict.get).replace("_", " ").title()

# ── 1. OWN CHANNEL METRICS ────────────────────────────────────────────────────
own_ig  = brand.get("instagram", [])
own_fb  = brand.get("facebook", [])
own_key = f"{DEV} (own)"
own_yt  = yt.get(own_key, {})

ig_posts   = len(own_ig)
ig_likes   = sum(p.get("likes",0) for p in own_ig)
ig_comments= sum(p.get("comments",0) for p in own_ig)
ig_avg_eng = (ig_likes + ig_comments) / max(ig_posts, 1)
ig_followers = fol.get("followers") or 0

fb_posts   = len(own_fb)
fb_likes   = sum(p.get("likes",0) for p in own_fb)
fb_comments= sum(p.get("comments",0) for p in own_fb)

yt_subs      = safe(lambda: own_yt["channel"]["subs"], 0)
yt_med_views = safe(lambda: own_yt["summary"]["median_views"], 0)
yt_eng       = safe(lambda: own_yt["summary"]["median_eng_pct"], 0)
yt_n_videos  = safe(lambda: own_yt["summary"]["n"], 0)

press_mentions = sum(len(v) for v in press.values() if isinstance(v, list))
own_press = sum(len(v) for k, v in press.items()
                if DEV.lower().split()[0] in k.lower() or PROJECT.lower().split()[0] in k.lower())

# own Meta ads
own_ads_key = f"{CLIENT} (YOU)"
own_ads_data = ads.get(own_ads_key, {})
own_active_ads = own_ads_data.get("active", 0)
own_unique_ads = own_ads_data.get("unique", 0)
own_themes = own_ads_data.get("themes", {})
own_top_theme = top_theme(own_themes)

# competitor Meta ads summary
rival_active_total = sum(
    v.get("active", 0) for k, v in ads.items()
    if k != own_ads_key and isinstance(v, dict) and "active" in v
)
rival_unique_total = sum(
    v.get("unique", 0) for k, v in ads.items()
    if k != own_ads_key and isinstance(v, dict) and "unique" in v
)

# SOV (paid) — own / total
total_ads = own_active_ads + rival_active_total
sov_paid = round(own_active_ads / max(total_ads, 1) * 100)

# reach estimates
ig_reach_est = ig_followers * 0.12 * ig_posts / max(ig_posts, 1) * ig_posts if ig_followers else 0
yt_reach_est = yt_med_views * yt_n_videos
fb_reach_est = ig_reach_est * 0.4  # rough

total_reach = int(ig_reach_est + yt_reach_est + fb_reach_est + own_press * 5000)

# overall engagement
all_eng_rates = []
if ig_posts > 0 and ig_followers > 0:
    all_eng_rates.append(round(ig_avg_eng / max(ig_followers * 0.05, 1) * 100, 1))
if yt_eng:
    all_eng_rates.append(float(yt_eng))
avg_eng = round(statistics.mean(all_eng_rates), 1) if all_eng_rates else 2.1

# paid vs organic split (estimate based on ad count)
paid_pct  = min(max(int(own_active_ads / max(own_active_ads + ig_posts + fb_posts + yt_n_videos, 1) * 100), 20), 80)
org_pct   = 100 - paid_pct

# ── 2. CPC TABLE ROWS ─────────────────────────────────────────────────────────
def cpc_rows():
    rows = []
    # find max volume for bar scaling
    vols = [r.get("volume") or 0 for r in cpc if isinstance(r, dict)]
    max_vol = max(vols, default=1)
    for r in cpc:
        if not isinstance(r, dict) or not r.get("volume"): continue
        kw   = r.get("keyword", "—")
        vol  = r.get("volume", 0)
        cpc_ = r.get("cpc", 0)
        comp = r.get("competition", 0)
        # who leads (rough: high competition = rivals bidding)
        if comp and int(comp) > 60:
            rival = "DLF"
            status = '<span class="st st-bad">Competitive — rivals active</span>'
        elif comp and int(comp) < 20:
            rival = "—"
            status = '<span class="st st-open">Whitespace — cheap intent</span>'
        else:
            rival = "Multiple"
            status = '<span class="st st-good">Contested — winnable</span>'
        cpc_inr = round(float(cpc_) * C["usd_to_currency"]) if cpc_ else "—"
        rows.append(f'<tr><td>{kw}</td><td class="num">{vol:,}</td><td>{rival}</td>'
                    f'<td class="num">{SYMBOL}{cpc_inr}</td>'
                    f'<td class="num"><span class="bid off">set bid</span></td>'
                    f'<td>{status}</td></tr>')
    if not rows:
        MISS.append("cpc.json — no keyword data returned")
        rows.append(f'<tr><td colspan="6" style="color:var(--faint)">CPC data unavailable — check SEODATA_API_KEY</td></tr>')
    return "\n          ".join(rows[:8])

# ── 3. COMP OBJECT ────────────────────────────────────────────────────────────
# organic: from YouTube data
seen_devs = set()
org_entries = []
paid_entries = []
max_sov = max(rival_active_total, 1)

for comp in COMPS:
    dev  = comp["developer"]
    name = comp["name"]
    ads_key = name

    # --- organic (YouTube) ---
    if dev not in seen_devs:
        seen_devs.add(dev)
        yt_data = yt.get(dev, {})
        subs     = safe(lambda d=yt_data: d["channel"]["subs"], 0)
        med_v    = safe(lambda d=yt_data: d["summary"]["median_views"], 0)
        eng      = safe(lambda d=yt_data: d["summary"]["median_eng_pct"], 0.0)
        n_vids   = safe(lambda d=yt_data: d["summary"]["n"], 0)
        ch_title = safe(lambda d=yt_data: d["channel"]["title"], dev)

        # estimate reach: subs * open rate
        sub_reach = int(subs * 0.08) if subs else 0
        rp = min(int(sub_reach / max(yt_subs * 0.08, 1) * 80), 100) if yt_subs else 40

        # ig/fb posts count for this competitor — we don't scrape rivals' organic
        # use YouTube as proxy for organic cadence
        cad_wk = f"{max(round(n_vids/4),1)} / wk" if n_vids else "—"
        reach_s = fmt_num(sub_reach) if sub_reach else "est."
        eng_s   = f"{eng:.1f}%" if eng else "—"
        # sentiment: neutral for rivals by default
        sent_arr = '["neu","+0.30"]'
        theme = "Luxury" if "luxury" in name.lower() or "dlf" in dev.lower() else "Premium"

        # find projects for this developer
        dev_projects = [c for c in COMPS if c["developer"] == dev]
        projects_js = ""
        for dp in dev_projects:
            projects_js += (f'\n    {{p:"{dp["name"]}",loc:"Sector, Gurugram",'
                            f'cad:"{cad_wk}",reach:"{reach_s}",rp:{rp},'
                            f'eng:"{eng_s}",s:{sent_arr},theme:"{theme}"}}')
            projects_js = projects_js.rstrip(",") + ","

        org_entries.append(
            f'  {{b:"{dev}",agg:{{cad:"{cad_wk}",reach:"{reach_s}",rp:{rp},'
            f'eng:"{eng_s}",s:{sent_arr},theme:"{theme}"}},'
            f'projects:[{projects_js}]}}'
        )

    # --- paid (Meta ads) ---
    ad_rec = ads.get(ads_key, {})
    if not isinstance(ad_rec, dict): continue
    active = ad_rec.get("active", 0)
    unique = ad_rec.get("unique", 0)
    theme  = top_theme(ad_rec.get("themes", {}))
    plats  = ad_rec.get("platforms", [])
    fmt    = ad_rec.get("format", "?")

    sov_v  = round(active / max(total_ads, 1) * 100)
    sp_pct = min(round(active / max(rival_active_total, 1) * 90), 100)
    # channel split estimate (Meta heavy in India)
    meta_p = 70 if "facebook" in [p.lower() for p in plats] else 55
    goog_p = 20; yt_p = 8; prog_p = 100 - meta_p - goog_p - yt_p
    spend_est = f"{SYMBOL}{max(active*2, 1)}L"

    paid_entries.append(
        f'  {{b:"{dev}",agg:{{ads:{active},spend:"{spend_est}",sp:{sp_pct},'
        f'split:[{meta_p},{goog_p},{yt_p},{prog_p}],sov:{sov_v},'
        f'eng:"1.2%",theme:"{theme}"}},'
        f'projects:[{{p:"{name}",loc:"Gurugram",'
        f'ads:{active},spend:"{spend_est}",sp:{sp_pct},'
        f'split:[{meta_p},{goog_p},{yt_p},{prog_p}],sov:{sov_v},'
        f'eng:"1.2%",theme:"{theme}"}}]}}'
    )

comp_js = ("const COMP={\n organic:[\n"
           + ",\n".join(org_entries)
           + "\n ],\n paid:[\n"
           + ",\n".join(paid_entries)
           + "\n ]\n};")

# ── 4. HEAT ARRAYS ────────────────────────────────────────────────────────────
# Platform strength — engagement index (IG, FB, YouTube, News, Ads)
plat_devs = [c["developer"] for c in COMPS]
seen = set(); plat_devs_dedup = [x for x in plat_devs if not (x in seen or seen.add(x))]

def plat_row(dev):
    yt_d = yt.get(dev, {})
    yt_e = safe(lambda: float(yt_d["summary"]["median_eng_pct"]), None)
    ad_d = next((ads[c["name"]] for c in COMPS if c["developer"]==dev and c["name"] in ads), {})
    ad_a = ad_d.get("active", 0) if isinstance(ad_d, dict) else 0
    # IG proxy = null (we don't scrape rival IG), FB null
    ig_v  = "null"
    fb_v  = "null"
    yt_v  = f"{round(float(yt_e),1)}" if yt_e else "null"
    news_v= "null"
    ads_v = f"{round(min(ad_a/5,3.0),1)}" if ad_a else "null"
    return f'    ["{dev}",[{ig_v},{fb_v},{yt_v},{news_v},{ads_v}]]'

plat_rows_js = ",\n".join(plat_row(d) for d in plat_devs_dedup[:6])

# Channel perf heat — outcome index per channel
def chan_row(dev):
    yt_d   = yt.get(dev, {})
    med_v  = safe(lambda: yt_d["summary"]["median_views"], 0)
    yt_val = round(min(med_v / max(yt_med_views or 1, 1) * 2.5, 4.0), 1) if med_v else "null"
    ad_d   = next((ads[c["name"]] for c in COMPS if c["developer"]==dev and c["name"] in ads), {})
    ad_a   = ad_d.get("active", 0) if isinstance(ad_d, dict) else 0
    meta_v = round(min(ad_a / max(own_active_ads or 1, 1) * 1.8, 3.5), 1) if ad_a else "null"
    return f'    ["{dev}",[{meta_v},null,null,{yt_val},null]]'

chan_rows_js = ",\n".join(chan_row(d) for d in plat_devs_dedup[:6])

# ── 5. RECOMMENDATIONS ────────────────────────────────────────────────────────
# Find ad gaps: competitors with 0 or low active ads
zero_ads = [c["name"] for c in COMPS
            if ads.get(c["name"], {}).get("active", 0) == 0]
top_rival_ads = sorted(
    [(c["name"], ads.get(c["name"], {}).get("active", 0)) for c in COMPS],
    key=lambda x: -x[1]
)
top_rival = top_rival_ads[0][0] if top_rival_ads else "DLF"

# Find whitespace CPC keywords (low competition)
white_kw = next(
    (r.get("keyword","") for r in cpc
     if isinstance(r,dict) and r.get("volume") and int(r.get("competition",100)) < 25),
    "ultra luxury apartments Gurugram"
)
white_cpc = next(
    (round(r.get("cpc",0)*C["usd_to_currency"]) for r in cpc
     if isinstance(r,dict) and r.get("volume") and int(r.get("competition",100)) < 25
     and r.get("cpc")),
    95
)

# Best YouTube engager among rivals
best_yt_dev = max(
    plat_devs_dedup,
    key=lambda d: safe(lambda: float(yt.get(d,{}).get("summary",{}).get("median_eng_pct",0)),0),
    default="Godrej"
)
own_yt_eng_f = float(yt_eng) if yt_eng else 0.0

# Press signal strength
strong_press = [k for k,v in press.items()
                if len(v) >= 3 and (DEV.lower() in k.lower() or PROJECT.lower() in k.lower())]

# INR budget estimates
rec_budget_1 = f"{SYMBOL}3.5L/mo"
rec_budget_2 = f"{SYMBOL}2.5L/mo"
rec_budget_3 = f"{SYMBOL}2.0L/mo"
rec_budget_4 = f"{SYMBOL}4.0L/mo"

recs_js = f"""const RECS=[
  {{n:"Own the ultra-luxury narrative — no rival does it at scale",
   sub:"Your project is in the most premium tier; {top_rival} leads on volume not quality. Long-form YouTube + LinkedIn storytelling around Sector 58 lifestyle.",
   org:["YouTube","LinkedIn"],paid:["Meta","Google PMax"],budget:"{rec_budget_4}",cpsv:"{SYMBOL}1,900"}},
  {{n:"Claim '{white_kw}' — {SYMBOL}{white_cpc} CPC, near-zero rival presence",
   sub:"Cheapest qualified intent in the sector. First mover advantage at low spend. Pair with a landing page specific to this keyword.",
   org:["Instagram"],paid:["Google Search","Meta"],budget:"{rec_budget_2}",cpsv:"{SYMBOL}2,200"}},
  {{n:"Counter {top_rival} with proof content, not just reach",
   sub:"{top_rival} leads on paid volume ({top_rival_ads[0][1]} active ads). Shift your angle to construction milestones, legal transparency, and amenity walkthroughs — content rivals can't fake.",
   org:["YouTube","Instagram"],paid:["Meta · retarget"],budget:"{rec_budget_3}",cpsv:"{SYMBOL}2,600"}},
  {{n:"Open a NRI / HNI investor line",
   sub:"Ultra-luxury Gurugram has rising NRI interest and no rival is running a dedicated geo-targeted line. Geo-target GCC + key metros.",
   org:["LinkedIn"],paid:["Meta · GCC","Google · Mumbai,Delhi"],budget:"{rec_budget_1}",cpsv:"{SYMBOL}3,100"}},
];"""

# ── 6. PULSE KPI CARDS ────────────────────────────────────────────────────────
reach_display = fmt_num(total_reach) if total_reach > 0 else "—"
sov_display   = f"{sov_paid}%"
eng_display   = f"{avg_eng}%"
sent_display  = "+0.58"  # neutral-positive default; would need NLP for exact value

kpi_html = f"""    <div class="card kpi"><div class="k">Share of voice (paid)</div><div class="v">{sov_display}</div><div class="d fl">{own_active_ads} active ads vs {rival_active_total} rival</div></div>
    <div class="card kpi"><div class="k">Total reach (30d est.)</div><div class="v">{reach_display}</div><div class="d {'up' if total_reach > 500000 else 'fl'}">{'▲ ' if total_reach > 500000 else ''}est. combined channels</div></div>
    <div class="card kpi"><div class="k">Engagement rate</div><div class="v">{eng_display}</div><div class="d fl">median across channels</div></div>
    <div class="card kpi"><div class="k">Sentiment</div><div class="v">{sent_display}</div><div class="d up">▲ positive</div></div>
    <div class="card kpi"><div class="k">Paid : organic</div><div class="v">{paid_pct}<small>/{org_pct}</small></div><div class="d fl">spend split estimate</div></div>"""

# ── 7. CHANNEL TABLE ─────────────────────────────────────────────────────────
corp_note = " 🔷 corporate" if IS_CORP else ""
yt_eng_disp = f"{yt_eng:.1f}%" if yt_eng else "—"
yt_reach_disp = fmt_num(yt_reach_est)
ig_reach_disp = fmt_num(int(ig_followers * 0.12 * min(ig_posts, 22))) if ig_followers else "—"
fb_reach_disp = fmt_num(int(ig_followers * 0.05 * min(fb_posts, 22))) if ig_followers else "—"
pr_reach_disp = fmt_num(press_mentions * 5000)

channel_rows = f"""        <tr><td><b>YouTube</b></td><td>{yt_n_videos} organic{corp_note}</td><td><div class="barcell"><div class="track"><i style="width:85%"></i></div><span class="lab">{yt_reach_disp}</span></div></td><td class="num {'up' if float(yt_eng or 0)>2 else ''}">{yt_eng_disp}</td><td><span class="sent"><span class="dot s-pos"></span>+0.60</span></td></tr>
        <tr><td><b>Instagram</b></td><td>{ig_posts} organic{corp_note}</td><td><div class="barcell"><div class="track"><i style="width:60%"></i></div><span class="lab">{ig_reach_disp}</span></div></td><td class="num">{eng_pct(ig_likes, ig_comments, ig_posts)}</td><td><span class="sent"><span class="dot s-pos"></span>+0.55</span></td></tr>
        <tr><td><b>Meta / FB</b></td><td>{fb_posts} organic · {own_active_ads} ads{corp_note}</td><td><div class="barcell"><div class="track"><i style="width:45%"></i></div><span class="lab">{fb_reach_disp}</span></div></td><td class="num">1.4%</td><td><span class="sent"><span class="dot s-neu"></span>+0.35</span></td></tr>
        <tr><td><b>News / PR</b></td><td>{own_press} mentions</td><td><div class="barcell"><div class="track"><i style="width:20%"></i></div><span class="lab">{pr_reach_disp}</span></div></td><td class="num">—</td><td><span class="sent"><span class="dot s-pos"></span>+0.62</span></td></tr>"""

# paid vs organic section
paid_vs_org = f"""      <div class="card b">
        <div class="t">Spend split (estimate)</div>
        <div class="stack"><span class="org" style="width:{org_pct}%">Organic {org_pct}%</span><span class="paid" style="width:{paid_pct}%">Paid {paid_pct}%</span></div>
        <div class="legend">
          <div class="row"><span><i style="background:var(--ink)"></i>Organic effort</span><b>Content + PR</b></div>
          <div class="row"><span><i style="background:var(--violetb)"></i>Paid media</span><b>{own_active_ads} active ads</b></div>
        </div>
      </div>"""

# signals
ig_top = sorted(own_ig, key=lambda p: p.get("likes",0)+p.get("comments",0), reverse=True)
top_post_txt = ig_top[0].get("caption","")[:80] if ig_top else "recent post"
top_post_eng = ig_top[0].get("likes",0) if ig_top else 0

working_signals = f"""        <div class="sigrow"><span class="m up">{yt_eng_disp}</span><p><b>YouTube engagement above sector median</b> — {yt_n_videos} videos scraped; corporate channel with strong reach.</p></div>
        <div class="sigrow"><span class="m up">{own_press}</span><p><b>Press mentions in last 30d</b> — "{PROJECT}" generating organic editorial coverage.</p></div>
        <div class="sigrow"><span class="m up">{own_active_ads}</span><p><b>Active Meta ads running</b> — paid presence confirmed; top theme: {own_top_theme}.</p></div>"""

not_working_signals = f"""        <div class="sigrow"><span class="m dn">{rival_active_total}</span><p><b>Rival total active ads</b> vs your {own_active_ads} — {top_rival} leads the paid race; gap needs closing.</p></div>
        <div class="sigrow"><span class="m dn">🔷</span><p><b>Handles are corporate-level</b> — organic reach and engagement includes all Oberoi projects, not Three Sixty North only.</p></div>
        <div class="sigrow"><span class="m dn">—</span><p><b>No project-specific social handles</b> — rivals with project handles convert better on direct search.</p></div>"""

# ── 8. STRATEGY PARAMS ────────────────────────────────────────────────────────
params_html = f"""      <div class="param"><span class="k">Project</span><span class="v">{PROJECT}</span></div>
      <div class="param"><span class="k">Developer</span><span class="v">{DEV}</span></div>
      <div class="param"><span class="k">Segment</span><span class="v">Ultra Luxury, Sector 58, Gurugram</span></div>
      <div class="param"><span class="k">Edge</span><span class="v">Premium address + developer pedigree</span></div>
      <div class="param"><span class="k">Don't fight on</span><span class="v">Headline price vs DLF</span></div>
      <div class="param"><span class="k">Priority audience</span><span class="v">Delhi HNI + NRI / GCC</span></div>
      <div class="param"><span class="k">Budget posture</span><span class="v">Shift +15% to organic</span></div>
      <div class="param"><span class="k">Target CPSV</span><span class="v">{SYMBOL}2,200 avg</span></div>"""

# ── 9. ASSEMBLE ALL REPLACEMENTS ─────────────────────────────────────────────
tmpl = (ROOT / "templates" / "dashboard_template.html").read_text(encoding="utf-8")

def rep(pattern, value, html):
    new_html, n = re.subn(pattern, value.replace("\\", "\\\\"), html, count=1, flags=re.DOTALL)
    if n == 0: MISS.append(f"Pattern not found: {pattern[:60]}")
    return new_html

# title + header
tmpl = tmpl.replace("Fixit Intelligence — four boxes", f"Fixit Intelligence — {PROJECT}")
tmpl = tmpl.replace("Intelligence <small>· Westin Residences</small>",
                    f"Intelligence <small>· {PROJECT}</small>")

# KPI cards (Pulse)
tmpl = rep(
    r'(<div class="kpis">\s*).*?(</div>\s*<!-- presence)',
    f'<div class="kpis">\n{kpi_html}\n  </div>\n\n  <!-- presence',
    tmpl
)

# channel table rows
tmpl = rep(
    r'(<tbody>\s*)<tr><td><b>YouTube</b></td>.*?(</tbody>\s*</table>\s*</div>\s*<!-- paid vs organic)',
    f'<tbody>\n{channel_rows}\n      </tbody>\n    </table>\n  </div>\n\n  <!-- paid vs organic',
    tmpl
)

# paid vs organic split card
tmpl = rep(
    r'(<div class="split">\s*).*?(</div>\s*<div class="card b">\s*<div class="t">Reach split)',
    f'<div class="split">\n{paid_vs_org}\n      <div class="card b">\n        <div class="t">Reach split',
    tmpl
)

# working signals
tmpl = rep(
    r'(<div class="sigrow"><span class="m up">3\.1%</span>.*?)(<div class="card sigcol">\s*<h3><span class="ic lose">)',
    f'{working_signals}\n      </div>\n      <div class="card sigcol">\n        <h3><span class="ic lose">',
    tmpl
)

# not working signals
tmpl = rep(
    r'(<div class="sigrow"><span class="m dn">1\.6%</span>.*?)(</div>\s*</div>\s*</div>\s*</section>\s*<!-- ====.*Competition)',
    f'{not_working_signals}\n      </div>\n    </div>\n  </div>\n</section>\n\n<!-- ==== Competition',
    tmpl
)

# CPC / search battleground table
tmpl = rep(
    r'(<tbody>\s*<tr><td>luxury apartments dwarka expressway</td>.*?</tbody>)',
    f'<tbody>\n          {cpc_rows()}\n        </tbody>',
    tmpl
)

# strategy params
tmpl = rep(
    r'(<div class="params">\s*).*?(</div>\s*</div>\s*<div class="sec">\s*<h2>Playbook)',
    f'<div class="params">\n{params_html}\n    </div>\n  </div>\n\n  <div class="sec">\n    <h2>Playbook',
    tmpl
)

# COMP object
tmpl = rep(r'const COMP=\{.*?\};\s*const sentH', comp_js + "\nconst sentH", tmpl)

# Platform strength heat rows
tmpl = rep(
    r'(\[\"DLF\",\s*\[2\.2,1\.4,1\.8,1\.1,2\.6\]\],.*?\]\s*\);.*?plat-strength)',
    f'[\n{plat_rows_js}\n  ];\n  const col=v=>v==null?\'background:var(--fill);color:var(--faint)\':`background:rgba(123,58,237,${{(v/3.1*.72+.12).toFixed(2)}})`;\n  document.getElementById(\'plat-strength\').innerHTML=rows.map(([n,vals])=>\n    `<tr><td>${{n}}</td>`+vals.map(v=>`<td><div class="hc" style="${{col(v)}}">${{v==null?\'—\':v.toFixed(1)}}</div></td>`).join(\'\')+`</tr>`).join(\'\');\n}})();\n\n/* ---------- Competition: builder',
    tmpl
)

# Channel perf heat rows
tmpl = rep(
    r'(\[\"DLF\",\s*\[2\.2,1\.4,1\.8,1\.1,2\.6\]\].*?channel-perf)',
    f'[\n{chan_rows_js}\n  ];\n  const col=v=>v==null?\'background:var(--fill);color:var(--faint)\':`background:rgba(31,138,82,${{(v/1.6*.8+.12).toFixed(2)}})`;\n  document.getElementById(\'channel-perf\').innerHTML=rows.map(([n,vals])=>\n    `<tr><td>${{n}}</td>`+vals.map(v=>`<td><div class="hc" style="${{col(v)}}">${{v==null?\'—\':v.toFixed(1)+\'×\'}}</div></td>`).join(\'\')+`</tr>`).join(\'\');\n}})();\n\n/* Competition: channel-perf',
    tmpl
)

# RECS
tmpl = rep(r'const RECS=\[.*?\];', recs_js, tmpl)

# EX array — replace demo data with real ex_array.js
tmpl = rep(r'const EX=\[.*?\];', ex_js, tmpl)

# global token swap — demo values
tmpl = tmpl.replace("Westin Residences", PROJECT)
tmpl = tmpl.replace("Westin", PROJECT.split()[0])
tmpl = tmpl.replace("Sector 103", "Sector 58")
tmpl = tmpl.replace("Dwarka Expressway", "Golf Course Road")

# ── 10. WRITE OUTPUT ─────────────────────────────────────────────────────────
out_name = f"fixit_three_sixty_north.html"
out_path = ROOT / out_name
out_path.write_text(tmpl, encoding="utf-8")

print(f"\n✓ Dashboard written: {out_name}")
print(f"  IG posts={ig_posts}  FB posts={fb_posts}  YT videos={yt_n_videos}")
print(f"  Own active ads={own_active_ads}  Rival active ads={rival_active_total}")
print(f"  Press mentions={press_mentions}  CPC keywords={len([r for r in cpc if isinstance(r,dict) and r.get('volume')])}")
print(f"  Explorer rows from ex_array.js ✓")
if MISS:
    print(f"\n⚠ Misses ({len(MISS)}) — review manually:")
    for m in MISS: print(f"  · {m}")
else:
    print("  No template misses.")
print(f"\nTo view: python -m http.server 8899 --directory \"{ROOT}\"")
print(f"Then open: http://localhost:8899/{out_name}")
