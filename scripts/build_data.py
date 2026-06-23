#!/usr/bin/env python3
"""Slim geocoded centers into the app's data.json (only placed records, only needed fields).

Each record carries a `type` of lead/service/outreach (baked here as a fallback when the
upstream merge didn't set it, using the shared classifier)."""
import json, pathlib, collections
from classify import classify
DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
ROOT = DATA.parent
src=json.load(open(DATA/"centers_geo.json"))
keep=["name","subtitle","is_lead","type","street","city","state","state_name","zip",
      "phone","email","website","facebook","lat","lng","geocode"]
# Give each island territory its own name (they were harvested under one "Pacific Islands" label)
TERRITORY_NAMES={"GU":"Guam","PW":"Palau","FM":"Micronesia (FSM)","MH":"Marshall Islands",
                 "MP":"Northern Mariana Islands","AS":"American Samoa","VI":"U.S. Virgin Islands"}
out=[]
for c in src:
    if not isinstance(c.get("lat"),(int,float)): continue
    c["type"] = classify(c.get("name",""), c.get("is_lead"), c.get("street",""), c.get("state",""))
    c["state_name"] = TERRITORY_NAMES.get(c.get("state"), c.get("state_name"))
    out.append({k:c.get(k) for k in keep})
# centers (lead+service) first, outreach last; within that by state then name
order={"lead":0,"service":1,"outreach":2}
out.sort(key=lambda c:(c["state"], order.get(c["type"],1), c["name"]))
json.dump(out, open(ROOT/"data.json","w"), separators=(",",":"))
tc=collections.Counter(c["type"] for c in out)
centers=tc["lead"]+tc["service"]
print(f"data.json: {len(out)} placed | centers(lead+service)={centers} outreach={tc['outreach']} "
      f"({round((ROOT/'data.json').stat().st_size/1024)} KB)")
miss=[c for c in src if not isinstance(c.get('lat'),(int,float))]
print("dropped (no coords):",len(miss))
