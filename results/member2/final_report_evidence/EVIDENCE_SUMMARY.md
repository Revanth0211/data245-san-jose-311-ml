# Member 2 final-report evidence (2024 validation only)

Generated on 2026-11-20 by Haritha Gottumukkala (Member 2). It covers only Member 2's
work: the controlled Poisson feature comparison (Groups A, B, C) and the 22 Member 2
unit tests.

**Scope guardrails.**
- All results are **2024 validation results**. The **2025 test targets were not accessed**.
  The script reads only the saved Member 2 prediction and metrics files. It stops if any
  row falls outside 2024.
- No model was trained, refit or tuned. Every number below comes from the saved
  predictions in `results/member2/feature_comparison_predictions.csv`.
- No existing project file was changed. Every new file is in this folder.

## Inputs used

| File | Use |
|---|---|
| `results/member2/feature_comparison_predictions.csv` | Saved predictions. Columns: `experiment, district, week_start, actual_count, prediction`. 1,560 rows (3 groups × 520). |
| `results/member2/feature_comparison_metrics.csv` | Saved MAE and RMSE, used only for the cross-check. |
| `tests/test_eda_features.py`, `tests/test_feature_comparison.py` | The 22 Member 2 unit tests. |

## Outputs generated (this folder)

| File | Content |
|---|---|
| `generate_evidence.py` | Script that creates every CSV and PNG below. |
| `run_member2_tests.py` | Script that runs the 22 Member 2 tests and writes the log. |
| `member2_input_checks.csv` | Row counts, key and target identity checks, 2024-only check. |
| `member2_additional_metrics_2024_validation.csv` | Overall MAE, RMSE, WAPE, mean error, mean Poisson deviance and R² for A/B/C, plus the saved-value cross-check. |
| `member2_district_metrics_2024_validation.csv` | 30 rows (10 districts × 3 groups): weeks, MAE, RMSE, mean error, WAPE, actual mean, predicted mean. |
| `member2_largest_error_districts_2024_validation.csv` | The 3 districts with the highest MAE in each group. |
| `member2_groupB_top10_absolute_errors.csv` | The 10 largest Group B absolute errors. |
| `member2_district3_2024-07-29_all_groups.csv` | District 3, week of 2024-07-29, for A/B/C. |
| `member2_groupB_high_demand_error_summary.csv` | Group B errors in high-demand district-weeks vs all other district-weeks. |
| `fig_district_mae_by_group.png`, `fig_district_rmse_by_group.png` | District-wise MAE and RMSE bar charts (300 dpi). |
| `fig_groupB_actual_vs_predicted.png` | Group B actual vs predicted scatter (300 dpi). |
| `fig_groupB_error_vs_relative_demand.png` | Group B signed error vs relative demand (300 dpi). |
| `member2_test_execution_log.txt` | Full log of the Member 2 test run. |

## Evaluation set

- **Weeks:** Monday week starts from 2024-01-01 to 2024-12-23 (52 complete weeks).
- **Size:** 10 districts × 52 weeks = **520 district-weeks** per group. The keys and
  actual counts are identical across A, B and C, and no key is duplicated within a group.
- **Zero counts:** no actual count is zero. All predictions are strictly positive, so the
  Poisson deviance is defined.

## Metric definitions

Here *y* is the actual count, *ŷ* the prediction, and *n* = 520.

- **MAE** = mean |ŷ − y|.
- **RMSE** = sqrt(mean (ŷ − y)²).
- **WAPE** = 100 × Σ|ŷ − y| / Σy. It is the total absolute error as a percentage of
  total reports, and it is defined because Σy > 0. Ordinary MAPE was not used.
- **Mean error (bias)** = mean (ŷ − y). A negative value means the model
  under-predicts on average.
- **Mean Poisson deviance** = mean of 2[y·ln(y/ŷ) − (y − ŷ)] (scikit-learn
  `mean_poisson_deviance`). It is the loss that matches a Poisson count model; lower is
  better.
- **R²** (supplementary only) = 1 − Σ(y − ŷ)² / Σ(y − ȳ)².
  - It is computed on all 520 district-weeks pooled together.
  - Much of that variance comes from fixed level differences between districts
    (District 3 averages about 132 reports a week, District 9 about 20). R² can
    therefore look good even when week-to-week errors inside a district are large.
  - It is not a count-specific measure, and it says nothing about direction of error or
    busy-week misses. It should not be the main metric.

## Main findings

1. **The recomputed MAE and RMSE match the saved values exactly.** The tolerance was
   1e-9, and the original results are unchanged.

   | Group | MAE | RMSE | WAPE % | Mean error | Mean Poisson deviance | R² |
   |---|---:|---:|---:|---:|---:|---:|
   | A: calendar | 17.861 | 24.532 | 31.25 | −7.291 | 9.414 | 0.529 |
   | B: + lags | 13.852 | 19.482 | 24.24 | −3.816 | 5.779 | 0.703 |
   | C: + lags + rolling | 14.131 | 19.781 | 24.72 | −2.538 | 5.760 | 0.694 |

2. **Comparing B and C depends on the metric.**
   - B is better on MAE, RMSE, WAPE and R².
   - C is very slightly better on mean Poisson deviance (5.760 vs 5.779) and has a
     smaller average bias.
   - All three groups under-predict on average.
3. **District results.**
   - B has a lower MAE than A in 9 of 10 districts. District 2 is the exception
     (15.73 vs 15.34).
   - C has a lower MAE than B in 5 districts (1, 2, 6, 7, 9).
   - District 3 alone adds 155.6 to C's total absolute error. That is more than C's whole
     overall gap to B (145.2). So C's overall loss mostly comes from one district.
4. **District 3 has the largest MAE in every group** (A 40.90, B 27.55, C 30.55). It also
   has by far the highest weekly volume, and its WAPE under B (20.8%) is among the
   lowest. Group A over-predicts District 9 heavily (mean error +24.2, WAPE 120%). The
   lag features largely fix this (Group B: +6.9).
5. **District 3, week of 2024-07-29** (actual 227 reports):
   - Group A: predicted 104.9, signed error −122.1.
   - Group B: predicted 119.0, signed error −108.0.
   - Group C: predicted 138.2, signed error −88.8.
   - This is the largest Group B error of 2024: about 7.8 times B's MAE. It is also the
     largest error for A and the second largest for C.
6. **Large errors are concentrated in weeks that are unusually high for their district.**
   - *Definition:* a high-demand district-week is one where the actual count is above that
     district's own 2024 90th percentile. There are 58 such district-weeks.
   - In those weeks, Group B has MAE 31.9, against 11.6 in the other 462.
   - Every one of the 58 was under-predicted.
   - 7 of the 10 largest Group B errors fall in these weeks. They hold 25.7% of total
     absolute error while being 11.2% of rows.
   - Signed error is strongly negatively related to demand relative to the district mean
     (Spearman −0.815). The model under-predicts unusually high weeks and over-predicts
     unusually low weeks, so its forecasts are pulled toward each district's recent level.
   - This describes how the errors are distributed. It does not explain why demand rose in
     those weeks; the saved data contain no event information.

## Unit-test execution

- **Command:**
  `PYTHONDONTWRITEBYTECODE=1 python -m unittest -v tests/test_eda_features.py tests/test_feature_comparison.py`
  (run through `run_member2_tests.py`).
- **Environment:** Python 3.11.15 with numpy 1.26.4, pandas 2.3.3, scikit-learn 1.6.1,
  scipy 1.17.1, shapely 2.0.7 and matplotlib 3.9.4.
- **Result:** 22 tests run (12 + 10): **22 passed, 0 failed, 0 errors**. The output ends
  with "OK". The full output, date and time are in `member2_test_execution_log.txt`.
- **Not run:** the team's 3 tests in `tests/test_demand_forecasting.py` (Member 5), so
  they are not counted.
- **What the tests do:** they use synthetic panels. `test_feature_comparison.py` fits
  small Poisson models on its synthetic panel. No real project data and no 2025 targets
  are used.

## Limitations

- **One validation year.** These are 2024 results, with no significance tests or
  prediction intervals.
- **WAPE and R² pool all districts,** so they are dominated by high-volume districts.
- **The high-demand definition is post hoc.** It uses 2024 actual counts, so it describes
  the errors and cannot serve as an advance warning rule. The 90th-percentile cut-off is
  one reasonable choice, not a tuned threshold.
- **Some figures are interpretive.** District-level figures (52 weeks each) and single
  weeks such as 2024-07-29 are noisy and should not be over-interpreted.
- **Assumptions still unapproved.** All results carry the saved status
  `provisional_pending_geography_and_coverage_approval`.

## Reproduce

From the repository root, using an environment with the pinned packages in
`requirements-forecasting.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python results/member2/final_report_evidence/generate_evidence.py
PYTHONDONTWRITEBYTECODE=1 python results/member2/final_report_evidence/run_member2_tests.py
```
