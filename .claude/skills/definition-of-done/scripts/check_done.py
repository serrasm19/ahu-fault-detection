"""Check a change: tests, lint, and the files that should change together with it."""

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

CODE = "submission/code"
DOCS = f"{CODE}/docs"
ROOT = Path(__file__).resolve().parents[4]
SKILLS = "../../.claude/skills"  # the path CI uses, from submission/code

# When a file like the left side changes, one of the files on the right should change too
COMPANIONS = (
    (f"{CODE}/src/ahu_fdd/data.py", (f"{DOCS}/01 - Data.md", f"{DOCS}/02 - Data quality.md")),
    (f"{CODE}/src/ahu_fdd/features.py", (f"{DOCS}/04 - Modelling.md",)),
    (f"{CODE}/src/ahu_fdd/rules.py", (f"{DOCS}/04 - Modelling.md",)),
    (f"{CODE}/src/ahu_fdd/models.py", (f"{DOCS}/04 - Modelling.md",)),
    (f"{CODE}/src/ahu_fdd/postprocess.py", (f"{DOCS}/04 - Modelling.md",)),
    (f"{CODE}/src/ahu_fdd/evaluation.py", (f"{DOCS}/04 - Modelling.md",)),
    (f"{CODE}/src/ahu_fdd/predict.py", (f"{DOCS}/04 - Modelling.md",)),
    (f"{CODE}/src/ahu_fdd/simulat*.py", (f"{DOCS}/04 - Modelling.md",)),
    (f"{CODE}/src/ahu_fdd/triage.py", (f"{DOCS}/07 - Claude skills.md",)),
    (f"{CODE}/src/ahu_fdd/config.py", (f"{DOCS}/decisions.md",)),
    (f"{CODE}/report/*.md", ("submission/report.pdf",)),
    (".claude/skills/*", (f"{DOCS}/07 - Claude skills.md",)),
    (".github/*", (f"{DOCS}/06 - Development workflow.md",)),
)
# Any notable change is listed in the changelog
NEEDS_CHANGELOG = (
    f"{CODE}/src/*",
    f"{CODE}/app/*",
    f"{CODE}/report/*",
    ".claude/skills/*",
    ".github/*",
)
# These must never go into the public repository
PRIVATE = ("AGENTS.md", "CLAUDE.md", "context/*", "assignment/*", "*.parquet", ".env")


def git(*args: str) -> str:
    """Run a git command in the repository and return its output."""
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return done.stdout


def changed_files(base: str) -> set[str]:
    """Everything that differs from `base`: commits, staged, unstaged and untracked files."""
    files = git("-c", "core.quotepath=off", "diff", "--name-only", f"{base}...HEAD").splitlines()
    files += git("-c", "core.quotepath=off", "diff", "--name-only", "HEAD").splitlines()
    files += git("ls-files", "--others", "--exclude-standard").splitlines()
    return set(files)


def _any_match(path: str, patterns: tuple[str, ...]) -> bool:
    """True if the path matches one of the patterns."""
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def missing_companions(files: set[str]) -> list[str]:
    """One line for each file that should have changed with this change and didn't."""
    missing = []
    for path in sorted(files):
        name = Path(path).name
        is_code = fnmatch.fnmatch(path, f"{CODE}/src/ahu_fdd/*.py")
        if is_code and name not in ("__init__.py", "config.py"):
            test = f"{CODE}/tests/unit/test_{name}"
            if test not in files:
                missing.append(f"{test} (changed with {path})")
    for pattern, needed in COMPANIONS:
        changed = sorted(path for path in files if fnmatch.fnmatch(path, pattern))
        if changed and not files & set(needed):
            missing.append(f"{' or '.join(needed)} (changed with {changed[0]})")
    if any(_any_match(path, NEEDS_CHANGELOG) for path in files) and "CHANGELOG.md" not in files:
        missing.append("CHANGELOG.md (a notable change needs a line)")
    return missing


def private_files(files: set[str]) -> list[str]:
    """Changed files that must stay out of the public repository."""
    return sorted(path for path in files if _any_match(path, PRIVATE))


def run_tool(*command: str) -> tuple[bool, str]:
    """Run a Python tool in submission/code. Returns if it passed and its last output line."""
    cwd = ROOT / CODE
    done = subprocess.run([sys.executable, "-m", *command], cwd=cwd, capture_output=True, text=True)
    lines = (done.stdout + done.stderr).strip().splitlines()
    return done.returncode == 0, lines[-1] if lines else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/develop", help="branch to compare with")
    parser.add_argument("--skip-tests", action="store_true", help="only check the changed files")
    args = parser.parse_args()

    files = changed_files(args.base)
    print(f"Changed files against {args.base}: {len(files)}")
    failed = False

    for line in missing_companions(files):
        print(f"MISSING  {line}")
        failed = True
    for path in private_files(files):
        print(f"PRIVATE  {path} must not go into the repository")
        failed = True

    if args.skip_tests:
        print("SKIPPED  tests and lint")
    else:
        checks = {
            "tests": ("pytest", "-q", "--cov"),
            "ruff check": ("ruff", "check", "."),
            "ruff format": ("ruff", "format", "--check", "."),
            "ruff check, skills": ("ruff", "check", "--config", "pyproject.toml", SKILLS),
            "ruff format, skills": (
                "ruff",
                "format",
                "--check",
                "--config",
                "pyproject.toml",
                SKILLS,
            ),
        }
        for name, command in checks.items():
            passed, last_line = run_tool(*command)
            print(f"{'OK' if passed else 'FAILED':8} {name}: {last_line}")
            failed = failed or not passed
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
