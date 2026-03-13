#!/usr/bin/env python3
"""
Phase 3 Feature Testing Script

Tests all Phase 3 (Intelligence & Optimization) modules:
1. ML Signal Predictor
2. ML Pattern Recognition
3. Portfolio Optimizer
4. Risk Analytics
5. Scenario Analysis
6. Visualization/Charts
7. Report Generator
8. Web Dashboard

Author: ScreenerIII
"""

import sys
import time
import os
from datetime import datetime, date, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, '.')

# Track results
results = {}

def run_test(name, test_fn):
    """Run a test and capture result."""
    print(f"\n{'=' * 70}")
    print(f"[TEST] {name}")
    print(f"{'=' * 70}")
    try:
        test_fn()
        results[name] = "PASS"
        print(f"\n  PASS: {name}")
    except Exception as e:
        results[name] = f"FAIL: {e}"
        print(f"\n  FAIL: {name} - {e}")
        import traceback
        traceback.print_exc()


def generate_ohlcv(n=500, start_price=100.0, seed=42):
    """Generate synthetic OHLCV data."""
    np.random.seed(seed)
    dates = pd.date_range(start='2024-01-01', periods=n, freq='B')
    returns = np.random.normal(0.0002, 0.015, n)
    close = start_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.008, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.008, n)))
    open_ = close * (1 + np.random.normal(0, 0.003, n))
    volume = np.random.randint(1000, 50000, n).astype(float)

    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })
    return df


def generate_returns(n=500, n_assets=4, seed=42):
    """Generate synthetic multi-asset returns."""
    np.random.seed(seed)
    assets = ['CL', 'GC', 'SI', 'NG'][:n_assets]
    data = {}
    for i, asset in enumerate(assets):
        data[asset] = np.random.normal(0.0003 * (i + 1), 0.01 + 0.005 * i, n)
    dates = pd.date_range(start='2024-01-01', periods=n, freq='B')
    return pd.DataFrame(data, index=dates)


# ========================================================================
# TEST 1: ML Signal Predictor
# ========================================================================
def test_signal_predictor():
    from src.ml.signal_predictor import (
        FeatureEngineering, SignalQualityLabeler, SignalPredictor,
        ModelEvaluator, ModelType, PredictionResult, EvaluationResult
    )

    df = generate_ohlcv(300)

    # Test FeatureEngineering
    fe = FeatureEngineering()
    features = fe.build_features(df.copy())
    n_features = len([c for c in features.columns if c not in df.columns])
    print(f"  FeatureEngineering: {n_features} features generated")
    assert n_features > 20, f"Expected >20 features, got {n_features}"
    print(f"  Feature columns sample: {list(features.columns[:10])}")

    # Test SignalQualityLabeler
    labeler = SignalQualityLabeler(lookahead=10, profit_threshold=0.5)
    labelled = labeler.label(features.copy())
    assert 'label' in labelled.columns, "Label column missing"
    label_counts = labelled['label'].value_counts()
    print(f"  SignalQualityLabeler: {len(label_counts)} classes, distribution: {dict(label_counts)}")

    # Test SignalPredictor
    clean = labelled.dropna()
    if len(clean) < 50:
        print(f"  Warning: Only {len(clean)} clean samples, using relaxed settings")

    feature_cols = [c for c in clean.columns
                    if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']]
    X = clean[feature_cols].values
    y = clean['label'].values

    predictor = SignalPredictor(model_type=ModelType.RANDOM_FOREST, scale_features=True)
    train_info = predictor.train(X, y, feature_names=feature_cols)
    print(f"  SignalPredictor trained: {train_info}")

    # Test prediction
    preds = predictor.predict(X[:5])
    assert len(preds) == 5, "Wrong prediction count"
    assert isinstance(preds[0], PredictionResult), "Wrong prediction type"
    print(f"  Predictions: {[(p.label, round(p.confidence, 3)) for p in preds]}")

    # Test single prediction
    single = predictor.predict_single(X[:1])
    assert isinstance(single, PredictionResult)
    print(f"  Single prediction: label={single.label}, confidence={single.confidence:.3f}")

    # Test feature importance
    importance = predictor.feature_importance(top_n=5)
    print(f"  Top 5 features:\n{importance.to_string()}")

    # Test ModelEvaluator
    evaluator = ModelEvaluator()
    y_pred = np.array([p.label for p in predictor.predict(X)])
    y_prob = np.array([p.probabilities.get(1, p.confidence) for p in predictor.predict(X)])
    eval_result = evaluator.evaluate(y, y_pred, y_prob)
    assert isinstance(eval_result, EvaluationResult)
    print(f"  Evaluation: accuracy={eval_result.accuracy:.3f}, f1={eval_result.f1:.3f}, roc_auc={eval_result.roc_auc:.3f}")


# ========================================================================
# TEST 2: ML Pattern Recognition
# ========================================================================
def test_pattern_recognition():
    from src.ml.pattern_recognition import (
        MLPatternDetector, AnomalyDetector, RegimeDetector,
        CandlestickClassifier, PatternType, RegimeType, AnomalyType
    )

    df = generate_ohlcv(200)

    # Test MLPatternDetector
    detector = MLPatternDetector(min_confidence=0.3, n_estimators=50)
    detector.fit(samples_per_pattern=50)
    print(f"  MLPatternDetector fitted with {len(PatternType)} pattern types")

    patterns = detector.detect(df)
    print(f"  Detected {len(patterns)} patterns")
    for p in patterns[:3]:
        print(f"    {p.pattern_type.value}: confidence={p.confidence:.2f}, direction={p.direction}")

    # Test AnomalyDetector
    anomaly_det = AnomalyDetector(zscore_threshold=2.5, lookback=20)
    anomalies = anomaly_det.detect_all(df)
    print(f"  AnomalyDetector: {len(anomalies)} anomalies found")
    for a in anomalies[:3]:
        print(f"    {a.anomaly_type.value}: severity={a.severity:.2f} at index {a.index}")

    # Test RegimeDetector
    regime_det = RegimeDetector(lookback=30)
    regimes = regime_det.detect(df)
    print(f"  RegimeDetector: {len(regimes)} regime periods")
    for r in regimes[:3]:
        print(f"    {r.regime.value}: confidence={r.confidence:.2f}, volatility={r.volatility_level}")

    current = regime_det.detect_current(df)
    print(f"  Current regime: {current.regime.value} (confidence={current.confidence:.2f})")

    # Test CandlestickClassifier
    candle_clf = CandlestickClassifier(n_estimators=50, min_confidence=0.1)
    candle_clf.fit(samples_per_pattern=50)
    # Classify all bars with enough context
    all_classified = candle_clf.classify(df)
    print(f"  CandlestickClassifier: {len(all_classified)} patterns detected across {len(df)} bars")
    if all_classified:
        print(f"    Sample: {all_classified[0]}")
    else:
        # Even if no patterns pass filter, the classify method works
        print(f"    No patterns above confidence threshold (expected with synthetic data)")


# ========================================================================
# TEST 3: Portfolio Optimizer
# ========================================================================
def test_portfolio_optimizer():
    from src.ml.portfolio_optimizer import (
        PortfolioOptimizer, RiskParityAllocator, DynamicAllocator,
        CorrelationAnalyzer, PositionSizer, PortfolioResult,
        PortfolioConstraints, OptimizationObjective
    )

    returns = generate_returns(300, 4)

    # Test PortfolioOptimizer
    optimizer = PortfolioOptimizer(returns, risk_free_rate=0.02)

    mv = optimizer.minimum_variance()
    assert isinstance(mv, PortfolioResult)
    print(f"  Min Variance: return={mv.expected_return:.4f}, vol={mv.volatility:.4f}, sharpe={mv.sharpe_ratio:.4f}")
    print(f"    Weights: {mv.weights}")

    ms = optimizer.maximum_sharpe()
    print(f"  Max Sharpe: return={ms.expected_return:.4f}, vol={ms.volatility:.4f}, sharpe={ms.sharpe_ratio:.4f}")
    print(f"    Weights: {ms.weights}")

    # Test constrained optimization
    constraints = PortfolioConstraints(min_weight=0.05, max_weight=0.50)
    mv_c = optimizer.minimum_variance(constraints=constraints)
    for w in mv_c.weights.values():
        assert w >= 0.05 - 0.01 and w <= 0.50 + 0.01, f"Weight {w} out of bounds"
    print(f"  Constrained Min Var: {mv_c.weights}")

    # Test efficient frontier
    frontier = optimizer.efficient_frontier(n_points=10)
    print(f"  Efficient frontier: {len(frontier)} points (DataFrame: {frontier.shape})")

    # Test RiskParityAllocator
    rpa = RiskParityAllocator(returns)
    rp = rpa.allocate()
    print(f"  Risk Parity: {rp.weights}")

    iv = rpa.inverse_volatility()
    print(f"  Inverse Vol: {iv.weights}")

    rc = rpa.risk_contribution_analysis()
    print(f"  Risk contributions:\n{rc.to_string()}")

    # Test DynamicAllocator
    da = DynamicAllocator(returns, target_vol=0.10, lookback=60)
    vt_weights = da.volatility_targeting()
    print(f"  Vol targeting weights: {vt_weights}")

    mom_weights = da.momentum_allocation(momentum_window=60)
    print(f"  Momentum weights: {mom_weights}")

    # Test CorrelationAnalyzer
    ca = CorrelationAnalyzer(returns)
    corr = ca.correlation_matrix()
    print(f"  Correlation matrix:\n{corr.to_string()}")

    div_ratio = ca.diversification_ratio()
    print(f"  Diversification ratio: {div_ratio:.4f}")

    # Test PositionSizer
    ps = PositionSizer(account_value=100000, risk_per_trade=0.02)
    kelly = ps.kelly_criterion(win_rate=0.55, avg_win=200, avg_loss=100)
    print(f"  Kelly criterion: {kelly}")

    ff = ps.fixed_fractional(entry_price=50.0, stop_loss_price=48.0)
    print(f"  Fixed fractional: {ff}")


# ========================================================================
# TEST 4: Risk Analytics
# ========================================================================
def test_risk_analytics():
    from src.risk.risk_analytics import (
        RiskAnalytics, DrawdownAnalyzer, PortfolioRiskDashboard,
        RiskLimitManager, VaRMethod, VaRResult, AlertSeverity
    )

    returns_df = generate_returns(300, 4)
    portfolio_returns = returns_df.mean(axis=1)

    # Test RiskAnalytics
    ra = RiskAnalytics(portfolio_returns, risk_free_rate=0.05)

    var_hist = ra.var_historical(confidence=0.95)
    assert isinstance(var_hist, VaRResult)
    print(f"  VaR Historical (95%): {var_hist.var_value:.6f}")

    var_param = ra.var_parametric(confidence=0.95)
    print(f"  VaR Parametric (95%): {var_param.var_value:.6f}")

    var_mc = ra.var_monte_carlo(confidence=0.95, n_simulations=5000, seed=42)
    print(f"  VaR Monte Carlo (95%): {var_mc.var_value:.6f}")

    cvar = ra.cvar(confidence=0.95)
    print(f"  CVaR (95%): {cvar:.6f}")

    sharpe = ra.sharpe_ratio()
    sortino = ra.sortino_ratio()
    calmar = ra.calmar_ratio()
    print(f"  Sharpe: {sharpe:.4f}, Sortino: {sortino:.4f}, Calmar: {calmar:.4f}")

    max_dd = ra.maximum_drawdown()
    print(f"  Max drawdown: {max_dd:.4f}")

    summary = ra.summary()
    print(f"  Summary keys: {list(summary.keys())}")

    # Test DrawdownAnalyzer
    dda = DrawdownAnalyzer(portfolio_returns)
    periods = dda.drawdown_periods(top_n=3)
    print(f"  Top 3 drawdown periods: {len(periods)}")
    for p in periods:
        print(f"    Depth: {p.depth:.4f}, Duration: {p.duration_days}d")

    dd_stats = dda.drawdown_statistics()
    print(f"  Drawdown stats: {dd_stats}")

    # Test PortfolioRiskDashboard
    weights = {'CL': 0.4, 'GC': 0.3, 'SI': 0.2, 'NG': 0.1}
    prd = PortfolioRiskDashboard(returns_df, weights=weights)

    port_vol = prd.portfolio_volatility()
    port_sharpe = prd.portfolio_sharpe()
    print(f"  Portfolio vol: {port_vol:.4f}, sharpe: {port_sharpe:.4f}")

    risk_contrib = prd.percentage_risk_contribution()
    print(f"  Risk contributions: {risk_contrib.to_dict()}")

    concentration = prd.concentration_risk()
    print(f"  Concentration risk: {concentration}")

    risk_summary = prd.risk_summary()
    print(f"  Risk summary keys: {list(risk_summary.keys())}")

    # Test RiskLimitManager
    rlm = RiskLimitManager(
        config={'daily_loss_limit': 0.02, 'max_drawdown_limit': 0.10},
        warning_threshold=0.80
    )
    alert = rlm.check_daily_loss(0.019)
    print(f"  Daily loss check (1.9%): {alert}")

    alert2 = rlm.check_daily_loss(0.025)
    print(f"  Daily loss check (2.5%): severity={alert2.severity.value if alert2 else 'none'}")

    history = rlm.alert_history  # property, not method
    print(f"  Alert history: {len(history)} alerts")


# ========================================================================
# TEST 5: Scenario Analysis
# ========================================================================
def test_scenario_analysis():
    from src.risk.scenario_analysis import (
        MonteCarloSimulator, StressTester, SensitivityAnalyzer,
        WalkForwardAnalyzer, ScenarioType, SimulationResult,
        StressTestResult, quick_monte_carlo, quick_stress_test
    )

    # Test MonteCarloSimulator
    mc = MonteCarloSimulator(n_simulations=1000, time_horizon=60, random_seed=42)
    sim = mc.simulate_gbm(current_price=100.0, drift=0.05, volatility=0.20)
    assert isinstance(sim, SimulationResult)
    print(f"  Monte Carlo GBM:")
    print(f"    Expected return: {sim.expected_return:.4f}")
    print(f"    VaR 95%: {sim.var_95:.4f}")
    print(f"    VaR 99%: {sim.var_99:.4f}")
    print(f"    P(profit): {sim.probability_of_profit:.2%}")
    print(f"    P(loss): {sim.probability_of_loss:.2%}")

    # Test quick_monte_carlo
    quick_sim = quick_monte_carlo(price=50.0, drift=0.03, volatility=0.25, days=30, n_sims=500, seed=42)
    print(f"  Quick MC: VaR95={quick_sim.var_95:.4f}")

    # Test StressTester
    portfolio = {'CL': 10000, 'GC': 15000, 'SI': 5000, 'NG': 8000}
    st = StressTester(portfolio=portfolio)

    crisis = st.run_scenario(ScenarioType.FINANCIAL_CRISIS_2008)
    assert isinstance(crisis, StressTestResult)
    print(f"  Stress Test - 2008 Crisis:")
    print(f"    Portfolio impact: {crisis.portfolio_impact_pct:.2%}")
    print(f"    Worst case loss: ${crisis.worst_case_loss:,.2f}")
    print(f"    Est recovery days: {crisis.estimated_recovery_days}")

    # Run all predefined scenarios
    all_results = st.run_all_predefined()
    print(f"  All scenarios: {len(all_results)} tested")
    for r in all_results:
        print(f"    {r.scenario_name}: impact={r.portfolio_impact_pct:.2%}")

    worst = st.identify_worst_case()
    print(f"  Worst case scenario: {worst.scenario_name}")

    # Test quick_stress_test
    quick_st = quick_stress_test(portfolio, ScenarioType.COVID_2020)
    print(f"  Quick stress test (COVID): impact={quick_st.portfolio_impact_pct:.2%}")

    # Test SensitivityAnalyzer
    def portfolio_value(factors):
        return (factors.get('CL', 50) * 200 +
                factors.get('GC', 1800) * 10 +
                factors.get('SI', 25) * 500)

    base_factors = {'CL': 50.0, 'GC': 1800.0, 'SI': 25.0}
    sa = SensitivityAnalyzer(valuation_fn=portfolio_value, base_factors=base_factors)

    cl_sens = sa.single_factor_sensitivity('CL', n_points=11)
    print(f"  CL Sensitivity: delta={cl_sens.delta:.2f}, gamma={cl_sens.gamma:.4f}")

    multi = sa.multi_factor_sensitivity(['CL', 'GC', 'SI'])
    print(f"  Multi-factor sensitivity: {len(multi)} factors analyzed")

    # Test WalkForwardAnalyzer
    df = generate_ohlcv(200)
    df = df.set_index('timestamp')

    def simple_strategy(data, fast=10, slow=30):
        """Simple MA crossover returns. Returns dict with 'returns' key."""
        ma_fast = data['close'].rolling(fast).mean()
        ma_slow = data['close'].rolling(slow).mean()
        signal = (ma_fast > ma_slow).astype(float)
        ret = data['close'].pct_change() * signal.shift(1)
        return {'returns': ret.dropna().values, 'params': {'fast': fast, 'slow': slow}}

    wfa = WalkForwardAnalyzer(data=df, strategy_fn=simple_strategy)
    wf_result = wfa.run(in_sample_pct=0.70, n_windows=3, strategy_params={'fast': 10, 'slow': 30})
    print(f"  Walk-Forward Analysis:")
    print(f"    IS returns: {len(wf_result.in_sample_returns)} windows")
    print(f"    OOS returns: {len(wf_result.out_of_sample_returns)} windows")
    print(f"    Overfitting score: {wf_result.overfitting_score:.4f}")
    print(f"    Robustness score: {wf_result.robustness_score:.4f}")
    print(f"    Is robust: {wf_result.is_robust}")


# ========================================================================
# TEST 6: Visualization/Charts
# ========================================================================
def test_visualization():
    from src.visualization.charts import (
        ChartGenerator, PerformanceCharts, CorrelationVisualizer,
        RiskVisualizer, DashboardGenerator, ChartConfig, ChartStyle,
        MPL_AVAILABLE
    )

    print(f"  Matplotlib available: {MPL_AVAILABLE}")

    # Test ChartConfig
    config = ChartConfig(width=10, height=6, dpi=100, style=ChartStyle.DARK)
    print(f"  ChartConfig created: {config.width}x{config.height}, dpi={config.dpi}, style={config.style.value}")

    # Test ChartGenerator
    cg = ChartGenerator(config=config)
    print(f"  ChartGenerator initialized")

    df = generate_ohlcv(100)

    if MPL_AVAILABLE:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend

        fig = cg.candlestick(df)
        assert fig is not None
        print(f"  Candlestick chart generated")

        # Test PerformanceCharts
        pc = PerformanceCharts(config=config)
        equity = pd.Series(
            np.cumprod(1 + np.random.normal(0.001, 0.02, 200)),
            index=pd.date_range('2024-01-01', periods=200, freq='B')
        )
        fig = pc.equity_curve(equity)
        assert fig is not None
        print(f"  Equity curve chart generated")

        # Test CorrelationVisualizer
        cv = CorrelationVisualizer(config=config)
        returns = generate_returns(100, 4)
        fig = cv.correlation_matrix(returns)
        assert fig is not None
        print(f"  Correlation matrix chart generated")

        # Test RiskVisualizer
        rv = RiskVisualizer(config=config)
        ret_series = pd.Series(
            np.random.normal(0.001, 0.02, 200),
            index=pd.date_range('2024-01-01', periods=200, freq='B')
        )
        fig = rv.var_cone(ret_series, horizon=30)
        assert fig is not None
        print(f"  VaR cone chart generated")

        # Test DashboardGenerator
        dg = DashboardGenerator(layout=(2, 2), config=config)
        print(f"  DashboardGenerator initialized")

        import matplotlib.pyplot as plt
        plt.close('all')
        print(f"  All chart figures cleaned up")
    else:
        # Test data fallback methods
        print(f"  Matplotlib not available - testing data fallback mode")
        data = cg.candlestick(df)
        print(f"  Candlestick data fallback: {type(data)}")


# ========================================================================
# TEST 7: Report Generator
# ========================================================================
def test_report_generator():
    from src.reporting.report_generator import (
        ReportGenerator, HTMLReportBuilder, CSVExporter,
        PerformanceReportData, ReportFrequency, OutputFormat,
        ReportMetadata
    )

    # Create sample trade data
    trades = pd.DataFrame({
        'trade_id': range(1, 21),
        'instrument': ['CL'] * 10 + ['GC'] * 10,
        'direction': ['BUY', 'SELL'] * 10,
        'entry_price': np.random.uniform(45, 55, 20),
        'exit_price': np.random.uniform(45, 55, 20),
        'size': np.random.randint(1, 10, 20),
        'pnl': np.random.normal(100, 500, 20),
        'entry_time': pd.date_range('2024-01-01', periods=20, freq='5D'),
        'exit_time': pd.date_range('2024-01-03', periods=20, freq='5D'),
    })

    equity = pd.Series(
        np.cumprod(1 + np.random.normal(0.001, 0.02, 100)) * 10000,
        index=pd.date_range('2024-01-01', periods=100, freq='B')
    )

    # Test PerformanceReportData
    prd = PerformanceReportData(trades=trades, equity_curve=equity)
    daily = prd.daily_returns()
    print(f"  PerformanceReportData: {len(daily)} daily returns")

    # Test HTMLReportBuilder
    builder = HTMLReportBuilder(title="Test Report")
    builder.add_metric_grid({
        'Total PnL': f"${trades['pnl'].sum():,.2f}",
        'Win Rate': '55%',
        'Sharpe Ratio': '1.23',
        'Max Drawdown': '-8.5%',
    }, section_title="Key Metrics")
    builder.add_table(trades.head(5), section_title="Recent Trades", pnl_column='pnl')
    builder.add_text("This is a test report generated by Phase 3 testing.", section_title="Notes")
    html = builder.render(subtitle="Test Period")
    assert '<html' in html.lower(), "HTML render failed"
    assert 'Total PnL' in html, "Metrics not in HTML"
    print(f"  HTMLReportBuilder: rendered {len(html)} chars of HTML")

    # Test CSVExporter
    csv_dir = '/tmp/screener_test_csv'
    os.makedirs(csv_dir, exist_ok=True)
    exporter = CSVExporter(output_dir=csv_dir)
    csv_path = exporter.export_trade_history(trades, filename='test_trades.csv')
    assert os.path.exists(csv_path), "CSV file not created"
    print(f"  CSVExporter: exported to {csv_path}")

    # Test ReportGenerator
    report_dir = '/tmp/screener_test_reports'
    gen = ReportGenerator(output_dir=report_dir, default_format=OutputFormat.HTML)
    metadata = gen.daily_report(prd)
    assert isinstance(metadata, ReportMetadata)
    print(f"  ReportGenerator daily report: {metadata.report_id}")
    if metadata.file_path:
        print(f"    Saved to: {metadata.file_path}")
        assert os.path.exists(metadata.file_path), "Report file not created"

    # Test ReportFrequency enum
    assert ReportFrequency.DAILY.value == 'daily'
    assert OutputFormat.HTML.value == 'html'
    print(f"  Enums validated: ReportFrequency, OutputFormat")


# ========================================================================
# TEST 8: Web Dashboard
# ========================================================================
def test_web_dashboard():
    from src.web.app import (
        ScreenerApp, ResponseFormatter, SortOrder,
        create_app, FLASK_AVAILABLE, API_VERSION, API_PREFIX
    )

    print(f"  Flask available: {FLASK_AVAILABLE}")
    print(f"  API Version: {API_VERSION}")
    print(f"  API Prefix: {API_PREFIX}")

    if not FLASK_AVAILABLE:
        print(f"  Skipping Flask tests (Flask not installed)")
        # Test ResponseFormatter standalone
        print(f"  ResponseFormatter class exists: {ResponseFormatter is not None}")
        return

    # Test create_app
    app = create_app(debug=False)
    assert app is not None
    print(f"  Flask app created")

    # Test with Flask test client
    client = app.test_client()

    # Test health endpoint
    resp = client.get(f'{API_PREFIX}/health')
    assert resp.status_code == 200
    data = resp.get_json()
    print(f"  GET /health: {data.get('status', 'unknown')}")

    # Test markets endpoint
    resp = client.get(f'{API_PREFIX}/markets')
    assert resp.status_code == 200
    data = resp.get_json()
    markets = data.get('data', [])
    print(f"  GET /markets: {len(markets)} markets")

    # Test signals endpoint
    resp = client.get(f'{API_PREFIX}/signals')
    assert resp.status_code == 200
    data = resp.get_json()
    print(f"  GET /signals: status={resp.status_code}")

    # Test portfolio endpoint
    resp = client.get(f'{API_PREFIX}/portfolio')
    assert resp.status_code == 200
    data = resp.get_json()
    print(f"  GET /portfolio: status={resp.status_code}")

    # Test performance endpoint
    resp = client.get(f'{API_PREFIX}/performance')
    assert resp.status_code == 200
    print(f"  GET /performance: status={resp.status_code}")

    # Test risk endpoint
    resp = client.get(f'{API_PREFIX}/risk')
    assert resp.status_code == 200
    print(f"  GET /risk: status={resp.status_code}")

    # Test config endpoint
    resp = client.get(f'{API_PREFIX}/config')
    assert resp.status_code == 200
    print(f"  GET /config: status={resp.status_code}")

    # Test dashboard HTML
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'ScreenerIII' in html or 'dashboard' in html.lower()
    print(f"  GET /: Dashboard HTML loaded ({len(html)} chars)")

    # Test 404
    resp = client.get(f'{API_PREFIX}/nonexistent')
    assert resp.status_code == 404
    print(f"  GET /nonexistent: 404 handled correctly")

    # Test ResponseFormatter
    success_resp, code = ResponseFormatter.success(data={'test': True}, message='ok')
    assert code == 200
    assert success_resp['data']['test'] is True
    print(f"  ResponseFormatter.success(): works")

    error_resp, code = ResponseFormatter.error('test error', status_code=400)
    assert code == 400
    print(f"  ResponseFormatter.error(): works")

    # Test SortOrder
    assert SortOrder.ASC.value in ('asc', 'ASC')
    print(f"  SortOrder enum: {SortOrder.ASC.value}, {SortOrder.DESC.value}")


# ========================================================================
# RUN ALL TESTS
# ========================================================================
print("=" * 70)
print("PHASE 3 - COMPREHENSIVE FEATURE TESTING")
print("=" * 70)
print(f"Started: {datetime.now()}")

run_test("1. ML Signal Predictor", test_signal_predictor)
run_test("2. ML Pattern Recognition", test_pattern_recognition)
run_test("3. Portfolio Optimizer", test_portfolio_optimizer)
run_test("4. Risk Analytics", test_risk_analytics)
run_test("5. Scenario Analysis", test_scenario_analysis)
run_test("6. Visualization/Charts", test_visualization)
run_test("7. Report Generator", test_report_generator)
run_test("8. Web Dashboard", test_web_dashboard)

# ========================================================================
# SUMMARY
# ========================================================================
print("\n" + "=" * 70)
print("PHASE 3 TEST SUMMARY")
print("=" * 70)
passed = sum(1 for v in results.values() if v == "PASS")
failed = sum(1 for v in results.values() if v != "PASS")
print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}\n")

for name, result in results.items():
    icon = "PASS" if result == "PASS" else "FAIL"
    print(f"  [{icon}] {name}")
    if result != "PASS":
        print(f"         {result}")

print(f"\nCompleted: {datetime.now()}")
print("=" * 70)
