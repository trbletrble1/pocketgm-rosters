#!/usr/bin/env python3
"""
nfl2k5 — read ESPN NFL 2K5 console gamesaves (Xbox SAVEGAME.DAT / bare .DAT).

Second backend for rosdump. Nothing here is shared with the Madden reader:
an Xtreme DB is a typed table container, a 2K5 save is a flat array of
fixed-length records with bit-packed fields. Only the CSV output matches.

Ported from BAD_AL's NFL2K5Tool (C#, github.com/BAD-AL/NFL2K5Tool), which is
the reason none of this had to be reverse-engineered.

FORMAT
------
Header:
    0x00  "ROST" (roster) — franchise saves use a different tag

Player records:
    fixed length 0x54 bytes, packed end to end. The first record is NOT at a
    fixed address (the C# tool scans for it too); we locate it by finding where
    eight consecutive records decode plausible names, then step back.

    +0x10  fname pointer (4 bytes, LE, self-relative: dest = loc + ptr - 1)
    +0x14  lname pointer
    +0x18  bit-packed: Turtleneck(6,7) Body(4,5) EyeBlack(3) Hand(2) Dreads(1)
    +0x19  DOB — and skin shares these bytes:
               skin = ((byte[0x19] & 0x0F) << 1) + (byte[0x18] >> 7)
    +0x20  jersey number
    +0x22  face  (value >> 1; a visor bit shares the byte)
    +0x25  years pro
    +0x29  depth
    +0x2A  weight, as 150 + value
    +0x2B  height in inches
    +0x35  position, then 11 ratings in order

Strings are UTF-16-ish: one ASCII byte every two bytes, NUL terminated.

SKIN
----
Values and their meaning are the tool author's own, from DebugDialog.cs where
he validates skin against face category. Not fitted by us:

    light      1, 9, 17
    mixed      2, 18   ("mixed White&black(light) guys, Samoans, Latino")
    dark       3, 4, 5, 6, 10, 11, 12, 13, 14, 19, 20, 21, 22

Skin3 is flagged "inconsistently assigned" in his comments. Value 2 and 18 are
the abstain bucket — the same shape as Madden's PSKI value 1, and they must not
be forced to a side.

Anchor-tested at 93.4% over 166 known players across the 1986, 1988, 1990 and
1996 community rosters.
"""
import string, re, csv, os, unicodedata, collections

PLAYER_LEN = 0x54

OFF = {
    'fname_ptr': 0x10, 'lname_ptr': 0x14, 'bodybits': 0x18, 'dob': 0x19,
    'jersey': 0x20, 'face': 0x22, 'years_pro': 0x25, 'depth': 0x29,
    'weight': 0x2A, 'height': 0x2B, 'position': 0x35,
}

RATINGS = ['Speed', 'Agility', 'PassArmStrength', 'Stamina', 'KickPower',
           'Durability', 'Strength', 'Jumping', 'Coverage', 'RunRoute', 'Tackle']

POSITIONS = ['QB', 'K', 'P', 'WR', 'CB', 'FS', 'SS', 'RB', 'FB', 'TE',
             'OLB', 'ILB', 'C', 'G', 'T', 'DE', 'DT', 'LB', 'ATH', 'LS']

SKIN_LIGHT = {1, 9, 17}
SKIN_MIXED = {2, 18}
SKIN_DARK = {3, 4, 5, 6, 10, 11, 12, 13, 14, 19, 20, 21, 22}

_NAME_OK = re.compile(r"^[A-Za-z][A-Za-z'\-. ]{1,14}$")


def plausible_name(s):
    return bool(s) and bool(_NAME_OK.match(s))


def norm(s):
    """Fold accents to ASCII, never strip them. Matches the project rule."""
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode()
    s = s.replace('-', ' ')
    s = re.sub(r"[.']", '', s)
    s = re.sub(r'[^A-Za-z ]', ' ', s).lower()
    return ' '.join(t for t in s.split()
                    if t not in ('jr', 'sr', 'ii', 'iii', 'iv', 'v'))


class Save:
    def __init__(self, path):
        self.path = path
        self.d = open(path, 'rb').read()
        self.magic = self.d[:4].decode('ascii', 'ignore')
        self.player_start = self._find_player_start()
        self.players = self._read_all() if self.player_start else []

    # ---- primitives -----------------------------------------------------
    def _ptr(self, loc):
        d = self.d
        p = (d[loc + 3] << 24) | (d[loc + 2] << 16) | (d[loc + 1] << 8) | d[loc]
        dest = loc + p - 1
        if not (0 <= dest < len(d)):
            raise ValueError('pointer out of range')
        return dest

    def _string(self, loc):
        out = []
        for i in range(loc, min(loc + 99, len(self.d)), 2):
            if self.d[i] == 0:
                break
            out.append(chr(self.d[i]))
        return ''.join(out)

    def _names(self, rec):
        b = rec + OFF['fname_ptr']
        return self._string(self._ptr(b)), self._string(self._ptr(b + 4))

    # ---- locating the player table --------------------------------------
    def _looks_like_run(self, start, n=8):
        good = 0
        for p in range(n):
            try:
                f, l = self._names(start + p * PLAYER_LEN)
            except Exception:
                return 0
            if plausible_name(f) and plausible_name(l):
                good += 1
        return good

    def _find_player_start(self):
        """The C# tool walks team pointers to find this. Scanning for where
        names decode is simpler and works on roster and franchise saves alike.
        Requires a full 8/8 run: 7/8 matches one record early, where the first
        name is blank, and every subsequent offset is then wrong."""
        hi = min(len(self.d) - 0x4000, 0x20000)
        for st in range(0x4000, hi, 4):
            if self._looks_like_run(st) == 8:
                # step back while both names stay plausible
                for _ in range(64):
                    prev = st - PLAYER_LEN
                    if prev < 0:
                        break
                    try:
                        f, l = self._names(prev)
                    except Exception:
                        break
                    if plausible_name(f) and plausible_name(l):
                        st = prev
                    else:
                        break
                return st
        return None

    # ---- record decoding -------------------------------------------------
    def _record(self, rec):
        d = self.d
        f, l = self._names(rec)
        pos = d[rec + OFF['position']]
        skin = ((d[rec + OFF['dob']] & 0x0F) << 1) + (d[rec + OFF['bodybits']] >> 7) + 1
        row = {
            'fname': f, 'lname': l,
            'position': POSITIONS[pos] if pos < len(POSITIONS) else f'?{pos}',
            'skin': skin,
            'skin_band': ('light' if skin in SKIN_LIGHT else
                          'dark' if skin in SKIN_DARK else
                          'mixed' if skin in SKIN_MIXED else 'unknown'),
            'face': d[rec + OFF['face']] >> 1,
            'jersey': d[rec + OFF['jersey']],
            'weight': 150 + d[rec + OFF['weight']],
            'height': d[rec + OFF['height']],
            'years_pro': d[rec + OFF['years_pro']],
            'depth': d[rec + OFF['depth']],
        }
        for i, name in enumerate(RATINGS):
            row[name] = d[rec + OFF['position'] + 1 + i]
        return row

    def _read_all(self):
        """Read forward to the end of the table. A record that will not decode
        is skipped, not a stop signal: these files carry placeholder rows and
        occasional bad pointers in the middle of real data. Stopping at the
        first one truncated several files to a third of their contents."""
        out, n, run = [], 0, 0
        while True:
            rec = self.player_start + n * PLAYER_LEN
            if rec + PLAYER_LEN > len(self.d):
                break
            try:
                f, l = self._names(rec)
                good = plausible_name(f) and plausible_name(l)
            except Exception:
                good = False
            if good and not self._placeholder(f, l):
                out.append(self._record(rec))
                run = 0
            else:
                run += 1
                if run > 400:            # a genuine wall, not a gap
                    break
            n += 1
        return out

    _POSCODES = set(POSITIONS)

    @staticmethod
    def _placeholder(f, l):
        """Unused roster slots hold things like ('DT', 'jaguars') rather than
        a person. A position code paired with a lowercase word is not a name."""
        return f.upper() in Save._POSCODES and l.islower()

    # ---- quality ---------------------------------------------------------
    def default_blocks(self, min_size=8):
        """Untouched records share an identical (position, weight, height).
        A modder edits the players who matter and leaves the rest at the
        template, so these carry no real appearance data."""
        grp = collections.Counter(
            (p['position'], p['weight'], p['height']) for p in self.players)
        return {k for k, c in grp.items() if c >= min_size}

    def edited(self):
        d = self.default_blocks()
        return [p for p in self.players
                if (p['position'], p['weight'], p['height']) not in d]


def write_csv(save, dest):
    rows = save.players
    if not rows:
        return 0
    cols = list(rows[0].keys())
    with open(dest, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def check(save):
    """Is this file worth using? Same question cmd_check answers for Madden."""
    lines, verdict = [], 'pass'
    P, E = save.players, save.edited()
    if not P:
        return ['no player records found — not a 2K5 roster save?'], 'FAILED'

    lines.append(f'players       {len(P)}')
    lines.append(f'hand-edited   {len(E)}  ({100*len(E)/len(P):.0f}%)')

    c = collections.Counter(p['skin'] for p in E)
    top, topn = (c.most_common(1)[0] if c else (0, 0))
    share = 100 * topn / len(E) if E else 0
    lines.append('skin          ' + '  '.join(f'{k}:{v}' for k, v in sorted(c.items())))

    bands = collections.Counter(p['skin_band'] for p in E)
    dark = bands['dark'] / max(1, bands['dark'] + bands['light'])
    lines.append(f'dark share    {100*dark:.0f}%   (real NFL runs ~60-70% in the modern era)')
    lines.append(f'abstain       {bands["mixed"]} on the mixed values 2 and 18')

    if share > 80:
        lines.append(f'FAIL: {share:.0f}% of edited players sit on skin {top} — the field is dead')
        verdict = 'FAILED'
    elif len(E) < 200:
        lines.append(f'FAIL: only {len(E)} hand-edited players — too little to source from')
        verdict = 'FAILED'
    elif not 0.35 <= dark <= 0.85:
        lines.append(f'WARN: dark share {100*dark:.0f}% is outside anything plausible')
        verdict = 'suspect'
    return lines, verdict
