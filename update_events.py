#!/usr/bin/env python3
"""Fetch Arthur Murray event calendar; fail closed if extraction is incomplete."""
import json,re,sys,datetime,calendar
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup

URL='https://www.arthurmurray.com/events/'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/events.json'
MONTHS={m.lower():i for i,m in enumerate(calendar.month_abbr) if m}
MONTHS.update({m.lower():i for i,m in enumerate(calendar.month_name) if m})


def extract_dates(text,year_hint=None):
    # Calendar listing date labels: 'Nov 19 - Nov 22' / 'Apr 24 - Apr 24'
    m=re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\s*[-–—]\s*(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(\d{1,2})(?:,?\s+(20\d{2}))?',text,re.I)
    if not m:return None
    now=datetime.datetime.now(datetime.timezone.utc).date()
    mon=MONTHS[m.group(1)[:3].lower()]; endmon=MONTHS[(m.group(3) or m.group(1))[:3].lower()]
    year=int(m.group(5) or year_hint or now.year)
    if not m.group(5) and not year_hint and (mon, int(m.group(2)))<(now.month,now.day):year+=1
    endyear=year+(endmon<mon)
    try:return (datetime.date(year,mon,int(m.group(2))).isoformat(),datetime.date(endyear,endmon,int(m.group(4))).isoformat())
    except ValueError:return None

def classify(name):
    n=name.lower()
    if 'superama' in n:return 'Superama'
    if 'world' in n and ('rama' in n or 'dance' in n):return 'World'
    return 'Dance-O-Rama'

def parse_calendar(html):
    soup=BeautifulSoup(html,'html.parser')
    events={}
    for h in soup.find_all(['h2','h3','h4']):
        name=h.get_text(' ',strip=True)
        if not name or len(name)>140:continue
        if not re.search(r'dance.o.rama|superama|beach.o.rama|holiday ball|perfect 10|osprey cup|world.*rama',name,re.I):continue
        a=h.find('a',href=True) or h.find_parent('a',href=True)
        if not a:continue
        url=urljoin(URL,a['href'])
        if '/am-events/' not in urlparse(url).path:continue
        parent=h
        dates=None
        for _ in range(5):
            if not parent.parent:break
            parent=parent.parent
            snippet=parent.get_text(' ',strip=True)
            if len(snippet)>3500:break
            dates=extract_dates(snippet)
            if dates:break
        if not dates:continue
        year_hint=re.search(r'\b20\d{2}\b',name)
        if year_hint and dates[0][:4]!=year_hint.group():
            dates=extract_dates(snippet,int(year_hint.group())) or dates
        events[url]={'name':name,'type':classify(name),'start':dates[0],'end':dates[1], 'city':'','venue':'','url':url}
    return list(events.values())

def detail_info(session,e):
    try:
        r=session.get(e['url'],timeout=20);r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        # Only take explicitly structured location information; no guessed cities.
        for s in soup.find_all('script',type='application/ld+json'):
            try: obj=json.loads(s.string or s.get_text())
            except (ValueError,TypeError):continue
            nodes=obj if isinstance(obj,list) else [obj]
            for node in nodes:
                if not isinstance(node,dict):continue
                if '@graph' in node:nodes+=node['@graph']
                if 'Event' not in str(node.get('@type','')):continue
                loc=node.get('location') or {}
                if isinstance(loc,list):loc=loc[0] if loc else {}
                if isinstance(loc,dict):
                    e['venue']=loc.get('name','')
                    address=loc.get('address') or {}
                    if isinstance(address,dict):e['city']=', '.join(filter(None,[address.get('addressLocality',''),address.get('addressRegion',''),address.get('addressCountry','')]))
        # Extract an explicit city/venue label when available
        for tag in soup.find_all(string=re.compile(r'^(Location|Venue|City):',re.I)):
            text=tag.parent.get_text(' ',strip=True)
            if len(text)<140:
                key,_,value=text.partition(':')
                if key.strip().lower()=='city' and not e['city']:e['city']=value.strip()
                if key.strip().lower() in ('venue','location') and not e['venue']:e['venue']=value.strip()
    except requests.RequestException:pass
    return e

def main():
    session=requests.Session();session.headers.update({'User-Agent':'AMGlobalConnectEvents/1.0 (+https://www.arthurmurray.com/events/)'})
    r=session.get(URL,timeout=35);r.raise_for_status()
    events=parse_calendar(r.text)
    if len(events)<5:raise RuntimeError(f'Only {len(events)} events extracted: preserving previous file')
    # Preserve previously known cities/venues only when exact URL matches.
    old={}
    if OUT.exists():
        try:old={e['url']:e for e in json.loads(OUT.read_text()).get('events',[])}
        except (ValueError,KeyError):pass
    for e in events:
        detail_info(session,e)
        if not e['city']:e['city']=old.get(e['url'],{}).get('city','')
        if not e['venue']:e['venue']=old.get(e['url'],{}).get('venue','')
    data={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':URL,'events':events}
    

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(OUT)


if __name__=='__main__':main()
