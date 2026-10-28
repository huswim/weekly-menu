#!/usr/bin/env python3
"""Download and validate the education center's weekly menu PDFs."""
import datetime as dt
import hashlib
import html
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent / 'dist'
BOARD = 'https://www.mma.go.kr/educenter/board/boardList.do?mc=mma0001927&gesipan_id=230'
ORIGIN = 'https://www.mma.go.kr'
DATE = re.compile(r'(20\d\d)\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*\.?\s*[~～-]\s*(?:(20\d\d)\s*[.\-/]\s*)?(\d{1,2})\s*[.\-/]\s*(\d{1,2})')
ALLERGENS = {'난류','우유','메밀','땅콩','대두','밀','고등어','게','새우','돼지고기','복숭아','토마토','아황산류','호두','닭고기','쇠고기','오징어','조개류','잣'}

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 weekly-menu/1.0'})
    with urllib.request.urlopen(req, timeout=40) as response:
        return response.read()

def posts(markup):
    for href, title in re.findall(r'<a\s+href="([^"]*boardView\.do\?[^"]+)"[^>]*>(.*?)</a>', markup, re.S):
        title = re.sub(r'<[^>]+>', '', html.unescape(title)).strip()
        match = DATE.search(title)
        if '식단표' not in title or not match:
            continue
        y, m, d, ey, em, ed = match.groups()
        start = dt.date(int(y), int(m), int(d))
        endyear = int(ey) if ey else int(y) + (int(em) < int(m))
        end = dt.date(endyear, int(em), int(ed))
        if start <= end and (end - start).days <= 6:
            yield start, end, urllib.parse.urljoin(BOARD, html.unescape(href))

def parse_pdf(blob, start, end):
    if not blob.startswith(b'%PDF-'):
        raise ValueError('Attachment is not a PDF')
    reader = PdfReader(io.BytesIO(blob))
    days = []
    for page in reader.pages[1:]:
        text = page.extract_text()
        heading = re.search(r'(\d{1,2})\s*/\s*(\d{1,2})\s*\(([월화수목금])\).*?알레르기', text)
        if not heading:
            continue
        month, day = map(int, heading.group(1, 2))
        candidates = [start + dt.timedelta(days=n) for n in range((end-start).days+1)]
        date = next((d for d in candidates if (d.month,d.day)==(month,day)), None)
        if not date or '월화수목금'[date.weekday()] != heading.group(3):
            raise ValueError('PDF date does not match post')
        sections = {k: [] for k in ('조식','중식A','중식B','석식A','석식B')}
        section = None
        body = text.split('구분 메뉴', 1)[-1].split('알레르기 유발물질이 포함', 1)[0]
        for line in body.splitlines():
            line = line.strip()
            if not line or line == '알레르기': continue
            found = re.match(r'^(조식|중식\s*[AB]|석식\s*[AB])\s*', line)
            if found:
                section = found.group(1).replace(' ', '')
                line = line[found.end():].strip()
            if not section or not line: continue
            parts = re.split(r'\s+', line, maxsplit=1)
            name = parts[0]
            allergy = parts[1].strip() if len(parts)>1 else ''
            if allergy and not all(x.strip() in ALLERGENS for x in allergy.split(',')):
                raise ValueError(f'Unrecognized PDF row: {line}')
            sections[section].append({'name':name, 'allergy':allergy})
        meals=[]
        for n in ('조식','중식','석식'):
            keys = [n] if n == '조식' else [n+'A',n+'B']
            limit = 5 if n == '조식' else 6
            corners = [{'label':'한식 메뉴' if n=='조식' else key[-1]+' 코너', 'items':[x for x in sections[key][:limit] if x['name'] != '-']} for key in keys if any(x['name'] != '-' for x in sections[key][:limit])]
            extra = [x for key in keys for x in sections[key][limit:] if x['name'] != '-' and not x['name'].startswith(('건강음료/', '그린샐러드&'))]
            meals.append({'corners':corners,'extra':extra,'allergy':[x for x in sum((sections[k] for k in keys),[]) if x['name'] != '-']})
        days.append({'day':heading.group(3),'date':date.isoformat(),'meals':meals})
    expected = [start+dt.timedelta(days=n) for n in range((end-start).days+1) if (start+dt.timedelta(days=n)).weekday()<5]
    if [d['date'] for d in days] != [d.isoformat() for d in expected] or not any(m['corners'] for d in days for m in d['meals']):
        raise ValueError('PDF pages are incomplete or out of order')
    return days

def main():
    now = dt.datetime.now(ZoneInfo('Asia/Seoul')).date()
    monday = now - dt.timedelta(days=now.weekday())
    allowed = {monday, monday+dt.timedelta(days=7)}
    index_path = ROOT/'weeks.json'
    index = json.loads(index_path.read_text())
    index['weeks'] = [w for w in index['weeks'] if dt.date.fromisoformat(w['start']) + dt.timedelta(days=6) >= monday]
    found = False
    for start, end, url in posts(fetch(BOARD).decode('utf-8')):
        week = start-dt.timedelta(days=start.weekday())
        if week not in allowed: continue
        found = True
        detail = fetch(url).decode('utf-8')
        match = re.search(r'href="([^"]*boardFileDown\.do\?[^"]+)"[^>]*>\s*<img[^>]+(?:pdf|PDF)', detail, re.S)
        if not match: raise ValueError(f'No PDF attachment: {url}')
        blob = fetch(urllib.parse.urljoin(ORIGIN, html.unescape(match.group(1))))
        digest = hashlib.sha256(blob).hexdigest()
        existing = next((w for w in index['weeks'] if w['start']==week.isoformat()), None)
        if existing and existing.get('sha256')==digest: continue
        days = parse_pdf(blob, start, end)
        file = f'assets/menu-{week.isoformat()}.pdf'
        (ROOT/file).write_bytes(blob)
        entry={'start':week.isoformat(),'end':end.isoformat(),'days':days,'source':url,'pdf':file,'sha256':digest}
        index['weeks'] = [w for w in index['weeks'] if w['start']!=entry['start']] + [entry]
    if not found: raise ValueError('No current or upcoming week found on the board')
    index['weeks'].sort(key=lambda w:w['start'])
    index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    referenced = {w['pdf'] for w in index['weeks']}
    for path in (ROOT/'assets').glob('menu-*.pdf'):
        if str(path.relative_to(ROOT)) not in referenced: path.unlink()

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(f'Menu update failed: {exc}', file=sys.stderr)
        sys.exit(1)
