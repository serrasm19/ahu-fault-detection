---
name: definition-of-done
description: Check that a change in this repository is really finished before saying it is done or committing it. Runs tests, coverage and lint, and finds the files that should have changed together, such as tests, docs notes, decisions, changelog, README or the report PDF. Use this whenever work on a change ends, before a commit or a pull request, or when someone asks "is this ready", "did I forget anything" or "can I commit".
---

# Definition of done

The script checks what a machine can check. Then you check what needs reading. A list of green ticks is not the goal: the user must know what was checked and what was not.

## Steps

1. **Run the script** from the repository root:

   ```bash
   .venv/bin/python .claude/skills/definition-of-done/scripts/check_done.py
   ```

   It compares the working tree with `origin/develop`. Use `--base <ref>` for another base, and `--skip-tests` for a quick look at the files only.

2. **Fix or explain each `MISSING` line.** Each one is a file that usually changes with the ones you changed. Sometimes the rule doesn't apply, for example a comment-only change in `src/`. Then say why, and don't add an empty change to make it pass.

3. **Read what the script can't judge.** Open the changed docs and ask:

   - Does the note say what the code does now, with real numbers?
   - Does a new cleaning choice, assumption or modelling choice have a row in `project/code/docs/decisions.md`?
   - If model code changed, does `python -m ahu_fdd.predict` still give the same `predictions.csv`? If it changed on purpose, is that written down?
   - If `src/` changed, do the notebooks that use it still run? Their outputs must match the code.
   - Do `AGENTS.md` and `context/WORK_PLAN.md` exist? They are local only. If they do, follow their rules and tick the finished tasks.

4. **Report it** with the format below. Don't commit or push unless the user asked for it.

## Report format

```markdown
**Ready to commit:** yes or no

| Check | Result |
|---|---|
| Tests and coverage | ... |
| Lint and format | ... |
| Files that change together | ... |
| Docs read | ... |

**Not checked:** <what I didn't run, and why>
**To do first:** <only if something is missing>
```
