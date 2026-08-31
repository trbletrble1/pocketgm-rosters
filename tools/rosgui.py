#!/usr/bin/env python3
"""
rosgui — drop Madden .ros files in, get CSVs out. No Windows, no install.

    python3 rosgui.py

Self-contained: the decoder is embedded, so this one file is the whole app.
Standard library only. Drag-and-drop into the window works if tkinterdnd2 is
installed (`pip3 install tkinterdnd2`); without it, use the Choose Files button
or drop files onto the app icon.

Decoder verified against Xtreme DB Editor exports on two files —
2020ROJOROSTER V22 and 2000 — 631,000 values, all exact.
"""
import os, sys, csv, struct, collections

# ------------------------------------------------------------------ decoder
# Container:
#   0x00 "DB" magic;  0x10 uint32 table count
#   0x18 directory, 8 bytes/entry: 4-char tag + uint32 offset relative to the
#        end of the directory
# Table header at that offset:
#   +0x08 uint32 record length in BYTES
#   +0x16 uint16 records used        (+0x14 is capacity, not count)
#   +0x1c uint32 field count
#   +0x28 field definitions, 16 bytes each:
#             uint32 type, uint32 bit offset, char[4] name, uint32 bit width
# Records follow the definitions. Each record is ONE little-endian integer and
# the bit offset counts up from its low end:
#     value = int.from_bytes(record, 'little') >> offset & ((1 << bits) - 1)
# type 0 = string, 2 = signed, 3 = unsigned.

class Table:
    def __init__(self, tag, buf, off):
        self.tag = tag; self.buf = buf; self.off = off
        self.record_bytes = struct.unpack_from('<I', buf, off + 0x08)[0]
        self.capacity     = struct.unpack_from('<H', buf, off + 0x14)[0]
        self.record_count = struct.unpack_from('<H', buf, off + 0x16)[0]
        self.field_count  = struct.unpack_from('<I', buf, off + 0x1c)[0]
        self.fields = []
        for i in range(self.field_count):
            o = off + 0x28 + i * 16
            typ, bitoff = struct.unpack_from('<2I', buf, o)
            name = buf[o+8:o+12].decode('latin-1').strip('\x00')
            bits = struct.unpack_from('<I', buf, o+12)[0]
            self.fields.append({'tag': name, 'bits': bits, 'type': typ, 'offset': bitoff})
        self.data_off = off + 0x28 + self.field_count * 16

    def rows(self):
        rb = self.record_bytes
        for i in range(self.record_count):
            raw = int.from_bytes(self.buf[self.data_off + i*rb : self.data_off + (i+1)*rb], 'little')
            out = {}
            for f in self.fields:
                v = (raw >> f['offset']) & ((1 << f['bits']) - 1)
                if f['type'] == 0:
                    b = bytes((v >> (8*k)) & 0xFF for k in range(f['bits'] // 8))
                    out[f['tag']] = b.split(b'\x00')[0].decode('latin-1', 'replace')
                elif f['type'] == 2 and v & (1 << (f['bits'] - 1)):
                    out[f['tag']] = v - (1 << f['bits'])
                else:
                    out[f['tag']] = v
            yield out


class Roster:
    def __init__(self, path):
        with open(path, 'rb') as fh: self.buf = fh.read()
        if self.buf[:2] != b'DB':
            raise ValueError('not a Madden .ros/.dbt file (missing "DB" magic)')
        self.path = path
        n = struct.unpack_from('<I', self.buf, 0x10)[0]
        base = 0x18 + n * 8
        self.tables = {}
        for i in range(n):
            o = 0x18 + i * 8
            tag = self.buf[o:o+4].decode('latin-1').strip('\x00')
            self.tables[tag] = base + struct.unpack_from('<I', self.buf, o+4)[0]

    def table(self, tag):
        if tag not in self.tables:
            raise KeyError(f'{tag} not present. Tables: {", ".join(sorted(self.tables))}')
        return Table(tag, self.buf, self.tables[tag])


def export(path, tag, outdir):
    r = Roster(path); t = r.table(tag)
    rows = list(t.rows())
    stem = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(outdir, f'{stem}_-_{tag}.csv')
    cols = [f['tag'] for f in t.fields]
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for row in rows: w.writerow(row)
    return out, len(rows), len(cols)


def screen(path):
    """The usable/unusable verdict from docs/PGM3_SOURCE_QUALITY.md."""
    r = Roster(path); lines = []; verdict = True
    for tag, skin, hair in (('PLAY','PSKI','PHCL'), ('COCH','CSKI','CHCL')):
        if tag not in r.tables: continue
        t = r.table(tag); rows = list(t.rows())
        tags = {f['tag'] for f in t.fields}
        lines.append(f'{tag}: {len(rows)} records, {t.field_count} fields')
        if skin in tags:
            c = collections.Counter(row[skin] for row in rows); tot = sum(c.values()) or 1
            dist = {k: 100.0*v/tot for k, v in sorted(c.items())}
            lines.append('   ' + skin + ': ' + '  '.join(f'{k}:{v:.1f}%' for k, v in dist.items()))
            # Players: 0 light, 1 unknown (abstain), 2+ dark.
            # Coaches: 0 light, ANYTHING above dark — no middle value.
            dark = sum(v for k, v in dist.items() if k >= (2 if tag == 'PLAY' else 1))
            if tag == 'PLAY':
                mid = dist.get(1, 0.0)
                if mid > 28:
                    lines.append(f'   FAIL  {mid:.0f}% on the middle value (gate is 28%).')
                    lines.append(f'         Field is collapsed — unusable for skin.')
                    verdict = False
                else:
                    lines.append(f'   pass  middle value {mid:.0f}%, calls {dark:.0f}% dark '
                                 f'(real NFL ~65-67%)')
            else:
                # Coach CSKI is calibrated differently: 0 = light, above = dark,
                # and there is no middle-value gate. ~21% dark is expected.
                odd = [k for k in dist if k > 2]
                lines.append(f'   coaches: {dark:.0f}% dark (expected ~21%)'
                             + (f'   [note: values {odd} are outside the usual 0-2]' if odd else ''))
        if hair in tags:
            c = collections.Counter(row[hair] for row in rows); tot = sum(c.values()) or 1
            d = {k: 100.0*v/tot for k, v in sorted(c.items())}
            lines.append('   ' + hair + ': ' + '  '.join(f'{k}:{v:.1f}%' for k, v in d.items())
                         + '   (expect 61-75% on 0)')
    lines.append('SCREEN PASSED — anchor-test before trusting it' if verdict
                 else 'SCREEN FAILED — do not use this file for skin')
    return verdict, lines


# ---------------------------------------------------------------------- gui

def run_gui(initial=()):
    import tkinter as tk
    from tkinter import filedialog, ttk
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk(); HAS_DND = True
    except Exception:
        root = tk.Tk(); HAS_DND = False

    root.title('Madden .ros exporter')
    root.geometry('720x560')
    files = list(initial)
    outdir = tk.StringVar(value='')

    top = tk.Frame(root, padx=12, pady=10); top.pack(fill='x')
    hint = ('Drag .ros files here, or use Choose Files'
            if HAS_DND else 'Click Choose Files to pick .ros files')
    tk.Label(top, text=hint, font=('Helvetica', 13)).pack(anchor='w')

    lb = tk.Listbox(root, height=6, selectmode='extended')
    lb.pack(fill='x', padx=12, pady=6)

    log = tk.Text(root, height=18, wrap='word', font=('Menlo', 11))
    log.pack(fill='both', expand=True, padx=12, pady=6)

    def say(s=''):
        log.insert('end', s + '\n'); log.see('end'); root.update_idletasks()

    def refresh():
        lb.delete(0, 'end')
        for f in files: lb.insert('end', os.path.basename(f))

    def add(paths):
        for p in paths:
            p = p.strip('{}')
            if p.lower().endswith(('.ros', '.dbt')) and p not in files:
                files.append(p)
        refresh()

    def choose():
        add(filedialog.askopenfilenames(
            title='Choose .ros files',
            filetypes=[('Madden roster', '*.ros *.dbt'), ('All files', '*.*')]))

    def clear():
        files.clear(); refresh(); log.delete('1.0', 'end')

    def target_dir(path):
        return outdir.get() or os.path.dirname(os.path.abspath(path))

    def do_export(tags):
        if not files: say('No files chosen.'); return
        for p in files:
            say(f'\n{os.path.basename(p)}')
            for tag in tags:
                try:
                    out, n, c = export(p, tag, target_dir(p))
                    say(f'   {tag}: {n} records x {c} fields  ->  {os.path.basename(out)}')
                except Exception as e:
                    say(f'   {tag}: FAILED — {e}')
        say('\nDone.')

    def do_screen():
        if not files: say('No files chosen.'); return
        for p in files:
            say(f'\n{os.path.basename(p)}')
            try:
                _, lines = screen(p)
                for l in lines: say('  ' + l)
            except Exception as e:
                say(f'  FAILED — {e}')

    def do_tables():
        if not files: say('No files chosen.'); return
        for p in files:
            say(f'\n{os.path.basename(p)}')
            try:
                r = Roster(p)
                for tag in sorted(r.tables):
                    t = r.table(tag)
                    say(f'   {tag:<6}{t.record_count:>7} records{t.field_count:>5} fields'
                        f'{t.record_bytes:>5} bytes/rec')
            except Exception as e:
                say(f'   FAILED — {e}')

    def pick_out():
        d = filedialog.askdirectory(title='Where to save CSVs')
        outdir.set(d or '')
        say(f'Output folder: {d or "alongside each .ros"}')

    bar = tk.Frame(root, padx=12, pady=4); bar.pack(fill='x')
    tk.Button(bar, text='Choose Files', command=choose).pack(side='left')
    tk.Button(bar, text='Clear', command=clear).pack(side='left', padx=6)
    tk.Button(bar, text='Output folder…', command=pick_out).pack(side='left')

    bar2 = tk.Frame(root, padx=12, pady=6); bar2.pack(fill='x', pady=(0, 8))
    tk.Button(bar2, text='Export Players',
              command=lambda: do_export(['PLAY'])).pack(side='left')
    tk.Button(bar2, text='Export Coaches',
              command=lambda: do_export(['COCH'])).pack(side='left', padx=6)
    tk.Button(bar2, text='Export Both',
              command=lambda: do_export(['PLAY', 'COCH'])).pack(side='left')
    tk.Button(bar2, text='Screen (usable?)',
              command=do_screen).pack(side='left', padx=16)
    tk.Button(bar2, text='List Tables', command=do_tables).pack(side='left')

    # macOS .app bundles receive opened/dropped files as an AppleEvent rather
    # than on the command line. This is what makes dropping onto the Dock icon
    # work once PyInstaller has built the bundle.
    try:
        root.createcommand('::tk::mac::OpenDocument', lambda *paths: add(list(paths)))
    except Exception:
        pass

    if HAS_DND:
        root.drop_target_register(DND_FILES)
        root.dnd_bind('<<Drop>>', lambda e: add(root.tk.splitlist(e.data)))
    else:
        say('Drag-and-drop needs tkinterdnd2 (pip3 install tkinterdnd2).')
        say('Without it, Choose Files does the same job.\n')

    refresh()
    if files: say(f'{len(files)} file(s) ready.')
    root.mainloop()


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if '--cli' in sys.argv:
        for p in args:
            print(f'\n{p}')
            _, lines = screen(p)
            for l in lines: print('  ' + l)
    else:
        run_gui(args)
