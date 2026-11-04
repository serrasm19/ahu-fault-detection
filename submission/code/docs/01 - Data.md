# Data

Back to the [project map](00%20-%20Project%20map.md).

The client data is not in the repository. The code reads it from the folder set in `config.py` (or `AHU_DATA_DIR`).

## Tables

All tables join on `ahu_id` (for example `B2-AHU-07`: building B2, unit 7).

| File | Rows | What it is |
|---|---|---|
| `ahu_metadata.csv` | 40, one per AHU | Building, what the unit serves, design airflow, fan rating, extra sensors, operating hours |
| `fault_labels_train.csv` | 28, one per fault event | `ahu_id`, `fault_type`, `start`, `end`. From work orders, confirmed on site |
| `ahu_train.parquet` | 2,053,533 | 5-minute sensor log, 1 Jan to 30 Jun 2025. Labels come from the table above |
| `ahu_test.parquet` | 711,994 | Same columns, 1 Jul to 31 Aug 2025, no labels. This is what I predict |

## Buildings

| Building | Type | AHUs | Hours | Extra sensors | Design airflow (m³/h) |
|---|---|---|---|---|---|
| B1 | Office | 16 | Mon–Fri 07:00–19:30, closed on public holidays. Two units 24/7 | CO2 | 12,500 – 30,000 |
| B2 | Hospital | 12 | 24/7 | CO2, supply airflow | 6,000 – 20,000 |
| B3 | Mall | 12 | Daily 09:00–23:00 | none | 25,000 – 44,500 |

Units are very different in size, so raw values can't be compared between units.

## Sensor columns

Local time UTC+8. Rows are logged while the fan is off too, but only rows with the fan on are scored.

| Group | Columns | Notes |
|---|---|---|
| Fan | `fan_status`, `fan_speed_pct`, `fan_power_kw`, `supply_static_pa`, `supply_static_sp_pa` | Fan speed is controlled to hold the static pressure setpoint |
| Air temperatures | `oat_c`, `oa_rh_pct`, `rat_c`, `mat_c`, `sat_c`, `sat_sp_c`, `zone_temp_sp_c` | Outdoor, return, mixed and supply air. The valve is controlled to hold `sat_sp_c` |
| Chilled water | `chw_valve_cmd_pct`, `chwst_c` | The valve column is the command, not the real position |
| Outdoor air and filter | `oa_damper_cmd_pct`, `filter_dp_pa` | The damper column is the command too. In B1 and B2 it opens more when CO2 rises |
| Extra | `co2_ppm` (B1, B2), `sa_flow_m3h` (B2) | Empty in buildings without the sensor |

## Labels

| Fault | Events | Typical length | B1 | B2 | B3 |
|---|---|---|---|---|---|
| `chw_valve_stuck` | 8 | 5.6 days | 2 | 2 | 4 |
| `low_coil_capacity` | 7 | 4.3 days | 3 | 3 | 1 |
| `oa_damper_stuck` | 7 | 5.6 days | 4 | 1 | 2 |
| `sat_sensor_bias` | 6 | 10.3 days | 1 | 0 | 5 |

Only 21 of the 40 units have a labelled event. The labels are accurate but maybe not complete.

More detail in `notebooks/01_data_overview.ipynb` (phase 1).
