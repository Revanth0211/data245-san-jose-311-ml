# Data sources and preparation

Abhijith Reddy’s [preparation pipeline](../src/data_preparation.py) downloads the annual files from the [San José 311 service request catalog](https://data.sanjoseca.gov/dataset/311-service-request-data), normalizes field names, identifies illegal-dumping service labels, and removes duplicate requests. The [cleaning guide](../notebooks/01_data_preparation/README.md) documents the fields and exclusion rules.

From the repository root:

```sh
python src/data_preparation.py --years 2018 2019 2020 2021 2022 2023 2024 2025
```

The pipeline stores annual downloads in `data/raw/` and writes the cleaned table, source manifest, data dictionary and audit files to `data/processed/`. The [cleaning summary](../results/member1_cleaning_summary.csv) is available for inspection without rebuilding the data.

## Geographic and weekly units

The [archived district map](reference/council_districts_snapshot.geojson) defines ten council districts. Forecast totals include requests that match exactly one district. Each target counts new requests during a complete Monday–Sunday week. Historical predictors use earlier completed weeks. The [frozen evaluation protocol](../config/final_evaluation_protocol.json) records the assumptions about coverage, zero filling, local timestamps and retrospective district boundaries.
