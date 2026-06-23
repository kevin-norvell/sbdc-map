# America's SBDC — National Center Locator

A single-page, static web app that maps every Small Business Development Center
(SBDC) in the America's SBDC nationwide network on an interactive Leaflet map.

No API keys. No build step. Just `index.html` + `data.json` + `assets/`.

![screenshot](assets/asbdc-logo.png)

## What it does

- **Interactive map** — Leaflet + OpenStreetMap tiles (keyless), with ~770 centers
  clustered so the whole network is legible at the national level and resolves to
  individual pins as you zoom in.
- **Brand** — America's SBDC colors (`#d11242` red, `#022d61` navy, `#5588c6` blue)
  and the official logo. Lead/state offices are navy pins; service centers are red.
- **Filter by state network** — dropdown of every state/territory with a live count.
- **Search** — by center name or city.
- **Popups** — center name, parent org, address, click-to-call phone, and website.
- **Sidebar list** — synced to the current filter; click an entry to fly to its pin.

## Data

There is no longer a one-click bulk download of SBDC service-center locations on
data.gov — the catalog entry just points to a human web page, and the old SBA
office JSON API was retired in the 2023 sba.gov redesign. So the data is sourced
directly from **America's SBDC's own "Find Your SBDC" directory**
(`americassbdc.org/find-your-sbdc`), which is the canonical, on-brand source.

Pipeline (all scripts in `scripts/`):

1. **`harvest.py`** — POSTs each state/territory to the America's SBDC state search
   and parses the returned center blocks (name, contact, address, phone, email,
   website, Facebook). The full street address is pulled from each "View Map" link.
2. **`reparse.py`** — re-parses the cached HTML with correct Lead-Center vs.
   Center section detection. → `data/centers_dedup.json` (770 unique centers).
3. **`geocode.py`** — the directory has **no lat/long**, so addresses are geocoded
   with the **free U.S. Census batch geocoder** (`Public_AR_Current`). Resilient by
   design: a disk cache (`data/geocache.json`) so reruns never redo solved
   addresses, chunked batches with retry/backoff, and oneline + territory-centroid
   fallbacks. Pacific territories (GU, AS, VI, MP, PW, FM, MH) use island centroids
   because Census doesn't cover them. → `data/centers_geo.json`.
4. **`build_data.py`** — slims placed records into the app's `data.json`.

To refresh the data end-to-end:

```bash
python3 scripts/harvest.py      # re-pull from America's SBDC
python3 scripts/reparse.py      # parse + dedupe
python3 scripts/geocode.py      # geocode (resumable; safe to re-run)
python3 scripts/build_data.py   # emit data.json
```

Centers the Census geocoder can't resolve (PO boxes, suite-only addresses during
service outages) are simply omitted from the map; re-running `geocode.py` later
picks them up once the service recovers, thanks to the cache.

## Run locally

Any static server works (the app `fetch`es `data.json`, so `file://` won't do):

```bash
cd sbdc-map
python3 -m http.server 8790
# open http://localhost:8790
```

## Deploy to Netlify

`netlify.toml` is configured for a no-build static deploy (publish = `.`).

```bash
# from the sbdc-map/ folder
netlify deploy --prod
```

or drag the `sbdc-map/` folder onto the Netlify dashboard. The only files the
deploy needs are `index.html`, `data.json`, `assets/`, and `netlify.toml`.

## Attribution

Map © OpenStreetMap contributors. Center data: America's SBDC.
