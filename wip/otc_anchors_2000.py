OTC = {
 # QB
 'Drew Bledsoe':8537857,'Mark Brunell':7300000,'Peyton Manning':6699333,
 'Jake Plummer':6030000,'Troy Aikman':5915892,'Tim Couch':5246231,
 'Steve McNair':4133017,'Rob Johnson':3753750,'Brett Favre':3675000,
 'Donovan McNabb':2212142,'Kurt Warner':2000857,'Chad Pennington':1122477,
 'Brian Griese':478000,'Tom Brady':205833,
 # RB
 'Jerome Bettis':4200000,'Emmitt Smith':3672000,'Curtis Martin':3530325,
 'Marshall Faulk':2852703,'Eddie George':2784668,'Terrell Davis':2452218,
 'Shaun Alexander':1064875,'Priest Holmes':472000,'Tiki Barber':472000,
 # WR
 'Jerry Rice':4521427,'Marvin Harrison':3277295,'Joey Galloway':2225714,
 'Rod Smith':2200000,'Ed McCaffrey':1600000,'Randy Moss':1321000,
 'Hines Ward':465000,'Brandon Stokley':290000,'Donald Driver':260666,
 # TE
 'Shannon Sharpe':1625000,'Tony Gonzalez':1355000,
 # K — the real 2000 kicker market tops out near $1.1M. The published files
 # put K at 1.50x the league median with a p95 of $7.68M, which is the same
 # K/P inflation defect as the ratings. Do not inherit it.
 'Jason Elam':1071167,'Sebastian Janikowski':1061000,'Adam Vinatieri':875000,
 'Phil Dawson':275000,
 # LB
 'Junior Seau':4623333,'Ray Lewis':3310000,'Keith Brooking':1458333,
 'Brian Urlacher':1400000,'Al Wilson':927500,'Ian Gold':601250,
 'London Fletcher':405500,
 # CB
 'Ty Law':3946218,'Charles Woodson':3308333,'Aaron Glenn':2395177,
 'Sam Madison':2201678,'Deion Sanders':1642857,'Champ Bailey':1521500,
 'Chris McAlister':1519375,'Antoine Winfield':976000,'Patrick Surtain':610000,
 'Ronde Barber':552000,
 # S
 'John Lynch':3308333,'Brian Dawkins':2326666,'Kenoy Kennedy':550000,
 # OL
 'Orlando Pace':4151666,'Jonathan Ogden':4021285,'Tony Boselli':3105974,
 'Kevin Mawae':2835000,'Walter Jones':2270396,'Mark Schlereth':2078000,
 'Tom Nalen':1450000,'Alan Faneca':1200000,
}
# EXCLUDED and why:
#   Matt Hasselbeck  — OTC lists him twice, Seahawks and Packers. He was a
#                      Packer in 2000; the Seattle row is misattributed.
#   Levon Kirkland   — cap number reads $0, a hole in OTC itself.
EXCLUDED = {'Jason Hanson': 'OTC lists two different cap numbers for him',
            'Matt Hasselbeck': 'listed twice, one row misattributed',
            'Levon Kirkland': 'OTC cap number is $0'}
