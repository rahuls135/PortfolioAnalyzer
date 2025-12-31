import { useState, useEffect } from 'react';
import './App.css';
import { api } from './api';
import { supabase } from './supabase';
import Auth from './Auth';
import ProfileForm from './components/ProfileForm';
import Portfolio from './components/Portfolio';
import Analysis from './components/Analysis';
import type { PortfolioAnalysis } from './api';
import type { User } from '@supabase/supabase-js';

type View = 'profile' | 'portfolio' | 'analysis';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<number | null>(null);
  const [view, setView] = useState<View>('profile');
  const [portfolioAnalysis, setPortfolioAnalysis] = useState<PortfolioAnalysis | null>(null);

  // Check for existing session and profile on mount
  useEffect(() => {
    const initAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user ?? null);
      
      if (session?.user) {
        console.log('Supabase User ID:', session.user.id);
        await checkExistingProfile(session.user.id);
      }
      
      setLoading(false);
    };

    initAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setUser(session?.user ?? null);
      
      if (session?.user) {
        await checkExistingProfile();
      } else {
        setUserId(null);
        setView('profile');
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const checkExistingProfile = async () => {
    
    try {
      const response = await api.getProfile();
      console.log('Profile found:', response.data);
      
      // User profile exists, go straight to portfolio
      setUserId(response.data.id);
      setView('portfolio');
    } catch (error: any) {
      console.log('Profile check error:', error.response?.status, error.response?.data);
      
      // User profile doesn't exist, show profile creation form
      if (error.response?.status === 404) {
        console.log('No profile found, showing profile creation form');
        setView('profile');
      }
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setUserId(null);
    setView('profile');
    setPortfolioAnalysis(null);
  };

  const handleProfileCreated = (newUserId: number) => {
    setUserId(newUserId);
    setView('portfolio');
  };

  const handleAnalyze = async () => {
    try {
      const response = await api.analyzePortfolio();
      setPortfolioAnalysis(response.data);
      setView('analysis');
    } catch (error) {
      alert('Error analyzing portfolio: ' + (error as Error).message);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        Loading...
      </div>
    );
  }

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
          <ProfileForm 
            supabaseUserId={user.id}
            onProfileCreated={handleProfileCreated}
          />
        )}

        {userId && view === 'portfolio' && (
          <Portfolio 
            userId={userId}
            onAnalyze={handleAnalyze}
          />
        )}

        {userId && view === 'analysis' && portfolioAnalysis && (
          <Analysis portfolioAnalysis={portfolioAnalysis} />
        )}
      </main>
    </div>
  );
}

export default App;