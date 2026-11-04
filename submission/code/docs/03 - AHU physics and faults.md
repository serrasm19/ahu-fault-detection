# AHU physics and faults

Back to the [project map](00%20-%20Project%20map.md).

## How an AHU works

Return air from the building mixes with outdoor air (outdoor-air damper), goes through a filter and a chilled-water coil, and the supply fan blows it back into the space.

- The controller moves the chilled-water valve to keep the supply air temperature (`sat_c`) at its setpoint.
- The fan speed holds the duct static pressure at its setpoint.
- In a tropical climate the units cool all year. Outdoor air is hotter and more humid than return air, so they take the minimum outdoor air.

Mixing energy balance (from `starter/ahu_utils.py`):

`MAT = x · OAT + (1 − x) · RAT`, so the outdoor-air fraction is `x = (MAT − RAT) / (OAT − RAT)`. It is unreliable when OAT and RAT are close.

## The four faults

| Fault | What happens | What I expect to see |
|---|---|---|
| `chw_valve_stuck` | The valve stops following its command | The command moves but `sat_c` doesn't respond. `sat_c` drifts from setpoint when the load changes. The command goes to 0% or 100% trying to fix it |
| `oa_damper_stuck` | The outdoor-air damper is stuck nearly closed | Outdoor-air fraction close to 0 (MAT ≈ RAT) while the damper command is open. CO2 goes up in B1 and B2 |
| `sat_sensor_bias` | The supply air sensor reads too high or too low, and the controller trusts it | `sat_c` looks fine against setpoint, because the controller "fixes" a wrong reading. The real air is colder or warmer, so I look at the valve level for the load, MAT − SAT vs valve, the return air response, and airflow in B2 |
| `low_coil_capacity` | The coil gives much less cooling for the same valve opening | The valve opens more than usual for the same load. `sat_c` can't reach setpoint at high load |

Detection (is something wrong?) and diagnosis (what is it?) are different questions. Some faults may look alike with these sensors (stuck valve vs low coil capacity).

To be checked against the labelled events in `notebooks/04_faults.ipynb` (phase 1).

## References

- APAR rules (House et al., NIST, 2001), a classic rule set for AHU fault detection.
- ASHRAE RP-1312 and the LBNL fault detection datasets.
