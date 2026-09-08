"""Per-club-run parsers for the 33 delimited pre-1950 guides (families C, D, E).

THE BOUNDARY PROOF. Entries are split on a header regex anchored on the POSITION
VOCABULARY or on a structural field line, never on punctuation, because OCR mangles
the punctuation. The split is then PROVED by an ANCHOR: a token that a man has
exactly once. Counted over the whole span (header + body), a missed header shows up
as TWO anchors in one span. That is the same test the Dons 1948 parse used with its
one BORN: line per man, generalised. A span with != 1 anchor is DROPPED and counted.

FAMILIES A AND B ARE NOT HERE. 17 prose-only guides have no field delimiters, so a
misread cannot be validated. They are a reading job.
"""
import re, collections

POS = (r"(?:KICKER|END|TACKLE|GUARD|CENTER|CENTRE|QUARTERBACK|HALFBACK|FULLBACK|"
       r"BACK|TAILBACK|WINGBACK|LINEMAN|Kicker|End|Tackle|Guard|Center|Quarterback|"
       r"Halfback|Fullback|Back|Tailback|Wingback)")

def _lines(path):
    return [l.rstrip("\n").rstrip() for l in open(path, encoding="utf-8", errors="replace")]

def split_entries(L, start, end, header_re, page_re=None):
    hdrs = []
    for i in range(start, end):
        m = header_re.match(L[i])
        if m and not (page_re and page_re.match(L[i])):
            hdrs.append((i, m))
    out = []
    for n, (i, m) in enumerate(hdrs):
        j = hdrs[n + 1][0] if n + 1 < len(hdrs) else end
        out.append((i, j, m))
    return out

def anchor_count(L, a, b, anchor_re):
    return sum(len(anchor_re.findall(L[k])) for k in range(a, b))

# ---------------------------------------------------------------- label readers
LBL_COLON = re.compile(r"^([A-Z][A-Za-z .'/&]{2,30}?)\s*:\s*(.*)$")
LBL_DASH  = re.compile(r"^([A-Z][A-Za-z .'/&]{2,30}?)\s*[—–]\s*(.*)$")
MARITAL   = re.compile(r"^(Married|Single|Marri|Is married|Is single)\b", re.I)

def read_labels(body, label_res, honour_parents=(), notes_labels=()):
    """Read `LABEL: value` / `LABEL— value` lines, keeping labels VERBATIM.
    Continuation lines append to the open label. Returns (fields, honours, notes)."""
    fields = collections.OrderedDict(); honours = []; notes = None; notes_label = None
    cur = None; parent = None; in_notes = False; nbuf = []; last = 0
    for _i, x in enumerate(body):
        s = x.strip()
        if not s:
            if in_notes: nbuf.append("")
            continue
        hit = None
        for lr in label_res:
            m = lr.match(s)
            if m:
                hit = (m.group(1).strip(), m.group(2).strip()); break
        if hit:
            last = _i + 1
            k, v = hit
            if k.upper() in notes_labels:
                in_notes = True; notes_label = k; nbuf = [v]; cur = None; continue
            in_notes = False
            if k.upper() == "HONORS" or k.upper() == "HONOURS":
                honours.append({"parent": parent, "value": v}); cur = "__h__"
            else:
                fields[k] = v; cur = k
                if k.upper() in honour_parents: parent = k
            continue
        if in_notes:
            nbuf.append(s); continue
        if MARITAL.match(s) and "_marital" not in fields:
            fields["_marital"] = s; cur = None; last = _i + 1; continue
        if cur == "__h__" and honours:
            honours[-1]["value"] = (honours[-1]["value"] + " " + s).strip(); last = _i + 1
        elif cur and cur in fields:
            fields[cur] = (fields[cur] + " " + s).strip(); last = _i + 1
    if nbuf:
        notes = "\n".join(nbuf).strip()
    return fields, honours, notes, notes_label, last

def trailing_prose(body, consumed_upto):
    """Unlabelled trailing prose block, VERBATIM, joined with newlines as printed."""
    blk = [x.rstrip() for x in body[consumed_upto:]]
    while blk and not blk[0].strip(): blk.pop(0)
    while blk and not blk[-1].strip(): blk.pop()
    return "\n".join(blk) if blk else None
