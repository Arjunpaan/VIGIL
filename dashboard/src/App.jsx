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
    return <div style={styles.loading}>Loading VIGIL portfolio...</div>;
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

  const healthColor = (score, confidence) => {
    if (confidence === 'insufficient_data' || confidence === 'no_data') return '#5a5a72';
    if (score >= 80) return '#4ade80';
    if (score >= 50) return '#facc15';
    return '#f87171';
  };

  const healthLabel = data.confidence === 'no_data' ? 'No trades occurred'
    : data.confidence === 'insufficient_data' ? `Insufficient data (only ${data.total_trades} trades — need 15+)`
    : data.health_score >= 80 ? 'Healthy'
    : data.health_score >= 50 ? 'Caution — decay detected'
    : 'Warning — significant decay';

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>VIGIL</h1>
          <p style={styles.subtitle}>Strategy decay monitoring · {tickers.length} stocks · 2 strategies</p>
        </div>
      </header>

      {/* Portfolio overview */}
      <section style={styles.overviewCard}>
        <div style={styles.overviewLabel}>PORTFOLIO OVERVIEW — {selectedStrategy.replace(/_/g, ' ').toUpperCase()}</div>
        <div style={styles.overviewRow}>
          <OverviewStat label="Total Trades" value={totalPortfolioTrades} />
          <OverviewStat label="Avg Win Rate" value={`${avgWinRate.toFixed(1)}%`} />
          <OverviewStat
            label="Stocks Showing Decay"
            value={`${stocksWithDecay} / ${tickers.length}`}
            color={stocksWithDecay > tickers.length / 3 ? '#f87171' : '#facc15'}
          />
        </div>
      </section>

      {/* Selectors */}
      <div style={styles.selectorRow}>
        <Selector label="Strategy" value={selectedStrategy} onChange={setSelectedStrategy}>
          <option value="momentum_crossover_5_20">Momentum Crossover (5/20)</option>
          <option value="mean_reversion_6mo">Mean Reversion (6mo)</option>
        </Selector>
        <Selector label="Stock" value={selectedStock} onChange={setSelectedStock}>
          {tickers.map(t => <option key={t} value={t}>{t}</option>)}
        </Selector>
      </div>

      {/* Stat cards */}
      <div style={styles.statRow}>
        <StatCard label="Total Trades" value={data.total_trades} />
        <StatCard label="Win Rate" value={`${data.win_rate.toFixed(1)}%`} />
        <StatCard label="Total Return" value={`${data.total_return_pct.toFixed(2)}%`} positive={data.total_return_pct > 0} />
        <StatCard label="Max Drawdown" value={`${data.max_drawdown_pct.toFixed(2)}%`} negative />
        <StatCard label="Sharpe Ratio" value={data.sharpe_ratio.toFixed(2)} positive={data.sharpe_ratio > 0} />
        <StatCard label="Health Score" value={data.health_score ?? 'N/A'} customColor={healthColor(data.health_score, data.confidence)} />
      </div>

      {/* Equity curve */}
      <section style={styles.panel}>
        <h3 style={styles.panelTitle}>{selectedStock} — Equity Curve</h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={equityChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#23233a" />
            <XAxis dataKey="day" stroke="#5a5a72" fontSize={12} />
            <YAxis stroke="#5a5a72" fontSize={12} domain={['auto', 'auto']} />
            <Tooltip contentStyle={styles.tooltip} labelStyle={{ color: '#888' }} />
            <Line type="monotone" dataKey="equity" stroke="#a78bfa" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </section>

      {/* Health score detail */}
      <section style={styles.panel}>
        <h3 style={styles.panelTitle}>Decay Health Score</h3>
        <div style={styles.healthRow}>
          <div style={{ ...styles.healthNumber, color: healthColor(data.health_score, data.confidence) }}>
            {data.health_score ?? '—'}
          </div>
          <div>
            <div style={{ color: healthColor(data.health_score, data.confidence), fontWeight: 600 }}>{healthLabel}</div>
            {data.decay_flags.length > 0 && (
              <ul style={styles.flagList}>
                {data.decay_flags.map((f, i) => (
                  <li key={i}>Trade #{f.trade_index} ({f.date}) — win rate shifted from baseline</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      {/* Win rate comparison chart */}
      <section style={styles.panel}>
        <h3 style={styles.panelTitle}>Win Rate by Stock — {selectedStrategy.replace(/_/g, ' ')}</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={winRateChartData} margin={{ bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#23233a" />
            <XAxis dataKey="ticker" stroke="#5a5a72" fontSize={11} angle={-45} textAnchor="end" interval={0} />
            <YAxis stroke="#5a5a72" fontSize={12} unit="%" />
            <Tooltip contentStyle={styles.tooltip} formatter={(v) => `${v.toFixed(1)}%`} />
            <Bar dataKey="winRate" radius={[4, 4, 0, 0]}>
              {winRateChartData.map((entry, i) => (
                <Cell key={i} fill={entry.ticker === selectedStock ? '#a78bfa' : '#3a3a5a'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>

      {/* Comparison table */}
      <section style={styles.panel}>
        <h3 style={styles.panelTitle}>All Stocks — {selectedStrategy.replace(/_/g, ' ')}</h3>
        <table style={styles.table}>
          <thead>
            <tr style={styles.tableHeadRow}>
              <th style={styles.th}>Stock</th>
              <th style={styles.th}>Trades</th>
              <th style={styles.th}>Win Rate</th>
              <th style={styles.th}>Return</th>
              <th style={styles.th}>Sharpe</th>
              <th style={styles.th}>Health</th>
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
                  style={{ ...styles.tr, backgroundColor: isSelected ? '#2a2a4a' : 'transparent' }}
                >
                  <td style={{ ...styles.td, fontWeight: 600 }}>{t}</td>
                  <td style={styles.td}>{row.total_trades}</td>
                  <td style={styles.td}>{row.win_rate.toFixed(1)}%</td>
                  <td style={{ ...styles.td, color: row.total_return_pct > 0 ? '#4ade80' : '#f87171' }}>
                    {row.total_return_pct > 0 ? '+' : ''}{row.total_return_pct.toFixed(2)}%
                  </td>
                  <td style={styles.td}>{row.sharpe_ratio.toFixed(2)}</td>
                  <td style={{ ...styles.td, color: healthColor(row.health_score, row.confidence) }}>
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

function OverviewStat({ label, value, color }) {
  return (
    <div>
      <div style={styles.overviewStatLabel}>{label}</div>
      <div style={{ ...styles.overviewStatValue, color: color ?? 'white' }}>{value}</div>
    </div>
  );
}

function Selector({ label, value, onChange, children }) {
  return (
    <div>
      <label style={styles.selectorLabel}>{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)} style={styles.select}>
        {children}
      </select>
    </div>
  );
}

function StatCard({ label, value, positive, negative, customColor }) {
  let color = 'white';
  if (customColor) color = customColor;
  else if (positive === true) color = '#4ade80';
  else if (positive === false) color = '#f87171';
  else if (negative) color = '#f87171';

  return (
    <div style={styles.statCard}>
      <div style={styles.statLabel}>{label}</div>
      <div style={{ ...styles.statValue, color }}>{value}</div>
    </div>
  );
}

const styles = {
  page: { padding: '40px 48px', backgroundColor: '#0a0a14', minHeight: '100vh', width: '100%', color: '#e5e5f0', fontFamily: "'Inter', -apple-system, sans-serif", boxSizing: 'border-box' },
  loading: { padding: 40, color: 'white', backgroundColor: '#0a0a14', minHeight: '100vh', fontFamily: 'sans-serif' },
  header: { marginBottom: 28, borderBottom: '1px solid #1e1e30', paddingBottom: 20 },
  title: { margin: 0, fontSize: 32, fontWeight: 700, letterSpacing: '0.5px' },
  subtitle: { margin: '4px 0 0', color: '#6a6a85', fontSize: 14 },
  overviewCard: { backgroundColor: '#14142a', border: '1px solid #26264a', borderRadius: 14, padding: 24, marginBottom: 28 },
  overviewLabel: { color: '#6a6a85', fontSize: 12, letterSpacing: '1px', marginBottom: 14, fontWeight: 600 },
  overviewRow: { display: 'flex', gap: 48 },
  overviewStatLabel: { color: '#6a6a85', fontSize: 13, marginBottom: 4 },
  overviewStatValue: { fontSize: 26, fontWeight: 700 },
  selectorRow: { display: 'flex', gap: 20, marginBottom: 28 },
  selectorLabel: { display: 'block', color: '#6a6a85', fontSize: 12, marginBottom: 6, fontWeight: 600 },
  select: { backgroundColor: '#14142a', color: 'white', padding: '10px 14px', borderRadius: 10, border: '1px solid #26264a', fontSize: 14, minWidth: 200, cursor: 'pointer' },
  statRow: { display: 'flex', gap: 16, marginBottom: 32, flexWrap: 'wrap' },
  statCard: { backgroundColor: '#14142a', border: '1px solid #22223a', padding: '18px 22px', borderRadius: 12, flex: '1 1 160px', minWidth: 150 },
  statLabel: { color: '#6a6a85', fontSize: 12, marginBottom: 8, fontWeight: 600, letterSpacing: '0.5px' },
  statValue: { fontSize: 26, fontWeight: 700 },
  panel: { backgroundColor: '#14142a', border: '1px solid #22223a', padding: 24, borderRadius: 14, marginBottom: 28 },
  panelTitle: { marginTop: 0, marginBottom: 20, fontSize: 16, fontWeight: 600, color: '#d5d5e5' },
  tooltip: { backgroundColor: '#1a1a30', border: '1px solid #333355', borderRadius: 8 },
  healthRow: { display: 'flex', gap: 24, alignItems: 'flex-start' },
  healthNumber: { fontSize: 44, fontWeight: 800, lineHeight: 1 },
  flagList: { color: '#8a8aa5', fontSize: 13, marginTop: 8, paddingLeft: 18 },
  table: { width: '100%', borderCollapse: 'collapse' },
  tableHeadRow: { borderBottom: '1px solid #2a2a4a', textAlign: 'left' },
  th: { padding: '10px 8px', color: '#6a6a85', fontSize: 12, fontWeight: 600, letterSpacing: '0.5px' },
  tr: { borderBottom: '1px solid #1e1e30', cursor: 'pointer', transition: 'background-color 0.15s' },
  td: { padding: '10px 8px', fontSize: 14 },
};

export default App;