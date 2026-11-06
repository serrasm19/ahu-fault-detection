"""Tests for the Claude skills in .claude/skills. Skipped in the ZIP, which doesn't have them."""

import importlib.util
import re

import pandas as pd
import pytest

from ahu_fdd.config import CODE_DIR

SKILLS_DIR = CODE_DIR.parents[1] / ".claude" / "skills"
SKILLS = (
    "ahu-alarm-triage",
    "definition-of-done",
    "fault-sensitivity-test",
    "notebook-consistency",
    "release-and-package",
)

pytestmark = pytest.mark.skipif(not SKILLS_DIR.exists(), reason="no .claude/skills folder here")


def _script(skill, name):
    """Load a skill script as a module."""
    path = SKILLS_DIR / skill / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _front_matter(skill):
    """The block on top of a SKILL.md as a dict of plain text values."""
    text = (SKILLS_DIR / skill / "SKILL.md").read_text()
    block = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL).group(1)
    return dict(line.split(": ", 1) for line in block.splitlines())


@pytest.mark.parametrize("skill", SKILLS)
def test_each_skill_has_a_name_and_a_description(skill):
    meta = _front_matter(skill)
    assert meta["name"] == skill
    assert 50 < len(meta["description"]) <= 1024


@pytest.mark.parametrize("skill", SKILLS)
def test_each_script_a_skill_names_exists(skill):
    text = (SKILLS_DIR / skill / "SKILL.md").read_text()
    for path in re.findall(r"\.claude/skills/[\w./-]+\.(?:py|sh)", text):
        assert (CODE_DIR.parents[1] / path).exists(), path


def test_only_a_person_can_start_a_release():
    assert _front_matter("release-and-package")["disable-model-invocation"] == "true"


def test_a_source_change_needs_its_test_doc_and_changelog():
    check = _script("definition-of-done", "check_done")
    missing = check.missing_companions({"submission/code/src/ahu_fdd/rules.py"})
    assert any("test_rules.py" in line for line in missing)
    assert any("04 - Modelling.md" in line for line in missing)
    assert any("CHANGELOG.md" in line for line in missing)


def test_a_complete_change_has_nothing_missing():
    check = _script("definition-of-done", "check_done")
    files = {
        "submission/code/src/ahu_fdd/rules.py",
        "submission/code/tests/unit/test_rules.py",
        "submission/code/docs/04 - Modelling.md",
        "CHANGELOG.md",
    }
    assert check.missing_companions(files) == []


def test_private_files_are_caught():
    check = _script("definition-of-done", "check_done")
    files = {"context/WORK_PLAN.md", "AGENTS.md", "x/ahu_train.parquet", "README.md"}
    assert check.private_files(files) == [
        "AGENTS.md",
        "context/WORK_PLAN.md",
        "x/ahu_train.parquet",
    ]


def test_numbers_in_skips_dates_code_and_machine_names():
    check = _script("notebook-consistency", "check_numbers")
    text = "On 22 April at 07:00 `min=24` B1-AHU-11 fell by 6.5 °C, in 2025 and 97.9% of rows."
    assert check.numbers_in(text) == ["6.5", "97.9%"]


@pytest.mark.parametrize(
    ("token", "values", "expected"),
    [
        ("93%", {0.926}, True),  # a share in the output, a percentage in the text
        ("93%", {92.6}, True),
        ("1,030", {1030.0}, True),
        ("−0.5", {-0.52}, True),
        ("93%", {90.0}, False),
        ("6.5", {6.7}, False),
    ],
)
def test_matches_allows_rounding_only(token, values, expected):
    check = _script("notebook-consistency", "check_numbers")
    assert check.matches(token, values) is expected


def _notebook(text, output, count=1):
    """A notebook with one code cell and the text after it."""
    code = {
        "cell_type": "code",
        "execution_count": count,
        "source": ["print(1)"],
        "outputs": [{"output_type": "stream", "text": [output]}],
    }
    return {"cells": [code, {"cell_type": "markdown", "source": [text]}]}


def test_a_number_that_left_the_outputs_is_found():
    check = _script("notebook-consistency", "check_numbers")
    not_found, far = check.check_notebook(_notebook("It finds 87% of the faults.", "share 0.93"))
    assert [token for token, _ in not_found] == ["87%"]
    assert far == []


def test_a_notebook_with_an_error_or_no_summary_is_reported():
    check = _script("notebook-consistency", "check_numbers")
    notebook = _notebook("**Goal:** x. How to read it.", "ok", count=None)
    notebook["cells"][0]["outputs"] = [{"output_type": "error"}]
    problems = check.structure_problems(notebook)
    assert "code cell 1 ended with an error" in problems
    assert "code cell 1 was not run" in problems
    assert "missing 'Summary'" in problems


def test_preflight_needs_this_version_with_a_real_date():
    check = _script("release-and-package", "release_preflight")
    assert check.changelog_problem("## [1.1.0] - 2026-11-20\n", "1.1.0") is None
    assert "not a real date" in check.changelog_problem("## [1.1.0] - YYYY-MM-DD\n", "1.1.0")
    assert "not 1.1.0" in check.changelog_problem("## [1.0.0] - 2026-11-05\n", "1.1.0")


def test_preflight_needs_the_link_to_the_release():
    check = _script("release-and-package", "release_preflight")
    assert check.readme_problem("see releases/tag/v1.1.0", "1.1.0") is None
    assert check.readme_problem("see releases/tag/v1.0.0", "1.1.0") is not None


def test_smallest_found_ignores_a_lucky_small_size():
    sweep = _script("fault-sensitivity-test", "run_sweep")
    table = pd.DataFrame(
        {
            "size": [float("nan"), 1.0, 2.0, 3.0, 4.0],
            "detected": [False, True, False, True, True],
        }
    )
    assert sweep.smallest_found(table) == "size 3"
    assert sweep.smallest_found(table.assign(detected=False)) == "none of the sizes"


def test_parse_sizes_reads_negative_sizes():
    sweep = _script("fault-sensitivity-test", "run_sweep")
    assert sweep.parse_sizes("-1,-2.5") == (-1.0, -2.5)
    assert sweep.parse_sizes(None) is None
