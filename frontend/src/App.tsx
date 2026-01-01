import { useState, useEffect, useRef } from 'react';
import './App.css';
import { api, type User as ApiUser } from './api';
import { computeRiskRecommendation } from './utils/risk';
import { supabase } from './supabase';
import Auth from './Auth';
import ProfileForm from './components/ProfileForm';
import Portfolio from './components/Portfolio';
import type { User as SupabaseUser } from '@supabase/supabase-js';

function App() {
  const [user, setUser] = useState<SupabaseUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<number | null>(null);
  const [profile, setProfile] = useState<ApiUser | null>(null);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsAge, setSettingsAge] = useState('');
  const [settingsIncome, setSettingsIncome] = useState('');
  const [settingsRiskTolerance, setSettingsRiskTolerance] = useState('moderate');
  const [settingsRiskAssessmentMode, setSettingsRiskAssessmentMode] = useState<'manual' | 'ai'>('manual');
  const [settingsRetirementYears, setSettingsRetirementYears] = useState('');
  const [settingsObligationsAmount, setSettingsObligationsAmount] = useState('');
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const profileMenuRef = useRef<HTMLDivElement | null>(null);

  // Check for existing session and profile on mount
  useEffect(() => {
    const initAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user ?? null);
      
      if (session?.user) {
        console.log('Supabase User ID:', session.user.id);
        await fetchProfile();
      }
      
      setLoading(false);
    };

    initAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setUser(session?.user ?? null);
      
      if (session?.user) {
        await fetchProfile();
      } else {
        setUserId(null);
        setProfile(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await api.getProfile();
      console.log('Profile found:', response.data);
      
      // User profile exists, go straight to portfolio
      setUserId(response.data.id);
      setProfile(response.data);
    } catch (error: any) {
      setProfile(null);
      console.log('Profile check error:', error.response?.status, error.response?.data);
      
      // User profile doesn't exist, show profile creation form
      if (error.response?.status === 404) {
        console.log('No profile found, showing profile creation form');
      }
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setUserId(null);
    setProfile(null);
  };

  const handleProfileCreated = (newUserId: number) => {
    setUserId(newUserId);
    fetchProfile();
  };

  const openSettings = () => {
    if (!profile) {
      return;
    }

    setSettingsAge(profile.age.toString());
    setSettingsIncome(profile.income.toString());
    setSettingsRiskTolerance(profile.risk_tolerance);
    setSettingsRiskAssessmentMode((profile.risk_assessment_mode as 'manual' | 'ai') || 'manual');
    setSettingsRetirementYears(profile.retirement_years.toString());
    setSettingsObligationsAmount(
      profile.obligations_amount !== undefined && profile.obligations_amount !== null
        ? profile.obligations_amount.toString()
        : ''
    );
    setSettingsError(null);
    setSettingsOpen(true);
    setProfileMenuOpen(false);
  };

  const closeSettings = () => {
    setSettingsOpen(false);
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    const age = parseInt(settingsAge, 10);
    const income = parseFloat(settingsIncome);
    const retirementYears = parseInt(settingsRetirementYears, 10);
    const obligationsAmount = settingsObligationsAmount ? parseFloat(settingsObligationsAmount) : undefined;

    if (Number.isNaN(age) || Number.isNaN(income) || Number.isNaN(retirementYears)) {
      setSettingsError('Please enter valid numbers for all fields.');
      return;
    }

    setSettingsSaving(true);
    setSettingsError(null);
    try {
      const response = await api.updateProfile({
        age,
        income,
        retirement_years: retirementYears,
        obligations_amount: Number.isNaN(obligationsAmount ?? 0) ? undefined : obligationsAmount,
        risk_assessment_mode: settingsRiskAssessmentMode,
        risk_tolerance: settingsRiskAssessmentMode === 'manual' ? settingsRiskTolerance : undefined
      });
      setProfile(response.data);
      setSettingsOpen(false);
    } catch (error: any) {
      setSettingsError(error.message || 'Failed to update profile.');
    } finally {
      setSettingsSaving(false);
    }
  };

  useEffect(() => {
    if (!profileMenuOpen) {
      return;
    }

    const handleClickOutside = (event: MouseEvent) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setProfileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [profileMenuOpen]);

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
        <div className="header-left">
          <h1>📊 AI Portfolio Analyzer</h1>
        </div>
        <div className="header-actions" ref={profileMenuRef}>
          <button
            className="profile-menu-trigger"
            onClick={() => setProfileMenuOpen((open) => !open)}
            aria-expanded={profileMenuOpen}
          >
            <span className="avatar-circle">{user.email?.slice(0, 1).toUpperCase()}</span>
            <span className="profile-menu-label">Settings</span>
            <span className={`profile-caret ${profileMenuOpen ? 'open' : ''}`}>▾</span>
          </button>
          {profileMenuOpen && (
            <div className="profile-menu">
              <div className="profile-menu-header">
                <span className="profile-email">{user.email}</span>
              </div>
              <button
                type="button"
                className="profile-menu-item"
                onClick={openSettings}
                disabled={!profile}
              >
                Profile Settings
              </button>
              <button
                type="button"
                className="profile-menu-item"
                onClick={handleSignOut}
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      </header>

      {settingsOpen && (
        <div className="modal-backdrop" onClick={closeSettings}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Profile Settings</h2>
              <button type="button" className="modal-close" onClick={closeSettings}>
                ✕
              </button>
            </div>
            <form onSubmit={handleSaveSettings}>
              <div className="form-group">
                <label>Age:</label>
                <input
                  type="number"
                  value={settingsAge}
                  onChange={(e) => setSettingsAge(e.target.value)}
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Annual Income ($):</label>
                <input
                  type="number"
                  value={settingsIncome}
                  onChange={(e) => setSettingsIncome(e.target.value)}
                  required
                />
              </div>
              
              <div className="form-group">
              <div className="form-group">
                <label>Major Financial Obligations:</label>
                <input
                  type="number"
                  placeholder="Monthly total (rent, mortgage, loans, car payments)"
                  value={settingsObligationsAmount}
                  onChange={(e) => setSettingsObligationsAmount(e.target.value)}
                />
                <span className="muted">Include recurring payments like rent, mortgage, loans, or car.</span>
              </div>

              <div className="form-group">
                <label>Risk Tolerance:</label>
                <select
                  value={settingsRiskTolerance}
                  onChange={(e) => {
                    setSettingsRiskTolerance(e.target.value);
                    setSettingsRiskAssessmentMode('manual');
                  }}
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
                  value={settingsRetirementYears}
                  onChange={(e) => setSettingsRetirementYears(e.target.value)}
                  required
                />
              </div>
              {settingsError && <div className="error">{settingsError}</div>}
              <div className="risk-mode-bar">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    const parsedAge = parseInt(settingsAge, 10);
                    const parsedIncome = parseFloat(settingsIncome);
                    const parsedRetirementYears = parseInt(settingsRetirementYears, 10);
                    const parsedObligations = parseFloat(settingsObligationsAmount || '0');

                    if (
                      Number.isNaN(parsedAge)
                      || Number.isNaN(parsedIncome)
                      || Number.isNaN(parsedRetirementYears)
                    ) {
                      setSettingsError('Enter age, income, and retirement years to get an AI recommendation.');
                      return;
                    }

                    const recommendation = computeRiskRecommendation({
                      age: parsedAge,
                      income: parsedIncome,
                      retirementYears: parsedRetirementYears,
                      obligationsAmount: Number.isNaN(parsedObligations) ? 0 : parsedObligations
                    });
                    setSettingsRiskTolerance(recommendation);
                    setSettingsRiskAssessmentMode('ai');
                  }}
                >
                  Use AI Recommendation
                </button>
                <span className="muted">
                  Mode: {settingsRiskAssessmentMode === 'ai' ? 'AI recommended' : 'Manual'}
                </span>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={closeSettings}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={settingsSaving}>
                  {settingsSaving ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <main className="container">
        {!userId && (
          <ProfileForm onProfileCreated={handleProfileCreated} />
        )}

        {userId && (
          <Portfolio />
        )}
      </main>
    </div>
  );
}

export default App;
