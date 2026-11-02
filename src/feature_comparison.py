"""Controlled Member 2 feature-ablation experiment.

This module fixes the model, preprocessing, rows, and target while changing
only the numeric feature group. It does not read 2025 evaluation rows or write
results. Callers must explicitly acknowledge provisional geography and source
coverage assumptions before fitting.
"""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from eda_features import assign_development_splits
    from demand_forecasting import metrics as forecasting_metrics
except ModuleNotFoundError:  # Support package-style imports from repository root.
    from src.eda_features import assign_development_splits
    from src.demand_forecasting import metrics as forecasting_metrics


BASIC_NUMERIC = ["month", "week_of_year", "sin_year", "cos_year"]
LAG_NUMERIC = ["lag_1", "lag_2", "lag_4", "lag_8"]
ROLLING_NUMERIC = [
    "rolling_4", "rolling_8", "rolling_13",
    "rolling_std_4", "rolling_std_8", "recent_change_1_4",
]
FEATURE_GROUPS = {
    "A_basic": BASIC_NUMERIC,
    "B_basic_lags": BASIC_NUMERIC + LAG_NUMERIC,
    "C_basic_lags_rolling": BASIC_NUMERIC + LAG_NUMERIC + ROLLING_NUMERIC,
}
MODEL_CONFIGURATION = "PoissonRegressor(alpha=1.0,max_iter=2000,tol=1e-8)"


@dataclass
class ComparisonResult:
    metrics: pd.DataFrame
    predictions: pd.DataFrame
    models: dict[str, object]
    training_keys: dict[str, pd.DataFrame]
    validation_keys: dict[str, pd.DataFrame]
    training_frame: pd.DataFrame
    validation_frame: pd.DataFrame


def _finite_or_raise(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    values = frame[columns].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{label} contains missing or infinite numeric values")


def select_common_evaluation_rows(featured_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select one common 2020-2023 train frame and one 2024 validation frame."""
    required = {
        "district", "week_start", "count",
        *[feature for group in FEATURE_GROUPS.values() for feature in group],
    }
    missing = sorted(required - set(featured_panel.columns))
    if missing:
        raise ValueError(f"Featured panel is missing required columns: {missing}")

    panel = assign_development_splits(featured_panel)
    if panel["week_start"].dt.year.ge(2025).any():
        raise ValueError("2025 rows are not allowed in development model evaluation")

    train = panel.loc[panel["development_split"].eq("train")].copy()
    validation = panel.loc[panel["development_split"].eq("validation")].copy()
    train = train.sort_values(["week_start", "district"]).reset_index(drop=True)
    validation = validation.sort_values(["week_start", "district"]).reset_index(drop=True)

    all_numeric = list(dict.fromkeys(
        [feature for group in FEATURE_GROUPS.values() for feature in group]
    ))
    _finite_or_raise(train, all_numeric + ["count"], "Training rows")
    _finite_or_raise(validation, all_numeric + ["count"], "Validation rows")
    if train.duplicated(["district", "week_start"]).any():
        raise ValueError("Training district-week keys are not unique")
    if validation.duplicated(["district", "week_start"]).any():
        raise ValueError("Validation district-week keys are not unique")
    return train, validation


def make_poisson_pipeline(numeric_features: list[str]):
    """Return the exact teammate preprocessing/model configuration."""
    preprocessing = ColumnTransformer([
        (
            "district",
            OneHotEncoder(handle_unknown="error", sparse_output=False),
            ["district"],
        ),
        ("numeric", StandardScaler(), numeric_features),
    ])
    return make_pipeline(
        preprocessing,
        PoissonRegressor(alpha=1.0, max_iter=2000, tol=1e-8),
    )


def run_feature_comparison(
    featured_panel: pd.DataFrame,
    *,
    accept_provisional_geography: bool = False,
    accept_provisional_coverage: bool = False,
) -> ComparisonResult:
    """Fit the three predeclared groups on identical rows and return results."""
    if not accept_provisional_geography:
        raise ValueError("Explicit acceptance of provisional fixed geography is required")
    if not accept_provisional_coverage:
        raise ValueError("Explicit acceptance of provisional source coverage is required")

    train, validation = select_common_evaluation_rows(featured_panel)
    key_columns = ["district", "week_start"]
    metrics_rows = []
    prediction_frames = []
    models = {}
    training_keys = {}
    validation_keys = {}

    for experiment, numeric_features in FEATURE_GROUPS.items():
        inputs = ["district"] + numeric_features
        model = make_poisson_pipeline(numeric_features)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(train[inputs], train["count"])
        predicted = model.predict(validation[inputs])
        if not np.isfinite(predicted).all():
            raise ValueError(f"{experiment} produced non-finite predictions")
        if (predicted < 0).any():
            raise ValueError(f"{experiment} produced negative count predictions")

        score = forecasting_metrics(validation["count"], predicted)
        metrics_rows.append({
            "experiment": experiment,
            "numeric_feature_count": len(numeric_features),
            "total_model_inputs": len(inputs),
            "train_rows": len(train),
            "validation_rows": len(validation),
            **score,
        })
        output = validation[key_columns + ["count"]].copy()
        output = output.rename(columns={"count": "actual_count"})
        output["prediction"] = predicted
        output.insert(0, "experiment", experiment)
        prediction_frames.append(output)
        models[experiment] = model
        training_keys[experiment] = train[key_columns].copy()
        validation_keys[experiment] = validation[key_columns].copy()

    metrics_table = pd.DataFrame(metrics_rows)
    basic = metrics_table.loc[metrics_table["experiment"].eq("A_basic")].iloc[0]
    metrics_table["mae_change_vs_basic"] = metrics_table["mae"] - basic["mae"]
    metrics_table["mae_improvement_percent_vs_basic"] = (
        100 * (basic["mae"] - metrics_table["mae"]) / basic["mae"]
    )
    metrics_table["rmse_change_vs_basic"] = metrics_table["rmse"] - basic["rmse"]
    metrics_table["rmse_improvement_percent_vs_basic"] = (
        100 * (basic["rmse"] - metrics_table["rmse"]) / basic["rmse"]
    )
    predictions = pd.concat(prediction_frames, ignore_index=True)
    return ComparisonResult(
        metrics=metrics_table,
        predictions=predictions,
        models=models,
        training_keys=training_keys,
        validation_keys=validation_keys,
        training_frame=train,
        validation_frame=validation,
    )
