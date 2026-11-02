import hashlib
import sys
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eda_features import add_forecasting_features
from feature_comparison import FEATURE_GROUPS, run_feature_comparison


TEAMMATE_HASHES = {
    "src/demand_forecasting.py": "8ec4f0db928ce9043c784d4b7ba51098cdac365b4c45c88486db2e73c44887f1",
    "notebooks/05_demand_forecasting/README.md": "28b8002b948995753c9d585b8bca63403586b6922e1e8eeb763b2d99ec72fc63",
    "results/demand_forecasting/validation_metrics.csv": "696a9699e54c1c79fd2e7650648bc7b20f8054b771af8112aba3f29e7075cf3e",
    "results/demand_forecasting/validation_predictions.csv": "4cc256226783dcce1947fd119cf0bdd9df764c68d4319a9da441b6ec548ee9a4",
}


class FeatureComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        weeks = pd.date_range("2018-01-01", "2024-12-23", freq="W-MON")
        rows = []
        for district in range(1, 11):
            for position, week in enumerate(weeks):
                count = 10 + district + position % 17 + (position // 52)
                rows.append((district, week, count))
        base = pd.DataFrame(rows, columns=["district", "week_start", "count"])
        cls.featured = add_forecasting_features(base)
        cls.result = run_feature_comparison(
            cls.featured,
            accept_provisional_geography=True,
            accept_provisional_coverage=True,
        )

    def test_identical_training_keys(self):
        reference = self.result.training_keys["A_basic"]
        for experiment in FEATURE_GROUPS:
            pd.testing.assert_frame_equal(reference, self.result.training_keys[experiment])

    def test_identical_validation_keys(self):
        reference = self.result.validation_keys["A_basic"]
        for experiment in FEATURE_GROUPS:
            pd.testing.assert_frame_equal(reference, self.result.validation_keys[experiment])

    def test_identical_validation_targets(self):
        pivot = self.result.predictions.pivot(
            index=["district", "week_start"], columns="experiment", values="actual_count"
        )
        for experiment in FEATURE_GROUPS:
            np.testing.assert_array_equal(pivot["A_basic"], pivot[experiment])

    def test_no_2025_evaluation_rows(self):
        self.assertFalse(self.result.training_frame.week_start.dt.year.ge(2025).any())
        self.assertFalse(self.result.validation_frame.week_start.dt.year.ge(2025).any())

    def test_preprocessing_fitted_only_on_training(self):
        for experiment, numeric_features in FEATURE_GROUPS.items():
            scaler = self.result.models[experiment].named_steps["columntransformer"].named_transformers_["numeric"]
            expected = self.result.training_frame[numeric_features].mean().to_numpy()
            np.testing.assert_allclose(scaler.mean_, expected)

    def test_lag_and_rolling_features_are_past_only(self):
        changed = self.featured.copy()
        current_week = pd.Timestamp("2024-01-01")
        changed.loc[changed.week_start.ge(current_week), "count"] = 99999
        rebuilt = add_forecasting_features(changed[["district", "week_start", "count"]])
        protected = [feature for feature in FEATURE_GROUPS["C_basic_lags_rolling"] if feature.startswith(("lag_", "rolling_", "recent_"))]
        original_row = self.featured.loc[self.featured.week_start.eq(current_week), protected].reset_index(drop=True)
        changed_row = rebuilt.loc[rebuilt.week_start.eq(current_week), protected].reset_index(drop=True)
        pd.testing.assert_frame_equal(original_row, changed_row)

    def test_no_missing_or_infinite_model_values(self):
        all_numeric = list(dict.fromkeys(feature for group in FEATURE_GROUPS.values() for feature in group))
        for frame in [self.result.training_frame, self.result.validation_frame]:
            self.assertTrue(np.isfinite(frame[all_numeric + ["count"]].to_numpy(dtype=float)).all())

    def test_predictions_and_metrics_are_finite_and_nonnegative(self):
        self.assertTrue(np.isfinite(self.result.predictions["prediction"]).all())
        self.assertTrue((self.result.predictions["prediction"] >= 0).all())
        self.assertTrue(np.isfinite(self.result.metrics[["mae", "rmse"]]).all().all())

    def test_explicit_assumption_acceptance_is_required(self):
        with self.assertRaises(ValueError):
            run_feature_comparison(self.featured)

    def test_original_teammate_files_unchanged(self):
        for relative_path, expected_hash in TEAMMATE_HASHES.items():
            actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            self.assertEqual(actual, expected_hash, relative_path)


if __name__ == "__main__":
    unittest.main()
