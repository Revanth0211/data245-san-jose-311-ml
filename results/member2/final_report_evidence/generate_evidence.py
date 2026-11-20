"""Member 2 final-report evidence from saved 2024 validation predictions.

Reads only two existing Member 2 files:
  results/member2/feature_comparison_predictions.csv
  results/member2/feature_comparison_metrics.csv

It does not train, refit, or tune any model, and it does not read any other
data file. Every output is written to results/member2/final_report_evidence/.
The script stops with an error if an input check fails or if the recomputed
MAE/RMSE differ from the saved metrics.

Run from the repository root:
  python results/member2/final_report_evidence/generate_evidence.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_poisson_deviance, r2_score

ROOT = Path(__file__).resolve().parents[3]
PRED_PATH = ROOT / "results/member2/feature_comparison_predictions.csv"
METRICS_PATH = ROOT / "results/member2/feature_comparison_metrics.csv"
OUT = Path(__file__).resolve().parent

GROUPS = ["A_basic", "B_basic_lags", "C_basic_lags_rolling"]
LABELS = {
    "A_basic": "A: calendar",
    "B_basic_lags": "B: calendar + lags",
    "C_basic_lags_rolling": "C: calendar + lags + rolling",
}
COLORS = {"A_basic": "#9e9e9e", "B_basic_lags": "#1f77b4", "C_basic_lags_rolling": "#ff7f0e"}
KEYS = ["district", "week_start"]
TOLERANCE = 1e-9
HIGH_DEMAND_QUANTILE = 0.90


def fail(message: str) -> None:
    print(f"CHECK FAILED: {message}")
    sys.exit(1)


def error_metrics(actual: pd.Series, predicted: pd.Series) -> dict:
    error = predicted - actual
    total_actual = actual.sum()
    return {
        "n": int(len(actual)),
        "mae": float(error.abs().mean()),
        "rmse": float(np.sqrt((error ** 2).mean())),
        "wape_percent": float(100 * error.abs().sum() / total_actual) if total_actual > 0 else np.nan,
        "mean_error": float(error.mean()),
        "actual_mean": float(actual.mean()),
        "predicted_mean": float(predicted.mean()),
    }


# ---------------------------------------------------------------- load + checks
pred = pd.read_csv(PRED_PATH, parse_dates=["week_start"])
saved = pd.read_csv(METRICS_PATH).set_index("experiment")
print("Prediction columns:", list(pred.columns), "| rows:", len(pred))

expected_columns = {"experiment", "district", "week_start", "actual_count", "prediction"}
if set(pred.columns) != expected_columns:
    fail(f"unexpected prediction columns {list(pred.columns)}")
if sorted(pred["experiment"].unique()) != sorted(GROUPS):
    fail(f"unexpected experiments {pred['experiment'].unique()}")
if pred[["actual_count", "prediction"]].isna().any().any():
    fail("missing actual or predicted values")
if not np.isfinite(pred[["actual_count", "prediction"]].to_numpy(dtype=float)).all():
    fail("non-finite actual or predicted values")
if not pred["week_start"].dt.year.eq(2024).all():
    fail("rows outside 2024 found; 2025 rows must not be used")

checks = {}
key_sets = {}
for group in GROUPS:
    part = pred[pred["experiment"] == group]
    if part.duplicated(KEYS).any():
        fail(f"duplicate district-week keys in {group}")
    key_sets[group] = part.set_index(KEYS).sort_index()
    checks[f"{group}_rows"] = len(part)
reference = key_sets[GROUPS[0]]
for group in GROUPS[1:]:
    if not key_sets[group].index.equals(reference.index):
        fail(f"{group} validation keys differ from {GROUPS[0]}")
    if not key_sets[group]["actual_count"].equals(reference["actual_count"]):
        fail(f"{group} actual counts differ from {GROUPS[0]}")
if len(reference) != 520:
    fail(f"expected 520 validation rows per group, found {len(reference)}")
checks.update({
    "identical_keys_across_groups": True,
    "identical_actuals_across_groups": True,
    "no_duplicate_keys_within_group": True,
    "districts": int(reference.index.get_level_values("district").nunique()),
    "weeks": int(reference.index.get_level_values("week_start").nunique()),
    "first_week_start": str(reference.index.get_level_values("week_start").min().date()),
    "last_week_start": str(reference.index.get_level_values("week_start").max().date()),
    "rows_outside_2024": 0,
    "zero_actual_rows": int((reference["actual_count"] == 0).sum()),
})

# ---------------------------------------------------------------- task 1
rows = []
for group in GROUPS:
    part = key_sets[group]
    y, p = part["actual_count"].astype(float), part["prediction"].astype(float)
    m = error_metrics(y, p)
    if not np.isclose(m["mae"], saved.loc[group, "mae"], rtol=0, atol=TOLERANCE):
        fail(f"{group} MAE {m['mae']} != saved {saved.loc[group, 'mae']}")
    if not np.isclose(m["rmse"], saved.loc[group, "rmse"], rtol=0, atol=TOLERANCE):
        fail(f"{group} RMSE {m['rmse']} != saved {saved.loc[group, 'rmse']}")
    m["mean_poisson_deviance"] = float(mean_poisson_deviance(y, p)) if (p > 0).all() else np.nan
    m["r2"] = float(r2_score(y, p))
    m["min_prediction"] = float(p.min())
    m["saved_mae"] = float(saved.loc[group, "mae"])
    m["saved_rmse"] = float(saved.loc[group, "rmse"])
    m["mae_matches_saved"] = True
    m["rmse_matches_saved"] = True
    rows.append({"group": group, "label": LABELS[group], **m})
overall = pd.DataFrame(rows)
overall.insert(2, "validation_period", "2024-01-01 to 2024-12-23 week starts")
overall.to_csv(OUT / "member2_additional_metrics_2024_validation.csv", index=False)
print(overall[["group", "mae", "rmse", "wape_percent", "mean_error", "mean_poisson_deviance", "r2"]].round(4).to_string(index=False))

# ---------------------------------------------------------------- task 2
district_rows = []
for group in GROUPS:
    part = key_sets[group].reset_index()
    for district, d in part.groupby("district"):
        m = error_metrics(d["actual_count"].astype(float), d["prediction"].astype(float))
        district_rows.append({"group": group, "district": int(district), **m})
by_district = pd.DataFrame(district_rows).rename(columns={"n": "validation_weeks"})
by_district.to_csv(OUT / "member2_district_metrics_2024_validation.csv", index=False)

wide = by_district.pivot(index="district", columns="group", values=["mae", "rmse"])
summary = []
for group in GROUPS:
    top = by_district[by_district["group"] == group].nlargest(3, "mae")
    for rank, (_, r) in enumerate(top.iterrows(), start=1):
        summary.append({
            "group": group, "rank_by_mae": rank, "district": int(r["district"]),
            "mae": r["mae"], "rmse": r["rmse"], "mean_error": r["mean_error"],
            "wape_percent": r["wape_percent"], "actual_mean": r["actual_mean"],
        })
pd.DataFrame(summary).to_csv(OUT / "member2_largest_error_districts_2024_validation.csv", index=False)


def district_bar(metric: str, filename: str, title: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(1, 11)
    width = 0.27
    for i, group in enumerate(GROUPS):
        values = wide[(metric, group)].reindex(x).to_numpy()
        ax.bar(x + (i - 1) * width, values, width, label=LABELS[group], color=COLORS[group])
    ax.set_xticks(x)
    ax.set_xlabel("Council district")
    ax.set_ylabel(f"{metric.upper()} (reports per district-week)")
    ax.set_title(title)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=300)
    plt.close(fig)


district_bar("mae", "fig_district_mae_by_group.png", "District-wise MAE, 2024 validation (52 weeks per district)")
district_bar("rmse", "fig_district_rmse_by_group.png", "District-wise RMSE, 2024 validation (52 weeks per district)")

b = key_sets["B_basic_lags"].reset_index()
fig, ax = plt.subplots(figsize=(6.2, 6))
sc = ax.scatter(b["actual_count"], b["prediction"], c=b["district"], cmap="tab10", s=16, alpha=0.8)
limit = max(b["actual_count"].max(), b["prediction"].max()) * 1.05
ax.plot([0, limit], [0, limit], color="black", lw=1, ls="--", label="Perfect forecast (y = x)")
ax.set_xlim(0, limit)
ax.set_ylim(0, limit)
ax.set_xlabel("Actual weekly reports")
ax.set_ylabel("Predicted weekly reports (Group B)")
ax.set_title("Group B: actual vs predicted, 520 district-weeks (2024)")
ax.legend(*sc.legend_elements(), title="District", fontsize=8, loc="upper left", ncol=2, frameon=False)
fig.tight_layout()
fig.savefig(OUT / "fig_groupB_actual_vs_predicted.png", dpi=300)
plt.close(fig)

# ---------------------------------------------------------------- task 3
b["signed_error"] = b["prediction"] - b["actual_count"]
b["absolute_error"] = b["signed_error"].abs()
district_mean = b.groupby("district")["actual_count"].transform("mean")
district_q90 = b.groupby("district")["actual_count"].transform(lambda s: s.quantile(HIGH_DEMAND_QUANTILE))
b["actual_to_district_mean"] = b["actual_count"] / district_mean
b["high_demand_week"] = b["actual_count"] > district_q90

top10 = b.nlargest(10, "absolute_error").copy()
top10.insert(0, "rank", range(1, 11))
top10["direction"] = np.where(top10["signed_error"] < 0, "under-prediction", "over-prediction")
top10[["rank", "district", "week_start", "actual_count", "prediction", "signed_error", "absolute_error",
       "direction", "actual_to_district_mean", "high_demand_week"]].to_csv(
    OUT / "member2_groupB_top10_absolute_errors.csv", index=False, date_format="%Y-%m-%d")

july = b[(b["district"] == 3) & (b["week_start"] == pd.Timestamp("2024-07-29"))]
if len(july) != 1:
    fail("District 3, week of 2024-07-29 not found exactly once")
july_all = pred[(pred["district"] == 3) & (pred["week_start"] == pd.Timestamp("2024-07-29"))].copy()
july_all["signed_error"] = july_all["prediction"] - july_all["actual_count"]
july_all["absolute_error"] = july_all["signed_error"].abs()
july_all["group_mae"] = july_all["experiment"].map(overall.set_index("group")["mae"])
july_all["absolute_error_to_group_mae"] = july_all["absolute_error"] / july_all["group_mae"]
july_all["rank_of_abs_error_in_group"] = [
    int((key_sets[g]["prediction"] - key_sets[g]["actual_count"]).abs().rank(ascending=False, method="min")
        .loc[(3, pd.Timestamp("2024-07-29"))])
    for g in july_all["experiment"]
]
july_all.to_csv(OUT / "member2_district3_2024-07-29_all_groups.csv", index=False, date_format="%Y-%m-%d")

high, normal = b[b["high_demand_week"]], b[~b["high_demand_week"]]
spearman = b["absolute_error"].corr(b["actual_to_district_mean"], method="spearman")
busy = pd.DataFrame([
    {"subset": "high-demand district-weeks (actual > district's 2024 90th percentile)", **error_metrics(high["actual_count"], high["prediction"])},
    {"subset": "all other district-weeks", **error_metrics(normal["actual_count"], normal["prediction"])},
    {"subset": "all 520 district-weeks", **error_metrics(b["actual_count"], b["prediction"])},
])
busy["share_of_total_absolute_error_percent"] = [
    100 * high["absolute_error"].sum() / b["absolute_error"].sum(),
    100 * normal["absolute_error"].sum() / b["absolute_error"].sum(),
    100.0,
]
busy["top10_errors_in_subset"] = [int(top10["high_demand_week"].sum()), int((~top10["high_demand_week"]).sum()), 10]
busy["spearman_abs_error_vs_actual_to_district_mean"] = spearman
busy["spearman_signed_error_vs_actual_to_district_mean"] = b["signed_error"].corr(b["actual_to_district_mean"], method="spearman")
busy["under_predicted_weeks"] = [int((high["signed_error"] < 0).sum()), int((normal["signed_error"] < 0).sum()), int((b["signed_error"] < 0).sum())]
busy.to_csv(OUT / "member2_groupB_high_demand_error_summary.csv", index=False)

fig, ax = plt.subplots(figsize=(7.5, 4.8))
ax.scatter(b.loc[~b["high_demand_week"], "actual_to_district_mean"], b.loc[~b["high_demand_week"], "signed_error"],
           s=14, alpha=0.6, color="#1f77b4", label="Other district-weeks")
ax.scatter(b.loc[b["high_demand_week"], "actual_to_district_mean"], b.loc[b["high_demand_week"], "signed_error"],
           s=22, alpha=0.9, color="#d62728", label="Actual above district's 2024 90th percentile")
j = july.iloc[0]
ax.annotate("District 3, week of 2024-07-29", xy=(j["actual_count"] / district_mean[july.index[0]], j["prediction"] - j["actual_count"]),
            xytext=(1.55, -60), arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.axhline(0, color="black", lw=0.8)
ax.set_xlabel("Actual count / district's 2024 mean weekly count")
ax.set_ylabel("Signed error (predicted - actual)")
ax.set_title("Group B: under-predicts unusually high weeks, over-predicts unusually low weeks")
ax.legend(frameon=False, fontsize=8, loc="lower left")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "fig_groupB_error_vs_relative_demand.png", dpi=300)
plt.close(fig)

pd.Series(checks, name="value").to_csv(OUT / "member2_input_checks.csv", header=True)
print("\nInput checks:", checks)
print("\nDistrict 3, 2024-07-29:\n", july_all.round(3).to_string(index=False))
print("\nTop 10 Group B absolute errors:\n", top10.round(2).to_string(index=False))
print("\nHigh-demand summary:\n", busy.round(3).to_string(index=False))
print("\nLargest-error districts:\n", pd.DataFrame(summary).round(3).to_string(index=False))
print("\nDone. Outputs written to", OUT.relative_to(ROOT))
