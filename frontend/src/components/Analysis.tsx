import type { PortfolioAnalysis } from '../api';

interface AnalysisProps {
  portfolioAnalysis: PortfolioAnalysis;
}

export default function Analysis({ portfolioAnalysis }: AnalysisProps) {
  return (
    <div className="card">
      <h2>AI Insights</h2>
      <div className="ai-analysis">
        {portfolioAnalysis.ai_analysis}
      </div>
    </div>
  );
}
