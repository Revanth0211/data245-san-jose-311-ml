import sys
from pathlib import Path
import unittest
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from demand_forecasting import features


class ForecastLeakageTests(unittest.TestCase):
    def panel(self):
        return pd.DataFrame({'district': [1]*20 + [2]*20,
            'week_start': list(pd.date_range('2020-01-06', periods=20, freq='W-MON'))*2,
            'count': list(range(20)) + list(range(100, 120))})

    def test_current_and_future_counts_cannot_change_current_features(self):
        before = self.panel()
        after = before.copy()
        after.loc[after.week_start.ge('2020-04-06'), 'count'] = 9999
        a, b = features(before), features(after)
        columns = ['lag_1', 'lag_2', 'lag_4', 'rolling_4', 'rolling_13']
        pd.testing.assert_frame_equal(a.loc[a.week_start.le('2020-04-06'), columns],
                                     b.loc[b.week_start.le('2020-04-06'), columns])

    def test_district_history_does_not_mix(self):
        result = features(self.panel())
        self.assertTrue(result.groupby('district').head(1).lag_1.isna().all())
        self.assertEqual(result.loc[21, 'lag_1'], 100)

    def test_missing_week_rejected(self):
        with self.assertRaises(ValueError):
            features(self.panel().drop(index=5))


if __name__ == '__main__':
    unittest.main()
