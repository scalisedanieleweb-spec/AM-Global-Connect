#!/usr/bin/env python3
"""Snapshot of official Arthur Murray locations. Never touches historical contacts.

Fail closed on incomplete or suspicious extraction. Run via GitHub Actions.
"""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

URL = 'https://www.arthurmurray.com/locations/'
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'official_studios.json'
GROUPS = ('United States', 'Canada', 'International')
MINIMUMS = {'United States': 120, 'Canada': 5, 'International': 5}


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def section_group(text):
    t = clean(text).lower()
    # The official site currently labels its h3 sections exactly as follows.
    labels = {
        'usa locations': 'United States',
        'united states studios': 'United States',
        'united states locations': 'United States',
        'canada locations': 'Canada',
        'canada studios': 'Canada',
        'international': 'International',
        'international studios': 'International',
        'international locations': 'International',
        'rest of the world': 'International',
    }
    return labels.get(t)


def external_link(tag):
    for a in tag.find_all('a', href=True):
        href = urljoin(URL, a['href'])
        parsed = urlparse(href)
        if parsed.scheme == 'https' and parsed.netloc and 'arthurmurray.com' not in parsed.netloc.lower():
            return href
        if parsed.scheme == 'https' and '/locations/' not in parsed.path and parsed.netloc:
            return href
    return ''


def parse_card(tag, group):
    title_tag = tag.find(re.compile(r'^h[2-6]$'))
    if not title_tag:
        title_tag = tag.find(['strong', 'b'])
    name = clean(title_tag.get_text(' ', strip=True)) if title_tag else ''
    if not name:
        a = tag.find('a', href=True)
        if a:
            name = clean(a.get_text(' ', strip=True))
    if not name or len(name) > 90 or section_group(name):
        return None
    if name.lower() in ('new', 'coming soon', 'website', 'view website', 'directions', 'contact'):
        return None

    address_tag = tag.find(class_=re.compile(r'address|location-address|studio-address', re.I))
    if not address_tag:
        address_tag = tag.find('address')
    address = clean(address_tag.get_text(' ', strip=True)) if address_tag else clean(tag.get_text(' ', strip=True))
    if address.lower().startswith(name.lower()):
        address = clean(address[len(name):])
    else:
        address = clean(re.sub(re.escape(name), '', address, count=1, flags=re.I))
    address = re.sub(r'\b(?:New|Coming Soon)\b\s*$', '', address, flags=re.I).strip()
    if not 12 <= len(address) <= 260 or not re.search(r'\d', address):
        return None
    if len(tag.find_all(re.compile(r'^h[2-6]$'))) > 1:
        return None
    link = external_link(tag)
    key = hashlib.sha256((group + '|' + name.casefold()).encode()).hexdigest()[:16]
    return {'id': key, 'name': name, 'address': address, 'region': group, 'url': link}


def extract(html):
    soup = BeautifulSoup(html, 'html.parser')
    for el in soup(['script', 'style', 'noscript', 'svg']):
        el.decompose()
    headings = [(h, section_group(h.get_text(' ', strip=True)))
                for h in soup.find_all(re.compile(r'^h[1-6]$'))]
    sections = [(h, group) for h, group in headings if group]
    seen = set()
    sections = [(h, group) for h, group in sections if not (group in seen or seen.add(group))]
    if set(group for _, group in sections) != set(GROUPS):
        raise RuntimeError('Missing official location sections; previous snapshot preserved')

    records = {}
    for idx, (heading, group) in enumerate(sections):
        stop = sections[idx + 1][0] if idx + 1 < len(sections) else None
        for element in heading.next_elements:
            if element is stop:
                break
            if not isinstance(element, Tag):
                continue
            if element.name not in ('div', 'li', 'article', 'a'):
                continue
            if element.find(re.compile(r'^h[2-6]$')) is None and element.name != 'a':
                continue
            if len(element.find_all(re.compile(r'^h[2-6]$'))) > 1:
                continue
            if len(clean(element.get_text(' ', strip=True))) > 450:
                continue
            result = parse_card(element, group)
            if result:
                old = records.get(result['id'])
                if not old or len(result['address']) < len(old['address']):
                    records[result['id']] = result

    studios = sorted(records.values(), key=lambda r: (r['region'], r['name'].casefold()))
    counts = {g: sum(x['region'] == g for x in studios) for g in GROUPS}
    print(f'Extracted studio counts: {counts}; total={len(studios)}', flush=True)
    if any(counts[g] < MINIMUMS[g] for g in GROUPS):
        raise RuntimeError(f'Incomplete official directory: {len(studios)} records {counts}; previous snapshot preserved')
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding='utf-8'))
            previous_count = len(previous.get('studios', []))
            if previous_count and len(studios) < previous_count * 0.75:
                raise RuntimeError(f'Suspicious drop {previous_count} -> {len(studios)}; previous snapshot preserved')
        except (ValueError, OSError):
            raise RuntimeError('Existing snapshot unreadable; refusing overwrite')
    return studios, counts


def main():
    response = requests.get(URL, timeout=45, headers={'User-Agent': 'Mozilla/5.0 (compatible; AMGlobalConnectDirectory/2.0)'})
    response.raise_for_status()
    studios, counts = extract(response.text)
    payload = {
        'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'source': URL,
        'count': len(studios),
        'counts': counts,
        'studios': studios,
    }
    temp = OUT.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(OUT)
    print(f'Official directory updated: {len(studios)} studios; {counts}')


if __name__ == '__main__':
    main()
