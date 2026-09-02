#!/usr/bin/env python3
"""rfm.py — read appearance data out of a Realistic Franchise Mod CAREER file.

    python3 rfm.py dump  sources/madden/CAREER-RFM -o wip/rfm_faces.csv
    python3 rfm.py probe  sources/madden/CAREER-RFM
    python3 rfm.py anchor sources/madden/CAREER-RFM wip/rfm_faces.csv < anchors.csv

Format, as supplied and verified here:

    FBCHUNKS container. A single zlib stream begins at offset 82 and
    decompresses to ~20MB. Player records carry a genericHeadName of the form

        gen_<skin>_<ethnicity>_<features>_<id>

    Field 1 is skin tone, 1-7. The head code is null-padded, followed by the
    surname, then a composite key "<Surname><Forename>_<numeric id>" which is
    what this reader uses for identity -- the standalone name fields around it
    belong to neighbouring records and reading those instead shifts every name
    by one player.

    1 to 2 = light, 4 to 7 = dark, 3 = ABSTAIN. The middle band is not a
    verdict and is never emitted as one.

SOURCE: Realistic Franchise Mod (RFM), a community Madden 27 mod. Same class
of source as the 2K5 community rosters -- a work in progress whose accuracy
varies with how much attention a given player got. Pin and date what you take
from it; see PGM3_DATA_SOURCES.md.
"""
import re, sys, csv, zlib, json, os, hashlib, datetime

# ethnicity and features are multi-letter for some players (BMH, BD, MG, S).
# A single-letter pattern silently matched only 2,028 of 3,070 head codes.
HEAD = re.compile(rb'gen_(\d)_([A-Z]+)_([A-Z]+)_(\d+)')
NAME = re.compile(rb'([A-Za-z\'\-\. ]{2,40})([A-Za-z\'\-\. ]{2,30})_(\d+)\x00')

def decompress(path):
    raw = open(path, 'rb').read()
    if raw[:8] != b'FBCHUNKS':
        raise SystemExit(f'{path}: not an FBCHUNKS container')
    return zlib.decompressobj().decompress(raw[82:]), raw

def band(skin):
    """1-2 light, 4-7 dark, 3 abstains. Returns None for the middle band."""
    if skin in (1, 2): return 'light'
    if skin >= 4:      return 'dark'
    return None

def records(dec):
    """Yield (skin, ethnicity, features, headid, surname, forename, playerid)."""
    for m in HEAD.finditer(dec):
        skin = int(m.group(1))
        # the composite key sits after the head code and the padded surname
        win = dec[m.end():m.end() + 220]
        parts = [p for p in win.split(b'\x00') if p]
        if len(parts) < 2: continue
        surname = parts[0].decode('latin-1', 'replace').strip()
        # The composite strips punctuation and spaces from the surname
        # ("Alie-Cox" -> "AlieCoxMo_13872"), so compare on letters only --
        # matching raw dropped every hyphenated and suffixed name, 207 of them.
        def letters(x): return ''.join(ch for ch in x if ch.isalpha()).lower()
        key = letters(surname)
        comp = None
        for p in parts[1:5]:
            s = p.decode('latin-1', 'replace')
            if '_' in s and key and letters(s).startswith(key):
                comp = s; break
        if not comp: continue
        stem, _, pid = comp.rpartition('_')
        if not pid.isdigit(): continue
        forename = stem[len(letters(surname)):].strip() if letters(stem).startswith(key) else ''
        # walk back to the real boundary: stem is <surname-without-punct><forename>
        n = 0; si = 0
        while si < len(stem) and n < len(key):
            if stem[si].isalpha(): n += 1
            si += 1
        forename = stem[si:].strip()
        if not forename: continue
        yield (skin, m.group(2).decode(), m.group(3).decode(),
               m.group(4).decode(), surname, forename, pid)

def cmd_dump(path, out):
    dec, raw = decompress(path)
    rows = list(records(dec))
    seen, uniq = set(), []
    for r in rows:
        if r[6] in seen: continue
        seen.add(r[6]); uniq.append(r)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['forename', 'surname', 'player_id', 'skin', 'band',
                    'ethnicity', 'features', 'head_id'])
        for skin, eth, feat, hid, sur, fore, pid in uniq:
            w.writerow([fore, sur, pid, skin, band(skin) or 'abstain', eth, feat, hid])
    print(f'{len(uniq)} players -> {out}')
    prov = {'source': 'Realistic Franchise Mod (RFM) CAREER file',
            'file': os.path.basename(path),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'decompressed': len(dec),
            'players': len(uniq),
            'extracted': datetime.date.today().isoformat(),
            'note': 'community mod, work in progress; accuracy varies by player'}
    with open(os.path.splitext(out)[0] + '_provenance.json', 'w') as f:
        json.dump(prov, f, indent=2)
    print('provenance:', prov['sha256'][:16], prov['extracted'])

def cmd_probe(path):
    dec, _ = decompress(path)
    import collections
    c = collections.Counter(); n = 0
    for skin, *_ in records(dec):
        c[skin] += 1; n += 1
    print(f'{n} records; skin tone distribution:')
    for k in sorted(c): print(f'   {k}: {c[k]:5d}  {band(k) or "ABSTAIN"}')

def present(dec, forename, surname):
    """EXISTENCE ASSERTION. Before an anchor is scored as a MISS, confirm the
    name is actually in the source: a name that is absent scores as a
    disagreement and makes a good source look worse than it is.

    This is the third false-join class in the build -- after Chris Jones cloned
    onto a Cincinnati rookie and Christian Jones cross-claimed between passes.
    Returns True only if the composite <surname><forename>_<id> is really
    there, compared on letters so punctuation and case cannot fake a miss.
    """
    key = ''.join(c for c in (surname + forename) if c.isalpha()).lower()
    return key.encode() in _flat(dec)

_FLAT = {}
def _flat(dec):
    if 'v' not in _FLAT:
        _FLAT['v'] = bytes(c for c in dec.lower() if 97 <= c <= 122 or 48 <= c <= 57)
    return _FLAT['v']

def cmd_anchor(path, csvpath):
    """Score anchors, separating ABSENT from DISAGREE."""
    dec, _ = decompress(path)
    got = {}
    for r in csv.DictReader(open(csvpath, encoding='utf-8')):
        got[(r['forename'].lower(), r['surname'].lower())] = r['band']
    ag = dis = absent = ab = 0
    for r in csv.DictReader(sys.stdin):
        k = (r['forename'].lower(), r['surname'].lower())
        if not present(dec, r['forename'], r['surname']): absent += 1; continue
        b = got.get(k)
        if b is None or b == 'abstain': ab += 1; continue
        if b == r['band']: ag += 1
        else:
            dis += 1
            print(f"   DISAGREE {r['forename']} {r['surname']}: expected {r['band']}, RFM {b}")
    n = ag + dis
    print(f'agree {ag}  disagree {dis}  rate {ag/n:.1%}' if n else 'no scorable anchors')
    print(f'   not in the source at all: {absent}   abstain band: {ab}')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'dump':
        out = sys.argv[sys.argv.index('-o') + 1] if '-o' in sys.argv else 'wip/rfm_faces.csv'
        cmd_dump(sys.argv[2], out)
    elif cmd == 'probe': cmd_probe(sys.argv[2])
    elif cmd == 'anchor': cmd_anchor(sys.argv[2], sys.argv[3])
    else: print(__doc__); sys.exit(2)
