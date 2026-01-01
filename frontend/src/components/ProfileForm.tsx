import { useState } from 'react';
import { api } from '../api';

interface ProfileFormProps {
  onProfileCreated: (userId: number) => void;
}

export default function ProfileForm({ onProfileCreated }: ProfileFormProps) {
  const [age, setAge] = useState('');
  const [income, setIncome] = useState('');
  const [riskTolerance, setRiskTolerance] = useState('moderate');
  const [riskAssessmentMode, setRiskAssessmentMode] = useState<'manual' | 'ai'>('manual');
  const [retirementYears, setRetirementYears] = useState('');
  const [obligations, setObligations] = useState<string[]>([]);

  const obligationOptions = [
    'Student loans',
    'Rent',
    'Mortgage',
    'Car payments'
  ];

  const toggleObligation = (value: string) => {
    setObligations((prev) => (
      prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value]
    ));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const payload = {
        age: parseInt(age),
        income: parseFloat(income),
        retirement_years: parseInt(retirementYears),
        obligations,
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
          <label>Risk Assessment:</label>
          <div className="radio-group">
            <label>
              <input
                type="radio"
                name="risk-assessment"
                value="manual"
                checked={riskAssessmentMode === 'manual'}
                onChange={() => setRiskAssessmentMode('manual')}
              />
              Manual
            </label>
            <label>
              <input
                type="radio"
                name="risk-assessment"
                value="ai"
                checked={riskAssessmentMode === 'ai'}
                onChange={() => setRiskAssessmentMode('ai')}
              />
              AI Recommended
            </label>
          </div>
        </div>

        <div className="form-group">
          <label>Risk Tolerance:</label>
          <select
            value={riskTolerance}
            onChange={(e) => setRiskTolerance(e.target.value)}
            disabled={riskAssessmentMode === 'ai'}
          >
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
          {riskAssessmentMode === 'ai' && (
            <span className="muted">We will recommend a risk level based on your profile.</span>
          )}
        </div>

        <div className="form-group">
          <label>Major Financial Obligations:</label>
          <div className="checkbox-group">
            {obligationOptions.map((option) => (
              <label key={option}>
                <input
                  type="checkbox"
                  checked={obligations.includes(option)}
                  onChange={() => toggleObligation(option)}
                />
                {option}
              </label>
            ))}
          </div>
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
  );
}
