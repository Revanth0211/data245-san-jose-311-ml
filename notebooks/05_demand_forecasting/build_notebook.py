"""Generate the readable notebook from the tested reusable implementation."""
from pathlib import Path
import nbformat as nbf

folder = Path(__file__).resolve().parent
book = nbf.v4.new_notebook()
book.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
book.cells = [
    nbf.v4.new_markdown_cell('# Weekly illegal-dumping demand forecasting\n\nRevanth — intermediate technical milestone. AI-assisted implementation; review the accompanying README and acknowledge assistance in the course certificate. Results are provisional pending timezone, coverage, coordinate, and boundary agreement. The 2025 final test is reserved.'),
    nbf.v4.new_code_cell('from pathlib import Path\nimport sys\nroot = Path.cwd().resolve()\nwhile not (root / "src/demand_forecasting.py").exists():\n    if root == root.parent:\n        raise RuntimeError("Open this notebook within the repository")\n    root = root.parent\nsys.path.insert(0, str(root / "src"))\nimport pandas as pd\nfrom demand_forecasting import run'),
    nbf.v4.new_markdown_cell('## Protocol\nPredict each complete Monday–Sunday district-week at its start using only completed prior weeks. Compare fixed Poisson models trained on 2018–2023 and 2020–2023 against identical previous-week and four-week-average baselines. Scaling is fitted on training only. Validation is 2024, ending with the week starting December 23. No final-test metrics are calculated.'),
    nbf.v4.new_code_cell('scores = run()\nscores'),
    nbf.v4.new_markdown_cell('## Comparison\nPositive improvement below means lower MAE than the four-week baseline. These are validation comparisons, not a claim of statistical significance or final-test performance.'),
    nbf.v4.new_code_cell('baseline = scores.loc[scores.model.eq("four_week_average"), "mae"].iloc[0]\ncomparison = scores.loc[scores.model.eq("poisson")].copy()\ncomparison["mae_improvement_percent"] = 100 * (baseline - comparison.mae) / baseline\ncomparison'),
    nbf.v4.new_code_cell('pd.read_csv(root / "results/demand_forecasting/location_audit.csv")'),
    nbf.v4.new_code_cell('pd.read_csv(root / "results/demand_forecasting/district_metrics.csv")'),
    nbf.v4.new_code_cell('from IPython.display import Image, display\ndisplay(Image(filename=str(root / "reports/figures/demand_forecasting/validation_timeseries.png")))\ndisplay(Image(filename=str(root / "reports/figures/demand_forecasting/district_mae.png")))'),
    nbf.v4.new_markdown_cell('## Interpretation and remaining dependencies\nChoose the training window using validation, then agree on the shared team protocol before final testing. A longer history can include older reporting patterns and does not necessarily improve current forecasts. All values depend on the retained request sample and the fixed current district geography. Resolve source timezone and completeness, upstream coordinate exclusions, and team district-map approval before treating these as final results. The README documents sources and limitations. The literature review, personal interpretation, and official AI-use certificate require student completion and verification.')
]
nbf.write(book, folder / 'weekly_demand_forecasting.ipynb')
