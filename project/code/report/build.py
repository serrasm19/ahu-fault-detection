"""Build project/report.pdf from the Markdown sections: python report/build.py (from code/)

Needs pandoc and tectonic (brew install pandoc tectonic) and pypdf (pip install pypdf).
"""

import subprocess
from pathlib import Path

from pypdf import PdfReader

REPORT_DIR = Path(__file__).resolve().parent
OUTPUT = REPORT_DIR.parents[1] / "report.pdf"  # project/report.pdf, next to code/

# Sections in order. Each section and the appendix start on a new page (newpage.md is a break)
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
    pandoc([*MAIN, "newpage.md", *APPENDIX], OUTPUT)
    print(f"{OUTPUT}: {page_count(OUTPUT)} pages")


if __name__ == "__main__":
    main()
