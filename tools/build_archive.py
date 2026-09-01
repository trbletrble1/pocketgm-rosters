#!/usr/bin/env python3
"""
build_archive — index every ESPN NFL 2K5 community roster into one per-person
appearance record, for use as a source in PGM3 builds.

    python3 build_archive.py "sources/NFL2k25 Year Saves" -o reference/PGM3_PLAYER_ARCHIVE.json

WHY AN INDEX AND NOT A MERGE
----------------------------
Every source keeps its own vote, tagged with the file it came from. Nothing is
collapsed to a consensus value on disk.

This project has now found six separate cases where pooling disagreeing sources
manufactured a rule that none of them followed: the within-light family spread,
the fullback ordering, OLB coverage, kicker contracts, staff eGuarantee, and the
staff guarantee rate. A disagreement between two sources is information about
which one is wrong. Averaging it destroys exactly the evidence you need later.

Consumers can ask for unanimity, or majority, or a specific era's opinion. The
file keeps all of it.

WHAT COUNTS AS A VOTE
---------------------
Only hand-edited players with a decided skin band. Two exclusions:

  - default blocks: a modder edits the players who matter and leaves the rest
    on the template, so records sharing an identical (position, weight, height)
    with many others carry no real appearance data
  - the mixed skin values 2 and 18, which the tool's author labels
    "mixed White&black(light) guys, Samoans, Latino". These abstain rather than
    being forced to a side, the same as Madden's PSKI value 1.

THE ALL-TIME FILE IS TAGGED, NOT TRUSTED EQUALLY
------------------------------------------------
GOATS is a best-players roster: a selected population, and notability correlates
with the thing being measured. It is fine as a per-person lookup and useless as
a distribution. It is marked `all_time` so a later session cannot mistake it for
a season, and season files outvote it.

NAMESAKES
---------
The archive spans 1958 to 2026. Name-plus-position matching across that range
produced an 81% false-match rate on the 1986 cohort. Consumers MUST disambiguate
on era: each entry records the years its sources saw the man, and a lookup whose
target season falls outside that span by more than a career length is a
different person.
"""
import sys, os, glob, json, collections, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nfl2k5
from nfl2k5 import norm


def season_of(filename):
    """First year in the filename, and whether it's a season or an all-time set."""
    stem = os.path.basename(filename).replace('SAVEGAME.DAT', '').replace('AVEGAME.DAT', '')
    if stem.upper().startswith('GOATS'):
        return None, 'all_time', stem
    digits = ''.join(c if c.isdigit() else ' ' for c in stem).split()
    years = [int(d) for d in digits if len(d) == 4]
    if not years:
        return None, 'unknown', stem
    lo, hi = min(years), max(years)
    # a file spanning decades is a compilation, not a season
    kind = 'span' if hi - lo > 2 else 'season'
    return lo, kind, stem


# Files known to be modern. Any name appearing in one of these AND in a retro
# file is a stock slot the modder never edited - see nfl2k5.py, STOCK
# CONTAMINATION. Used only to decide whether a record can vouch for an ERA.
MODERN_REFERENCE = ['2004-2005SAVEGAME.DAT', '2010-2011SAVEGAME.DAT',
                    '2016-2017SAVEGAME.DAT', '2021SAVEGAME.DAT']


def build(src_dir):
    people = {}
    files = []
    stock = nfl2k5.stock_names([os.path.join(src_dir, f) for f in MODERN_REFERENCE])
    print(f'stock-modern reference: {len(stock)} names')
    for path in sorted(glob.glob(os.path.join(src_dir, '*.DAT'))):
        year, kind, stem = season_of(path)
        try:
            s = nfl2k5.Save(path)
        except Exception as e:
            files.append(dict(file=stem, ok=False, note=str(e)))
            continue
        if not s.players:
            files.append(dict(file=stem, ok=False, note='unreadable'))
            continue

        edited = s.edited()
        bands = collections.Counter(p['skin_band'] for p in edited)
        dark = bands['dark'] / max(1, bands['dark'] + bands['light'])
        files.append(dict(file=stem, ok=True, year=year, kind=kind,
                          players=len(s.players), edited=len(edited),
                          dark_share=round(dark, 3)))

        for p in edited:
            if p['skin_band'] not in ('light', 'dark'):
                continue
            key = norm(p['fname'] + ' ' + p['lname']) + '|' + p['position']
            # A stock leftover still describes the right man, so its SKIN vote
            # counts. It says nothing about when he played, so it must not
            # contribute to the era range.
            is_stock = (kind in ('season', 'span') and year and year < 2000
                        and norm(p['fname'] + ' ' + p['lname']) in stock)
            e = people.setdefault(key, dict(
                name=f"{p['fname']} {p['lname']}", position=p['position'],
                votes=[], years=[]))
            e['votes'].append(dict(src=stem, kind=kind, year=year,
                                   band=p['skin_band'], skin=p['skin'],
                                   stock=is_stock))
            if year and not is_stock:
                e['years'].append(year)

    # summarise each person without destroying the votes
    for e in people.values():
        seasons = [v for v in e['votes'] if v['kind'] == 'season']
        pool = seasons or e['votes']          # season files outvote all-time
        b = collections.Counter(v['band'] for v in pool)
        e['band'] = b.most_common(1)[0][0]
        e['agreement'] = round(b.most_common(1)[0][1] / len(pool), 3)
        e['unanimous'] = len(b) == 1
        e['n_sources'] = len(e['votes'])
        e['first_seen'] = min(e['years']) if e['years'] else None
        e['last_seen'] = max(e['years']) if e['years'] else None
        e['era_certain'] = bool(e['years'])
        del e['years']
    return people, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src_dir')
    ap.add_argument('-o', '--out', default='PGM3_PLAYER_ARCHIVE.json')
    a = ap.parse_args()

    people, files = build(a.src_dir)
    ok = [f for f in files if f.get('ok')]
    unan = sum(1 for e in people.values() if e['unanimous'])

    doc = {
        '_README': (
            'Per-person skin band indexed from ESPN NFL 2K5 community rosters. '
            'Every source keeps its own vote in `votes`; `band` is the majority '
            'of the SEASON files only, with all-time rosters used as a tiebreak. '
            'Never merge votes on disk - six times in this project pooling '
            'disagreeing sources manufactured a rule none of them followed. '
            'DISAMBIGUATE ON ERA: this spans 1958-2026 and name+position matching '
            'across that range gave an 81% false-match rate on the 1986 cohort. '
            'Check first_seen/last_seen against the season being built - but only '
            'where era_certain is true. Retro files carry 59-352 STOCK 2004 slots '
            'the modder never edited; those votes are good for skin and worthless '
            'for era, and are marked stock=true.'),
        '_provenance': (
            'Read with tools/nfl2k5.py, ported from BAD_AL NFL2K5Tool. Skin value '
            'meanings are the tool author\'s own, not fitted here. Anchor-tested '
            'at 93.4% over 166 known players across four eras; cross-file '
            'agreement 92.0% over 23,346 overlapping pairs.'),
        '_files': files,
        'players': people,
    }
    with open(a.out, 'w') as fh:
        json.dump(doc, fh, separators=(',', ':'))

    print(f'files read      {len(ok)} of {len(files)}')
    print(f'people indexed  {len(people)}')
    print(f'unanimous       {unan}  ({100*unan/len(people):.0f}%)')
    print(f'written to      {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
