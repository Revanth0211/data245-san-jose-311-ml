# Data handoff

Put unchanged source downloads in `data/raw/` and generated cleaned tables in `data/processed/`. These directories are ignored by Git. Add reproducible download/cleaning instructions here when sources are acquired.

For each source, record its URL, access date, year/period, local filename, checksum where available, source row count, illegal-dumping row count, and known schema or coverage issues. Record the archived district boundary version too.

## Early sample for shared development

Agree on canonical column names before implementation. The initial handoff should provide:

| Field | Requirement |
| --- | --- |
| Request ID | Identifier and documented duplicate-handling rules. |
| Creation date/time | Parsed value with documented timezone and invalid/missing-date handling. |
| Illegal-dumping category | Documented source labels and mappings across years. |
| Council district | Consistent district assignment, or usable coordinates for shared assignment. |
| Coverage notes | Periods/files known to be complete, missing, or affected by reporting gaps. |
| Completion date/time | Optional, only if the field reliably establishes completion; explain its meaning and follow-up rules. |

Keep requests with different IDs as separate reports unless there is evidence they are duplicates. Track missing/invalid locations and their effect on usable coverage.

## Weekly forecasting table

Each row will represent a district and the start of a complete Monday–Sunday forecast week. The target is the number of newly created illegal-dumping reports in that week. Historical lags and rolling averages use completed earlier weeks only. Zero counts require verified source coverage.

The source manifest, final schema, download instructions, and cleaning decisions are pending the data audit.
