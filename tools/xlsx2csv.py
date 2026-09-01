#!/usr/bin/env python3
"""Minimal stdlib xlsx -> csv. No third-party deps (project rule: tools run from a clean clone)."""
import zipfile, csv, sys, re
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def col_to_idx(ref):
    m = re.match(r'([A-Z]+)', ref)
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1

def read(path):
    z = zipfile.ZipFile(path)
    # shared strings
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        root = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in root.findall(NS + 'si'):
            shared.append(''.join(t.text or '' for t in si.iter(NS + 't')))
    # first sheet
    names = [n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n)]
    names.sort()
    rows = []
    root = ET.fromstring(z.read(names[0]))
    for row in root.iter(NS + 'row'):
        cells = {}
        for c in row.findall(NS + 'c'):
            ref = c.get('r'); t = c.get('t')
            v = c.find(NS + 'v'); isn = c.find(NS + 'is')
            if t == 's' and v is not None:
                val = shared[int(v.text)]
            elif t == 'inlineStr' and isn is not None:
                val = ''.join(x.text or '' for x in isn.iter(NS + 't'))
            elif v is not None:
                val = v.text
            else:
                val = ''
            cells[col_to_idx(ref)] = val
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, '') for i in range(width)])
    return rows, len(names)

if __name__ == '__main__':
    rows, nsheets = read(sys.argv[1])
    w = max(len(r) for r in rows)
    with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f)
        for r in rows:
            wr.writerow(r + [''] * (w - len(r)))
    print(f'sheets={nsheets} rows={len(rows)} cols={w} -> {sys.argv[2]}')
