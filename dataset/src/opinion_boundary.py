"""Where does the COURT's text begin?

A legal-database page can stack three layers: site chrome, a machine-generated
summary, and the opinion. Only the third is `observed`. Detected structurally,
in priority order, and every rule below was tested against the 16 documents held.
"""
import re

SUMMARY_HEADS = ("Legal Issues Presented", "Arguments of the Parties",
                 "Table of Precedents Cited", "Court's Reasoning and Analysis",
                 "Factual and Procedural Background")

# NOTE: no \b after "J." - a period followed by a space has no word boundary,
# which silently dropped every California opinion from the first audit.
JUDGE = re.compile(r"\b[A-Z][A-Za-z'\-]{2,20}\s*,\s*"
                   r"(?:Circuit |District |Chief |Senior |Acting )?"
                   r"(?:Judge|Justice|C\.\s*J\.|J\.)")

def find(text):
    """-> (offset, rule, has_summary_layer)

    Tested against all 16 documents held. Three failures the naive rules produced,
    and what fixed them:
      * Cowan  - `COPE, Judge` appears FIRST as a metadata field ("JUDGES COPE,
                 Judge."). Excluded by the preceding-JUDGES test.
      * Kapp   - the LAST judge marker is a citation of another judge inside the
                 opinion ("Marshall, J. in Flood, supra"). Take the FIRST valid one.
      * Gardin,
        Heidel - Tax Court documents put an `OPINION` heading MID-document, after
                 the findings of fact. Taking it would cut off exactly where the
                 money is. Take the EARLIEST boundary, not the OPINION heading.
    """
    flat = re.sub(r"\s+", " ", text)
    has_summary = sum(h in flat for h in SUMMARY_HEADS) >= 2

    if has_summary:
        m = list(re.finditer(r"\bJUDGMENT\b", flat))
        if m:
            return m[-1].end(), "after the last JUDGMENT marker (summary layer present)", True

    cands = []
    m = re.search(r"\bOPINION\b", flat)
    # only trust an OPINION heading if a judge's name follows soon after -
    # otherwise it is a navigation element (vLex) rather than a section heading
    if m and JUDGE.search(flat[m.end():m.end() + 400]):
        cands.append((m.end(), "after the first OPINION heading"))
    for j in JUDGE.finditer(flat):
        before = flat[max(0, j.start() - 10):j.start()]
        if "JUDGES" in before.upper():
            continue                      # a metadata field, not the opinion
        tail = flat[j.end():j.end() + 120]
        # prose, not a citation list. An all-caps section heading may follow the
        # judge's name ("SWEIGERT, District Judge. THE RECORD ..."), so test for a
        # lowercase run anywhere nearby rather than a Capitalised next word.
        if re.match(r"[:.]?\s", tail) and re.search(r"[a-z]{4,}", tail):
            cands.append((j.start(), "first judge marker followed by prose"))
            break
    if cands:
        off, rule = min(cands)
        return off, rule, has_summary
    return 0, "NO BOUNDARY FOUND - treat the whole document as suspect", has_summary
