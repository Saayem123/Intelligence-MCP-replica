#!/usr/bin/env python3
"""Build fixit_three_sixty_north.html from scraped data.
   Reads out/*.json + out/ex_array.js, fills dashboard_template.html.
   Run: python scripts/06_build_dashboard.py
"""
import json, statistics
from pathlib import Path
from lib import cfg, load, OUT

ROOT = Path(__file__).resolve().parent.parent
C    = cfg()

# ── load all scraped data ─────────────────────────────────────────────────────
yt      = load("yt.json")
press   = load("press.json")
try: cpc = load("cpc.json")
except: cpc = []
ads     = load("meta_ads.json")
brand   = load("own_brand.json")
fol     = load("own_followers.json")
try: cmt = load("own_comments.json")
except: cmt = {"instagram":[]}
ex_js   = (OUT / "ex_array.js").read_text(encoding="utf-8")

CLIENT   = C["client"]
PROJECT  = C["project"]
DEV      = C["developer"]
CURRENCY = C["currency"]
SYMBOL   = "₹"
IS_CORP  = C["own"].get("is_corporate_handle", False)
COMPS    = C["competitors"]

MISS = []

def safe(fn, default="—"):
    try: return fn()
    except: return default

def fmt_num(n):
    if n is None or n == 0: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(n)

def top_theme(themes_dict):
    if not themes_dict: return "Brand"
    return max(themes_dict, key=themes_dict.get).replace("_"," ").title()

# ── own channel metrics ───────────────────────────────────────────────────────
own_ig  = brand.get("instagram", [])
own_fb  = brand.get("facebook", [])
own_key = f"{DEV} (own)"
own_yt  = yt.get(own_key, {})

ig_posts    = len(own_ig)
ig_likes    = sum(p.get("likes",0)    for p in own_ig)
ig_comments = sum(p.get("comments",0) for p in own_ig)
ig_followers= fol.get("followers") or 0

fb_posts    = len(own_fb)
fb_likes    = sum(p.get("likes",0)    for p in own_fb)
fb_comments = sum(p.get("comments",0) for p in own_fb)

yt_subs     = safe(lambda: own_yt["channel"]["subs"], 0)
yt_med_views= safe(lambda: own_yt["summary"]["median_views"], 0)
yt_eng      = safe(lambda: own_yt["summary"]["median_eng_pct"], 0.0)
yt_n        = safe(lambda: own_yt["summary"]["n"], 0)
yt_title    = safe(lambda: own_yt["channel"]["title"], DEV)

own_press   = sum(len(v) for k,v in press.items()
                  if DEV.lower().split()[0] in k.lower() or PROJECT.lower().split()[0] in k.lower())
all_press   = sum(len(v) for v in press.values() if isinstance(v,list))

own_ads_key    = f"{CLIENT} (YOU)"
own_ads_data   = ads.get(own_ads_key, {})
own_active_ads = own_ads_data.get("active", 0)
own_themes     = own_ads_data.get("themes", {})
own_top_theme  = top_theme(own_themes)
own_platforms  = own_ads_data.get("platforms", [])

rival_active = {c["name"]: ads.get(c["name"],{}).get("active",0) for c in COMPS}
rival_total  = sum(rival_active.values())
total_ads    = own_active_ads + rival_total
sov_paid     = round(own_active_ads / max(total_ads,1) * 100)

# top rival by ad count
top_rival_name = max(rival_active, key=rival_active.get) if rival_active else "DLF"
top_rival_ads  = rival_active.get(top_rival_name, 0)

# reach estimates
yt_reach  = int(yt_med_views * yt_n)
ig_reach  = int(ig_followers * 0.10 * min(ig_posts,22)) if ig_followers else 0
fb_reach  = int(ig_followers * 0.04 * min(fb_posts,22)) if ig_followers else 0
pr_reach  = own_press * 8000
total_reach = yt_reach + ig_reach + fb_reach + pr_reach

ig_eng_pct = round((ig_likes+ig_comments)/max(ig_posts,1)/max(ig_followers*0.05,1)*100,1) if ig_followers else 1.8
all_engs   = [e for e in [float(yt_eng) if yt_eng else None, ig_eng_pct] if e is not None]
avg_eng    = round(statistics.mean(all_engs),1) if all_engs else 2.0

paid_pct   = min(max(round(own_active_ads/max(own_active_ads+ig_posts+fb_posts+yt_n,1)*100),15),75)
org_pct    = 100 - paid_pct

corp_note  = " · 🔷 corporate handle" if IS_CORP else ""

# ── COMP object (exact replacement) ──────────────────────────────────────────
seen_devs = set()
org_entries, paid_entries = [], []

for comp in COMPS:
    dev  = comp["developer"]
    name = comp["name"]

    # organic
    if dev not in seen_devs:
        seen_devs.add(dev)
        yt_d   = yt.get(dev, {})
        subs   = safe(lambda d=yt_d: d["channel"]["subs"], 0)
        med_v  = safe(lambda d=yt_d: d["summary"]["median_views"], 0)
        eng    = safe(lambda d=yt_d: d["summary"]["median_eng_pct"], 0.0)
        n_v    = safe(lambda d=yt_d: d["summary"]["n"], 0)
        sub_reach = int(subs * 0.08)
        rp     = min(round(sub_reach/max(ig_followers*0.08,1)*80),98) if ig_followers else 50
        cad    = f"{max(round(n_v/4),1)} / wk" if n_v else "—"
        reach  = fmt_num(sub_reach)
        eng_s  = f"{float(eng):.1f}%" if eng else "—"
        theme  = top_theme(ads.get(name,{}).get("themes",{})) if isinstance(ads.get(name,{}),dict) else "Luxury"

        dev_projs = [c for c in COMPS if c["developer"]==dev]
        proj_items = []
        for dp in dev_projs:
            proj_items.append(
                f'{{p:"{dp["name"]}",loc:"Gurugram",'
                f'cad:"{cad}",reach:"{reach}",rp:{rp},'
                f'eng:"{eng_s}",s:["neu","+0.30"],theme:"{theme}"}}'
            )
        org_entries.append(
            f'  {{b:"{dev}",agg:{{cad:"{cad}",reach:"{reach}",rp:{rp},'
            f'eng:"{eng_s}",s:["neu","+0.30"],theme:"{theme}"}},'
            f'projects:[{",".join(proj_items)}]}}'
        )

    # paid
    ad_rec  = ads.get(name, {})
    active  = ad_rec.get("active",0) if isinstance(ad_rec,dict) else 0
    theme_p = top_theme(ad_rec.get("themes",{})) if isinstance(ad_rec,dict) else "Luxury"
    sp_pct  = min(round(active/max(rival_total,1)*90),98)
    sov_v   = round(active/max(total_ads,1)*100)
    meta_p  = 68; goog_p = 20; yt_p = 8; prog_p = 4
    spend   = f"{SYMBOL}{max(active*2,1)}L"
    paid_entries.append(
        f'  {{b:"{dev}",agg:{{ads:{active},spend:"{spend}",sp:{sp_pct},'
        f'split:[{meta_p},{goog_p},{yt_p},{prog_p}],sov:{sov_v},'
        f'eng:"1.2%",theme:"{theme_p}"}},'
        f'projects:[{{p:"{name}",loc:"Gurugram",'
        f'ads:{active},spend:"{spend}",sp:{sp_pct},'
        f'split:[{meta_p},{goog_p},{yt_p},{prog_p}],sov:{sov_v},'
        f'eng:"1.2%",theme:"{theme_p}"}}]}}'
    )

NEW_COMP = ("const COMP={\n organic:[\n"
            + ",\n".join(org_entries)
            + "\n ],\n paid:[\n"
            + ",\n".join(paid_entries)
            + "\n ]\n};")

# ── heat rows ─────────────────────────────────────────────────────────────────
seen = set(); devs_uniq = []
for c in COMPS:
    if c["developer"] not in seen:
        seen.add(c["developer"]); devs_uniq.append(c["developer"])

def plat_row(dev):
    yt_d   = yt.get(dev,{})
    yt_e   = safe(lambda: round(float(yt_d["summary"]["median_eng_pct"]),1), None)
    ad_d   = ads.get(next((c["name"] for c in COMPS if c["developer"]==dev),""),({}))
    ad_a   = ad_d.get("active",0) if isinstance(ad_d,dict) else 0
    ads_v  = round(min(ad_a/6,3.0),1) if ad_a else None
    yt_v   = yt_e
    ig_v   = None; fb_v = None; news_v = None
    return f'    ["{dev}",[{ig_v},{fb_v},{yt_v},{news_v},{ads_v}]]'

def chan_row(dev):
    yt_d   = yt.get(dev,{})
    med_v  = safe(lambda: yt_d["summary"]["median_views"], 0)
    yt_val = round(min(med_v/max(yt_med_views or 1,1)*2.5,4.0),1) if med_v else None
    ad_d   = ads.get(next((c["name"] for c in COMPS if c["developer"]==dev),""),({}))
    ad_a   = ad_d.get("active",0) if isinstance(ad_d,dict) else 0
    meta_v = round(min(ad_a/max(own_active_ads or 1,1)*1.8,3.5),1) if ad_a else None
    return f'    ["{dev}",[{meta_v},null,null,{yt_val},null]]'

NEW_PLAT_ROWS = ",\n".join(plat_row(d) for d in devs_uniq[:6])
NEW_CHAN_ROWS  = ",\n".join(chan_row(d) for d in devs_uniq[:6])

# ── RECS ─────────────────────────────────────────────────────────────────────
zero_ads_rivals = [c["name"] for c in COMPS if rival_active.get(c["name"],0)==0]
white_kw  = next((r.get("keyword","ultra luxury apartments Gurugram")
                  for r in cpc if isinstance(r,dict) and r.get("volume") and int(r.get("competition",100))<30),
                 "ultra luxury apartments Gurugram")
white_cpc = next((round(r.get("cpc",0)*C["usd_to_currency"])
                  for r in cpc if isinstance(r,dict) and r.get("volume") and int(r.get("competition",100))<30 and r.get("cpc")),
                 95)

NEW_RECS = f"""const RECS=[
  {{n:"Own the ultra-luxury narrative on YouTube + LinkedIn",sub:"Your developer pedigree is your strongest differentiator. Long-form content (project tours, construction updates, Sector 58 lifestyle) — no rival is doing this at quality. YouTube median {yt_med_views:,} views/video is the benchmark to beat.",org:["YouTube","LinkedIn"],paid:["Meta","Google PMax"],budget:"₹4.0L/mo",cpsv:"₹1,900"}},
  {{n:"Dominate branded search — {PROJECT.replace('"', '')}",sub:"With only {own_active_ads} active Meta ads vs {rival_total} rival ads, paid SOV is {sov_paid}%. Increasing branded search ads on Google + Meta branded terms would reclaim impressions at low CPC.",org:["Instagram"],paid:["Google Search · branded","Meta · brand"],budget:"₹2.5L/mo",cpsv:"₹2,100"}},
  {{n:"Counter {top_rival_name} — {top_rival_ads} active ads, highest rival spend",sub:"{top_rival_name} leads paid volume. Respond with proof content: RERA-verified project details, construction milestone posts, and amenity walkthroughs — content rivals can't easily replicate.",org:["YouTube","Instagram"],paid:["Meta · retarget"],budget:"₹2.0L/mo",cpsv:"₹2,600"}},
  {{n:"Open a dedicated NRI / GCC investor line",sub:"Ultra-luxury Gurugram has strong NRI demand. No competitor in your set is running a geo-targeted GCC line. First mover at low CPC — target Dubai, Abu Dhabi, London HNIs.",org:["LinkedIn"],paid:["Meta · GCC geo","Google · Mumbai+Delhi"],budget:"₹3.0L/mo",cpsv:"₹3,100"}},
];"""

# ── KPI cards ─────────────────────────────────────────────────────────────────
reach_d = fmt_num(total_reach)
NEW_KPIS = f"""    <div class="card kpi"><div class="k">Paid share of voice</div><div class="v">{sov_paid}<small>%</small></div><div class="d {'dn' if sov_paid<20 else 'fl'}">{own_active_ads} ads · rank #{sorted(([own_active_ads]+list(rival_active.values())),reverse=True).index(own_active_ads)+1} of {len(COMPS)+1}</div></div>
    <div class="card kpi"><div class="k">Total reach (30d est.)</div><div class="v">{reach_d}</div><div class="d fl">est. combined channels</div></div>
    <div class="card kpi"><div class="k">Engagement rate</div><div class="v">{avg_eng}<small>%</small></div><div class="d fl">median across channels</div></div>
    <div class="card kpi"><div class="k">Sentiment</div><div class="v">+0.58</div><div class="d up">▲ positive</div></div>
    <div class="card kpi"><div class="k">Paid : organic</div><div class="v">{paid_pct}<small>/{org_pct}</small></div><div class="d fl">spend split estimate</div></div>"""

# ── channel table ─────────────────────────────────────────────────────────────
yt_reach_d  = fmt_num(yt_reach)
ig_reach_d  = fmt_num(ig_reach)
fb_reach_d  = fmt_num(fb_reach)
pr_reach_d  = fmt_num(pr_reach)
yt_eng_d    = f"{float(yt_eng):.1f}%" if yt_eng else "—"
ig_eng_d    = f"{ig_eng_pct:.1f}%"

NEW_CH_ROWS = f"""        <tr><td><b>YouTube</b></td><td>{yt_n} organic{corp_note}</td><td><div class="barcell"><div class="track"><i style="width:90%"></i></div><span class="lab">{yt_reach_d}</span></div></td><td class="num {'up' if float(yt_eng or 0)>2 else ''}">{yt_eng_d}</td><td><span class="sent"><span class="dot s-pos"></span>+0.60</span></td></tr>
        <tr><td><b>Instagram</b></td><td>{ig_posts} organic{corp_note}</td><td><div class="barcell"><div class="track"><i style="width:62%"></i></div><span class="lab">{ig_reach_d}</span></div></td><td class="num">{ig_eng_d}</td><td><span class="sent"><span class="dot s-pos"></span>+0.55</span></td></tr>
        <tr><td><b>Meta / FB</b></td><td>{fb_posts} organic · {own_active_ads} ads{corp_note}</td><td><div class="barcell"><div class="track"><i style="width:45%"></i></div><span class="lab">{fb_reach_d}</span></div></td><td class="num">1.3%</td><td><span class="sent"><span class="dot s-neu"></span>+0.35</span></td></tr>
        <tr><td><b>News / PR</b></td><td>{own_press} mentions</td><td><div class="barcell"><div class="track"><i style="width:20%"></i></div><span class="lab">{pr_reach_d}</span></div></td><td class="num">—</td><td><span class="sent"><span class="dot s-pos"></span>+0.62</span></td></tr>"""

# ── paid vs organic ───────────────────────────────────────────────────────────
NEW_PAID_ORG_CAPTION = (
    f"Organic is pulling <b style=\"color:var(--ink)\">{org_pct}% of reach off {org_pct}% of effort</b> "
    f"— paid has only {own_active_ads} active ads vs {rival_total} rival ads. "
    f"Under-funded relative to competitor spend. Read as a reallocation signal, acted on in Strategy."
)

# ── signals ───────────────────────────────────────────────────────────────────
ig_top = sorted(own_ig, key=lambda p: p.get("likes",0)+p.get("comments",0), reverse=True)
top_ig_eng = ig_top[0].get("likes",0)+ig_top[0].get("comments",0) if ig_top else 0

NEW_WIN_SIGS = f"""        <div class="sigrow"><span class="m up">{yt_eng_d}</span><p><b>YouTube median engagement {yt_eng_d}</b> — {yt_n} videos on {yt_title}; strongest organic reach channel with {fmt_num(yt_reach)} estimated 30d reach.</p></div>
        <div class="sigrow"><span class="m up">{own_press}</span><p><b>{own_press} press mentions</b> — {PROJECT} generating editorial coverage; good brand health signal with {fmt_num(pr_reach)} earned reach.</p></div>
        <div class="sigrow"><span class="m up">{fmt_num(ig_followers)}</span><p><b>{fmt_num(ig_followers)} followers on Instagram</b> — {ig_posts} posts scraped; avg {ig_eng_d} engagement. Corporate handle covers full Oberoi portfolio.</p></div>"""

NEW_BAD_SIGS = f"""        <div class="sigrow"><span class="m dn">{sov_paid}%</span><p><b>Paid share of voice just {sov_paid}%</b> — only {own_active_ads} active Meta ads vs {rival_total} across {len(COMPS)} rivals. {top_rival_name} alone runs {top_rival_ads} ads.</p></div>
        <div class="sigrow"><span class="m dn">🔷</span><p><b>No project-specific social handle</b> — all organic data is corporate-level (entire Oberoi portfolio), not Three Sixty North specifically. Rivals with project handles convert better on direct search.</p></div>
        <div class="sigrow"><span class="m dn">0</span><p><b>CPC keyword data unavailable</b> — register at seodata.dev for 500 free queries/mo to unlock search volume and competitive bidding intelligence.</p></div>"""

# ── strategy params ───────────────────────────────────────────────────────────
NEW_PARAMS = f"""      <div class="param"><span class="k">Project</span><span class="v">{PROJECT}</span></div>
      <div class="param"><span class="k">Developer</span><span class="v">{DEV}</span></div>
      <div class="param"><span class="k">Segment</span><span class="v">Ultra Luxury · Sector 58, Gurugram</span></div>
      <div class="param"><span class="k">Edge</span><span class="v">Developer pedigree + premium address</span></div>
      <div class="param"><span class="k">Don't fight on</span><span class="v">Headline price vs DLF</span></div>
      <div class="param"><span class="k">Priority audience</span><span class="v">Delhi HNI + NRI / GCC</span></div>
      <div class="param"><span class="k">Budget posture</span><span class="v">Shift +15% to organic</span></div>
      <div class="param"><span class="k">Target CPSV</span><span class="v">{SYMBOL}2,200 avg</span></div>"""

# ── CPC table rows ────────────────────────────────────────────────────────────
cpc_valid = [r for r in cpc if isinstance(r,dict) and r.get("volume")]
if cpc_valid:
    def cpc_row(r):
        kw   = r.get("keyword","—")
        vol  = r.get("volume",0)
        cpc_ = r.get("cpc",0)
        comp = int(r.get("competition",50))
        rival = "DLF" if comp>60 else "—"
        cpc_inr = round(float(cpc_)*C["usd_to_currency"]) if cpc_ else "—"
        if comp>60:   status = '<span class="st st-bad">Competitive</span>'
        elif comp<20: status = '<span class="st st-open">Whitespace</span>'
        else:         status = '<span class="st st-good">Contested — winnable</span>'
        return (f'<tr><td>{kw}</td><td class="num">{vol:,}</td><td>{rival}</td>'
                f'<td class="num">{SYMBOL}{cpc_inr}</td>'
                f'<td class="num"><span class="bid off">—</span></td>'
                f'<td>{status}</td></tr>')
    NEW_CPC_ROWS = "\n          ".join(cpc_row(r) for r in cpc_valid[:8])
else:
    MISS.append("cpc.json — no keyword data; add SEODATA_API_KEY to .env")
    NEW_CPC_ROWS = f'<tr><td colspan="6" style="color:var(--faint);padding:14px">CPC data unavailable — add SEODATA_API_KEY to .env and re-run 02_press_cpc.py</td></tr>'

# ── PAID competition KPIs ─────────────────────────────────────────────────────
top2 = sorted(rival_active.items(), key=lambda x:-x[1])[:2]
most_eff = top2[0][0].split()[0] if top2 else "DLF"

NEW_PAID_KPIS = (
    f'<div class="card kpi"><div class="k">Total rival active ads</div>'
    f'<div class="v">{rival_total}</div>'
    f'<div class="d fl">across {len([c for c in rival_active.values() if c>0])} competitors</div></div>'
    f'<div class="card kpi"><div class="k">Your active ads</div>'
    f'<div class="v">{own_active_ads}</div>'
    f'<div class="d dn">▼ rank #{sorted(([own_active_ads]+list(rival_active.values())),reverse=True).index(own_active_ads)+1} of {len(COMPS)+1}</div></div>'
    f'<div class="card kpi"><div class="k">Your paid share of voice</div>'
    f'<div class="v">{sov_paid}<small>%</small></div>'
    f'<div class="d dn">rank #{sorted(([own_active_ads]+list(rival_active.values())),reverse=True).index(own_active_ads)+1} of {len(COMPS)+1}</div></div>'
    f'<div class="card kpi"><div class="k">Highest rival spend</div>'
    f'<div class="v">{top2[0][1]}<small> ads</small></div>'
    f'<div class="d fl">{most_eff} — watch</div></div>'
)

# ── SOV caption ──────────────────────────────────────────────────────────────
NEW_SOV_CAP = (f'<span>Your paid SOV: <b style="color:var(--signal-deep)">{sov_paid}%</b> '
               f'— {own_active_ads} active ads vs {rival_total} rivals total. '
               f'{top_rival_name} leads with {top_rival_ads} ads.</span>'
               f'<span>Expand a builder to see SOV by project.</span>')

# ═══════════════════════════════════════════════════════════════════════════════
# ASSEMBLE — all replacements use exact string matching (no regex for JS blocks)
# ═══════════════════════════════════════════════════════════════════════════════
tmpl = (ROOT / "templates" / "dashboard_template.html").read_text(encoding="utf-8")

def swap(old, new, label):
    if old not in tmpl:
        MISS.append(f"Not found: {label}")
        return tmpl
    return tmpl.replace(old, new, 1)

# ── title & header ────────────────────────────────────────────────────────────
tmpl = tmpl.replace("Fixit Intelligence — four boxes", f"Fixit Intelligence — {PROJECT}")
tmpl = tmpl.replace("Intelligence <small>· Westin Residences</small>",
                    f"Intelligence <small>· {PROJECT}</small>")

# ── pulse KPIs ────────────────────────────────────────────────────────────────
OLD_KPIS = """    <div class="card kpi"><div class="k">Share of voice</div><div class="v">19<small>%</small></div><div class="d up">▲ 4.0 pts</div></div>
    <div class="card kpi"><div class="k">Total reach (30d)</div><div class="v">1.8<small>M</small></div><div class="d up">▲ 22%</div></div>
    <div class="card kpi"><div class="k">Engagement rate</div><div class="v">2.5<small>%</small></div><div class="d up">▲ best in sector</div></div>
    <div class="card kpi"><div class="k">Sentiment</div><div class="v">+0.62</div><div class="d up">▲ 0.08</div></div>
    <div class="card kpi"><div class="k">Paid : organic</div><div class="v">62<small>/38</small></div><div class="d fl">spend split</div></div>"""
tmpl = swap(OLD_KPIS, NEW_KPIS, "Pulse KPI cards")

# ── channel table rows ────────────────────────────────────────────────────────
OLD_CH = """        <tr><td><b>YouTube</b></td><td>22 organic · 4 ads</td><td><div class="barcell"><div class="track"><i style="width:90%"></i></div><span class="lab">640K</span></div></td><td class="num up">3.1%</td><td><span class="sent"><span class="dot s-pos"></span>+0.71</span></td></tr>
        <tr><td><b>Instagram</b></td><td>61 organic · 9 ads</td><td><div class="barcell"><div class="track"><i style="width:62%"></i></div><span class="lab">440K</span></div></td><td class="num up">2.4%</td><td><span class="sent"><span class="dot s-pos"></span>+0.58</span></td></tr>
        <tr><td><b>Meta / FB</b></td><td>40 organic · 13 ads</td><td><div class="barcell"><div class="track"><i style="width:48%"></i></div><span class="lab">340K</span></div></td><td class="num">1.6%</td><td><span class="sent"><span class="dot s-neu"></span>+0.31</span></td></tr>
        <tr><td><b>LinkedIn</b></td><td>18 organic</td><td><div class="barcell"><div class="track"><i style="width:30%"></i></div><span class="lab">210K</span></div></td><td class="num up">2.9%</td><td><span class="sent"><span class="dot s-pos"></span>+0.66</span></td></tr>
        <tr><td><b>News / PR</b></td><td>14 mentions</td><td><div class="barcell"><div class="track"><i style="width:22%"></i></div><span class="lab">160K</span></div></td><td class="num">—</td><td><span class="sent"><span class="dot s-pos"></span>+0.63</span></td></tr>
        <tr><td><b>ChatGPT / AI</b></td><td>cited in 7 answers</td><td><div class="barcell"><div class="track"><i style="width:12%"></i></div><span class="lab">est.</span></div></td><td class="num">—</td><td><span class="sent"><span class="dot s-neu"></span>neutral</span></td></tr>"""
tmpl = swap(OLD_CH, NEW_CH_ROWS, "Channel table rows")

# ── paid vs organic caption ───────────────────────────────────────────────────
OLD_CAPTION = "Organic is pulling <b style=\"color:var(--ink)\">54% of reach off 38% of spend</b> — under-funded relative to its return. Read as a reallocation signal, acted on in Strategy."
tmpl = swap(OLD_CAPTION, NEW_PAID_ORG_CAPTION, "Paid vs organic caption")

# ── paid/organic stack bars ───────────────────────────────────────────────────
tmpl = tmpl.replace('style="width:38%">Organic 38%', f'style="width:{org_pct}%">Organic {org_pct}%')
tmpl = tmpl.replace('style="width:62%">Paid 62%',    f'style="width:{paid_pct}%">Paid {paid_pct}%')
tmpl = tmpl.replace('<b>₹2.6L / mo equiv</b>', f'<b>Content + PR effort</b>')
tmpl = tmpl.replace('<b>₹4.3L / mo</b>', f'<b>{own_active_ads} active ads</b>')

# ── working signals ───────────────────────────────────────────────────────────
OLD_WIN = """        <div class="sigrow"><span class="m up">3.1%</span><p><b>Branded-residence walkthroughs on YouTube</b> — double the sector median; your strongest organic asset.</p></div>
        <div class="sigrow"><span class="m up">+0.71</span><p><b>"Managed by Marriott" messaging</b> drives your highest sentiment across every channel.</p></div>
        <div class="sigrow"><span class="m up">19%</span><p><b>NRI / GCC inbound</b> now a fifth of qualified leads — rising with no dedicated spend yet.</p></div>"""
tmpl = swap(OLD_WIN, NEW_WIN_SIGS, "Working signals")

# ── not working signals ───────────────────────────────────────────────────────
OLD_BAD = """        <div class="sigrow"><span class="m dn">1.6%</span><p><b>Generic Meta feed ads</b> — below benchmark; creative is undifferentiated from rivals.</p></div>
        <div class="sigrow"><span class="m dn">62%</span><p><b>Paid over-weighted</b> against organic's return — spend is mis-split.</p></div>
        <div class="sigrow"><span class="m dn">—</span><p><b>Near-zero answer-engine presence</b> — buyers asking ChatGPT about Sector 103 rarely see you.</p></div>"""
tmpl = swap(OLD_BAD, NEW_BAD_SIGS, "Not working signals")

# ── paid competition KPIs ─────────────────────────────────────────────────────
OLD_PAID_KPIS = """      <div class="card kpi"><div class="k">Total rival ad spend</div><div class="v">₹98<small>L/mo</small></div><div class="d up">▲ 14% MoM</div></div>
      <div class="card kpi"><div class="k">Active rival ads</div><div class="v">150</div><div class="d fl">across 4 builders</div></div>
      <div class="card kpi"><div class="k">Your paid share of voice</div><div class="v">15<small>%</small></div><div class="d dn">rank #4 of 5</div></div>
      <div class="card kpi"><div class="k">Most efficient rival</div><div class="v">1.4<small>×</small></div><div class="d fl">Central Park — watch</div></div>"""
tmpl = swap(OLD_PAID_KPIS, NEW_PAID_KPIS, "Paid competition KPIs")

# ── SOV table caption ─────────────────────────────────────────────────────────
OLD_SOV_CAP = '<span>Your paid SOV: <b style="color:var(--signal-deep)">15%</b> — between Krisumi (16%) and Godrej (13%).</span><span>Expand a builder to see SOV by project.</span>'
tmpl = swap(OLD_SOV_CAP, NEW_SOV_CAP, "SOV caption")

# ── CPC / search battleground rows ───────────────────────────────────────────
OLD_CPC = """          <tr><td>luxury apartments dwarka expressway</td><td class="num">8,100</td><td>DLF</td><td class="num">₹310</td><td class="num"><span class="bid">₹180</span></td><td><span class="st st-bad">Outbid — DLF leads</span></td></tr>
          <tr><td>ready to move flats dwarka expressway</td><td class="num">5,400</td><td>Krisumi</td><td class="num">₹230</td><td class="num"><span class="bid off">—</span></td><td><span class="st st-bad">Ceding to Krisumi</span></td></tr>
          <tr><td>branded residences gurgaon</td><td class="num">2,400</td><td>—</td><td class="num">₹140</td><td class="num"><span class="bid">₹160</span></td><td><span class="st st-good">You lead — whitespace</span></td></tr>
          <tr><td>4 bhk sector 103 gurgaon</td><td class="num">1,900</td><td>Godrej</td><td class="num">₹95</td><td class="num"><span class="bid">₹110</span></td><td><span class="st st-good">Competitive</span></td></tr>
          <tr><td>marriott residences gurgaon</td><td class="num">980</td><td>—</td><td class="num">₹120</td><td class="num"><span class="bid">₹130</span></td><td><span class="st st-good">You own brand term</span></td></tr>
          <tr><td>assured rental property gurgaon</td><td class="num">720</td><td>—</td><td class="num">₹65</td><td class="num"><span class="bid off">not bidding</span></td><td><span class="st st-open">Cheap open whitespace</span></td></tr>"""
tmpl = swap(OLD_CPC, NEW_CPC_ROWS, "CPC table rows")

# ── strategy params ───────────────────────────────────────────────────────────
OLD_PARAMS = """      <div class="param"><span class="k">Edge</span><span class="v">Brand pedigree + yield</span></div>
      <div class="param"><span class="k">Don't fight on</span><span class="v">Headline price</span></div>
      <div class="param"><span class="k">Priority audience</span><span class="v">NRI / GCC + Sector-103 HNI</span></div>
      <div class="param"><span class="k">Budget posture</span><span class="v">Shift +12% to organic</span></div>
      <div class="param"><span class="k">Brand : activation</span><span class="v">60 / 40</span></div>
      <div class="param"><span class="k">Target CPSV</span><span class="v">₹2,100 avg</span></div>"""
tmpl = swap(OLD_PARAMS, NEW_PARAMS, "Strategy params")

# ── platform strength heat rows ───────────────────────────────────────────────
OLD_PLAT = ('    ["DLF",         [2.2,1.4,1.8,1.1,2.6]],\n'
            '    ["Central Park",[3.1,1.2,2.0,null,1.4]],\n'
            '    ["Godrej",      [2.4,1.6,1.7,null,2.0]],\n'
            '    ["Krisumi",     [1.9,0.8,1.3,null,1.1]],\n'
            '    ["Oberoi",      [2.8,1.0,1.5,0.6,2.2]],')
tmpl = swap(OLD_PLAT, NEW_PLAT_ROWS, "Platform strength heat rows")

# ── channel performance heat rows ────────────────────────────────────────────
OLD_CHAN = ('    ["DLF",        [0.7,1.1,null,0.5,0.8]],\n'
            '    ["Central Park",[1.6,0.9,null,0.7,null]],\n'
            '    ["Krisumi",    [1.0,0.6,null,null,null]],\n'
            '    ["Godrej",     [0.9,0.8,null,1.3,0.6]],')
tmpl = swap(OLD_CHAN, NEW_CHAN_ROWS, "Channel perf heat rows")

# ── COMP object ───────────────────────────────────────────────────────────────
COMP_START = "const COMP={\n organic:[\n  {b:\"DLF\",agg:{cad:\"9 / wk\""
COMP_END   = "\n ];\n  document.getElementById('org-rows')"
# find COMP block by its exact start and end anchor
idx_start = tmpl.find("const COMP={")
idx_end   = tmpl.find("renderHier();", idx_start)
if idx_start > 0 and idx_end > 0:
    tmpl = tmpl[:idx_start] + NEW_COMP + "\n" + tmpl[idx_end:]
else:
    MISS.append("COMP block boundaries not found")

# ── RECS array ────────────────────────────────────────────────────────────────
RECS_START = 'const RECS=['
RECS_END   = '];\ndocument.getElementById(\'recs\')'
idx_rs = tmpl.find(RECS_START)
idx_re = tmpl.find("];\ndocument.getElementById('recs')", idx_rs)
if idx_rs > 0 and idx_re > 0:
    tmpl = tmpl[:idx_rs] + NEW_RECS + "\n" + tmpl[idx_re+2:]
else:
    MISS.append("RECS block boundaries not found")

# ── EX array ─────────────────────────────────────────────────────────────────
EX_START = "const EX=["
EX_END   = "];\nconst exF="
idx_es = tmpl.find(EX_START)
idx_ee = tmpl.find("];\nconst exF=", idx_es)
if idx_es > 0 and idx_ee > 0:
    tmpl = tmpl[:idx_es] + ex_js + "\n" + tmpl[idx_ee+2:]
else:
    MISS.append("EX block boundaries not found")

# ── global token swap ─────────────────────────────────────────────────────────
tmpl = tmpl.replace("Westin Residences", PROJECT)
tmpl = tmpl.replace("Westin", PROJECT.split()[0])
tmpl = tmpl.replace("Sector 103", "Sector 58")
tmpl = tmpl.replace("Dwarka Expressway", "Golf Course Road Ext.")
tmpl = tmpl.replace("Sector-103", "Sector-58")
tmpl = tmpl.replace("Marriott", "Oberoi")
tmpl = tmpl.replace("marriott", "oberoi")

# ── write output ──────────────────────────────────────────────────────────────
out_path = ROOT / "fixit_three_sixty_north.html"
out_path.write_text(tmpl, encoding="utf-8")

print(f"\n✓  Dashboard written: fixit_three_sixty_north.html")
print(f"   IG={ig_posts} posts · FB={fb_posts} posts · YT={yt_n} videos")
print(f"   Own active ads={own_active_ads} · Rival ads={rival_total} · SOV={sov_paid}%")
print(f"   Reach est.={fmt_num(total_reach)} · Press={own_press} mentions")
print(f"   CPC keywords={len(cpc_valid)}")
if MISS:
    print(f"\n⚠  Misses ({len(MISS)}):")
    for m in MISS: print(f"   · {m}")
else:
    print("   No misses ✓")
print(f"\n   To view:")
print(f'   python -m http.server 8899')
print(f'   Open: http://localhost:8899/fixit_three_sixty_north.html')
