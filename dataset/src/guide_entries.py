"""Find where one man's press-guide entry ends and the next begins, and take the
free text whole. Read-only; writes nothing.

THE BOUNDARY IS THE WHOLE PROBLEM. A block attached to the wrong man is
undetectable and permanent, and this project has produced that error twice --
Perko's 1946 notes running on into Tony Compagno's entry, and Wedemeyer's header
split across two lines nearly merging two men. So the boundary is PROVED, never
inferred, and an entry that cannot be proved is DROPPED and counted.

THE PROOF, in three parts:
  1. a span runs from one HEADER-SHAPED LINE to the next, so by construction it
     opens on a header;
  2. inside the span, no OTHER rostered man may appear in header position. This
     is the Perko check: a missed header would silently merge two men, and this
     catches it from the roster side rather than the layout side;
  3. the span must carry at least one per-player label and be of sane length.

Header shape is detected GENERICALLY -- a name-like line carrying at least two
vitals signals -- and not from the roster, so that a man the archive does not hold
still breaks the span rather than being swallowed into his neighbour's entry.
"""
import os, re, collections, unicodedata

POS = (r"Quarterback|Running Back|Fullback|Halfback|Tailback|Wide Receiver|Receiver|Tight End|"
       r"Offensive Tackle|Offensive Guard|Defensive Tackle|Defensive End|Defensive Back|Guard|Tackle|"
       r"Center|Linebacker|Cornerback|Safety|Kicker|Punter|End|Nose Tackle|Defensive Lineman|"
       r"QB|RB|FB|HB|WR|TE|OT|OG|DT|DE|DB|CB|LB|LS|SS|FS|OL|DL|NT|PK|P|K|G|T|C|S")
SIG = [re.compile(r"\((\d{1,2})\)"), re.compile(r"\b(?:No\.?|#)\s?\d{1,2}\b"),
       re.compile(r"\b[4-7][-'’]\s?\d{1,2}\b"), re.compile(r"\b(?:Ht|HT|Height|HEIGHT)\b\s?:"),
       re.compile(r"\b(?:Wt|WT|Wr|Weight|WEIGHT)\b\s?:"), re.compile(r"\b[12]\d{2}\b"),
       re.compile(r"\b(?:%s)\b" % POS), re.compile(r"\b(?:College|COLLEGE)\b\s?:"),
       re.compile(r"\b\d{1,2}(?:st|nd|rd|th)\s+(?:Year|Season)\b|\b\d{1,2}\s*Yr\.?\b|"
                  r"\b(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Rookie)\s+Year\b", re.I),
       re.compile(r"\b(?:Born|BORN|Birthdate|BIRTHDATE)\b\s?:"),
       re.compile(r"\b(?:Years? in NFL|NFL EXPERIENCE|Acquired|ACQUIRED|How Acquired|HOW ACQUIRED)\b")]
NAME = re.compile(r"^[\s>|=~*•·\.\-]{0,6}((?:[A-Z][A-Za-z'’\.\-]+|[A-Z]{2,})"
                  r"(?:\s+(?:\([A-Za-z'’\.\-]+\)|[A-Z][A-Za-z'’\.\-]*|[A-Z]{2,}|[A-Z]\.))"
                  r"{1,3})(?=[\s,]|$)")
LABEL = re.compile(r"(?:(?<=^)|(?<=[\s>|]))([A-Z][A-Za-z][A-Za-z .,/&'-]{0,26}?)\s?:\s", re.M)
PROSE_LABELS = {"PERSONAL", "PRO", "PRO CAREER", "COLLEGE", "COLLEGE, PERSONAL", "COLLEGE/PERSONAL",
                "COLLEGIATE, PERSONAL", "TRANSACTIONS", "PRO RECORD", "COLLEGE RECORD",
                "PRO PLAYING RECORD", "COLLEGE PLAYING RECORD", "PRO COACHING RECORD"}
ANCHOR = PROSE_LABELS | {"BORN", "HIGH SCHOOL", "HT", "WT", "HEIGHT", "WEIGHT", "BIRTHDATE",
                         "BIRTHPLACE", "COLLEGE", "ACQUIRED", "HOW ACQUIRED", "NFL EXPERIENCE", "AGE"}
STOP = re.compile(r"\b(RECORDS|STATISTICS|ALL-TIME|YEAR[- ]BY[- ]YEAR|TOTALS|STANDINGS|SCHEDULE)\b")


def norm(n):
    n = unicodedata.normalize("NFKD", n or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", n.lower()).strip()


def lines_with_offsets(t):
    out, p = [], 0
    for ln in t.split("\n"):
        out.append((p, ln)); p += len(ln) + 1
    return out


def header_lines(t):
    """Every line that LOOKS like the head of a player entry: a name, and at least
    two vitals signals on it or the two lines under it."""
    L = lines_with_offsets(t); out = []
    for i, (p, ln) in enumerate(L):
        s = ln.strip()
        if not (4 <= len(s) <= 90): continue
        m = NAME.match(ln)
        if not m: continue
        nm = m.group(1).strip()
        if len(nm.split()) < 2: continue
        if STOP.search(ln): continue
        # the next four NON-EMPTY lines: OCR routinely puts two or three blank lines
        # between a name and its vitals, and a fixed three-line window sees only those
        nxt, j = [], i + 1
        while j < len(L) and len(nxt) < 4:
            if L[j][1].strip(): nxt.append(L[j][1])
            j += 1
        window = " ".join([ln] + nxt)
        hits = sum(1 for r in SIG if r.search(window))
        if hits >= 2: out.append({"pos": p, "line": ln.rstrip(), "name": nm, "signals": hits})
    return out


def name_pattern(name):
    """Surname exact, forename by its first three letters, within a short span, so a
    guide printing 'John McKee (Johnny) Allen' still finds Johnny Allen. Never
    surname alone: that is how a namesake gets someone else's entry."""
    parts = norm(name).split()
    if len(parts) < 2: return None
    return re.compile(r"\b" + re.escape(parts[0][:3]) + r"[A-Za-z .'’()\-]{0,40}?"
                      + re.escape(parts[-1]) + r"\b")


def real_headers(t, H):
    """A header-shaped line only OPENS AN ENTRY if a per-player label follows it
    within 600 characters. Stat tables and section titles are header-shaped too, and
    splitting on them cuts a man's entry in half; they are still counted as intruders
    by the roster check below, so dropping them here cannot merge two men."""
    out = []
    for h in H:
        seg = t[h["pos"]: h["pos"] + 1200]
        if any(m.group(1).strip().upper() in ANCHOR for m in LABEL.finditer(seg)):
            out.append(h)
    # A HEADER SPLIT ACROSS LINES IS ONE HEADER. Wedemeyer's 1948 header broke over
    # two lines and nearly merged two men; here the same break makes a span of a few
    # characters that would be thrown away. Real headers closer together than 150
    # characters are collapsed into one, carrying both lines for the name match.
    merged = []
    for h in out:
        if merged and h["pos"] - merged[-1]["pos"] < 150:
            merged[-1]["line"] = merged[-1]["line"] + " " + h["line"].strip()
            merged[-1]["name"] = merged[-1]["name"] + " " + h["name"]
            merged[-1]["merged_lines"] = merged[-1].get("merged_lines", 1) + 1
        else:
            merged.append(dict(h))
    return merged


def entries(t, roster):
    """roster: {pid: name}. Returns proved entries and the reasons for every drop."""
    H = real_headers(t, header_lines(t))
    if not H: return [], collections.Counter({"no header-shaped line in the guide": 1})
    pats = {pid: name_pattern(nm) for pid, nm in roster.items()}
    pats = {k: v for k, v in pats.items() if v}
    low = t.lower()
    # every place a rostered man's name stands in HEADER POSITION, computed once
    head_positions = {}
    for pid, p in pats.items():
        spots = []
        for m in p.finditer(low):
            ls = low.rfind("\n", 0, m.start()) + 1
            if m.start() - ls <= 8 and sum(1 for r in SIG if r.search(t[ls:ls + 220])) >= 2:
                spots.append(m.start())
        if spots: head_positions[pid] = spots
    kept, dropped = [], collections.Counter()
    for i, h in enumerate(H):
        a = h["pos"]
        b = H[i + 1]["pos"] if i + 1 < len(H) else len(t)
        span = t[a:b]
        # the cap is a sanity guard, not the proof. The proof that a long span holds
        # one man is the roster check below; capping tightly only threw away entries
        # whose guide puts a page of statistics between one man and the next.
        if not (120 <= len(span) <= 60000):
            dropped["span length outside 120-60,000 characters"] += 1; continue
        labs = [m.group(1).strip() for m in LABEL.finditer(span)]
        if not any(l.upper() in ANCHOR for l in labs):
            dropped["no per-player label inside the span"] += 1; continue
        # who does the HEADER name? match against the roster on the header line only
        head_low = h["line"].lower()
        who = [pid for pid, p in pats.items() if p.search(head_low)]
        # THE PERKO CHECK: another rostered man in header position inside the span.
        # Positions are found ONCE per guide, not once per span: at corpus scale the
        # per-span scan was the whole cost.
        intruder = set()
        for pid, pos in head_positions.items():
            if pid in who: continue
            if any(a <= q < b for q in pos): intruder.add(pid)
        if intruder:
            dropped["another rostered man appears in header position inside the span"] += 1; continue
        if len(who) > 1:
            dropped["the header line names more than one rostered man"] += 1; continue
        kept.append({"start": a, "end": b, "header": h["line"], "header_name": h["name"],
                     "person": who[0] if who else None, "text": span})
    return kept, dropped


def blocks(entry):
    """The free text, whole and verbatim, with the guide's own label where it has one.
    Nothing is summarised, rewritten, normalised or OCR-corrected."""
    t = entry["text"]; out = []
    marks = [(m.start(), m.end(), m.group(1).strip()) for m in LABEL.finditer(t)]
    keep = [(s, e, l) for s, e, l in marks if l.upper() in PROSE_LABELS]
    for j, (s, e, lab) in enumerate(keep):
        nxt = len(t)
        for s2, _, l2 in marks:
            if s2 > e and (l2.upper() in ANCHOR):
                nxt = s2; break
        seg = t[e:nxt]
        if len(re.findall(r"[a-z]{3,}", seg)) >= 12:
            out.append({"label_as_printed": lab, "text": seg,
                        "start": entry["start"] + e, "end": entry["start"] + e + len(seg)})
    if not out:
        # unlabelled trailing prose: the run after the header that reads as sentences
        nl = t.find("\n")
        seg = t[nl + 1:] if nl > 0 else ""
        if len(re.findall(r"[a-z]{3,}", seg)) >= 20:
            out.append({"label_as_printed": None, "text": seg,
                        "start": entry["start"] + nl + 1, "end": entry["start"] + nl + 1 + len(seg)})
    return out


VIT = {"height": re.compile(r"\b(?:Ht|HT|Height|HEIGHT)\b\s?:?\s*([4-7][-'’]\s?\d{1,2})|"
                            r"(?<![\d-])([4-7]-\d{1,2})(?![\d-])"),
       "weight": re.compile(r"\b(?:Wt|WT|Wr|Weight|WEIGHT)\b\s?:?\s*([12]\d{2})\b|"
                            r"\b([4-7]-\d{1,2})\s+([12]\d{2})\b"),
       "jersey": re.compile(r"\((\d{1,2})\)|\b(?:No\.?|#)\s?(\d{1,2})\b|(?<=\s)(\d{1,2})\s*$")}


def vitals(entry):
    """Height, weight and jersey AS THAT GUIDE PRINTED THEM, from the header only."""
    head = entry["text"][:max(0, entry["text"].find("\n", 0)) + 260] or entry["text"][:260]
    out = {}
    for k, r in VIT.items():
        m = r.search(head)
        if m: out[k] = next((g for g in m.groups() if g), None)
    if out.get("weight") and out.get("height") and out["weight"] == out["height"]: out.pop("weight")
    return {k: v.strip() for k, v in out.items() if v}


def club_norm(s):
    """Like norm(), but KEEPS DIGITS. Stripping them turned '49ers' into 'ers',
    which matched as a substring of Packers, Steelers, Chargers and sixty more, so
    a 49ers guide resolved a roster of 1,201 men drawn from every club in the league
    and a prose block could have been attached to a man who was never there."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()


def resolve_club(nick, year, clubs, filename="", _fallback=True):
    """The archive club codes a guide's club token denotes, that season.

    The nickname must be the club's LAST WORD, not a substring of its name. Where
    two clubs share a nickname -- the Detroit Lions and the BC Lions -- the guide's
    own filename decides, and if it cannot, BOTH are returned so the ambiguity is
    visible rather than silently resolved to one."""
    n = club_norm(nick.replace("-", " "))
    last = n.split()[-1] if n.split() else ""
    cand = []
    for k, v in clubs.items():
        code, y = k.split("|")
        if y != str(year): continue
        name = club_norm(v)
        parts = name.split()
        if not parts: continue
        if parts[-1] == last or name == n: cand.append((code, name))
    if len(cand) > 1 and filename:
        f = club_norm(filename.replace("-", " "))
        narrowed = [c for c in cand if any(w in f.split() for w in c[1].split()[:-1])]
        if len(narrowed) == 1: return [narrowed[0][0]], "the filename names the city"
    if cand:
        return sorted({c[0] for c in cand}), ("one club" if len(cand) == 1 else "ambiguous nickname")
    # TWO FALLBACKS, each only when the plain nickname found nothing. Measured on the
    # 95 guides that resolved to no club: 34 carried a slug with a league or
    # publication word on it ('buffalo-bills-aafc', 'chicago-bears-yearbook'), and 3
    # carried a nickname the club did not have that year ('chiefs' in 1962, when they
    # were the Dallas Texans), which the filename's city settles. 58 stay unresolved:
    # Hall of Fame books, 'official', and nicknames with no city in the filename.
    if not _fallback:
        return [], "no club of that name that season"
    words = [w for w in nick.replace("-", " ").lower().split() if w not in _DROP]
    if words and words != nick.lower().split():
        r, w = resolve_club(" ".join(words), year, clubs, filename, _fallback=False)
        if r: return r, "slug stripped of league or publication words"
        r, w = resolve_club(words[-1], year, clubs, filename, _fallback=False)
        if r: return r, "slug's last word as the nickname"
    if filename:
        city = [w for w in club_norm(filename.replace("-", " ").replace(".txt", "")).split()
                if w not in _DROP and not w.isdigit() and w != n]
        hits = []
        for k, v in clubs.items():
            code, y = k.split("|")
            if y == str(year) and city and all(w in club_norm(v).split() for w in city[-2:] if w):
                hits.append(code)
        if len(set(hits)) == 1: return sorted(set(hits)), "the filename's city, and that year's club there"
    return [], "no club of that name that season"


_DROP = {"aafc", "usfl", "afl", "wfl", "xfl", "cfl", "nfl", "yearbook", "media", "guide",
         "press", "official", "book", "review", "roster"}
