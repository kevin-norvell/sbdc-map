#!/usr/bin/env python3
"""Shared SBDC location-type classifier (kept in sync with the JS copy in index.html).

  lead     - state office / lead center / regional headquarters
  service  - a permanently staffed service center (street address, own/college office)
  outreach - circuit-rider / by-appointment site hosted at a partner venue
             (chamber, library, county building...) or with no fixed street address
"""
import re

LEAD = re.compile(r"(State Office|Lead Center|\bNetwork\b|Headquarters|State HQ|State Lead|Regional HQ)", re.I)
PARTNER = re.compile(
    r"(Outreach|Circuit|Satellite|Chamber|Library|Church|Main Street|Economic Develop|"
    r"\bEDC\b|Partnership|\bAlliance\b|Government Complex|Permit Center|Office Share|"
    r"Workforce|Community Partnership|Business Resource|Incubator|Collaborative|\bBID\b|"
    r"Conference Center|Recreation|Development Group)", re.I)
COUNTY = re.compile(r"[–\-]\s*[A-Za-z. ]+\bCounty\b", re.I)   # 'Host – Xxx County' satellite
MAINISH = re.compile(r"(Main|Regional HQ|\bHQ\b|Lead|State Office|\bNetwork\b)", re.I)
SERVICE = re.compile(r"Service Center", re.I)   # self-identified staffed center

# Island territories: addresses are sparse and each listed office is a real (often sole)
# center, so a missing street must NOT downgrade it to "outreach".
TERRITORIES = {"GU", "AS", "VI", "MP", "PW", "FM", "MH"}

def classify(name, is_lead=False, street="", state=""):
    name = name or ""
    if is_lead or LEAD.search(name):
        return "lead"
    if state in TERRITORIES:
        return "service"
    if SERVICE.search(name):            # names that self-identify as a service center
        return "service"
    # outreach / circuit-rider: hosted at a partner venue or a county satellite
    if PARTNER.search(name):
        return "outreach"
    if COUNTY.search(name) and not MAINISH.search(name):
        return "outreach"
    return "service"                    # default: a staffed service center
