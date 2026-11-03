"""Unit tests for Member 4. No real dataset, git state, or 2025 access needed.
Run from repo root: python -m unittest discover -s notebooks/04_resolution_regression -p 'test_member4_xgboost.py' -v
"""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import member4_xgboost as m


def synthetic_panel():
    # All weeks are complete, and 2023-12-25 -> 2024-01-01 is the correct boundary.
    dates = pd.date_range('2023-09-04', '2024-04-29', freq='W-MON')
    frame = pd.MultiIndex.from_product([[1, 2], dates], names=['district','week_start']).to_frame(index=False)
    frame = frame.sort_values(['district','week_start']).reset_index(drop=True)
    frame['count'] = (10 + frame['district'] * 3 + np.arange(len(frame)) % 7).astype(int)
    grouped = frame.groupby('district')['count']
    for lag in (1,2,4): frame[f'lag_{lag}'] = grouped.shift(lag)
    for w in (4,13):
        frame[f'rolling_{w}'] = grouped.transform(lambda x: x.shift(1).rolling(w, min_periods=w).mean())
    phase = 2*np.pi*frame.week_start.dt.dayofyear/365.25
    frame['sin_year'], frame['cos_year'] = np.sin(phase), np.cos(phase)
    frame['week_end'] = frame.week_start + pd.Timedelta(days=6)
    frame['split'] = np.where(frame.week_start < pd.Timestamp('2024-01-01'), 'train', 'validation')
    frame['coverage_status'] = 'assumed_complete_pending_team_confirmation'
    return frame


class PrimaryAnalysisTests(unittest.TestCase):
    def test_member2_lags_is_primary_when_available(self):
        self.assertEqual(m.resolve_primary_experiment({'shared': m.SHARED,
                                                        'member2_lags': m.M2_LAGS,
                                                        'member2_full': m.M2_FULL}), 'member2_lags')

    def test_shared_is_primary_without_member2(self):
        self.assertEqual(m.resolve_primary_experiment({'shared': m.SHARED}), 'shared')

    def test_cannot_select_untrained_experiment(self):
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            m.resolve_primary_experiment({'shared': m.SHARED}, 'member2_lags')

    def test_primary_rows_are_consistent_across_output_tables(self):
        for field in ('district', 'busy_district_week', 'feature'):
            frame = pd.DataFrame({'experiment': ['shared', 'member2_lags', 'member2_lags'],
                                  field: ['a', 'b', 'c']})
            selected = m.primary_rows(frame, 'member2_lags')
            self.assertEqual(len(selected), 2)
            self.assertTrue(selected.experiment.eq('member2_lags').all())
        with self.assertRaisesRegex(ValueError, 'No rows'):
            m.primary_rows(frame, 'unknown')


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'panel.csv'
        synthetic_panel().to_csv(self.path, index=False)

    def tearDown(self): self.tmp.cleanup()

    def save(self, df): df.to_csv(self.path, index=False)

    def test_load_panel_accepts_complete_week_history(self):
        loaded = m.load_panel(self.path)
        self.assertEqual(len(loaded), len(synthetic_panel()))

    def test_2025_is_never_accepted_in_development(self):
        df = synthetic_panel(); df.loc[df.index[-1], 'week_start'] = pd.Timestamp('2025-01-06')
        df.loc[df.index[-1], 'week_end'] = pd.Timestamp('2025-01-12')
        self.save(df)
        with self.assertRaisesRegex(ValueError, 'NEVER include 2025'):
            m.load_panel(self.path)

    def test_duplicate_district_week_rejected(self):
        df = synthetic_panel(); self.save(pd.concat([df, df.head(1)]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            m.load_panel(self.path)

    def test_non_monday_rejected(self):
        df = synthetic_panel(); df.loc[0, 'week_start'] += pd.Timedelta(days=1)
        self.save(df)
        with self.assertRaisesRegex(ValueError, 'Non-Monday'):
            m.load_panel(self.path)

    def test_split_mismatch_rejected(self):
        df = synthetic_panel(); df.loc[df.week_start.eq(pd.Timestamp('2024-01-01')), 'split']='train'
        self.save(df)
        with self.assertRaisesRegex(ValueError, 'Split/date'):
            m.load_panel(self.path)

    def test_noncontiguous_history_rejected(self):
        df = synthetic_panel(); df=df.loc[~((df.district==1)&(df.week_start==pd.Timestamp('2023-10-02')))]
        self.save(df)
        with self.assertRaisesRegex(ValueError, 'Non-contiguous'):
            m.load_panel(self.path)

    def test_negative_counts_rejected(self):
        df = synthetic_panel(); df.loc[0, 'count']=-1; self.save(df)
        with self.assertRaisesRegex(ValueError, 'nonnegative'):
            m.load_panel(self.path)

    def test_train_and_valid_temporally_separate(self):
        train, valid = m.choose_rows(m.load_panel(self.path), m.SHARED)
        self.assertTrue(train.week_start.dt.year.eq(2023).all())
        self.assertTrue(valid.week_start.dt.year.eq(2024).all())
        self.assertLess(train.week_end.max(), valid.week_start.min())
        self.assertFalse(set(m.SHARED) & {'count', 'date_last_updated', 'status'})

    def test_no_training_on_provisional_data_without_acknowledgement(self):
        with self.assertRaisesRegex(ValueError, 'provisional'):
            m.run(panel_path=self.path, provisional=False)

    def test_busy_threshold_training_only_and_posthoc(self):
        train = pd.DataFrame({'district':[1]*10, 'week_start':pd.date_range('2023-01-02', periods=10, freq='W-MON'), 'count':range(10)})
        val = pd.DataFrame({'district':[1,1], 'week_start':pd.to_datetime(['2024-01-01','2024-01-08']),
                            'actual_count':[1, 50], 'prediction':[4.,4.]})
        a, thresh = m.annotate_busy(val,train)
        self.assertAlmostEqual(a.district_busy_threshold_train_p90.iloc[0], 8.1)
        self.assertEqual(a.busy_district_week.tolist(), [False,True])
        self.assertAlmostEqual(thresh, 8.1)

    def test_metrics_formula_and_empty_guard(self):
        result=m.scores([0,2],[1,1])
        self.assertAlmostEqual(result['mae'],1)
        self.assertAlmostEqual(result['rmse'],1)
        with self.assertRaises(ValueError): m.scores([],[])

    def test_end_to_end_outputs_include_notebook_manifest_contract(self):
        # This regression test covers the API field previously missing from an
        # older script even though all the original unit tests had passed.
        result_dir = Path(self.tmp.name) / 'results'
        figure_dir = Path(self.tmp.name) / 'figures'
        output, manifest = m.run(panel_path=self.path, results_dir=result_dir,
                                 figures_dir=figure_dir, provisional=True,
                                 with_member2=False,
                                 team_predictions=Path(self.tmp.name) / 'no_team_predictions.csv')
        self.assertEqual(manifest['artifact_api_version'], m.ARTIFACT_API_VERSION)
        self.assertEqual(manifest['primary_analysis_experiment'], 'shared')
        self.assertEqual(manifest['experiment_names'], ['shared'])
        self.assertGreater(len(output['validation_predictions']), 0)
        self.assertEqual(set(output['district_metrics'].experiment), {'shared'})
        self.assertEqual(set(output['busy_week_metrics'].experiment), {'shared'})
        self.assertEqual(set(output['feature_importance'].experiment), {'shared'})
        self.assertTrue((result_dir / 'run_manifest.json').is_file())
        self.assertTrue((figure_dir / 'district_mae.png').is_file())

    def test_member5_rows_and_targets_check(self):
        df = pd.DataFrame({'district':[1,2], 'week_start':pd.to_datetime(['2024-01-01','2024-01-01']), 'count':[10,20]})
        f = Path(self.tmp.name)/'member5.csv'
        df2 = df.copy(); df2['experiment']='poisson_2020'; df2.to_csv(f,index=False)
        self.assertEqual(m.check_team_validation(df,f)['team_validation_crosscheck'], 'passed')
        df2.loc[0,'count']=11; df2.to_csv(f,index=False)
        with self.assertRaisesRegex(ValueError,'differ'):
            m.check_team_validation(df,f)


if __name__ == '__main__': unittest.main()
