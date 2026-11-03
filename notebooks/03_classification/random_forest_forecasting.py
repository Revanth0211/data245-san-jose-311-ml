from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# Find the repository root
REPO_ROOT = Path(__file__).resolve().parents[2]

# File locations
INPUT_FILE = REPO_ROOT / "data" / "processed" / "district_week_development.csv"
RESULTS_DIR = REPO_ROOT / "results" / "member3_random_forest"
FIGURES_DIR = REPO_ROOT / "reports" / "figures" / "member3_random_forest"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# Load the shared district-week table
df = pd.read_csv(INPUT_FILE)

df["week_start"] = pd.to_datetime(df["week_start"])
df["count"] = pd.to_numeric(df["count"], errors="coerce")


# Use the agreed chronological split
train = df[
    (df["week_start"] >= "2020-01-01")
    & (df["week_start"] <= "2023-12-31")
    & (df["split"] == "train")
].copy()

validation = df[
    (df["week_start"].dt.year == 2024)
    & (df["split"] == "validation")
].copy()


# Candidate features
all_features = [
    "district",
    "sin_year",
    "cos_year",
    "lag_1",
    "lag_2",
    "lag_4",
    "rolling_4",
    "rolling_13",
]


# Keep the same eligible rows for every experiment.
# This makes the feature comparison fair.
combined = pd.concat([train, validation], axis=0)

combined = combined.dropna(
    subset=all_features + ["count"]
).copy()

train = combined[combined["split"] == "train"].copy()
validation = combined[combined["split"] == "validation"].copy()


print("Training rows:", len(train))
print("Validation rows:", len(validation))


# Feature-removal experiments
feature_groups = {
    "full_model": [
        "district",
        "sin_year",
        "cos_year",
        "lag_1",
        "lag_2",
        "lag_4",
        "rolling_4",
        "rolling_13",
    ],
    "without_calendar": [
        "district",
        "lag_1",
        "lag_2",
        "lag_4",
        "rolling_4",
        "rolling_13",
    ],
    "without_lags": [
        "district",
        "sin_year",
        "cos_year",
        "rolling_4",
        "rolling_13",
    ],
    "without_rolling": [
        "district",
        "sin_year",
        "cos_year",
        "lag_1",
        "lag_2",
        "lag_4",
    ],
    "basic_model": [
        "district",
        "sin_year",
        "cos_year",
    ],
}


results = []
all_predictions = []


for experiment_name, features in feature_groups.items():

    categorical_features = ["district"]
    numeric_features = [
        feature for feature in features if feature != "district"
    ]

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "district_encoding",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
                categorical_features,
            ),
            (
                "numeric_features",
                "passthrough",
                numeric_features,
            ),
        ],
        remainder="drop",
    )

    model = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        min_samples_leaf=2,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            ("random_forest", model),
        ]
    )

    X_train = train[features]
    y_train = train["count"]

    X_validation = validation[features]
    y_validation = validation["count"]

    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_validation)

    # Counts cannot be negative
    predictions = np.maximum(predictions, 0)

    mae = mean_absolute_error(y_validation, predictions)
    rmse = np.sqrt(mean_squared_error(y_validation, predictions))

    results.append(
        {
            "experiment": experiment_name,
            "features_used": ", ".join(features),
            "training_rows": len(train),
            "validation_rows": len(validation),
            "mae": mae,
            "rmse": rmse,
        }
    )

    experiment_predictions = validation[
        ["district", "week_start", "count"]
    ].copy()

    experiment_predictions["experiment"] = experiment_name
    experiment_predictions["actual_count"] = experiment_predictions["count"]
    experiment_predictions["predicted_count"] = predictions

    experiment_predictions = experiment_predictions.drop(
        columns=["count"]
    )

    all_predictions.append(experiment_predictions)


# Save metrics
metrics_df = pd.DataFrame(results)
metrics_df = metrics_df.sort_values("mae")

metrics_file = RESULTS_DIR / "random_forest_feature_removal_metrics.csv"
metrics_df.to_csv(metrics_file, index=False)


# Save predictions
predictions_df = pd.concat(all_predictions, ignore_index=True)

predictions_file = RESULTS_DIR / "random_forest_validation_predictions.csv"
predictions_df.to_csv(predictions_file, index=False)


# Print results
print("\nRandom Forest validation results:")
print(metrics_df.to_string(index=False))


# Create a comparison figure
plot_df = metrics_df.set_index("experiment")[["mae", "rmse"]]

ax = plot_df.plot(
    kind="bar",
    figsize=(10, 6),
    color=["#4C78A8", "#F58518"],
)

ax.set_title(
    "Random Forest Feature-Removal Experiment"
)
ax.set_xlabel("Experiment")
ax.set_ylabel("Error in reports per district-week")
ax.legend(["MAE", "RMSE"])
plt.xticks(rotation=30, ha="right")
plt.tight_layout()

figure_file = FIGURES_DIR / "random_forest_feature_removal.png"
plt.savefig(figure_file, dpi=200)
plt.close()


print("\nSaved metrics to:")
print(metrics_file)

print("\nSaved predictions to:")
print(predictions_file)

print("\nSaved figure to:")
print(figure_file)
