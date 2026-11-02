import sys
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from eda_features import (
    add_calendar_features,
    add_forecasting_features,
    add_historical_features,
    assign_development_splits,
    validate_weekly_panel,
)
from demand_forecasting import features as teammate_features


class EDAFeatureTests(unittest.TestCase):
    def panel(self, periods=20):
        weeks = pd.date_range("2023-10-02", periods=periods, freq="W-MON")
        return pd.DataFrame({
            "district": [1] * periods + [2] * periods,
            "week_start": list(weeks) * 2,
            "count": list(range(periods)) + list(range(100, 100 + periods)),
        })

    def test_lag_values_are_correct(self):
        result = add_historical_features(self.panel())
        district_one = result.loc[result.district.eq(1)].reset_index(drop=True)
        self.assertEqual(district_one.loc[8, "lag_1"], 7)
        self.assertEqual(district_one.loc[8, "lag_2"], 6)
        self.assertEqual(district_one.loc[8, "lag_4"], 4)
        self.assertEqual(district_one.loc[8, "lag_8"], 0)

    def test_rolling_means_are_correct(self):
        result = add_historical_features(self.panel())
        district_one = result.loc[result.district.eq(1)].reset_index(drop=True)
        self.assertEqual(district_one.loc[4, "rolling_4"], 1.5)
        self.assertEqual(district_one.loc[8, "rolling_8"], 3.5)
        self.assertEqual(district_one.loc[13, "rolling_13"], 6.0)

    def test_rolling_standard_deviation_is_correct(self):
        result = add_historical_features(self.panel())
        district_one = result.loc[result.district.eq(1)].reset_index(drop=True)
        self.assertAlmostEqual(district_one.loc[4, "rolling_std_4"], np.sqrt(5 / 3))
        self.assertAlmostEqual(district_one.loc[8, "rolling_std_8"], np.sqrt(6))

    def test_district_histories_remain_separate(self):
        result = add_historical_features(self.panel())
        district_two = result.loc[result.district.eq(2)].reset_index(drop=True)
        self.assertTrue(pd.isna(district_two.loc[0, "lag_1"]))
        self.assertEqual(district_two.loc[1, "lag_1"], 100)

    def test_current_count_cannot_change_its_own_features(self):
        before = self.panel()
        after = before.copy()
        current = pd.Timestamp("2023-12-25")
        after.loc[after.week_start.eq(current), "count"] = 9999
        a = add_forecasting_features(before).set_index(["district", "week_start"])
        b = add_forecasting_features(after).set_index(["district", "week_start"])
        columns = [column for column in a if column not in {"count"}]
        pd.testing.assert_series_equal(a.loc[(1, current), columns], b.loc[(1, current), columns])

    def test_future_counts_cannot_change_earlier_features(self):
        before = self.panel()
        after = before.copy()
        cutoff = pd.Timestamp("2024-01-01")
        after.loc[after.week_start.gt(cutoff), "count"] = 9999
        a = add_forecasting_features(before)
        b = add_forecasting_features(after)
        feature_columns = [column for column in a if column != "count"]
        pd.testing.assert_frame_equal(
            a.loc[a.week_start.le(cutoff), feature_columns],
            b.loc[b.week_start.le(cutoff), feature_columns],
        )

    def test_history_is_continuous_across_year_and_split_boundary(self):
        panel = self.panel()
        result = add_forecasting_features(panel)
        row = result.loc[
            result.district.eq(1) & result.week_start.eq(pd.Timestamp("2024-01-01"))
        ].iloc[0]
        self.assertEqual(row.lag_1, 12)
        self.assertEqual(row.lag_2, 11)
        self.assertEqual(row.rolling_4, 10.5)

    def test_missing_week_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_weekly_panel(self.panel().drop(index=5))

    def test_incomplete_and_split_crossing_weeks_are_not_scored(self):
        panel = pd.DataFrame({
            "district": [1] * 5,
            "week_start": pd.to_datetime([
                "2023-12-25", "2024-01-01", "2024-12-23", "2024-12-30", "2024-01-02"
            ]),
            "count": [1, 2, 3, 4, 5],
        })
        result = assign_development_splits(panel).set_index("week_start")
        self.assertEqual(result.loc["2023-12-25", "development_split"], "train")
        self.assertEqual(result.loc["2024-01-01", "development_split"], "validation")
        self.assertEqual(result.loc["2024-12-23", "development_split"], "validation")
        self.assertEqual(result.loc["2024-12-30", "development_split"], "excluded_split_crossing")
        self.assertEqual(result.loc["2024-01-02", "development_split"], "excluded_incomplete_week")
        self.assertFalse(result.loc["2024-12-30", "is_scoring_eligible"])
        self.assertFalse(result.loc["2024-01-02", "is_scoring_eligible"])

    def test_features_preserve_keys_and_target(self):
        panel = self.panel()
        result = add_forecasting_features(panel)
        pd.testing.assert_frame_equal(
            panel.sort_values(["district", "week_start"]).reset_index(drop=True),
            result[["district", "week_start", "count"]],
        )

    def test_existing_feature_definitions_are_preserved(self):
        panel = self.panel()
        existing = teammate_features(panel.copy())
        extended = add_forecasting_features(panel.copy())
        columns = ["lag_1", "lag_2", "lag_4", "rolling_4", "rolling_13", "sin_year", "cos_year"]
        pd.testing.assert_frame_equal(existing[columns], extended[columns])

    def test_calendar_features_are_known_from_week_start(self):
        result = add_calendar_features(self.panel())
        row = result.loc[result.week_start.eq(pd.Timestamp("2024-01-01"))].iloc[0]
        self.assertEqual(row["month"], 1)
        self.assertEqual(row["week_of_year"], 1)


if __name__ == "__main__":
    unittest.main()
