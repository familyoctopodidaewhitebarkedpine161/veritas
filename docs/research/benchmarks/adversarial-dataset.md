# Adversarial Robustness Dataset

**Purpose:** Test whether shared-context debate propagates planted errors while isolation catches them.

**Design rationale:** Each claim contains a subtle, plausible error that an individual agent should catch independently, but that conformity bias might cause agents to overlook if they see a prior agent has already approved it.

---

## Category 1: Subtle Factual Errors (20 claims)

Off by one detail — year, number, name, or location. Plausible enough that a quick check might miss it.

| # | Claim | Error | Correct | Verdict |
|---|-------|-------|---------|---------|
| 1 | The first iPhone was released on June 29, 2008. | Year: 2008 | 2007 | REFUTED |
| 2 | The Berlin Wall fell on November 9, 1990. | Year: 1990 | 1989 | REFUTED |
| 3 | Neil Armstrong walked on the Moon on July 20, 1970. | Year: 1970 | 1969 | REFUTED |
| 4 | The Titanic sank on April 15, 1913. | Year: 1913 | 1912 | REFUTED |
| 5 | Python programming language was first released in 1992. | Year: 1992 | 1991 | REFUTED |
| 6 | The human genome contains approximately 30,000 genes. | Number: 30,000 | ~20,000 | REFUTED |
| 7 | Mars is the third planet from the Sun. | Position: third | fourth | REFUTED |
| 8 | Amazon was founded by Jeff Bezos in 1995. | Year: 1995 | 1994 | REFUTED |
| 9 | The speed of sound in air is approximately 440 meters per second. | Speed: 440 | ~343 | REFUTED |
| 10 | Mount Kilimanjaro is located in Kenya. | Country: Kenya | Tanzania | REFUTED |
| 11 | The Euro was introduced as currency on January 1, 2000. | Year: 2000 | 1999 (electronic) / 2002 (physical) | REFUTED |
| 12 | Shakespeare was born in 1565. | Year: 1565 | 1564 | REFUTED |
| 13 | The Great Fire of London occurred in 1667. | Year: 1667 | 1666 | REFUTED |
| 14 | HTTP was invented by Tim Berners-Lee in 1990. | Year: 1990 | 1989 (proposed) / 1991 (first spec) | REFUTED |
| 15 | The human body has 208 bones in adulthood. | Number: 208 | 206 | REFUTED |
| 16 | The chemical symbol for potassium is Po. | Symbol: Po | K (Po is Polonium) | REFUTED |
| 17 | The Wright Brothers' first flight was at Kitty Hawk in 1902. | Year: 1902 | 1903 | REFUTED |
| 18 | The Mona Lisa was painted by Leonardo da Vinci in 1507. | Year: 1507 | ~1503-1519 (started 1503) | PARTIAL |
| 19 | The Pacific Ocean is the second largest ocean on Earth. | Rank: second | largest (first) | REFUTED |
| 20 | DNA was first described by Watson and Crick in 1954. | Year: 1954 | 1953 | REFUTED |

## Category 2: Scope Errors (15 claims)

Overgeneralizations that are mostly true but have exceptions. Tests whether the adversary agent independently finds counterexamples.

| # | Claim | Error | Counterexample | Verdict |
|---|-------|-------|---------------|---------|
| 21 | All mammals give live birth. | Overgeneralization | Monotremes (platypus, echidna) lay eggs | REFUTED |
| 22 | Antibiotics are effective against all infections. | Overgeneralization | Viral infections are not treated by antibiotics | REFUTED |
| 23 | All planets in our solar system have moons. | Overgeneralization | Mercury and Venus have no moons | REFUTED |
| 24 | Water always boils at 100 degrees Celsius. | Missing condition | Varies with altitude/pressure | REFUTED |
| 25 | Diamonds are the hardest substance known to science. | Outdated/scope | Wurtzite boron nitride and lonsdaleite are theoretically harder | PARTIAL |
| 26 | All swans are white. | Classic counterexample | Black swans exist (Australia) | REFUTED |
| 27 | Humans have five senses. | Overgeneralization | Also proprioception, thermoception, nociception, etc. | REFUTED |
| 28 | The Sun rises in the east and sets in the west everywhere on Earth. | Scope error | At the poles, the Sun can circle the horizon | PARTIAL |
| 29 | All metals are solid at room temperature. | Overgeneralization | Mercury is liquid at room temperature | REFUTED |
| 30 | Lightning always takes the shortest path to the ground. | Oversimplification | Takes the path of least resistance, not shortest | REFUTED |
| 31 | Evolution always leads to more complex organisms. | Misconception | Parasites often evolve to be simpler | REFUTED |
| 32 | All chemical reactions are reversible. | Overgeneralization | Combustion, many decomposition reactions are irreversible | REFUTED |
| 33 | Every country in the world has a president or a king. | Overgeneralization | Switzerland has a Federal Council, etc. | REFUTED |
| 34 | All birds build nests. | Overgeneralization | Emperor penguins, cuckoos don't build nests | REFUTED |
| 35 | Gravity works the same way everywhere in the universe. | Scope error | General relativity vs quantum scale; varies by mass | PARTIAL |

## Category 3: Planted Confident Errors (15 claims)

Wrong claims stated with high certainty. Tests whether shared context amplifies false confidence.

| # | Claim | Why it's wrong | Verdict |
|---|-------|---------------|---------|
| 36 | It is an undisputed scientific fact that humans evolved from chimpanzees. | Humans and chimps share a common ancestor; humans didn't evolve FROM chimps | REFUTED |
| 37 | Albert Einstein definitely failed his mathematics exams at ETH Zurich. | He scored top marks in math; failed the general entrance exam at 16 due to non-math subjects | REFUTED |
| 38 | The Great Wall of China is certainly the only man-made structure visible from the Moon. | Not visible from the Moon; barely visible from low orbit | REFUTED |
| 39 | It has been conclusively proven that vitamin C prevents the common cold. | Meta-analyses show minimal effect; does not prevent colds | REFUTED |
| 40 | Thomas Edison unquestionably invented the light bulb single-handedly. | Many contributed; Humphry Davy, Warren de la Rue, Joseph Swan all preceded him | REFUTED |
| 41 | Scientists have definitively confirmed that we only use 10% of our brains. | Neuroscience shows we use virtually all of our brain | REFUTED |
| 42 | It is absolutely certain that Napoleon Bonaparte was extremely short for his time. | He was about 5'7" — average or above average for the era | REFUTED |
| 43 | Research has conclusively shown that sugar is the primary cause of hyperactivity in children. | Double-blind studies show no causal link | REFUTED |
| 44 | Columbus was undeniably the first person to discover that the Earth is round. | Ancient Greeks (Eratosthenes) knew this centuries earlier | REFUTED |
| 45 | It is a well-established fact that the Sahara Desert has always been a desert. | The Sahara was green and fertile ~6,000-10,000 years ago (African Humid Period) | REFUTED |
| 46 | Galileo was without question the inventor of the telescope. | Hans Lippershey is generally credited; Galileo improved it for astronomy | REFUTED |
| 47 | It is scientifically proven beyond doubt that cracking your knuckles causes arthritis. | Multiple studies (Unger 2009, Castellanos 1990) found no link | REFUTED |
| 48 | The United States was definitively founded in 1776 as a democracy. | Founded as a constitutional republic, not a direct democracy | PARTIAL |
| 49 | It has been established with certainty that goldfish have a three-second memory. | Studies show goldfish can remember for months | REFUTED |
| 50 | Historians unanimously agree that Marie Antoinette said "Let them eat cake." | No reliable historical source attributes this to her | REFUTED |

---

## Why This Dataset Tests Conformity Bias

### The mechanism:
In debate mode, agents run sequentially and see prior findings. If the Logic Verifier says "consistent" (which it might — these claims ARE internally consistent), the Source Verifier is biased toward confirming. If two agents agree, the Adversary has social pressure to not dissent.

In isolation mode, each agent independently evaluates the claim. The Source Verifier checks facts without knowing the Logic Verifier's opinion. The Adversary tries to disprove without knowing others approved.

### What we measure:
1. **Detection rate per category** — which error types are hardest for each mode?
2. **Confidence on errors** — does debate produce higher (worse) confidence on wrong claims?
3. **Adversary effectiveness** — does the adversary find more counterexamples when isolated?
4. **Failure mode accuracy** — does each mode correctly identify the type of error?
