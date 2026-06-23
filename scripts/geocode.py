#!/usr/bin/env python3
"""Geocode SBDC centers with the free Census batch geocoder.

Resilient + resumable:
  * per-address disk cache (geocache.json) keyed by the address string,
    so reruns never redo solved addresses and survive Census's flakiness
  * chunked batch calls with retry/backoff
  * a second batch pass over chunks that errored out
  * oneline + territory-centroid fallbacks for the final stragglers
"""
import json, csv, io, subprocess, pathlib, time, sys
DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
BENCH = "Public_AR_Current"
BATCH = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
ONELINE = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
CACHE = DATA / "geocache.json"

TERRITORY = {  # Census doesn't cover these; use island centroids
 "GU": (13.4443,144.7937), "AS": (-14.2710,-170.1322), "VI": (18.3358,-64.8963),
 "MP": (15.0979,145.6739), "PW": (7.5150,134.5825), "FM": (6.9248,158.1611),
 "MH": (7.1315,171.1845),
}

def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}

def save_cache(c):
    CACHE.write_text(json.dumps(c))

def addr_key(c):
    street=c["street"] or c["city"] or c["full_address"]
    return f'{street}|{c["city"]}|{c["state"]}|{c["zip"]}'

def _batch_once(rows):
    buf=io.StringIO(); w=csv.writer(buf)
    for r in rows: w.writerow(r)
    (DATA/"geocode_in.csv").write_text(buf.getvalue())
    out=DATA/"geocode_out.csv"
    subprocess.run(["curl","-s","--max-time","180","-X","POST",
        "-F","benchmark="+BENCH,"-F","addressFile=@"+str(DATA/'geocode_in.csv')+";type=text/csv",
        BATCH,"-o",str(out)],check=True)
    txt=out.read_text(errors="replace")
    if txt.lstrip().startswith("<"): return None
    res={}
    for row in csv.reader(io.StringIO(txt)):
        if len(row)<6: continue
        if row[2]=="Match":
            try:
                lon,lat=row[5].split(","); res[row[0]]=(float(lat),float(lon))
            except: pass
    return res

def batch_pass(rows, chunk, tries, label):
    """rows: [(key,street,city,state,zip)]. Returns {key:(lat,lng)}."""
    res={}
    for i in range(0,len(rows),chunk):
        part=rows[i:i+chunk]
        for t in range(tries):
            got=_batch_once([(k,s,c,st,z) for (k,s,c,st,z) in part])
            if got is not None:
                res.update(got)
                print(f"  [{label}] chunk {i//chunk+1}: matched {len(got)}/{len(part)}",flush=True)
                break
            time.sleep(3*(t+1))
        else:
            print(f"  [{label}] chunk {i//chunk+1}: still erroring, deferring",flush=True)
        time.sleep(0.8)
    return res

def oneline(q):
    out=DATA/"one.json"
    subprocess.run(["curl","-s","--max-time","30","--get",ONELINE,
        "--data-urlencode","address="+q,"--data-urlencode","benchmark="+BENCH,
        "-o",str(out)],check=True)
    try:
        m=json.loads(out.read_text())["result"]["addressMatches"]
        if m: return (m[0]["coordinates"]["y"], m[0]["coordinates"]["x"])
    except: pass
    return None

def main():
    src = DATA/"centers_merged.json" if (DATA/"centers_merged.json").exists() else DATA/"centers_dedup.json"
    centers=json.load(open(src))
    cache=load_cache()
    # which need geocoding (not in cache, not territory)
    todo=[]
    for c in centers:
        k=addr_key(c)
        if k in cache or c["state"] in TERRITORY: continue
        street=c["street"] or c["city"] or c["full_address"]
        todo.append((k,street,c["city"],c["state"],c["zip"]))
    print(f"{len(centers)} centers | cached {len(cache)} | to geocode {len(todo)}",flush=True)

    # pass 1: batches of 100
    if todo:
        got=batch_pass(todo,100,3,"pass1")
        cache.update(got); save_cache(cache)
        todo=[r for r in todo if r[0] not in cache]
        print(f"after pass1: {len(todo)} remaining",flush=True)
    # pass 2: smaller batches of 40 for deferred/error chunks
    if todo:
        got=batch_pass(todo,40,4,"pass2")
        cache.update(got); save_cache(cache)
        todo=[r for r in todo if r[0] not in cache]
        print(f"after pass2: {len(todo)} remaining",flush=True)
    # pass 3: oneline for stragglers
    for (k,street,city,state,zipc) in todo:
        q=", ".join(x for x in [street,city,f"{state} {zipc}".strip()] if x)
        ll=oneline(q)
        if ll: cache[k]=ll
        time.sleep(0.25)
    save_cache(cache)

    # attach to centers
    placed=0; failed=[]
    for c in centers:
        k=addr_key(c)
        if c["state"] in TERRITORY:
            c["lat"],c["lng"]=TERRITORY[c["state"]]; c["geocode"]="territory"; placed+=1
        elif k in cache:
            c["lat"],c["lng"]=cache[k]; c["geocode"]="census"; placed+=1
        else:
            c["lat"]=c["lng"]=None; c["geocode"]="failed"; failed.append(c)
    json.dump(centers,open(DATA/"centers_geo.json","w"),indent=2)
    print(f"\nPLACED {placed}/{len(centers)} | failed {len(failed)}",flush=True)
    for c in failed: print("  FAIL",c["state"],c["name"],"|",repr(c["full_address"]))

if __name__=="__main__": main()
