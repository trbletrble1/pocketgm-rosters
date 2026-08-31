#!/usr/bin/env python3
"""
rosdump — read Madden .ros / .dbt roster files without Windows.

Pure Python 3, standard library only. Nothing to install.

    python3 rosdump.py tables FILE.ros
    python3 rosdump.py dump   FILE.ros PLAY -o play.csv
    python3 rosdump.py dump   FILE.ros COCH -o coch.csv
    python3 rosdump.py check  FILE.ros

The point of `check` is to answer, in about a second, the question that
otherwise costs a trip to the Windows machine: is this file worth using?
See docs/PGM3_SOURCE_QUALITY.md — seven of seventeen files we already hold
carry no usable skin signal, and three of those had been trusted for months.

FORMAT
------
Container:
    0x00  "DB" magic
    0x10  uint32  table count
    0x18  table directory, 8 bytes each: 4-char tag + uint32 offset,
          relative to the end of the directory

Table header (at the resolved offset):
    +0x00 uint32  hash
    +0x04 uint32  version (6 in everything seen so far)
    +0x08 uint32  record length in BYTES (bits rounded up)
    +0x0c uint32  record length in BITS
    +0x14 uint16  allocated capacity
    +0x16 uint16  records actually used
    +0x1c uint32  field count
    +0x30 field definitions, 16 bytes each:
              4-char tag, uint32 bit width, uint32 type, uint32 bit offset

Records follow the field definitions, packed to `record length` bits each.

Field layouts differ between game years, which is why this reads the schema
out of each file rather than hardcoding offsets. The handoff records PSKI at
bit 402; the template shipped with Xtreme DB Editor puts it at 613. Both are
right, for their own file.
STATUS
------
The container, table directory, record counts, field names and widths are
verified correct against Xtreme DB Editor's own CSV exports.

Record decoding is INCOMPLETE. 47 of 108 numeric PLAY fields and 34 of 67 COCH
fields decode exactly; the rest do not, because the bit offset in the field
definition is close to but not exactly the real offset (deltas of -8..+6 bits).
See docs/PGM3_TASK_ros_decoder.md and reference/ros_solved_offsets.json.

`tables` is reliable today. `dump` and `check` are not, until that is finished.
"""
import sys, os, csv, struct, collections

# Fields that hold text rather than a number. The `type` word in the field
# definition does NOT separate them — CLNA and PSKI are both type 3 — so this
# is a width heuristic plus an explicit list of the ones that matter.
KNOWN_STRINGS = {
    'PFNA','PLNA','CLNA','CFNA','TLNA','TSNM','TDNA','CTNA','SNAM','PNAM',
}

def _is_string(tag, bits):
    return tag in KNOWN_STRINGS or (bits >= 32 and bits % 8 == 0)


class Table:
    # Record data begins 8 bytes BEFORE the end of the field definitions.
    # Confirmed independently for PLAY and COCH in 2020ROJOROSTER_V22.ros.
    # The -8 is not yet understood; the value is right.
    DATA_START_ADJUST = -8

    def __init__(self, tag, buf, off):
        self.tag = tag
        self.buf = buf
        self.off = off
        self.record_bytes = struct.unpack_from('<I', buf, off + 0x08)[0]
        self.record_bits  = struct.unpack_from('<I', buf, off + 0x0c)[0]
        self.capacity     = struct.unpack_from('<H', buf, off + 0x14)[0]
        self.record_count = struct.unpack_from('<H', buf, off + 0x16)[0]
        self.field_count  = struct.unpack_from('<I', buf, off + 0x1c)[0]
        self.fields = []
        self.bad_fields = []
        for i in range(self.field_count):
            o = off + 0x30 + i * 16
            tag4 = buf[o:o+4].decode('latin-1').strip('\x00')
            bits, typ, bitoff = struct.unpack_from('<3I', buf, o + 4)
            # Guard: real files contain occasional corrupt definitions —
            # 2020ROJOROSTER_V22 has a PFEx entry with offset 1867645653.
            # Skip anything that cannot fit inside a record.
            if bitoff + bits > self.record_bytes * 8:
                self.bad_fields.append(tag4)
                continue
            self.fields.append({'tag': tag4, 'bits': bits, 'type': typ,
                                'offset': bitoff, 'str': _is_string(tag4, bits)})
        self.data_off = off + 0x30 + self.field_count * 16 + self.DATA_START_ADJUST
        self.fields.sort(key=lambda f: f['offset'])

    def _bits(self, rec_i, bitoff, nbits, msb_first=True):
        base = self.data_off * 8 + rec_i * self.record_bytes * 8 + bitoff
        v = 0
        for i in range(nbits):
            p = base + i
            byte = self.buf[p >> 3]
            bit = (byte >> (7 - (p & 7))) & 1 if msb_first else (byte >> (p & 7)) & 1
            v = (v << 1) | bit
        return v

    def read(self, rec_i, msb_first=True):
        out = {}
        for f in self.fields:
            raw = self._bits(rec_i, f['offset'], f['bits'], msb_first)
            if f['str']:
                b = raw.to_bytes(f['bits'] // 8, 'big')
                out[f['tag']] = b.split(b'\x00')[0].decode('latin-1', 'replace').strip()
            else:
                out[f['tag']] = raw
        return out

    def rows(self, limit=None, msb_first=True):
        n = self.record_count if limit is None else min(limit, self.record_count)
        for i in range(n):
            yield self.read(i, msb_first)


class Roster:
    def __init__(self, path):
        with open(path, 'rb') as fh:
            self.buf = fh.read()
        if self.buf[:2] != b'DB':
            raise ValueError(f'{path}: not a TDB file (expected "DB" magic, got '
                             f'{self.buf[:2]!r}). If this came from a zip, unzip it first.')
        self.path = path
        n = struct.unpack_from('<I', self.buf, 0x10)[0]
        base = 0x18 + n * 8
        self.tables = {}
        for i in range(n):
            o = 0x18 + i * 8
            tag = self.buf[o:o+4].decode('latin-1').strip('\x00')
            rel = struct.unpack_from('<I', self.buf, o + 4)[0]
            self.tables[tag] = base + rel

    def table(self, tag):
        if tag not in self.tables:
            raise KeyError(f'{tag} not in {self.path}. Present: {", ".join(sorted(self.tables))}')
        return Table(tag, self.buf, self.tables[tag])


def load_definitions():
    """Human-readable field names, if definitions.csv sits alongside."""
    for c in ('definitions.csv', os.path.join(os.path.dirname(__file__), 'definitions.csv')):
        if os.path.exists(c):
            out = {}
            with open(c, encoding='latin-1') as fh:
                for r in csv.reader(fh):
                    if len(r) >= 2 and r[0]:
                        out[r[0]] = r[1]
            return out
    return {}


# ---------------------------------------------------------------- commands

def cmd_tables(path):
    r = Roster(path)
    print(f'{os.path.basename(path)}  —  {len(r.tables)} tables')
    print(f'{"tag":<6}{"records":>9}{"capacity":>10}{"fields":>8}{"rec bytes":>11}')
    for tag in sorted(r.tables):
        t = r.table(tag)
        print(f'{tag:<6}{t.record_count:>9}{t.capacity:>10}{t.field_count:>8}{t.record_bytes:>11}')
    return 0


def cmd_dump(path, tag, out, limit=None, lsb=False):
    r = Roster(path)
    t = r.table(tag)
    rows = list(t.rows(limit, msb_first=not lsb))
    if not rows:
        print(f'{tag}: no records'); return 1
    cols = [f['tag'] for f in t.fields]
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f'{tag}: wrote {len(rows)} records x {len(cols)} fields -> {out}')
    return 0


def cmd_check(path, lsb=False):
    """Screen a file before trusting it. Implements the tests in
    docs/PGM3_SOURCE_QUALITY.md."""
    r = Roster(path)
    print(f'{os.path.basename(path)}')
    print('=' * 66)
    ok = True

    for tag, skin, hair, first, last in (
            ('PLAY', 'PSKI', 'PHCL', 'PFNA', 'PLNA'),
            ('COCH', 'CSKI', 'CHCL', 'CFNA', 'CLNA')):
        if tag not in r.tables:
            print(f'{tag}: absent'); continue
        t = r.table(tag)
        rows = list(t.rows(msb_first=not lsb))
        print(f'\n{tag}: {len(rows)} records, {t.field_count} fields')

        names = [str(row.get(last, '')) for row in rows if str(row.get(last, '')).strip()]
        print(f'  names readable: {len(names)}/{len(rows)}', end='')
        if names:
            print(f'   e.g. {", ".join(names[:3])}')
        else:
            print('   <-- NONE. Bit order or string handling is wrong; try --lsb')
            ok = False

        if skin in {f["tag"] for f in t.fields}:
            c = collections.Counter(row[skin] for row in rows)
            tot = sum(c.values()) or 1
            dist = {k: 100.0 * v / tot for k, v in sorted(c.items())}
            print(f'  {skin}: ' + '  '.join(f'{k}:{v:.1f}%' for k, v in dist.items()))
            mid = dist.get(1, 0.0)
            # The discriminator is the MIDDLE value, not the largest. The
            # largest is supposed to be large — most of the league is dark.
            if mid > 28:
                print(f'        FAIL — {mid:.0f}% on the middle value (>28%). '
                      f'Field is collapsed; unusable for skin.')
                ok = False
            else:
                dark = sum(v for k, v in dist.items() if k >= 2)
                print(f'        pass — middle value {mid:.0f}%. '
                      f'Calls {dark:.0f}% dark (real NFL ~65-67%; coaches ~21%).')
                print(f'        Still anchor-test it before trusting. AUC measures'
                      f' ordering, not calibration.')

        if hair in {f["tag"] for f in t.fields}:
            c = collections.Counter(row[hair] for row in rows)
            tot = sum(c.values()) or 1
            d = {k: 100.0 * v / tot for k, v in sorted(c.items())}
            print(f'  {hair}: ' + '  '.join(f'{k}:{v:.1f}%' for k, v in d.items()))
            print(f'        expect ~61-75% on 0 (black). Source quality is per '
                  f'field — a dead skin field does not mean dead hair.')

    print('\n' + '-' * 66)
    print('screen passed — anchor-test next' if ok else 'screen FAILED — see above')
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return 1
    lsb = '--lsb' in a
    a = [x for x in a if x != '--lsb']
    cmd = a[0]
    try:
        if cmd == 'tables' and len(a) == 2:
            return cmd_tables(a[1])
        if cmd == 'check' and len(a) == 2:
            return cmd_check(a[1], lsb)
        if cmd == 'dump' and len(a) >= 3:
            out = None
            if '-o' in a:
                out = a[a.index('-o') + 1]
                a = a[:a.index('-o')]
            tag = a[2]
            out = out or f'{os.path.splitext(os.path.basename(a[1]))[0]}_-_{tag}.csv'
            return cmd_dump(a[1], tag, out, lsb=lsb)
    except (ValueError, KeyError) as e:
        print(f'error: {e}'); return 1
    print(__doc__); return 1


if __name__ == '__main__':
    sys.exit(main())
