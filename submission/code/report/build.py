"""Build submission/report.pdf from the Markdown sections: python report/build.py (from code/)

Needs pandoc and tectonic (brew install pandoc tectonic) and pypdf (pip install pypdf).
"""

import subprocess
from pathlib import Path

from pypdf import PdfReader

REPORT_DIR = Path(__file__).resolve().parent
OUTPUT = REPORT_DIR.parents[1] / "report.pdf"  # submission/report.pdf, next to code/

# Sections in order. The appendix starts on a new page and does not count in the 12 pages
# Each question starts on a new page (newpage.md is a page break)
MAIN = [
    "00_cover.md",
    "01_eda.md",
    "newpage.md",
    "02_model_summary.md",
    "newpage.md",
    "03_architecture.md",
    "newpage.md",
    "04_client.md",
]
APPENDIX = ["appendix.md"]
MAX_PAGES = 12


def pandoc(sections: list[str], output: Path) -> None:
    """Join the sections and turn them into a PDF with pandoc and tectonic (LaTeX)."""
    subprocess.run(
        [
            "pandoc",
            *sections,
            "--from=markdown",
            "--pdf-engine=tectonic",
            "--include-in-header=header.tex",
            "--lua-filter=glance.lua",
            "--metadata-file=metadata.yaml",
            "-o",
            str(output),
        ],
        cwd=REPORT_DIR,  # image paths in the sections are relative to this folder
        check=True,
        capture_output=True,  # tectonic is chatty; errors still stop the build
    )


def page_count(pdf: Path) -> int:
    """Number of pages of a PDF."""
    return len(PdfReader(pdf).pages)


def main() -> None:
    # First the main part alone, to check the page limit of the brief
    main_only = REPORT_DIR / "main_only.pdf"
    pandoc(MAIN, main_only)
    main_pages = page_count(main_only)
    main_only.unlink()

    # Then the full report, with the appendix on a new page
    pandoc([*MAIN, "newpage.md", *APPENDIX], OUTPUT)
    total = page_count(OUTPUT)
    status = "OK" if main_pages <= MAX_PAGES else "TOO LONG"
    appendix = total - main_pages
    print(f"{OUTPUT}: {main_pages} main pages ({status}, max {MAX_PAGES}) + {appendix} appendix")


if __name__ == "__main__":
    main()
