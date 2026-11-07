---
name: release-and-package
description: Prepare a project release, promote it from develop to qa to main, and build and test the project ZIP in a clean folder.
disable-model-invocation: true
---

# Release and package

This skill only runs when the user asks for it with `/release-and-package <version>`, because it changes protected branches and publishes a tag. A tag is never moved or reused, so a mistake here stays in the public history.

Stop and ask before each step marked **ask**. An approval for one step doesn't count for the next.

## 1. Prepare

1. Start from an up-to-date `develop`, then create `feature/release-<version>`.
2. Update these files:
   - `CHANGELOG.md`: put the real date on the current version.
   - `project/code/pyproject.toml`: set the version, then run `pip install -e project/code` so the package reports it.
   - `README.md` and `project/code/README.md`: update the "Latest release" link.
3. Rebuild the model card, so it shows the new version: `python -m ahu_fdd.predict`. Compare `predictions.csv` with the old one. If it changed and that was not planned, stop and tell the user.
4. Run `definition-of-done`, and `notebook-consistency` if notebooks or results changed.
5. Run the preflight. Every line must say `OK`:

   ```bash
   .venv/bin/python .claude/skills/release-and-package/scripts/release_preflight.py --version <version>
   ```

## 2. Promote

Wait for green CI at each pull request. Use the merge type of each step, because the branch rules refuse the other ones.

| Step | Pull request | Merge |
|---|---|---|
| **ask** | `feature/release-<version>` to `develop` | Squash |
| **ask** | `develop` to `qa` | Merge commit |
| **ask** | `qa` to `main` | Merge commit |

Then check that the `release` workflow ran, that the tag `v<version>` points to the merge commit on `main`, and that the GitHub Release exists. Delete the feature branch on GitHub and locally. If a step fails, stop and report. Don't force push, and don't work around the branch rules.

## 3. Package

Build the ZIP from `main` and test it as a stranger would: a clean folder, a new environment, only the ZIP and the data. This takes about 5 minutes, so run it in the background.

```bash
bash .claude/skills/release-and-package/scripts/clean_check.sh origin/main ahu-fault-detection-<version>.zip
```

It needs `AHU_DATA_DIR` if the data is not in `data/`. It stops at the first failure.

## 4. Report

Tell the user the release link, the ZIP path and size, the test results, and that `predictions.csv` is byte-identical (same sha256). Say what you didn't check. Uploading the ZIP is up to the user.
