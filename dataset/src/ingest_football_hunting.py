"""The Football Hunting folder (Dropbox, Football Archive/docs/Football Hunting), ingested
under Ryan's rulings of 2026-09-11. Inventory first: reports/2026-09-11-football-hunting-inventory.md.

TWO STORES, because a store carries one league token:
  build/football-hunting.json      claims on club-seasons the archive HOLDS; the league is read
                                   from each stint subject's season key (APFA-1920, NFL-1925 ...)
  build/football-hunting-ind.json  the three club-seasons OPENED from this folder -- Dayton 1919,
                                   Pottsville 1924, Portsmouth 1929 -- under the IND token

THE JOIN, ruling One. A printed name joins a man held ON THAT CLUB-SEASON, never anywhere else:
  * exact full name, held once on the club-season; or
  * SURNAME UNIQUE ON THE CLUB-SEASON -- exactly one held man of that surname, and the document
    prints that surname once. A second man of the surname on the roster refuses both. A printed
    initial or forename that agrees with none of the held man's name forms also refuses.
  This is NARROWER than "unique in the archive", the tier that took Andy King's figures: unique
  among twenty men on one roster is not unique among the names the archive happens to hold.
  Gated by src/gate_surname_on_club_season.py.

NOTHING IS PROMOTED FROM A HELD CLUB-SEASON. A name that does not join is a CANDIDATE, reported
with any visible counterpart and joined to nobody -- ruling Three: `Cocoran` against Bunny
Corcoran is a spelling question, and minting a person beside him is the Behman failure.

THE OPENED CLUB-SEASONS, ruling Two. They hold nobody, so the join has no roster. Each man is
placed by stated evidence against the SAME CITY'S NEXT SEASON, which the archive holds (Dayton
1920, Pottsville 1925, Portsmouth 1930) -- a neighbour, not a lineage; the clubs stay unlinked:
  (a) exact full name, held by exactly one person in the archive, AND that person is on the
      neighbouring season -> joined to him, the evidence written on the claim
  (b) anyone of that surname on the neighbouring season, otherwise -> CANDIDATE, not promoted:
      he may be that man, and minting him beside that man is the failure the surname-only
      refusal exists for
  (c) nobody of that surname there and no exact name -> a lead, which promote_players makes a
      person (the Bethlehem and Pacific Coast Wildcats shape)

STAFF, ruling Four. `club_staff_role` is a fact about the CLUB-SEASON: its subject is the
club-season, it names no person and joins no one, and it is kept apart from `role_title`, the
coaching predicate the bios read. Herman Smith the trainer is not P_008811 Herman Smith (1994-2003).

  python3 src/ingest_football_hunting.py [--write]
"""
import os, re, sys, json, sqlite3, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
from readings import person_name
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

OUT = os.path.join(BASE, "build", "football-hunting.json")
OUT_IND = os.path.join(BASE, "build", "football-hunting-ind.json")
MINE = ("football-hunting", "football-hunting-ind")
PROM = os.path.join(BASE, "build", "player-promotions.json")
FOLDER = "Dropbox: Football Archive/docs/Football Hunting"

PREDICATE_DEFINITIONS = {
    "club_staff_role": {
        "definition": "named by a document in a NON-COACHING staff role for a club-season: trainer, "
                      "manager, business manager, president. The role is held exactly as printed.",
        "subject": "the CLUB-SEASON. It names no person and joins no one: the person line stops at "
                   "players, coaches and officials (Ryan), and a trainer is a fact about the "
                   "club-season, not a person (Ryan, 2026-09-11).",
        "is_not_role_title": "role_title is the coaching predicate and the bios read it. This is kept "
                             "apart so a trainer or a president never becomes a coaching season.",
        "ruled_by": "Ryan, 2026-09-11.",
    },
    "programme.team_photograph": {
        "definition": "named in the caption to a team photograph: this man was photographed with this "
                      "club, as this club.",
        "_note": "the predicate's name is source-flavoured and its definition is not; a newspaper or "
                 "loose print caption asserts the same thing a programme's does.",
    },
    "newspaper.lineup_membership": {
        "definition": "placed on this club-season because a game account printed after the game names "
                      "him in the starting eleven. The companion roster_membership.started_a_game "
                      "says he STARTED; this one places him (the Bethlehem shape).",
    },
    "newspaper.scoring_as_printed": {
        "definition": "named in a game account's scoring summary. A THIRD assertion: not a starter (he "
                      "is not in the eleven) and not a substitution (none is printed). It places no "
                      "one on a club-season.",
    },
}

# ---------------------------------------------------------------- documents, as read
# Each: (name as printed, role as printed or None, where on the page)
def rows(label, names): return [(n, r, label) for n, r in names]

DOCS = {
 "dayton-1919": dict(file="1919 Dayton Triangles.webp", kind="photo", store="ind",
   club="Dayton Triangles", printed="TRIANGLES 1919", year=1919,
   rights="photograph of 1919 -- public domain by date; the scan's provenance is not stated",
   names=rows("Standing", [("Storck", "Mgr."), ("Roudebush", None), ("Reese", None), ("Albers", None),
     ("Clark", None), ("Winston", None), ("Thiele", None), ("Cutler", None), ("Stoecklein", None),
     ("Houser", None), ("Dellinger", None), ("Partlow", None), ("Talbott", "Coach")]) +
     rows("Sitting", [("Bacon", None), ("Yerges", None), ("Abrell", None), ("Mahrt", "Captain"),
     ("Fenner", None), ("Kinderdine", None), ("Tidd", None)])),
 "akron-1920": dict(file="1920 Akron Professionals.jpg", kind="photo", club_id="club-akron-pros-1920",
   code="AKR", league="APFA", year=1920, printed="Akron 1920 Professionals",
   rights="photograph of 1920 -- public domain by date. The scan carries a private stamp "
          "('John G. Schwil..., 37 Franklin St, Akron, Ohio'); the scan is not the document",
   names=rows("Top row", [("Art Ranny", "Mgr."), ("Nash", None), ("Benny Leonard", None), ("Nesser", None),
     ("Bailey", None), ("Copley", "Capt."), ("Crawford", None), ("Cobb", None), ("Bierce", None),
     ("King", None), ("Neid", "Mgr.")]) +
     rows("Bottom row", [("Johnson", None), ("McCormack", None), ("Harris", None), ("Tomlin", None),
     ("Sweetland", None), ("Garret", None), ("Pollard", None)])),
 "canton-1920": dict(file="1920 Canton Bulldogs.webp", kind="photo", club_id="club-canton-bulldogs-1920",
   code="CAN", league="APFA", year=1920, printed="CANTON BULLDOGS 1920 WORLD'S CHAMPIONS",
   rights="published 1920 with notice '(c) 1920 by J.J. Proskauer, Roth & Hugs, official "
          "photographers' -- the copyright has expired; public domain",
   names=[(n, None, f"No. {i}") for i, n in enumerate(["Griggs", "Buck", "O'Connor", "Cocoran", "Martin",
     "Dadum", "Edwards", "Thorpe", "Guyon", "Calac", "Henry", "Green", "Wahlen", "Gilroy", "Speck",
     "Feeny", "Haley", "Hendren"], 1)]),
 "canton-1922": dict(file="1922 Canton Bulldogs.webp", kind="photo", club_id="club-canton-bulldogs-1920",
   code="CAN", league="NFL", year=1922, printed="The CANTON BULLDOGS 1922",
   rights="montage of 1922 -- public domain by date",
   names=[(n, r, "oval montage") for n, r in [("Robb", None), ("Sacksteder", None), ("Kendricks", None),
     ("Elliott", None), ("Roberts", None), ("Waldsmith", None), ("McQuade", None), ("Smyth", None),
     ("Murrah", None), ("Speck", None), ("Carroll", None), ("Bowser", None), ("Taylor", None),
     ("Osborn", "Capt."), ("Chamberlin", "Coach"), ("Shaw", None), ("Lyman", None),
     ("Smallwood", None), ("Criggs", None), ("Henry", None), ("R.E. Hay", "Mgr.")]]),
 "canton-1923": dict(file="1923 Canton Bulldogs.webp", kind="photo", club_id="club-canton-bulldogs-1920",
   code="CAN", league="NFL", year=1923, printed="CANTON BULL DOGS World's Professional Champions 1923",
   rights="photograph of 1923 -- public domain by date",
   names=rows("Top Row", [("Oscar Hendrian", None), ("Harry Robb", None), ("Ben Jones", None),
     ("Louis Smythe", None), ("Cecil Griggs", None), ("Wallace Elliott", None), ("Walcott Roberts", None)]) +
     rows("Middle Row", [("Elmer Carroll", None), ("Wilbur Henry", None), ("Robert Osborne", "Capt."),
     ("Larry Conover", None), ("Roudolph Comstock", None), ("Roy Lyman", None), ("B. Guy Ch[amberlin]", None)]) +
     rows("Bottom Row", [("Norman Speck", None), ("Herman Smith", "trainer"), ("Joe Williams", None)])),
 "racine-1922": dict(file="Racine Legion Team Photo.jpeg", kind="photo", club_id="club-racine-legion-1922",
   code="RAC", league="NFL", year=1922, printed="1922 HORLICK-RACINE-LEGION 1922",
   rights="photograph of 1922 -- public domain by date. The image is the RACINE HERITAGE MUSEUM's "
          "watermarked scan; the museum's copy is not the document",
   names=[(n, r, f"No. {k}") for k, n, r in [(12, "Gillo", "Captain"), (17, "Morrissy", "Asst. Mgr."),
     (23, "Zirbes", "Bus. Mgr."), (24, "Ruetz", "Team Mgr."), (25, "McDowell", "Com. Racine Post"),
     (26, "William Horlick Sr.", None), (1, "Sieb", None), (2, "Rhenstrom", None), (3, "Roessler", None),
     (4, "Miller", None), (5, "Mintin", None), (6, "Braman", None), (7, "Johnson", None),
     (8, "Hueller", None), (16, "Hogoboam", "TRAINERS?"), (21, "Larson", "TRAINERS?"),
     (22, "Kautz", "TRAINERS?"), (9, "Gorman", None), (10, "Murry", None), (11, "Elliott", None),
     (13, "Langhoff", None), (14, "Foster", None), (15, "Murray", None), (18, "Hayes", None),
     (19, "Dressen", None), (20, "Heinisch", None)]]),
 "giants-1927": dict(file="1927 New York Giants.webp", kind="photo", club_id="club-new-york-giants-1925",
   code="NYG", league="NFL", year=1927, printed="NEW YORK FOOTBALL GIANTS 1927",
   rights="photograph of 1927 -- public domain by date",
   names=rows("TOP ROW", [("Joe Alexander", "T"), ("Pete Henry", "T"), ("Riley Biggs", "C"), ("Al Nesser", "G"),
     ("Dick Stahlman", "T"), ("Steve Owen", "G"), ("Cal Hubbard", "E"), ("Charley Corgan", "E"),
     ("George Murtagh", "G"), ("Arthur Harms", "T"), ("Paul Jappe", "E")]) +
     rows("BOTTOM ROW", [("Phil White", "B"), ("Doug Wycoff", "B"), ("Jack Hagerty", "B"), ("Talma Imlay", "B"),
     ("Hinkie Haines", "B"), ("Earl Potteiger", "B (Coach)"), ("Jack McBride", "B"), ("Joe Guyon", "B"),
     ("Faye Mule Wilson", "B"), ("Cliff Marker", "B")])),
 "portsmouth-1929": dict(file="1929 Portsmouth Spartans.webp", kind="photo", store="ind",
   club="Portsmouth Spartans", printed="The SPARTANS 1929 PORTSMOUTH-OHIO", year=1929,
   rights="photograph of 1929 -- public domain by date (1929 and earlier, as of 2026)",
   names=rows("standing", [("Sneeze Achiu", None), ("Chuck Bennett", None), ("Buck Weaver", None),
     ("Paul Armil", None), ("Whity Fyock", None), ('Roy "Pop" Lumpkin', None), ("Russ Mayer", None),
     ("Roy Whitt", None), ("Roy Estese", None), ("Carl Brumbaugh", None), ("Keith Molesworth", None),
     ("Harold Griffen", "CCAH [sic: Coach]")]) +
     rows("kneeling", [("Hank Weber", None), ("Bob Jessen", None), ("Doug Harris", None), ("Harry Richman", None),
     ("Puss Meyers", None), ("Clare Randolph", None), ("Abe Deweese", None), ("George Lyons", None),
     ("Mack McDermott", None), ("Chuck Braidwood", None)])),
 "portsmouth-1932": dict(file="1932 Portsmouth Spartans.webp", kind="photo", club_id="club-portsmouth-spartans-1930",
   code="POR", league="NFL", year=1932, printed="1932 -- PORTSMOUTH SPARTANS -- 1932",
   rights="clipping from an UNNAMED publication of 1932 -- NOT public domain by date; renewal unknown. "
          "Facts are read; the image is not reproduced",
   names=rows("BACK ROW", [('"Potsy" Clark', "Coach"), ('"Father" Lumpkin', None), ("Presnell", None),
     ("Alford", None), ('"Dutch" Clark', None), ("Wilson", None), ("Cavosie", None), ("Gutowsky", None),
     ("Doc Neff", None), ("Harry Snyder", None)]) +
     rows("FRONT ROW", [("Ebding", None), ("Christensen", None), ("Mitchell", None), ("Emerson", None),
     ("Randolph", None), ("Davis", None), ("Bodenger", None), ("Wager", None), ("Rascher", None), ("McKalip", None)])),
}

POTTSVILLE = dict(file="1924 Pottsville Maroons/img.jpg", store="ind", club="Pottsville Maroons", year=1924,
  printed_in="Allentown Morning Call, September 22, 1924, p. 14",
  headline="POTTSVILLE WINS ITS OPENING GRID BATTLE -- Maroons Defeat Darby Eleven, Scoring Six "
           "Touchdowns in Second Half",
  rights="newspaper of 1924 -- public domain by date. Page cited by Wikipedia's 1924 Pottsville "
         "Maroons season article (ref. 1); the clipping is the page, the article is not the source",
  eleven=[("Julian", "L.E."), ("C. Beck", "L.T."), ("Hudnek", "L.G."), ("Connell", "C."), ("Tribit", "R.G."),
          ("Potter", "R.T."), ("Emmanuel", "R.E."), ("Robb", "Q."), ("Nemzek", "L.H."), ("Carl Beck", "R.H."),
          ("Brunner", "F.")],
  darby=[("Graham", "L.E."), ("Taggart", "L.T."), ("Brady", "L.G."), ("Dolan", "C."), ("Conover", "R.G."),
         ("Yost", "R.T."), ("Frauberg", "R.E."), ("Watson", "Q."), ("Homan", "L.H."), ("Buchannon", "R.H."),
         ("Allen", "F.")],
  scoring="Touchdowns: Nemzek, 2; Scott, 1; Emmanuel, 1; Julian, 1; C. Beck, 1. Points after "
          "touchdowns, Boyd, 3.",
  officials="Referee, Brennan; umpire, Molak; head linesman, Bennett. Time of periods, 12 minutes.")

PROG_1925 = dict(file="New York Football Giants vs. Yellow Jackets Oct. 18, 1925 Program/ebay-images.zip",
  game=["game", "NFL", "1925", "1925-10-18-nyg-v-fyj"],
  copy="THE COPY PHOTOGRAPHED MAY BE A 1976 FACSIMILE. A Giants Stadium insert marking the stadium's "
       "opening on 10 October 1976 is photographed with it, and its text appears to describe the "
       "booklet as a reproduction. Too little of the insert is legible to settle it, so this is "
       "stated on the claim rather than assumed either way. The DOCUMENT is 1925.",
  rights="the 1925 programme is public domain by date; the 1976 insert is not, and is not read",
  giants=[("Nash", "Left End", "18", "Rutgers"), ("Milstead", "Left Tackle", "24", "Yale"),
          ("Carney", "Left Guard", "23", "Navy"), ("Alexander", "Center", "20", "Syracuse"),
          ("Williams", "Right Guard", "25", "Lafayette"), ("McGinley", "Right Tackle", "10", "Penn"),
          ("Bomar", "Right End", "7", "Vanderbilt"), ("Brennan", "Quarterback", "5", "Lafayette"),
          ("Thorpe", "Right Halfback", "21", "Carlisle"), ("Benkert", "Left Halfback", "2", "Rutgers"),
          ("McBride", "Fullback", "16", "Syracuse")],
  giants_subs=[("Haines", "1", "Penn State"), ("Hedner", "3", "Lafayette"), ("Myers", "4", "Fordham"),
          ("Hendrian", "6", "Pittsburg"), ("Smith", "8", "St. Johns"), ("Frugonne", "9", "Syracuse"),
          ("Parnell", "12", "Colgate"), ("Nordstrom", "14", "Trinity"), ("Walbridge", "15", "Lafayette"),
          ("Reynolds", "17", "Georgia"), ("Jappe", "22", "Syracuse")],
  fyj=[("Chamberlain", "Left End", "Lafayette"), ("Behman", "Left Tackle", "Dickinson"),
       ("Hoffman", "Left Guard", "Lehigh"), ("Springsteen", "Center", "Lehigh"),
       ("Seacrist", "Right Guard", "Colgate"), ("R. Carten", "Right Tackle", "Holy Cross"),
       ("Crowther", "Right End", "Colgate"), ("Haws", "Quarterback", "Dartmouth"),
       ("Fitzke", "Right Halfback", "Idaho"), ("Sullivan", "Left Halfback", "Penn"),
       ("Hamer", "Fullback", "Penn")],
  fyj_subs=[("Burnham", "9", "Harvard"), ("Clement", "8", "Williams"), ("Wilsbach", "7", "Bucknell"),
            ("Welsh", "19", "Colgate"), ("Harms", "18", "Vermont"), ("Stockton", "6", "Gonzaga")],
  photo=[("Lynn Bomar", "Front line"), ("Ed McGinley", "Front line"), ("Joe Williams", "Front line"),
         ("Joe Alexander", "Front line"), ("Arthur Carney", "Front line"), ('"Century" Milstead', "Front line"),
         ("Dick Jappe", "Front line"), ("Hendrian", "Back Row"), ('"Heinie" Benkert', "Back Row"),
         ("Jack McBride", "Back Row"), ('"Hinkey" Haines', "Back Row")])

KEZAR = dict(game=["game", "NFL", "1934", "1935-01-20-nyg-v-nevers-pcaa"],
  season_note="Played Sunday 20 January 1935 at Kezar Stadium: 1934-SEASON football, a post-season "
              "exhibition, under the 1926-programme precedent (a January game is the previous "
              "season's). The Pacific Coast All-Americans are a scratch side and have no club-season. "
              "AN EXHIBITION SQUAD IS NOT A SEASON ROSTER: Edwards and Corzine are printed in the Giants' "
              "squad and are NOT held on the 1934 Giants, so the squad may carry guests. Only men already "
              "held on NFL|1934|NYG are joined, so nothing here adds a season to anyone.",
  copies="ONE GAME, TWO COPIES. The folder named '1934' holds a worn original (8 images); the folder "
         "named '1935' holds a clean, square-edged copy photographed on felt that is PROBABLY A MODERN "
         "REPRINT -- not proven. The line-up spread is read from the second copy (the first copy's "
         "is cropped); both carry the same cover and the same spread.",
  rights="published January 1935 (the Camel advertisement is marked 'Copyright, 1934') -- NOT public "
         "domain by date; renewal unknown. Facts are read; the images are not reproduced",
  squad=[("Smith", "0", "q"), ("Flaherty", "1", "e"), ("Del Isola", "2", "c"), ("Grant", "3", "t"),
         ("Clancy", "4", "q"), ("Hein", "7", "c"), ("Bellinger", "8", "g"), ("Reese", "9", "c"),
         ("Jones", "10", "g"), ("Gibson", "11", "g"), ("Richards", "13", "h"), ("Corzine", "14", "f"),
         ("Burnett", "18", "h"), ("Frankian", "21", "e"), ("Danowski", "22", "h"), ("Molenda", "23", "f"),
         ("Krause", "25", "h"), ("Morgan", "27", "t"), ("Irvin", "29", "t"), ("Owen", "36", "e"),
         ("Strong", "50", "q"), ("Edwards", "55", "t")],
  lineups=[("LER", ["Frankian", "Del Isola"], ["Ebding", "Norgard"]),
           ("LTR", ["Morgan", "Grant"], ["Barber", "Gordon"]),
           ("LGR", ["Gibson"], ["Handler"]),
           ("C", ["Hein", "Reese"], ["Siemering", "Hughes"]),
           ("RGL", ["Jones", "Bellinger"], ["O'Connor", "Field"]),
           ("RTL", ["Irvin", "Edwards"], ["Johnson", "Schwammel"]),
           ("REL", ["Flaherty", "Owen"], ["Creighton", "Smith"]),
           ("Q", ["Strong", "Smith", "Clancy"], ["Gutowski", "Sarboe", "Bosshardt"]),
           ("LHR", ["Burnett", "Krause"], ["Caddel", "Cook"]),
           ("RHL", ["Danowski", "Richards"], ["Storm", "Russell"]),
           ("F", ["Molenda", "Corzine"], ["Griffith", "Sulkosky"])],
  giants_photo=rows("Upper Row", [("John V. Mara", "President"), ("Ray Flaherty", None), ("Ed. Danowski", None),
         ("Dale Burnett", None), ("Tom Jones", None), ("Bo Molenda", None), ("Mel Hein", None),
         ("Ken Strong", None), ('Glenn "Turk" Edwards', None), ("Len Grant", None), ("Bill Morgan", None),
         ('Elvin "Kink" Richards', None), ("Butch Gibson", None), ("Steve Owen", "Coach")]) +
       rows("Lower Row", [("Stuart Clancy", None), ('"Tex" Irvin', None), ("Lester Corzine", None),
         ("Hank Reese", None), ("Willie Smith", None), ("Max Krause", None), ("Bill Owen", None),
         ("Bob Bellinger", None), ("John Del Isola", None)]),
  pcaa_squad="5 Gutowski f&q; 6 Cook h; 8 Schwammel t&g; 12 Griffith f; 16 Caddel h; 18 Norgard e; "
             "22 Gordon t; 23 Storm h; 24 Creighton e; 25 Bosshardt q; 28 Siemering c; 30 Field g; "
             "31 Barber t; 32 Russell h; 33 Ebding e; 45 Hughes c; 46 Handler g; 50 Sarboe q; "
             "53 O'Connor g; 60 Johnson t; 67 Smith e; 76 Sulkosky f&q. Ernie Nevers, Coach.",
  pcaa_photo="Upper Row (left to right): Ernie Nevers, William Smith, Lou Gordon, Ed Storm, Ace Gutowski, "
             "Bob O'Connor, Jim Barber, Bernie Hughes, Ernie Caddel, Larry Siemering, Ade Schwammel, "
             "Dave Cook, Harry Field and Jack Johnson. Lower Row (left to right): Paul Sulkosky, Phil "
             "Handler, Homer Griffith, Harry Ebding, Milan Creighton, Phil Sarboe and Doug Russell. "
             "Absent: Bob Bosshardt and Ken Bright.")

# 1921: the printed short name -> the club the archive holds for that city in 1921. A READING,
# declared here and asserted unique below, never a guess at a lineage.
COURIER_CLUB = {"Buffalo": "club-buffalo-all-americans-1920", "Canton": "club-canton-bulldogs-1920",
                "Rochester": "club-rochester-jeffersons-1920", "Akron": "club-akron-pros-1920",
                "Cleveland": "club-cleveland-tigers-1920", "Staleys": "club-decatur-staleys-1920",
                "Hammond": "club-hammond-pros-1920", "Detroit": "club-detroit-heralds-1920"}
COURIER = {"FIRST TEAM": [("LE", "Nash", "Buffalo"), ("LT", "West", "Canton"), ("LG", "Youngstrom", "Buffalo"),
             ("C", "Alexander", "Rochester"), ("RG", "Nesser", "Akron"), ("RT", "Henry", "Canton"),
             ("RE", "Bierce", "Akron"), ("QB", "Boynton", "Rochester"), ("LH", "Guyon", "Cleveland"),
             ("RH", "Oliphant", "Buffalo"), ("FB", "King", "Hammond")],
           "SECOND TEAM": [("LE", "Robeson", "Akron"), ("LT", "Thomas", "Rochester"), ("LG", "Murphy", "Cleveland"),
             ("C", "Bailey", "Akron"), ("RG", "Brace", "Buffalo"), ("RT", "Copley", "Buffalo"),
             ("RE", "Baujaun", "Cleveland"), ("QB", "Kempton", "Canton"), ("LH", "Pollard", "Akron"),
             ("RH", "Anderson", "Buffalo"), ("FB", "King", "Akron")],
           "THIRD TEAM": [("LE", "Halas", "Staleys"), ("LT", "Hornung", "Buffalo"), ("LG", "Usher", "Rochester"),
             ("C", "Feeney", "Canton"), ("RG", "Smith", "Staleys"), ("RT", "Coughlin", "Detroit"),
             ("RE", "Higgins", "Canton"), ("QB", "Griggs", "Canton"), ("LH", "Stinchcomb", "Staleys"),
             ("RH", "Harley", "Staleys"), ("FB", "Smith", "Buffalo")]}
MILLER_NOTE = ("(*Copley misidentified as playing for Buffalo. He actually played for Akron. Not sure if "
               "this error was on the part of the writer or the newspaper.)")

COLEMAN = {"person": "P_045339", "club_id": "club-philadelphia-quakers-1926", "code": "AFLPHI",
           "league": "AFL", "year": 1926, "printed": "1926 Philadelphia Quakers (AFL)",
           "facts": [("pfa.name_as_printed", "Coleman, William Thomas, Jr."), ("name", "Bill Coleman"),
                     ("pfa.position_career", "G"), ("pfa.height", "6-0"), ("pfa.weight", "200"),
                     ("pfa.birth_date", "February 7, 1902"), ("pfa.birth_place", "NY"),
                     ("pfa.death_date", "August 20, 1969"), ("pfa.death_place", "Rochester, NY"),
                     ("pfa.high_school", "Free Academy (Elmira, NY)")]}

# The three opened club-seasons, and the neighbouring season the archive holds for each city.
OPENED = {"dayton-1919": dict(code="DOC:DAY-IND", club_id="club-dayton-triangles-1919",
                               neighbour=("club-dayton-triangles-1920", 1920)),
          "portsmouth-1929": dict(code="DOC:POR-IND", club_id="club-portsmouth-spartans-1929",
                                  neighbour=("club-portsmouth-spartans-1930", 1930)),
          "pottsville-1924": dict(code="DOC:POT-IND", club_id="club-pottsville-maroons-1924",
                                  neighbour=("club-pottsville-maroons-1925", 1925))}
STAFF_ROLES = ("Mgr.", "Asst. Mgr.", "Bus. Mgr.", "Team Mgr.", "trainer", "President", "TRAINERS?")
COACH_ROLES = ("Coach", "CCAH [sic: Coach]", "B (Coach)")


# ---------------------------------------------------------------- the one reading of a name
SUFFIX = {"jr", "sr", "ii", "iii"}
def _clean(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().replace("'", "")
    return [t for t in re.sub(r"[^a-z\s]", " ", s).split() if t not in SUFFIX]
def _prep(s):
    s = str(s or "").replace("“", '"').replace("”", '"')
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"\(([^)]*)\)", r' "\1" ', s)          # 'Henry, Wilbur Frank (Fats)': (Fats) is a nickname
    if "," in s:                                        # 'Hendrian, Oscar George' is surname-first
        last, rest = s.split(",", 1); s = f"{rest} {last}"
    return s
def toks(s):
    """The name with any quoted nickname removed: 'Glenn "Turk" Edwards' -> glenn edwards."""
    return _clean(re.sub(r'"[^"]*"', " ", _prep(s)))
def variants(s):
    """Every reading of a name, as token tuples: without the nickname, with it, and nickname +
    surname -- so 'Elvin "Kink" Richards' meets a held 'Kink Richards' as an EXACT name, and
    '"Potsy" Clark' is not refused against '"Dutch" Clark' as two bare Clarks."""
    p = _prep(s); base = toks(s); out = {tuple(base)} if base else set()
    for nk in re.findall(r'"([^"]*)"', p):
        n = _clean(nk)
        if n and base: out.add(tuple(n + base[-1:]))
        out.add(tuple(_clean(p.replace('"', " "))))
    return {v for v in out if v}
def surname(s): t = toks(s); return t[-1] if t else ""
def forename(s): t = toks(s); return t[0] if len(t) > 1 else None


class RM:
    """The read model, BASE STATE: every stint claim EXCEPT this route's own stores, so a re-run
    never finds a man because it placed him (a decider that reads its own output)."""
    def __init__(self):
        self.c = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
        self.names = collections.defaultdict(set)
        for p, n in self.c.execute("select person, name from person_name"):
            self.names[p].add(n)
        self.index_name = dict(self.c.execute("select id, index_name from person where merged_into is null"))
        self.by_full = collections.defaultdict(set)
        for p, n in self.index_name.items():
            if n: self.by_full[" ".join(toks(n))].add(p)
        self.years = {p: (a, b) for p, a, b in
                      self.c.execute("select id, first_year, last_year from person where merged_into is null")}
        self.by_sur = collections.defaultdict(set)
        for p, ns in self.names.items():
            for n in ns:
                s = surname(n)
                if s: self.by_sur[s].add(p)
    def surname_near(self, s, year, band):
        """Held men of surname `s` with a season within `band` years of `year`, anywhere."""
        out = set()
        for p in self.by_sur.get(s, ()):
            a, b = self.years.get(p, (None, None))
            if a is not None and a - band <= year <= (b or a) + band:
                out.add(self.index_name.get(p))
        return sorted(out - {None})
    def roster(self, club_id, year):
        q = ("select distinct person from claim where scope='stint' and club_id=? and year=? "
             "and store not in (?,?) and person is not null")
        return {p for (p,) in self.c.execute(q, (club_id, year, *MINE))}


def join(printed, roster, rm, printed_surnames):
    """-> (tier, person or None, evidence). Ruling One, and nothing looser."""
    t = toks(printed)
    if not t: return None, None, "no name read"
    pv = {v for v in variants(printed) if len(v) > 1}
    exact = {p for p in roster if any(pv & variants(n) for n in rm.names[p])} if pv else set()
    if len(exact) == 1:
        p = next(iter(exact))
        return ("exact_full_name_on_the_club_season", p,
                "exact full name (or nickname and surname), held once on the club-season")
    s = t[-1]
    same = sorted(p for p in roster if any(surname(n) == s for n in rm.names[p]))
    if len(same) > 1:
        return None, None, f"REFUSED: {len(same)} men of surname '{s}' on the club-season ({same[:3]}) -- a second man refuses both"
    if len(same) == 0:
        return None, None, "not on the club-season"
    if printed_surnames[s] > 1:
        return None, None, f"REFUSED: the document prints the surname '{s}' {printed_surnames[s]} times; one held man cannot be both"
    p = same[0]
    ev = "surname held by exactly one man on the club-season, printed once in this list"
    f = forename(printed)
    if f and not any(v[0][:1] == f[:1] for n in rm.names[p] for v in variants(n) if len(v) > 1):
        # NOT a refusal. Ruling One: the unique surname is enough. A printed forename meeting none
        # of the held forms is usually a nickname -- Norman 'Dutch' Speck, Roy 'Link' Lyman -- and is
        # written on the claim so it can be looked at, never silently agreed.
        ev += f"; NOTE: the printed forename '{f}' agrees with none of the held forms {sorted(rm.names[p])[:3]}"
    return "surname_unique_on_the_club_season", p, ev


def counterpart(printed, roster, joined, rm):
    """A VISIBLE counterpart for a candidate: an unjoined man on the club-season whose surname shares
    its first three letters. Shown so Ryan can rule; never a join."""
    s = surname(printed)
    return sorted({rm.index_name.get(p) for p in roster - joined
                   if any(toks(n) and toks(n)[-1][:3] == s[:3] for n in rm.names[p])} - {None})[:3]


RESTATED = ("restated: the same fact -- same subject, predicate, source record and asserted value -- with only "
            "its `_`-annotations changed (2026-09-11: `_joined_on`, the season and copy notes). Not a loss of any fact.")
# A DEFECT, CORRECTED, AND STATED AS ONE. The ten Pro Football Archives facts about Bill Coleman were
# first written onto P_002554 -- the Buffalo Smith the Courier section had joined just before -- because
# the Coleman block read a `pid` it never set. Found by checking which person the claims were on, not by
# any gate; src/gate_surname_on_club_season.py S3 now fails that shape.
MISATTACHED = {("football-hunting#pfa-bill-coleman", "P_002554"):
               "attached in error to P_002554 (a Buffalo 1921 Smith) by a defect in this ingest -- a person id "
               "carried over from the previous section -- and moved to P_045339, the one Coleman held (2026-09-11)"}


def _plain(v):
    return {k: x for k, x in v.items() if not str(k).startswith("_")} if isinstance(v, dict) else v


def _restated(claims):
    """write_store's account of a lost claim (index_io.write_store `reasons`). The writer compares facts
    including their annotations, so a claim whose `_`-keys changed reads as lost and re-gained: that is a
    RESTATEMENT and is named. A claim that moved to a DIFFERENT PERSON is not a restatement -- only
    MISATTACHED names one, with its evidence. Anything else lost gets no reason, on purpose, so that
    gate_reingest_losses R1 fails it."""
    keys = {(json.dumps(c.get("subject")), c.get("predicate"), json.dumps(_plain(c.get("value")), sort_keys=True),
             c.get("source_record")) for c in claims}
    def reasons(old):
        s = old.get("subject") or []
        who = s[1] if len(s) > 1 else None
        if (old.get("source_record"), who) in MISATTACHED:
            return (MISATTACHED[(old["source_record"], who)], {})
        k = (json.dumps(s), old.get("predicate"), json.dumps(_plain(old.get("value")), sort_keys=True),
             old.get("source_record"))
        return (RESTATED, {}) if k in keys else None
    return reasons


def promoted_leads():
    if not os.path.exists(PROM): return {}
    return {p["reversible"]["lead_ref"]: p["person_id"] for p in json.load(open(PROM))["promotions"]
            if str(p.get("source", "")).startswith("football-hunting-ind")}


def main(write=False):
    rm = RM()
    promoted = promoted_leads()
    S = {"held": dict(claims=[], leads=[], candidates=[], refusals=[], srecs={}),
         "ind": dict(claims=[], leads=[], candidates=[], refusals=[], srecs={})}
    n = collections.Counter(); three = collections.Counter(); opened_n = collections.Counter()
    # THE CLUB-SEASON A JOIN WAS MADE ON, written on every joined claim. A line-up or an honour has a
    # person subject, so without this the claim does not say which roster its surname was unique on,
    # and src/gate_surname_on_club_season.py could not recount it -- 66 claims went unchecked that way.
    cur = {}

    def sr_of(which, key, desc, rights, locator):
        sr = f"{MINE[0] if which == 'held' else MINE[1]}#{key}"
        S[which]["srecs"][sr] = {"source_id": MINE[0] if which == "held" else MINE[1], "locator": locator,
                                 "description": desc, "rights": rights, "folder": FOLDER}
        return sr

    def claim(which, sr, subj, pred, val, stated_by, attribution, **kw):
        c = {"source_record": sr, "source_id": MINE[0] if which == "held" else MINE[1],
             "stated_by": stated_by, "attribution": attribution, "subject": subj,
             "predicate": pred, "value": val, "kind": "observed", "observed_at": "photographed-2026-09"}
        c.update(kw)
        v = c["value"] if isinstance(c["value"], dict) else c.get("extra")
        if isinstance(v, dict) and v.get("_join_tier") and cur:
            v.setdefault("_joined_on", dict(cur))
        S[which]["claims"].append(c); n[pred] += 1

    def staff(which, sr, cs_subj, name, role, club_printed, stated_by, attr, note=None):
        v = {"name_as_printed": name, "role_as_printed": role, "club_as_printed": club_printed,
             "_definition": PREDICATE_DEFINITIONS["club_staff_role"]["definition"],
             "_not_a_person": "names no person and joins no one; the archive may hold a namesake and "
                              "that is not this man"}
        if note: v["_note"] = note
        claim(which, sr, cs_subj, "club_staff_role", v, stated_by, attr)

    # ------------------------------------------------ captions on held club-seasons
    for key, d in DOCS.items():
        if d.get("store") == "ind": continue
        sr = sr_of("held", key, f"captioned photograph: {d['printed']}", d["rights"], d["file"])
        stated, attr = "the photograph's caption (publisher not named)", [f"{d['file']} ({FOLDER})"]
        seas = f"{d['league']}-{d['year']}"; cs = ["club_season", d["league"], str(d["year"]), d["code"]]
        roster = rm.roster(d["club_id"], d["year"])
        cur.clear(); cur.update(club_id=d["club_id"], year=d["year"])
        sn = collections.Counter(surname(nm) for nm, r, _ in d["names"] if r not in STAFF_ROLES)
        joined = set()
        for nm, role, where in d["names"]:
            if role in STAFF_ROLES:
                note = ("a 'TRAINERS' heading sits over the column of Nos. 16, 21 and 22; whether it labels "
                        "these three men is NOT established from the page" if role == "TRAINERS?" else None)
                staff("held", sr, cs, nm, "TRAINERS" if role == "TRAINERS?" else role, d["printed"], stated, attr, note)
                if role != "TRAINERS?": continue
            tier, pid, ev = join(nm, roster, rm, sn)
            if pid and role != "TRAINERS?":
                joined.add(pid); three[tier] += 1
                claim("held", sr, ["stint", pid, d["code"], seas], "programme.team_photograph",
                      {"name_as_printed": nm, "held_as": rm.index_name.get(pid), "caption_place": where,
                       "role_as_printed": role, "club_as_printed": d["printed"], "club_code": d["code"],
                       "league": d["league"], "year": d["year"], "_join_tier": tier, "_join_evidence": ev,
                       "_definition": PREDICATE_DEFINITIONS["programme.team_photograph"]["definition"]},
                      stated, attr, person=pid)
            else:
                three["not_joined"] += 1
                S["held"]["candidates"].append({"document": key, "name_as_printed": nm, "role_as_printed": role,
                    "club_season": f"{d['league']}|{d['year']}|{d['code']}", "why": ev,
                    "visible_counterpart_NOT_a_join": counterpart(nm, roster, joined, rm),
                    "ruling": "Ryan, 2026-09-11 (Three): a spelling variant stays out -- reported, joined to nobody, not promoted"})
        claim("held", sr, ["document", d["file"]], "programme.caption_verbatim",
              {"club_as_printed": d["printed"], "names": [f"{nm}{', ' + r if r else ''}" for nm, r, _ in d["names"]]},
              stated, attr)

    # ------------------------------------------------ the three opened club-seasons
    def opened(key, club, year, entries, evidence_kind, sr, stated, attr, printed, claim_for):
        o = OPENED[key]; code = o["code"]; nb = rm.roster(*o["neighbour"])
        cur.clear(); cur.update(club_id=o["club_id"], year=year, neighbour=list(o["neighbour"]))
        printed_n = collections.Counter(surname(nm) for nm, role, _ in entries
                                        if role not in STAFF_ROLES and role not in COACH_ROLES)
        nb_sur = collections.defaultdict(set)
        for p in nb:
            for nm in rm.names[p]:
                if toks(nm): nb_sur[toks(nm)[-1]].add(p)
        for i, (nm, role, where) in enumerate(entries, 1):
            lead_id = f"lead-fh-{key}-{i:02d}"
            if role in STAFF_ROLES:
                staff("ind", sr, ["club_season", "IND", str(year), code], nm, role, printed, stated, attr); continue
            full = " ".join(toks(nm)); held_full = rm.by_full.get(full, set()) if len(toks(nm)) > 1 else set()
            if len(held_full) == 1 and next(iter(held_full)) in nb:
                pid = next(iter(held_full)); opened_n["a_exact_name_on_the_neighbouring_season"] += 1
                claim_for(pid, nm, role, where, "exact_full_name_held_once_and_on_the_neighbouring_season",
                          f"exact full name held by one person in the archive, who is on {o['neighbour'][0]} "
                          f"{o['neighbour'][1]} -- the same city's next season. NOT a lineage: the clubs stay unlinked.")
                continue
            # RULING, 2026-09-11 (Ryan, on the 31): a surname unique on the club's ADJACENT season places
            # a man, as a surname unique on the club-season does -- the club does the work, not the
            # calendar. And the refusal is built in, across the boundary: two men of the surname on the
            # season joined TO, or the document printing it twice on the season joined FROM, refuses.
            s_ = surname(nm); here = nb_sur.get(s_, set())
            # THE REFUSAL RUNS FIRST, whatever else is true of the name: 'Carl Beck' is also an exact name
            # held elsewhere, and testing that first sent him to the candidates with the wrong reason while
            # 'C. Beck' was refused -- two Becks printed on one list refuse BOTH.
            if role not in COACH_ROLES and here and (len(here) > 1 or printed_n[s_] > 1):
                opened_n["refused_two_of_the_surname"] += 1
                S["ind"]["refusals"].append({"document": key, "name_as_printed": nm,
                    "club_season": f"IND|{year}|{code}", "neighbouring_season": list(o["neighbour"]),
                    "why": (f"REFUSED: {len(here)} men of surname '{s_}' on {o['neighbour'][0]} {o['neighbour'][1]} "
                            f"({sorted(rm.index_name.get(p) for p in here)[:3]})" if len(here) > 1 else
                            f"REFUSED: the document prints the surname '{s_}' {printed_n[s_]} times on {club} "
                            f"{year}; one man on the adjacent season cannot be both"),
                    "ruling": "Ryan, 2026-09-11: two of the surname on either roster refuses the join"})
                continue
            # PLACED: exactly one man of the surname on the adjacent season -- unless the exact printed name is
            # held by a DIFFERENT person elsewhere (Roy Lumpkin, P_047760, 1939 beside Father Lumpkin on 1930):
            # then joining would choose between two ids, and he stays a candidate with that reason.
            if role not in COACH_ROLES and len(here) == 1 and not (held_full - here):
                pid = next(iter(here)); opened_n["surname_unique_on_the_adjacent_season"] += 1
                ev = (f"surname held by exactly one man on {o['neighbour'][0]} {o['neighbour'][1]}, the same club's "
                      f"adjacent season, and printed once here (Ryan, 2026-09-11)")
                f_ = forename(nm)
                if f_ and not any(v[0][:1] == f_[:1] for n_ in rm.names[pid] for v in variants(n_) if len(v) > 1):
                    ev += f"; NOTE: the printed forename '{f_}' agrees with none of the held forms {sorted(rm.names[pid])[:3]}"
                claim_for(pid, nm, role, where, "surname_unique_on_the_adjacent_season", ev)
                continue
            near = rm.surname_near(surname(nm), year, 2) if forename(nm) is None else []
            if role in COACH_ROLES or nb_sur.get(surname(nm)) or held_full or near:
                opened_n["b_candidate"] += 1
                why = ("a coach named in a caption is a coaching question, not a player promotion" if role in COACH_ROLES
                       else f"the exact printed name is held by a DIFFERENT person elsewhere "
                            f"({sorted(rm.index_name.get(p) or p for p in held_full)[:3]}, {sorted(held_full)[:3]}) while "
                            f"the adjacent season holds {sorted(rm.index_name.get(p) for p in nb_sur[surname(nm)])[:3]}: "
                            "joining would choose between two ids, and a possible unmerged duplicate is for Ryan"
                       if held_full and nb_sur.get(surname(nm)) and (held_full - nb_sur[surname(nm)])
                       else f"a man of surname '{surname(nm)}' is on the neighbouring season "
                            f"({sorted(rm.index_name.get(p) for p in nb_sur[surname(nm)])[:3]}); he may be that man, "
                            "and minting him beside that man is the failure the surname-only refusal exists for"
                       if nb_sur.get(surname(nm))
                       else f"{len(held_full)} person(s) in the archive already carry this exact name "
                            f"({sorted(rm.index_name.get(p) for p in held_full)[:3]}), none on the neighbouring season: "
                            "joining him would be the unique-in-the-archive tier, and minting a second would duplicate him"
                       if held_full
                       else f"a bare surname, and the archive holds man/men of surname '{surname(nm)}' playing within "
                            f"two years ({near[:3]}); he may be one of them")
                S["ind"]["candidates"].append({"document": key, "name_as_printed": nm, "role_as_printed": role,
                    "club_season": f"IND|{year}|{code}", "neighbouring_season": list(o["neighbour"]), "why": why,
                    "ruling": "not joined and not promoted; reported for Ryan"})
                continue
            pid = promoted.get(lead_id)
            if pid:
                opened_n["c_promoted"] += 1
                claim_for(pid, nm, role, where, "promoted_from_this_document",
                          "NOT a join: nobody of this surname is on the neighbouring season and no one person "
                          "holds this exact name there; promoted from this document's lead "
                          "(build/player-promotions.json)")
                continue
            opened_n["c_lead"] += 1
            S["ind"]["leads"].append({"lead_id": lead_id, "category": "player_lead_unpromoted", "IS_NOT_A_PERSON": True,
                "name_as_printed": nm, "evidence_kind": evidence_kind,
                "places_on": {"club_as_printed": printed, "club_code": code, "league": "", "year": year,
                              "club_season": f"IND|{year}|{code}"},
                "source_id": MINE[1], "source_record": sr,
                "why": f"named by a document on {club} {year}, a club-season opened by Ryan's ruling of 2026-09-11; "
                       f"nobody of this surname is on the neighbouring season {o['neighbour'][0]} {o['neighbour'][1]}"})

    for key in ("dayton-1919", "portsmouth-1929"):
        d = DOCS[key]; code = OPENED[key]["code"]
        sr = sr_of("ind", key, f"captioned photograph: {d['printed']}", d["rights"], d["file"])
        stated, attr = "the photograph's caption (publisher not named)", [f"{d['file']} ({FOLDER})"]
        def cf(pid, nm, role, where, tier, ev, d=d, code=code, sr=sr, stated=stated, attr=attr):
            claim("ind", sr, ["stint", pid, code, str(d["year"])], "programme.team_photograph",
                  {"name_as_printed": nm, "held_as": rm.index_name.get(pid), "caption_place": where,
                   "role_as_printed": role, "club_as_printed": d["printed"], "club_code": code, "league": "",
                   "year": d["year"], "_join_tier": tier, "_join_evidence": ev,
                   "_opened_club_season": "Ryan, 2026-09-11: a document naming a squad on a club-season nothing "
                                          "else covers opens it (the Bethlehem and Gilberton shape)"},
                  stated, attr, person=pid)
        opened(key, d["club"], d["year"], d["names"], "team_photograph", sr, stated, attr, d["printed"], cf)
        claim("ind", sr, ["document", d["file"]], "programme.caption_verbatim",
              {"club_as_printed": d["printed"], "names": [f"{nm}{', ' + r if r else ''}" for nm, r, _ in d["names"]]},
              stated, attr)

    P = POTTSVILLE; code = OPENED["pottsville-1924"]["code"]
    sr = sr_of("ind", "pottsville-1924-morning-call", f"{P['printed_in']}: game account and line-ups",
               P["rights"], P["file"])
    stated, attr = "Allentown Morning Call", [P["printed_in"]]
    game = ["game", "IND", "1924", "1924-09-21-pottsville-v-darby"]
    def cfp(pid, nm, role, where, tier, ev):
        key = f"IND|1924|{code}"
        claim("ind", sr, ["person", pid], "roster_membership.started_a_game", key, stated, attr, person=pid,
              extra={"name_as_printed": nm, "position_as_printed": role, "club_as_printed": "Pottsville",
                     "printed_in": P["printed_in"], "_join_tier": tier, "_join_evidence": ev,
                     "_why_started_and_not_probable": "a GAME ACCOUNT printed the day after the game, not a "
                                                      "programme printed before it"})
        claim("ind", sr, ["stint", pid, code, "1924"], "newspaper.lineup_membership",
              {"name_as_printed": nm, "position_as_printed": role, "club_as_printed": "Pottsville",
               "printed_in": P["printed_in"], "_join_tier": tier, "_join_evidence": ev}, stated, attr, person=pid)
    opened("pottsville-1924", "Pottsville Maroons", 1924, [(nm, pos, "Pottsville eleven") for nm, pos in P["eleven"]],
           "printed_lineup", sr, stated, attr, "Pottsville", cfp)
    claim("ind", sr, game, "newspaper.lineup_verbatim",
          {"Pottsville": [f"{nm} {pos}" for nm, pos in P["eleven"]], "Darby": [f"{nm} {pos}" for nm, pos in P["darby"]],
           "_conover_and_yost": "CONOVER (R.G.) AND YOST (R.T.) ARE PRINTED IN DARBY'S COLUMN. Wikipedia's 1924 "
               "Pottsville roster lists both as Pottsville linemen; the clipping, the stronger source, contradicts it "
               "on these two men. Held as printed; Wikipedia's roster is not ingested."}, stated, attr)
    for nm in ("Scott", "Boyd"):
        claim("ind", sr, game, "newspaper.scoring_as_printed",
              {"name_as_printed": nm, "scoring_as_printed": P["scoring"], "club_as_printed": None,
               "_third_assertion": PREDICATE_DEFINITIONS["newspaper.scoring_as_printed"]["definition"]}, stated, attr)
        S["ind"]["leads"].append({"lead_id": f"lead-fh-pottsville-1924-scoring-{nm.lower()}", "category": "player_lead_unpromoted",
            "IS_NOT_A_PERSON": True, "name_as_printed": nm, "evidence_kind": "scoring_summary",
            "places_on": {"club_as_printed": "Pottsville", "club_code": code, "league": "", "year": 1924,
                          "club_season": f"IND|1924|{code}"},
            "source_id": MINE[1], "source_record": sr,
            "why": "named in the scoring only -- not in the eleven, and no substitution is printed. A third "
                   "assertion; the evidence kind is not a roster and promote_players refuses it by default"})
    claim("ind", sr, game, "newspaper.score_as_printed",
          {"text_as_printed": "running up a 39 to 9 victory over Darby at Minersville Park", "headline": P["headline"],
           "_internal_contradiction": "the account's own scoring (six touchdowns and three points after) totals 39 "
               "for Pottsville and lists NO Darby score; Wikipedia's schedule gives 39-0. Held as printed: '39 to 9'."},
          stated, attr)
    claim("ind", sr, game, "newspaper.officials_as_printed", P["officials"], stated, attr)

    # ------------------------------------------------ the 1925 programme
    G = PROG_1925
    sr = sr_of("held", "programme-1925-10-18", "Official Programme, New York Football Giants vs. Yellow Jackets, "
               "Polo Grounds, October 18, 1925: line-up page, team photograph, Folwell article", G["rights"], G["file"])
    stated = "the programme's publisher: New York All Collegians, operating the New York Football Giants"
    attr = ["Official Programme, New York Football Giants vs. Yellow Jackets, Polo Grounds, October 18, 1925"]
    for side, starters, subs, cid, cd, printed in (
            ("giants", G["giants"], G["giants_subs"], "club-new-york-giants-1925", "NYG", "NEW YORK GIANTS"),
            ("fyj", G["fyj"], G["fyj_subs"], "club-frankford-yellow-jackets-1924", "FYJ", "PHILA. YELLOW JACKETS")):
        roster = rm.roster(cid, 1925)
        cur.clear(); cur.update(club_id=cid, year=1925)
        # PRINTED-TWICE IS COUNTED PER LIST. The photo caption repeats the line-up page's men, and a
        # man named in two parts of one programme is one man, not a collision.
        sn = collections.Counter(surname(x) for x in [s[0] for s in starters] + [s[0] for s in subs])
        sn_photo = collections.Counter(surname(p[0]) for p in G["photo"])
        for i, row in enumerate(starters):
            nm, pos = row[0], row[1]
            jersey = row[2] if side == "giants" else None
            college = row[3] if side == "giants" else row[2]
            tier, pid, ev = join(nm, roster, rm, sn)
            if not pid:
                three["not_joined"] += 1
                S["held"]["candidates"].append({"document": "programme-1925", "name_as_printed": nm, "club_season": f"NFL|1925|{cd}",
                    "why": ev, "visible_counterpart_NOT_a_join": counterpart(nm, roster, set(), rm),
                    "ruling": "Ryan, 2026-09-11 (Three): reported, joined to nobody"}); continue
            three[tier] += 1
            claim("held", sr, ["person", pid], "programme.probable_lineup",
                  {"name_as_printed": nm, "jersey_as_printed": jersey, "position_as_printed": pos,
                   "college_as_printed": college, "club_as_printed": printed, "game": G["game"],
                   "printed_before_the_game": True, "_copy": G["copy"], "_join_tier": tier, "_join_evidence": ev},
                  stated, attr, person=pid)
        for row in subs:
            nm, jersey, college = row
            tier, pid, ev = join(nm, roster, rm, sn)
            if not pid:
                three["not_joined"] += 1
                S["held"]["candidates"].append({"document": "programme-1925", "name_as_printed": nm, "club_season": f"NFL|1925|{cd}",
                    "why": ev, "visible_counterpart_NOT_a_join": counterpart(nm, roster, set(), rm),
                    "ruling": "Ryan, 2026-09-11 (Three): reported, joined to nobody"}); continue
            three[tier] += 1
            claim("held", sr, ["stint", pid, cd, "NFL-1925"], "programme.roster_as_printed",
                  {"name_as_printed": nm, "jersey_as_printed": jersey, "college_as_printed": college,
                   "listed_as": "substitutes", "club_as_printed": printed, "game": G["game"], "_copy": G["copy"],
                   "_join_tier": tier, "_join_evidence": ev}, stated, attr, person=pid)
        if side == "giants":
            for nm, where in G["photo"]:
                tier, pid, ev = join(nm, roster, rm, sn_photo)
                if not pid:
                    three["not_joined"] += 1
                    S["held"]["candidates"].append({"document": "programme-1925-photo", "name_as_printed": nm,
                        "club_season": "NFL|1925|NYG", "why": ev, "ruling": "reported, joined to nobody"}); continue
                three[tier] += 1
                claim("held", sr, ["stint", pid, "NYG", "NFL-1925"], "programme.team_photograph",
                      {"name_as_printed": nm, "held_as": rm.index_name.get(pid), "caption_place": where,
                       "club_as_printed": "NEW YORK FOOTBALL GIANTS", "club_code": "NYG", "league": "NFL", "year": 1925,
                       "_copy": G["copy"], "_join_tier": tier, "_join_evidence": ev}, stated, attr, person=pid)

    # ------------------------------------------------ the Kezar programme, 20 January 1935
    K = KEZAR
    sr = sr_of("held", "programme-1935-01-20-kezar", "Knights of Columbus Official Souvenir Program, World's "
               "Champions New York Giants vs. Ernie Nevers' Pacific Coast All-Americans, Kezar Stadium, "
               "Sunday January 20, 1935", K["rights"],
               "1934 ... Football Program/ebay-images.zip and 1935 ... Football Game Program 195520/ebay-images.zip")
    stated = "Knights of Columbus (the programme's publisher)"
    attr = ["Knights of Columbus Fifth Annual Charity Football Classic, official souvenir program, Kezar Stadium, 20 January 1935"]
    roster = rm.roster("club-new-york-giants-1925", 1934)
    cur.clear(); cur.update(club_id="club-new-york-giants-1925", year=1934)
    allnames = [s[0] for s in K["squad"]] + [nm for nm, r, _ in K["giants_photo"] if r not in STAFF_ROLES]
    sn_sq = collections.Counter(surname(x) for x in [s[0] for s in K["squad"]])
    sn_ph = collections.Counter(surname(nm) for nm, r, _ in K["giants_photo"] if r not in STAFF_ROLES)
    sq_pid = {}
    for nm, jersey, pos in K["squad"]:
        tier, pid, ev = join(nm, roster, rm, sn_sq)
        if not pid:
            three["not_joined"] += 1
            S["held"]["candidates"].append({"document": "kezar-squad", "name_as_printed": nm, "club_season": "NFL|1934|NYG",
                "why": ev, "visible_counterpart_NOT_a_join": counterpart(nm, roster, set(), rm),
                "ruling": "reported, joined to nobody"}); continue
        three[tier] += 1; sq_pid[nm] = (pid, tier, ev, jersey)
        claim("held", sr, ["stint", pid, "NYG", "NFL-1934"], "programme.roster_as_printed",
              {"name_as_printed": nm, "jersey_as_printed": jersey, "position_as_printed": pos,
               "listed_as": "NEW YORK GIANTS SQUAD", "club_as_printed": "NEW YORK GIANTS", "game": K["game"],
               "_season": K["season_note"], "_copies": K["copies"], "_join_tier": tier, "_join_evidence": ev},
              stated, attr, person=pid)
    for pos, giants, pcaa in K["lineups"]:
        for order, nm in enumerate(giants, 1):
            if nm not in sq_pid: continue
            pid, tier, ev, jersey = sq_pid[nm]
            claim("held", sr, ["person", pid], "programme.probable_lineup",
                  {"name_as_printed": nm, "jersey_as_printed": jersey, "position_as_printed": pos,
                   "listed_order_at_position": order, "listed_with": [x for x in giants if x != nm],
                   "club_as_printed": "NEW YORK GIANTS", "game": K["game"], "printed_before_the_game": True,
                   "_season": K["season_note"], "_copies": K["copies"], "_join_tier": tier, "_join_evidence": ev,
                   "_several_per_position": "the programme prints two or three men at each position; each is held "
                                            "with his order, and none is read as THE starter"},
                  stated, attr, person=pid)
    for nm, role, where in K["giants_photo"]:
        if role in STAFF_ROLES:
            staff("held", sr, ["club_season", "NFL", "1934", "NYG"], nm, role,
                  "NEW YORK GIANTS 1934-1935 WORLD'S FOOTBALL CHAMPIONS", stated, attr,
                  "the archive holds no Mara as a person; named here as the club's president and joined to no one. "
                  + K["season_note"] + " " + K["copies"])
            continue
        tier, pid, ev = join(nm, roster, rm, sn_ph)
        if not pid:
            three["not_joined"] += 1
            S["held"]["candidates"].append({"document": "kezar-giants-photo", "name_as_printed": nm, "club_season": "NFL|1934|NYG",
                "why": ev, "visible_counterpart_NOT_a_join": counterpart(nm, roster, set(), rm),
                "ruling": "reported, joined to nobody"}); continue
        three[tier] += 1
        claim("held", sr, ["stint", pid, "NYG", "NFL-1934"], "programme.team_photograph",
              {"name_as_printed": nm, "held_as": rm.index_name.get(pid), "caption_place": where, "role_as_printed": role,
               "club_as_printed": "NEW YORK GIANTS 1934-1935 WORLD'S FOOTBALL CHAMPIONS", "club_code": "NYG",
               "league": "NFL", "year": 1934, "_season": K["season_note"], "_copies": K["copies"],
               "_join_tier": tier, "_join_evidence": ev}, stated, attr, person=pid)
    claim("held", sr, K["game"], "programme.club_in_game",
          {"club_as_printed": "ERNIE NEVERS' PACIFIC COAST ALL-AMERICANS", "squad_as_printed": K["pcaa_squad"],
           "lineup_as_printed": {pos: pc for pos, _, pc in K["lineups"]}, "team_photograph_caption": K["pcaa_photo"],
           "_a_scratch_side": "no club-season exists and none is opened: its men are held as printed and joined "
                              "to NO archive person, because the only join available would be a name across the "
                              "whole archive -- the tier ruled out", "_season": K["season_note"],
           "_copies": K["copies"]}, stated, attr)

    # ------------------------------------------------ the Buffalo Courier, 2 December 1921
    sr = sr_of("held", "buffalo-courier-1921-12-02", "Buffalo Courier, December 2, 1921: a three-team all-pro "
               "selection, as transcribed by Jeffrey J. Miller, Pro Football Journal, 31 May 2018",
               "the 1921 newspaper is public domain by date; the TRANSCRIPTION and the post are Miller's (2018) "
               "and are not reproduced", "1921 Long Lost All Pro Team/ (post HTML and the transcription image)")
    stated = "an unidentified season-ticket holder, printed in Billy Kelly's column in the Buffalo Courier"
    attr = ["Buffalo Courier, December 2, 1921 (column of Billy Kelly)",
            "transcribed by Jeffrey J. Miller, 'Long Lost All-Pro Team of 1921', Pro Football Journal, 31 May 2018"]
    for team, sel in COURIER.items():
        for pos, nm, club in sel:
            cid = COURIER_CLUB[club]; roster = rm.roster(cid, 1921)
            cur.clear(); cur.update(club_id=cid, year=1921)
            sn = collections.Counter([nm])
            tier, pid, ev = join(nm, roster, rm, sn)
            val = {"name_as_printed": nm, "year": 1921, "position_as_printed": pos, "honour_as_printed": team,
                   "club_as_printed": club, "selector_as_printed": stated, "published_in": attr[0],
                   "_transcription": attr[1] + " -- the newspaper page itself was not seen",
                   "_definition": "named to an honour team for a season by a named selector -- an all-pro or "
                                  "all-league selection.", "_selector_is_part_of_the_claim": True}
            if nm == "Copley":
                val["_courier_says"] = "Buffalo"; val["_annotation"] = MILLER_NOTE
                if not pid:
                    tier, pid, ev = join(nm, rm.roster(COURIER_CLUB["Akron"], 1921), rm, sn)
                    cur.clear(); cur.update(club_id=COURIER_CLUB["Akron"], year=1921)
                    if pid: ev = ("joined on AKRON 1921, not Buffalo: the Courier prints 'Copley (Buffalo)' and Miller's "
                                  "2018 footnote says he played for Akron. The one join in this store resting on an "
                                  "annotation; both assertions are held with their sources. " + ev)
            if not pid:
                three["not_joined"] += 1
                S["held"]["candidates"].append({"document": "courier-1921", "name_as_printed": nm, "club": club,
                    "why": ev, "ruling": "an honour names a man; unjoined it stays unjoined"}); continue
            three[tier] += 1
            val.update({"_join_tier": tier, "_join_evidence": ev + f" (the 1921 {club} club-season)"})
            claim("held", sr, ["person", pid], "honour_team_selection", val, stated, attr, person=pid)
            if nm == "Copley":
                claim("held", sr, ["person", pid], "annotation.club_correction",
                      {"name_as_printed": "Copley", "club_as_printed_by_the_courier": "Buffalo",
                       "club_asserted_by_the_annotator": "Akron", "annotator": "Jeffrey J. Miller, Pro Football Journal, 2018",
                       "text_as_printed": MILLER_NOTE,
                       "_two_assertions": "the Courier's (Buffalo) and Miller's (Akron) are held apart, each with its source"},
                      "Jeffrey J. Miller", [attr[1]], person=pid)

    # ------------------------------------------------ Bill Coleman: an attachment, not a merge
    # NOT THE SURNAME TIER. Ghosts printed him `BillColeman`, run together, and the archive holds
    # that exactly as printed -- so no surname reading finds him, and splitting run-together names
    # in general would break McCoy and DeMayo, the eight other held names of that shape. The
    # attachment rests on Ryan's ruling of 2026-09-11 for THIS man, and the property that makes it
    # safe is checked rather than assumed: he is the only man on the club-season whose name
    # contains `coleman` at all.
    C_ = COLEMAN
    roster = rm.roster(C_["club_id"], C_["year"])
    cur.clear(); cur.update(club_id=C_["club_id"], year=C_["year"])
    hits = sorted(p for p in roster if any("coleman" in n.lower() for n in rm.names[p]))
    if hits != [C_["person"]]:
        raise SystemExit(f"COLEMAN: the men on {C_['club_id']} {C_['year']} whose name contains 'coleman' are {hits}, "
                         f"not [{C_['person']}]. The attachment was ruled on one held man; stop and look.")
    # SET HERE, NEVER CARRIED OVER. This block once read a `pid` it did not set, and the ten PFA facts
    # below landed on P_002554 -- the Buffalo Smith the Courier section had joined just before.
    pid = C_["person"]
    tier = "ruled_attachment_one_coleman_on_the_club_season"
    ev = (f"Ryan's ruling, 2026-09-11: not a merge -- PFA's full name and dates attach to the one Coleman held. "
          f"He is the only man on AFL|1926|AFLPHI whose name contains 'coleman' (held as printed by Ghosts: "
          f"'BillColeman'); PFA names the same club-season")
    sr = sr_of("held", "pfa-bill-coleman", "Pro Football Archives player page, Bill Coleman (saved page)",
               "facts from Pro Football Archives, the source already ingested", "Bill Coleman ... Pro Football Archives.html")
    stated, attr = "Pro Football Archives", ["Pro Football Archives, player page 'Bill Coleman'"]
    three[tier] += 1
    for pred, v in C_["facts"]:
        claim("held", sr, ["person", pid], pred, v, stated, attr, person=pid,
              extra={"_join_tier": tier, "_join_evidence": ev + " (AFL|1926|AFLPHI); PFA's college, Pennsylvania, "
                     "agrees with the Ghosts record's 'Penn'",
                     "_not_a_merge": "PFA's William Thomas Coleman Jr. is not a second record in the archive; his "
                                     "facts attach to the one Coleman held"})

    # ------------------------------------------------ held for rulings not yet given
    held_back = [
      {"document": "1922 Canton Bulldogs2.webp", "why": "captioned '1922-23': which season the line photo is placed on is not ruled; "
               "its sixteen names are held unplaced"},
      {"document": "1920 Rock Island ... Pro-Football-Reference.com.html", "why": "consult only: all twelve names are already held "
               "on APFA 1920 Rock Island, and PFR's statistics are Neft's"},
      {"document": "1924 Pottsville Maroons season - Wikipedia.html", "why": "tertiary; its roster contradicts the clipping on Conover "
               "and Yost. Consulted, not ingested, until ruled"},
      {"document": "1974 Shreveport Steamer/...Fandom.html", "why": "tertiary (CC BY-SA); the archive already holds 81 men on the club"},
      {"document": "Maybe Useful Someday/ (Mare Island 1918, Elizabeth v Rahway 1924, Columbus Muldoons c.1911)",
       "why": "non-professional club-seasons; whether the archive takes them is not ruled"}]
    claim("held", sr_of("held", "canton-1922-23-line", "captioned photograph: CANTON BULL DOGS World's Professional "
          "Champions 1922-23", "photograph of 1922 or 1923 -- public domain by date", "1922 Canton Bulldogs2.webp"),
          ["document", "1922 Canton Bulldogs2.webp"], "programme.caption_verbatim",
          {"club_as_printed": "CANTON BULL DOGS World's Professional Champions 1922-23",
           "names": ["Roy Lyman", "B. Guy Chamberlin", "Louis Symthe", "Joe Williams", "Cecil Griggs", "Ben Jones",
                     "Wilbur Henry", "Larry Conover", "Harry Robb", "Norman Speck", "Roudolph Comstock", "Wallace Elliott",
                     "Robert Osborne", "Oscar Hendrian", "Elmer Carroll", "Walcott Roberts"],
           "_unplaced": "the season is printed as '1922-23'; no one is placed until Ryan rules which"},
          "the photograph's caption (publisher not named)", ["1922 Canton Bulldogs2.webp"])

    SOURCE = {"source_id": MINE[0], "name": "The Football Hunting folder -- photographs, programmes, clippings and "
              "saved pages Ryan gathered", "acquisition": "photographed and saved pages, supplied by Ryan",
              "stated_by": "per document; see each source record", "attribution": [FOLDER],
              "rights": "PER DOCUMENT, never assumed for the folder -- each source record carries its own",
              "transcription": "one reader, NOT checked by a second (Archive, 2026-09-11)",
              "inventory": "reports/2026-09-11-football-hunting-inventory.md"}
    outs = {}
    for which, path, sid in (("held", OUT, MINE[0]), ("ind", OUT_IND, MINE[1])):
        s = S[which]
        outs[which] = {"source": {**SOURCE, "source_id": sid}, "source_records": s["srecs"],
            "predicate_definitions": PREDICATE_DEFINITIONS, "claims": s["claims"], "leads": s["leads"],
            "candidates": s["candidates"], "refusals": s["refusals"],
            "held_back": held_back if which == "held" else [],
            "counts": {"claims": len(s["claims"]), "leads": len(s["leads"]), "candidates": len(s["candidates"]),
                       "by_predicate": dict(collections.Counter(c["predicate"] for c in s["claims"])),
                       "people_touched": len({c["person"] for c in s["claims"] if c.get("person")}),
                       **({"the_three_numbers": dict(three)} if which == "held" else {"opened_club_seasons": dict(opened_n)})}}
        if write:
            IO.write_store(outs[which], path, reasons=_restated(s["claims"]), indent=1)
    return outs


if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    for w, d in o.items():
        c = d["counts"]
        print(f"{w}: claims {c['claims']}  leads {c['leads']}  candidates {c['candidates']}  people {c['people_touched']}")
        print(f"   {c.get('the_three_numbers') or c.get('opened_club_seasons')}")
        print(f"   {c['by_predicate']}")
    if "--write" not in sys.argv:
        print("DRY RUN -- nothing written. --write to write.")
