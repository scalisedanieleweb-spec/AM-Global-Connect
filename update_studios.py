#!/usr/bin/env python3
"""Conservative official studio snapshot. Never modifies private historical contacts."""
import datetime
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

URL = 'https://www.arthurmurray.com/locations/'
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'official_studios.json'


def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def extract(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Locate named country sections; only accept linked location records with addresses.
    headings = soup.find_all(re.compile('^h[1-6]$'))
    sections = []
    for h in headings:
        title = clean(h.get_text(' ', strip=True)).lower()
        if any(x in title for x in ('usa locations', 'united states studios', 'canada locations', 'canada studios', 'international', 'rest of the world')):
            country_group = ('United States' if 'usa' in title or 'united states' in title else
                             'Canada' if 'canada' in title else 'International')
            sections.append((h, country_group))
    if len({g for _, g in sections}) < 3:
        raise RuntimeError('Official page sections missing; previous snapshot preserved')
    records = {}
    for index, (heading, group) in enumerate(sections):
        stop = sections[index+1][0] if index+1 < len(sections) else None
        for sibling in heading.next_elements:
            if sibling is stop:
                break
            if getattr(sibling, 'name', None) != 'a' or not sibling.get('href'):
                continue
            href = urljoin(URL, sibling['href'])
            if not href.startswith('https://') or 'arthurmurray.com' not in href:
                continue
            name = clean(sibling.get_text(' ', strip=True))
            if not name or len(name) > 100 or name.lower() in ('learn more','contact','directions','website','view studio'):
                continue
            parent = sibling.parent
            address = clean(parent.get_text(' ', strip=True)) if parent else ''
            if len(address) > 300 or len(address) < len(name) + 12 or not re.search(r'\d', address):
                continue
            address = clean(address.replace(name, '', 1))
            if not address or len(address) > 220:
                continue
            key = hashlib.sha256((group+'|'+name.lower()+'|'+href).encode()).hexdigest()[:16]
            records[key] = {'id':key,'name':name,'address':address,'region':group,'url':href}
    data = sorted(records.values(), key=lambda x:(x['region'],x['name'].lower()))
    counts = {g:sum(x['region']==g for x in data) for g in ('United States','Canada','International')}
    if len(data) < 150 or min(counts.values()) < 5:
        raise RuntimeError(f'Only {len(data)} studio records extracted ({counts}); preserving previous snapshot')
    return data


def main():
    session = requests.Session()
    session.headers['User-Agent'] = 'AMGlobalConnectOfficialDirectory/1.0'
    response = session.get(URL, timeout=40)
    response.raise_for_status()
    studios = extract(response.text)
    payload = {'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source':URL,'count':len(studios),'studios':studios}
    tmp = OUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(OUT)
    print(f'Official directory updated: {len(studios)} studios')

if __name__=='__main__':
    main()
