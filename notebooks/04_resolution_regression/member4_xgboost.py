"""Member 4: reproducible, PROVISIONAL XGBoost district-week forecasts.

Run from the repository root:
  python notebooks/04_resolution_regression/member4_xgboost.py --provisional
  python notebooks/04_resolution_regression/member4_xgboost.py --provisional --with-member2

Uses Member 5's pre-built district-week panel unchanged. Optional Member 2 features
are computed using Member 2's module, NOT independently re-implemented here.
Train: 2020-2023. Validation: 2024. 2025 is never read or scored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor
import xgboost
import sklearn

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL = ROOT / 'data/processed/district_week_development.csv'
DEFAULT_RESULTS = ROOT / 'results/member4_xgboost'
DEFAULT_FIGURES = ROOT / 'reports/figures/member4_xgboost'
DEFAULT_TEAM_PREDS = ROOT / 'results/demand_forecasting/validation_predictions.csv'
SHARED = ['lag_1', 'lag_2', 'lag_4', 'rolling_4', 'rolling_13', 'sin_year', 'cos_year']
M2_LAGS = ['month', 'week_of_year', 'sin_year', 'cos_year', 'lag_1', 'lag_2', 'lag_4', 'lag_8']
M2_FULL = M2_LAGS + ['rolling_4', 'rolling_8', 'rolling_13',
                     'rolling_std_4', 'rolling_std_8', 'recent_change_1_4']
FEATURE_SETS = {'shared': SHARED, 'member2_lags': M2_LAGS, 'member2_full': M2_FULL}
# Contract checked by the notebook and an end-to-end regression test.
ARTIFACT_API_VERSION = 2
# Predeclared fixed configuration; no hyperparameter tuning and no test-set access.
PARAMS = dict(objective='reg:squarederror', n_estimators=250, max_depth=4,
              learning_rate=0.05, subsample=0.85, colsample_bytree=0.85,
              min_child_weight=3, reg_lambda=1.0, tree_method='hist',
              random_state=42, n_jobs=2)


def scores(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if len(actual) == 0 or actual.shape != predicted.shape:
        raise ValueError('Empty or mismatched evaluation vectors')
    if not (np.isfinite(actual).all() and np.isfinite(predicted).all()):
        raise ValueError('Non-finite validation target or prediction')
    return {'rows': int(len(actual)),
            'mae': float(mean_absolute_error(actual, predicted)),
            'rmse': float(np.sqrt(mean_squared_error(actual, predicted)))}


def load_panel(path: Path):
    """Validate ONLY the shared 2018-2024 development panel (no 2025)."""
    if not path.is_file():
        raise FileNotFoundError(f'Shared district-week panel missing: {path}\n'
                                'From the repository root run: python src/demand_forecasting.py')
    panel = pd.read_csv(path)
    required = ['district', 'week_start', 'week_end', 'split', 'count',
                'coverage_status', *SHARED]
    missing = sorted(set(required) - set(panel.columns))
    if missing:
        raise ValueError(f'Shared panel is missing columns: {missing}')
    for date_col in ['week_start', 'week_end']:
        panel[date_col] = pd.to_datetime(panel[date_col], errors='raise')
    if panel[required].isna().any().any():
        # Historical warmup features are legitimately null; check keys separately.
        if panel[['district', 'week_start', 'week_end', 'split', 'count']].isna().any().any():
            raise ValueError('Null district/week/split/target values')
    if panel.duplicated(['district', 'week_start']).any():
        raise ValueError('Duplicate district-week keys')
    if not panel.week_start.dt.dayofweek.eq(0).all():
        raise ValueError('Non-Monday week start')
    if not (panel.week_end == panel.week_start + pd.Timedelta(days=6)).all():
        raise ValueError('Non-complete Monday-Sunday week')
    if panel.week_start.min() < pd.Timestamp('2018-01-01') or panel.week_end.max() >= pd.Timestamp('2025-01-01'):
        raise ValueError('Development-only panel expected: NEVER include 2025')
    if not panel['split'].isin(['train', 'validation']).all():
        raise ValueError('Unexpected split label')
    istrain = panel.week_end.lt(pd.Timestamp('2024-01-01'))
    isvalid = panel.week_start.ge(pd.Timestamp('2024-01-01')) & panel.week_end.lt(pd.Timestamp('2025-01-01'))
    if not ((istrain & panel.split.eq('train')) | (isvalid & panel.split.eq('validation'))).all():
        raise ValueError('Split/date mismatch or split-crossing week')
    counts = pd.to_numeric(panel['count'], errors='raise')
    if counts.lt(0).any() or not np.isfinite(counts).all() or not np.allclose(counts, np.round(counts)):
        raise ValueError('Target counts must be finite nonnegative integers')
    if panel[SHARED].isin([np.inf, -np.inf]).any().any():
        raise ValueError('Infinite input feature values')
    for district, block in panel.sort_values('week_start').groupby('district'):
        if not block.week_start.diff().dropna().eq(pd.Timedelta(days=7)).all():
            raise ValueError(f'Non-contiguous week history for district {district}')
    return panel.sort_values(['week_start', 'district']).reset_index(drop=True)


def add_member2_features(panel):
    """Optional: compute exact features from Member 2 module; check shared fields."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from src.eda_features import add_forecasting_features
    except ImportError as ex:
        raise ImportError('Member 2 src/eda_features.py is missing. Merge/pull '
                          'Member 2 PR before running --with-member2.') from ex
    newer = add_forecasting_features(panel[['district', 'week_start', 'count']].copy())
    newer = newer[['district', 'week_start', *M2_FULL]].copy()
    # Avoid overwriting Member 5's canonical seven shared features.
    additional = [f for f in M2_FULL if f not in SHARED]
    joined = panel.merge(newer[['district', 'week_start', *additional]],
                         on=['district', 'week_start'], how='left', validate='one_to_one',
                         sort=False)
    reference = panel[['district', 'week_start', *SHARED]].merge(
        newer[['district', 'week_start', *[f for f in SHARED if f in newer.columns]]],
        on=['district', 'week_start'], how='left', validate='one_to_one', suffixes=('_team', '_m2'))
    # Check overlapping lag, mean and cyclic calendar definitions for consistency.
    for col in SHARED:
        a, b = reference[f'{col}_team'].to_numpy(dtype=float), reference[f'{col}_m2'].to_numpy(dtype=float)
        if not np.allclose(a, b, equal_nan=True, rtol=1e-10, atol=1e-10):
            raise ValueError(f'Member 2 feature definition differs from Member 5: {col}')
    return joined


def choose_rows(panel, feature_cols):
    """Keep the *same* common scoring cohort for all compared models."""
    needed = sorted(set(SHARED + M2_FULL) & set(panel.columns))
    if not set(feature_cols).issubset(panel.columns):
        raise ValueError(f'Missing model features: {sorted(set(feature_cols) - set(panel.columns))}')
    # Member 5 drops NA only on seven shared features. Member 2 features are
    # fully available by 2020 and must NOT silently change that common cohort.
    ready = panel.dropna(subset=SHARED).copy()
    train = ready.loc[ready.split.eq('train') &
                      ready.week_start.ge(pd.Timestamp('2020-01-01'))].copy()
    valid = ready.loc[ready.split.eq('validation')].copy()
    if train.empty or valid.empty:
        raise ValueError('Empty 2020-2023 training set or 2024 validation set')
    if train.week_end.max() >= valid.week_start.min():
        raise ValueError('Train/validation time overlap')
    if not (train.week_start.dt.year.between(2020, 2023).all() and
            valid.week_start.dt.year.eq(2024).all()):
        raise ValueError('Unexpected train or validation dates')
    for name, subset in [('train', train), ('validation', valid)]:
        if subset[feature_cols].isna().any().any() or not np.isfinite(subset[feature_cols].to_numpy(dtype=float)).all():
            raise ValueError(f'Missing or non-finite {name} features; no imputation allowed')
    return train.reset_index(drop=True), valid.reset_index(drop=True)


def check_team_validation(valid, team_predictions_path):
    if not team_predictions_path.is_file():
        # Explicitly reported; can still score but cannot claim exact cross-check.
        return {'team_validation_crosscheck': 'unavailable (team predictions file absent)'}
    others = pd.read_csv(team_predictions_path)
    required = ['district', 'week_start', 'count', 'experiment']
    if not set(required).issubset(others.columns):
        raise ValueError('Unexpected Member 5 validation_predictions.csv schema')
    others = others.loc[others.experiment.eq('poisson_2020'), ['district', 'week_start', 'count']].copy()
    if others.empty:
        raise ValueError('Member 5 Poisson 2020 validation rows not found')
    others['week_start'] = pd.to_datetime(others['week_start'])
    lhs = valid[['district', 'week_start', 'count']].sort_values(['week_start','district']).reset_index(drop=True)
    rhs = others.sort_values(['week_start','district']).reset_index(drop=True)
    if len(lhs) != len(rhs) or not lhs.equals(rhs):
        # Type differences (ints/floats) are permitted only for numeric count equivalence.
        if len(lhs) != len(rhs) or not lhs[['district','week_start']].equals(rhs[['district','week_start']]) or not np.allclose(lhs['count'], rhs['count']):
            raise ValueError('Validation rows/targets differ from Member 5 Poisson 2020')
    return {'team_validation_crosscheck': 'passed', 'team_poisson_rows': len(rhs)}


def make_pipeline(features):
    transform = ColumnTransformer([
        ('district', OneHotEncoder(handle_unknown='error', sparse_output=False), ['district']),
        ('numeric', 'passthrough', features),
    ])
    return Pipeline([('transform', transform), ('xgb', XGBRegressor(**PARAMS))])


def evaluate_groups(pred, group_by):
    rows = []
    grouper = group_by if isinstance(group_by, list) else [group_by]
    for key, grp in pred.groupby(grouper, dropna=False):
        keys = key if isinstance(key, tuple) else (key,)
        row = {col: (bool(value) if isinstance(value, (np.bool_, bool)) else value)
               for col, value in zip(grouper, keys)}
        row.update(scores(grp['actual_count'], grp['prediction']))
        row['mean_bias_prediction_minus_actual'] = float((grp.prediction - grp.actual_count).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def annotate_busy(pred, train):
    """Busy labels are POST-HOC and use observed validation target ONLY for evaluation."""
    out = pred.copy()
    district_p90 = train.groupby('district')['count'].quantile(.9)
    out['district_busy_threshold_train_p90'] = out.district.map(district_p90)
    out['busy_district_week'] = out.actual_count >= out.district_busy_threshold_train_p90
    train_city = train.groupby('week_start')['count'].sum()
    city_cut = float(train_city.quantile(.9))
    val_city = out.groupby('week_start')['actual_count'].sum()
    out['busy_citywide_week'] = out.week_start.map(val_city.ge(city_cut))
    return out, city_cut


def resolve_primary_experiment(experiments, primary_experiment=None):
    """Choose the predeclared reporting focus; do not infer it from test results.

    Member 2's lag set is the main analysis when that module is available;
    shared remains the fully reproducible fallback when it is absent.
    """
    available = list(experiments)
    chosen = primary_experiment or ('member2_lags' if 'member2_lags' in available else 'shared')
    if chosen not in experiments:
        raise ValueError(f'Primary experiment {chosen!r} unavailable. Choose from: {available}')
    return chosen


def primary_rows(table, primary_experiment):
    """Extract exactly the model used for district, busy-week and plot interpretation."""
    selected = table.loc[table.experiment.eq(primary_experiment)].copy()
    if selected.empty:
        raise ValueError(f'No rows found for primary analysis: {primary_experiment}')
    return selected


def write_figures(pred, district, busy, metrics, importance, figdir, *, primary_experiment):
    figdir.mkdir(parents=True, exist_ok=True)
    all_metrics = metrics.sort_values('mae')
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.barh(all_metrics.experiment, all_metrics.mae)
    ax.invert_yaxis(); ax.set(xlabel='Validation MAE (reports per district-week)',
                               title='2024 validation: XGBoost feature sets (provisional)')
    for i, v in enumerate(all_metrics.mae): ax.text(v+.15, i, f'{v:.2f}', va='center', fontsize=9)
    ax.set_xlim(0, max(all_metrics.mae) * 1.16)
    fig.tight_layout(); fig.savefig(figdir/'model_comparison.png', dpi=170); plt.close(fig)

    base_district = primary_rows(district, primary_experiment).sort_values('district')
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(base_district.district.astype(str), base_district.mae)
    ax.set(xlabel='Council district', ylabel='MAE (reports per district-week)',
           title=f'XGBoost {primary_experiment}: district errors (2024, provisional)')
    fig.tight_layout(); fig.savefig(figdir/'district_mae.png', dpi=170); plt.close(fig)

    base_busy = primary_rows(busy, primary_experiment).sort_values('busy_district_week')
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = ['Non-busy', 'Busy'] if len(base_busy) == 2 else base_busy.busy_district_week.astype(str).tolist()
    ax.bar(labels, base_busy.mae)
    ax.set(ylabel='MAE (reports per district-week)',
           title=f'XGBoost {primary_experiment}: observed busy-week errors (post-hoc)')
    fig.tight_layout(); fig.savefig(figdir/'busy_week_mae.png', dpi=170); plt.close(fig)

    base = primary_rows(pred, primary_experiment)
    totals = base.groupby('week_start')[['actual_count', 'prediction']].sum()
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(totals.index, totals.actual_count, label='Observed', linewidth=1.8)
    ax.plot(totals.index, totals.prediction, label='XGBoost', linewidth=1.5)
    ax.set(ylabel='Citywide reports per week', title=f'XGBoost {primary_experiment}: 2024 weekly totals (provisional)')
    ax.legend(); fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(figdir/'weekly_citywide.png', dpi=170); plt.close(fig)

    top = primary_rows(importance, primary_experiment).nlargest(12, 'importance').sort_values('importance')
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.barh(top.feature, top.importance)
    ax.set(xlabel='XGBoost gain-normalized importance (model-provided)',
           title=f'{primary_experiment}: feature importances (not causal)')
    fig.tight_layout(); fig.savefig(figdir/'feature_importance.png', dpi=170); plt.close(fig)


def run(panel_path=DEFAULT_PANEL, results_dir=DEFAULT_RESULTS, figures_dir=DEFAULT_FIGURES,
        *, provisional=False, with_member2=False, primary_experiment=None, team_predictions=DEFAULT_TEAM_PREDS):
    if not provisional:
        raise ValueError('Team geography and coverage remain provisional: pass --provisional.')
    panel_path, results_dir, figures_dir = map(Path, [panel_path, results_dir, figures_dir])
    panel = load_panel(panel_path)
    if with_member2:
        panel = add_member2_features(panel)
    experiments = {'shared': SHARED}
    if with_member2:
        experiments.update({'member2_lags': M2_LAGS, 'member2_full': M2_FULL})
    primary_experiment = resolve_primary_experiment(experiments, primary_experiment)
    metrics, predictions, district, busy, citybusy, importance = [], [], [], [], [], []
    common_train_keys, common_valid_keys = None, None
    train_primary = valid_primary = None
    for experiment, feats in experiments.items():
        train, valid = choose_rows(panel, feats)
        train_keys = train[['district', 'week_start']].reset_index(drop=True)
        valid_keys = valid[['district', 'week_start']].reset_index(drop=True)
        if common_train_keys is None:
            common_train_keys, common_valid_keys = train_keys, valid_keys
            train_primary, valid_primary = train, valid
        elif not (common_train_keys.equals(train_keys) and common_valid_keys.equals(valid_keys)):
            raise ValueError('Different comparison cohorts: violates team agreement')
        model = make_pipeline(feats)
        model.fit(train[['district', *feats]], train['count'])
        prediction = np.maximum(model.predict(valid[['district', *feats]]), 0.0)
        pred = valid[['district','week_start','count']].copy().rename(columns={'count':'actual_count'})
        pred['experiment'] = experiment
        pred['prediction'] = prediction
        pred['absolute_error'] = np.abs(pred.prediction - pred.actual_count)
        pred['signed_error'] = pred.prediction - pred.actual_count
        pred, city_cut = annotate_busy(pred, train)
        row = {'experiment':experiment, 'training_start':2020, 'training_end':2023,
               'training_rows':len(train), 'validation_year':2024,
               'validation_rows':len(valid), 'numeric_feature_count':len(feats),
               'status':'provisional', **scores(pred.actual_count,pred.prediction)}
        metrics.append(row)
        predictions.append(pred)
        bydist = evaluate_groups(pred, 'district'); bydist.insert(0, 'experiment', experiment)
        district.append(bydist)
        bybusy = evaluate_groups(pred, 'busy_district_week'); bybusy.insert(0, 'experiment', experiment)
        busy.append(bybusy)
        bycitybusy = evaluate_groups(pred, 'busy_citywide_week'); bycitybusy.insert(0, 'experiment', experiment)
        citybusy.append(bycitybusy)
        names = model.named_steps['transform'].get_feature_names_out()
        importance.append(pd.DataFrame({'experiment':experiment, 'feature':names,
                                        'importance':model.named_steps['xgb'].feature_importances_}))
    check = check_team_validation(valid_primary, Path(team_predictions))
    metrics_df = pd.DataFrame(metrics)
    preds_df = pd.concat(predictions, ignore_index=True)
    district_df = pd.concat(district, ignore_index=True)
    busy_df = pd.concat(busy, ignore_index=True)
    citybusy_df = pd.concat(citybusy, ignore_index=True)
    importance_df = pd.concat(importance, ignore_index=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    outputs = dict(validation_metrics=metrics_df, validation_predictions=preds_df,
                   district_metrics=district_df, busy_week_metrics=busy_df,
                   citywide_busy_week_metrics=citybusy_df, feature_importance=importance_df)
    for name, table in outputs.items():
        if name == 'validation_predictions':
            table = table.copy()
            table['week_start'] = table['week_start'].dt.strftime('%Y-%m-%d')
        table.to_csv(results_dir / f'{name}.csv', index=False)
    write_figures(preds_df, district_df, busy_df, metrics_df, importance_df, figures_dir,
                  primary_experiment=primary_experiment)
    manifest = dict(artifact_api_version=ARTIFACT_API_VERSION,
                    status='provisional', train_window='2020-2023', validation='2024',
                    final_test_2025_accessed=False, panel_path=(str(panel_path.relative_to(ROOT)) if panel_path.is_relative_to(ROOT) else str(panel_path)),
                    panel_sha256=hashlib.sha256(panel_path.read_bytes()).hexdigest(),
                    experiment_names=list(experiments), primary_analysis_experiment=primary_experiment,
                    features=experiments,
                    xgb_settings=PARAMS, training_rows=len(train_primary), validation_rows=len(valid_primary),
                    validation_week_count=valid_primary.week_start.nunique(),
                    validation_district_count=valid_primary.district.nunique(),
                    coverage_statuses=sorted(panel.coverage_status.astype(str).unique().tolist()),
                    timezone='naive local wall-clock (provisional team convention)',
                    test_evaluated=False, team_validation_check=check,
                    generated_utc=datetime.now(timezone.utc).isoformat(),
                    software=dict(python=platform.python_version(), xgboost=xgboost.__version__,
                                  sklearn=sklearn.__version__, pandas=pd.__version__, numpy=np.__version__),
                    caveats=['Reported demand != dumping incidents',
                             'Archived geographic boundaries applied retrospectively',
                             'Completeness/zero-filling require team confirmation',
                             'Busy-week labels use observed 2024 counts for POST-HOC diagnostics only',
                             'Feature importances are not causal effects',
                             '2024 results for development; 2025 must remain untouched'])
    (results_dir/'run_manifest.json').write_text(json.dumps(manifest, indent=2, default=str), encoding='utf-8')
    print('\nPROVISIONAL 2024 VALIDATION (per district-week)')
    print(metrics_df[['experiment','training_rows','validation_rows','mae','rmse']].to_string(index=False))
    print('Primary district/busy-week/importance analysis:', primary_experiment)
    print('Team validation cross-check:', check['team_validation_crosscheck'])
    print('Files:', (results_dir.relative_to(ROOT) if results_dir.is_relative_to(ROOT) else results_dir),
          (figures_dir.relative_to(ROOT) if figures_dir.is_relative_to(ROOT) else figures_dir))
    return outputs, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_PANEL)
    parser.add_argument('--results-dir', type=Path, default=DEFAULT_RESULTS)
    parser.add_argument('--figures-dir', type=Path, default=DEFAULT_FIGURES)
    parser.add_argument('--provisional', action='store_true')
    parser.add_argument('--with-member2', action='store_true',
                        help='Run extra ablations with Member 2 src/eda_features.py; only after that PR is available')
    parser.add_argument('--primary-experiment', choices=list(FEATURE_SETS), default=None,
                        help='Model for district/busy-week/importance figures; defaults to member2_lags when enabled, else shared')
    parser.add_argument('--team-predictions', type=Path, default=DEFAULT_TEAM_PREDS)
    args = parser.parse_args()
    run(args.input, args.results_dir, args.figures_dir, provisional=args.provisional,
        with_member2=args.with_member2, primary_experiment=args.primary_experiment,
        team_predictions=args.team_predictions)


if __name__ == '__main__':
    main()
