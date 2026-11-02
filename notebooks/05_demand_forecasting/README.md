# Revanth: weekly demand forecasting

This component implements the intermediate technical milestone: a shared district-week development table, past-only count features, previous-week and four-week-average baselines, Poisson regression, and district-level validation errors. Results are **provisional**, not a declaration that the source coverage and geography have been approved.

## Reproduce

From the repository root, create a Python environment and install `requirements-forecasting.txt`. Run:

```sh
python -m unittest discover -s tests -v
python src/demand_forecasting.py
```

Input: `data/processed/illegal_dumping_cleaned.csv` from Member 1's merged PR. The archived official geometry and metadata are in `data/reference/`. The run manifest records input and geometry SHA-256 hashes. Generated weekly data and unmatched request IDs remain in ignored `data/processed/`; small metric tables and figures are in `results/demand_forecasting/` and `reports/figures/demand_forecasting/`.

## Target and forecast protocol

The target is the number of retained, uniquely mapped illegal-dumping reports created in each district during a complete Monday–Sunday week. This measures reported demand, not the true number of dumping incidents. Requests excluded upstream or outside the archived polygons are not counted; inspect `location_audit.csv` before interpretation.

At the start of each week, predict that week's count using actual counts from already completed weeks. The fitted model remains fixed throughout 2024. This is rolling one-week-ahead evaluation, not a forecast of all of 2024 made in January. No current-week status, update timestamp, or future count is used as a feature.

Features: district identity, counts from 1, 2, and 4 weeks earlier, shifted 4- and 13-week means, and sine/cosine annual calendar terms. Lags are computed independently within districts on a continuous weekly grid. The first 13 weeks are warm-up history and cannot be scored. Historical 2018–2019 observations can supply lag history for the 2020 training-window experiment.

## Evaluation agreement

Compare training starts of 2018 and 2020, ending in 2023, on exactly the same 2024 validation district-weeks. Every district for a week stays in the same split. Scaling and district encoding are fitted on training rows only. The Poisson model uses fixed alpha=1; no hyperparameter search has been performed. Both baselines are evaluated on the identical rows. MAE and RMSE are in requests per district-week; the plotted citywide totals are descriptive, not the pooled district-level metric.

The latest validation week starts December 23, 2024. The week beginning December 30 crosses into the reserved test year and is excluded. **2025 has not been evaluated**. Freeze the shared data version, protocol, training-window choice, and model settings before implementing the final test. For the final test, exclude incomplete edge weeks; preserve continuous history for feature construction. The current implementation deliberately stops at validation.

## Dependencies and limitations

### Measured provisional results

Across 520 validation district-weeks, previous-week MAE/RMSE are 15.804/22.271; four-week-average MAE/RMSE are 15.030/20.714. Poisson trained from 2018 achieves 13.843/19.415, while Poisson trained from 2020 achieves 13.643/19.132. The latter reduces MAE by approximately 9.23% relative to the four-week baseline. The difference between training windows is small (about 0.20 requests in MAE), so this is evidence for the existing 2020 start in this experiment, not a universal rule to discard older history. Both charts compare the two baselines with the 2020-start Poisson experiment.

Of 181,326 cleaned development-period requests, 180,863 map uniquely to the archived districts; 463 fall outside all polygons and are excluded from district counts. No multiple matches occurred. Upstream exclusions are additional. These geography exclusions and the unconfirmed coverage assumptions limit interpretation.

The first execution exposed numerical warnings with NumPy 2.0.2 on this machine. The pinned NumPy 1.26.4 environment reproduced the same scores with runtime warnings treated as errors. Leakage tests and fresh-kernel notebook execution are part of the verification.

- Member 1 must confirm timestamp semantics. For this provisional run, naive creation timestamps are treated as San Jose local wall-clock times; no unsupported UTC conversion is applied.
- Annual export completeness is an assumption. Prior review found all calendar days represented in the raw 2018–2025 exports, but that does not prove every reporting channel was complete. Zero-filled district-weeks require team confirmation; known gaps must become missing coverage, not zero demand.
- Members 1 and 2 must agree on the district map. The official snapshot is a current layer based on the 2021 redistricting with subsequent updates. Applying it consistently to old records gives retrospective fixed geography, not historical administrative districts or a strictly historical deployment simulation. Do not use population or officeholder attributes as model features.
- Member 1's 1,071 coordinate exclusions are retained. Prior review identified 783 excluded records with potentially sign-flipped longitude; corrections require a documented source decision and a rerun by all members.
- Model scores are observational validation estimates. A longer training history is not automatically better; compare the two windows and discuss temporal changes. Keep the common team split consistent after choosing.
- A Poisson mean model does not guarantee calibrated prediction intervals. None are supplied. Request counts may be overdispersed and correlated over time.

## AI use and student review

AI assistance was used to draft the forecasting implementation, tests, explanations, and experiment workflow. Revanth must inspect and understand the code, verify assumptions with teammates, interpret the results, and acknowledge assistance according to the course's certificate requirements. This note is not an official certificate and does not claim completion of any required training.

The individual literature review (at least 13 papers in the repository plan), personal progress narrative, instructor certificate, and teammate review remain separate deliverables. Do not claim to have read papers or personally performed analysis that you have not reviewed.

## Sources

- City 311 data: https://data.sanjoseca.gov/dataset/311-service-request-data
- Official district layer: https://geo.sanjoseca.gov/server/rest/services/PLN/PLN_AdministrativeBoundaries/MapServer/1
- Poisson model reference: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.PoissonRegressor.html
