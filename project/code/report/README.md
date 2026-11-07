# Report sources

The sections of `project/report.pdf`, one Markdown file per section, and the script that builds the PDF in LaTeX:

```bash
brew install pandoc tectonic   # once
python report/build.py         # from project/code/
```

It writes `project/report.pdf` and prints the number of pages.

I keep it short: clear decisions, not a list of everything.

| File | Content | Pages |
|---|---|---|
| `00_cover.md` | Title, name and GitHub link | top of page 1 |
| `01_eda.md` | Approach, data quality, patterns, faults | 5-6 |
| `02_model_summary.md` | Summary of the model | 1 |
| `03_architecture.md` | Production design: diagram and explanation | 2 |
| `04_client.md` | Example scenario: reply and internal note | 1.5 |
| `appendix.md` | Details that don't fit in the main pages | free |

Figures come from `../figures/` (written by the notebooks and by `architecture_diagram.py`). The look of the PDF is in `header.tex` and `metadata.yaml`.
