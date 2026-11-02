"""Leakage-safe Member 2 features for the district-week demand panel.

The functions in this module are deliberately separate from model fitting.
They do not scale, impute, select features, train models, or write outputs.
Existing forecasting feature names keep their existing definitions.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


KEY_COLUMNS = ["district", "week_start"]
LAG_WEEKS = (1, 2, 4, 8)
ROLLING_WINDOWS = (4, 8, 13)
HISTORICAL_FEATURES = [
    "lag_1", "lag_2", "lag_4", "lag_8",
    "rolling_4", "rolling_8", "rolling_13",
    "rolling_std_4", "rolling_std_8", "recent_change_1_4",
]


def validate_weekly_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted copy after validating district-week continuity.

    A missing row in a weekly series is dangerous: ``shift(1)`` would then
    mean "previous available row" rather than "previous calendar week".
    This check detects that problem instead of silently creating a wrong lag.
    Missing target values are allowed so unknown coverage can remain missing.
    """
    required = set(KEY_COLUMNS + ["count"])
    missing = sorted(required - set(panel.columns))
    if missing:
        raise ValueError(f"Weekly panel is missing required columns: {missing}")

    result = panel.copy()
    result["week_start"] = pd.to_datetime(result["week_start"], errors="coerce")
    if result[KEY_COLUMNS].isna().any().any():
        raise ValueError("District and week_start keys cannot be missing or invalid")
    if result.duplicated(KEY_COLUMNS).any():
        raise ValueError("District-week keys must be unique")
    if not pd.api.types.is_numeric_dtype(result["count"]):
        result["count"] = pd.to_numeric(result["count"], errors="coerce")

    result = result.sort_values(KEY_COLUMNS).reset_index(drop=True)
    for district, group in result.groupby("district", sort=False):
        differences = group["week_start"].diff().dropna()
        if not differences.eq(pd.Timedelta(days=7)).all():
            raise ValueError(
                f"Weekly grid must be continuous within district {district}"
            )
    return result


def add_calendar_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add calendar features known at the start of the forecast week.

    ``sin_year`` and ``cos_year`` exactly preserve the formulas already used
    in ``src/demand_forecasting.py``. Together they describe annual position
    without treating late December and early January as far apart.
    """
    result = validate_weekly_panel(panel)
    result["month"] = result["week_start"].dt.month.astype("int8")
    result["week_of_year"] = (
        result["week_start"].dt.isocalendar().week.astype("int16")
    )
    phase = 2 * np.pi * result["week_start"].dt.dayofyear / 365.25
    result["sin_year"] = np.sin(phase)
    result["cos_year"] = np.cos(phase)
    return result


def add_historical_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add past-only lags, rolling statistics, and recent-demand change.

    Every calculation is grouped by district. Rolling windows first shift by
    one row, so the current week's target never enters its own predictors.
    Sample standard deviation (``ddof=1``) is used for rolling variability.
    """
    result = validate_weekly_panel(panel)
    grouped = result.groupby("district", sort=False)["count"]

    for lag in LAG_WEEKS:
        result[f"lag_{lag}"] = grouped.shift(lag)

    for window in ROLLING_WINDOWS:
        result[f"rolling_{window}"] = grouped.transform(
            lambda values: values.shift(1).rolling(
                window, min_periods=window
            ).mean()
        )

    for window in (4, 8):
        result[f"rolling_std_{window}"] = grouped.transform(
            lambda values: values.shift(1).rolling(
                window, min_periods=window
            ).std(ddof=1)
        )

    result["recent_change_1_4"] = result["lag_1"] - result["rolling_4"]
    return result


def add_forecasting_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add calendar and historical features while preserving keys/target."""
    return add_historical_features(add_calendar_features(panel))


def assign_development_splits(panel: pd.DataFrame) -> pd.DataFrame:
    """Label feature history, training, validation, and excluded edge weeks.

    Training scoring weeks are complete Monday-Sunday weeks in 2020-2023.
    Validation scoring weeks are complete Monday-Sunday weeks in 2024.
    Earlier weeks remain feature history. Weeks crossing a split boundary and
    non-Monday starts are retained but marked ineligible for scoring.
    """
    result = panel.copy()
    result["week_start"] = pd.to_datetime(result["week_start"], errors="coerce")
    if result["week_start"].isna().any():
        raise ValueError("week_start contains missing or invalid values")
    result["week_end"] = result["week_start"] + pd.Timedelta(days=6)
    monday = result["week_start"].dt.dayofweek.eq(0)

    result["development_split"] = "excluded_outside_development"
    history = monday & result["week_end"].lt(pd.Timestamp("2020-01-01"))
    train = (
        monday
        & result["week_start"].ge(pd.Timestamp("2020-01-01"))
        & result["week_end"].lt(pd.Timestamp("2024-01-01"))
    )
    validation = (
        monday
        & result["week_start"].ge(pd.Timestamp("2024-01-01"))
        & result["week_end"].lt(pd.Timestamp("2025-01-01"))
    )
    result.loc[history, "development_split"] = "feature_history"
    result.loc[train, "development_split"] = "train"
    result.loc[validation, "development_split"] = "validation"

    boundaries = [
        pd.Timestamp("2020-01-01"),
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2025-01-01"),
    ]
    crossing = pd.Series(False, index=result.index)
    for boundary in boundaries:
        crossing |= result["week_start"].lt(boundary) & result["week_end"].ge(boundary)
    result.loc[monday & crossing, "development_split"] = "excluded_split_crossing"
    result.loc[~monday, "development_split"] = "excluded_incomplete_week"
    result["is_scoring_eligible"] = result["development_split"].isin(
        ["train", "validation"]
    )
    return result


def build_shared_development_panel(
    data_path: str | Path,
    boundary_path: str | Path,
    *,
    preserve_team_zero_fill: bool = False,
) -> pd.DataFrame:
    """Reconstruct the existing 2018-2024 district-week target grid in memory.

    This mirrors the aggregation in ``demand_forecasting.run`` but does not
    call that writing/training function. The caller must explicitly allow the
    team's provisional zero-fill convention if any grid cells are unobserved.
    A Boolean column records exactly which rows, if any, were zero-filled.
    """
    data_path = Path(data_path)
    boundary_path = Path(boundary_path)
    if not data_path.exists() or not boundary_path.exists():
        raise FileNotFoundError("Cleaned data and local district boundary are required")

    raw = pd.read_csv(data_path, dtype={"request_id": "string"}, low_memory=False)
    raw["date_created"] = pd.to_datetime(raw["date_created"], errors="raise")
    if raw["request_id"].duplicated().any():
        raise ValueError("Duplicate request IDs are incompatible with the shared target")
    for column in ("latitude", "longitude"):
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    development = raw.loc[
        raw["date_created"].between("2018-01-01", "2024-12-31 23:59:59")
    ].copy()
    if not np.isfinite(development[["longitude", "latitude"]].to_numpy()).all():
        raise ValueError("Development requests contain missing or invalid coordinates")

    # Local import keeps the pure feature functions independent of model code.
    try:
        from demand_forecasting import assign_districts
    except ModuleNotFoundError:  # Support ``from src.eda_features import ...``.
        from src.demand_forecasting import assign_districts

    geojson = json.loads(boundary_path.read_text(encoding="utf-8"))
    mapped = assign_districts(development, geojson)
    usable = mapped.loc[mapped["location_matches"].eq(1)].copy()
    usable["week_start"] = (
        usable["date_created"].dt.normalize()
        - pd.to_timedelta(usable["date_created"].dt.dayofweek, unit="D")
    )

    weeks = pd.date_range("2018-01-01", "2024-12-23", freq="W-MON")
    districts = sorted(
        int(feature["properties"]["DISTRICT"])
        for feature in geojson["features"]
    )
    grid = pd.MultiIndex.from_product(
        [districts, weeks], names=["district", "week_start"]
    )
    observed = usable.groupby(KEY_COLUMNS).size().reindex(grid)
    zero_fill_mask = observed.isna()
    if zero_fill_mask.any() and not preserve_team_zero_fill:
        raise ValueError(
            "The shared grid has unobserved district-weeks. Set "
            "preserve_team_zero_fill=True only to reproduce the existing "
            "provisional forecasting convention."
        )

    counts = observed.fillna(0).astype("int64")
    panel = counts.rename("count").reset_index()
    panel["provisional_zero_filled"] = zero_fill_mask.to_numpy()
    panel["coverage_status"] = "assumed_complete_pending_team_confirmation"
    panel = validate_weekly_panel(panel)
    panel.attrs.update({
        "development_request_count": len(development),
        "uniquely_mapped_request_count": len(usable),
        "complete_week_target_count": int(counts.sum()),
        "split_crossing_request_count": int(len(usable) - counts.sum()),
        "provisional_zero_filled_rows": int(zero_fill_mask.sum()),
    })
    return panel
