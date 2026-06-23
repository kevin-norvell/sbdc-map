#!/usr/bin/env python3
"""Harvest all SBDC centers from America's SBDC 'Find Your SBDC' state search.

For each state/territory the plugin returns a server-rendered HTML block.
Each center is an <h4 class="centerName"> followed by a contact/address block
whose Google-Maps 'View Map' link embeds the full address (geocoder-ready).
"""
import re, json, time, urllib.parse, subprocess, html, sys, pathlib

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
RAW = DATA / "states"
RAW.mkdir(parents=True, exist_ok=True)

STATES = {
 "AL":"Alabama","AK":"Alaska","AS":"American Samoa","AZ":"Arizona","AR":"Arkansas",
 "CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"District of Columbia",
 "FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana",
 "IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland",
 "MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri",
 "MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey",
 "NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio",
 "OK":"Oklahoma","OR":"Oregon","GU":"Pacific Islands","PA":"Pennsylvania","PR":"Puerto Rico",
 "RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas",
 "UT":"Utah","VT":"Vermont","VA":"Virginia","VI":"Virgin Islands","WA":"Washington",
 "WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
}

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
URL = "https://americassbdc.org/find-your-sbdc/"
CJ = str(DATA / "cj.txt")

def seed_cookie():
    subprocess.run(["curl","-s","--compressed","-c",CJ,"-A",UA,URL,"-o","/dev/null"],check=True)

def fetch_state(code):
    out = RAW / f"{code}.html"
    subprocess.run([
        "curl","-s","--compressed","-b",CJ,"-A",UA,
        "-H",f"Referer: {URL}","-H","Origin: https://americassbdc.org",
        "-H","Accept: text/html,application/xhtml+xml",
        "-H","Content-Type: application/x-www-form-urlencoded",
        "-X","POST",URL,"--data",f"state={code}","-o",str(out)
    ],check=True)
    return out.read_text(encoding="utf-8",errors="replace")

def clean(s): return re.sub(r"\s+"," ",re.sub("<.*?>","",s)).strip()

def parse_state(code, name, page):
    # grab just the results region
    i = page.find('id="results"')
    j = page.find('</div>', page.find('SBDC Centers', i))  # rough; we parse by h4 anyway
    region = page[i:i+60000] if i>=0 else page
    # split into center chunks on the centerName h4
    parts = re.split(r'<h4 class="centerName[^"]*"[^>]*>', region)
    header = parts[0]
    records = []
    lead_marker = header  # track lead/center section via running text
    running = header
    for chunk in parts[1:]:
        nm_end = chunk.find('</h4>')
        center_name = clean(chunk[:nm_end])
        body = chunk[nm_end+5:]
        # stop body at the next section header h2 if present (keeps fields local)
        body_stop = re.search(r'<h2', body)
        body_local = body[:body_stop.start()] if body_stop else body
        # is this under Lead Center section?
        section = "Lead Center" if "<em>Lead Center</em>" in running and "<em>Centers</em>" not in running else "Center"
        running += chunk[:nm_end+5+len(body_local)]
        # subtitle
        sub = re.search(r'<p class="subtitle">(.*?)</p>', body_local, re.S)
        subtitle = clean(sub.group(1)) if sub else ""
        # full address from the maps link
        mp = re.search(r"maps\.google\.com/\?q=([^'\"]+)", body_local)
        full_addr = ""
        if mp:
            full_addr = urllib.parse.unquote_plus(mp.group(1)).strip(" ,")
        # city, state, zip from the 'City, ST ZIP -' line
        csz = re.search(r'([A-Za-z .,\'\-/]+),\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*-\s*<a', body_local)
        city = clean(csz.group(1)) if csz else ""
        st_abbr = csz.group(2) if csz else code
        zipc = csz.group(3) if csz else ""
        # street: the <br> lines between the contact/title and the City line
        # decode br-structure
        pre = body_local
        # contact name + title are first two <br> tokens after the opening <p ...>
        ptxt = re.split(r'<br\s*/?>', re.sub(r'^.*?<p[^>]*>', '', pre, count=1, flags=re.S))
        ptxt = [clean(x) for x in ptxt]
        # street = the segment immediately before 'City, ST ZIP'
        street = ""
        if full_addr and city:
            # remove trailing 'City ST ZIP' from full_addr to get street
            tail = f"{city} {st_abbr} {zipc}"
            if full_addr.replace(",","").endswith(tail.replace(",","")):
                street = full_addr[:len(full_addr)-len(tail)].strip(" ,")
            else:
                street = full_addr
        phone = re.search(r'<b>Phone:\s*</b>\s*([0-9().\- x]+)', body_local)
        phone = clean(phone.group(1)) if phone else ""
        email = re.search(r"mailto:([^'\"]+)", body_local)
        email = email.group(1) if email else ""
        web = re.search(r"<b>Web Site:\s*</b>\s*<a href='([^']+)'", body_local)
        website = web.group(1) if web else ""
        fb = re.search(r"<b>Facebook:\s*</b>\s*<a href='([^']+)'", body_local)
        facebook = fb.group(1) if fb else ""
        records.append({
            "name": html.unescape(center_name),
            "subtitle": html.unescape(subtitle),
            "is_lead": section=="Lead Center",
            "street": html.unescape(street),
            "city": html.unescape(city),
            "state": st_abbr,
            "state_name": name,
            "zip": zipc,
            "full_address": html.unescape(full_addr),
            "phone": phone,
            "email": email,
            "website": website,
            "facebook": facebook,
        })
    return records

def main():
    seed_cookie()
    all_recs=[]
    summary=[]
    for code,name in STATES.items():
        try:
            page=fetch_state(code)
            recs=parse_state(code,name,page)
        except Exception as e:
            print(f"{code}: ERROR {e}",file=sys.stderr); recs=[]
        summary.append((code,len(recs)))
        all_recs.extend(recs)
        print(f"{code} {name}: {len(recs)} centers")
        time.sleep(0.4)
    (DATA/"centers_raw.json").write_text(json.dumps(all_recs,indent=2))
    print(f"\nTOTAL: {len(all_recs)} centers across {len(STATES)} states/territories")
    nostreet=[r for r in all_recs if not r['street']]
    print(f"Missing street: {len(nostreet)}")

if __name__=="__main__":
    main()
