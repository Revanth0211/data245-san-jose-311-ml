# District-map verification

**Contributor:** Haritha Gottumukkala

## Scope

This verification checks the existing local San José council-district snapshot against the cleaned 2018–2024 illegal-dumping requests. It reuses the forecasting team's district-assignment function but does not change the map, coordinates, assignments, forecasting pipeline, or teammate results. It does not use 2025 records.

The executable evidence is in `01_district_map_verification.ipynb`. Counts in this document are results calculated from the committed local data, not estimates.

## Map source and version

- Documented source: City of San José ArcGIS feature layer `PLN_AdministrativeBoundaries/MapServer/1`.
- Source URL: <https://geo.sanjoseca.gov/server/rest/services/PLN/PLN_AdministrativeBoundaries/MapServer/1>
- Local geometry: `data/reference/council_districts_snapshot.geojson`.
- Local metadata: `data/reference/council_districts_metadata.json`.
- Boundary SHA-256: `29ba080e546a747541716349e4c0620923a751322ea37a153646f4005ea31430`.
- Metadata layer name: **City Council Districts (Current)**.
- Metadata description: the layer represents the 2021 council districts, effective February 11, 2022, and may receive later annexation or city-boundary updates.

The local file is a frozen snapshot of that current service. It is not evidence of the boundaries that legally applied in each historical request year.

## Coordinate reference interpretation

The ArcGIS metadata reports native WKID 102643 and latest WKID 2227, with map units in feet. The saved GeoJSON has no explicit `crs` member. Its coordinates are in plausible San José longitude/latitude ranges, and the forecasting implementation creates points as `(longitude, latitude)`.

This makes longitude/latitude usage internally consistent and technically reproducible. The precise GeoJSON export transformation remains **unresolved** because the export query, acquisition timestamp, and requested output CRS are not recorded in the repository.

## Reproducible checks

The notebook performs these checks:

1. Confirms all required local files exist.
2. Records cleaned-data and map SHA-256 hashes.
3. Requires exactly one map feature for every district from 1 through 10.
4. Checks that each geometry is a non-empty valid `Polygon` or `MultiPolygon`.
5. Parses creation dates and coordinates with explicit failure behavior.
6. Excludes 2025 before spatial assignment.
7. Calls `assign_districts()` from `src/demand_forecasting.py` without modifying it.
8. Recomputes total, uniquely assigned, unmatched, and multiple-match counts.
9. Reconciles the year-by-year result against `results/demand_forecasting/location_audit.csv`.
10. Summarizes unmatched points by year, nearest district, map distance, and overall bounding-box position without correcting them.
11. Screens for exact multiple matches and points close to district boundaries.
12. Displays a deterministic sample of matched points plus all unmatched points over the district polygons.

## Verified results

| Check | Result | Status |
| --- | ---: | --- |
| Cleaned requests dated 2018–2024 | 181,326 | Verified |
| Uniquely assigned requests | 180,863 | Verified |
| Unmatched requests | 463 | Verified |
| Requests matching multiple districts | 0 | Verified |
| 2025 requests used | 0 | Verified |
| District identifiers | 1–10 exactly | Verified |
| Empty or invalid district geometries | 0 | Verified |
| Recomputed annual audit vs committed audit | Exact match | Verified |

An unmatched request is not automatically a data error. Possible explanations include a point just outside the city boundary, coordinate imprecision, annexation or boundary-version differences, or a source coordinate problem that passed the broad upstream plausibility bounds. No unmatched request is deleted, corrected, or forced into a district by this work.

The descriptive unmatched-point screening found:

- 459 of 463 unmatched points lie inside the overall rectangular bounding box of the district map. A bounding box is only the outer rectangle around the map, so this does not mean those points fall inside a district.
- 170 unmatched points are within 0.0001 angular degrees of the saved district union.
- 365 unmatched points are within 0.001 angular degrees of the saved district union.
- The median distance to the saved map is 0.000207 angular degrees; the maximum is 0.076656 angular degrees.

These are angular GeoJSON distances, not verified meter distances. They are useful for screening but must not be presented as physical distance until the GeoJSON export CRS is confirmed.

Likewise, a point close to a boundary is a sensitivity flag, not proof of an incorrect assignment. The exact assignment produced no multiple matches in the current data.

Among uniquely assigned requests, 909 are within 0.00001 angular degrees of at least one district boundary and 4,120 are within 0.0001 angular degrees. None is exactly on a boundary at the notebook's numerical tolerance, and there are no exact multiple matches. These proximity counts identify potentially boundary-sensitive records; they do not invalidate their current assignments.

## Historical limitation

Applying the same map to 2018–2024 creates a consistent **retrospective fixed-geography analysis**. It does not reconstruct the district that governed an address when an older request was created. This distinction matters for comparisons before the 2021 redistricting took effect and for areas affected by later boundary updates.

The map should therefore be described as provisional until the team explicitly agrees that fixed current geography matches the project question.

## Status summary

### Verified

- Local map structure, district identifiers, geometry types, and geometry validity.
- Internal longitude/latitude ordering used by the existing pipeline.
- Exact reproduction of the forecasting location audit on actual 2018–2024 cleaned data.
- Preservation and descriptive investigation of all 463 unmatched records.
- No 2025 use.

### Provisional

- Treating the GeoJSON as longitude/latitude coordinates based on coordinate ranges and current code behavior.
- Using one 2021/current boundary snapshot as a fixed analytical geography for all years.

### Unresolved / teammate confirmation required

- Exact map snapshot acquisition date and GeoJSON export query/output CRS.
- Team approval of retrospective fixed geography.
- Whether official historical boundary layers should be used for a separate sensitivity analysis.
- Review criteria for unmatched and near-boundary points.
- Independent known-address checks against an official district lookup.

## Reproduction

From the repository root, execute the notebook with the project Python 3.11 environment. Notebook assertions stop execution if the current data no longer matches the documented map structure or assignment counts.

This workflow does not run forecasting models and does not write into teammate result directories.
