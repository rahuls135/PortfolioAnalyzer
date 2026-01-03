import type { PortfolioAnalysis } from '../api';

interface AnalysisMetricsProps {
  metrics: PortfolioAnalysis['metrics'];
}

export default function AnalysisMetrics({ metrics }: AnalysisMetricsProps) {
  const totalSectorPct = metrics.sector_allocation.reduce((sum, item) => sum + item.pct, 0);
  let current = 0;
  const pieStops = metrics.sector_allocation.map((item, index) => {
    const start = current;
    const size = totalSectorPct > 0 ? (item.pct / totalSectorPct) * 100 : 0;
    current += size;
    const hue = (index * 55) % 360;
    return {
      label: item.sector,
      pct: item.pct,
      color: `hsl(${hue} 75% 55%)`,
      start,
      end: current
    };
  });
  const pieStyle = pieStops.length
    ? {
        background: `conic-gradient(${pieStops
          .map((stop) => `${stop.color} ${stop.start}% ${stop.end}%`)
          .join(', ')})`
      }
    : undefined;

  return (
    <div className="card">
      <h2>Portfolio Metrics</h2>
      <div className="metrics-grid">
        <div className="metrics-block">
          <h3>Sector Allocation</h3>
          {pieStops.length === 0 ? (
            <span className="muted">No sector data yet.</span>
          ) : (
            <div className="pie-layout">
              <div className="pie-chart" style={pieStyle} />
              <div className="pie-legend">
                {pieStops.map((stop) => (
                  <div className="pie-legend-row" key={stop.label}>
                    <span className="pie-swatch" style={{ background: stop.color }} />
                    <span className="pie-label">{stop.label}</span>
                    <span className="pie-value">{stop.pct.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="metrics-block">
          <h3>Top Holdings</h3>
          {metrics.top_holdings.length === 0 ? (
            <span className="muted">No holdings yet.</span>
          ) : (
            metrics.top_holdings.map((holding) => (
              <div className="metrics-row" key={holding.ticker}>
                <div className="metrics-label">{holding.ticker}</div>
                <div className="metrics-bar">
                  <span style={{ width: `${holding.pct.toFixed(1)}%` }} />
                </div>
                <div className="metrics-value">{holding.pct.toFixed(1)}%</div>
              </div>
            ))
          )}
        </div>
      </div>
      <div className="metrics-summary">
        <div>
          <span className="summary-label">Top 3 Concentration</span>
          <span className="summary-value">{metrics.concentration_top3_pct.toFixed(1)}%</span>
        </div>
        <div>
          <span className="summary-label">Diversification Score</span>
          <span className="summary-value">{metrics.diversification_score.toFixed(0)}/100</span>
        </div>
      </div>
    </div>
  );
}
