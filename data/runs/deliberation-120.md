# CivicTwin - resident deliberation

**The population is synthetic.** It is generated from Singapore open transport data and demographic distributions. No resident here is a real person.

## The policy

> Close bus stops 54241 and 54248 on Ang Mo Kio Ave 3 and let service 265 run non-stop between them. No extra buses, no budget increase.

## What this run can and cannot speak for

- **2000** residents in the study area
- **120** asked to reason (affected 44, tied 76, comparison 0)
- **109** produced an account that survived the grounding guard
- **1891** were never asked. They are *unknown*, not unaffected.
- **8** were asked and said nothing that could be checked
- 70 turns rejected; 23 changed course without saying why (kept, and counted)

Model `deepseek-r1:8b` - 44 calls, 30 from cache, 7101s

## What they decided

| metric | value |
|---|---|
| `n` | 109 |
| `avg_journey_time_delta` | 0.0 |
| `severe_harm_count` | 2 |
| `severe_harm_rate` | 0.0183 |
| `essential_trip_completion` | 1.0 |
| `walk_distance_p90` | 768 |

Every rate above is over **109 evaluated residents**, not over 2000.

## What residents said would help


Asked for something this model cannot represent, which is a finding rather than a gap to hide:

- **2** - something else this model cannot represent
  - "A closer bus stop or alternative transportation options for my frequent hospital visits."
  - "A more accessible bus stop closer to home."
- **1** - somewhere to sit or shelter while waiting
  - "somewhere to sit while I wait"

## The residents

### Mr Ang - `p_0524`

*65-74, employed, mild difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.15

- **Round 0** - I'm used to the services stopping at Blk 700B, especially for my morning walk down Avenue 3 and trips home or out.
  - *grounded in:* `p_0524:f1`, `p_0524:f2`
- **Round 1** - The policy closes Blk 700B (54241), which is my normal bus stop and the one I use for trips to Ang Mo Kio Community Hosp—I wouldn’t skip it because of difficulty walking over longer distances or relying solely on buses if necessary. Now, I have to walk to Opp Al-Muttaqin Mque (54031) which is 360m away—much farther than the current 135m from my home and within manageable distance given my mild walking issues. This could mean longer daily commutes or increased physical effort, especially if I still need service 265 for work-related trips (8:30 AM). The change might also indirectly affect hospital visits but not directly.
  - *changed because:* p_0736, p_0985
  - *grounded in:* `p_0524:f1`, `p_0524:f8`
- **Round 3** - The policy closes Blk 700B (fact grounded_in: #p_0524:f9), my usual stop, and the nearest alternative is Opp Al-Muttaqin Mque at 360m—too far to walk comfortably due to my mild walking difficulty. I am employed starting work at 8:30 AM, so this increase in travel time might mean longer daily commutes or reduced efficiency.
  - *what would help:* "A more accessible bus stop closer to home."
  - *grounded in:* `p_0524:f1`, `p_0524:f9`

### Chua Mei Ling - `p_0847`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.65 -> 0.25

- **Round 0** - I mostly use bus from Ang Mo Kio Int, stop number 54009, to get around town for work and errands because I start at 8am so it's not too bad. The nearest stop is only about half a km away which is manageable even when tired after walking up to one point.
  - *grounded in:* `p_0847:f1`, `p_0847:f3`
- **Round 3** - The policy doesn't affect my normal stop but it does impact the Blk 700B stop that I used, which might be relevant for other residents near me or in the same area as Ang Mo Kio Int has services that could still work, so no change yet.
  - *grounded in:* `p_0847:f3`, `p_0847:f6`

### Tan Beng Chye - `p_0168`

*65-74, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.35

- **Round 0** - I'm a bit older, still working at age 68 and start around 8:30 AM each day – though I retired now but used to work till this time. My closest bus stop is Castle Green (55171), it's about 599 m away which I can handle without a problem normally because walking that much isn't bad for me. But the hospital trip, Ang Mo Kio Community Hosp, cannot be skipped though its straight line distance from home is listed at 648m – way too long to walk even if we have a car. This proposed change might not affect my main commute but could impact my hospital trips.
  - *grounded in:* `p_0168:f1`, `p_0168:f2`
- **Round 2** - Hearing from p_0169 and others that the policy removes services at Blk 700B (fact grounded_in: #p_0168:f9) might be part of a broader trend affecting bus stops with mild walking difficulty, but fact f4 suggests I could handle up to 1200m walks. The hospital trip requires transport from home as it's too far (fact p_0168:f4), so if the policy reduces service availability at close points like Castle Green or affects efficiency due to longer waits for others.
  - *grounded in:* `p_0168:f9`
- **Round 3** - The policy's closure of Blk 700B (fact p_0168:f6) is my usual stop and I use it for the hospital trip mentioned in facts f1 to f4. This change necessitates a longer walk from home or other adjustments given my mild walking difficulty per fact f3, making me consider substituting this leg of my journey with alternatives if available. Observing p_0852's mention about potential impact on similar routines reinforces the severity but doesn't address household vehicle factors directly.
  - *grounded in:* `p_0168:f1`, `p_0168:f3`, `p_0168:f4`, `p_0168:f5`, `p_0168:f6`

### Ms Ho - `p_0666`

*55-64, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.90 -> 0.75

- **Round 0** - I'm fine walking up to twelve hundred meters for a bus stop, but I don't like waiting much because of the car at home.
  - *grounded in:* `p_0666:f4`, `p_0666:f2`
- **Round 1** - I use the bus stop at Blk 700B (54241) and it's closing, so I'll have to walk further to Opp Al-Muttaqin Mque (54031). The distance has increased from 112 meters to 383 meters—which is manageable with my walking ability up to 1200 meters but adds extra time during commute.
  - *grounded in:* `p_0666:f1`, `p_0666:f2`, `p_0666:f6`

### Lau Kim Leng - `p_0852`

*65-74, employed, mild difficulty walking*

**adapting**, severity **moderate**, support 0.30 -> 0.18

- **Round 0** - I usually don't have any trouble getting around, but I do the regular checkup at Ang Mo Kio Community Hosp which is about 2115 m straight line – definitely not a walkable distance for me given my mild walking issues and that I wouldn't go beyond an extra bus stop. But currently, Opp Blk 649 (54469) stops by services including the one I take, like the 138 or 668. If they close two of these specific stops on Ave 3 for service 265 to run non-stop without stopping as mentioned – which might affect my way to hospital too because it's near there – that could be a big deal.
  - *grounded in:* `p_0852:f1`, `p_0852:f2`
- **Round 2** - The closed bus stops near p_0849's home might reduce the frequency of buses stopping at Opp Blk 649, which I also rely on for commuting to work and potential hospital trips. This could mean longer waits or fewer convenient options if service adjustments impact my routine similarly.
  - *changed because:* Realization that service 265's non-stop operation could affect bus routes converging at my usual stop.
  - *grounded in:* `p_0852:f1`, `p_0852:f2`, `p_0852:f3`, `p_0852:f4`, `p_0852:f5`, `p_0852:f6`, `p_0852:f7`, `p_0852:f8`

### Chua Hui Ling - `p_1051`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.40 -> 0.30

- **Round 0** - They're talking about closing a nearby primary school bus stop and changing service 265? That sounds confusing because I usually use that number for commuting to work, but maybe it's part of bigger plans. Since my home is close enough to the Ang Mo Kio Pr Sch stop, and there are other services like 132 around here too, perhaps this change will save some time overall or make buses busier during rush hours.
  - *grounded in:* `p_1051:f1`, `p_1051:f2`
- **Round 1** - I use the Ang Mo Kio Pr Sch bus stop (765 meters away) normally for commuting to work starting at 07:00 and there are other services available like 132, so this policy change might save time or make buses more efficient during rush hours.
  - *grounded in:* `p_1051:f1`, `p_1051:f3`

### Wei Min Tan - `p_0848`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.50

- **Round 0** - The policy says to close Blk 700B stop and let service 130, which I sometimes use starting work at 08:30, run without stopping between stops 54241 and 54248. But my nearest is still that same stop Blk 700B (54241) about 551 meters away. Since I can walk up to a kilometer easily, maybe it's okay but not ideal.
  - *grounded in:* `p_0848:f1`, `p_0848:f2`, `p_0848:f3`
- **Round 1** - The policy directly closes the bus stop I normally use. Now, my nearest alternative is Blk 322 (54247), which is slightly further away at about 594 meters compared to my current half-kilometer walk. While I can still walk there without too much trouble due to p_0848:f4, the increased distance might mean a longer commute if this becomes my only option.
  - *moved by:* `p_0847`
  - *grounded in:* `p_0848:f1`, `p_0848:f2`, `p_0848:f6`

### Tan Siew Fen - `p_1665`

*65-74, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.30 -> 0.20

- **Round 0** - I know that Ang Mo Kio Community Hosp is too far for me to walk, about four kilometers away in a straight line, but I don't usually complain if buses get faster as long as it doesn't mess up my daily trips there by bus every morning.
  - *grounded in:* `p_1665:f3`, `p_1665:f4`
- **Round 1** - With the bus stop at Blk 700B closing, my trip to Ang Mo Kio Community Hospital has changed. Previously, I relied on a quick walk from that stop, but now it's gone and the nearest alternative is much further away. This means walking longer distances or possibly more car trips than before just to get to my bus stop for the hospital journey.
  - *moved by:* `p_1666`
  - *grounded in:* `p_1665:f3`, `p_1665:f8`, `p_1665:f9`

### Chen Jia Ren - `p_0788`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 1.00 -> 0.92

- **Round 0** - The bus stop changes at Blk 700B are really nothing for me since I'm a student and the nearest ones might be slightly further – but only by about 35 meters from where my friends sit? Anyway, if service 265 runs non-stop without stopping here or nearby, that's fine. Most days I just walk to catch one of the buses like 130 or 138 anyway, and sometimes when I get tired walking, I ride school bus home.
  - *grounded in:* `p_0788:f2`
- **Round 1** - I rely on the Blk 700B stop for daily commutes to school, and it's closing due to service 265 running non-stop without stops. This means I'll have to walk longer or find alternative routes now – but as a student who walks up to 1200m with ease, this doesn't seem too problematic.
  - *grounded in:* `p_0788:f3`, `p_0788:f4`
- **Round 3** - The policy removes my nearest bus stop at Blk 700B (54241), forcing me to walk +324m to Opp Al-Muttaqin Mque (54031) now that service 265 runs non-stop. I'm a student who walks easily up to 1200m so this distance increase is manageable, but it does require more time for my morning travels.
  - *grounded in:* `p_0788:f1`, `p_0788:f3`, `p_0788:f4`

### Wong Jia Yi - `p_1684`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.75 -> 0.70

- **Round 0** - I go home every day via buses from Ang Mo Kio Ave, and I find walking is okay up to a point (p_1684:f4). From my facts, nearest stop is Blk 586 with walk of 559 meters, which gets me close but not exactly at the target stops mentioned in policy. However, service 265 happens to call here per p_1684:f2, and walking from this stop might be needed if they're closing certain routes on that number.
  - *grounded in:* `p_1684:f3`, `p_1684:f5`
- **Round 1** - I don't use Blk 700B or the nearby stops that are being closed, so this policy doesn't directly affect my journey to hospital with service 265 stopping at Blk 586. However, hearing about it might mean fewer bus options on Ang Mo Kio Ave if other services aren't available there anymore.
  - *grounded in:* `p_1684:f3`, `p_1684:f7`

### Lim Tze Hong - `p_0850`

*65-74, retired, mild difficulty walking*

**adapting**, severity **moderate**, support 0.20 -> 0.15

- **Round 0** - Okay, so they're closing bus stops near me and making the 265 service run non-stop between them without adding more buses or money. I need to go every day to Ang Mo Kio Community Hospital; it's a bit over five thousand meters from my place too far to walk. But my nearest stop is Blk 307A, about four hundred twenty meters away and manageable for me since the doctor said with mild difficulty walking, I shouldn't push more than eight hundred meters at most. Normally when buses are slow or crowded, that's a problem, but this policy might not directly affect my current routine much.
  - *grounded in:* `p_0850:f1`, `p_0850:f2`, `p_0850:f3`, `p_0850:f4`
- **Round 1** - The policy closes two stops that I might otherwise use for convenience, including the morning routine for my walker household member p_0849. Since they are not directly impacting me, but affecting others near these stops, it doesn't change my support level much, though their frustration is noted.
  - *moved by:* `p_0849`
  - *grounded in:* `p_0850:f1`, `p_0850:f6`
- **Round 2** - The policy removes the bus stops near my household member p_0849, who relies on them for their hospital trip and daily commute. This indirectly affects me as it reduces the number of services calling at Blk 307A, which I also use occasionally. However, since these changes are impacting others more directly, I am reconsidering my support slightly.
  - *changed because:* Observation of how the change affects p_0849 and alters service patterns at Blk 307A.
  - *grounded in:* `p_0850:f1`, `p_0850:f2`, `p_0850:f3`, `p_0850:f4`, `p_0850:f5`, `p_0850:f6`, `p_0850:f7`, `p_0850:f8`, `p_0850:f9`

### Loh Siew Keat - `p_1046`

*65-74, retired, no difficulty walking*

**substituting**, severity **moderate**, support 0.30 -> 0.28

- **Round 0** - I am retired and walk to Blk 324 stop, which is about 421 meters from my home. This stop has buses like 130, 132, etc., and I need one of them for regular trips to Ang Mo Kio Community Hosp—it's a must for me since the hospital is too far to walk directly (54248). However, if service 265 runs non-stop between Blk 324 and Blk 700B, it might be faster in theory but requires walking from my home or using another route. I have a car at home with mild difficulty sometimes going out, so maybe it won't affect me much unless the change makes buses slower on other routes.
  - *grounded in:* `p_1046:f1`, `p_1046:f2`, `p_1046:f3`
- **Round 1** - My regular trips to Ang Mo Kio Community Hosp now depend on the nearest open stop Blk 322 (about 611m away), which is further than my current usual walk of 421 meters and introduces more difficulty because I can only comfortably walk up to around 500-600 meters. The increased walking might lead me to take on bus journeys for others, like elderly relatives who cannot drive themselves.
  - *grounded in:* `p_1046:f3`, `p_1046:f9`
- **Round 3** - The policy makes it harder for me to get to Ang Mo Kio Community Hospital without relying on the household car, which may affect my ability to assist elderly relatives.
  - *changed because:* I realized that walking 611 meters is beyond my comfortable limit, especially given my age and health considerations.
  - *what would help:* "somewhere to sit while I wait"
  - *grounded in:* `p_1046:f3`, `p_1046:f8`

### Yi Lin Pang - `p_0120`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.40 -> 0.40

- **Round 0** - Starting work at eight-thirty, I'd normally take the 138M from Blk 700B which is just about a hundred and eighty three meters away - not bad for me since walking to five stops isn't an issue when my household doesn't have a car. The news that service 265 will run straight past here means I have to walk further every morning, but maybe it saves time so the journey itself might be worth it.
  - *grounded in:* `p_0120:f3`
- **Round 1** - This policy directly impacts my morning routine, closing Blk 700B stop which I previously used—now walking to Opp Al-Muttaqin Mque (code 54031) is a bigger effort due to the longer distance, but since service 265 itself runs non-stop and it’s still early enough for my start time at eight-thirty, maybe this change helps me save valuable waiting or travel time.
  - *grounded in:* `p_0120:f1`, `p_0120:f3`
- **Round 2** - The policy is closing my usual bus stop, Blk 700B (54241), which I relied on for my morning commute to work starting at 08:30. The nearest open alternative is Opp Al-Muttaqin Mque (code 54031), about +319m from my home, making the walk longer and more strenuous due to fact f4 limiting me to up to 1200m walks without difficulty. Service 265 running non-stop means I might save waiting time in theory if it arrives faster, but given my age (fact p_0120:f3) and household situation (fact p_0120:f5), the increased walking effort could disrupt my routine.
  - *grounded in:* `p_0120:f1`, `p_0120:f6`, `p_0120:f8`
- **Round 3** - I rely on the closure of Blk 700B (54241) in my facts to be relevant for this policy. However, service p_0120:f2 confirms that I don't use any other services mentioned here as a regular commute option except via bus stop f6. But note: last round we reasoned the closure would increase walking effort and possibly disrupt routine because of proximity factors (p_0120:f8). Now, observing p_0121's comment about relying on service 130 or others might alter my view regarding whether this trip is essential despite age group. Also, considering that Blk 700B was explicitly mentioned as mine in fact f7 and closed per policy, the impact remains directly tied to me unless household vehicle availability (p_0120:f5) can be leveraged or service patterns change for other routes I use regularly.
  - *grounded in:* `p_0120:f3`, `p_0120:f4`, `p_0120:f5`, `p_0120:f6`, `p_0120:f7`, `p_0120:f8`

### Ming Xuan Ho - `p_0121`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.70 -> 0.70

- **Round 0** - I used to walk from home to Blk 700B stop and then take the 138M or another service for work, but I'm told that my nearest bus stop will be closed off entirely with the car park nearby being bypassed by non-stop service 265. Starting at eight-thirty each day makes me think this might actually help because it's faster than walking here and then to the next stop - about one hundred seventy two meters walk is manageable, but I'm looking forward to a quicker trip.
  - *grounded in:* `p_0121:f3`
- **Round 1** - I used to walk to Blk 700B stop (54241) which is about 172m away and then take buses like the 138M or other services for work starting at 08:30. Now that this stop is closed, I have to walk further to Blk 322 (54247), a distance of 521m which adds an extra +349 meters compared to the previous walk. This means my usual morning routine now involves walking almost half a kilometer more than before just to reach the nearest open stop, increasing my total daily steps and potentially affecting my start time.
  - *grounded in:* `p_0121:f1`, `p_0121:f3`, `p_0121:f4`, `p_0121:f6`, `p_0121:f8`
- **Round 2** - Fact p_0121:f6 states the policy closes Blk 700B (54241) and Blk 324 (54248), which directly impacts me as I used them before for my work commute starting at 08:30. The nearest open stop is now Blk 322 (54247) about +349m from home, significantly increasing walking distance due to fact p_0121:f4 allowing up to 1200m but this adds inconvenience for my age group and without a car. Others mentioning longer walks or hospital trips in their reasoning makes me think this affects people differently based on household vehicles.
  - *grounded in:* `p_0121:f6`, `p_0121:f7`
- **Round 3** - Fact p_0121:f6 states the policy directly affects me by closing Blk 700B (54241) which is my nearest stop per fact f1 and essential for my morning routine starting at 08:30 as a bus user. The increased walking to Opp Al-Muttaqin Mque now outweighs my capacity for up to 1200m walks, forcing adaptation despite household's no car status (fact p_0121:f5). Neighbours' comments mentioning longer waits or service disruptions elsewhere might signal broader systemic effects that I was previously unaware of in fact f4 and f9.
  - *grounded in:* `p_0121:f1`, `p_0121:f2`, `p_0121:f3`, `p_0121:f4`, `p_0121:f5`, `p_0121:f6`, `p_0121:f7`, `p_0121:f8`

### Mr Loo - `p_0665`

*65-74, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.80 -> 0.80

- **Round 0** - I'm retired but still find it easy to walk up to eight hundred meters, so I rely on the bus stops and take buses like 136 or the evening ones.
  - *grounded in:* `p_0665:f4`, `p_0665:f2`
- **Round 1** - I rely on the bus stop at Blk 700B (54241) for my mild walking difficulty, and it's closing which affects me significantly. The nearest open alternative is Opp Al-Muttaqin Mque (54031), about 368 meters away—twice as far as before—which I can't comfortably manage.
  - *grounded in:* `p_0665:f1`, `p_0665:f2`, `p_0665:f3`, `p_0665:f4`, `p_0665:f6`
- **Round 2** - The policy effectively removes Blk 700B (54241) from my daily routine, forcing me to walk an additional 241 meters which adds significant time and effort despite having a car available for occasional use.
  - *changed because:* The change affects my mild difficulty walking constraint more than I initially thought, impacting my commute.
  - *grounded in:* `p_0665:f3`, `p_0665:f7`
- **Round 3** - The policy closes Blk 700B (54241) bus stop, which was my nearest and only regularly used stop due to my mild walking difficulty. Previously, I could walk up to 800m but now the minimum walk is 368m with multiple services still available. However, the increased distance adds significant time especially on my commute days before work when retired.
  - *grounded in:* `p_0665:f1`, `p_0665:f2`, `p_0665:f4`, `p_0665:f7`

### Tan Wei Shun - `p_0672`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I'm a student and usually take the bus to school, but my nearest stop is only 187 meters from home anyway so walking there isn't much trouble for me even if buses skip stops further away sometimes.
  - *grounded in:* `p_0672:f4`, `p_0672:f5`
- **Round 1** - I was already aware that Blk 700B is closing, and I am under 18 so walking to the new stop at Opp Al-Muttaqin Mque (now +334 meters from home) wasn't much trouble anyway since it's still within my capabilities of walking up to 1200m. The increase in distance doesn't significantly affect me as a student.
  - *grounded in:* `p_0672:f3`, `p_0672:f4`
- **Round 2** - I am still a student and walking up to 1200m is no problem for me, so the increased distance to Opp Al-Muttaqin Mque (now +334 meters from home) doesn't affect my daily routine much. However, I heard p_0786 mention concerns about longer waiting times or inconvenient travel due to the policy's indirect effects on routes.
  - *changed because:* p_0786's comment about indirect effects
  - *grounded in:* `p_0672:f1`, `p_0672:f2`, `p_0672:f3`, `p_0672:f4`
- **Round 3** - The policy removes my nearest bus stop, requiring me to walk an additional 334 meters despite being a student with no walking difficulty up to 1200m. My household has a car so I don't expect significant change yet, but the increased waiting time and inconvenience might affect future commuting habits.
  - *grounded in:* `p_0672:f1`, `p_0672:f2`

### Ong Teck Kim Hua - `p_0199`

*55-64, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - The proposed change involves fewer buses, but I don't know if it helps me as I use other services not mentioned.
  - *grounded in:* `p_0199:f1`, `p_0199:f4`, `p_0199:f5`
- **Round 1** - Previously, I was unaffected by the policy change because it didn't impact my usual bus stops or services. However, hearing from p_267 about their elderly companion's trip to Ang Mo Kio Community Hospital has made me realize that closing nearby stops might indirectly affect residents like myself who rely on accessible transit for essential trips.
  - *changed because:* Hearing about p_267's elderly companion concern
  - *grounded in:* `p_0199:f3`, `p_0199:f4`, `p_0199:f6`
- **Round 2** - I previously thought the policy wouldn't affect me, but now I'm concerned that even though my usual stops aren't directly impacted, some residents might be forced to walk longer distances or substitute their routes with less convenient options due to closed stops like Blk 324 (54248).
  - *changed because:* Neighbours discussing accessibility changes forced me to consider the wider impact.
  - *grounded in:* `p_0199:f1`, `p_0199:f6`
- **Round 3** - I previously thought the policy wouldn't affect me because my usual stops aren't directly impacted, but after hearing from neighbours like p_0267 about concerns for elderly companions and p_0666 about longer walks to substitute routes, I realize that closed stops might indirectly alter how people travel. This change could impact residents who rely on these bus stops due to mobility issues or lack of alternatives.
  - *grounded in:* `p_0199:f3`, `p_0199:f4`, `p_0199:f6`

### Liu Wei Xuan - `p_0787`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I normally take service 265 to work, but it doesn't stop at Blk 700B where I am – my nearest is actually the other end of Ang Mo Kio Ave if memory serves correctly from looking at buses 130 and 138. The change might not affect me much because most days I walk anyway for my morning exercises, but I'll need to check closer when it happens.
  - *grounded in:* `p_0787:f1`, `p_0787:f2`
- **Round 1** - I was not directly affected by the policy before because I use service 265 but it doesn't stop at Blk 700B anyway, and my nearest open stop is Opp Al-Muttaqin Mque (54031) which is closer than some alternatives. Now that Blk 700B (54241) is closing, I need to walk the extra distance or adjust my route if service 265 does call here without stopping. The closure might indirectly affect me as I consider other services for convenience.
  - *grounded in:* `p_0787:f1`, `p_0787:f3`, `p_0787:f4`, `p_0787:f6`
- **Round 3** - The policy closes Blk 700B (54241) stop which I relied on for getting to work, forcing me to walk the extra +239m to Opp Al-Muttaqin Mque (54031). Previously my reliance was minimal since service 265 didn't stop there anyway, but now it directly impacts my morning commute.
  - *grounded in:* `p_0787:f1`, `p_0787:f7`

### Lim Mei Ling - `p_0789`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 1.00 -> 1.00

- **Round 0** - I normally take one of the services to Blk 700B, but that's only because I need a bus stop break after school before going home via service 258 or something? No, wait – all these buses go to work areas like Ang Mo Kio Hub. And since my house is only 118 meters from there, the closure might actually help me if I switch to service 265 running non-stop without breaks.
  - *grounded in:* `p_0789:f3`
- **Round 1** - I use the Blk 700B stop for school commutes, but it's closing which means I have to walk more or adapt my transport habits.
  - *grounded in:* `p_0789:f3`, `p_0789:f4`
- **Round 3** - The policy closes Blk 700B (my normal stop), so I need to walk the extra distance or adjust my route for service 265 if it calls here without stopping. The nearest open stop is Opp Al-Muttaqin Mque, which is +259m away, requiring a longer walk than usual but still within my capability as a student who can handle up to 1200m walks easily.
  - *moved by:* `p_0787`
  - *grounded in:* `p_0789:f3`, `p_0789:f6`

### Lau Zhi Xuan - `p_1589`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - My nearest stop is Blk 758 (54241), just a short walk of about 276 m from home. I'm usually on services like 138M or 133 to get around for my part-time job and school stuff. The change might not affect the bus service timings, but since my stop is closing down, maybe some buses won't call anymore? Or perhaps service 265 will be calling closer now? I'm too young to have a car anyway, so walking longer distances isn't easy for me—up to about 1200 m might be okay if necessary. But let's see how the hospital is involved here.
  - *grounded in:* `p_1589:f2`, `p_1589:f4`
- **Round 2** - As a student, I rely on buses for my part-time job and school activities. The closure of Blk 700B stop means I must now walk to Opp Al-Muttaqin Mque which is +46m away from home compared to before, so my usual trips to catch the 138M bus would require a longer initial walk. Since I'm <18 and can handle up to 1200m walks with no problem, this might be manageable but adds inconvenience daily.
  - *grounded in:* `p_1589:f6`, `p_1589:f7`, `p_1589:f8`
- **Round 3** - The policy closes the bus stop I use for my part-time job and school activities, forcing me to walk an additional +46m each time I need to catch a bus like 138M. As a student who can handle up to 1200m walks but relies on buses for convenience, this daily change adds significant inconvenience despite being manageable in terms of physical ability.
  - *changed because:* p_1587 and p_1666 mentioned that their reliance on Blk 700B stop is impacting me.
  - *grounded in:* `p_1589:f6`, `p_1589:f7`, `p_1589:f3`, `p_1589:f4`

### Chen Ean Lee - `p_0169`

*65-74, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.40 -> 0.40

- **Round 0** - They mentioned the policy about closing bus stops and having service number 265 run straight without stopping, but I'm wondering how this affects me since my nearest stop is different, at Castle Green which is six hundred twenty-seven meters away from home. That's too far to walk because with mild difficulty walking, normally I wouldn't go beyond eight hundred meters for a bus stop. There are services that call here: 114, 668, and others like 71 – so if they're adjusting the route by removing stops near me, it might mean fewer options or longer waits because other buses don't stop there as often.
  - *grounded in:* `p_0169:f1`, `p_0169:f2`, `p_0169:f3`, `p_0169:f4`
- **Round 2** - Fact p_0169:f8 and f2 confirm that none of the closed stops (Blk 700B or Blk 324) are my usual bus stop at Castle Green, so this change does not directly affect me for commuting work. However, as a retired person with mild walking difficulty, I rely on household vehicle availability (fact p_0169:f5). If the service adjustments impact others' travel times or routes in ways that might indirectly influence my own trips.
  - *grounded in:* `p_0169:f2`, `p_0169:f3`
- **Round 3** - As an unaffected resident last round due to no reliance on the closed stops (fact p_0169:f7), my reasoning this round considers that service changes might affect efficiency for others like p_0168 who have similar household setups but older age and mild walking issues. However, I still don't need these services myself as per facts f2 to f4 — the nearest stop is too far away anyway. The comments from neighbours suggest some adaptation elsewhere that doesn't directly help me unless my own route shifts.
  - *grounded in:* `p_0169:f3`, `p_0169:f4`, `p_0169:f5`

### Lim Bao Xiang - `p_1706`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.59 -> 0.59

- **Round 0** - Bao Xiang walks to Blk 564 and uses various services including the one being modified by closing stops on Ang Mo Kio Ave 3.
  - *grounded in:* `p_1706:f1`, `p_1706:f2`
- **Round 1** - As someone who relies on buses to work starting at 07:30, the closure of Blk 700B and the other nearby stop might mean I have less convenient options if my usual route is affected by fewer stops or altered service patterns. But since none are directly relevant to me yet, this affects my thinking about future travel.
  - *moved by:* `p_0635`
  - *grounded in:* `p_1706:f3`, `p_1706:f4`
- **Round 3** - Even though none of the affected stops are my usual ones, I might need to adapt if other services change or if my access improves indirectly from this policy affecting nearby residents like p_1666 and p_1756.
  - *grounded in:* `p_1706:f3`, `p_1706:f4`

### Hui Min Tan - `p_0098`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - I usually take the 138M or the 132 to work at 7:30am, but they don't stop here anymore because Blk 700B is being closed off for service 265 only. The walk from home to that stop is about 218 meters - not too far in my book since I can handle up to a kilometer walking without trouble. It'll mean changing my routine, but the car is parked at home so no big deal.
  - *grounded in:* `p_0098:f5`, `p_0098:f3`
- **Round 1** - In this round, the policy announcement that bus stop Blk 700B (code 54241) is being closed for service 265 non-stop has made me realize how directly this affects my daily commute. Previously, I was content with minor inconveniences because walking up to a kilometer wasn’t much trouble, but now the increased walk distance means I might need to reconsider relying solely on the car even though it’s parked at home.
  - *grounded in:* `p_0098:f1`, `p_0098:f2`, `p_0098:f3`, `p_0098:f4`

### Kwai Lin Chng - `p_0099`

*18-34, unemployed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I don't really use the bus for work since I'm between jobs, but sometimes I hop one just to see how it works or go out with friends. The policy says they're closing my nearest stop Blk 700B so that service 265 can run non-stop - well that's about 170 meters walk anyway, but the car is still here if needed.
  - *grounded in:* `p_0099:f3`, `p_0099:f1`
- **Round 1** - Hearing from my neighbor p_0098 about the policy change, I now understand that Blk 700B is being closed even though it’s only 170 meters away for me—unlike their car option, but since we have a household car and can handle up to 1200 meters walking without difficulty, this affects my routine less directly than if the walk was longer.
  - *grounded in:* `p_0099:f1`, `p_0099:f2`, `p_0099:f3`

### Madam Tan - `p_0523`

*75+, retired, severe difficulty walking*

**substituting**, severity **high**, support 0.30 -> 0.30

- **Round 0** - I live close to stop 54241, so normally I walk there easily for my regular bus trips and catch services like 138M homebound.
  - *grounded in:* `p_0523:f1`, `p_0523:f2`
- **Round 3** - The policy closes Blk 700B (fact grounded_in: #p_0523:f9), which is my usual stop and required for trips to Ang Mo Kio Community Hosp, despite it being too far to walk directly now. This means I must now walk the additional distance or find alternative transport if no bus services are available at nearby stops like Opp Al-Muttaqin Mque (54031).
  - *changed because:* Hearing from p_0736 about the non-stop service and lack of family assistance for mobility.
  - *what would help:* "A closer bus stop or alternative transportation options for my frequent hospital visits."
  - *grounded in:* `p_0523:f1`, `p_0523:f9`, `p_0523:f6`

### Lau Mei Lin - `p_0670`

*35-54, unemployed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I've heard buses will be faster between home and work, but I'm not sure how it affects me personally because I don't have a job right now. My nearest stop is Blk 700B at 213 meters away, and I usually wait for one of the services that stops here like 138 or 138M to commute in the morning. If they close it, maybe service 265 will come earlier since no one gets off there anymore? It might mean fewer buses during my usual travel times though.
  - *grounded in:* `p_0670:f2`, `p_0670:f1`
- **Round 1** - My main concern is that the closing of Blk 700B (54241) might lead to fewer buses coming my way, even though I don't have a job now and there's no direct impact on my commute.
  - *grounded in:* `p_0670:f1`, `p_0670:f2`

### Eugene Tan - `p_0756`

*75+, retired, mild difficulty walking*

**absorbing**, severity **none**, support 0.20 -> 0.20

- **Round 0** - I'm worried about this bus change. My nearest stop is Blk 324, which I can reach in just a short 135m walk from home, and it's where my daughter helps me get to the hospital every morning for my checkup. Now they want to close that stop completely with service 265 skipping right over it? That means even though Blk 324 is close by, I won't be able to catch a bus there anymore because services normally call at it like the 130s and 165s do. Instead they're pushing for me to use service 265 which runs non-stop between my original stop location (which must mean Ang Mo Kio Ave something) and another point further away since I don't know where exactly those stops are numbered 54241 or 54248 actually are. But the worst part is that Ang Mo Kio Community Hospital is over 4km from here, too far for any old person like me to walk regularly anyway, and service 265 doesn't stop near Blk 324 at all so my morning routine will be completely disrupted if I'm forced into using it. Also being retired means I don't have other transport options typically since we don't even own a car.
  - *grounded in:* `p_0756:f1`, `p_0756:f2`, `p_0756:f3`, `p_0756:f4`, `p_0756:f5`
- **Round 1** - The closure of Blk 324 is a direct problem because it's my nearest stop and I can't walk more than 800 meters normally without difficulty due to my mild mobility issues. Now, having no car option, the non-stop service might not help as it doesn't stop near home or at Blk 324 itself. The advice from neighbors p_0757 and others on alternative stops like Blk 322 feels inadequate because they're farther away (about +83m), requiring more walking than usual.
  - *grounded in:* `p_0756:f1`, `p_0756:f3`, `p_0756:f4`, `p_0756:f8`

### Amy Koh - `p_0757`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.30 -> 0.30

- **Round 0** - I heard the bus service change might affect my elderly mother, who lives with me and struggles a bit walking. She normally uses the same Ang Mo Kio Community Hospital stop near here for her trips because Blk 324 is only about 120m away from our home according to fact p_0756:f1. Now if they're closing stops on Ang Mo Kio Ave 3, including probably where she needs the bus now? It's unclear how this will impact her routine since hospitals are far but maybe service 265 can help as long as it doesn't require walking too much more than usual.
  - *grounded in:* `p_0757:f1`, `p_0757:f2`, `p_0757:f3`
- **Round 1** - I'm realizing that while I can walk without difficulty, the bus service changes could affect me because I often use buses that stop at nearby Blk 324 for my work commute to Ang Mo Kio Primary School. But more importantly, if the hospital trip is affected by this change which involves our elderly mother needing assistance from home, then indirectly it might impact us as her support system.
  - *changed because:* Understanding the elderly resident's need for help with walking near home due to service changes.
  - *grounded in:* `p_0757:f1`, `p_0757:f3`

### Marcus Lim - `p_0758`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.40 -> 0.40

- **Round 0** - As a student living in this area, I rely on the frequent buses stopping at Blk 324 to get around easily since we don't have a car and my walk distance is manageable up to over 1km away from home. Now they want to close stops near me including probably Ang Mo Kio Community Hospital route? That sounds confusing but maybe service 265 will work better for getting between nearby places.
  - *grounded in:* `p_0758:f3`
- **Round 1** - As a student, I rely heavily on the frequent bus stops at Blk 324 for my daily commute to Ang Mo Kio Primary School and other places without car assistance. The non-stop service might mean fewer buses stopping by as they skip my usual stop location entirely if it's being replaced elsewhere in this policy change.
  - *grounded in:* `p_0758:f1`, `p_0758:f3`

### Vivian Foo - `p_0759`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - I think the proposed bus network change might not be great for me, especially since I need to go regularly to Ang Mo Kio Community Hospital which is quite far from here as per fact p_0754:f4—about four and a half kilometers away in straight line. Normally we don't have trouble with it because there are buses stopping at Blk 324 only around three blocks over, where I can catch the 136 bus or something without too much walking. But if they're closing stop numbers like p_0754:f1 and forcing me to use service 265 running non-stop from probably one farther point to another even more distant, that could mean longer walks for someone my age who's fine with up to twelve kilometers walk distance.
  - *grounded in:* `p_0759:f3`
- **Round 1** - The information from my neighbor p_0756, who is elderly and uses the same hospital route, indicates that they are worried about the bus stop closure at Blk 324 affecting their morning routine for getting to Ang Mo Kio Community Hospital. This confirms that using service 265 non-stop would require them to walk further or not catch it directly from home, which aligns with my own concern since I also rely on Blk 324 as a regular stop and have no car.
  - *grounded in:* `p_0759:f1`, `p_0759:f6`, `p_0759:f7`

### Lim Boon Teik - `p_1007`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I'm still young and I can walk, so maybe this doesn't affect me much right now. But if the bus is faster then it might be worth checking how far I have to go.
  - *grounded in:* `p_1007:f3`, `p_1007:f4`
- **Round 3** - The closure affects me directly as I use Blk 324, but since I have a car in my household and can walk the distance, it might not be too disruptive initially.
  - *changed because:* I learned that I have a car in my household, which lessens the reliance on buses.
  - *grounded in:* `p_1007:f5`, `p_1007:f6`

### Chua Hock Seng - `p_1080`

*35-54, employed, no difficulty walking*

**adapting**, severity **none**, support 0.45 -> 0.45

- **Round 0** - I don't have a car at home and walk to Blk 700B stop (98 meters). I'm employed from 09:00 onwards, so I use buses regularly—services here include those that go my way or near Ang Mo Kio Community Hospital. But the policy says they are closing stops like 54241 and making service 265 non-stop between? That might mean some rerouting without car access for me, since Blk 324 is nearby but not as close—about 400 meters away I think (from p_1047 data). However, if it affects my commute time to work or the trip to hospital via bus stop changes significantly because buses won't call here anymore, then yes, but for now services at Blk 324 are there and not directly impacted.
  - *grounded in:* `p_1080:f1`, `p_1080:f2`
- **Round 1** - My nearest stop Blk 700B is closing, so I need to walk at least 311 meters more and use a different bus or carpool. The non-stop service might affect my commute if buses are rerouted.
  - *grounded in:* `p_1080:f6`, `p_1080:f7`

### Ling Wei Min - `p_1181`

*18-34, employed, no difficulty walking*

**absorbing**, severity **none**, support 0.25 -> 0.25

- **Round 0** - I work at 08:00, so I start from Blk 700B stop (58 meters walk). Without a car, the bus is my main transport—services there are plenty for me including those that might go via Ang Mo Kio Community Hospital. But if they close nearby stops like on Ang Mo Kio Ave3 side and force buses to be non-stop between, it could mean longer wait or different travel times because Blk 324 isn't my nearest—it's farther away (my home is not at that end; p_1080 might know distances better). I would have to walk more if the new service doesn't call at my stop anymore—perhaps up to a mile? That could be tiring since walking without difficulty, but 542 meters straight line isn't impossible.
  - *grounded in:* `p_1181:f1`, `p_1181:f2`
- **Round 1** - As a regular bus user without car access for long distances, I rely heavily on Blk 700B stop closing at eight-thirty; my alternative is Bef Al-Muttaqin Mque which is slightly farther and not as direct for hospital visits.
  - *grounded in:* `p_1181:f2`, `p_1181:f9`

### Chua Mei Ling - `p_1587`

*35-54, employed, no difficulty walking*

**adapting**, severity **none**, support 0.60 -> 0.60

- **Round 0** - Eh, the bus stop near my home is being closed. That's Blk 704 (54241). I normally take service 138M from there to get around for work. But now it'll be gone, so I have to see what other buses come by. Service 130 also stops here sometimes but not every day. The policy says bus 265 will run non-stop between the old Blk 704 stop and the next one. That's fine for me as long as it passes close enough. I'm starting work at 7 am, so if my usual services are affected too much during rush hour, I might have to figure out a new way to get there.
  - *grounded in:* `p_1587:f2`, `p_1587:f3`
- **Round 1** - The policy removes my nearest bus stop, Blk 700B (p_1587:f1), which I use regularly for work with services like 138M and 130. Since these are closing or not affected by the changes, there's a need to reassess commuting options—perhaps service 265 via Opp Al-Muttaqin Mque (p_1587:f8) could be an alternative, but walking three hundred meters might mean starting work later than usual.
  - *changed because:* The realization that my own stop is closing down has necessitated a new way to commute, perhaps checking service 265 timing or walking distance.
  - *grounded in:* `p_1587:f7`, `p_1587:f8`

### Nguyen Jia Hui - `p_1588`

*35-54, employed, no difficulty walking*

**adapting**, severity **moderate**, support 0.70 -> 0.70

- **Round 0** - The bus stop at Blk 738 (54241) is the closest, about 266 m from home. I usually take services 138 or 130 to go to Ang Mo Kio Community Hospital for appointments every other week. But they are not calling there anymore since it's being closed down. The policy mentions letting bus service 265 run non-stop between the two stops. That means I'll have to check if that route works as a substitute or how much trouble it will be walking further. Since I can't skip my hospital trip, this might affect me more than others.
  - *grounded in:* `p_1588:f2`, `p_1588:f3`
- **Round 1** - The information from p_1587 and the policy details confirm that bus stop Blk 738 (54241) is closing, affecting my access to services like 138M which I rely on for hospital trips. This means a longer walk starting from Opp Al-Muttaqin Mosque, about +50 meters compared to p_738 due to the non-stop bus service 265.
  - *changed because:* Neighbour p_1587's comments and the policy.
  - *grounded in:* `p_1588:f9`, `p_1588:f3`

### Ho Ee Lin - `p_0158`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - I usually walk to the nearest stop Aft Ang Mo Kio Stn Exit A (54261) since we don't have a car, and it's only about 192m away so fine for me. The buses serving that stop are key for my morning routine as I start work late at 9am too. Faster might be nice but walking is part of my daily life already.
  - *grounded in:* `p_0158:f1`, `p_0158:f3`
- **Round 1** - As a resident who doesn't use any of the closing stops (Blk 700B or Blk 324), I rely on my nearest stop Aft Ang Mo Kio Stn Exit A (54261). The policy makes service 265 run non-stop without stopping at these areas, but since it doesn't affect me directly yet, I'm still unaffected. However, knowing that residents like p_0098 are changing their routines because of this might mean that over time the route adjustment could impact other stops nearby.
  - *grounded in:* `p_0158:f7`, `p_0158:f6`

### Ling Si Chen - `p_1902`

*18-34, unemployed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - Even though I'm young and unemployed right now, Blk 209 is my nearest stop at about 153 meters away. My family has a car so we can still drive to places normally if the bus becomes too inconvenient. Services stopping here include 165 which goes past many of our potential job locations, I think that could be affected significantly by any changes.
  - *grounded in:* `p_1902:f1`, `p_1902:f3`
- **Round 1** - I am 18-34 and unemployed, so my reliance on the bus for job opportunities is minimal as per p_1902:f3. However, since I do not normally use the closed stops (p_1902:f7), this change does not directly affect me. My household has a car (p_1902:f5) which provides flexibility, making any minor adjustments to bus services irrelevant for my daily commutes.
  - *grounded in:* `p_1902:f3`, `p_1902:f6`

### Priya - `p_0348`

*18-34, employed, mild difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - My main issue is that my closest stop, Blk 586 (bus stop code 54271), is being closed along with others nearby. I normally take service 132 or 265 from there to work at 7:30 AM, but according to fact p_0348:f2, these services also call at other stops like Ang Mo Kio Pr Sch (code 54229). Fact p_0348:f4 says I have mild difficulty walking more than 800 meters, so if the new service from Blk 561 doesn't stop nearby or is not available on my route, it might be a problem. The fact that buses will run non-stop between Ang Mo Kio Pr Sch and other points means that some services might not have convenient stops for me.
  - *grounded in:* `p_0348:f2`, `p_0348:f1`
- **Round 1** - I have to consider the impact of this policy on my daily commute. Fact p_0348:f7 confirms that none of the closing stops are mine, so I'm unaffected by them directly. However, fact p_0348:f2 shows that services 132 and 265 stop at Blk 586 (code 54271), which is my usual spot. The policy removes service 265 stops, but since it also calls via other points like Ang Mo Kio Pr Sch (fact p_0348:f1 references services stopping there including 265 and 132), I can still access these routes. My mild difficulty walking (p_0348:f4) means I prefer shorter walks, but Blk 586 is only 443m away; however, the fact that my usual stop isn't closed shouldn't affect me too much.
  - *grounded in:* `p_0348:f1`, `p_0348:f2`, `p_0348:f7`

### Siti - `p_0760`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.45 -> 0.45

- **Round 0** - The proposal is to close stops at my home, Ang Mo Kio Pr Sch (stop code 54229), and let service 165 operate non-stop from there or nearby points? Actually, fact p_0760:f1 says nearest stop is Ang Mo Kio Pr Sch, about 768 meters away. But with the change, I might have to walk longer if those stops are removed. Fact p_0760:f2 lists services that do call at this stop: 132, etc., but service 265 is mentioned in another fact for a different resident. My household has no car according to p_0760:f5.
  - *grounded in:* `p_0760:f2`, `p_0760:f1`
- **Round 1** - Having heard from p_0120 about the potential impact on walking distance due to bus stop closures, I realize that my usual access point might become less convenient if service 265 requires longer walks or changes its stopping pattern.
  - *grounded in:* `p_0760:f1`, `p_0760:f6`

### Chua Wei Xiang - `p_0114`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.65 -> 0.65

- **Round 0** - I'm used to the slow buses near my home, Blk 452 stop. Service 132 and 265 usually keep me waiting because of their stops along Ang Mo Kio Ave 3. But since I have a car for short trips, maybe I don't rely on buses as much.
  - *grounded in:* `p_0114:f2`, `p_0114:f3`
- **Round 1** - The policy closing Blk 700B and others doesn’t affect me directly since I use Blk 452 (code 54289). However, the news has raised awareness about general service changes due to non-stop buses—maybe that means more wait times or inconvenient stops elsewhere? I need to keep an eye on my usual routes like services calling at 132 and if they are altered.
  - *grounded in:* `p_0114:f1`, `p_0114:f2`

### Chang Si Min - `p_1447`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.85 -> 0.85

- **Round 0** - I'm very used to the bus services at Blk 209 stop near home, and I walk with no problem up to a kilometer for buses on my way to work starting at nine AM. If service number two six five runs non-stop faster between these specific Ang Mo Kio stops, it might help reduce waiting times.
  - *grounded in:* `p_1447:f2`, `p_1447:f3`
- **Round 1** - The policy closes the nearby stops but I don't normally use them anyway, as my usual stop at Blk 209 is unaffected and still served by multiple services including 265 now running non-stop. Since service 265 might be faster even though it doesn't affect me directly, this could slightly improve overall transit efficiency without personal cost.
  - *grounded in:* `p_1447:f3`, `p_1447:f4`

### Kenneth Lee - `p_0313`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - Usually I start work early so the morning rush hour buses are fine. The Blk 570 stop (bus stop code 54281) is only 407 meters away and I can easily walk that without breaking a sweat. But honestly, this news about closing stops 54241 and 54248 – which aren't my usual ones anyway since they're further down Ang Mo Kio Ave 3 – doesn't impact me much right now because no extra buses are involved. I'm just wondering what the practical effect will be if we remove bus stops, maybe fewer people use this particular service? But for my daily routine by Blk 570 with services like 265 and 165 calling there, nothing seems to change directly. The changes might not really affect where I go in terms of commuting distance – it's still manageable on foot.
  - *grounded in:* `p_0313:f2`, `p_0313:f3`, `p_0313:f4`
- **Round 1** - The policy doesn't directly impact my nearest stop or my regular commute, but knowing that nearby stops are closed might change bus service patterns which could indirectly affect accessibility and timing for future needs.
  - *grounded in:* `p_0313:f2`, `p_0313:f6`

### Amelia Koh - `p_1162`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.75 -> 0.75

- **Round 0** - I work in the mornings starting from 09:00 and rely mainly on bus for my commute without using our household car – I think I can manage up to a kilometer walk just fine. Right now, it doesn't seem like this policy change will impact me because Opp Ang Mo Kio Pr Sch is not where I live or go directly; but maybe indirectly? No service numbers are mentioned that would be affected by the closure of stops 54241 and 54248 on my route – wait, no, it's about service 265 which is one of them. But since I already walk from Opp Ang Mo Kio Pr Sch to get there easily, why take this risk? I'm considering that maybe the trip times will be faster so perhaps I could use this service more often or something like that.
  - *grounded in:* `p_1162:f2`, `p_1162:f3`
- **Round 1** - My nearest stop is Opp Ang Mo Kio Pr Sch (375 meters) and I walk without difficulty up to a kilometer, but this policy change might indirectly affect me if buses are rerouted or my commute time changes.
  - *grounded in:* `p_1162:f2`

### Eleanor Tan - `p_0736`

*75+, retired, moderate difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - Although I don't normally walk more than half a km due to my walking difficulties – that's why we have a car available sometimes – this particular change doesn't directly affect me since the Castle Green stop (code 55171) is still there and close enough for me. But the idea of buses not stopping makes me pause because normally family member p_0737 would help get us from home to bus stops, but I can see why this might change things if we need longer walking or more inconvenience dealing with a regular trip down the road to Ang Mo Kio Community Hosp which is too far for my current ability. However, since services at Castle Green include 114 and others that don't require stopping changes elsewhere on the route like between 54241-54248, maybe I'm overthinking it.
  - *grounded in:* `p_0736:f6`, `p_0736:f3`
- **Round 1** - Although the bus stop changes don't directly impact my nearest Castle Green stop, I realize now that service 265 might not provide an efficient alternative because it doesn't call at Blk 324 or nearby stops, and we rely on family member p_0737 to assist with our mobility. The closed stops are far from where I normally walk for short trips, but the non-stop feature could mean longer travel times if I need to use this service indirectly for my hospital visit.
  - *changed because:* Learning from neighbor p_0757's perspective on the hospital trip.
  - *grounded in:* `p_0736:f1`, `p_0736:f2`, `p_0736:f8`

### Maureen Tan - `p_0985`

*75+, retired, severe difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - I usually catch bus service 13 or 852 from Opp Courts Ang Mo Kio to get to the community hospital for my check-ups, but if they close stops 54041 and 54048? Wait no, that's not it. The policy says close stops 54041 and 54048—wait is that Opp Courts or something else? Let me read again: 'Close bus stops 54241 and 54248 on Ang Mo Kio Ave 3' — I think they mean along the road. Anyway, my nearest stop is at home's opposite side, about 770 meters walk away because Opp Courts AMK is too far for me to handle even just walking there without any breaks. Since it’s already my bus stop and I’m used to catching buses from here on a regular basis going to hospital which isn’t close enough by foot alone anyway—let's see, the distance straight line wise to hospital is 2683 meters? That sounds like more than three laps around this block! No way could I walk that much without getting exhausted. So normally I don't even think about what would happen if my nearest stop changes because it’s so close and convenient already.
  - *grounded in:* `p_0985:f1`, `p_0985:f2`
- **Round 1** - I am a retired individual who makes regular trips to Ang Mo Kio Community Hospital (f3), normally catching service 13 or 852 from Opp Courts stop (f1). While my nearest bus stop is already very close at home's opposite side, the policy closes Blk 324 (54048) which might slightly alter routes but doesn't directly harm me. However, I'm concerned about increased walking if this affects access to future hospitals.
  - *grounded in:* `p_0985:f1`, `p_0985:f3`

### Ng Weng Kim - `p_1935`

*65-74, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - They're talking about closing bus stops and modifying service 265 to not stop, which sounds interesting but probably doesn't affect me since my nearest stop is Blk 645 at three hundred eleven meters away – that's manageable with or without a car because I walk fine up to twelve hundred meters. Actually, there's a vehicle in the household from fact p_1935:f5, so even if buses change schedule it might be convenient not to use them as much for the hospital trip that goes daily: five point one thousand one meters from home and too far without transport, but with a car nearby maybe we can handle this.
  - *grounded in:* `p_1935:f1`, `p_1935:f2`
- **Round 2** - The policy is closing bus stops near my home, but I was already unaffected because Blk 700B (54241) wasn't my usual stop and I use the existing one at Blk 645. Since this doesn't impact my daily routine or the hospital trip managed by p_1936, it shouldn't change anything for me.
  - *grounded in:* `p_1935:f3`, `p_1935:f4`

### Liu Keng Hua - `p_0834`

*65-74, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.65 -> 0.65

- **Round 0** - My nearest bus stop is Courts Ang Mo Kio, only 139 meters away. I usually take services like 851 or even the M service if it goes my way without making too many transfers. The policy says buses will be faster between stops on Ave 3, but that doesn't directly affect me because I'm not using those specific service numbers mentioned for the closed stops.
  - *grounded in:* `p_0834:f1`, `p_0834:f2`
- **Round 1** - The policy doesn't directly affect my usual bus stop at Courts Ang Mo Kio, as I'm retired and don't rely on it for daily commuting. Walking up to a kilometer is manageable even in old age, but the change might indirectly impact other services like buses between Blk 700B and 324 stops that I sometimes use without issue.
  - *grounded in:* `p_0834:f1`, `p_0834:f2`

### Tan Bee Choo - `p_1488`

*55-64, employed, mild difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - My nearest stop is the AMK Police Div HQ, which I can reach with mild difficulty due to my limited walk distance of up to 800 meters. The news about service 265 bypassing certain stops might actually help if those closed ones are not on my usual route anymore.
  - *grounded in:* `p_1488:f1`, `p_1488:f2`, `p_1488:f3`
- **Round 3** - The policy closes nearby stops but does not affect my primary stop at AMK Police Div HQ, so I don't expect any direct changes. However, I've heard from p_1487 about potential ripple effects on public transport efficiency, which might indirectly influence travel times or convenience.
  - *grounded in:* `p_1488:f3`, `p_1488:f6`

### Eugene Lim - `p_0090`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.65 -> 0.65

- **Round 0** - I was told buses would be faster between stops 54241 and 54248, which aren't my nearest ones anyway. My main bus stop is Aft Ang Mo Kio Int, where I take service 159B to work every day at eight-thirty in the morning. Maybe the change won't affect me much if they're consolidating routes or something.
  - *grounded in:* `p_0090:f3`, `p_0090:f2`
- **Round 1** - I am a professional aged around 45, employed and starting work at 8:30 AM every day. My main bus stop is Aft Ang Mo Kio Int (code 54391), about 343 meters from home. The policy closing Blk 700B (54241) might affect me indirectly if I need to catch service 265 at these points for connections, as the bus stop is closer than my usual one but not a direct part of my commute route.
  - *grounded in:* `p_0090:f1`, `p_0090:f7`

### Michelle Koh - `p_0430`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.70 -> 0.70

- **Round 0** - I read online that bus service 265 will run non-stop between those two places – Ang Mo Kio Int and Opp Pr Sch, I think? But my daily route is via Blk 564 stop where services include 132, 165, etc. For me it might not matter as long as buses aren't overcrowded or delayed on the usual ones.
  - *grounded in:* `p_0430:f2`, `p_0430:f3`
- **Round 1** - The policy closes Blk 700B (54241) and Blk 324 (54248), but my nearest stop is Opp Ang Mo Kio Pr Sch (54221). Fact p_0430:f6 states that service 265 runs non-stop between these two, so I need to check if this affects my access. However, fact p_0430:f2 indicates services calling at Opp Pr Sch include multiple numbers including 268 and 132. Fact p_0430:f7 says none of the closing stops are mine, meaning Blk 586 (my stop) is unaffected by this policy directly.
  - *grounded in:* `p_0430:f1`, `p_0430:f2`

### Priya Gopal - `p_0654`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.75 -> 0.75

- **Round 0** - I heard about the non-stop service for buses running between Ang Mo Kio Int and Opp Pr Sch – my nearest stop is Blk 564, which might not be affected directly. But if this means fewer bus stops overall or changes to routes I use like number 268A, it could make commuting harder because we don't have a car and the walk can be long.
  - *grounded in:* `p_0654:f1`, `p_0654:f2`
- **Round 1** - I heard about the non-stop service for buses running between Ang Mo Kio Int and Opp Pr Sch, but my nearest stop is Blk 564 (54291), which was not directly affected by this policy change. However, I am concerned that other services might be impacted indirectly due to route adjustments or schedule changes.
  - *grounded in:* `p_0654:f1`, `p_0654:f2`, `p_0654:f3`

### Loo Meng Keat - `p_1778`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I heard the plan to skip stops on service 265 between my home and work areas, but I don't think it'll affect me much since Blk 209 is very close anyway. Plus, other services like 132 still stop here, so options remain open for shorter walks or different timings.
  - *grounded in:* `p_1778:f1`, `p_1778:f2`
- **Round 1** - Since Blk 700B was not my nearest stop, the closure doesn't affect my regular commute using service 265 or other buses stopping at Blk 209. However, knowing that this policy affects nearby stops adds a layer of concern about possible future changes.
  - *grounded in:* `p_1778:f2`

### Lau Mei Lin - `p_0924`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.65 -> 0.65

- **Round 0** - I usually take buses to go to school and work. From my home, I walk to Blk 346 stop (f1). At this stop, service 262 stops for me (f2). But the proposal says they'll close 54241 and 54248, which are nearby but not exactly where I stand. According to my facts, those specific numbered stops aren't part of my routine yet.
  - *grounded in:* `p_0924:f3`, `p_0924:f4`
- **Round 1** - I am a student who usually takes buses to school and work, walking from my home to Blk 346 stop (f1). This stop serves services like 262 that I rely on for getting around, but the policy doesn't affect this directly since none of the closed stops are part of my routine. However, knowing that bus service changes might create congestion or alter routes could indirectly impact how quickly buses arrive at existing stops.
  - *grounded in:* `p_0924:f3`, `p_0924:f1`

### Amirah Tan - `p_0483`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.75 -> 0.75

- **Round 0** - I am a young working professional, aged about 28 and employed with work starting at 8:30 AM every day. Currently, I use bus services to commute since my nearest stop is Opp Mayflower Secondary School at block 579 (not explicitly stated but inferred as nearby). The proposed change involves closing the Ang Mo Kio Ave 3 stops near me, specifically 54241 and 54248. Service 265 would now run non-stop between these two points. I reason that since my nearest stop is Opp Mayflower, which is not one of the closed ones, this might affect other services more directly.
  - *grounded in:* `p_0483:f1`, `p_0483:f2`
- **Round 1** - I heard from p_0089 and p_1941 that the change involves closing stops near them, which might indicate a general improvement in bus services for efficiency or frequency. However, since my nearest stop (Opp Mayflower Sec Sch) is not closed, I'm unaffected by this specific policy change. Service 265 still calls at multiple points including other nearby stops, so while the non-stop route could make it faster between the two closed locations, it doesn't directly impact my morning commute or routine.
  - *grounded in:* `p_0483:f1`, `p_0483:f2`, `p_0483:f6`

### Jason Ang - `p_1941`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.85 -> 0.85

- **Round 0** - I am a young adult, aged between 18 and 34, employed with work starting at 8:00 AM daily. My nearest bus stop is Blk 209 which has multiple services including the frequently used one, service 265 (as per p_1947's f2 but applicable to me too). The proposed policy removes some bus stops along Ang Mo Kio Ave 3 and makes service 265 run non-stop without stopping at those particular points. This might improve the frequency or speed of service 265, which could be beneficial for my morning commute if I use that route.
  - *grounded in:* `p_1941:f1`, `p_1941:f2`
- **Round 1** - I am a young adult, employed and starting work at 08:00 AM daily. The policy removes certain bus stops but does not affect my nearest stop (Blk 209). My usual services include the ones that remain operational, so there should be no significant change for me.
  - *grounded in:* `p_1941:f3`, `p_1941:f6`

### Betty Chew - `p_0024`

*75+, retired, moderate difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I am an elderly resident, aged over 75 and retired, so I don't have a fixed daily work schedule at 8:30 anymore. However, I need to make regular trips to the Ang Mo Kio Community Hospital because it's part of my routine healthcare needs despite having moderate difficulty walking which normally means I wouldn't go beyond about 500 meters for commuting.
  - *grounded in:* `p_0024:f1`, `p_0024:f3`
- **Round 1** - I am an elderly resident, aged over 75 and retired, so I don't have a fixed daily work schedule at 8:30 anymore. However, I need to make regular trips to the Ang Mo Kio Community Hospital because it's part of my routine healthcare needs despite having moderate difficulty walking which normally means I wouldn't go beyond about 500 meters for commuting. The news that bus stop Blk 700B (54241) is being closed affects me indirectly through p_0025, but since it's not my usual route and the hospital trip remains unchanged in terms of access from other stops nearby like Blk 570, I don't see an immediate impact on my travels.
  - *grounded in:* `p_0024:f3`, `p_0024:f9`

### Lau Kim Kiu - `p_0460`

*75+, retired, moderate difficulty walking*

**unaffected**, severity **none**, support 0.20 -> 0.20

- **Round 0** - I normally take the bus from Ang Mo Kio Pr Sch stop which is close to me, about 186 meters away. Service 265 does run via that place so it's convenient for my trips. But I don't use it too regularly because there are other buses at the nearby school stop like 132 and 165. The hospital trip requires using service stops and I normally walk a bit to reach one if necessary, but I have p_0461 who can help me sometimes.
  - *grounded in:* `p_0460:f1`, `p_0460:f2`
- **Round 1** - The policy does not close my nearest stop, Ang Mo Kio Pr Sch (54229), so I still have access to service 265 and other buses that run there. It might affect the frequency or convenience of these services slightly by removing stops on Avenue 3, but since I don't rely heavily on those specific closed stops for my hospital trips—which require a bus stop—I can manage with what's left. The change could potentially reduce wait times for some but doesn't directly impact me as much.
  - *grounded in:* `p_0460:f1`, `p_0460:f2`, `p_0460:f3`, `p_0460:f8`

### Tan Wei Ming - `p_0435`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - Wei Ming is a busy professional, usually catching bus service 265 to go to Ang Mo Kio Primary School which is close by. His home has multiple stops nearby including one he uses for commuting. The hospital trip might be affected if the non-stop route changes things.
  - *grounded in:* `p_0435:f1`, `p_0435:f2`, `p_0435:f3`
- **Round 1** - As the person caring for my elderly household member (fact p_0435:f8), I need to consider how this policy affects her trip to Ang Mo Kio Community Hosp, which is essential and cannot be skipped. Fact p_0352 states that she has mild difficulty walking but would not normally walk more than 800m because the hospital is over 4km away (p_0352:f4). Now, with bus service changes via non-stop routes, I might have to help her adapt or find alternative ways. Fact p_0435:f6 confirms that none of these stops are hers.
  - *grounded in:* `p_0435:f1`, `p_0435:f2`

### Lau Kim Woon - `p_0897`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.65 -> 0.65

- **Round 0** - Kim Woon walks to Blk 561 and uses service 265 for work, starting at 9am. His current setup allows him to reach school easily without a car.
  - *grounded in:* `p_0897:f1`, `p_0897:f2`, `p_0897:f3`
- **Round 1** - I rely on the bus stop at Blk 561 for service 265 to my work location, and walking up to 1200 meters is manageable with my current physical capacity.
  - *grounded in:* `p_0897:f2`, `p_0897:f4`

### Chua Boon Leong - `p_0671`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - My usual bus from home at Blk 700B is only 210 meters, and I start work at 9am so even if buses are faster now maybe it doesn't help much for my commute because I'd still need to catch one before leaving. But I have a car too sometimes when I'm not using public transport anyway.
  - *grounded in:* `p_0671:f2`, `p_0671:f1`

### Nguyen Thi Nga - `p_0729`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - I walk a bit further to get to the main stop, it's about 280 meters from home, but I know service numbers change often so maybe this is just another adjustment for my morning bus routine with work starting at 8:30am.
  - *grounded in:* `p_0729:f1`, `p_0729:f4`

### Madam Ong Shu Lin - `p_0988`

*65-74, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.40 -> 0.40

- **Round 0** - I normally catch the bus from Blk 324 (54248) because it's only 404 meters and my walking is limited - I cannot comfortably walk more than 800 m usually, so going to stop 54241 would be too far for me. With no car in household, the bus service changes are concerning if they affect accessibility.
  - *grounded in:* `p_0988:f1`, `p_0988:f3`, `p_0988:f4`

### Ah Cheong Tan - `p_0989`

*55-64, unemployed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I use the buses because I don't have a car at all, and my nearest stop is Blk 324 (54248) about 391 meters away - not too far for me to handle since I can walk long distances normally. But if service 166 or 165 stops are affected by the change that removes calls at stop 54248, it might impact my travel plans.
  - *grounded in:* `p_0989:f1`, `p_0989:f3`

### Chong Wei - `p_1005`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.30 -> 0.30

- **Round 0** - I usually get off the service 265 at Ang Mo Kio Community Hosp (54248), but now it's closed and I have to walk from home which is about 417m away, that might be a bit much especially if the bus journey itself becomes faster.
  - *grounded in:* `p_1005:f1`, `p_1005:f2`, `p_1005:f3`

### Tan Ah Lian - `p_1627`

*65-74, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.40 -> 0.40

- **Round 0** - The walk to my main stop, Blk 795 (54241), is about 605 m which already feels long for me due to my mild walking difficulties. Service number 138 still stops there but I usually rely on others as well—maybe service 265? But the issue is that bus stop Blk 795 (54241) might be closing because of this new arrangement with service 265 running non-stop between here and somewhere else. Ang Mo Kio Community Hospital is about four kilometers away straight line, too far to walk properly despite my limited mobility.
  - *grounded in:* `p_1627:f3`, `p_1627:f6`

### Chua Kim Leng - `p_1628`

*75+, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.40 -> 0.40

- **Round 0** - I'm pretty okay with not having too much trouble finding out what's going to change, but I do know that my nearest bus stop is Blk 700B (54241), which is about 578 meters from home. Services at this stop are mainly the ones like 130 and a few others for regular travel including shopping trips around Ang Mo Kio Community Hosp, but I can't skip that hospital because of my health issues.
  - *grounded in:* `p_1628:f1`, `p_1628:f2`, `p_1628:f3`

### Lee Boon Teik - `p_0032`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.55 -> 0.55

- **Round 0** - I need to be at work by 7:30 am, so my main transport mode involves getting in a private car from home as nearest stop is Aft Ang Mo Kio Stn Exit A (54261) which is just 160m away. Even though I can walk further than that sometimes for bus convenience, the time crunch means walking isn't always practical.
  - *grounded in:* `p_0032:f1`, `p_0032:f3`

### Chan Kim Wei - `p_0089`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I work starting at 9am so the bus is generally my go-to because I can't use cars too early in morning without delay anyway, and Bef Ang Mo Kio Stn Exit B (stop code 54399) is only about quarter km from place. Since there's no big rush yet by that time, walking around a bit for bus isn't much hassle.
  - *grounded in:* `p_0089:f1`, `p_0089:f3`

### Tan Wei Xuan - `p_1969`

*18-34, unemployed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I usually take the 132 or 165 from my place to get to town but I don't know if that'll change because of this new bus plan. The policy says buses between stops will be faster so maybe it's worth a try? But Opp Ang Mo Kio Pr Sch is only about 243 meters away and there are several services stopping there, including the 169 which goes to my friends' places nearby.
  - *grounded in:* `p_1969:f1`, `p_1969:f2`

### Chua Jing Hui - `p_0622`

*18-34, unemployed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I mostly use the bus to get to classes at NUS but I have my doubts about this new policy. There are so many services stopping at Blk 452 including one called number 652 which is perfect for my commute route sometimes? The distance from home isn't too bad, just about 103 meters walk. Maybe if the bus runs faster it will help me catch fewer buses.
  - *grounded in:* `p_0622:f1`, `p_0622:f2`

### David - `p_1929`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.45 -> 0.45

- **Round 0** - My current stop is Blk 570 (code 54281), which I know from p_1929:f1, about 126 meters away — very convenient for me as I walk without issues up to 1200m. However, the policy change says stops like that near Ang Mo Kio Ave might be closed if they are far apart? Fact p_1929:f4 allows walking much longer than needed here now. But fact p_1929:f3 doesn't specify which services I use — though service 265 is mentioned elsewhere.
  - *grounded in:* `p_1929:f2`, `p_1929:f1`

### Low Wei Jie - `p_1960`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.35 -> 0.35

- **Round 0** - My nearest bus stop is Ang Mo Kio Station Exit A, about 431 meters away from home and work starts at seven in the morning so I usually wait for buses to save on transport costs.
  - *grounded in:* `p_1960:f2`, `p_1960:f3`

### Ng Wei Loong - `p_1968`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.40 -> 0.40

- **Round 0** - I hate waiting for buses because they stop often near Opp Ang Mo Kio Pr Sch, where I live. Service 265 is important to my routine, and it will be faster without those stops.
  - *grounded in:* `p_1968:f2`, `p_1968:f3`

### Grace Tan - `p_1561`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.70 -> 0.70

- **Round 0** - I mainly take the 265 to go to work every day, starting at 08:30 sharp. The nearest stop is Opp Blk 527 (bus stop code 54419), which is just over half a km away and I can handle that walk without any issue. There's no car in my household so I have to stick with buses for commuting, but at least the service number hasn't changed – it's still going by 265. I'm guessing this means less waiting because maybe they're running these buses more frequently or something? But the policy says no extra buses and same budget, so probably just faster speed between stops 54241 and 54248 which aren't near my place anyway – that's over six blocks away. So for me personally, it doesn't affect much but I think this might mean we'll have to walk a bit more if the buses are pulling out passengers from other stops along the route.
  - *grounded in:* `p_1561:f2`, `p_1561:f3`, `p_1561:f4`, `p_1561:f5`

### Daryl Lim - `p_0901`

*75+, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.65 -> 0.65

- **Round 0** - I walk from Opp Yio Chu Kang Station stop to the community hospital most days? No, my nearest bus stop is at home's opposite side Ang Mo Kio Library—414 meters away! That’s about a quarter kilometer so I can easily manage that every morning before work. But now buses won’t stop there anymore for service 265 running directly from one point to another bypassing those stations between here and the hospital? Let me confirm what stops are being closed: wait, it says close bus stops along Ang Mo Kio Ave, maybe affecting my usual route because right now I use services that call at that station like number 851 or whatever. But I don't know much about the changes yet—my doctor just called and said no change for me today.
  - *grounded in:* `p_0901:f1`, `p_0901:f2`

### Robert Lim - `p_1252`

*75+, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.90 -> 0.90

- **Round 0** - If bus service along this route is altered and some stops are closed—like the ones mentioned—but my main trip to hospital requires specific routes, maybe walking distances would increase? Or perhaps I can rely more on public transport as long as it’s accessible with help from family members like p_1253 living here. But right now my nearest stop is at Ang Mo Kio Library side—400 meters walk away! That’s manageable even for me without any issues because I’m okay walking up to 1,200 meters in a straight line if needed.
  - *grounded in:* `p_1252:f1`, `p_1252:f6`

### Wong Siew Keat - `p_0849`

*65-74, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.30 -> 0.30

- **Round 0** - They're saying they're going to close two bus stops near me and have the 265 service go straight without stopping. Right now, my nearest stop is Blk 307A at 462 meters away, which I can walk just fine since I'm still working up till 8am every day. For the hospital trip that happens regularly to Ang Mo Kio Community Hospital – it's over five thousand straight line meters from home and too far for me or my walker. The affected stops might mean less bus routes coming by Blk 307A, since services like 13 and 265 normally stop there. I use multiple buses including 13, but with the changes it could impact how often they come around.
  - *grounded in:* `p_0849:f1`, `p_0849:f2`, `p_0849:f3`, `p_0849:f4`

### Wong Mei Hua - `p_0900`

*65-74, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I normally walk to Opp Yio Chu Kang Stn bus stop, which is about 170 meters away, because the service numbers like 45 and 668 are convenient for me when I need to go out. But now if those stops on Ave 3 are closed, I might have to walk a lot further or even more than my usual limit of 800 meters just to catch one bus that goes through there.
  - *grounded in:* `p_0900:f1`, `p_0900:f2`

### Hwee Siew Kiong - `p_1329`

*65-74, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I've heard buses might be faster, but I don't know how it affects me directly because I use the nearby Bef Ang Mo Kio Lib stop regularly.
  - *grounded in:* `p_1329:f1`, `p_1329:f5`

### Tham Kim Poh - `p_0267`

*55-64, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I haven't heard much about this specific change, though I know the trips to Ang Mo Kio Community Hosp are a concern for my elderly companion.
  - *grounded in:* `p_0267:f3`, `p_0267:f4`

### Nguyen Thi Phuong - `p_0839`

*55-64, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - The announcement about faster buses is confusing, especially since my household doesn't have a car and I use Blk 307A.
  - *grounded in:* `p_0839:f1`, `p_0839:f4`

### Ong Kim Leng - `p_0814`

*55-64, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.60

- **Round 0** - I usually use the AMK Ave 3 stop for service 265, which is crucial for my morning commute to work starting at 8:30 am. The proposed change means buses will skip stops that I used in the past, making it less convenient if not impossible without adjusting my route.
  - *grounded in:* `p_0814:f1`, `p_0814:f2`, `p_0814:f3`

### Ng Swee Kiat - `p_1227`

*55-64, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I'm an early riser, starting work at 7 am, and rely heavily on service 138 to Blk 649 stop for my commute. The plan to have buses skip certain stops could make it harder if I need to walk farther or wait longer.
  - *grounded in:* `p_1227:f1`, `p_1227:f2`, `p_1227:f3`

### Lim Hock Seng - `p_1796`

*55-64, unemployed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.50

- **Round 0** - I don't have a fixed commute since I'm not working, but my home is near Opp Courts AMK stop which services many buses including 138. The change to service 265 skipping stops might not directly affect me unless it changes the timing or frequency of those buses.
  - *grounded in:* `p_1796:f1`, `p_1796:f2`

### Tan Wei Ming - `p_0635`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.70 -> 0.70

- **Round 0** - The news about closing bus stops on Ang Mo Kio Ave 3 caught my attention because I go to work via bus and Blk 542 is nearby, though a bit far from home. Service number 265 might be faster without stopping at those two points if they are close together, but since the stop between my home and school is still operating, it's probably not too bad for me as long as I use what works.
  - *grounded in:* `p_0635:f1`, `p_0635:f2`

### Tan Wei Xin - `p_1357`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.68 -> 0.68

- **Round 0** - I live near Blk 586 with a walk of 544 meters (p_1357:f1). Services stopping here include 261 and 268A besides the ones I know about from home facts (p_1357:f2) but not service 265. Since my facts say services calling at Blk 586 do not include 265, and the policy mentions two other stops closed by 265 on a specific route, this doesn't directly impact me unless I change habits.
  - *grounded in:* `p_1357:f2`, `p_1357:f4`

### Chen Siyi - `p_1511`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.72 -> 0.72

- **Round 0** - I'm a student living opposite Ang Mo Kio Primary School (p_1511:f1). This stop is served by services 132 and others besides the ones listed in my home facts but not service 265 yet (from p_1511:f2 it shows other routes including 265 stopping here, so I should take that too? But wait no—service 265 does call at Opp Ang Mo Kio Pr Sch per p_1511:f2. And according to the policy, they're closing stops on a specific route operated by service 265 between two points.
  - *grounded in:* `p_1511:f3`, `p_1511:f4`

### Chua Li Mui - `p_0728`

*75+, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.30 -> 0.30

- **Round 0** - I usually walk to the Ang Mo Kio Pr Sch bus stop which is only 465 meters away, and I can handle that quite well at my age. Service 265 does come here so it's a normal part of my routine for the hospital trip even though there are other options like walking directly sometimes shorter distances. Having to walk from Opp Blk 527 would be tough for me as it's not within my range anyway, but I don't need to worry about that yet.
  - *grounded in:* `p_0728:f1`

### Chan Ah Fook - `p_0770`

*75+, retired, moderate difficulty walking*

**unaffected**, severity **none**, support 0.20 -> 0.20

- **Round 0** - The Opp Blk 527 bus stop is only a short walk away, less than half a kilometer from home, so it's quite convenient to use for buses like service 265 that I take regularly. But the distance to Ang Mo Kio Community Hosp would be very difficult without this stop if we couldn't find another nearby one within walking range, though my difficulty isn't severe and there might be alternative transport options.
  - *grounded in:* `p_0770:f1`

### Chua Ai Lin - `p_1555`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.67 -> 0.67

- **Round 0** - Ai Lin uses bus services to go to Ang Mo Kio Community Hospital, but she relies on other stops that still have buses coming through.
  - *grounded in:* `p_1555:f1`, `p_1555:f2`

### Marcus Koh - `p_1947`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.55 -> 0.58

- **Round 0** - I am a young adult, aged between 18 and 34, employed with work starting at the usual time (probably around 7:50 to 8:20). I walk without difficulty up to about 1200 meters, which is standard for commuting. My nearest bus stop is Blk 322 (54247), located 175 meters from home, and it has services like 138, 169, etc., but not the ones being closed directly affecting my immediate route unless I'm going far away elsewhere.
  - *grounded in:* `p_1947:f1`
- **Round 1** - I am a young adult, employed and starting work at 08:00 AM daily. My nearest bus stop (Blk 322) is unaffected by the policy changes mentioned here. However, I need to consider if there are other indirect effects or if my walking distance might be affected in future policies.
  - *grounded in:* `p_1947:f3`, `p_1947:f6`

### Low Ean Keow - `p_1666`

*65-74, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.20 -> 0.25

- **Round 0** - I rely on the bus to Ang Mo Kio Community Hosp every week, and my nearest stop is Blk 700B at around six hundred meters away, which I can manage with some mild walking issues. But if that stop is closed for buses like service number 265 running non-stop between two points, then I might have to walk or use the car more often because I don't think I'd want to travel longer distances on foot.
  - *grounded in:* `p_1666:f3`, `p_1666:f4`
- **Round 1** - The closure of Blk 700B bus stop impacts my daily commute to Ang Mo Kio Community Hospital significantly. Now I must walk a longer distance, up to 800 meters which is beyond my walking capabilities due to mild difficulty. Using the car means extra trips for parking and fuel costs, so this change affects me directly.
  - *moved by:* `p_1665`
  - *grounded in:* `p_1666:f3`, `p_1666:f4`, `p_1666:f5`
- **Round 2** - The nearest stop Blk 700B is closing and my hospital trip must now start from Opp Al-Muttaqin Mque which is +497m away, exceeding my walking limit of +436m as I have mild difficulty walking beyond that. Previously I could use the car for this route with minimal concern about parking or fuel due to household having a car; now these factors might increase because the stop closure forces longer walks requiring more time.
  - *grounded in:* `p_1666:f8`, `p_1666:f9`
- **Round 3** - My daily hospital trip, which I cannot skip, now requires a longer walk from Opp Al-Muttaqin Mque (+497m compared to before). As someone with mild difficulty walking beyond +800m, this exceeds my limit and forces me to reconsider the use of household car services more often than previously.
  - *grounded in:* `p_1666:f3`, `p_1666:f4`, `p_1666:f5`, `p_1666:f8`

### Yeo Jia Min - `p_1008`

*<18, student, no difficulty walking*

**giving_up**, severity **high**, support 0.40 -> 0.45

- **Round 0** - I don't have a car and I usually walk to the nearest stop, but if they're making buses faster between here and Ang Mo Kio Community Hosp (54248), maybe that could help me sometimes.
  - *grounded in:* `p_1008:f1`, `p_1008:f3`
- **Round 1** - The policy removes the bus stops I usually use and requires me to walk home or take a slightly longer route if necessary. This change affects my convenience because while buses might be faster due to running non-stop between Ang Mo Kio Community Hosp (54248) and Blk 700B, it introduces additional walking distance and time which is inconvenient for a student like me.
  - *grounded in:* `p_1008:f3`, `p_1008:f4`, `p_1008:f6`, `p_1008:f7`
- **Round 2** - The closure of Blk 324 means I must now use a farther stop, increasing my walking time and discomfort as a student who values efficiency. Since multiple residents are affected similarly, this change directly impacts me more than initially thought.
  - *changed because:* Direct impact on my own routine due to the bus stop closing.
  - *grounded in:* `p_1008:f1`, `p_1008:f2`, `p_1008:f3`, `p_1008:f4`, `p_1008:f5`, `p_1008:f6`, `p_1008:f7`, `p_1008:f8`

### Ling Kim Seng - `p_0813`

*65-74, employed, moderate difficulty walking*

**unaffected**, severity **none**, support 0.20 -> 0.25

- **Round 0** - I'm in my late sixties, still working at the Community Hospital nearby – it's just about 5044m away which is too far to walk even for me, given I only like walking up to about half a km normally due to moderate difficulty. My nearest bus stop is Blk 307A (54019), easily reachable from home at 265 m without much trouble – and buses calling there include the ones needed for work or other things. Since my hospital trip must be done via bus, the idea of closing specific stops on Ang Mo Kio Ave 3 might mean I have to walk a lot more if they're not connected properly.
  - *grounded in:* `p_0813:f1`, `p_0813:f2`
- **Round 1** - The policy directly affects my regular trips to Ang Mo Kio Community Hospital, which I cannot skip. My nearest bus stop was Blk 700B (now closed) and the next is Opp Al-Muttaqin Mque – both too far for a walk. This means I might have to take multiple buses or longer routes, but since my household doesn't have a car, walking isn't feasible.
  - *grounded in:* `p_0813:f2`, `p_0813:f3`
- **Round 3** - The policy closes Blk 700B and Opp Al-Muttaqin Mque, both of which are too far for my walking ability given the increased distance to these stops compared with my usual walks or bus rides. I must now consider driving if possible despite not having a car, but this might be difficult.
  - *grounded in:* `p_0813:f4`, `p_0813:f6`

### Tan Mei Ling - `p_1006`

*35-54, employed, no difficulty walking*

**adapting**, severity **moderate**, support 0.20 -> 0.25

- **Round 0** - I don't have a car so I rely on buses to get anywhere, but now they're closing the stops near my place and service 165/166 are stopping at Ang Mo Kio Community Hosp which is a bit further than usual.
  - *grounded in:* `p_1006:f2`, `p_1006:f3`
- **Round 3** - The policy directly closes the bus stop I rely on, forcing me to walk farther or use substitute services that are still available but may not be as convenient.
  - *grounded in:* `p_1006:f3`, `p_1006:f4`, `p_1006:f5`, `p_1006:f7`

### Rajiv Tan - `p_0846`

*35-54, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.70 -> 0.75

- **Round 0** - I usually catch bus from Blk 700B stop, but the proposed change says service 265 will not call there anymore and run directly without stopping between stops 54241 and 54248. Since I walk to work every day starting at 08:00, this might mean longer wait times if buses skip my usual stop. But since I have a car in the household sometimes it's faster anyway.
  - *grounded in:* `p_0846:f1`, `p_0846:f2`, `p_0846:f3`
- **Round 3** - The policy closes my normal bus stop and introduces a longer walk to reach Opp Al-Muttaqin Mque, which is +27m compared with now, so I will have to adapt by walking further or changing when I start work at 8:00 if driving isn't an option. Since I am usually at the stop early enough that buses might not skip my block frequently, this could still be manageable.
  - *grounded in:* `p_0846:f1`, `p_0846:f7`

### Bryan - `p_1910`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.35 -> 0.40

- **Round 0** - I find that walking from Blk 561 (stop code 54429, only 165 meters away) is very easy as per p_1910:f4. But now service 265 would run non-stop between some points including the stop I might be forced to use? Fact p_1910:f2 says services calling at Blk 561 are just 265, so if it's closed or altered from there, that's a big issue. The nearest stop mentioned in fact p_1910:f1 is the same location I walk to.
  - *grounded in:* `p_1910:f2`, `p_1910:f1`
- **Round 1** - As an employed individual who starts work at 07:00 (fact p_1910:f3), the closure of nearby stops might indirectly impact my routine if I need to travel farther for buses that stop near my workplace or home. Fact p_1910:f2 confirms that only service 265 calls at Blk 561, so its alteration could affect me significantly by forcing longer walks.
  - *grounded in:* `p_1910:f3`, `p_1910:f6`

### Leong Lai Keat - `p_1486`

*65-74, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.70 -> 0.75

- **Round 0** - I use services like 269 or 860 that call at Blk 649, about 315 meters from home. If I can catch service number 265 without walking to the main stops on Ang Mo Kio Ave 3, then this might actually save me time in getting around.
  - *grounded in:* `p_1486:f1`, `p_1486:f2`
- **Round 1** - Hearing from p_0665 that service changes like this don't always consider individual needs has made me more cautious. The policy might speed up travel between stops but since my nearest stop is far beyond the recommended walk limit, it could mean longer waits or less frequent buses overall, which doesn't help even if 265 improves elsewhere.
  - *moved by:* `p_0665`
  - *grounded in:* `p_1486:f3`, `p_1486:f7`

### David Tan - `p_1707`

*35-54, unemployed, no difficulty walking*

**unaffected**, severity **none**, support 0.50 -> 0.59

- **Round 0** - I heard that the buses will be faster now between two stops, but I don't know which ones exactly. My nearest stop is Blk 564 with services like 132 and 268 going there regularly. The policy might affect nearby stops though? Not sure yet.
  - *grounded in:* `p_1707:f3`
- **Round 1** - I heard that buses between stops will run non-stop, but I don't need to use the closed stops anyway. The policy doesn't directly affect me since my nearest stop (Blk 564) remains open and unchanged.
  - *grounded in:* `p_1707:f3`

### Angeline Tan - `p_0945`

*18-34, employed, no difficulty walking*

**unaffected**, severity **none**, support 0.70 -> 0.80

- **Round 0** - I heard buses might be faster if they skip stops. My main stop is Blk 570, which has several services like 132 and 261. If I can't use those, I'll have to walk or find another option. Walking up to 1200 meters isn't too bad for me as a young working person who walks everywhere before catching the bus anyway.
  - *grounded in:* `p_0945:f3`, `p_0945:f2`
- **Round 1** - Having to walk extra might affect my morning routine because I usually leave home early for work. But the faster buses could mean arriving quicker if they are more frequent or don't stop as often.
  - *grounded in:* `p_0945:f3`, `p_0945:f2`
- **Round 2** - I've considered using the nearby shops for a few minutes to see if it's worth the walk. It adds time but might be okay compared to waiting longer.
  - *grounded in:* `p_0945:f3`, `p_0945:f2`
- **Round 3** - I think the change is fine if it means less stops and maybe more comfortable rides. Some people might prefer other routes now that stop 54241 is gone.
  - *grounded in:* `p_0945:f3`, `p_0945:f2`
- **Round 1** - I am an employed resident who relies on buses for my daily commute, normally catching service 268 from Blk 570 (f1). This policy removes nearby stops but doesn't directly affect me yet as none of the closed stops are part of my regular trips. However, changes in bus frequency or route efficiency might indirectly impact wait times and reliability if I need to adapt.
  - *grounded in:* `p_0945:f1`, `p_0945:f2`

### Phyllis Koh - `p_0281`

*75+, retired, severe difficulty walking*

**unaffected**, severity **none**, support 0.55 -> 0.70

- **Round 0** - I get around just fine without walking much, but the news about closing bus stops along this route—like stop numbers mentioned—might affect my trip to hospital if it forces me further? Or maybe I’ll need to walk more now because service is skipping those stations entirely between my current spot and hospital. But right now from home near Ang Mo Kio Library side, nearest stop is at Opp Yio Chu Kang Station which is 875 meters away in a straight line—that’s about three blocks! However since I can only handle up to 250 meters normally without assistance or rest due to my poor mobility—oh yes severe difficulty walking so even getting there feels like climbing a mountain.
  - *grounded in:* `p_0281:f1`, `p_0281:f4`
- **Round 1** - The policy directly affects my ability to walk only up to 250 meters, so I must now find alternative ways to reach bus stops if the closed ones impact essential trips like to the community hospital.
  - *grounded in:* `p_0281:f1`, `p_0281:f3`, `p_0281:f4`, `p_0281:f5`

### Alex Soh - `p_0648`

*<18, student, no difficulty walking*

**unaffected**, severity **none**, support 0.20 -> 0.35

- **Round 0** - Yeah, they're closing some bus stops on Ang Mo Kio Ave? But I usually just walk to Blk 586 anyway, and services there like 132 still work fine for the whole route even if stop 542 isn't used anymore. Since school's my main thing and buses are okay without extra effort walking, maybe it won't matter much.
  - *grounded in:* `p_0648:f1`, `p_0648:f2`
- **Round 1** - The policy closes stops I don't use, and my nearest stop is unaffected so no change.
  - *grounded in:* `p_0648:f1`, `p_0648:f3`

### Tan Wei Ming - `p_0786`

*35-54, employed, mild difficulty walking*

**adapting**, severity **none**, support 0.30 -> 0.45

- **Round 0** - I rely heavily on the Blk 700B (54241) bus stop because it's only 106 meters from my home, and I have mild difficulty walking so I wouldn't be able to handle a longer walk to another stop like they're suggesting. The closure of stops 54241 and 54248 might force me to take service 138M or one of the others that do call here, but those are not my usual buses and I'm worried about travel time if there's no direct connection.
  - *grounded in:* `p_0786:f1`, `p_0786:f2`
- **Round 1** - After hearing from p_0787 and p_0788 about their experiences with the bus routes, including potential savings if walking further becomes necessary because of non-stop service, I'm reconsidering that losing easy access might lead to longer waiting times or more inconvenient travel.
  - *grounded in:* `p_0786:f1`, `p_0786:f6`

### Ng Wee Keat - `p_1756`

*75+, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.30 -> 0.50

- **Round 0** - I use the bus to Ang Mo Kio Community Hosp regularly, so if Blk 700B is closed and buses go straight without stopping, I'd have to walk the distance which is quite far—my nearest stop is around three hundred meters away but services at that spot are limited.
  - *grounded in:* `p_1756:f3`, `p_1756:f4`
- **Round 2** - The closure of Blk 700B stop near my home has affected how I get to the hospital via buses, especially since service 265 will run non-stop now. Opp Al-Muttaqin Mque is +338m away but it's still within my walking limit and allows me to continue using existing bus services; however, this policy forces a longer walk than usual for commuting purposes despite household having car.
  - *grounded in:* `p_1756:f8`, `p_1756:f9`
- **Round 3** - The closure of my nearest bus stop means I now have to walk a bit further for the hospital trip, from +257m instead of less than that. This change might affect future routine healthcare visits as it adds time and effort.
  - *grounded in:* `p_1756:f8`, `p_1756:f9`

### Nguyen Thanh Nam - `p_1494`

*18-34, employed, mild difficulty walking*

**adapting**, severity **moderate**, support 0.50 -> 0.82

- **Round 0** - My work starts at 7am and there's only one bus service stopping near me here – the number 265 itself actually! Blk 561 is quite far from home too, about 232 meters walk which I can manage sometimes but it would be tough if we close stops. Plus my mild walking problem means longer walks are harder anyway even though this particular stop isn't too bad at just that distance.
  - *grounded in:* `p_1494:f1`, `p_1494:f3`
- **Round 1** - Learning from p_0120 and the change in service pattern for others, I realize that while my own situation hasn't changed dramatically yet (still able to reach stop easily), this policy might mean longer walks or reduced bus services elsewhere causing ripple effects on efficiency.
  - *moved by:* `p_0120`
  - *grounded in:* `p_1494:f3`, `p_1494:f7`
- **Round 3** - While the policy doesn't directly impact my nearest stop, I've learned from p_0666 that other residents might be forced to walk longer distances due to closed stops. This could affect overall bus usage in the area, potentially leading to longer walks for me if service 265 becomes more efficient but others' routes are disrupted.
  - *grounded in:* `p_1494:f3`, `p_1494:f7`

### Chan Eng Seng - `p_1033`

*65-74, retired, no difficulty walking*

**unaffected**, severity **none**, support 0.60 -> 0.92

- **Round 0** - I am used to taking the bus from Blk 207, which is about 344 meters away. Service number 13 or 851 comes every day. Now they are removing stops 54241 and 54248 on Ang Mo Kio Ave 3. The new service 265 will run non-stop between them, which means I have to go further to the main route bus stop for other buses or use a different service if available. From my facts, services calling at Blk 207 include several numbers including those that might be affected by this change.
  - *grounded in:* `p_1033:f1`, `p_1033:f2`
- **Round 1** - I am retired but still walk easily to my nearest stop, Blk 207 (which is at least several hundred meters away). The policy does not directly affect my current route because I'm already past the affected stops. However, if other residents are mentioning longer walks or reduced service options due to closed stops like 54241 and 54248, it might be part of a larger adjustment that could eventually influence accessibility for me too.
  - *grounded in:* `p_1033:f7`, `p_1033:f6`

### Ah Kow - `p_0580`

*75+, retired, moderate difficulty walking*

**unaffected**, severity **none**, support 0.30 -> 0.70

- **Round 0** - I'm 75, retired, and have trouble walking a lot more than usual people. My nearest bus stop is Yio Chu Kang Stn (55189), just about 136 m from home. I need to get to Ang Mo Kio Community Hosp regularly because it's my thing – can't skip that trip for health reasons, and while the straight line says 949m which is way too far to walk even with a helper, but mostly I use buses. Right now, without more info, the idea of closing stops on my route sounds bad.
  - *grounded in:* `p_0580:f1`, `p_0580:f2`
- **Round 1** - The policy does not affect my nearest bus stop or the hospital trip I rely on, so nothing has changed for me regarding this specific route.
  - *grounded in:* `p_0580:f1`, `p_0580:f3`
- **Round 2** - The policy directly impacts residents with mobility issues like p_0665 who rely on easily accessible stops for their hospital trips despite the inconvenience of walking, and it forces them to walk further even if my own nearest stop remains unaffected.
  - *changed because:* Neighbours' experiences reinforce how this change affects accessibility for vulnerable groups.
  - *grounded in:* `p_0580:f1`, `p_0580:f7`
- **Round 3** - The policy directly affects residents with moderate walking difficulty, forcing them to walk further for essential trips like mine to Ang Mo Kio Community Hosp. This change could impact many elderly individuals who rely on nearby stops due to the hospital's distance and lack of car options.
  - *grounded in:* `p_0580:f1`, `p_0580:f3`

### Tan Ah Lek - `p_0352`

*75+, retired, mild difficulty walking*

**unaffected**, severity **none**, support 0.10 -> 0.60

- **Round 0** - I normally walk to the Blk 422 bus stop, which is a good portion of my day. But for now, I don't use service 265 often since it's just one trip that I must take every week or so. The change means I might have to drive more as we don't have a car at home, but the nearest stop Blk 422 is still within reach given my mobility. However, if service 135 doesn't come by frequently enough for this particular route then it could become quite inconvenient.
  - *grounded in:* `p_0352:f7`
- **Round 1** - This policy directly impacts my ability to get to the hospital because I rely on buses, and Ang Mo Kio Community Hosp is too far for me (fact p_0352:f4). Fact p_0352:f8 states that service 265 will run non-stop between Blk 700B and other stops, but my nearest stop is still at Blk 422 (p_0352:f1), which I use to walk there with some mild difficulty. The policy doesn't require me to change my routine because the closing of service 265 does not affect how far away the hospital is; it's just over 5,598m in a straight line (p_0352:f4). Fact p_0352:f7 says none of these stops are mine, so I'm primarily concerned about using buses for this essential trip.
  - *grounded in:* `p_0352:f1`, `p_0352:f2`, `p_0352:f3`

### Tan Mei Lin - `p_1047`

*65-74, retired, mild difficulty walking*

**adapting**, severity **moderate**, support 0.20 -> 0.85

- **Round 0** - I'm retired and used to relying on the bus at Blk 324 (nearest is about 437 meters). I can only walk up to 800 meters normally, so even though buses are slower now with service 265 running non-stop between there and Blk 700B—wait no, that's not relevant. Actually, my concern is that if the hospital trip requires a different stop or route because of this change? But from facts, it's still listed at services calling here: 130, 132 etc., so I think they are keeping the necessary routes for stops like these—perhaps this measure doesn't directly impact me since Blk 324 is close enough to walk and has multiple buses.
  - *grounded in:* `p_1047:f1`, `p_1047:f2`
- **Round 1** - Due to my mild difficulty walking beyond about 800 meters, I cannot directly walk home from the new nearest stop Blk 322 (about +631m compared to the old one). This change affects me more because the bus stop at Blk 324 is no longer available. My household has a car, but using it means extra trips or coordination with others for my elderly relatives who might have difficulty.
  - *grounded in:* `p_1047:f8`, `p_1047:f6`
- **Round 2** - The policy closes my nearest bus stop, Blk 324 (54248), which I previously used for its services including those that take me to Ang Mo Kio Community Hospital. Now, due to my mild difficulty walking and age, I must walk further or use the car more often, coordinating with elderly household members who also rely on accessible transit.
  - *changed because:* Because p_1046 mentioned their elderly relatives needing help with longer bus walks due to the same policy.
  - *moved by:* `p_1046`
  - *grounded in:* `p_1047:f3`, `p_1047:f6`, `p_1047:f7`
- **Round 3** - The policy directly closes my nearest bus stop, Blk 324 (54248), which I previously used for essential trips to Ang Mo Kio Community Hospital. Now, with mild difficulty walking and age factors, I must either walk further or rely more on the car, but since I have a household car available, this might be manageable without significant hardship.
  - *changed because:* The policy closing my stop directly affects me, and I've heard from p_1046 that similar changes can impact household coordination.
  - *grounded in:* `p_1047:f3`, `p_1047:f6`
