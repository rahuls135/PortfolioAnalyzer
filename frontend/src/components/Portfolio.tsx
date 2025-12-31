import { useState, useEffect } from 'react';
import { api } from '../api';
import type { Holding } from '../api';

interface PortfolioProps {
  onAnalyze: () => void;
}

export default function Portfolio({ onAnalyze }: PortfolioProps) {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [ticker, setTicker] = useState('');
  const [shares, setShares] = useState('');
  const [avgPrice, setAvgPrice] = useState('');
  
  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editShares, setEditShares] = useState('');
  const [editAvgPrice, setEditAvgPrice] = useState('');

  useEffect(() => {
    loadHoldings();
  }, []);

  const loadHoldings = async () => {
    try {
      const response = await api.getHoldings();
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
      await api.addHolding({
        ticker: newTicker,
        shares: newShares,
        avg_price: newPrice
      });

      await loadHoldings();
      
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

  const handleSaveEdit = async (holdingId: number) => {
    const newShares = parseFloat(editShares);
    const newPrice = parseFloat(editAvgPrice);

    if (isNaN(newShares) || isNaN(newPrice)) {
      alert('Please enter valid numbers.');
      return;
    }

    try {
      await api.updateHolding(holdingId, {
        shares: newShares,
        avg_price: newPrice
      });

      await loadHoldings();
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
      alert('Holding deleted!');
    } catch (error) {
      alert('Error deleting holding: ' + (error as Error).message);
    }
  };

  return (
    <div>
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
                <th>Average Price</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.id}>
                  <td>{holding.ticker}</td>
                  
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
                      <td>
                        <button 
                          onClick={() => handleSaveEdit(holding.id)}
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
        
        {holdings.length > 0 && (
          <button onClick={onAnalyze} className="btn-primary">
            Analyze Portfolio
          </button>
        )}
      </div>
    </div>
  );
}