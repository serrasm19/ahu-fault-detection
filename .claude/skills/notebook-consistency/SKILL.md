---
name: notebook-consistency
description: Check that the text of the project notebooks and the report agrees with the real outputs. Finds numbers in the Markdown that appear in no output, execution errors, cells run out of order and missing sections. Use this after any notebook is re-run, after code changes that move the results, before a release, or when someone asks if the numbers in a notebook or in the report are still right.
---

# Notebook consistency

A notebook is built in two steps: the code writes the outputs, and a person writes the text after reading them. When the code changes, the outputs move and the text stays. The script finds the candidates. You read them and decide.

## Steps

1. **Run the script** from the repository root. Give it the notebooks, and the report sources if the numbers there come from the notebooks:

   ```bash
   .venv/bin/python .claude/skills/notebook-consistency/scripts/check_numbers.py submission/code/notebooks/*.ipynb --text submission/code/report/*.md
   ```

2. **Fix any `ERROR` line first.** A notebook with an error, or run out of order, has outputs you can't trust. Run it again before you look at its numbers.

3. **Read every `NOT FOUND` line** with its sentence. Many are fine: a setting from `config.py`, a number from the brief, a date, or a value computed in the text. A real mismatch is a result that changed. Check in `src/ahu_fdd/config.py` and in the data before you call it wrong.

4. **Look at `FAR` lines only for key results.** The number exists, but not near this text, so it could be a coincidence.

5. **Report it** with the format below. Never change a number in the text to make the check pass unless you confirmed the right value in an output. Then fix the text, or run the notebook again if the output is the old one.

## Report format

```markdown
**Result:** <consistent, or how many real mismatches>

| Where | Text says | Output says | Verdict |
|---|---|---|---|
<one row for each line that needed a decision>

**Checked by reading:** <what I looked at by hand>
**Not checked:** <numbers in figures, and numbers that match by chance>
```

## Limits

The script checks that a number exists in the outputs, not that it is the right one. A short number can match by chance. It can't read numbers inside figures.
