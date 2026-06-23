#!/usr/bin/env python3
"""Merge enriched per-state center lists into the national directory.

For each state present in data/enrich/*.json, the enriched list REPLACES that
state's national-directory entries (the enriched lists are satellite-level
complete). States not enriched keep their national-directory entries.
"""
import json, glob, pathlib, re
from harvest import STATES
from classify import classify
DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

LEAD_PAT = re.compile(r"(State Office|Lead Center|Network|Headquarters|State HQ|State Lead)", re.I)

def norm(s): return re.sub(r"\s+"," ",(s or "")).strip()

def main():
    national = json.load(open(DATA/"centers_dedup.json"))
    # collect enriched states
    enriched = {}
    for f in sorted(glob.glob(str(DATA/"enrich"/"*.json"))):
        d = json.load(open(f))
        for st, recs in d.items():
            enriched.setdefault(st, []).extend(recs)
    print("enriched states:", sorted(enriched.keys()), "| records:", sum(len(v) for v in enriched.values()))

    out = []
    # keep national entries for states NOT enriched
    for c in national:
        if c["state"] in enriched:
            continue
        c["type"] = classify(c["name"], c.get("is_lead"), c.get("street"), c.get("state"))
        out.append(c)
    # add enriched records with full schema
    for st, recs in enriched.items():
        seen = set()
        for r in recs:
            key = (norm(r["name"]).lower(), norm(r["street"]).lower(), norm(r["city"]).lower())
            if key in seen:
                continue
            seen.add(key)
            is_lead = bool(LEAD_PAT.search(r["name"]))
            out.append({
                "name": norm(r["name"]),
                "subtitle": "",
                "is_lead": is_lead,
                "type": classify(r["name"], is_lead, r.get("street",""), st),
                "street": norm(r.get("street","")),
                "city": norm(r["city"]),
                "state": st,
                "state_name": STATES.get(st, st),
                "zip": norm(r.get("zip","")),
                "full_address": ", ".join(x for x in [norm(r.get("street","")), norm(r["city"]),
                                f'{st} {norm(r.get("zip",""))}'.strip()] if x),
                "phone": norm(r.get("phone","")),
                "email": "",
                "website": norm(r.get("website","")),
                "facebook": "",
                "enriched": True,
            })
    for i, c in enumerate(out):
        c["id"] = i + 1
    json.dump(out, open(DATA/"centers_merged.json","w"), indent=2)
    import collections
    sc = collections.Counter(c["state"] for c in out)
    print(f"merged total: {len(out)} centers")
    print("enriched-state counts:", {st: sc[st] for st in sorted(enriched)})

if __name__ == "__main__":
    main()
