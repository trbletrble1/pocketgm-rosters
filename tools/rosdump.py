#!/usr/bin/env python3
"""
rosdump — read Madden .ros / .dbt and ESPN NFL 2K5 gamesaves without Windows.

Pure Python 3, standard library only. Nothing to install.

    python3 rosdump.py tables  FILE.ros
    python3 rosdump.py offsets FILE.ros -o reference/ros_solved_offsets.json
    python3 rosdump.py dump   FILE.ros PLAY -o play.csv
    python3 rosdump.py dump   FILE.ros --all -o outdir/
    python3 rosdump.py verify FILE.ros PLAY reference.csv
    python3 rosdump.py check  FILE.ros
    python3 rosdump.py gui

The same commands work on ESPN NFL 2K5 console saves (Xbox SAVEGAME.DAT).
The format is detected from the file header and routed to nfl2k5.py, which
must sit alongside this file. 2K5 saves expose a single table, PLAY.
That backend matters because it reaches seasons Madden exports do not:
community rosters exist back to 1958, and the 1986/1988/1990 files carry
real skin data at 93% against known players.

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
    +0x08 uint32  record length in BYTES
    +0x0c uint32  record length in BITS
    +0x14 uint16  allocated capacity
    +0x16 uint16  records actually used
    +0x1c uint32  field count
    +0x28 field definitions, 16 bytes each:
              uint32 type, uint32 bit offset, 4-char tag, uint32 bit width

Note the definition array starts at +0x28, NOT +0x30, and the type and offset
come BEFORE the name. Reading it as (tag, bits, type, offset) from +0x30 looks
almost right — the tags and widths land correctly — but pairs every name with
the *previous* field's type and offset. That misreading is what made the format
look unsolvable for so long: it also made the last definition appear corrupt
(it is not; the array ends exactly where the record data starts) and made the
data appear to start 8 bytes "early".

Record data begins at `table_offset + 0x28 + field_count*16`, and records are
packed at `record_bytes * 8` bits each — for PLAY that is 832, not the 831 the
header quotes.

Decoding a record:
    v = int.from_bytes(record_bytes, 'little') >> field.offset & mask

That is, the whole record is one little-endian integer and the field offset
counts bits up from its low end. Field types: 0 = string (take the raw bytes
at offset//8, NUL-terminated), 2 = signed two's complement, 3 = unsigned.

Two bit conventions are in play and they are easy to confuse. The offset stored
in the file counts up from the LOW end of the little-endian record, which is
what the decode above uses. Earlier work on this project quoted positions the
other way round — MSB-first across the raw bytes. For a field inside one byte
they convert as

    raw_msb_first = 8*(offset//8) + 8 - offset%8 - bits

PLAY `PSKI` here is stored at offset 404, width 2, which is raw bit 402 — the
number `docs/PGM3_PROJECT_HANDOFF.md` records for the 2003-2008 and 2016-2025
files, derived years ago by a different route. Quote the stored offset when
talking to this tool and the raw number when reading the handoff.

Field layouts differ between game years, which is why this reads the schema out
of each file rather than hardcoding anything.

STATUS
------
Verified exactly against Xtreme DB Editor's own CSV exports of
2020ROJOROSTER_V22: all 3027 x 110 PLAY values and all 218 x 68 COCH values,
strings and negative numbers included. `verify` re-runs that comparison.

Only ONE .ros is in the repo, so the decoder has not yet been tested against a
second game year. Run `verify` on one before trusting `check` on old files.
"""
import sys, os, csv, json, struct, collections

STRING, SIGNED, UNSIGNED = 0, 2, 3


class Field:
    __slots__ = ('tag', 'bits', 'type', 'offset')

    def __init__(self, tag, bits, typ, offset):
        self.tag, self.bits, self.type, self.offset = tag, bits, typ, offset

    @property
    def is_string(self):
        return self.type == STRING

    def __repr__(self):
        return f'<{self.tag} {self.bits}b type{self.type} @{self.offset}>'


class Table:
    # The field definition array starts 8 bytes before the "obvious" place and
    # holds (type, offset, name, bits) rather than (name, bits, type, offset).
    FIELD_DEFS = 0x28
    FIELD_SIZE = 16

    def __init__(self, tag, buf, off):
        self.tag, self.buf, self.off = tag, buf, off
        self.record_bytes = struct.unpack_from('<I', buf, off + 0x08)[0]
        self.record_bits  = struct.unpack_from('<I', buf, off + 0x0c)[0]
        self.capacity     = struct.unpack_from('<H', buf, off + 0x14)[0]
        self.record_count = struct.unpack_from('<H', buf, off + 0x16)[0]
        self.field_count  = struct.unpack_from('<I', buf, off + 0x1c)[0]

        self.fields, self.bad_fields = [], []
        for i in range(self.field_count):
            o = off + self.FIELD_DEFS + i * self.FIELD_SIZE
            typ, bitoff = struct.unpack_from('<2I', buf, o)
            name = buf[o + 8:o + 12].decode('latin-1').rstrip('\x00')
            bits = struct.unpack_from('<I', buf, o + 12)[0]
            # A definition that cannot fit inside a record means the schema is
            # not being read the way this file wrote it. Do not silently drop
            # it — a skipped field is a missing CSV column, which reads as a
            # clean export right up until someone diffs it.
            if bitoff + bits > self.record_bytes * 8:
                self.bad_fields.append(Field(name, bits, typ, bitoff))
                continue
            self.fields.append(Field(name, bits, typ, bitoff))

        self.data_off = off + self.FIELD_DEFS + self.field_count * self.FIELD_SIZE

    def raw(self, i):
        b = self.data_off + i * self.record_bytes
        return self.buf[b:b + self.record_bytes]

    def read(self, i):
        rec = self.raw(i)
        v = int.from_bytes(rec, 'little')
        out = {}
        for f in self.fields:
            if f.type == STRING:
                b = rec[f.offset // 8: f.offset // 8 + f.bits // 8]
                out[f.tag] = b.split(b'\x00')[0].decode('latin-1')
            else:
                x = (v >> f.offset) & ((1 << f.bits) - 1)
                if f.type == SIGNED and x >> (f.bits - 1):
                    x -= 1 << f.bits
                out[f.tag] = x
        return out

    def rows(self, limit=None):
        n = self.record_count if limit is None else min(limit, self.record_count)
        for i in range(n):
            yield self.read(i)

    def columns(self):
        return [f.tag for f in self.fields]


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
            tag = self.buf[o:o + 4].decode('latin-1').strip('\x00')
            self.tables[tag] = base + struct.unpack_from('<I', self.buf, o + 4)[0]

    def table(self, tag):
        if tag not in self.tables:
            raise KeyError(f'{tag} not in {os.path.basename(self.path)}. '
                           f'Present: {", ".join(sorted(self.tables))}')
        return Table(tag, self.buf, self.tables[tag])


# ---------------------------------------------------------------- commands

def write_csv(t, out, limit=None):
    cols = t.columns()
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in t.rows(limit):
            w.writerow(row)
    return cols


def detect_format(path):
    """Which backend reads this file. Madden containers open with 'DB',
    2K5 console saves with 'ROST'."""
    with open(path, 'rb') as fh:
        head = fh.read(8)
    if head[:2] == b'DB':
        return 'madden'
    if head[:4] == b'ROST':
        return 'nfl2k5'
    return 'unknown'


def _load2k5(path):
    try:
        import nfl2k5
    except ImportError:
        raise OSError('nfl2k5.py must sit next to rosdump.py to read 2K5 saves')
    s = nfl2k5.Save(path)
    if not s.players:
        raise ValueError('no player records found — is this a 2K5 roster save?')
    return nfl2k5, s


def cmd_tables_2k5(path):
    m, s = _load2k5(path)
    print(f'{os.path.basename(path)}  —  NFL 2K5 gamesave')
    print(f'{"tag":<6}{"records":>9}{"edited":>9}{"fields":>8}{"rec bytes":>11}')
    print(f'{"PLAY":<6}{len(s.players):>9}{len(s.edited()):>9}'
          f'{len(s.players[0]):>8}{m.PLAYER_LEN:>11}')
    return 0


def cmd_dump_2k5(path, tag, out):
    m, s = _load2k5(path)
    if tag not in ('PLAY', '--all'):
        print(f'2K5 saves expose one table, PLAY (asked for {tag})'); return 1
    stem = os.path.splitext(os.path.basename(path))[0]
    dest = out or f'{stem}_-_PLAY.csv'
    if tag == '--all':
        os.makedirs(out or '.', exist_ok=True)
        dest = os.path.join(out or '.', f'{stem}_-_PLAY.csv')
    n = m.write_csv(s, dest)
    print(f'PLAY: wrote {n} records x {len(s.players[0])} fields -> {dest}')
    return 0


def cmd_check_2k5(path):
    m, s = _load2k5(path)
    lines, verdict = m.check(s)
    print(f'{os.path.basename(path)}  —  NFL 2K5 gamesave  (players at 0x{s.player_start:X})')
    for l in lines:
        print('   ' + l)
    print(f'\nscreen {verdict}' + ('' if verdict == 'FAILED' else
          ' — still anchor-test it against known players before trusting it'))
    return 0 if verdict == 'pass' else 1


def cmd_tables(path):
    r = Roster(path)
    print(f'{os.path.basename(path)}  —  {len(r.tables)} tables')
    print(f'{"tag":<6}{"records":>9}{"capacity":>10}{"fields":>8}{"rec bytes":>11}')
    for tag in sorted(r.tables, key=lambda k: r.tables[k]):
        t = r.table(tag)
        note = f'   [{len(t.bad_fields)} unreadable field defs]' if t.bad_fields else ''
        print(f'{tag:<6}{t.record_count:>9}{t.capacity:>10}{t.field_count:>8}'
              f'{t.record_bytes:>11}{note}')
    return 0


def cmd_dump(path, tag, out, limit=None):
    r = Roster(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    tags = sorted(r.tables) if tag == '--all' else [tag]
    if tag == '--all':
        outdir = out or '.'
        os.makedirs(outdir, exist_ok=True)
    rc = 0
    for tg in tags:
        t = r.table(tg)
        if not t.record_count:
            print(f'{tg}: no records — skipped')
            continue
        dest = (os.path.join(out or '.', f'{stem}_-_{tg}.csv')
                if tag == '--all' else (out or f'{stem}_-_{tg}.csv'))
        cols = write_csv(t, dest, limit)
        print(f'{tg}: wrote {min(limit or t.record_count, t.record_count)} records '
              f'x {len(cols)} fields -> {dest}')
        if t.bad_fields:
            print(f'   WARNING: {len(t.bad_fields)} field definitions did not fit the '
                  f'record and are missing from the CSV: '
                  f'{", ".join(f.tag for f in t.bad_fields)}')
            rc = 1
    return rc


def cmd_verify(path, tag, ref):
    """Compare a decoded table against an Xtreme DB Editor CSV, value by value.

    Exact equality or failure — see docs/PGM3_TASK_ros_decoder.md. A field that
    matches on most records and not all is not a rounding problem, it is a
    layout problem, so nothing here tolerates a near miss."""
    r = Roster(path)
    t = r.table(tag)
    with open(ref, encoding='latin-1', newline='') as fh:
        rows = list(csv.reader(fh))
    hdr, rows = rows[0], rows[1:]
    print(f'{os.path.basename(path)} [{tag}]  vs  {os.path.basename(ref)}')

    ok = True
    if t.bad_fields:
        print(f'  FAIL  {len(t.bad_fields)} field definitions did not fit the record: '
              f'{", ".join(f.tag for f in t.bad_fields)}')
        ok = False
    if t.columns() != hdr:
        print(f'  FAIL  column names/order differ')
        print(f'        decoded: {len(t.columns())} cols, reference: {len(hdr)} cols')
        only_a = [c for c in t.columns() if c not in hdr]
        only_b = [c for c in hdr if c not in t.columns()]
        if only_a: print(f'        only in decode:    {", ".join(only_a)}')
        if only_b: print(f'        only in reference: {", ".join(only_b)}')
        return 1
    if t.record_count != len(rows):
        print(f'  FAIL  record count {t.record_count} != {len(rows)} rows')
        return 1

    bad = collections.defaultdict(list)
    for i in range(t.record_count):
        row = t.read(i)
        ref_row = rows[i]
        for ci, f in enumerate(t.fields):
            got = row[f.tag] if f.is_string else str(row[f.tag])
            if got != ref_row[ci]:
                bad[f.tag].append((i, got, ref_row[ci]))

    total = t.record_count * len(t.fields)
    if not bad:
        print(f'  OK    {t.record_count} records x {len(t.fields)} fields '
              f'= {total} values, all exact')
        return 0 if ok else 1
    print(f'  FAIL  {sum(len(v) for v in bad.values())} of {total} values differ, '
          f'in {len(bad)} of {len(t.fields)} fields')
    for tg, v in sorted(bad.items(), key=lambda kv: -len(kv[1])):
        f = next(f for f in t.fields if f.tag == tg)
        i, got, want = v[0]
        print(f'        {tg:6} w={f.bits:<3} type={f.type} off={f.offset:<4} '
              f'{len(v):>6} bad   first: rec {i} got {got!r} want {want!r}')
    return 1


def cmd_check(path):
    """Screen a file before trusting it. Implements the tests in
    docs/PGM3_SOURCE_QUALITY.md."""
    r = Roster(path)
    print(f'{os.path.basename(path)}')
    print('=' * 66)
    ok = True

    for tag, skin, hair, first, last in (
            ('PLAY', 'PSKI', 'PHCL', 'PFNA', 'PLNA'),
            ('COCH', 'CSKI', 'CHCL', 'CFNA', 'CLNA')):
        # Player and coach skin are screened differently. The middle-value gate
        # is a player-file test: PSKI 1 is a bimodal bucket carrying no signal,
        # and a file with too much weight on it has collapsed. Coach CSKI is
        # documented as correctly calibrated, with 0 = light and everything
        # above it dark — see docs/PGM3_SOURCE_QUALITY.md, "Coach skin".
        player = tag == 'PLAY'
        if tag not in r.tables:
            print(f'{tag}: absent'); continue
        t = r.table(tag)
        rows = list(t.rows())
        print(f'\n{tag}: {len(rows)} records, {t.field_count} fields')
        if t.bad_fields:
            print(f'  {len(t.bad_fields)} field definitions did not fit the record '
                  f'— schema read is wrong, treat everything below as suspect')
            ok = False
        present = {f.tag for f in t.fields}

        names = [str(row.get(last, '')) for row in rows if str(row.get(last, '')).strip()]
        print(f'  names readable: {len(names)}/{len(rows)}', end='')
        if names:
            print(f'   e.g. {", ".join(names[:3])}')
        else:
            print('   <-- NONE. The schema read is wrong; run `verify` against a '
                  'known CSV')
            ok = False

        if skin in present:
            c = collections.Counter(row[skin] for row in rows)
            tot = sum(c.values()) or 1
            dist = {k: 100.0 * v / tot for k, v in sorted(c.items())}
            print(f'  {skin}: ' + '  '.join(f'{k}:{v:.1f}%' for k, v in dist.items()))
            if player:
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
                          f'Calls {dark:.0f}% dark (real NFL ~65-67%).')
                    print(f'        Still anchor-test it before trusting. AUC '
                          f'measures ordering, not calibration.')
            else:
                dark = sum(v for k, v in dist.items() if k >= 1)
                print(f'        calls {dark:.0f}% dark (0 = light, 1 and above '
                      f'dark; real coaching population ~21%, registry 24.1%).')
                print(f'        No middle-value gate applies to coaches. A share '
                      f'far off ~21% is the thing to question.')

        if hair in present:
            c = collections.Counter(row[hair] for row in rows)
            tot = sum(c.values()) or 1
            d = {k: 100.0 * v / tot for k, v in sorted(c.items())}
            print(f'  {hair}: ' + '  '.join(f'{k}:{v:.1f}%' for k, v in d.items()))
            print(f'        expect ~61-75% on 0 (black). Source quality is per '
                  f'field — a dead skin field does not mean dead hair.')

    print('\n' + '-' * 66)
    print('screen passed — anchor-test next' if ok else 'screen FAILED — see above')
    return 0 if ok else 1



def cmd_offsets(path, out, note=None):
    """Emit the full verified field layout as JSON.

    This exists so reference/ros_solved_offsets.json is DERIVED, not curated.
    A hand-maintained artifact with no regeneration path goes stale and
    nothing notices: the committed copy sat at 2 tables / 47 PLAY offsets for
    months while the superseding 10-table version lived only in an untracked
    working directory. Regenerate rather than restore."""
    ros = Roster(path)
    tables = {}
    for tag in sorted(ros.tables):
        t = ros.table(tag)
        tables[tag] = {
            'record_bytes':       t.record_bytes,
            'record_bits_header': t.record_bits,
            'records':            t.record_count,
            'capacity':           t.capacity,
            'field_count':        t.field_count,
            'unreadable_field_defs': [
                {'tag': f.tag, 'offset': f.offset, 'bits': f.bits, 'type': f.type}
                for f in t.bad_fields],
            'fields': [
                {'tag': f.tag, 'offset': f.offset, 'bits': f.bits, 'type': f.type}
                for f in t.fields],
        }
    doc = {
        '_note': note or (
            'Full verified field layout of ' + os.path.basename(path) + ', produced by '
            'tools/rosdump.py offsets. `offset` is the bit offset up from the LOW end '
            'of the record read as a little-endian integer, exactly as stored in the '
            'file. type 0 = string, 2 = signed, 3 = unsigned.'),
        '_source': path,
        '_tables': sorted(ros.tables),
        'tables': tables,
    }
    # match the artifact's existing on-disk format (indent=1) so the diff stays
    # reviewable -- format churn disables the control that catches everything else
    with open(out, 'w') as f:
        json.dump(doc, f, indent=1)
        f.write('\n')
    n = sum(v['field_count'] for v in tables.values())
    print(f'{out}: {len(tables)} tables, {n} fields')

def cmd_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext
    import io, contextlib

    root = tk.Tk()
    root.title('rosdump — Madden .ros reader')
    path_var, dir_var = tk.StringVar(), tk.StringVar(value=os.getcwd())
    play_var = tk.BooleanVar(value=True)
    coch_var = tk.BooleanVar(value=True)
    all_var = tk.BooleanVar(value=False)
    check_var = tk.BooleanVar(value=True)

    frm = tk.Frame(root, padx=10, pady=10); frm.pack(fill='both', expand=True)
    log = scrolledtext.ScrolledText(frm, width=88, height=24, font=('Menlo', 11))

    def say(s=''):
        log.insert('end', s + '\n'); log.see('end'); root.update_idletasks()

    def pick():
        p = filedialog.askopenfilename(
            title='Choose a roster',
            filetypes=[('Madden roster', '*.ros *.ROS *.dbt *.DBT'), ('All files', '*')])
        if p:
            path_var.set(p)
            log.delete('1.0', 'end')
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    cmd_tables(p)
                say(buf.getvalue().rstrip())
            except Exception as e:
                say(f'error: {e}')

    def pick_dir():
        d = filedialog.askdirectory(title='Where should the CSVs go?')
        if d: dir_var.set(d)

    def run():
        p = path_var.get()
        if not p:
            messagebox.showwarning('rosdump', 'Choose a .ros file first.'); return
        log.delete('1.0', 'end')
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                if check_var.get():
                    cmd_check(p); print()
                if all_var.get():
                    cmd_dump(p, '--all', dir_var.get())
                else:
                    stem = os.path.splitext(os.path.basename(p))[0]
                    for tg, var in (('PLAY', play_var), ('COCH', coch_var)):
                        if var.get():
                            cmd_dump(p, tg, os.path.join(dir_var.get(),
                                                         f'{stem}_-_{tg}.csv'))
            say(buf.getvalue().rstrip())
        except Exception as e:
            say(buf.getvalue().rstrip()); say(f'error: {e}')

    row = tk.Frame(frm); row.pack(fill='x')
    tk.Button(row, text='Roster…', width=10, command=pick).pack(side='left')
    tk.Label(row, textvariable=path_var, anchor='w').pack(side='left', padx=6)

    row = tk.Frame(frm); row.pack(fill='x', pady=(4, 8))
    tk.Button(row, text='Output to…', width=10, command=pick_dir).pack(side='left')
    tk.Label(row, textvariable=dir_var, anchor='w').pack(side='left', padx=6)

    row = tk.Frame(frm); row.pack(fill='x')
    tk.Checkbutton(row, text='PLAY', variable=play_var).pack(side='left')
    tk.Checkbutton(row, text='COCH', variable=coch_var).pack(side='left')
    tk.Checkbutton(row, text='every table', variable=all_var).pack(side='left')
    tk.Checkbutton(row, text='source screen', variable=check_var).pack(side='left')
    tk.Button(row, text='Run', width=10, command=run).pack(side='right')

    log.pack(fill='both', expand=True, pady=(8, 0))
    say('Choose a roster to see its tables.')
    root.mainloop()
    return 0


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return 1
    cmd = a[0]
    try:
        if cmd == 'gui' and len(a) == 1:
            return cmd_gui()
        if cmd == 'offsets' and len(a) >= 3 and a[2] == '-o' and len(a) == 4:
            return cmd_offsets(a[1], a[3])
        if cmd == 'tables' and len(a) == 2:
            return (cmd_tables_2k5 if detect_format(a[1]) == 'nfl2k5'
                    else cmd_tables)(a[1])
        if cmd == 'check' and len(a) == 2:
            return (cmd_check_2k5 if detect_format(a[1]) == 'nfl2k5'
                    else cmd_check)(a[1])
        if cmd == 'verify' and len(a) == 4:
            return cmd_verify(a[1], a[2], a[3])
        if cmd == 'dump' and len(a) >= 3:
            out = None
            if '-o' in a:
                i = a.index('-o'); out = a[i + 1]; a = a[:i] + a[i + 2:]
            if detect_format(a[1]) == 'nfl2k5':
                return cmd_dump_2k5(a[1], a[2], out)
            return cmd_dump(a[1], a[2], out)
    except (ValueError, KeyError, OSError) as e:
        # KeyError stringifies to its repr, which quotes the whole message.
        print(f'error: {e.args[0] if isinstance(e, KeyError) else e}'); return 1
    print(__doc__); return 1


if __name__ == '__main__':
    sys.exit(main())
