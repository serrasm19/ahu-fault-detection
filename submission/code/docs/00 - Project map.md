# Project map

Fault detection and diagnosis for air handling units (AHUs), from 5-minute BMS data of 40 units in three buildings. This is the entry point to the docs. You can open this folder as an Obsidian vault, or read it on GitHub.

## Notes

| Note | What it covers | Status |
|---|---|---|
| [Data](01%20-%20Data.md) | The four tables, their columns and the sensors in each building | First version |
| [Data quality](02%20-%20Data%20quality.md) | Problems found in the data and how I handle them | Phase 1 |
| [AHU physics and faults](03%20-%20AHU%20physics%20and%20faults.md) | How an AHU works and what each fault looks like in the sensors | First version |
| [Modelling](04%20-%20Modelling.md) | Approach, features, validation and results | Phase 2 |
| [Architecture](05%20-%20Architecture.md) | How this would run in production | Phase 3 |
| [Development workflow](06%20-%20Development%20workflow.md) | Setup, tests, CI, branches and releases | Done |
| [Decisions](decisions.md) | Log of the decisions and assumptions I made | Ongoing |

## Where things are

- Code: `src/ahu_fdd/`
- Notebooks: `notebooks/`
- Tests: `tests/unit/`
- Changes per version: `CHANGELOG.md` at the root of the repository
