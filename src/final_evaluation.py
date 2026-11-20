"""Freeze and run the selected forecasting model on reserved complete 2025 weeks.

The check and freeze commands do not aggregate or score the test period.
Run `python src/final_evaluation.py check` before the team records its decisions.
"""
import argparse
import hashlib
import json
import platform
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from demand_forecasting import NUMERIC, assign_districts, features, metrics

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'config/final_evaluation_protocol.json'
OUT = ROOT / 'results/demand_forecasting_final'
DECISIONS = ('source_coverage', 'timestamp_handling', 'coordinate_exclusions',
             'fixed_district_geography', 'geojson_coordinate_system', 'unmatched_points')
CONVENTIONS = {
    'source_coverage': 'annual_exports_complete_for_zero_fill',
    'timestamp_handling': 'naive_creation_timestamps_as_local_wall_clock',
    'coordinate_exclusions': 'retain_current_cleaned_input_exclusions',
    'fixed_district_geography': 'fixed_archived_current_map_for_all_years',
    'geojson_coordinate_system': 'saved_geojson_interpreted_as_longitude_latitude',
    'unmatched_points': 'exclude_nonunique_matches_from_district_counts',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def versions():
    return {'python': platform.python_version(), 'numpy': np.__version__,
            'pandas': pd.__version__, 'scikit_learn': sklearn.__version__}


def check_protocol(config, root=ROOT):
    """Return explicit unresolved decisions without inspecting test outcomes."""
    pending = []
    for name in DECISIONS:
        decision = config.get('decisions', {}).get(name, {})
        if (decision.get('status') not in ('confirmed', 'documented_assumption')
                or not str(decision.get('decision', '')).strip()
                or not str(decision.get('evidence_or_limitation', '')).strip()
                or decision.get('adopted_convention') != CONVENTIONS[name]):
            pending.append(name)
    for key, relative in (('input_sha256', 'data/processed/illegal_dumping_cleaned.csv'),
                          ('boundary_sha256', 'data/reference/council_districts_snapshot.geojson')):
        if sha(root / relative) != config[key]:
            pending.append(key + '_changed_regenerate_validation_before_freezing')
    if config.get('model') != {'name': 'poisson', 'alpha': 1.0, 'max_iter': 2000, 'tol': 1e-8}:
        pending.append('model_must_match_selected_validation_configuration')
    if config.get('training_start') != '2020-01-01' or config.get('refit_end') != '2024-12-31':
        pending.append('unexpected_final_refit_window')
    if config.get('test_start') != '2025-01-01' or config.get('test_end') != '2025-12-31':
        pending.append('unexpected_test_window')
    return pending


def freeze(protocol_path=PROTOCOL, out=OUT, root=ROOT):
    config = json.loads(protocol_path.read_text())
    pending = check_protocol(config, root)
    if pending:
        raise ValueError('Pending: ' + ', '.join(pending))
    out.mkdir(parents=True, exist_ok=True)
    lock = out / 'protocol_lock.json'
    if lock.exists():
        raise ValueError('Protocol already frozen; preserve the existing lock')
    payload = {'protocol_sha256': sha(protocol_path), 'implementation_sha256': sha(__file__),
               'shared_implementation_sha256': sha(root / 'src/demand_forecasting.py'),
               'requirements_sha256': sha(root / 'requirements-forecasting.txt'),
               'runtime_versions': versions(), 'protocol': config}
    lock.write_text(json.dumps(payload, indent=2) + '\n')
    return payload


def partition(panel, config):
    """Select complete calendar-year weeks; retain crossing weeks only as history."""
    ready = features(panel).dropna(subset=NUMERIC).copy()
    ready['week_end'] = ready.week_start + pd.Timedelta(days=6)
    train = ready.loc[ready.week_start.ge(config['training_start'])
                      & ready.week_end.le(config['refit_end'])].copy()
    test = ready.loc[ready.week_start.ge(config['test_start'])
                     & ready.week_end.le(config['test_end'])].copy()
    if train.empty or test.empty or train.week_end.max() >= test.week_start.min():
        raise ValueError('Empty or overlapping evaluation windows')
    return train, test


def fit_predict(train, test, settings):
    model = make_pipeline(ColumnTransformer([
        ('district', OneHotEncoder(handle_unknown='error', sparse_output=False), ['district']),
        ('numeric', StandardScaler(), NUMERIC)]), PoissonRegressor(
            alpha=settings['alpha'], max_iter=settings['max_iter'], tol=settings['tol']))
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        model.fit(train[['district'] + NUMERIC], train['count'])
    pred = model.predict(test[['district'] + NUMERIC])
    if not np.isfinite(pred).all() or (pred < 0).any():
        raise ValueError('Invalid predictions')
    return pred


def evaluate(protocol_path=PROTOCOL, out=OUT, root=ROOT):
    config = json.loads(protocol_path.read_text())
    pending = check_protocol(config, root)
    if pending:
        raise ValueError('Pending: ' + ', '.join(pending))
    lock = json.loads((out / 'protocol_lock.json').read_text())
    expected = {'protocol_sha256': sha(protocol_path), 'implementation_sha256': sha(__file__),
                'shared_implementation_sha256': sha(root / 'src/demand_forecasting.py'),
                'requirements_sha256': sha(root / 'requirements-forecasting.txt')}
    if any(lock.get(k) != v for k, v in expected.items()):
        raise ValueError('Frozen protocol or implementation changed')
    if lock.get('runtime_versions') != versions():
        raise ValueError('Software versions differ from the frozen environment')
    started = out / 'evaluation_started.json'
    # Exclusive creation prevents an accidental second look after outcomes are visible.
    with started.open('x') as f:
        json.dump({'protocol_sha256': expected['protocol_sha256'],
                   'started_utc': pd.Timestamp.now(tz='UTC').isoformat()}, f, indent=2)
    raw = pd.read_csv(root / 'data/processed/illegal_dumping_cleaned.csv',
                      dtype={'request_id': 'string'})
    if raw.request_id.isna().any() or raw.request_id.duplicated().any():
        raise ValueError('Missing or duplicate request IDs')
    raw['date_created'] = pd.to_datetime(raw.date_created, errors='raise')
    history = raw.loc[raw.date_created.ge('2018-01-01')
                      & raw.date_created.lt('2026-01-01')].copy()
    geojson = json.loads((root / 'data/reference/council_districts_snapshot.geojson').read_text())
    mapped = assign_districts(history, geojson)
    usable = mapped.loc[mapped.location_matches.eq(1)].copy()
    usable['week_start'] = usable.date_created.dt.normalize() - pd.to_timedelta(
        usable.date_created.dt.dayofweek, unit='D')
    districts = sorted(int(f['properties']['DISTRICT']) for f in geojson['features'])
    if districts != list(range(1, 11)):
        raise ValueError('Expected ten distinct districts')
    weeks = pd.date_range('2018-01-01', '2025-12-22', freq='W-MON')
    grid = pd.MultiIndex.from_product([districts, weeks], names=['district', 'week_start'])
    panel = usable.groupby(['district', 'week_start']).size().reindex(grid, fill_value=0)
    train, test = partition(panel.rename('count').reset_index(), config)
    if len(train) != 2600 or len(test) != 510:
        raise ValueError('Unexpected complete-week row counts')
    predictions, scores = [], []
    for name, pred in [('previous_week', test.lag_1.to_numpy()),
                       ('four_week_average', test.rolling_4.to_numpy()),
                       ('poisson', fit_predict(train, test, config['model']))]:
        frame = test[['district', 'week_start', 'count']].copy()
        frame['experiment'], frame['prediction'] = name, pred
        predictions.append(frame)
        scores.append({'model': name, 'training_rows': len(train), 'test_rows': len(test),
                       **metrics(test['count'], pred)})
    predictions = pd.concat(predictions, ignore_index=True)
    predictions.to_csv(out / 'test_predictions.csv', index=False)
    pd.DataFrame(scores).to_csv(out / 'test_metrics.csv', index=False)
    district_scores = []
    for (name, district), group in predictions.groupby(['experiment', 'district']):
        district_scores.append({'model': name, 'district': int(district),
                                **metrics(group['count'], group.prediction)})
    pd.DataFrame(district_scores).to_csv(out / 'district_metrics.csv', index=False)
    figure, ax = plt.subplots(figsize=(10, 4))
    observed = test.groupby('week_start')['count'].sum()
    ax.plot(observed.index, observed, color='black', label='observed')
    for name, group in predictions.groupby('experiment'):
        totals = group.groupby('week_start').prediction.sum()
        ax.plot(totals.index, totals, label=name.replace('_', ' '))
    ax.set(title='2025 final test: weekly citywide totals', ylabel='Reports')
    ax.legend(); figure.tight_layout()
    figure.savefig(out / 'test_timeseries.png', dpi=180); plt.close(figure)
    figure, ax = plt.subplots(figsize=(10, 4))
    pd.DataFrame(district_scores).pivot(index='district', columns='model', values='mae').plot.bar(ax=ax)
    ax.set(title='2025 final test: district error', ylabel='MAE (reports per district-week)')
    figure.tight_layout(); figure.savefig(out / 'district_mae.png', dpi=180); plt.close(figure)
    mapped.groupby([mapped.date_created.dt.year.rename('year'), 'location_matches']).size().rename(
        'requests').to_csv(out / 'location_audit.csv')
    manifest = {**expected, 'test_evaluated': True, 'model_refit': '2020-2024 complete weeks',
                'test_weeks': '2025-01-06 through 2025-12-22 (51 weeks)',
                'forecast_protocol': 'Fixed fitted model; observed completed prior weeks supply history',
                **versions(),
                'limitations': config['decisions'],
                'predictions_sha256': sha(out / 'test_predictions.csv')}
    (out / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'freeze', 'evaluate'])
    args = parser.parse_args()
    try:
        if args.command == 'check':
            pending = check_protocol(json.loads(PROTOCOL.read_text()))
            print(json.dumps({'ready_to_freeze': not pending, 'pending': pending,
                              'test_evaluated': False}, indent=2))
            return 2 if pending else 0
        print(json.dumps(freeze() if args.command == 'freeze' else evaluate(), indent=2))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
