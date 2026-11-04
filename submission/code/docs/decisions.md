# Decisions and assumptions

Back to the [project map](00%20-%20Project%20map.md).

Short log of the choices I made and why. Newest at the bottom.

| # | Topic | Decision | Why | Ask the client |
|---|---|---|---|---|
| 1 | Location and holidays | I assume the buildings are in Singapore and use the Singapore public holiday calendar. | The data is in UTC+8 and the office closed on exactly the 7 weekdays that are Singapore 2025 public holidays. Kuala Lumpur (also UTC+8) has different holidays. | Where are the three buildings, and which holiday calendar do they follow? |
| 2 | Rows I score | I only learn from and score rows with the fan on. With the fan off I predict normal. | The brief scores only fan-on rows. With the fan off there is no air flow, so most faults can't be seen. | Do you also want alerts when the AHU is off, for example a sensor that drifts overnight? |
| 3 | Shifted office week | I will move the B1 data from 2 to 8 June 8 hours later in the cleaning step (notebook 02). | That week was saved in UTC instead of local time. It explains the night running, the 96 duplicates on 1 June and the 8-hour hole on 8 June. | Did the office BMS change its time settings in early June? |
