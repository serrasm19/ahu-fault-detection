"""Compare the numbers in notebook text and report files with the notebook outputs."""

import argparse
import json
import re
import sys
from pathlib import Path

NEAR_CELLS = 3  # outputs of this many code cells before the text count as near
MAX_PLAIN_INTEGER = 12  # small whole numbers are usually counts in the text, not results
REQUIRED_TEXT = ("**Goal:**", "How to read", "Summary")
HTML_TAG = re.compile(r"<[^>]+>")

NUMBER = re.compile(r"(?<![\w.,-])[+\-−]?\d[\d,]*(?:\.\d+)?(?![\w-]|\.\d)(\s?%)?")
# Parts of the text that hold no results: code, links, images, dates, machine names and headings
NOT_RESULTS = (
    re.compile(r"`[^`]*`"),
    re.compile(r"!?\[[^\]]*\]\([^)]*\)"),
    re.compile(r"^#+ .*$", re.MULTILINE),
    re.compile(r"^\s*\d+\.\s", re.MULTILINE),
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    re.compile(r"\b\d{1,2}:\d{2}\b"),
    re.compile(
        r"\b\d{1,2}(?:\s?(?:to|-|–)\s?\d{1,2})?\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*"
    ),
    re.compile(r"\b(?:January|February|March|April|May|June|July|August)\s\d{1,4}\b"),
    re.compile(r"\b20\d{2}\b"),
)


def as_float(token: str) -> float:
    """'1,030' to 1030.0 and '−0.5' to -0.5."""
    return float(token.replace(",", "").replace("−", "-").replace("%", "").strip())


def decimals(token: str) -> int:
    """How many decimals the number has, as written."""
    token = token.replace("%", "").strip()
    return len(token.split(".")[1]) if "." in token else 0


def numbers_in(text: str) -> list[str]:
    """The numbers in a piece of text, as written, without the parts that hold no results."""
    for pattern in NOT_RESULTS:
        text = pattern.sub(" ", text)
    return [match.group(0).strip() for match in NUMBER.finditer(text)]


def is_worth_checking(token: str) -> bool:
    """Skip small whole numbers such as '3 machines'. Percentages and decimals always count."""
    if "%" in token or "." in token:
        return True
    return abs(as_float(token)) > MAX_PLAIN_INTEGER


def matches(token: str, output_values: set[float]) -> bool:
    """True if an output rounds to the number in the text, directly or as a share (0.93 is 93%)."""
    value = abs(as_float(token))
    places = decimals(token)
    tolerance = 0.5 * 10**-places + 1e-9
    for found in output_values:
        found = abs(found)
        if abs(found - value) <= tolerance:
            return True
        if "%" in token and abs(found * 100 - value) <= tolerance:
            return True
    return False


def cell_text(cell: dict) -> str:
    """The source of a cell as one string."""
    return "".join(cell["source"])


def output_text(cell: dict) -> str:
    """Everything a code cell printed or showed as text."""
    parts = []
    for output in cell.get("outputs", []):
        parts += output.get("text", [])
        parts += output.get("data", {}).get("text/plain", [])
        # Styled tables keep their numbers only in the HTML
        parts.append(HTML_TAG.sub(" ", "".join(output.get("data", {}).get("text/html", []))))
    return "".join(parts)


def output_values(text: str) -> set[float]:
    """All the numbers in an output, with no filter: an output can show any number."""
    return {as_float(match.group(0)) for match in NUMBER.finditer(text)}


def structure_problems(notebook: dict) -> list[str]:
    """Errors, cells that never ran or ran out of order, and missing sections."""
    problems = []
    code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    for position, cell in enumerate(code, start=1):
        if any(output.get("output_type") == "error" for output in cell.get("outputs", [])):
            problems.append(f"code cell {position} ended with an error")
        if cell.get("source") and cell.get("execution_count") is None:
            problems.append(f"code cell {position} was not run")
    counts = [cell["execution_count"] for cell in code if cell.get("execution_count")]
    if counts != sorted(counts):
        problems.append("code cells were run out of order")
    text = "\n".join(cell_text(c) for c in notebook["cells"] if c["cell_type"] == "markdown")
    problems += [f"missing '{part}'" for part in REQUIRED_TEXT if part not in text]
    return problems


def check_notebook(notebook: dict) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Numbers in the text with no output anywhere, and those only found far from the text."""
    outputs = [
        output_values(output_text(cell))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]
    everywhere = set().union(*outputs) if outputs else set()
    not_found, far = [], []
    code_seen = 0
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            code_seen += 1
            continue
        near = set().union(*outputs[max(0, code_seen - NEAR_CELLS) : code_seen], set())
        for line in cell_text(cell).splitlines():
            for token in filter(is_worth_checking, numbers_in(line)):
                if matches(token, near):
                    continue
                target = far if matches(token, everywhere) else not_found
                target.append((token, line.strip()))
    return not_found, far


def check_text(path: Path, outputs: set[float]) -> list[tuple[str, str]]:
    """Numbers in a report file that appear in no notebook output."""
    missing = []
    for line in path.read_text().splitlines():
        for token in filter(is_worth_checking, numbers_in(line)):
            if not matches(token, outputs):
                missing.append((token, line.strip()))
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="+", type=Path)
    parser.add_argument("--text", nargs="*", type=Path, default=[], help="report files to check")
    args = parser.parse_args()

    all_outputs: set[float] = set()
    errors = 0
    for path in args.notebooks:
        notebook = json.loads(path.read_text())
        problems = structure_problems(notebook)
        not_found, far = check_notebook(notebook)
        all_outputs |= output_values(
            " ".join(output_text(c) for c in notebook["cells"] if c["cell_type"] == "code")
        )
        print(f"\n== {path.name}: {len(not_found)} not found, {len(far)} far")
        for problem in problems:
            print(f"ERROR      {problem}")
        for token, line in not_found:
            print(f"NOT FOUND  {token}  |  {line[:110]}")
        for token, line in far:
            print(f"FAR        {token}  |  {line[:110]}")
        errors += len(problems)

    for path in args.text:
        missing = check_text(path, all_outputs)
        print(f"\n== {path.name}: {len(missing)} not found")
        for token, line in missing:
            print(f"NOT FOUND  {token}  |  {line[:110]}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
