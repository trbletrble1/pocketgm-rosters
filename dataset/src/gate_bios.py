"""Gate for the biography layers. Properties, over the WHOLE population, not the
fifty. Fails loudly on the first property broken. Each property is a fix that
shipped on 2026-09-06 and this is the check that ships with it.

  P1  identity is not in the prose: no bio says born / college / high school /
      hometown / drafted / pounds outside a guide's quoted text.
  P2  one name per club per bio: a club code is never rendered under two names.
  P3  the lead sentence never names the same club twice.
  P4  a disputed birth date is never picked: every man in the disputed set has
      more than one birth_date value in his panel and the field is listed under
      disagreements.
  P5  a guide's prose wins the close outright: whenever notes_excerpt() returns
      text, the close is the notes close.
  P6  no backfill: a bio with no close fact ends after the career; a close is
      never a hometown or a high school.
  P7  at most three numbers in a bio, outside quoted guide text.

  python3 src/gate_bios.py [--sample N]
"""
import os, re, sys, json, random, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from bio_select import Tables, select, notes_excerpt, club_name, seasons, _club_table
from bio_write import write

# lowercase words only: "State College" is a town and "Pounds" is a surname
IDENT = re.compile(r"\b([Bb]orn|college|high school|hometown|[Dd]rafted|pounds|weighed|stood)\b")
ALL_NAMES = None


def unquoted(text):
    return re.sub(r"“[^”]*”", "", text)


def club_names_in(text, codes_years):
    """Which held club names for these codes appear in the text, per code."""
    out = collections.defaultdict(set)
    for code, years in codes_years.items():
        for y in years:
            nm = club_name(code, y)
            if nm and nm != code and nm in text: out[code].add(nm)
    return out


def main():
    T = Tables()
    ids = sorted(T.people)
    population = len(ids)
    if "--sample" in sys.argv:
        random.seed(7); ids = random.sample(ids, int(sys.argv[sys.argv.index("--sample") + 1]))
    counts = collections.Counter(); fails = []
    for g in ids:
        F = select(T, g)
        if not F: continue
        text = write(F); plain = unquoted(text)
        counts["bios"] += 1
        # P1
        if IDENT.search(plain): fails.append(("P1", g, F["name"], text)); continue
        # P2: one name per club (codes with a rename during his tenure). Names are
        # matched as whole names: "Brooklyn Tigers" inside "Boston Yanks/Brooklyn Tigers"
        # is a merged club's own name, not a second name for the Dodgers.
        # the club is the club table's club, not the code: a code the table splits
        # into two clubs (CFLOTT: Rough Riders to 1996, Renegades from 2002) may
        # carry two names in one bio, one per club
        cy = collections.defaultdict(set)
        for s_ in seasons(T.people[g]):
            hit = _club_table().resolve(s_["club"], s_["year"], None, source="season_key")
            cy[(hit[0] if hit else s_["club"], s_["club"])].add(s_["year"])
        def mentions_of(nm, text, article="the "):
            return [m.start() for m in re.finditer(r"(?<![/\w])" + re.escape(article + nm) + r"(?![/\w])", text)]
        for (cid, code), years in cy.items():
            names = {club_name(code, y) for y in years if club_name(code, y) != code}
            shown = {nm for nm in names if mentions_of(nm, plain)}
            if len(shown) > 1:
                # A second name is EXPLAINED when the prose introduces it as a rename
                # of the club already named. bio_write renders that chain as
                #   "the Detroit Heralds, later the Detroit Tigers, from 1920 to 1921"
                # so the marker is a comma (or a paren), then earlier/later/then, and
                # what follows is the club's WHOLE name. The old pattern looked for
                # "(later the Tigers" -- an open paren the writer never emits, and the
                # last word of the name rather than the name -- so it matched nothing
                # and every renamed club failed P2. It went unseen because the gate is
                # usually run --sample, and 6 of 43,517 people are affected.
                def explained(nm):
                    # bio_write introduces a rename in two shapes, and the exemption
                    # must know both or it exempts neither:
                    #   "the Detroit Heralds, later the Detroit Tigers, from 1920"  (L227, whole name)
                    #   "the Cleveland Indians (later the Bulldogs; 1923-25)"       (L189/L223, last word)
                    tail = re.escape(nm.split()[-1])
                    return re.search(r"[(,] ?(earlier|later|then) the (%s|%s)\b"
                                     % (re.escape(nm), tail), plain)
                bare = [n for n in shown if not explained(n)]
                if len(bare) > 1: fails.append(("P2", g, F["name"], text)); break
        # P3: the same club is never named twice in a row in the lead sentence
        # ("the X" mentions; "a new X" is a different club and says so)
        lead = re.split(r"(?<=[.;])\s+(?=[A-Z])", plain)[0]
        mentions = []
        names = {club_name(code, y) for (cid, code), years in cy.items() for y in years}
        for nm in names:
            for pos in mentions_of(nm, lead): mentions.append((pos, nm))
        mentions.sort()
        if any(x[1] == y[1] for x, y in zip(mentions, mentions[1:])): fails.append(("P3", g, F["name"], lead))
        # P4
        V = F["vitals"]
        if g in T.disputed:
            vals = {json.dumps(r["value"]) for r in V.get("birth_date", [])}
            if len(vals) < 2 or "birth_date" not in V.get("disagreements", []):
                fails.append(("P4", g, F["name"], json.dumps(V.get("birth_date"))))
            counts["disputed_listed"] += 1
        # P5
        if g in T.notes and notes_excerpt(T.notes[g]["text"]) and F["close_kind"] != "notes":
            fails.append(("P5", g, F["name"], F["close_kind"]))
        # P6
        if F["close_kind"] in ("hometown", "high_school", "college", "birth_date"):
            fails.append(("P6", g, F["name"], F["close_kind"]))
        counts["close:" + str(F["close_kind"])] += 1
        # P7
        undated = re.sub(r"\b[A-Z][a-z]+ \d{1,2}, (1[89]|20)\d{2}\b", "", plain)      # January 20, 1985
        nums = re.findall(r"\b\d[\d,]*\b", re.sub(r"\b(1[89]|20)\d{2}(–\d{2,4})?\b", "", undated))
        if len(nums) > 3: fails.append(("P7", g, F["name"], text))
    sampled = len(ids) < population
    print(json.dumps({"checked": counts["bios"], "of_people": population,
                      "sampled": sampled,
                      "closes": {k[6:]: v for k, v in counts.items() if k.startswith("close:")},
                      "disputed_birth_dates_listed": counts["disputed_listed"], "failures": len(fails)}, indent=1))
    for f in fails[:20]: print("FAIL", *f)
    if len(fails) > 20: print(f"... and {len(fails) - 20} more")
    if fails: sys.exit(1)
    # A sample that finds nothing has not shown the property holds, and must not say
    # so. P2 was broken for every renamed club and --sample 1000 still reported
    # "all properties hold": the 6 affected men are 0.01% of the index, so a sample
    # of a thousand missed them every time. Only the full sweep is a pass.
    if sampled:
        print(f"gate_bios: no failure in a SAMPLE of {len(ids)} of {population} "
              f"-- this is not a pass; run without --sample to gate")
    else:
        print(f"gate_bios: all properties hold ({population} people, full sweep)")


if __name__ == "__main__":
    main()
