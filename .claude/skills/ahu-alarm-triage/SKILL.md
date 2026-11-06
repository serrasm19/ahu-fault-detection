---
name: ahu-alarm-triage
description: Explain one AHU alarm from the sensor data, name the likely fault and say what a technician should check. Use this whenever someone asks what is wrong with an air handling unit, asks about a unit such as B1-AHU-11, wants to review an alarm from predictions.csv, wants to know if an alarm is real or a false alarm, or needs a work order text, even if they don't say "triage".
---

# AHU alarm triage

Turn an alarm into a short diagnosis a maintenance team can act on. The script gives the numbers and you give the judgement, so every statement must point to a number from the script.

## Steps

Run the commands from the repository root with the project environment (`.venv/bin/python` if it exists). The data folder comes from `AHU_DATA_DIR` or the default in `config.py`.

1. **Find the alarm.** If you have no machine and dates, list the alarms in `submission/predictions.csv` and ask which one, or take the one the user describes:

   ```bash
   .venv/bin/python .claude/skills/ahu-alarm-triage/scripts/alarm_evidence.py --list
   ```

2. **Get the evidence.** `--end` is not included, so for "to 3 April" write `--end 2025-04-04`:

   ```bash
   .venv/bin/python .claude/skills/ahu-alarm-triage/scripts/alarm_evidence.py --ahu B1-AHU-11 --start 2025-04-23 --end 2025-04-29
   ```

3. **Read `references/fault_fingerprints.md`.** It has the fingerprints, the look-alikes, the confidence levels and what to check on site.

4. **Decide.** Compare the signals and the rules with the fingerprints. "No clear fault" and "the data can't separate these two" are valid answers. A wrong diagnosis sends a technician to the wrong part, so don't force a fault.

5. **Write the card** with the format below. Use the plain fault name next to the label, for example stuck flap (`oa_damper_stuck`).

Work from the sensors. Don't open the work orders (`fault_labels_train.csv`) or `EXTRA_LABELS` unless the user asks, because then the diagnosis is no longer independent. Those labels only remove known faults from the machine's normal inside the script.

## Card format

```markdown
## <ahu_id>, <start> to <end>

**Diagnosis:** <plain name> (`<label>`), or no clear fault
**Confidence:** high, medium or low, and one line on why

| Signal | Window | Normal | Change |
|---|---|---|---|
<only the signals that matter for this decision>

**Why:** <2 or 3 short sentences that link the numbers to the physics>
**What else it could be:** <the look-alike and why I rule it out, or why I can't>
**Send someone?** <yes, now / yes, at the next visit / no>
**What to check on site:** <the check for this fault>
**Limits:** <what this data can't show here, for example no checks at rest>
```

If the user asks for a message to the client or a work order, write it after the card, in plain words, without labels or model terms.
