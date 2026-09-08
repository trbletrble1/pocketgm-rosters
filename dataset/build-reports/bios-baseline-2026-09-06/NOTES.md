# Bio baselines, 2026-09-06

`coach-bios.txt`, `coaching-only.txt`, `bios.txt` are the prints `gate_coach_runs.py` R4
holds the writer to. Rebaselined after patch 1 of the club job (runs named from the club
table) on Ryan's acceptance of all 21 changed bios; the twenty as they read before patch 1
are kept beside them as `coach-bios-before-patch1.txt`.

## Recorded, not ruled

Two of the accepted changes depend on the club table's `lineage_splits`, which is held for
a ruling: Joe Paopao (Ottawa Renegades 2002-05, not the Rough Riders, who folded in 1996)
and Shorty Barr (Racine Tornadoes 1926, not the Legion). If CFLOTT or RAC is later ruled
ONE club, both revert and this baseline must be regenerated deliberately.

## Rebaselined 2026-09-07 after the stint-shape fix and rebuild

The 1926 AFL (102 men) and the 1934 Reds (12) entered the index. Eleven coached men's
bios changed, every one a man who gained a 1926 AFL season (Flaherty: Wilson's
Wildcats; Grange, Scott, Griffen: New York Yankees; Strader, Sternaman: Chicago Bulls;
Pierotti: Boston Bulldogs; Nesser: Cleveland Panthers; Behman: Philadelphia Quakers;
Wycoff: Newark Demons; Armstrong: Rock Island). One writer fix rode with it: 'a new X'
is said only when the table holds two clubs of that name -- the 1925 NFL and 1926 AFL
Rock Island Independents are one club, corroborated by the men. Previous prints kept as
*-before-rebuild-2026-09-07.txt.

## Rebaselined 2026-09-07 (second) after LVR 2020 landed

The twenty and the fifteen are identical. The fifty player bios changed SAMPLE, not text:
print_bios draws with a fixed seed from the whole population, and 86 men entering shifts
which fifty are drawn (ten different men). No bio of a man in both draws changed. Previous
print kept as bios-before-lvr-2026-09-07.txt. R4 is fragile to population growth by
construction; a draw from a stored id list would fix that and is noted, not done.

## Rebaselined 2026-09-07 (third): the media-guide seasons and Fetching's Arena rosters

49 of 737 coached men's bios changed: 39 of the 73 men whose media-guide staff records
joined them (they gained the guide's seasons and its role strings), 9 who gained an ARENA
season from build/arena-1987-2019.json, and Wally Buono, whose text reflowed to another
true variant because the writer's variant choice depends on population statistics that
moved when 1,794 promoted coaches entered. Previous prints kept as *-before-guides-2026-09-07.txt.

R4 is fragile to population growth twice over: print_bios draws its fifty with a fixed
seed from the whole population, and the writer's variant selection is population-dependent.
A draw from a stored id list would fix the first; the second is by design.

## Rebaselined 2026-09-07 (fourth): Arena clubs gained names

Fetching's 404 ARENA club_name claims landed, so an Arena season reads "the Portland
Thunder" where it read "the ARENAPOT". Also in this rebuild: 1,598 phantom entries dropped
(Ryan's ruling) and 201 guide club-name keys folded onto their codes.
