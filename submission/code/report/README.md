# Report sources

The sections of `submission/report.pdf`, one Markdown file per question, and the script that builds the PDF in LaTeX:

```bash
brew install pandoc tectonic   # once
python report/build.py         # from submission/code/
```

It writes `submission/report.pdf` and checks the page limit.

Brief: at most 12 pages plus appendix. "We value a short report that makes clear decisions over a long one that lists everything."

| File | Content | Page budget |
|---|---|---|
| `00_cover.md` | Title, name, GitHub link and release | top of page 1 |
| `01_eda.md` | Q1: approach, data quality, patterns, faults | 5-6 |
| `02_model_summary.md` | Q2: summary of the model | 1 |
| `03_architecture.md` | Q3: diagram and explanation | 2 |
| `04_client.md` | Q4: reply to the client and internal note | 1.5 |
| `appendix.md` | Details that don't fit (not counted in the 12 pages) | free |

Figures come from `../figures/` (written by the notebooks and by `architecture_diagram.py`). The look of the PDF is in `header.tex` and `metadata.yaml`.
