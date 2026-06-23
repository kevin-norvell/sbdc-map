#!/usr/bin/env python3
"""Secondary fallback: geocode centers Census couldn't place, using the free,
keyless OpenStreetMap Nominatim service. One loose query per center, >=1.1s
apart (policy compliant). Merges into data/geocache.json. Re-runnable."""
import json, subprocess, time, pathlib
DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
CACHE = DATA / "geocache.json"
UA = "americas-sbdc-locator/1.0 (static map build; contact kevin.norvell@gmail.com)"
NOM = "https://nominatim.openstreetmap.org/search"
TERR = {"GU","AS","VI","MP","PW","FM","MH"}

def addr_key(c):
    street=c["street"] or c["city"] or c["full_address"]
    return f'{street}|{c["city"]}|{c["state"]}|{c["zip"]}'

def nominatim(q):
    out=DATA/"nom.json"
    subprocess.run(["curl","-s","--max-time","30","-A",UA,"--get",NOM,
        "--data-urlencode","format=jsonv2","--data-urlencode","limit=1",
        "--data-urlencode","countrycodes=us","--data-urlencode","q="+q,
        "-o",str(out)],check=True)
    try:
        d=json.loads(out.read_text())
        if d: return (float(d[0]["lat"]), float(d[0]["lon"]))
    except: pass
    return None

def main():
    src = DATA/"centers_merged.json" if (DATA/"centers_merged.json").exists() else DATA/"centers_dedup.json"
    centers=json.load(open(src))
    cache=json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo=[c for c in centers if c["state"] not in TERR and addr_key(c) not in cache]
    print(f"OSM fallback: {len(todo)} centers to place",flush=True)
    placed=0
    for i,c in enumerate(todo):
        q=", ".join(x for x in [c["street"],c["city"],
                    f'{c["state"]} {c["zip"]}'.strip()] if x)
        ll=nominatim(q)
        if not ll and c["city"]:                       # fall back to city/state
            ll=nominatim(f'{c["city"]}, {c["state"]}'); time.sleep(1.1)
        if ll:
            cache[addr_key(c)]=ll; placed+=1
        time.sleep(1.1)
        if (i+1)%20==0:
            CACHE.write_text(json.dumps(cache))
            print(f"  {i+1}/{len(todo)} done, {placed} placed",flush=True)
    CACHE.write_text(json.dumps(cache))
    print(f"OSM fallback placed {placed}/{len(todo)}",flush=True)

if __name__=="__main__": main()
