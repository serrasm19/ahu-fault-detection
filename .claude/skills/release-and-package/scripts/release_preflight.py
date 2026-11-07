"""Check that the repository is ready for a release, before any branch moves."""

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CODE = ROOT / "project" / "code"
READMES = (ROOT / "README.md", CODE / "README.md")


def git(*args: str) -> str:
    """Run a git command in the repository and return its output."""
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def changelog_problem(text: str, version: str) -> str | None:
    """The first version in the changelog must be this one, with a real date."""
    heading = re.search(r"^## \[([0-9.]+)\] - (.+)$", text, re.MULTILINE)
    if heading is None:
        return "no version heading"
    if heading.group(1) != version:
        return f"the first version is {heading.group(1)}, not {version}"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", heading.group(2)):
        return f"the date is {heading.group(2)}, not a real date"
    return None


def readme_problem(text: str, version: str) -> str | None:
    """The README must link to this release."""
    return None if f"releases/tag/v{version}" in text else "no link to this release"


def checks(version: str) -> dict[str, str | None]:
    """Each check with its problem, or None if it is fine."""
    package = tomllib.loads((CODE / "pyproject.toml").read_text())["project"]["version"]
    card = CODE / "artifacts" / f"lgbm-v{version}" / "model_card.json"
    found = {
        "changelog": changelog_problem((ROOT / "CHANGELOG.md").read_text(), version),
        "package version": None if package == version else f"pyproject.toml says {package}",
        "model card": None if card.exists() else f"{card.name} missing in lgbm-v{version}",
        "new tag": "the tag already exists" if git("tag", "--list", f"v{version}") else None,
        "working tree": "uncommitted changes" if git("status", "--porcelain") else None,
    }
    for readme in READMES:
        name = str(readme.relative_to(ROOT))
        found[name] = readme_problem(readme.read_text(), version)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="for example 1.1.0")
    args = parser.parse_args()

    found = checks(args.version)
    for name, problem in found.items():
        print(
            f"{'OK' if problem is None else 'FAILED':7} {name}{f': {problem}' if problem else ''}"
        )
    return 1 if any(found.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
