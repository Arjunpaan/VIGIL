import LiveView from './LiveView';
import { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './App.css';

function App() {
  const [portfolio, setPortfolio] = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);
  const [selectedStrategy, setSelectedStrategy] = useState('momentum_crossover_5_20');

  useEffect(() => {
    fetch('/portfolio_data.json')
      .then(res => res.json())
      .then(json => {
        setPortfolio(json);
        setSelectedStock(Object.keys(json)[0]);
      });
  }, []);

  if (!portfolio) {
    return (
      <div className="vigil-root" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
        INITIALIZING VIGIL…
      </div>
    );
  }

  const tickers = Object.keys(portfolio).sort();
  const data = portfolio[selectedStock][selectedStrategy];
  const equityChartData = data.equity_curve.map((val, i) => ({ day: i, equity: val }));

  const strategyAcrossPortfolio = tickers.map(t => ({ ticker: t, ...portfolio[t][selectedStrategy] }));
  const avgWinRate = strategyAcrossPortfolio.reduce((sum, s) => sum + s.win_rate, 0) / strategyAcrossPortfolio.length;
  const totalPortfolioTrades = strategyAcrossPortfolio.reduce((sum, s) => sum + s.total_trades, 0);
  const stocksWithDecay = strategyAcrossPortfolio.filter(s => s.decay_flags.length > 0).length;

  const winRateChartData = strategyAcrossPortfolio
    .map(s => ({ ticker: s.ticker, winRate: s.win_rate }))
    .sort((a, b) => b.winRate - a.winRate);

  const healthVar = (score, confidence) => {
    if (confidence === 'insufficient_data' || confidence === 'no_data') return 'var(--text-faint)';
    if (score >= 80) return 'var(--signal)';
    if (score >= 50) return 'var(--amber)';
    return 'var(--red)';
  };

  const healthLabel = data.confidence === 'no_data' ? 'NO TRADES RECORDED'
    : data.confidence === 'insufficient_data' ? `INSUFFICIENT DATA — ${data.total_trades} TRADES (NEED 15+)`
    : data.health_score >= 80 ? 'HEALTHY'
    : data.health_score >= 50 ? 'CAUTION — DECAY DETECTED'
    : 'WARNING — SIGNIFICANT DECAY';

  return (
    <div className="vigil-root">
      <header className="vigil-header">
        <div className="vigil-logo">
          <div className="vigil-wordmark">VI<span>◈</span>GIL</div>
          <div className="vigil-tagline">Strategy Decay Monitor</div>
        </div>
        <div className="vigil-status">
          <span className="vigil-status-dot" />
          {tickers.length} INSTRUMENTS TRACKED
        </div>
      </header>
      <LiveView />

      {/* Portfolio overview */}
      <section className="vigil-panel" style={{ animationDelay: '0ms' }}>
        <div className="vigil-panel-label">Portfolio Overview — {selectedStrategy.replace(/_/g, ' ')}</div>
        <div className="vigil-overview-grid">
          <div>
            <div className="vigil-overview-stat-label">Total Trades</div>
            <div className="vigil-overview-stat-value">{totalPortfolioTrades.toLocaleString()}</div>
          </div>
          <div>
            <div className="vigil-overview-stat-label">Avg Win Rate</div>
            <div className="vigil-overview-stat-value">{avgWinRate.toFixed(1)}%</div>
          </div>
          <div>
            <div className="vigil-overview-stat-label">Decay Flagged</div>
            <div className="vigil-overview-stat-value" style={{ color: stocksWithDecay > tickers.length / 3 ? 'var(--amber)' : 'var(--signal)' }}>
              {stocksWithDecay} / {tickers.length}
            </div>
          </div>
        </div>
      </section>

      {/* Selectors */}
      <div className="vigil-selector-row">
        <div>
          <label className="vigil-selector-label">Strategy</label>
          <select className="vigil-select" value={selectedStrategy} onChange={e => setSelectedStrategy(e.target.value)}>
            <option value="momentum_crossover_5_20">Momentum Crossover (5/20)</option>
            <option value="mean_reversion_6mo">Mean Reversion (6mo)</option>
          </select>
        </div>
        <div>
          <label className="vigil-selector-label">Instrument</label>
          <select className="vigil-select" value={selectedStock} onChange={e => setSelectedStock(e.target.value)}>
            {tickers.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      {/* Stat cards */}
      <div className="vigil-stat-grid">
        <StatCard label="Total Trades" value={data.total_trades} delay={0} />
        <StatCard label="Win Rate" value={`${data.win_rate.toFixed(1)}%`} delay={40} />
        <StatCard label="Total Return" value={`${data.total_return_pct.toFixed(2)}%`} color={data.total_return_pct > 0 ? 'var(--signal)' : 'var(--red)'} delay={80} />
        <StatCard label="Max Drawdown" value={`${data.max_drawdown_pct.toFixed(2)}%`} color="var(--red)" delay={120} />
        <StatCard label="Sharpe Ratio" value={data.sharpe_ratio.toFixed(2)} color={data.sharpe_ratio > 0 ? 'var(--signal)' : 'var(--red)'} delay={160} />
        <StatCard label="Health Score" value={data.health_score ?? 'N/A'} color={healthVar(data.health_score, data.confidence)} delay={200} />
      </div>

      {/* Equity curve */}
      <section className="vigil-panel" style={{ animationDelay: '80ms' }}>
        <div className="vigil-panel-label">{selectedStock} — Equity Curve</div>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={equityChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1c1f28" />
            <XAxis dataKey="day" stroke="#565a6b" fontSize={11} tickLine={false} />
            <YAxis stroke="#565a6b" fontSize={11} domain={['auto', 'auto']} tickLine={false} />
            <Tooltip
              contentStyle={{ background: '#12141a', border: '1px solid #2a2e3a', borderRadius: 8, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
              labelStyle={{ color: '#8b8fa3' }}
            />
            <Line type="monotone" dataKey="equity" stroke="#5eead4" strokeWidth={2} dot={false} animationDuration={900} />
          </LineChart>
        </ResponsiveContainer>
      </section>

      {/* Health score detail */}
      <section className="vigil-panel" style={{ animationDelay: '120ms' }}>
        <div className="vigil-panel-label">Decay Health Score</div>
        <div className="vigil-health-row">
          <div className="vigil-radar" style={{ '--sweep-color': healthVar(data.health_score, data.confidence) }}>
            <div className="vigil-radar-value" style={{ color: healthVar(data.health_score, data.confidence) }}>
              {data.health_score ?? '—'}
            </div>
          </div>
          <div>
            <div className="vigil-health-label" style={{ color: healthVar(data.health_score, data.confidence) }}>{healthLabel}</div>
            {data.decay_flags.length > 0 && (
              <ul className="vigil-flag-list">
                {data.decay_flags.map((f, i) => (
                  <li key={i}>Trade #{f.trade_index} · {f.date} · win rate shifted from baseline (CUSUM)</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      {/* Win rate comparison chart */}
      <section className="vigil-panel" style={{ animationDelay: '160ms' }}>
        <div className="vigil-panel-label">Win Rate by Instrument — {selectedStrategy.replace(/_/g, ' ')}</div>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={winRateChartData} margin={{ bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1c1f28" />
            <XAxis dataKey="ticker" stroke="#565a6b" fontSize={10} angle={-45} textAnchor="end" interval={0} tickLine={false} />
            <YAxis stroke="#565a6b" fontSize={11} unit="%" tickLine={false} />
            <Tooltip
              contentStyle={{ background: '#12141a', border: '1px solid #2a2e3a', borderRadius: 8, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
              formatter={(v) => `${v.toFixed(1)}%`}
            />
            <Bar dataKey="winRate" radius={[3, 3, 0, 0]} animationDuration={700}>
              {winRateChartData.map((entry, i) => (
                <Cell key={i} fill={entry.ticker === selectedStock ? '#5eead4' : '#262a36'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>

      {/* Comparison table */}
      <section className="vigil-panel" style={{ animationDelay: '200ms' }}>
        <div className="vigil-panel-label">All Instruments — {selectedStrategy.replace(/_/g, ' ')}</div>
        <table className="vigil-table">
          <thead>
            <tr>
              <th>Instrument</th>
              <th>Trades</th>
              <th>Win Rate</th>
              <th>Return</th>
              <th>Sharpe</th>
              <th>Health</th>
            </tr>
          </thead>
          <tbody>
            {tickers.map(t => {
              const row = portfolio[t][selectedStrategy];
              const isSelected = t === selectedStock;
              return (
                <tr
                  key={t}
                  onClick={() => setSelectedStock(t)}
                  className={`vigil-row-clickable ${isSelected ? 'vigil-row-selected' : ''}`}
                >
                  <td style={{ fontWeight: 600 }}>{t}</td>
                  <td>{row.total_trades}</td>
                  <td>{row.win_rate.toFixed(1)}%</td>
                  <td style={{ color: row.total_return_pct > 0 ? 'var(--signal)' : 'var(--red)' }}>
                    {row.total_return_pct > 0 ? '+' : ''}{row.total_return_pct.toFixed(2)}%
                  </td>
                  <td>{row.sharpe_ratio.toFixed(2)}</td>
                  <td style={{ color: healthVar(row.health_score, row.confidence) }}>
                    {row.health_score ?? 'N/A'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function StatCard({ label, value, color, delay }) {
  return (
    <div className="vigil-stat-card" style={{ animationDelay: `${delay}ms` }}>
      <div className="vigil-stat-label">{label}</div>
      <div className="vigil-stat-value" style={{ color: color ?? 'var(--text)' }}>{value}</div>
    </div>
  );
}

export default App;
