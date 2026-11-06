# Fault fingerprints

The numbers come from the labelled events in `notebooks/04_faults.ipynb`. The script reports medians of the running rows (fan on, after the 30-minute start-up).

How to read the script output:

- `supply_air_error_c` is supply air minus its target. Positive means the air is too warm, negative too cold.
- Compare the `change` column with the table below, not the `window` column. `change` is against this machine's own normal, and the rules use the same comparison.
- A stuck tap shows the command and the real valve going opposite ways. Cold air with the command at 0% means the valve is stuck open. Warm air with the command at 100% means it is stuck nearly closed.

## The four faults

| Fault | What breaks | Main signals | Typical change | What to check on site |
|---|---|---|---|---|
| Stuck tap (`chw_valve_stuck`) | The chilled water valve doesn't follow its command | `supply_air_error_c` far from normal, valve command at 0% or 100% | +4 to +12 °C (stuck nearly closed) or -4.5 to -5.6 °C (stuck open) | Move the valve by hand from the BMS, watch the actuator and the supply air |
| Stuck flap (`oa_damper_stuck`) | The outdoor air damper doesn't open | `outdoor_air_fraction` near 0, `damper_command_pct` up, `co2_ppm` up | Fraction down by about 0.10 to almost 0, command +40 points, CO2 +440 to +1,030 ppm | Command the damper open and look at the blades and the linkage |
| Lying thermometer (`sat_sensor_bias`) | The supply air sensor reads wrong | `offset_at_rest_c` | Normal -0.5 °C, with a fault +2.0 to +2.4 or -2.5 to -3.2 °C | Put a calibrated thermometer next to the sensor |
| Weak radiator (`low_coil_capacity`) | The coil gives less cooling | `valve_above_usual_for_same_work`, `valve_command_pct` | Valve +8 to +36 points, supply air on target until the valve reaches 100% | Check coil dirt, air in the coil, chilled water flow and temperature |

## Look-alikes

- **Stuck tap or weak radiator.** Both can end with the valve open and warm air. With a stuck tap the supply air is off target almost all the time (97% of the rows). With a weak radiator the air stays near target in most rows.
- **Machine always at its limit.** If `valve_at_limit_share_when_healthy` is high (the three known ones are B1-AHU-05, B3-AHU-02 and B3-AHU-09, at 60-80%), the valve at 100% is normal for that machine. It is probably too small for its zone, so the valve alone proves nothing. The supply air `change` still counts, because it is against this machine's normal. If the stuck tap rule fires on most rows, name the stuck tap with medium confidence and say the weak radiator can't be ruled out. If no rule fires, it is normal for this machine.
- **Storm.** Outdoor air falls 3 °C or more in minutes (`largest_outdoor_drop_1h_c`) and valves close for a short time. A storm lasts hours, not days.
- **Start-up.** The first 30 minutes look like a weak radiator. The script leaves them out.
- **Frozen or missing sensors.** Look at `missing_share_when_running`. If a sensor needed for a rule is missing for much of the window, say so. The cleaning blanks frozen sensors, so a frozen sensor looks like missing data here.
- **Filter drift.** Dirty filters move slowly for months. They are not one of the four faults.

## Blind spots

- **Lying thermometer on a machine that never stops.** Without the fan off for an hour there are no checks at rest (`checks_at_rest_in_window` = 0). I can't confirm or rule out this fault there, so I say that.
- **No CO2 sensor.** The mall has none (`has_co2_sensor` false). A stuck flap then shows only in the outdoor air fraction.
- **Small outdoor-return difference.** The outdoor air fraction is not reliable when outdoor and return air are less than 2 °C apart (`outdoor_minus_return_c`).

## Confidence

| Level | When |
|---|---|
| High | The main rule fires on at least half of the running rows, and a second signal agrees |
| Medium | The rule fires on 10% to 50% of the rows, or only one signal moves |
| Low | The rule fires on under 10% of the rows, signals disagree, a look-alike applies, or a needed sensor is missing |

No checks at rest only limits what I can say about a lying thermometer. It doesn't lower the confidence of another fault with clear signals, but say it under Limits.

The share of rows depends on the window you ask for. A short fault in a long window gives a low share, so narrow the window before you call it weak.

A second signal is one the fingerprint table names, other than the one in the rule: for example CO2 for a stuck flap, or the valve command against the air for a stuck tap. A lying thermometer has only the offset at rest, so many checks at rest count as the second signal. Another rule that fires on a small share of the rows, next to a clear main rule, is usually a side effect. Mention it, but don't change the diagnosis.

## Send someone?

| Answer | When |
|---|---|
| Now | People or the building are affected today: supply air far off target, or overcooling for days in a hospital |
| At the next visit | A real fault, but the machine still does its job |
| No | No clear fault, or only a question about the size of the machine |

