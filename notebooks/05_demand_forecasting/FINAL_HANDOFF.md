# Member 5 forecasting and final-evaluation handoff

## Completed contribution

The shared pipeline assigns cleaned requests to the archived districts, builds a continuous Monday–Sunday weekly panel, and creates district-specific past-count features. It implements previous-week and four-week-average reference forecasts and Poisson regression. All preprocessing is fitted on training rows. Current or future counts cannot change the current prediction's historical features.

The validation comparison now reconciles the saved outputs from all four modeling workstreams against identical district-week keys and targets. `python src/forecasting_summary.py` produces the combined table, district diagnostics, largest Poisson misses, and two scientific figures under `results/forecasting_presentation/` and `reports/figures/forecasting_presentation/`. It does not read the request-level source or score 2025.

## Recorded findings

| Configuration | 2024 MAE | 2024 RMSE |
|---|---:|---:|
| Previous week | 15.804 | 22.271 |
| Four-week average | 15.030 | 20.714 |
| Shared Poisson | **13.643** | **19.132** |
| Member 2 Poisson with lags | 13.852 | 19.482 |
| Random Forest without rolling features | 14.027 | 20.107 |
| XGBoost with Member 2 lag features | 13.942 | 20.195 |

All rows use the same 520 district-weeks in 2024. MAE and RMSE are reports per district-week. These configurations have different feature sets and were compared on validation data; this is a comparison of recorded experiments, not an isolated causal effect of algorithm choice. Small differences have not been tested for statistical significance. XGBoost figures refer to the saved Windows run; prior macOS review produced different scores. Its CSV predictions are rounded, so reconstructed metrics differ from the original full-precision metrics by less than 0.00001.

The shared Poisson model improves MAE by 9.23% relative to the four-week reference. Its mean signed error (prediction minus observation) is −3.452 reports per district-week. It improves district MAE in eight of ten districts; Districts 4 and 9 favor the four-week average. District 3 has the largest absolute Poisson error, while District 9 has the highest error relative to observed volume (WAPE). WAPE is `100 × sum(absolute error) / sum(observed counts)`; it is neither percentage accuracy nor a population adjustment.

A concrete large miss is District 3 in the week beginning July 29, 2024: observed 227 reports, Poisson prediction 123.414, absolute error 103.586. This identifies a forecasting limitation without establishing a cause for that week's volume.

Training from 2018 instead of 2020 gave Poisson MAE 13.843 versus 13.643 on the same validation rows. Earlier data remain available for feature history. The small validation difference supports the selected window for this experiment; it does not prove that older observations are generally harmful.

## Final evaluation: prepared, not executed

`config/final_evaluation_protocol.json` records the proposed final setup and six pending data decisions. The implementation supports the current conventions only. For each decision, record `confirmed` or `documented_assumption`, a decision explanation, evidence or a limitation, and the exact `adopted_convention` listed below. A documented assumption is acceptable when it is explicitly adopted and its limitation is disclosed; unsupported facts must not be marked verified.

| Decision | Owner | Supported adopted_convention |
|---|---|---|
| Source coverage and zero filling | Member 1 | `annual_exports_complete_for_zero_fill` |
| Timestamp handling | Member 1 | `naive_creation_timestamps_as_local_wall_clock` |
| Coordinate exclusions | Member 1 | `retain_current_cleaned_input_exclusions` |
| District geography | Member 2 | `fixed_archived_current_map_for_all_years` |
| GeoJSON coordinates | Member 2 | `saved_geojson_interpreted_as_longitude_latitude` |
| Nonunique district assignments | Member 2 | `exclude_nonunique_matches_from_district_counts` |

If a decision changes any convention, revise the implementation and regenerate the validation comparisons before freezing. If the cleaned data or boundary hash changes, the check rejects the previous input version. In particular, a known coverage gap cannot simply be accepted while continuing to zero-fill it as complete data.

Run from the repository root in the pinned forecasting environment:

```bash
python src/final_evaluation.py check
```

The check currently lists the pending decisions and exits with status 2. It does not aggregate or score 2025. After the decisions are recorded and the protocol is reviewed:

```bash
python src/final_evaluation.py freeze
python src/final_evaluation.py evaluate
```

Freezing records protocol, source-code, shared-code, dependency-file, cleaned-data and boundary hashes. Evaluation refuses changed locked inputs and creates an exclusive start marker to prevent an accidental repeat. If execution fails after that marker, preserve the files and investigate the failure before a documented recovery; do not delete the marker to tune against observed test outcomes.

### Proposed final protocol

- Select the shared Poisson configuration using 2024 validation; retain alpha 1, max_iter 2000 and tolerance 1e-8.
- Refit this chosen configuration on all complete weeks from 2020–2024 (2,600 district-weeks). Adding 2024 to the fit is a final refit after model selection, not the original validation training window.
- Evaluate January 6–December 22, 2025: 51 complete Monday–Sunday weeks × 10 districts = 510 district-weeks. Weeks beginning December 30, 2024 and December 29, 2025 cross calendar-year boundaries and are excluded from scoring.
- Preserve continuous history across the split. The December 30–January 5 completed week can supply a lag for the January 6 forecast, even though it is not a scored test week.
- Keep the fitted model fixed throughout the test. Counts from completed earlier test weeks may supply history for later predictions; this simulates sequential one-week-ahead forecasts, not a whole-year forecast made on January 1.
- Score Poisson and both reference forecasts on identical rows. Save predictions, pooled and district MAE/RMSE, geographic audit, software versions and hashes in `results/demand_forecasting_final/`.
- Do not choose new features, windows, models or hyperparameters after seeing 2025 scores. Any later exploratory change needs a separately identified evaluation.

## Presentation preparation

Explain the target, forecast timing and split before showing scores. Report units with MAE and RMSE. Show the baseline alongside the chosen model, give the district exceptions and a large miss, and distinguish recorded validation findings from pending test results. Present source coverage, timestamp and fixed-map choices as confirmed facts or documented assumptions according to the actual evidence.

The existing individual intermediate report remains a separate deliverable. Final report updates must use completed results only. Each member should understand their code and analysis and complete any course-required AI disclosure/certificate.

## Questions to rehearse

1. **What exactly is predicted?** The number of newly created illegal-dumping 311 reports per council district during the next complete week. Reports measure recorded demand and may differ from incident prevalence.
2. **Why abandon closure-duration tasks?** A separate reliable completion timestamp has not been established. Date Last Updated cannot supply valid closure labels without evidence about its meaning.
3. **What is one row?** One council district and one complete Monday–Sunday week, including a count of zero only under the documented coverage convention.
4. **Why use chronological splitting?** The intended use predicts future weeks from past information. Every district from a week stays in the same period.
5. **Can actual earlier validation weeks supply lags?** Yes. At each weekly forecast origin, those weeks are already complete. The current week and future weeks cannot enter the predictor values. The fitted coefficients remain fixed.
6. **What does MAE 13.643 mean?** The average absolute error across 520 validation district-weeks is approximately 13.6 reports. RMSE 19.132 gives larger misses more weight. Neither metric is a percentage accuracy.
7. **Why Poisson?** It produces a positive expected count using a log link and the shared predictors. Its observed validation error is lower than the saved alternatives. This alone does not prove that the counts satisfy equal mean and variance or that Poisson is universally best.
8. **Why not train from 2018?** We tested both windows on identical 2024 rows. The 2020 start had a 0.200 lower MAE. This is a validation comparison with a small difference, not a causal explanation. Earlier observations still support history construction.
9. **Why did more features or trees not win?** The saved experiments show that extra flexibility did not improve this validation comparison. Redundancy, regularization and changing patterns are possible explanations, not established causes.
10. **Is District 3 the worst in every sense?** It has the highest absolute Poisson MAE. Relative to observed volume, District 9 has the highest WAPE. Population-adjusted performance has not been established.
11. **What is still uncertain?** Coverage, timestamp semantics, coordinate handling and historical geography await recorded decisions. Source-system and reporting-behavior changes limit interpretation of trends.
12. **What happens before final testing?** Record the data decisions, regenerate validation if needed, freeze inputs and model settings, refit the selected configuration on 2020–2024, then run the reserved 2025 comparison once.
13. **Why are 2025 test rows 510 rather than 520?** Only 51 Monday–Sunday weeks lie entirely within calendar 2025. Boundary-crossing weeks remain history where needed but are not scored.
14. **Can the model allocate cleanup staff directly?** The experiment provides report-demand forecasts. An operational allocation would require staffing constraints, costs, reporting bias and service outcomes that this model has not evaluated.

## Evidence and reproduction

```bash
python -m unittest discover -s tests -v
python src/forecasting_summary.py
```

The final-evaluation end-to-end test uses synthetic records and synthetic geography assignments only. It does not inspect the real 2025 outcomes. Original teammate predictions and figures are kept in their existing directories.
