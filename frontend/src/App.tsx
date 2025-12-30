import { useState, useEffect } from 'react';
import './App.css';
import { api } from './api';
import { supabase } from './supabase';
import Auth from './Auth';
import type { Holding, PortfolioAnalysis } from './api';
import type { User } from '@supabase/supabase-js';

type View = 'profile' | 'portfolio' | 'analysis';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  
  const [userId, setUserId] = useState<number | null>(null);
  const [view, setView] = useState<View>('profile');
  
  // User profile state
  const [age, setAge] = useState<string>('');
  const [income, setIncome] = useState<string>('');
  const [riskTolerance, setRiskTolerance] = useState<string>('moderate');
  const [retirementYears, setRetirementYears] = useState<string>('');
  const [aiAnalysis, setAiAnalysis] = useState<string>('');
  
  // Portfolio state
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [ticker, setTicker] = useState<string>('');
  const [shares, setShares] = useState<string>('');
  const [purchasePrice, setPurchasePrice] = useState<string>('');
  
  // Analysis state
  const [portfolioAnalysis, setPortfolioAnalysis] = useState<PortfolioAnalysis | null>(null);

  // Check for existing session on mount
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setUserId(null);
    setView('profile');
  };

const handleCreateProfile = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!user) return;
  
  try {
    const response = await api.createUser({
      supabase_user_id: user.id,
      age: parseInt(age),
      income: parseFloat(income),
      risk_tolerance: riskTolerance,
      retirement_years: parseInt(retirementYears)
    });
    setUserId(response.data.id);
    setAiAnalysis(response.data.ai_analysis || '');
    setView('portfolio');
    alert('Profile created successfully!');
  } catch (error: any) {
    alert('Error creating profile: ' + error.message);
  }
};

  const handleAddHolding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;
    
    try {
      await api.addHolding(userId, {
        ticker: ticker.toUpperCase(),
        shares: parseFloat(shares),
        purchase_price: parseFloat(purchasePrice),
        purchase_date: new Date().toISOString()
      });
      
      const response = await api.getHoldings(userId);
      setHoldings(response.data);
      
      setTicker('');
      setShares('');
      setPurchasePrice('');
      
      alert('Holding added!');
    } catch (error) {
      alert('Error adding holding: ' + (error as Error).message);
    }
  };

  const handleAnalyze = async () => {
    if (!userId) return;
    
    try {
      const response = await api.analyzePortfolio(userId);
      setPortfolioAnalysis(response.data);
      setView('analysis');
    } catch (error) {
      alert('Error analyzing portfolio: ' + (error as Error).message);
    }
  };

  const loadHoldings = async () => {
    if (!userId) return;
    
    try {
      const response = await api.getHoldings(userId);
      setHoldings(response.data);
    } catch (error) {
      console.error('Error loading holdings:', error);
    }
  };

  useEffect(() => {
    if (userId && view === 'portfolio') {
      loadHoldings();
    }
  }, [userId, view]);

  // Show loading state
  if (loading) {
    return <div>Loading...</div>;
  }

  // Show auth screen if not logged in
  if (!user) {
    return <Auth onAuthSuccess={() => {}} />;
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>📊 AI Portfolio Analyzer</h1>
        <div className="header-actions">
          {userId && (
            <nav>
              <button onClick={() => setView('portfolio')}>Portfolio</button>
              <button onClick={() => setView('analysis')}>Analysis</button>
            </nav>
          )}
          <div className="user-info">
            <span>{user.email}</span>
            <button onClick={handleSignOut} className="sign-out-btn">
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="container">
        {!userId && view === 'profile' && (
          <div className="card">
            <h2>Create Your Profile</h2>
            <form onSubmit={handleCreateProfile}>
              <div className="form-group">
                <label>Age:</label>
                <input
                  type="number"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Annual Income ($):</label>
                <input
                  type="number"
                  value={income}
                  onChange={(e) => setIncome(e.target.value)}
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Risk Tolerance:</label>
                <select
                  value={riskTolerance}
                  onChange={(e) => setRiskTolerance(e.target.value)}
                >
                  <option value="conservative">Conservative</option>
                  <option value="moderate">Moderate</option>
                  <option value="aggressive">Aggressive</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Years Until Retirement:</label>
                <input
                  type="number"
                  value={retirementYears}
                  onChange={(e) => setRetirementYears(e.target.value)}
                  required
                />
              </div>
              
              <button type="submit" className="btn-primary">
                Create Profile
              </button>
            </form>
          </div>
        )}

        {userId && view === 'portfolio' && (
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
                    placeholder="Purchase Price"
                    value={purchasePrice}
                    onChange={(e) => setPurchasePrice(e.target.value)}
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
                      <th>Purchase Price</th>
                      <th>Purchase Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map((holding) => (
                      <tr key={holding.id}>
                        <td>{holding.ticker}</td>
                        <td>{holding.shares}</td>
                        <td>${holding.purchase_price.toFixed(2)}</td>
                        <td>{new Date(holding.purchase_date).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              
              {holdings.length > 0 && (
                <button onClick={handleAnalyze} className="btn-primary">
                  Analyze Portfolio
                </button>
              )}
            </div>
          </div>
        )}

        {userId && view === 'analysis' && portfolioAnalysis && (
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
        )}
      </main>
    </div>
  );
}

export default App;