import type { PortfolioAnalysis } from '../api';

interface AnalysisProps {
  portfolioAnalysis: PortfolioAnalysis;
}

export default function Analysis({ portfolioAnalysis }: AnalysisProps) {
  return (
    <div>
      <div className="card">
        <h2>Portfolio Analysis</h2>
        <h3>Total Value: ${portfolioAnalysis.total_value.toFixed(2)}</h3>
        
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Current Price</th>
              <th>Current Value</th>
              <th>Gain/Loss</th>
            </tr>
          </thead>
          <tbody>
            {portfolioAnalysis.holdings.map((holding) => (
              <tr key={holding.ticker}>
                <td>{holding.ticker}</td>
                <td>${holding.current_price.toFixed(2)}</td>
                <td>${holding.current_value.toFixed(2)}</td>
                <td className={holding.gain_loss >= 0 ? 'positive' : 'negative'}>
                  {holding.gain_loss >= 0 ? '+' : ''}
                  {holding.gain_loss_pct.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>AI Recommendations</h2>
        <div className="ai-analysis">
          {portfolioAnalysis.ai_analysis}
        </div>
      </div>
    </div>
  );
}