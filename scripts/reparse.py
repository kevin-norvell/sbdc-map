#!/usr/bin/env python3
"""Reparse cached state HTML with correct Lead-Center/Center section detection."""
import re, json, urllib.parse, html, pathlib
from harvest import STATES, DATA, RAW

def clean(s): return re.sub(r"\s+"," ",re.sub("<.*?>","",s)).strip()

def parse_state(code, name, page):
    i = page.find('id="results"')
    region = page[i:i+80000] if i>=0 else page
    # section boundaries
    lead_pos = region.find('<em>Lead Center</em>')
    cen_pos  = region.find('<em>Centers</em>')
    records=[]
    for m in re.finditer(r'<h4 class="centerName[^"]*"[^>]*>(.*?)</h4>', region, re.S):
        pos = m.start()
        center_name = clean(m.group(1))
        body = region[m.end(): m.end()+4000]
        nxt = re.search(r'<h[24]', body)
        body_local = body[:nxt.start()] if nxt else body
        is_lead = (lead_pos!=-1 and pos>lead_pos) and (cen_pos==-1 or pos<cen_pos)
        sub = re.search(r'<p class="subtitle">(.*?)</p>', body_local, re.S)
        subtitle = clean(sub.group(1)) if sub else ""
        mp = re.search(r"maps\.google\.com/\?q=([^'\"]+)", body_local)
        full_addr = urllib.parse.unquote_plus(mp.group(1)).strip(" ,") if mp else ""
        csz = re.search(r'([A-Za-z .,\'\-/]+),\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*-\s*<a', body_local)
        city = clean(csz.group(1)) if csz else ""
        st_abbr = csz.group(2) if csz else code
        zipc = csz.group(3) if csz else ""
        street=""
        if full_addr and city:
            tail=f"{city} {st_abbr} {zipc}"
            if full_addr.replace(",","").endswith(tail.replace(",","")):
                street=full_addr[:len(full_addr)-len(tail)].strip(" ,")
            else: street=full_addr
        elif full_addr and not city:
            street=full_addr
        ph=re.search(r'<b>Phone:\s*</b>\s*([0-9().\- x]+)', body_local)
        em=re.search(r"mailto:([^'\"]+)", body_local)
        web=re.search(r"<b>Web Site:\s*</b>\s*<a href='([^']+)'", body_local)
        fb=re.search(r"<b>Facebook:\s*</b>\s*<a href='([^']+)'", body_local)
        records.append({
            "name":html.unescape(center_name),"subtitle":html.unescape(subtitle),
            "is_lead":is_lead,"street":html.unescape(street),"city":html.unescape(city),
            "state":st_abbr,"state_name":name,"zip":zipc,
            "full_address":html.unescape(full_addr),
            "phone":clean(ph.group(1)) if ph else "",
            "email":em.group(1) if em else "",
            "website":web.group(1) if web else "",
            "facebook":fb.group(1) if fb else "",
        })
    return records

def main():
    all_recs=[]
    for code,name in STATES.items():
        f=RAW/f"{code}.html"
        if not f.exists(): continue
        all_recs.extend(parse_state(code,name,f.read_text(encoding="utf-8",errors="replace")))
    for idx,r in enumerate(all_recs): r["id"]=idx+1
    (DATA/"centers_raw.json").write_text(json.dumps(all_recs,indent=2))
    print("total",len(all_recs),"| lead",sum(r['is_lead'] for r in all_recs),
          "| missing street",sum(1 for r in all_recs if not r['street']))

if __name__=="__main__": main()
