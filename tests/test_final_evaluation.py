import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from final_evaluation import check_protocol, evaluate, freeze, partition, PROTOCOL, CONVENTIONS, sha
from demand_forecasting import NUMERIC


class FinalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(PROTOCOL.read_text())

    def panel(self):
        weeks = pd.date_range('2018-01-01', '2025-12-29', freq='W-MON')
        return pd.DataFrame({'district': [1] * len(weeks), 'week_start': weeks,
                             'count': list(range(len(weeks)))})

    def test_pending_decisions_prevent_request_parsing(self):
        with patch('final_evaluation.pd.read_csv', side_effect=AssertionError('Test read')):
            with tempfile.TemporaryDirectory() as directory:
                self.config['decisions']['source_coverage']['status'] = 'pending'
                path = Path(directory) / 'pending.json'
                path.write_text(json.dumps(self.config))
                with self.assertRaisesRegex(ValueError, 'Pending:'):
                    evaluate(protocol_path=path)

    def test_hash_change_requires_new_validation(self):
        config = copy.deepcopy(self.config)
        config['input_sha256'] = 'changed'
        self.assertIn('input_sha256_changed_regenerate_validation_before_freezing',
                      check_protocol(config))

    def test_complete_weeks_and_crossing_history(self):
        train, test = partition(self.panel(), self.config)
        self.assertEqual(len(train), 260)
        self.assertEqual(len(test), 51)
        self.assertEqual(train.week_start.max(), pd.Timestamp('2024-12-23'))
        self.assertEqual(test.week_start.min(), pd.Timestamp('2025-01-06'))
        self.assertEqual(test.week_start.max(), pd.Timestamp('2025-12-22'))
        previous = self.panel().set_index('week_start').loc['2024-12-30', 'count']
        self.assertEqual(test.iloc[0].lag_1, previous)

    def test_future_test_targets_do_not_change_fit_or_current_features(self):
        before = self.panel()
        after = before.copy()
        after.loc[after.week_start.ge('2025-06-02'), 'count'] = 99999
        a_train, a_test = partition(before, self.config)
        b_train, b_test = partition(after, self.config)
        pd.testing.assert_frame_equal(a_train, b_train)
        columns = ['district', 'week_start'] + NUMERIC
        pd.testing.assert_frame_equal(a_test.loc[a_test.week_start.le('2025-06-02'), columns],
                                      b_test.loc[b_test.week_start.le('2025-06-02'), columns])

    def test_frozen_synthetic_run_and_repeated_evaluation_guard(self):
        # Synthetic records only: no reserved project outcomes are read.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ['data/processed', 'data/reference', 'src']:
                (root / folder).mkdir(parents=True)
            data_path = root / 'data/processed/illegal_dumping_cleaned.csv'
            boundary_path = root / 'data/reference/council_districts_snapshot.geojson'
            data_path.write_text('synthetic fixture')
            boundary_path.write_text(json.dumps({'features': [
                {'properties': {'DISTRICT': i}} for i in range(1, 11)]}))
            (root / 'src/demand_forecasting.py').write_text('synthetic source marker')
            (root / 'requirements-forecasting.txt').write_text('synthetic requirements marker')
            config = copy.deepcopy(self.config)
            config.update(input_sha256=sha(data_path), boundary_sha256=sha(boundary_path))
            for name, convention in CONVENTIONS.items():
                config['decisions'][name].update(status='documented_assumption',
                    decision='Synthetic fixture only', evidence_or_limitation='Synthetic test',
                    adopted_convention=convention)
            protocol_path = root / 'protocol.json'
            protocol_path.write_text(json.dumps(config))
            out = root / 'outputs'
            freeze(protocol_path, out, root)
            records = []
            for district in range(1, 11):
                for week in pd.date_range('2018-01-01', '2025-12-22', freq='W-MON'):
                    records.append({'request_id': f'{district}-{week}', 'date_created': week,
                                    'fixture_district': district})
            def fake_mapping(frame, _):
                return frame.assign(district=frame.fixture_district, location_matches=1)
            with patch('final_evaluation.pd.read_csv', return_value=pd.DataFrame(records)), \
                 patch('final_evaluation.assign_districts', side_effect=fake_mapping):
                rows = evaluate(protocol_path, out, root)
            self.assertTrue(all(r['test_rows'] == 510 and r['mae'] < 1e-8 for r in rows))
            self.assertTrue(json.loads((out / 'run_manifest.json').read_text())['test_evaluated'])
            with patch('final_evaluation.pd.read_csv', side_effect=AssertionError('Second read')):
                with self.assertRaises(FileExistsError):
                    evaluate(protocol_path, out, root)


if __name__ == '__main__':
    unittest.main()
