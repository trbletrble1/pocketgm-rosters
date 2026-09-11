"""Measure the game line-ups on the preserved Ghosts of the Gridiron pages.

    python3 src/measure_ghosts_lineups.py            # dry run: read, and show what moved
    python3 src/measure_ghosts_lineups.py --write    # write build-reports/ghosts-lineups.json

WHY THIS FILE EXISTS. The measurement ingest_ghosts_lineups.py reads was written on
10 September by `lineup2.py` in that session's /tmp scratchpad, and then rewritten twice by
inline scripts: once to split game line-ups from honours lists, once to add `away_club` and
`home_club`. A script in a dead session's /tmp, whose output was hand-patched afterwards, is
not a source of claims (Ryan, 2026-09-11). This is that reader, brought into the repo
verbatim first and proved to reproduce the file it wrote, and only then fixed.

`away_club` and `home_club` are NOT carried. Nothing reads them, and what they held was
mostly a player's name (Riggs, Thomas, Hayes): a reader taking the capitalised strings
before the first position picks up the first PLAYER. The side-to-club map is declared in
declarations/ghosts-lineups.json for exactly that reason.
"""
import os, re, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
M = os.path.expanduser("~/Documents/pgm3-sources/ghostsofthegridiron/mirror")
OUT = os.path.join(BASE, "build-reports", "ghosts-lineups.json")


def text(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"</t[dhr]>", " | ", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    h = h.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8212;", "--")
    return re.sub(r"[ \t\|]*\|[ \t\|]*", " | ", re.sub(r"\s+", " ", h))


# THE ELEVEN, in the order a line-up prints them, each in both the abbreviated and the
# spelt-out form the site uses. The SEQUENCE is the shape; a roster repeats positions
# and has no sequence, which is what separates the two without testing any header string.
# BOUNDED ON BOTH SIDES. Without the boundaries `c\.?` matched the c in "Athletic Club"
# and `e` the e in "quarterback", so an index page yielded eight "positions" and the men
# came out as 'tic Club' and 'erback'. An abbreviation must be an abbreviation: letters
# with stops, touching no other letter.
def _abbr(*letters):
    return r"(?<![A-Za-z])" + r"\.\s*".join(letters) + r"\.(?![A-Za-z])"


SEQ = [("LE",  _abbr("l", "e")      + r"|\bleft\s+end\b"),
       ("LT",  _abbr("l", "t")      + r"|\bleft\s+tackle\b"),
       ("LG",  _abbr("l", "g")      + r"|\bleft\s+guard\b"),
       ("C",   _abbr("c")           + r"|\bcen(?:ter|tre)\b"),
       ("RG",  _abbr("r", "g")      + r"|\bright\s+guard\b"),
       ("RT",  _abbr("r", "t")      + r"|\bright\s+tackle\b"),
       ("RE",  _abbr("r", "e")      + r"|\bright\s+end\b"),
       # FIXED 2026-09-11, the three forms that cost 11 of 17 pages two men a side.
       # `Quarter-back`, `Full-back` and `half-back` are HYPHENATED on most of these
       # pages; `quarter\s*back` matched none of them, and `left half` stopped before
       # `-back` so the name after it was never reached. Washington 1921 prints the
       # halves as `L. H.` and `R. H.`, with no B. The longer abbreviation is tried
       # first, so `L. H. B.` is never read as `L. H.` followed by a man called `B.`.
       ("QB",  _abbr("q", "b")      + r"|\bquarter[\s-]*back\b"),
       ("LHB", _abbr("l", "h", "b") + "|" + _abbr("l", "h") + r"|\bleft\s+half(?:[\s-]*back)?\b"),
       ("RHB", _abbr("r", "h", "b") + "|" + _abbr("r", "h") + r"|\bright\s+half(?:[\s-]*back)?\b"),
       ("FB",  _abbr("f", "b")      + r"|\bfull[\s-]*back\b")]
NAME = r"[A-Z][A-Za-z'\.\-]+(?:\s+[A-Z][A-Za-z'\.\-]+)?"

# THE BACKFIELD HAS NO FIXED ORDER. The line prints end to end, always; the backs do not
# -- Frankford 1902 prints right half-back BEFORE left half-back, and a walk that insists
# on LHB-then-RHB loses whichever comes second. So the seven linemen are walked in order
# and the four backs are each searched from where the line ends, then set in PRINTED
# order. The sequence is still the shape; it is the line's sequence.
BACKFIELD = {"QB", "LHB", "RHB", "FB"}

# A NAME IN BRACKETS AFTER A NAME -- `Anderson (Hogan)`. Ryan ruled 2026-09-11 that this
# reads as Hogan substituting for Anderson, CONFIRMED against a page whose prose names the
# substitution before it is applied. No page in the 243 has such prose: the bracketed men
# are named nowhere else on their pages. So what this reader does is the part that holds
# under ANY reading of the brackets -- the first-named man is the man printed in that
# place -- and the bracketed name is KEPT, as printed, beside him. It is not made a
# substitution. Before this, the away side took "the last capitalised word before the
# position", which in `Anderson (Hogan)` is Hogan: two bracketed men read as starters.
BRACKET = r"\s*\(\s*(%s)\s*\)" % NAME
OFF = re.compile(r"(Referee|Umpire|Head\s+linesman|Linesman|Field\s+judge)\s*(?:--|—|:)\s*([^.;|]+)", re.I)
SUB = re.compile(r"Substitutions?\s*(?:--|—|:)\s*(.+?)(?:Referee|Umpire|Head\s+linesman|Linesman|Field\s+judge|Time\s+of|$)", re.I | re.S)

# A LINE-UP IS CONTIGUOUS. Without this the reader found eight "positions" on links.htm
# and stadiums.htm -- `c\.?` matches any stray "c." and `E`/`T`/`G` are single letters, so
# a long page of prose will always contain the eleven SOMEWHERE in order. The shape is not
# "these letters appear in this order", it is "these eleven sit together in one block".
SPAN = 1500


def lineup_of(t):
    """Walk the eleven in order, taking the name each side of each position."""
    best = []
    for start in range(0, max(1, len(t)), 400):
        window = t[start:start + SPAN]
        pos = 0; rows = []; back_from = None
        for code, pat in SEQ:
            if code in BACKFIELD and back_from is None: back_from = pos
            frm = back_from if code in BACKFIELD else pos
            m = re.compile(r"(%s)\s*\|?\s*(%s)?(?:%s)?" % (pat, NAME, BRACKET), re.I).search(window, frm)
            if not m: continue
            before = window[max(0, m.start() - 60):m.start()]
            bm = re.search(r"\(\s*(%s)\s*\)\s*\|?\s*$" % NAME, before)
            if bm: before = before[:bm.start()]
            b = re.findall(NAME, before)
            rows.append({"position": code, "away": (b[-1] if b else None), "home": m.group(2),
                         "away_bracketed": bm.group(1) if bm else None,
                         # A capital, as the away side already requires: NAME runs under
                         # re.I here, and Parkside 1919 prints `F. Weber (capt.)` -- a
                         # captain, not a man. Brackets on these pages are not one thing.
                         "home_bracketed": m.group(3) if (m.group(3) or " ")[0].isupper() else None,
                         "_at": m.start()})
            if code not in BACKFIELD: pos = m.end()
        rows = sorted((r for r in rows if r["away"] or r["home"]), key=lambda r: r["_at"])
        rows = [r for r in rows if not (_not_a_man(r["away"]) or _not_a_man(r["home"]))]
        if len(rows) > len(best): best = rows
    return best


# A MAN IS NOT A POSITION, AND A NAME BEGINS WITH A CAPITAL. NAME is compiled under re.I,
# so `[A-Z]` accepts `for` -- the pattern cannot say this, and it has to be said after.
# Found 2026-09-11 the moment the backfield stopped being walked in a fixed order: three
# pages that are NOT line-ups -- a "Name | Position | Weight" roster and two prose
# accounts -- scored eight "positions" apiece, with men called `Left`, `Quarter-back` and
# `for Frankford.`. A row whose man is a position word is not a row, and the page then
# falls back below eight, where it belongs.
_POSWORD = re.compile(r"\b(left|right|end|tackle|guard|cent(?:re|er)|quarter|half|full|"
                      r"back|position|weight)\b", re.I)


def _not_a_man(s):
    return bool(s) and (not s[0].isupper() or bool(_POSWORD.search(s)))


def measure():
    out = []
    for path in sorted(glob.glob(os.path.join(M, "*.htm*"))):
        h = open(path, encoding="utf-8", errors="replace").read()
        t = text(h); page = os.path.basename(path)
        rows = lineup_of(t)
        codes = [r["position"] for r in rows]
        if len(rows) < 8 or len(set(codes)) != len(codes): continue   # a roster repeats; a line-up does not
        sm = SUB.search(t); subs = []
        if sm:
            for piece in re.split(r"[;,]", sm.group(1)):
                piece = piece.strip().rstrip(".").strip("| ")
                if re.search(r"\bfo[er]\b", piece, re.I): subs.append(re.sub(r"\s*\|\s*", " ", piece))
        offs = [(k.title().replace("  ", " "), re.sub(r"\s*\|\s*", " ", v).strip()) for k, v in OFF.findall(t)]
        out.append({"page": page, "positions_found": len(rows),
                    "positions": [r["position"] for r in rows],
                    "away_men": [r["away"] for r in rows], "home_men": [r["home"] for r in rows],
                    "away_bracketed_as_printed": [r["away_bracketed"] for r in rows],
                    "home_bracketed_as_printed": [r["home_bracketed"] for r in rows],
                    "substitutions": subs, "officials": offs})
    # A GAME LINE-UP NAMES ELEVEN DIFFERENT MEN; AN HONOURS LIST REPEATS CLUBS in its left
    # column. This was the second inline rewrite of 10 September, now part of the reader.
    #
    # THE BRACKET FIX NEARLY BROKE THIS, 2026-09-11. An honours list prints `Player (Club)`,
    # so its repeated CLUBS are the bracketed part; with the bracket set aside the left
    # column held eleven different men and the 1928 all-pro list read as a game. The left
    # column is therefore read here AS IT WAS PRINTED IN THAT PLACE -- the bracketed name
    # where there is one -- which is exactly what the reader returned before the fix, and
    # an honours row keeps that reading, because the honours ingest reads its left column
    # as the club. A fix to game line-ups must not move an honours list.
    games, honours = [], []
    for x in out:
        printed_left = [b or a for a, b in zip(x["away_men"], x["away_bracketed_as_printed"])]
        left = [v for v in printed_left if v]
        dup = len(left) - len(set(left))
        if dup >= 2:
            honours.append({**x, "away_men": printed_left, "_repeats_in_the_left_column": dup})
        else:
            games.append({**x, "_repeats_in_the_left_column": dup})
    return {"games": games, "honours": honours}


def _rows(d):
    return {x["page"]: x for x in d["games"] + d["honours"]}


def diff(old, new):
    """Every page whose read changed, field by field. `away_club`/`home_club` are not
    compared: this reader deliberately does not produce them."""
    o, n = _rows(old), _rows(new)
    keys = ("positions", "away_men", "home_men", "substitutions", "officials")
    out = {}
    for p in sorted(set(o) | set(n)):
        if p not in o or p not in n:
            out[p] = "only in " + ("new" if p in n else "old"); continue
        ch = {k: (o[p].get(k), n[p].get(k)) for k in keys if o[p].get(k) != n[p].get(k)}
        if [x["page"] for x in old["games"]].count(p) != [x["page"] for x in new["games"]].count(p):
            ch["class"] = ("games" if p in [x["page"] for x in old["games"]] else "honours",
                           "games" if p in [x["page"] for x in new["games"]] else "honours")
        if ch: out[p] = ch
    return out


def main(argv):
    # Round-tripped, so the comparison is against what would be WRITTEN: officials are
    # tuples in memory and lists on disk, and a tuple never equals a list.
    new = json.loads(json.dumps(measure()))
    old = json.load(open(OUT)) if os.path.exists(OUT) else None
    if old is None:
        raise SystemExit(f"{OUT} is absent -- nothing to compare against. Run with --write "
                         "only if a first measurement is intended.")
    d = diff(old, new)
    print(f"GHOSTS LINE-UPS   ({'WRITE' if '--write' in argv else 'dry run'})")
    print(f"  game line-ups {len(new['games'])}, honours lists {len(new['honours'])}")
    print(f"  pages whose read changed: {len(d)}")
    for p, ch in d.items():
        print(f"    {p}: {ch if isinstance(ch, str) else sorted(ch)}")
    if "--write" in argv:
        tmp = OUT + ".tmp"
        json.dump(new, open(tmp, "w"), indent=1); os.replace(tmp, OUT)
        print(f"  wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
