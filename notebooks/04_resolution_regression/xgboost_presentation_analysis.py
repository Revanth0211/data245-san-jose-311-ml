"""Member 4 presentation diagnostics from SAVED 2024 validation predictions.

No model fitting, shared-data regeneration, or 2025 test access occurs here.
Run from the repository root:
    python notebooks/04_resolution_regression/xgboost_presentation_analysis.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "results/member4_xgboost"
PRIMARY = "member2_lags"


def verify_close(actual: float, recorded: float, label: str) -> None:
    if not np.isclose(actual, recorded, rtol=0, atol=1e-5):
        raise ValueError(f"Saved-result mismatch for {label}: {actual} vs {recorded}")


def main(repo_root: Path, output_dir: Path, figure_dir: Path) -> None:
    source = repo_root / "results/member4_xgboost"
    predictions = pd.read_csv(source / "validation_predictions.csv")
    saved_metrics = pd.read_csv(source / "validation_metrics.csv")
    saved_districts = pd.read_csv(source / "district_metrics.csv")
    saved_busy = pd.read_csv(source / "busy_week_metrics.csv")
    manifest = json.loads((source / "run_manifest.json").read_text(encoding="utf-8"))

    if manifest.get("final_test_2025_accessed") is not False or manifest.get("test_evaluated") is not False:
        raise ValueError("Manifest does not confirm an untouched 2025 final test")
    if manifest.get("train_window") != "2020-2023" or manifest.get("validation") != "2024":
        raise ValueError("Training or validation window does not match the team protocol")
    if manifest.get("primary_analysis_experiment") != PRIMARY:
        raise ValueError("Saved primary experiment is not member2_lags")

    expected = {"shared", PRIMARY, "member2_full"}
    if set(predictions["experiment"]) != expected or set(saved_metrics["experiment"]) != expected:
        raise ValueError("Expected all three saved XGBoost experiments")
    predictions["week_start"] = pd.to_datetime(predictions["week_start"], errors="raise")
    if not predictions["week_start"].dt.year.eq(2024).all():
        raise ValueError("Only 2024 development validation predictions are allowed")
    if not predictions["week_start"].dt.dayofweek.eq(0).all():
        raise ValueError("All scored week starts must be Mondays")
    if predictions.duplicated(["experiment", "district", "week_start"]).any():
        raise ValueError("Duplicate experiment / district / week keys")

    key_sets = []
    for name in sorted(expected):
        rows = predictions.loc[predictions["experiment"].eq(name)].copy()
        if len(rows) != 520 or rows["week_start"].nunique() != 52 or rows["district"].nunique() != 10:
            raise ValueError(f"Unexpected 2024 coverage for {name}")
        if not rows.groupby("week_start")["district"].nunique().eq(10).all():
            raise ValueError(f"Missing council district on one or more weeks: {name}")
        key_sets.append(rows[["district", "week_start", "actual_count"]]
                        .sort_values(["week_start", "district"]).reset_index(drop=True))
        y = rows["actual_count"].to_numpy(dtype=float)
        yhat = rows["prediction"].to_numpy(dtype=float)
        error = yhat - y
        if not (np.isfinite(y).all() and np.isfinite(yhat).all()):
            raise ValueError("Non-finite target or prediction")
        if not (y >= 0).all() or not (yhat >= 0).all():
            raise ValueError("Negative report count or clipped prediction")
        if not np.allclose(rows["signed_error"], error, atol=1e-4, rtol=0):
            raise ValueError(f"Signed-error column inconsistent for {name}")
        if not np.allclose(rows["absolute_error"], np.abs(error), atol=1e-4, rtol=0):
            raise ValueError(f"Absolute-error column inconsistent for {name}")
        recorded = saved_metrics.set_index("experiment").loc[name]
        verify_close(np.abs(error).mean(), float(recorded["mae"]), f"{name} MAE")
        verify_close(np.sqrt(np.mean(error**2)), float(recorded["rmse"]), f"{name} RMSE")
        if int(recorded["validation_rows"]) != 520 or int(recorded["training_rows"]) != 2080:
            raise ValueError(f"Unexpected row counts for {name}")
    for other in key_sets[1:]:
        if not key_sets[0].equals(other):
            raise ValueError("XGBoost variants do not score the same district-week targets")

    primary = predictions.loc[predictions["experiment"].eq(PRIMARY)].copy()
    for district, group in primary.groupby("district"):
        recorded = saved_districts.loc[(saved_districts.experiment == PRIMARY)
                                       & (saved_districts.district == district)]
        if len(recorded) != 1:
            raise ValueError("Missing saved district metric")
        verify_close(group.absolute_error.mean(), float(recorded.iloc[0].mae), f"district {district} MAE")
    for busy, group in primary.groupby("busy_district_week"):
        recorded = saved_busy.loc[(saved_busy.experiment == PRIMARY)
                                  & (saved_busy.busy_district_week == busy)]
        if len(recorded) != 1:
            raise ValueError("Missing saved busy-week metric")
        verify_close(group.absolute_error.mean(), float(recorded.iloc[0].mae), f"busy={busy} MAE")
        verify_close(group.signed_error.mean(), float(recorded.iloc[0].mean_bias_prediction_minus_actual),
                     f"busy={busy} signed bias")

    team_path = repo_root / "results/demand_forecasting/validation_predictions.csv"
    team_check = "unavailable (team prediction file absent)"
    if team_path.is_file():
        team = pd.read_csv(team_path)
        poisson = team.loc[team.experiment.eq("poisson_2020")].copy()
        poisson["week_start"] = pd.to_datetime(poisson["week_start"], errors="raise")
        shared_keys = key_sets[0].rename(columns={"actual_count": "count"})
        team_keys = poisson[["district", "week_start", "count"]].sort_values(
            ["week_start", "district"]).reset_index(drop=True)
        if not shared_keys.equals(team_keys):
            raise ValueError("Saved XGBoost validation targets differ from team Poisson targets")
        team_check = "passed"

    top = primary.loc[primary.signed_error < 0].nsmallest(10, "signed_error").copy()
    top["week_start"] = top["week_start"].dt.strftime("%Y-%m-%d")
    cols = ["district", "week_start", "actual_count", "prediction", "absolute_error",
            "signed_error", "busy_district_week"]
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    top[cols].to_csv(output_dir / "largest_underpredictions.csv", index=False,
                     float_format="%.6f")

    # Descriptive presentation chart only; existing figures remain untouched.
    chart = top.head(5).iloc[::-1]
    labels = [f"D{int(r.district)} | {r.week_start}" for r in chart.itertuples()]
    positions = np.arange(len(chart))
    fig, ax = plt.subplots(figsize=(9.8, 4.4))
    ax.barh(positions - 0.18, chart.actual_count, height=0.36, label="Observed reports")
    ax.barh(positions + 0.18, chart.prediction, height=0.36, label="XGBoost forecast")
    ax.set_yticks(positions, labels)
    ax.set_xlabel("Weekly reported illegal-dumping requests")
    ax.set_title("Five largest underpredictions — 2024 validation (member2_lags)")
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(figure_dir / "largest_underpredictions.png", dpi=220)
    plt.close(fig)

    district_stats = primary.groupby("district").absolute_error.mean().sort_values(ascending=False)
    busy_stats = primary.groupby("busy_district_week").absolute_error.agg(["size", "mean"])
    worst = top.iloc[0]
    print("2024 validation: 520 district-weeks, 52 Mondays x 10 districts; 2025 not accessed")
    print(f"Saved XGBoost metrics and subgroup checks: PASSED; team row alignment: {team_check}")
    print(saved_metrics[["experiment", "mae", "rmse"]].to_string(index=False))
    print(f"Highest district MAE: District {int(district_stats.index[0])}, {district_stats.iloc[0]:.2f}")
    print(f"Busy district-weeks: {int(busy_stats.loc[True, 'size'])}, MAE {busy_stats.loc[True, 'mean']:.2f}; "
          f"nonbusy: {int(busy_stats.loc[False, 'size'])}, MAE {busy_stats.loc[False, 'mean']:.2f}")
    print(f"Largest underprediction: D{int(worst.district)} | {worst.week_start}; "
          f"observed {int(worst.actual_count)}, forecast {worst.prediction:.2f}, "
          f"under by {-worst.signed_error:.2f}")
    print(f"Created: {output_dir / 'largest_underpredictions.csv'}")
    print(f"Created: {figure_dir / 'largest_underpredictions.png'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--figure-dir", type=Path, default=None)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    main(root, args.output_dir or root / "results/member4_presentation",
         args.figure_dir or root / "reports/figures/member4_presentation")
