import { useState, useEffect } from 'react';
import { api } from '../api';
import Analysis from './Analysis';
import type { PortfolioHolding, Holding, PortfolioAnalysis } from '../api';

interface HoldingWithPrice extends Holding {
  sector?: string; // Add this!
  current_price?: number;
  current_value?: number;
  gain_loss?: number;
  gain_loss_pct?: number;
  price_loading?: boolean;
}

export default function Portfolio() {
  const [holdings, setHoldings] = useState<HoldingWithPrice[]>([]);
  const [ticker, setTicker] = useState('');
  const [shares, setShares] = useState('');
  const [avgPrice, setAvgPrice] = useState('');
  const [totalValue, setTotalValue] = useState<number>(0);
  const [totalGainLoss, setTotalGainLoss] = useState<number>(0);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [portfolioAnalysis, setPortfolioAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisStale, setAnalysisStale] = useState(false);
  const [cooldownRemainingSeconds, setCooldownRemainingSeconds] = useState(0);
  const [nextAvailableAt, setNextAvailableAt] = useState<string | null>(null);
  const [lastAnalysisAt, setLastAnalysisAt] = useState<string | null>(null);
  
  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editShares, setEditShares] = useState('');
  const [editAvgPrice, setEditAvgPrice] = useState('');

  useEffect(() => {
    loadHoldings();
  }, []);

  useEffect(() => {
    if (!nextAvailableAt) {
      return;
    }

    const updateRemaining = () => {
      const next = new Date(nextAvailableAt).getTime();
      const remaining = Math.max(0, Math.floor((next - Date.now()) / 1000));
      setCooldownRemainingSeconds(remaining);
    };

    updateRemaining();
    const timer = setInterval(updateRemaining, 60000);
    return () => clearInterval(timer);
  }, [nextAvailableAt]);

  const loadHoldings = async () => {
    try {
      const response = await api.getHoldings();
      const baseHoldings = response.data;
      
      // Set holdings first (without prices)
      setHoldings(baseHoldings.map(h => ({ ...h, price_loading: true })));
      
      // Fetch prices for all holdings
      await loadPrices(baseHoldings);
      setAnalysisError(null);

    } catch (error) {
      console.error('Error loading holdings:', error);
    }
  };

  const loadPrices = async (baseHoldings: Holding[]) => {
    try {
      // 1. Fetch prices and metadata from your Alpha Vantage backed API
      const pricePromises = baseHoldings.map(holding => 
        api.getStockPrice(holding.ticker)
          .then(res => ({ 
            ticker: holding.ticker, 
            price: res.data.current_price, 
            sector: res.data.sector, // Captured to satisfy the PortfolioHolding interface
            cached: res.data.cached 
          }))
          .catch(err => {
            console.error(`Failed to fetch price for ${holding.ticker}:`, err);
            return { ticker: holding.ticker, price: null, sector: 'Unknown', cached: false };
          })
      );

      const priceResults = await Promise.all(pricePromises);

      // 2. Transform base holdings into PortfolioHoldings with calculated fields
      const holdingsWithPrices: PortfolioHolding[] = baseHoldings.map(holding => {
        const priceData = priceResults.find(p => p.ticker === holding.ticker);
        const stockSector = priceData?.sector || 'Unknown';

        if (priceData?.price) {
          const currentPrice = priceData.price;
          const currentValue = holding.shares * currentPrice;
          const costBasis = holding.shares * holding.avg_price;
          const gainLoss = currentValue - costBasis;
          const gainLossPct = costBasis > 0 ? (gainLoss / costBasis) * 100 : 0;
          
          return {
            ...holding,
            sector: stockSector,
            current_price: currentPrice,
            current_value: currentValue,
            gain_loss: gainLoss,
            gain_loss_pct: gainLossPct,
            price_loading: false
          };
        }
        
        // Fallback object if the price fetch failed for this specific ticker
        return { 
          ...holding, 
          sector: stockSector,
          current_price: null,
          current_value: 0, 
          gain_loss: 0, 
          gain_loss_pct: 0, 
          price_loading: false 
        };
      });
      
      // 3. Update component state
      setHoldings(holdingsWithPrices);
      
      // 4. Calculate aggregate portfolio totals
      const total = holdingsWithPrices.reduce((sum, h) => sum + (h.current_value || 0), 0);
      const totalGL = holdingsWithPrices.reduce((sum, h) => sum + (h.gain_loss || 0), 0);
      
      setTotalValue(total);
      setTotalGainLoss(totalGL);
      setLastUpdated(new Date());
      
    } catch (error) {
      console.error('Error in loadPrices master flow:', error);
    }
  };

  const handleAddHolding = async (e: React.FormEvent) => {
    e.preventDefault();
    const newTicker = ticker.toUpperCase();
    const newShares = parseFloat(shares);
    const newPrice = parseFloat(avgPrice);

    if (isNaN(newShares) || isNaN(newPrice)) {
      alert('Please enter valid numbers for shares and price.');
      return;
    }

    try {
      await api.addHolding({
        ticker: newTicker,
        shares: newShares,
        avg_price: newPrice
      });

      await loadHoldings();
      setAnalysisStale(true);
      
      setTicker('');
      setShares('');
      setAvgPrice('');
      
      alert('Holding added!');
    } catch (error) {
      console.error("Failed to save:", error);
      alert('Error: ' + (error as Error).message);
    }
  };

  const handleEdit = (holding: Holding) => {
    setEditingId(holding.id);
    setEditShares(holding.shares.toString());
    setEditAvgPrice(holding.avg_price.toString());
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditShares('');
    setEditAvgPrice('');
  };

  const handleSaveEdit = async (holding: Holding) => {
    const newShares = parseFloat(editShares);
    const newPrice = parseFloat(editAvgPrice);

    if (isNaN(newShares) || isNaN(newPrice)) {
      alert('Please enter valid numbers.');
      return;
    }

    try {
      await api.updateHolding(holding.id, {
        ticker: holding.ticker,
        shares: newShares,
        avg_price: newPrice
      });

      await loadHoldings();
      setAnalysisStale(true);
      setEditingId(null);
      alert('Holding updated!');
    } catch (error) {
      alert('Error updating holding: ' + (error as Error).message);
    }
  };

  const handleDelete = async (holdingId: number, ticker: string) => {
    if (!confirm(`Are you sure you want to delete ${ticker}?`)) {
      return;
    }

    try {
      await api.deleteHolding(holdingId);
      await loadHoldings();
      setAnalysisStale(true);
      alert('Holding deleted!');
    } catch (error) {
      alert('Error deleting holding: ' + (error as Error).message);
    }
  };

  const handleRefreshPrices = async () => {
    const baseHoldings = holdings.map(({ current_price, current_value, gain_loss, gain_loss_pct, price_loading, ...rest }) => rest);
    setHoldings(holdings.map(h => ({ ...h, price_loading: true })));
    await loadPrices(baseHoldings);
  };

  const handleRunAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysisError(null);

    try {
      const response = await api.analyzePortfolio();
      setPortfolioAnalysis(response.data);
      setAnalysisStale(false);
      setCooldownRemainingSeconds(response.data.analysis_meta.cooldown_remaining_seconds);
      setNextAvailableAt(response.data.analysis_meta.next_available_at);
      setLastAnalysisAt(response.data.analysis_meta.last_analysis_at);
    } catch (error) {
      setAnalysisError((error as Error).message || 'Failed to analyze portfolio.');
    } finally {
      setAnalysisLoading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours <= 0) {
      return `${minutes}m`;
    }
    if (minutes <= 0) {
      return `${hours}h`;
    }
    return `${hours}h ${minutes}m`;
  };

  return (
    <div>
      {totalValue > 0 && (
        <div className="card portfolio-summary">
          <div className="summary-row">
            <div className="summary-item">
              <span className="summary-label">Total Value</span>
              <span className="summary-value">${totalValue.toFixed(2)}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Total Gain/Loss</span>
              <span className={`summary-value ${totalGainLoss >= 0 ? 'positive' : 'negative'}`}>
                {totalGainLoss >= 0 ? '+' : ''}${totalGainLoss.toFixed(2)}
              </span>
            </div>
            {lastUpdated && (
              <div className="summary-item">
                <span className="summary-label">Last Updated</span>
                <span className="summary-value-small">
                  {lastUpdated.toLocaleTimeString()}
                  <button onClick={handleRefreshPrices} className="btn-refresh">
                    🔄 Refresh
                  </button>
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <h2>Add Holding</h2>
        <form onSubmit={handleAddHolding}>
          <div className="form-row">
            <input
              type="text"
              placeholder="Ticker (e.g., AAPL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Shares"
              value={shares}
              onChange={(e) => setShares(e.target.value)}
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Average Price"
              value={avgPrice}
              onChange={(e) => setAvgPrice(e.target.value)}
              required
            />
            <button type="submit" className="btn-primary">Add</button>
          </div>
        </form>
      </div>

      <div className="card">
        <h2>Your Holdings</h2>
        {holdings.length === 0 ? (
          <p>No holdings yet. Add your first stock above!</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Shares</th>
                <th>Avg Price</th>
                <th>Current Price</th>
                <th>Current Value</th>
                <th>Gain/Loss</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.id}>
                  <td><strong>{holding.ticker}</strong></td>
                  
                  {editingId === holding.id ? (
                    <>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          value={editShares}
                          onChange={(e) => setEditShares(e.target.value)}
                          className="edit-input"
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          value={editAvgPrice}
                          onChange={(e) => setEditAvgPrice(e.target.value)}
                          className="edit-input"
                        />
                      </td>
                      <td colSpan={3}>-</td>
                      <td>
                        <button 
                          onClick={() => handleSaveEdit(holding)}
                          className="btn-save"
                        >
                          Save
                        </button>
                        <button 
                          onClick={handleCancelEdit}
                          className="btn-cancel"
                        >
                          Cancel
                        </button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{holding.shares}</td>
                      <td>${holding.avg_price.toFixed(2)}</td>
                      <td>
                        {holding.price_loading ? (
                          <span className="loading">Loading...</span>
                        ) : holding.current_price ? (
                          `$${holding.current_price.toFixed(2)}`
                        ) : (
                          <span className="error">N/A</span>
                        )}
                      </td>
                      <td>
                        {holding.current_value ? (
                          `$${holding.current_value.toFixed(2)}`
                        ) : '-'}
                      </td>
                      <td>
                        {holding.gain_loss !== undefined && holding.gain_loss_pct !== undefined ? (
                          <span className={holding.gain_loss >= 0 ? 'positive' : 'negative'}>
                            {holding.gain_loss >= 0 ? '+' : ''}${holding.gain_loss.toFixed(2)}
                            <br />
                            ({holding.gain_loss_pct >= 0 ? '+' : ''}{holding.gain_loss_pct.toFixed(2)}%)
                          </span>
                        ) : '-'}
                      </td>
                      <td>
                        <button 
                          onClick={() => handleEdit(holding)}
                          className="btn-edit"
                        >
                          Edit
                        </button>
                        <button 
                          onClick={() => handleDelete(holding.id, holding.ticker)}
                          className="btn-delete"
                        >
                          Delete
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="analysis-actions">
          <button
            onClick={handleRunAnalysis}
            className="btn-primary"
            disabled={holdings.length === 0 || analysisLoading || cooldownRemainingSeconds > 0}
          >
            {analysisLoading ? 'Analyzing...' : 'Run Analysis'}
          </button>
          {analysisError && <span className="error">{analysisError}</span>}
          {analysisStale && portfolioAnalysis && (
            <span className="warning">Holdings changed since the last analysis.</span>
          )}
          {lastAnalysisAt && (
            <span className="muted">
              Last analysis: {new Date(lastAnalysisAt).toLocaleString()}
            </span>
          )}
          {cooldownRemainingSeconds > 0 && (
            <span className="muted">
              Next analysis available in {formatDuration(cooldownRemainingSeconds)}
            </span>
          )}
        </div>
      </div>

      {portfolioAnalysis && (
        <Analysis portfolioAnalysis={portfolioAnalysis} />
      )}
    </div>
  );
}
