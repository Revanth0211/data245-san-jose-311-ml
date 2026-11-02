"""Revanth's reproducible, provisional one-week-ahead demand experiment.

Run from the repository root: python src/demand_forecasting.py
2025 is deliberately excluded from aggregation and evaluation.
"""
from pathlib import Path
import hashlib
import json
import platform
import warnings

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.exceptions import ConvergenceWarning
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/demand_forecasting'
FIG = ROOT / 'reports/figures/demand_forecasting'
DATA = ROOT / 'data/processed/illegal_dumping_cleaned.csv'
BOUNDARY = ROOT / 'data/reference/council_districts_snapshot.geojson'
NUMERIC = ['lag_1', 'lag_2', 'lag_4', 'rolling_4', 'rolling_13', 'sin_year', 'cos_year']


def features(panel):
    """Require a continuous weekly grid so shifts cannot jump missing weeks."""
    panel = panel.sort_values(['district', 'week_start']).copy()
    for _, group in panel.groupby('district'):
        if not group.week_start.diff().dropna().eq(pd.Timedelta(days=7)).all():
            raise ValueError('Weekly grid must be continuous')
    grouped = panel.groupby('district')['count']
    for lag in [1, 2, 4]:
        panel[f'lag_{lag}'] = grouped.shift(lag)
    for window in [4, 13]:
        panel[f'rolling_{window}'] = grouped.transform(
            lambda values: values.shift(1).rolling(window, min_periods=window).mean())
    phase = 2 * np.pi * panel.week_start.dt.dayofyear / 365.25
    panel['sin_year'], panel['cos_year'] = np.sin(phase), np.cos(phase)
    return panel


def assign_districts(frame, geojson):
    points = shapely.points(frame.longitude.to_numpy(), frame.latitude.to_numpy())
    assigned = np.zeros(len(frame), dtype=int)
    matches = np.zeros(len(frame), dtype=int)
    for feature in geojson['features']:
        polygon = shape(feature['geometry'])
        if not polygon.is_valid:
            raise ValueError('Invalid district geometry; review the archived source')
        shapely.prepare(polygon)
        mask = shapely.covers(polygon, points)
        assigned[mask] = int(feature['properties']['DISTRICT'])
        matches += mask
    result = frame.copy()
    result['district'] = assigned
    result['location_matches'] = matches
    return result


def metrics(actual, predicted):
    return {'mae': mean_absolute_error(actual, predicted),
            'rmse': float(np.sqrt(mean_squared_error(actual, predicted)))}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(DATA, dtype={'request_id': 'string'})
    raw['date_created'] = pd.to_datetime(raw.date_created, errors='raise')
    if raw.request_id.duplicated().any():
        raise ValueError('Duplicate request IDs')
    # Provisional interpretation: timestamps are San Jose local wall-clock times.
    # No UTC conversion is invented. This assumption requires team confirmation.
    development = raw.loc[raw.date_created.between('2018-01-01', '2024-12-31 23:59:59')].copy()
    geojson = json.loads(BOUNDARY.read_text())
    mapped = assign_districts(development, geojson)
    audit = mapped.groupby([mapped.date_created.dt.year.rename('year'), 'location_matches']).size().rename('requests').reset_index()
    audit.to_csv(OUT / 'location_audit.csv', index=False)
    mapped.loc[mapped.location_matches.ne(1), ['request_id', 'source_year', 'location_matches']].to_csv(
        ROOT / 'data/processed/forecast_location_exclusions.csv', index=False)
    usable = mapped.loc[mapped.location_matches.eq(1)].copy()
    usable['week_start'] = usable.date_created.dt.normalize() - pd.to_timedelta(usable.date_created.dt.dayofweek, unit='D')
    weeks = pd.date_range('2018-01-01', '2024-12-23', freq='W-MON')
    districts = sorted(int(f['properties']['DISTRICT']) for f in geojson['features'])
    grid = pd.MultiIndex.from_product([districts, weeks], names=['district', 'week_start'])
    # Zero fill is provisional, conditional on the annual exports being complete.
    counts = usable.groupby(['district', 'week_start']).size().reindex(grid, fill_value=0)
    panel = features(counts.rename('count').reset_index())
    panel['week_end'] = panel.week_start + pd.Timedelta(days=6)
    panel['split'] = np.where(panel.week_end.lt(pd.Timestamp('2024-01-01')), 'train', 'validation')
    panel['coverage_status'] = 'assumed_complete_pending_team_confirmation'
    panel.to_csv(ROOT / 'data/processed/district_week_development.csv', index=False)
    ready = panel.dropna(subset=NUMERIC).copy()
    validation = ready.loc[ready.split.eq('validation')]
    scores, predictions, district_scores = [], [], []
    for start in [2018, 2020]:
        train = ready.loc[ready.split.eq('train') & ready.week_start.ge(f'{start}-01-01')]
        assert train.week_end.max() < validation.week_start.min()
        model = make_pipeline(ColumnTransformer([
            ('district', OneHotEncoder(handle_unknown='error', sparse_output=False), ['district']),
            ('numeric', StandardScaler(), NUMERIC)]),
            PoissonRegressor(alpha=1.0, max_iter=2000, tol=1e-8))
        with warnings.catch_warnings():
            warnings.simplefilter('error', ConvergenceWarning)
            model.fit(train[['district'] + NUMERIC], train['count'])
        for name, pred in [('previous_week', validation.lag_1.to_numpy()),
                           ('four_week_average', validation.rolling_4.to_numpy()),
                           ('poisson', model.predict(validation[['district'] + NUMERIC]))]:
            tag = f'{name}_{start}'
            scores.append({'model': name, 'training_start': start, 'train_rows': len(train),
                           'validation_rows': len(validation), **metrics(validation['count'], pred)})
            output = validation[['district', 'week_start', 'count']].copy()
            output['prediction'], output['experiment'] = pred, tag
            predictions.append(output)
            for district, group in output.groupby('district'):
                district_scores.append({'experiment': tag, 'district': district,
                                        **metrics(group['count'], group.prediction)})
    scores = pd.DataFrame(scores)
    scores.to_csv(OUT / 'validation_metrics.csv', index=False)
    prediction_table = pd.concat(predictions, ignore_index=True)
    prediction_table.to_csv(OUT / 'validation_predictions.csv', index=False)
    pd.DataFrame(district_scores).to_csv(OUT / 'district_metrics.csv', index=False)
    fig, ax = plt.subplots(figsize=(10, 4))
    chart_experiments = {
        'previous_week_2018': 'previous week',
        'four_week_average_2018': 'four-week average',
        'poisson_2020': 'Poisson (train 2020–2023)',
    }
    for name, label in chart_experiments.items():
        group = prediction_table.loc[prediction_table.experiment.eq(name)]
        city = group.groupby('week_start')[['count', 'prediction']].sum()
        ax.plot(city.index, city.prediction, label=label)
    ax.plot(city.index, city['count'], color='black', label='observed', linewidth=2)
    ax.set(title='Provisional 2024 validation: weekly citywide totals', ylabel='Requests')
    ax.legend(); fig.tight_layout(); fig.savefig(FIG / 'validation_timeseries.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4))
    ds = pd.DataFrame(district_scores)
    district_chart = ds.loc[ds.experiment.isin(chart_experiments)].copy()
    district_chart['model'] = district_chart.experiment.map(chart_experiments)
    district_chart.pivot(index='district', columns='model', values='mae').plot.bar(ax=ax)
    ax.set(title='Provisional validation error by district', ylabel='MAE (requests per district-week)')
    fig.tight_layout(); fig.savefig(FIG / 'district_mae.png', dpi=160); plt.close(fig)
    manifest = {'input_sha256': hashlib.sha256(DATA.read_bytes()).hexdigest(),
                'boundary_sha256': hashlib.sha256(BOUNDARY.read_bytes()).hexdigest(),
                'python': platform.python_version(), 'pandas': pd.__version__,
                'boundary_source': 'https://geo.sanjoseca.gov/server/rest/services/PLN/PLN_AdministrativeBoundaries/MapServer/1',
                'test_evaluated': False, 'status': 'provisional',
                'development_requests': len(development), 'mapped_requests': len(usable),
                'assumptions': ['Naive source timestamps treated as local wall clock',
                                'Annual exports assumed complete; zero filling is conditional',
                                'One current archived district geometry applied to all years; retrospective geography',
                                'Member 1 coordinate exclusions retained unchanged'],
                'forecast_protocol': 'Fixed fitted model; one-week-ahead forecasts with actual completed prior-week counts'}
    (OUT / 'run_manifest.json').write_text(json.dumps(manifest, indent=2))
    print(scores.to_string(index=False))
    return scores


if __name__ == '__main__':
    run()
