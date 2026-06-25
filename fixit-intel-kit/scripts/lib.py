#!/usr/bin/env python3
"""Shared config/env loader + helpers. All scripts import from here."""
import os, json, sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent          # fixit-intel-kit/
OUT  = ROOT / "out"
OUT.mkdir(exist_ok=True)
load_dotenv(ROOT / ".env", override=True)

def cfg():
    p = ROOT / "config.json"
    if not p.exists():
        sys.exit("ERROR: config.json not found. Copy config.example.json -> config.json and edit it.")
    return json.loads(p.read_text())

def env(k, required=True):
    v = os.getenv(k)
    if required and not v:
        sys.exit(f"ERROR: {k} missing from .env (copy .env.template -> .env and fill it).")
    return v

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote out/{name}")

def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))

# Theme keyword buckets — tune per market if needed.
THEMES = {
 "possession": ["possession","ready","handover","completion","2030","2031"],
 "price":      ["price","aed","inr","payment plan","80/20","starting","from","booking","crore"],
 "amenities":  ["amenity","amenities","pool","beach","wellness","furnished","infinity","sky","gym"],
 "location":   ["location","creek","harbour","waterfront","canal","downtown","minutes","views","metro"],
 "builder_rep":["trusted","developer","award","branded","iconic","legacy"],
 "investment": ["investment","roi","returns","yield","golden visa","capital","nri","rental"],
 "luxury":     ["luxury","luxurious","premium","ultra","exclusive","penthouse","branded"],
 "waterfront": ["waterfront","creek","sea","marina","lagoon","canal","beach","river"],
}
def tag_themes(text):
    t = (text or "").lower()
    return [k for k, kw in THEMES.items() if any(w in t for w in kw)]
