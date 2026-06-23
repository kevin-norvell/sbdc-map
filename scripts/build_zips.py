#!/usr/bin/env python3
"""Build a compact ZIP->[lat,lng] lookup for client-side 'nearest center' search.

Source: U.S. Census ZCTA Gazetteer (free, keyless, official).
  data/gaz_zcta/2023_Gaz_zcta_national.txt  (tab-delimited)
Output: zip-centroids.json at the project root, e.g. {"40508":[38.04,-84.51], ...}
ZCTAs approximate USPS ZIP codes; PO-box-only ZIPs aren't covered (the UI falls
back to the 3-digit prefix area for those)."""
import json, glob, pathlib
DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
ROOT = DATA.parent
src = glob.glob(str(DATA / "gaz_zcta" / "*.txt"))[0]
out = {}
with open(src, encoding="utf-8", errors="replace") as f:
    header = f.readline()  # GEOID ALAND AWATER ALAND_SQMI AWATER_SQMI INTPTLAT INTPTLONG
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 7:
            continue
        zc = parts[0].strip()
        try:
            lat = round(float(parts[5].strip()), 4)
            lng = round(float(parts[6].strip()), 4)
        except ValueError:
            continue
        if len(zc) == 5:
            out[zc] = [lat, lng]
path = ROOT / "zip-centroids.json"
json.dump(out, open(path, "w"), separators=(",", ":"))
print(f"zip-centroids.json: {len(out)} ZIPs ({round(path.stat().st_size/1024)} KB)")
