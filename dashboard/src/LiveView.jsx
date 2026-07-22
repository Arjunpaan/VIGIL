import { useState, useEffect } from 'react';

function LiveView() {
  const [liveData, setLiveData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const poll = () => {
      fetch('http://localhost:5000/api/live-status')
        .then(res => res.json())
        .then(json => {
          setLiveData(json);
          setError(false);
        })
        .catch(() => setError(true));
    };

    poll(); // fetch immediately on mount
    const interval = setInterval(poll, 2000); // then every 2 seconds
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="vigil-panel">
        <div className="vigil-panel-label">Live Feed</div>
        <div style={{ color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
          Cannot reach live server at localhost:5000 — run <code>python live_server.py</code> locally to see this in action.
        </div>
      </div>
    );
  }

  if (!liveData) {
    return <div className="vigil-panel">Connecting to live feed…</div>;
  }

  return (
    <div className="vigil-panel">
      <div className="vigil-panel-label">
        Live Feed — {liveData.ticker}
        <span className="vigil-status-dot" style={{ marginLeft: 10 }} />
      </div>
      <div style={{ display: 'flex', gap: 32, fontFamily: 'var(--font-mono)', fontSize: 13, marginBottom: 16 }}>
        <div>
          <div style={{ color: 'var(--text-faint)', fontSize: 10, textTransform: 'uppercase' }}>Status</div>
          <div style={{ color: liveData.status === 'running' ? 'var(--signal)' : 'var(--text-dim)' }}>{liveData.status}</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-faint)', fontSize: 10, textTransform: 'uppercase' }}>Bars Processed</div>
          <div>{liveData.bars_processed}</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-faint)', fontSize: 10, textTransform: 'uppercase' }}>Current Date</div>
          <div>{liveData.current_date}</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-faint)', fontSize: 10, textTransform: 'uppercase' }}>Current Price</div>
          <div>₹{liveData.current_price?.toFixed(2)}</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-faint)', fontSize: 10, textTransform: 'uppercase' }}>Health Score</div>
          <div style={{ color: liveData.health_score >= 80 ? 'var(--signal)' : liveData.health_score >= 50 ? 'var(--amber)' : liveData.confidence === 'insufficient_data' ? 'var(--text-faint)' : 'var(--red)' }}>
            {liveData.health_score ?? 'N/A'}
          </div>
        </div>
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-dim)' }}>
        {liveData.trades.length === 0 ? 'No trades yet.' : 'Recent trades:'}
        {liveData.trades.map((t, i) => (
          <div key={i} style={{ color: t.win ? 'var(--signal)' : 'var(--red)' }}>
            {t.date}: {t.pnl_pct > 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%
          </div>
        ))}
      </div>
    </div>
  );
}

export default LiveView;