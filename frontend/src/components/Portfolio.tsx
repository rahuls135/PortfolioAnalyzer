import { useState, useEffect } from 'react';
import { api } from '../api';
import type { Holding } from '../api';

interface PortfolioProps {
  userId: number;
  onAnalyze: () => void;
}

export default function Portfolio({ userId, onAnalyze }: PortfolioProps) {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [ticker, setTicker] = useState('');
  const [shares, setShares] = useState('');
  const [avgPrice, setAvgPrice] = useState('');

  useEffect(() => {
    loadHoldings();
  }, [userId]);

  const loadHoldings = async () => {
    try {
      const response = await api.getHoldings(userId);
      setHoldings(response.data);
    } catch (error) {
      console.error('Error loading holdings:', error);
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
      // Check if holding already exists
      const existing = holdings.find(h => h.ticker === newTicker);

      if (existing) {
        // Calculate new average price
        const totalShares = existing.shares + newShares;
        const updatedAvgPrice =
          (existing.shares * existing.avg_price + newShares * newPrice) / totalShares;
        console.log("updating holding...");
        await api.updateHolding(userId, existing.id, {
          shares: totalShares,
          avg_price: updatedAvgPrice
        });
      } else {
        // Create new holding
        console.log("Create new holding...");
        await api.addHolding({
          ticker: newTicker,
          shares: newShares,
          avg_price: newPrice
        });
      }
      console.log("holding created!");
      await loadHoldings();

      // Clear input fields
      setTicker('');
      setShares('');
      setAvgPrice('');

      alert('Holding saved!');
    } catch (error) {
      alert('Error saving holding: ' + (error as Error).message);
    }
  };

  return (
    <div>
      <div className="card">
        <h2>Add / Update Holding</h2>
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
              placeholder="Average Purchase Price"
              value={avgPrice}
              onChange={(e) => setAvgPrice(e.target.value)}
              required
            />
            <button type="submit" className="btn-primary">Save</button>
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
                <th>Average Price</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.id}>
                  <td>{holding.ticker}</td>
                  <td>{holding.shares}</td>
                  <td>${holding.avg_price.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {holdings.length > 0 && (
          <button onClick={onAnalyze} className="btn-primary">
            Analyze Portfolio
          </button>
        )}
      </div>
    </div>
  );
}
