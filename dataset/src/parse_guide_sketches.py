"""Parse player sketches from a media guide. ONE GUIDE: LA Dons 1948.

Two things here are load-bearing and neither is a guess.

THE SKETCH BOUNDARY. A sketch runs from its "NAME . . . POSITION" header to the
line before the next. The header is anchored on the POSITION VOCABULARY, not on
punctuation, because the OCR mangles the dot leaders (%§END, © © CENTER). The
boundary is then PROVED independently: every man has exactly one BORN: line, so a
sketch holding two means a header was missed and two men merged. Those are
DROPPED, never rescued by loosening the boundary -- one man's war record on
another man is undetectable and permanent.

THE HONOURS PARENT. HONORS is nested: it follows HIGH SCHOOL FOOTBALL, COLLEGE
FOOTBALL or MAJOR LEAGUE FOOTBALL and belongs to whichever it sits under. The
parent goes IN THE PREDICATE NAME -- guide.HONORS@COLLEGE FOOTBALL -- so an
honour cannot be stored without saying what it is an honour in. Where no parent
heading precedes it, the predicate is guide.HONORS@UNATTACHED, which makes
"unattached" a thing you must look at rather than a silent default.
"""
import re, json, collections

POS = r'(KICKER|END|TACKLE|GUARD|CENTER|QUARTERBACK|HALFBACK|FULLBACK)'
HDR = re.compile(r"^\s*([A-Z][A-Z.'’()\- ]{2,40}?)\s*[^A-Za-z]{3,}\s*" + POS + r"\s*$")
PAGE = re.compile(r'^\s*(\d+\s+)?LOS ANGELES DONS(\s*\.?\s*\d+)?\s*$')
LABEL = re.compile(r"^([A-Z][A-Z .'/]{2,30}?):\s*(.*)$")
HWL = re.compile(r"^\s*(\d[’'`]?\s?\d{0,2}[”\"]?)\s+(.+?)\s+(\d{2,3})\s*[Il]bs?\.?\s*$")
# an honour belongs to whichever of these it sits under
HONOUR_PARENTS = ("HIGH SCHOOL FOOTBALL", "COLLEGE FOOTBALL", "MAJOR LEAGUE FOOTBALL",
                  "SERVICE FOOTBALL", "SERVICE RECORD")


def parse(path, section_marker="Player Sketches"):
    L = [l.rstrip() for l in open(path, encoding="utf-8", errors="replace")]
    start = next(i for i, l in enumerate(L) if section_marker in l)
    hdrs = [(i, HDR.match(L[i])) for i in range(start, len(L))
            if HDR.match(L[i]) and not PAGE.match(L[i])]
    born_total = sum(1 for i in range(start, len(L)) if L[i].strip().startswith("BORN:"))
    clean, ambiguous = [], []
    for n, (i, m) in enumerate(hdrs):
        j = hdrs[n + 1][0] if n + 1 < len(hdrs) else len(L)
        body = L[i + 1:j]
        nb = sum(1 for x in body if x.strip().startswith("BORN:"))
        rec = {"name_as_printed": m.group(1).strip(), "position": m.group(2),
               "span": [i, j], "fields": collections.OrderedDict(),
               "honours": [], "raw": "\n".join(x for x in body if x.strip())}
        cur = None          # current label, for continuation lines
        parent = None       # current honours parent heading
        for x in body:
            s = x.strip()
            if not s:
                continue
            hw = HWL.match(s)
            if hw and "height" not in rec["fields"]:
                rec["fields"]["height"] = hw.group(1)
                rec["fields"]["college_header"] = hw.group(2).strip()
                rec["fields"]["weight"] = hw.group(3)
                continue
            lm = LABEL.match(s)
            if lm:
                k, v = lm.group(1).strip(), lm.group(2).strip()
                if k == "HONORS":
                    rec["honours"].append({"parent": parent, "value": v})
                    cur = "__honour__"
                else:
                    rec["fields"][k] = v
                    cur = k
                    if k in HONOUR_PARENTS:
                        parent = k
                continue
            if re.match(r"^(Married|Single)\b", s):
                rec["fields"]["_marital"] = s; cur = None; continue
            # continuation of the previous line
            if cur == "__honour__" and rec["honours"]:
                rec["honours"][-1]["value"] = (rec["honours"][-1]["value"] + " " + s).strip()
            elif cur and cur in rec["fields"]:
                rec["fields"][cur] = (rec["fields"][cur] + " " + s).strip()
        (clean if nb == 1 else ambiguous).append(
            rec if nb == 1 else (rec, f"{nb} BORN: lines -- a header was missed and "
                                      f"{nb} men merged"))
    return {"clean": clean, "ambiguous": ambiguous, "born_total": born_total,
            "headers": len(hdrs)}
