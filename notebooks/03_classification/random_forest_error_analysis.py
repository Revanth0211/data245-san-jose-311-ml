from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PREDICTION_FILE = (
    PROJECT_ROOT
    / "results"
    / "member3_random_forest"
    / "random_forest_validation_predictions.csv"
)

RESULTS_DIR = PROJECT_ROOT / "results" / "member3_random_forest"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures" / "member3_random_forest"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


predictions = pd.read_csv(PREDICTION_FILE)

# Use the best Random Forest experiment.
df = predictions[
    predictions["experiment"] == "without_rolling"
].copy()

df["error"] = df["predicted_count"] - df["actual_count"]
df["absolute_error"] = df["error"].abs()
df["underprediction"] = df["actual_count"] - df["predicted_count"]


# Summarize errors by district.
district_errors = (
    df.groupby("district")
    .agg(
        mae=("absolute_error", "mean"),
        average_error=("error", "mean"),
        actual_reports=("actual_count", "sum"),
    )
    .reset_index()
    .sort_values("mae", ascending=False)
)

district_errors.to_csv(
    RESULTS_DIR / "random_forest_error_by_district.csv",
    index=False,
)


# Save the largest individual errors.
largest_errors = (
    df.sort_values("absolute_error", ascending=False)
    .head(10)
)

largest_errors[
    [
        "district",
        "week_start",
        "actual_count",
        "predicted_count",
        "error",
        "absolute_error",
    ]
].to_csv(
    RESULTS_DIR / "random_forest_largest_errors.csv",
    index=False,
)


# Save the largest underpredictions.
largest_underpredictions = (
    df.sort_values("underprediction", ascending=False)
    .head(10)
)

largest_underpredictions[
    [
        "district",
        "week_start",
        "actual_count",
        "predicted_count",
        "underprediction",
    ]
].to_csv(
    RESULTS_DIR / "random_forest_largest_underpredictions.csv",
    index=False,
)


# Create a district MAE figure.
plt.figure(figsize=(9, 5))

plt.bar(
    district_errors["district"].astype(str),
    district_errors["mae"],
)

plt.title("Random Forest Validation MAE by District")
plt.xlabel("Council district")
plt.ylabel("Mean absolute error")
plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "random_forest_error_by_district.png",
    dpi=300,
)

plt.close()


print("Random Forest error analysis completed.")
print(f"Rows analyzed: {len(df)}")
print("\nError summary by district:")
print(district_errors.round(2).to_string(index=False))

