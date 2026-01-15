import { useState } from 'react';
import { api } from '../api';
import { computeRiskRecommendation } from '../utils/risk';

interface ProfileFormProps {
  onProfileCreated: (userId: number) => void;
}

export default function ProfileForm({ onProfileCreated }: ProfileFormProps) {
  const [age, setAge] = useState('');
  const [income, setIncome] = useState('');
  const [riskTolerance, setRiskTolerance] = useState('moderate');
  const [riskAssessmentMode, setRiskAssessmentMode] = useState<'manual' | 'ai'>('manual');
  const [retirementYears, setRetirementYears] = useState('');
  const [obligationsAmount, setObligationsAmount] = useState('');

  const handleAiRecommendation = () => {
    const parsedAge = parseInt(age, 10);
    const parsedIncome = parseFloat(income);
    const parsedRetirementYears = parseInt(retirementYears, 10);
    const parsedObligations = parseFloat(obligationsAmount || '0');

    if (Number.isNaN(parsedAge) || Number.isNaN(parsedIncome) || Number.isNaN(parsedRetirementYears)) {
      alert('Enter age, income, and retirement years to get AI Insights.');
      return;
    }

    const recommendation = computeRiskRecommendation({
      age: parsedAge,
      income: parsedIncome,
      retirementYears: parsedRetirementYears,
      obligationsAmount: Number.isNaN(parsedObligations) ? 0 : parsedObligations
    });
    setRiskTolerance(recommendation);
    setRiskAssessmentMode('ai');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const payload = {
        age: parseInt(age),
        income: parseFloat(income),
        retirement_years: parseInt(retirementYears),
        obligations_amount: obligationsAmount ? parseFloat(obligationsAmount) : undefined,
        risk_assessment_mode: riskAssessmentMode
      } as const;

      const response = await api.createUser({
        ...payload,
        risk_tolerance: riskAssessmentMode === 'manual' ? riskTolerance : undefined
      });
      
      onProfileCreated(response.data.id);
      alert('Profile created successfully!');
    } catch (error: any) {
      alert('Error creating profile: ' + error.message);
    }
  };

  return (
    <div className="card">
      <h2>Create Your Profile</h2>
      <form onSubmit={handleSubmit}>
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
          <label>Major Financial Obligations:</label>
          <input
            type="number"
            placeholder="Monthly total (rent, mortgage, loans, car payments)"
            value={obligationsAmount}
            onChange={(e) => setObligationsAmount(e.target.value)}
          />
          <span className="muted">Include recurring payments like rent, mortgage, loans, or car.</span>
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
        <div className="form-group">
          <label>Risk Tolerance:</label>
          <select
            value={riskTolerance}
            onChange={(e) => {
              setRiskTolerance(e.target.value);
              setRiskAssessmentMode('manual');
            }}
          >
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
        </div>

        <div className="risk-mode-bar">
          <button type="button" className="btn-primary btn-with-icon" onClick={handleAiRecommendation}>
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
            Use AI Insights
          </button>
          <span className="muted">
            Mode: {riskAssessmentMode === 'ai' ? 'AI insights' : 'Manual'}
          </span>
        </div>
      </form>
    </div>
  );
}
