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
  const [transcriptSummaries, setTranscriptSummaries] = useState<Record<string, string>>({});
  const [transcriptsLoading, setTranscriptsLoading] = useState(false);
  const [transcriptsError, setTranscriptsError] = useState<string | null>(null);
  const [cooldownRemainingSeconds, setCooldownRemainingSeconds] = useState(0);
  const [nextAvailableAt, setNextAvailableAt] = useState<string | null>(null);
  const [lastAnalysisAt, setLastAnalysisAt] = useState<string | null>(null);
  const [pricesCached, setPricesCached] = useState(false);
  const [importMode, setImportMode] = useState<'merge' | 'replace'>('merge');
  const [importErrors, setImportErrors] = useState<string[]>([]);
  const [importLoading, setImportLoading] = useState(false);
  const [importRows, setImportRows] = useState<Array<{ id: number; ticker: string; shares: string; avg_price: string }>>([
    { id: 1, ticker: '', shares: '', avg_price: '' }
  ]);
  
  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editShares, setEditShares] = useState('');
  const [editAvgPrice, setEditAvgPrice] = useState('');

  useEffect(() => {
    const init = async () => {
      await loadHoldings();
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

  const loadHoldings = async () => {
    try {
      const response = await api.getHoldings();
      const baseHoldings = response.data;
      
      // Set holdings first (without prices)
      setHoldings(baseHoldings.map(h => ({ ...h, price_loading: true })));
      
      // Fetch prices for all holdings
      await loadPrices(baseHoldings);
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

  const loadAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysisError(null);
    setTranscriptsError(null);

    try {
      const response = await api.analyzePortfolio();
      setPortfolioAnalysis(response.data);
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
            api.getEarningsTranscript(holding.ticker, quarter)
          )
        );
        const summaries: Record<string, string> = {};
        results.forEach((result) => {
          if (result.status === 'fulfilled') {
            summaries[result.value.data.ticker] = result.value.data.summary;
          }
        });
        setTranscriptSummaries(summaries);
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

  const parseImportRows = () => {
    const preview: Holding[] = [];
    const errors: string[] = [];

    importRows.forEach((row, index) => {
      const tickerRaw = row.ticker.trim();
      if (!tickerRaw && !row.shares && !row.avg_price) {
        return;
      }
      const sharesValue = parseFloat(row.shares);
      const priceValue = parseFloat(row.avg_price);
      if (!tickerRaw || Number.isNaN(sharesValue) || Number.isNaN(priceValue)) {
        errors.push(`Row ${index + 1}: enter ticker, shares, and avg price.`);
        return;
      }
      preview.push({
        id: row.id,
        ticker: tickerRaw.toUpperCase(),
        shares: sharesValue,
        avg_price: priceValue
      });
    });

    setImportErrors(errors);
    return { preview, errors };
  };

  const handleImportHoldings = async () => {
    const { preview, errors } = parseImportRows();
    if (preview.length === 0 || errors.length > 0) {
      return;
    }

    setImportLoading(true);
    try {
      const uniqueTickers = Array.from(new Set(preview.map((item) => item.ticker)));
      for (const ticker of uniqueTickers) {
        const validation = await api.validateTicker(ticker);
        if (!validation.data.valid) {
          setImportErrors([`Invalid ticker: ${ticker}`]);
          setImportLoading(false);
          return;
        }
      }

      await api.bulkUpsertHoldings({
        mode: importMode,
        holdings: preview.map(({ ticker, shares, avg_price }) => ({
          ticker,
          shares,
          avg_price
        }))
      });
      await loadHoldings();
      setAnalysisStale(true);
      setImportRows([{ id: Date.now(), ticker: '', shares: '', avg_price: '' }]);
      setImportErrors([]);
    } catch (error) {
      alert('Import failed: ' + (error as Error).message);
    } finally {
      setImportLoading(false);
    }
  };

  const addImportRowAfter = (rowId: number) => {
    const newRow = { id: Date.now(), ticker: '', shares: '', avg_price: '' };
    setImportRows((prev) => {
      const index = prev.findIndex((row) => row.id === rowId);
      if (index === -1) {
        return [...prev, newRow];
      }
      const next = [...prev];
      next.splice(index + 1, 0, newRow);
      return next;
    });
  };

  const handleRunAnalysis = async () => {
    await loadAnalysis();
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

      <div className="card">
        <h2>Add Holdings</h2>
        <div className="advanced-import">
          <p className="muted">Add rows for each holding and import all at once.</p>
          <table className="import-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Shares</th>
                <th>Avg Price</th>
                <th />
              </tr>
            </thead>
            <tbody>
                {importRows.map((row, index) => (
                  <tr key={row.id}>
                  <td>
                    <input
                      type="text"
                      value={row.ticker}
                      onChange={(e) => {
                        const value = e.target.value;
                        setImportRows((prev) => prev.map((item) => (
                          item.id === row.id ? { ...item, ticker: value } : item
                        )));
                      }}
                      placeholder="AAPL"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={row.shares}
                      onChange={(e) => {
                        const value = e.target.value;
                        setImportRows((prev) => prev.map((item) => (
                          item.id === row.id ? { ...item, shares: value } : item
                        )));
                      }}
                      placeholder="10"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={row.avg_price}
                      onChange={(e) => {
                        const value = e.target.value;
                        setImportRows((prev) => prev.map((item) => (
                          item.id === row.id ? { ...item, avg_price: value } : item
                        )));
                      }}
                      placeholder="150.25"
                    />
                  </td>
                    <td>
                      <div className="import-row-actions">
                        {importRows.length > 1 && index !== 0 ? (
                          <button
                            type="button"
                            className="btn-delete"
                            onClick={() => setImportRows((prev) => prev.filter((item) => item.id !== row.id))}
                            aria-label="Remove row"
                          >
                            ✕
                          </button>
                        ) : (
                          <span className="import-row-spacer" />
                        )}
                        {index === importRows.length - 1
                        && row.ticker.trim()
                        && row.shares.trim()
                        && row.avg_price.trim() ? (
                          <button
                            type="button"
                            className="btn-save"
                            onClick={() => addImportRowAfter(row.id)}
                            aria-label="Add row"
                          >
                            +
                          </button>
                        ) : (
                          <span className="import-row-spacer" />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="form-row">
              <button
                type="button"
                className={`btn-secondary ${importMode === 'merge' ? 'btn-secondary-active' : ''}`}
                onClick={() => setImportMode('merge')}
            >
              Merge Import
            </button>
            <button
              type="button"
              className={`btn-secondary ${importMode === 'replace' ? 'btn-secondary-active' : ''}`}
              onClick={() => setImportMode('replace')}
            >
              Replace Import
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleImportHoldings}
              disabled={importLoading}
            >
              {importLoading ? 'Importing...' : 'Import Portfolio'}
            </button>
          </div>
          {importErrors.length > 0 && (
            <div className="error">
              {importErrors.map((err) => (
                <div key={err}>{err}</div>
              ))}
            </div>
          )}
        </div>
      </div>

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
                          aria-label="Edit holding"
                        >
                          ✎
                        </button>
                        <button 
                          onClick={() => handleDelete(holding.id, holding.ticker)}
                          className="btn-delete"
                          aria-label="Delete holding"
                        >
                          🗑
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
        <>
          <AnalysisMetrics portfolioAnalysis={portfolioAnalysis} />
          <Analysis portfolioAnalysis={portfolioAnalysis} />
          <div className="card">
            <h2>Earnings Call Summaries</h2>
            {transcriptsLoading && <span className="muted">Loading transcripts...</span>}
            {transcriptsError && <div className="error">{transcriptsError}</div>}
            {!transcriptsLoading && Object.keys(transcriptSummaries).length === 0 && (
              <span className="muted">No summaries available yet.</span>
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
    </div>
  );
}
