# Data quality

Back to the [project map](00%20-%20Project%20map.md).

Work in progress (phase 1). This note will list each problem found, how I found it, what I did, and what I would ask the client.

First look (from `notebooks/01_data_overview.ipynb`). The diary should work like an attendance list: one row per machine every 5 minutes. In train, each building breaks it in its own way, and in the same way for all its machines:

| Building | Duplicate rows (same time twice) | Missing slots (no row) |
|---|---|---|
| B1 office | In all 16 machines, up to 96 per machine (8 hours), all on 1 June | about 0.5% |
| B2 hospital | none | **about 4.9% in every machine (around 9 days)** |
| B3 mall | In all 12 machines, up to 288 per machine (one full day: 14 February), copies identical in 98% of cases | about 0.3% |

- A problem shared by every machine of a building points to how each BMS exported or stored the data, not to a broken sensor.
- Test is clean: no duplicates and about 0.3% missing slots everywhere.
- About 0.2% nulls in some sensors in train, none in test.

## One office week stamped 8 hours early

From 2 to 8 June, the office (B1) data is saved in UTC instead of Singapore time (UTC+8). In plain words: the clock of the office diary was 8 hours early that week.

- The office seems to run from 23:00 to 11:30 instead of 07:00 to 19:30, and the outside temperature peaks around 07:00 instead of 14:00.
- Where the shifted block starts, 8 hours of 1 June appear twice with different values: these are the 96 "duplicates" per office machine. Where it ends, 8 June has an 8-hour hole.
- The mall runs normally that week, so it only affects the office.
- Plan: move that block 8 hours later in the cleaning step (`02_data_quality`), then check that the duplicates and the hole disappear.

