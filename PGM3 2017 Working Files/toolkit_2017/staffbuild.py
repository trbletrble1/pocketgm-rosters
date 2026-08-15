"""Build PGM3 staff records field-by-field.

Two rules from section 8 are load-bearing here:

1. NEVER clone a record and overwrite the headline field. The 2010 build did and
   produced 27 coaches sharing one avatar and ratings that collapsed on hire,
   because only the primary attribute was set and the rest kept the template's.
   Every record here is constructed from an empty dict, every field assigned.

2. NEVER let a name repeat. The 2010 build shipped 51 duplicates including 19
   people simultaneously employed and in the free agent pool. A single registry
   holds every name already used anywhere in either file.
"""
import random

PRIM = {'Head Coach': 'HCcoach', 'Off Co-ord': 'OCcoach', 'Def Co-ord': 'DCcoach',
        'Special Teams': 'STcoach', 'Head Scout': 'Hscout', 'Off Scout': 'Oscout',
        'Def Scout': 'Dscout', 'Head Physio': 'Hphysio', 'Assistant Physio': 'Aphysio'}

STYLE = {
    'blitzStyle': ['High', 'Medium', 'Low'],
    'physType': ['Preventor', 'Healer', 'Balanced'],
    'rbStyle': ['Lead Back', 'Bellcow', 'Backfield Committee'],
    'scoutType': ['Diamond Spotter', 'Current Evaluator', 'Balanced'],
    'fourthStyle': ['Aggressive', 'Cautious', 'Balanced'],
    'offStyle': ['Pro Style', 'West Coast', 'Spread', 'Air Raid', 'Smashmouth', 'Option'],
    'defStyle': ['3-4 Man', '3-4 Zone', '4-3 Man', '4-3 Zone', '4-2 Man', '4-2 Zone',
                 'Hybrid Man', 'Hybrid Zone'],
    'scoutBoost': ['QB', 'RB', 'WR', 'TE', 'OT', 'OG', 'C', 'DE', 'DT', 'OLB', 'MLB', 'CB', 'S'],
    'physBoost': ['Broken Leg', 'Turf Toe', 'High Ankle Sprain', 'Torn Hamstring', 'Lisfranc',
                  'Torn Bicep', 'Shoulder Sprain', 'Torn Pectoral', 'Hamstring Strain',
                  'Broken Foot', 'Knee Sprain', 'Ankle Sprain', 'Torn ACL', 'Concussion',
                  'Torn Tricep'],
}

# Invented-name stock. Deliberately ordinary American coaching names; checked
# against the registry so nothing collides with a real person in the file.
FORE = ['Dale', 'Curt', 'Wendell', 'Roy', 'Marcus', 'Glen', 'Terry', 'Neil', 'Vaughn',
        'Cliff', 'Dwayne', 'Lamar', 'Bruce', 'Owen', 'Rex', 'Hal', 'Deon', 'Grant',
        'Lyle', 'Ross', 'Vince', 'Clay', 'Otis', 'Nolan', 'Reggie', 'Warren', 'Gene',
        'Milton', 'Sid', 'Perry', 'Cal', 'Emmett', 'Bernard', 'Rudy', 'Lonnie', 'Cecil',
        'Dexter', 'Wade', 'Hollis', 'Marvin', 'Elmer', 'Rufus', 'Barrett', 'Judd',
        'Winston', 'Alton', 'Percy', 'Horace', 'Delmar', 'Royce']
SUR = ['Tolliver', 'Brennan', 'Whitfield', 'Ackerman', 'Rademacher', 'Stallworth',
       'Kettering', 'Vandergriff', 'Hobbs', 'Mulcahy', 'Prentice', 'Ashby', 'Deveraux',
       'Coyle', 'Bramlett', 'Ferrante', 'Nadeau', 'Quintero', 'Sandoval', 'Okafor',
       'Lindquist', 'Boudreaux', 'Marchetti', 'Yancey', 'Pruitt', 'Halloran', 'Estrada',
       'Kowalczyk', 'Bertrand', 'Skinner', 'Vaughters', 'Delgado', 'Ruffin', 'Castellano',
       'Winslow', 'Abernathy', 'Trombley', 'Sowell', 'Machado', 'Kirkpatrick', 'Dupree',
       'Bledsoe', 'Rhoades', 'Ontiveros', 'Fitzhugh', 'Calloway', 'Sedillo', 'Hargrove',
       'Petrosian', 'Wojcik', 'Amundsen', 'Beaulieu', 'Cardoso', 'Ivory', 'Landrum']


class NameRegistry:
    """Every name used anywhere in either file. Prevents the 51-duplicate bug."""

    def __init__(self, taken=()):
        self.used = {self._k(f, s) for f, s in taken}

    @staticmethod
    def _k(fore, sur):
        return f"{fore.strip().lower()} {sur.strip().lower()}"

    def claim_real(self, fore, sur):
        """Register a real person. Returns False if the name is already present."""
        k = self._k(fore, sur)
        if k in self.used:
            return False
        self.used.add(k)
        return True

    def invent(self, rng):
        for _ in range(4000):
            f, s = rng.choice(FORE), rng.choice(SUR)
            if self._k(f, s) not in self.used:
                self.used.add(self._k(f, s))
                return f, s
        raise RuntimeError('name stock exhausted')


def build_record(role, rating, potential, age, team_id, fore, sur, iden,
                 model, mask, appearance, rng, growth_len=31,
                 off_style=None, def_style=None, salary=0, guarantee=0,
                 length=0, e_salary=0, e_guarantee=0, e_length=0, start_season=2026):
    """Construct one staff record from scratch. No cloning, no inheritance."""
    rec = {}

    # 1. every numeric attribute from the fitted per-role model
    m = model[role]
    for field, spec in m.items():
        if spec[0] == 'const':
            v = spec[1]
        else:
            v = spec[1] + spec[2] * rating + rng.gauss(0, spec[3] * 0.45)
        rec[field] = int(max(1, min(99, round(v))))

    # 2. apply the per-role field mask — zero everything this role should not carry.
    #    staff_consistency.apply() floors at 1, which is what left every 2010
    #    record with 1s in fields belonging to other roles.
    for field in list(rec):
        if not mask[role].get(field, False):
            rec[field] = 0

    # 3. the primary attribute MUST equal rating or it collapses on hire
    rec[PRIM[role]] = rating

    rec['rating'] = rating
    rec['potential'] = potential
    rec['age'] = age
    rec['role'] = role
    rec['teamID'] = team_id
    rec['forename'] = fore
    rec['surname'] = sur
    rec['iden'] = iden
    rec['startSeason'] = start_season
    rec['salary'] = salary
    rec['guarantee'] = guarantee
    rec['length'] = length
    rec['eSalary'] = e_salary
    rec['eGuarantee'] = e_guarantee
    rec['eLength'] = e_length
    rec['greed'] = _trait(rng)
    rec['loyalty'] = _trait(rng)
    rec['ambition'] = _trait(rng)
    rec['appearance'] = appearance
    rec['growthType'] = [0] * growth_len
    for field, vocab in STYLE.items():
        rec[field] = rng.choice(vocab)
    if off_style:
        rec['offStyle'] = off_style
    if def_style:
        rec['defStyle'] = def_style
    return rec


def _trait(rng):
    r = rng.random()
    if r < 0.28:
        return rng.randint(8, 29)
    if r < 0.72:
        return rng.randint(40, 69)
    return rng.randint(72, 96)
