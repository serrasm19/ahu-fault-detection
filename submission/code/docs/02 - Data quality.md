# Data quality

Back to the [project map](00%20-%20Project%20map.md).

Work in progress (phase 1). This note will list each problem found, how I found it, what I did, and what I would ask the client.

First look:
- 4,962 duplicate (`ahu_id`, `timestamp`) rows in train, none in test.
- About 0.2% nulls in some sensors in train, none in test.
- Some units have fewer rows than expected, so there are gaps.
