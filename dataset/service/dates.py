"""Read a date string the way a person reads it, without rewriting it.

The store holds what the source printed: `May 12, 1925`, `1925-05-12`, `December
1977`, `c. 1960`, `August 9, 1989 (aged 72)`, `April 3, 1925 in Warren, Ohio.`
Ruled 2026-09-07: the strings are NEVER standardised. This module returns a
reading -- (year, month, day) at the precision the string carries -- so that two
strings can be compared on the calendar day. The reading is a DERIVED value and
is labelled as one wherever it is shown.

A string this cannot read returns None, and gate G1 refuses to publish a read
model holding one that is not declared in declarations/dates-as-printed.json.
"""
import re

RECIPE = "date-reading@v1"

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})
_MONTHS["sept"] = 9

_AGE = re.compile(r"\s*\((?:aged?|age)\b[^)]*\)\s*$", re.I)           # "(aged 72)", "(age )", "(aged 64 or 65)"
_WIKI = re.compile(r"^\{\{nowrap\|")                                  # a template fragment left in the text
_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_ISO_YM = re.compile(r"^(\d{4})-(\d{1,2})$")
_YEAR = re.compile(r"^(\d{4})$")
_MDY = re.compile(r"^([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})$")
_MY = re.compile(r"^([A-Za-z]+)\.?,?\s+(\d{4})$")
_DMY = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\.?,?\s+(\d{4})$")
_CIRCA = re.compile(r"^(?:c\.?|ca\.?|circa|about|abt\.?)\s*(\d{4})$", re.I)
_QUERY = re.compile(r"^(\d{4})\s*\?$")
# a date followed by a place: "April 3, 1925 in Warren, Ohio." / "August 7, 1901Avilés, Asturias, Spain"
_LEADING = re.compile(r"^((?:[A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})|(?:\d{4}-\d{1,2}-\d{1,2}))(?=\s+in\s|[A-Za-z(\)])")


def read(s):
    """-> {"year", "month", "day", "precision": day|month|year, "approximate": bool,
           "trailing": str|None} or None if the string cannot be read as a date."""
    if s is None: return None
    t = str(s).strip()
    if not t: return None
    approx = False; trailing = None
    t = _WIKI.sub("", t)
    t2 = _AGE.sub("", t)
    if t2 != t: trailing = t[len(t2):].strip(); t = t2
    t = t.rstrip(")").strip()
    m = _LEADING.match(t)
    if m and m.end() < len(t):
        trailing = (t[m.end():].strip() + (" " + trailing if trailing else "")).strip()
        t = m.group(1)
    m = _ISO.match(t)
    if m:
        y, mo, d = map(int, m.groups())
        return _mk(y, mo, d, "day", approx, trailing)
    m = _ISO_YM.match(t)
    if m:
        y, mo = map(int, m.groups()); return _mk(y, mo, None, "month", approx, trailing)
    m = _MDY.match(t)
    if m and m.group(1).lower() in _MONTHS:
        return _mk(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)), "day", approx, trailing)
    m = _DMY.match(t)
    if m and m.group(2).lower() in _MONTHS:
        return _mk(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)), "day", approx, trailing)
    m = _MY.match(t)
    if m and m.group(1).lower() in _MONTHS:
        return _mk(int(m.group(2)), _MONTHS[m.group(1).lower()], None, "month", approx, trailing)
    m = _YEAR.match(t)
    if m: return _mk(int(m.group(1)), None, None, "year", approx, trailing)
    m = _CIRCA.match(t) or _QUERY.match(t)
    if m: return _mk(int(m.group(1)), None, None, "year", True, trailing)
    return None


def _mk(y, mo, d, precision, approx, trailing):
    if mo is not None and not 1 <= mo <= 12: return None
    if d is not None and not 1 <= d <= 31: return None
    return {"year": y, "month": mo, "day": d, "precision": precision,
            "approximate": approx, "trailing": trailing or None}


def key(reading):
    """The comparison key: the calendar day where the string carries one, else the month
    or the year. Two readings with the same key are 'the same day' at the coarser precision
    of the two ONLY if a caller asks for that; this key does not coarsen."""
    if reading is None: return None
    return (reading["year"], reading["month"], reading["day"])


def same_day_groups(items):
    """items: [(literal, reading)]. Groups literals that read as the same calendar day.
    A partial reading (year only, or year-month) joins a full date ONLY when exactly one
    group agrees with it; when none or more than one does it stands alone -- a year is not
    evidence for one of two days in that year. Unreadable strings are left to the caller.
    Deterministic: groups ordered by day, then by first appearance."""
    full = {}   # (y,m,d) -> [literals]
    partial = []
    for lit, r in items:
        if r is None: continue
        if r.get("day") is not None: full.setdefault(key(r), []).append(lit)
        else: partial.append((r, lit))
    keys = sorted(full)
    groups = [list(full[k]) for k in keys]
    extra = []
    for r, lit in partial:
        home = [i for i, k in enumerate(keys) if k[0] == r["year"] and (r.get("month") is None or k[1] == r["month"])]
        if len(home) == 1: groups[home[0]].append(lit)
        else: extra.append([lit])
    return groups + extra
