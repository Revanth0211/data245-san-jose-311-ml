"""Reconcile saved 2024 predictions and build the forecasting presentation evidence.

This script never reads request-level data or evaluates 2025.
"""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/forecasting_presentation'
FIG = ROOT / 'reports/figures/forecasting_presentation'
SOURCES = [
    ('Previous week', 'results/demand_forecasting/validation_predictions.csv', 'previous_week_2020', 'count', 'prediction'),
    ('Four-week average', 'results/demand_forecasting/validation_predictions.csv', 'four_week_average_2020', 'count', 'prediction'),
    ('Shared Poisson', 'results/demand_forecasting/validation_predictions.csv', 'poisson_2020', 'count', 'prediction'),
    ('Member 2 Poisson + lags', 'results/member2/feature_comparison_predictions.csv', 'B_basic_lags', 'actual_count', 'prediction'),
    ('Random Forest, no rolling', 'results/member3_random_forest/random_forest_validation_predictions.csv', 'without_rolling', 'actual_count', 'predicted_count'),
    ('XGBoost + Member 2 lags', 'results/member4_xgboost/validation_predictions.csv', 'member2_lags', 'actual_count', 'prediction'),
]


def score(frame):
    error = frame.prediction - frame['count']
    return {'mae': float(error.abs().mean()), 'rmse': float(np.sqrt((error ** 2).mean())),
            'signed_bias': float(error.mean()),
            'wape_percent': float(100 * error.abs().sum() / frame['count'].sum())}


def reconcile(root=ROOT):
    tables, sources, reference = [], {}, None
    for label, path, experiment, actual, prediction in SOURCES:
        frame = pd.read_csv(root / path, parse_dates=['week_start'])
        frame = frame.loc[frame.experiment.eq(experiment),
                          ['district', 'week_start', actual, prediction]].copy()
        frame.columns = ['district', 'week_start', 'count', 'prediction']
        frame = frame.sort_values(['district', 'week_start']).reset_index(drop=True)
        if len(frame) != 520 or frame.duplicated(['district', 'week_start']).any():
            raise ValueError('Expected 520 unique validation keys: ' + label)
        if not frame.week_start.between('2024-01-01', '2024-12-23').all():
            raise ValueError('Unexpected evaluation period: ' + label)
        if not np.isfinite(frame[['count', 'prediction']]).all().all():
            raise ValueError('Non-finite values: ' + label)
        cohort = frame[['district', 'week_start', 'count']]
        if reference is None:
            reference = cohort
        else:
            pd.testing.assert_frame_equal(cohort, reference, check_dtype=False)
        frame['model'] = label
        tables.append(frame)
        sources[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    return pd.concat(tables, ignore_index=True), sources


def run(root=ROOT):
    out, fig = root / OUT.relative_to(ROOT), root / FIG.relative_to(ROOT)
    out.mkdir(parents=True, exist_ok=True)
    fig.mkdir(parents=True, exist_ok=True)
    predictions, sources = reconcile(root)
    rows = []
    for model, frame in predictions.groupby('model', sort=False):
        rows.append({'model': model, 'validation_rows': len(frame), **score(frame)})
    table = pd.DataFrame(rows)
    baseline = table.loc[table.model.eq('Four-week average'), 'mae'].iloc[0]
    table['mae_improvement_vs_four_week_percent'] = 100 * (baseline - table.mae) / baseline
    table['period'] = '2024 validation'
    table.to_csv(out / 'model_comparison.csv', index=False)
    predictions.to_csv(out / 'aligned_validation_predictions.csv', index=False)
    district_rows = []
    for (model, district), frame in predictions.groupby(['model', 'district']):
        district_rows.append({'model': model, 'district': int(district),
                              'mean_weekly_count': float(frame['count'].mean()), **score(frame)})
    districts = pd.DataFrame(district_rows)
    districts.to_csv(out / 'district_comparison.csv', index=False)
    poisson = predictions.loc[predictions.model.eq('Shared Poisson')].copy()
    poisson['absolute_error'] = (poisson.prediction - poisson['count']).abs()
    poisson.sort_values('absolute_error', ascending=False).head(10).to_csv(
        out / 'largest_poisson_errors.csv', index=False)
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
    ordered = table.sort_values('mae')
    f, ax = plt.subplots(figsize=(10, 4.8))
    bars = ax.barh(ordered.model, ordered.mae, color=['#087f8c'] + ['#8095a8'] * 5)
    ax.bar_label(bars, fmt='%.3f', padding=5)
    ax.invert_yaxis()
    ax.set(xlabel='MAE (reports per district-week)', xlim=(0, 18),
           title='2024 validation: same 520 district-weeks')
    f.tight_layout(); f.savefig(fig / 'model_comparison.png', dpi=180); plt.close(f)
    p = districts.loc[districts.model.eq('Shared Poisson')].sort_values('district')
    f, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    axes[0].bar(p.district, p.mae, color='#087f8c')
    axes[0].set(title='Poisson absolute error', ylabel='MAE (reports per district-week)')
    axes[1].bar(p.district, p.wape_percent, color='#d88732')
    axes[1].set(title='Poisson error relative to observed volume', ylabel='WAPE (%)')
    for ax in axes:
        ax.set_xticks(range(1, 11)); ax.set_xlabel('Council district')
    f.tight_layout(); f.savefig(fig / 'district_diagnostics.png', dpi=180); plt.close(f)
    manifest = {'test_evaluated': False, 'rows_per_model': 520, 'sources_sha256': sources,
                'metrics_recomputed_from': 'committed validation predictions',
                'xgboost_note': 'Saved Windows run; rounded CSV predictions can differ from stored full-precision metrics by less than 1e-5. Different platforms produced different XGBoost scores during prior review.',
                'selection_note': 'Configurations were compared on 2024; small differences do not establish statistical significance.',
                'wape_definition': '100 * sum(abs(prediction - count)) / sum(count); descriptive error relative to volume, not accuracy or a population adjustment'}
    (out / 'evidence_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(table[['model', 'mae', 'rmse', 'signed_bias']].to_string(index=False))
    return table


if __name__ == '__main__':
    run()
