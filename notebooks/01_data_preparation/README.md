# Member 1 — Data preparation

Run the reproducible pipeline from the repository root:

```bash
python src/data_preparation.py --years 2017 2018 2019 2020 2021 2022 2023 2024 2025
```

The pipeline uses the official City of San José Open Data CKAN API, downloads annual 311 files into `data/raw/`, and writes generated outputs to `data/processed/`.

## Cleaning decisions

- Annual files are combined after mapping year-specific headers to a canonical schema.
- A row is classified as illegal dumping when `Service Type` or `Category` contains `Illegal Dumping` or `Illegal Dump`, case-insensitively.
- Records with missing request IDs or invalid creation timestamps are excluded because they cannot be reliably identified or placed in time.
- Coordinates are retained when missing, but implausible coordinates are excluded; missing-coordinate counts remain in the audit.
- Exact duplicate rows and repeated request IDs are removed, keeping the first occurrence after chronological sorting.
- `Date Last Updated` is retained as an update field and is not interpreted as a completion date.
- Category/service labels are preserved for audit, while the cleaned handoff uses the canonical `Illegal Dumping` service label.

## Evidence files

- `source_manifest.csv`: source URL, access time, checksum, row counts, and coverage/missingness audit.
- `cleaning_counts.csv`: records retained and excluded at each stage.
- `data_dictionary.csv`: canonical fields and cleaning rules.
- `illegal_dumping_audit_rows.csv`: filtered rows with exclusion reasons.
- `illegal_dumping_cleaned.csv`: final handoff dataset for Members 2–5.
