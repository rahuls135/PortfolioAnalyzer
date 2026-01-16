import { useState, useEffect } from 'react';
import { api } from '../api';
import Analysis from './Analysis';
import AnalysisMetrics from './AnalysisMetrics';
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
  const [totalValue, setTotalValue] = useState<number>(0);
  const [totalGainLoss, setTotalGainLoss] = useState<number>(0);
  const [totalInvested, setTotalInvested] = useState<number>(0);
  const [portfolioAnalysis, setPortfolioAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisStale, setAnalysisStale] = useState(false);
  const [cachedAnalysisText, setCachedAnalysisText] = useState<string | null>(null);
  const [cachedAnalysisMeta, setCachedAnalysisMeta] = useState<{
    last_analysis_at: string | null;
  } | null>(null);
  const [cachedMetrics, setCachedMetrics] = useState<PortfolioAnalysis['metrics'] | null>(null);
  const [liveMetrics, setLiveMetrics] = useState<PortfolioAnalysis['metrics'] | null>(null);
  const [cachedTranscripts, setCachedTranscripts] = useState<Record<string, string>>({});
  const [cachedTranscriptsQuarter, setCachedTranscriptsQuarter] = useState<string | null>(null);
  const [transcriptSummaries, setTranscriptSummaries] = useState<Record<string, string>>({});
  const [transcriptsLoading, setTranscriptsLoading] = useState(false);
  const [transcriptsError, setTranscriptsError] = useState<string | null>(null);
  const [cooldownRemainingSeconds, setCooldownRemainingSeconds] = useState(0);
  const [nextAvailableAt, setNextAvailableAt] = useState<string | null>(null);
  const [lastAnalysisAt, setLastAnalysisAt] = useState<string | null>(null);
  const [pricesCached, setPricesCached] = useState(false);
  const [newHoldingRows, setNewHoldingRows] = useState<Array<{ id: number; ticker: string; shares: string; avg_price: string }>>([]);
  
  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editShares, setEditShares] = useState('');
  const [editAvgPrice, setEditAvgPrice] = useState('');

  useEffect(() => {
    const init = async () => {
      await loadHoldings();
      await loadCachedAnalysis();
    };
    init();
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

  const loadMetrics = async () => {
    try {
      const response = await api.getPortfolioMetrics();
      setLiveMetrics(response.data.metrics);
    } catch (error) {
      console.error('Error loading metrics:', error);
    }
  };

  const loadHoldings = async () => {
    try {
      const response = await api.getHoldings();
      const baseHoldings = response.data;
      
      // Set holdings first (without prices)
      setHoldings(baseHoldings.map(h => ({ ...h, price_loading: true })));
      
      // Fetch prices for all holdings
      await loadPrices(baseHoldings);
      await loadMetrics();
      setAnalysisError(null);
      return baseHoldings;

    } catch (error) {
      console.error('Error loading holdings:', error);
      return [];
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
      const allCached = priceResults.length > 0 && priceResults.every(result => result.cached);
      setPricesCached(allCached);

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
      const invested = holdingsWithPrices.reduce((sum, h) => sum + (h.shares * h.avg_price), 0);
      
      setTotalValue(total);
      setTotalGainLoss(totalGL);
      setTotalInvested(invested);
      
    } catch (error) {
      console.error('Error in loadPrices master flow:', error);
    }
  };

  const loadCachedAnalysis = async () => {
    try {
      const response = await api.getCachedAnalysis();
      setCachedAnalysisText(response.data.ai_analysis);
      setCachedAnalysisMeta({ last_analysis_at: response.data.analysis_meta.last_analysis_at });
      setCooldownRemainingSeconds(response.data.analysis_meta.cooldown_remaining_seconds);
      setNextAvailableAt(response.data.analysis_meta.next_available_at);
      setLastAnalysisAt(response.data.analysis_meta.last_analysis_at);
      setCachedMetrics(response.data.metrics ?? null);
      setCachedTranscripts(response.data.transcripts ?? {});
      setCachedTranscriptsQuarter(response.data.transcripts_quarter ?? null);
    } catch (error) {
      setCachedAnalysisText(null);
      setCachedAnalysisMeta(null);
      setCooldownRemainingSeconds(0);
      setNextAvailableAt(null);
      setLastAnalysisAt(null);
      setCachedMetrics(null);
      setCachedTranscripts({});
      setCachedTranscriptsQuarter(null);
    }
  };

  const loadAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysisError(null);
    setTranscriptsError(null);

    try {
      const response = await api.analyzePortfolio();
      setPortfolioAnalysis(response.data);
      setCachedAnalysisText(response.data.ai_analysis);
      setCachedAnalysisMeta({ last_analysis_at: response.data.analysis_meta.last_analysis_at });
      setCachedMetrics(response.data.metrics);
      setAnalysisStale(false);
      setCooldownRemainingSeconds(response.data.analysis_meta.cooldown_remaining_seconds);
      setNextAvailableAt(response.data.analysis_meta.next_available_at);
      setLastAnalysisAt(response.data.analysis_meta.last_analysis_at);

      if (response.data.holdings.length > 0) {
        const now = new Date();
        const quarter = `${now.getFullYear()}Q${Math.floor(now.getMonth() / 3) + 1}`;
        setTranscriptsLoading(true);
        const excludedAssetTypes = new Set(['ETF', 'MUTUAL FUND', 'FUND']);
        const filteredHoldings = response.data.holdings.filter((holding) => {
          const assetType = holding.asset_type?.toUpperCase();
          return !assetType || !excludedAssetTypes.has(assetType);
        });
        const sortedHoldings = [...filteredHoldings].sort((a, b) => b.current_value - a.current_value);
        const totalValue = sortedHoldings.reduce((sum, holding) => sum + holding.current_value, 0);
        let running = 0;
        const topHoldings = sortedHoldings.filter((holding) => {
          if (totalValue <= 0) {
            return false;
          }
          if (running / totalValue >= 0.7) {
            return false;
          }
          running += holding.current_value;
          return true;
        });
        const results = await Promise.allSettled(
          topHoldings.map((holding) =>
            api.getEarningsTranscript(holding.ticker, quarter, 2)
          )
        );
        const summaries: Record<string, string> = {};
        results.forEach((result) => {
          if (result.status === 'fulfilled') {
            summaries[result.value.data.ticker] = result.value.data.summary;
          }
        });
        setTranscriptSummaries(summaries);
        setCachedTranscripts(summaries);
        setCachedTranscriptsQuarter(quarter);
        if (Object.keys(summaries).length > 0) {
          api.cacheTranscriptSummaries(quarter, summaries).catch(() => null);
        }
        if (results.some((result) => result.status === 'rejected')) {
          setTranscriptsError('Some transcripts could not be loaded.');
        }
        setTranscriptsLoading(false);
      }
    } catch (error) {
      setAnalysisError((error as Error).message || 'Failed to analyze portfolio.');
    } finally {
      setAnalysisLoading(false);
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

  const handleRefreshHoldings = async () => {
    await loadHoldings();
    if (portfolioAnalysis) {
      setAnalysisStale(true);
    }
  };

  const isValidNumberInput = (value: string) => {
    if (!value.trim()) {
      return false;
    }
    return !Number.isNaN(Number(value));
  };

  const handleAddHoldingRow = () => {
    setNewHoldingRows((prev) => [
      ...prev,
      { id: Date.now(), ticker: '', shares: '', avg_price: '' }
    ]);
  };

  const updateNewHoldingRow = (rowId: number, updates: Partial<{ ticker: string; shares: string; avg_price: string }>) => {
    setNewHoldingRows((prev) => prev.map((row) => (
      row.id === rowId ? { ...row, ...updates } : row
    )));
  };

  const removeNewHoldingRow = (rowId: number) => {
    setNewHoldingRows((prev) => prev.filter((row) => row.id !== rowId));
  };

  const handleCreateHolding = async (row: { id: number; ticker: string; shares: string; avg_price: string }) => {
    const ticker = row.ticker.trim().toUpperCase();
    const shares = parseFloat(row.shares);
    const avgPrice = parseFloat(row.avg_price);
    if (!ticker || Number.isNaN(shares) || Number.isNaN(avgPrice)) {
      alert('Enter a ticker, shares, and avg price.');
      return;
    }

    try {
      await api.addHolding({ ticker, shares, avg_price: avgPrice });
      await loadHoldings();
      setAnalysisStale(true);
      removeNewHoldingRow(row.id);
    } catch (error) {
      alert('Error adding holding: ' + (error as Error).message);
    }
  };

  const handleRunAnalysis = async () => {
    await loadAnalysis();
  };

  const metricsToShow = liveMetrics || cachedMetrics || portfolioAnalysis?.metrics || null;

  const isNewHoldingRowValid = (row: { ticker: string; shares: string; avg_price: string }) => (
    row.ticker.trim() !== ''
    && isValidNumberInput(row.shares)
    && isValidNumberInput(row.avg_price)
  );

  const isEditRowValid = editingId === null
    || (isValidNumberInput(editShares) && isValidNumberInput(editAvgPrice));

  const hasPendingRows = editingId !== null || newHoldingRows.length > 0;
  const pendingRowsValid = isEditRowValid && newHoldingRows.every(isNewHoldingRowValid);
  const showAddRowIcon = holdings.length > 0 && (!hasPendingRows || pendingRowsValid);

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
      {totalInvested > 0 && (
        <div className="card portfolio-summary">
          <div className="summary-row">
            <div className="summary-item">
              <span className="summary-label">Total Invested</span>
              <span className="summary-value">${totalInvested.toFixed(2)}</span>
            </div>
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
          </div>
        </div>
      )}

      {metricsToShow && (
        <AnalysisMetrics metrics={metricsToShow} />
      )}

      <div className="card">
        <div className="card-header">
          <h2>Your Holdings</h2>
          <button
            onClick={handleRefreshHoldings}
            className="btn-refresh"
            disabled={pricesCached}
            title={pricesCached ? 'Prices are already cached.' : 'Sync holdings and refresh prices.'}
          >
            Sync Holdings
          </button>
        </div>
        {holdings.length === 0 && newHoldingRows.length === 0 ? (
          <p>No holdings yet. Add your first stock!</p>
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
                          className="btn-save action-btn"
                          aria-label="Save changes"
                          title="Save changes"
                        >
                          <svg viewBox="0 0 20 20" aria-hidden="true">
                            <path
                              d="M5 10.5l3 3 7-7"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.8"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </button>
                        <button 
                          onClick={handleCancelEdit}
                          className="btn-cancel action-btn"
                          aria-label="Cancel edit"
                          title="Cancel edit"
                        >
                          <svg viewBox="0 0 20 20" aria-hidden="true">
                            <path
                              d="M5 5l10 10M15 5L5 15"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.8"
                              strokeLinecap="round"
                            />
                          </svg>
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
                          className="btn-edit action-btn"
                          aria-label="Edit holding"
                          title="Edit holding"
                        >
                          <svg viewBox="0 0 20 20" aria-hidden="true">
                            <path
                              d="M13.5 4.5l2 2-8.5 8.5-3 1 1-3 8.5-8.5z"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.6"
                              strokeLinejoin="round"
                            />
                            <path
                              d="M12 6l2 2"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.6"
                              strokeLinecap="round"
                            />
                          </svg>
                        </button>
                        <button 
                          onClick={() => handleDelete(holding.id, holding.ticker)}
                          className="btn-delete action-btn"
                          aria-label="Delete holding"
                          title="Delete holding"
                        >
                          <svg viewBox="0 0 20 20" aria-hidden="true">
                            <path
                              d="M6 6h8M8 6V5h4v1M7 6l.8 9h4.4L13 6"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.6"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
              {newHoldingRows.map((row) => (
                <tr key={`new-${row.id}`}>
                  <td>
                    <input
                      type="text"
                      value={row.ticker}
                      onChange={(e) => updateNewHoldingRow(row.id, { ticker: e.target.value })}
                      className="edit-input"
                      placeholder="AAPL"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={row.shares}
                      onChange={(e) => updateNewHoldingRow(row.id, { shares: e.target.value })}
                      className="edit-input"
                      placeholder="10"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={row.avg_price}
                      onChange={(e) => updateNewHoldingRow(row.id, { avg_price: e.target.value })}
                      className="edit-input"
                      placeholder="150.25"
                    />
                  </td>
                  <td colSpan={3}>-</td>
                  <td>
                    <button
                      onClick={() => handleCreateHolding(row)}
                      className="btn-save action-btn"
                      aria-label="Add holding"
                      title="Add holding"
                    >
                      <svg viewBox="0 0 20 20" aria-hidden="true">
                        <path
                          d="M5 10.5l3 3 7-7"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                    <button
                      onClick={() => removeNewHoldingRow(row.id)}
                      className="btn-cancel action-btn"
                      aria-label="Cancel add"
                      title="Cancel add"
                    >
                      <svg viewBox="0 0 20 20" aria-hidden="true">
                        <path
                          d="M5 5l10 10M15 5L5 15"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
              {showAddRowIcon && holdings.length > 0 && (
                <tr className="add-row">
                  <td>
                    <button
                      type="button"
                      className="btn-add-row"
                      onClick={handleAddHoldingRow}
                    >
                      <svg viewBox="0 0 20 20" aria-hidden="true">
                        <path
                          d="M10 4v12M4 10h12"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                      </svg>
                      <span>Add Holding</span>
                    </button>
                  </td>
                  <td colSpan={6} />
                </tr>
              )}
            </tbody>
          </table>
        )}
        {holdings.length === 0 && (
          <div className="form-row">
            <button
              type="button"
              className="btn-secondary"
              onClick={handleAddHoldingRow}
            >
              Add Row
            </button>
          </div>
        )}

        <div className="analysis-actions">
          <button
            onClick={handleRunAnalysis}
            className="btn-primary btn-with-icon"
            disabled={holdings.length === 0 || analysisLoading || cooldownRemainingSeconds > 0}
          >
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path
                d="M4 16l7-7"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
              <path
                d="M11 9l2 2"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
              <path
                d="M14.5 3.5l.6 1.7 1.7.6-1.7.6-.6 1.7-.6-1.7-1.7-.6 1.7-.6z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
            </svg>
            {analysisLoading ? 'Analyzing...' : 'Run Analysis'}
          </button>
          {analysisError && <span className="error">{analysisError}</span>}
          {analysisStale && portfolioAnalysis && (
            <span className="warning">Holdings have been edited since the last analysis.</span>
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
        <>
          <Analysis portfolioAnalysis={portfolioAnalysis} />
          <div className="card">
            <h2>Earnings Call Key Points</h2>
            {transcriptsLoading && <span className="muted">Loading transcripts...</span>}
            {transcriptsError && <div className="error">{transcriptsError}</div>}
            {!transcriptsLoading && Object.keys(transcriptSummaries).length === 0 && (
              <span className="muted">No transcript summaries available yet.</span>
            )}
            {Object.entries(transcriptSummaries).map(([ticker, summary]) => (
              <div key={ticker} className="transcript-summary">
                <strong>{ticker}</strong>
                <p>{summary}</p>
              </div>
            ))}
          </div>
        </>
      )}
      {!portfolioAnalysis && cachedAnalysisText && (
        <>
          <div className="card">
            <h2>AI Insights</h2>
            {cachedAnalysisMeta?.last_analysis_at && (
              <span className="muted">
                Last analysis: {new Date(cachedAnalysisMeta.last_analysis_at).toLocaleString()}
              </span>
            )}
            <div className="ai-analysis">
              {cachedAnalysisText}
            </div>
          </div>
          <div className="card">
            <h2>Earnings Call Key Points</h2>
            {cachedTranscriptsQuarter && (
              <span className="muted">Quarter: {cachedTranscriptsQuarter}</span>
            )}
            {Object.keys(cachedTranscripts).length === 0 && (
              <span className="muted">No transcript summaries available yet.</span>
            )}
            {Object.entries(cachedTranscripts).map(([ticker, summary]) => (
              <div key={ticker} className="transcript-summary">
                <strong>{ticker}</strong>
                <p>{summary}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
