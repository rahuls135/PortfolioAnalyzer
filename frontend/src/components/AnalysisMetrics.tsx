import type { PortfolioAnalysis } from '../api';

interface AnalysisMetricsProps {
  portfolioAnalysis: PortfolioAnalysis;
}

export default function AnalysisMetrics({ portfolioAnalysis }: AnalysisMetricsProps) {
  const { metrics } = portfolioAnalysis;

  return (
    <div className="card">
      <h2>Portfolio Metrics</h2>
      <div className="metrics-grid">
        <div className="metrics-block">
          <h3>Sector Allocation</h3>
          {metrics.sector_allocation.length === 0 ? (
            <span className="muted">No sector data yet.</span>
          ) : (
            metrics.sector_allocation.map((sector) => (
              <div className="metrics-row" key={sector.sector}>
                <div className="metrics-label">{sector.sector}</div>
                <div className="metrics-bar">
                  <span style={{ width: `${sector.pct.toFixed(1)}%` }} />
                </div>
                <div className="metrics-value">{sector.pct.toFixed(1)}%</div>
              </div>
            ))
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
