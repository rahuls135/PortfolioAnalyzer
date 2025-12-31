import { useState } from 'react';
import { api } from '../api';

interface ProfileFormProps {
  onProfileCreated: (userId: number) => void;
}

export default function ProfileForm({ onProfileCreated }: ProfileFormProps) {
  const [age, setAge] = useState('');
  const [income, setIncome] = useState('');
  const [riskTolerance, setRiskTolerance] = useState('moderate');
  const [retirementYears, setRetirementYears] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await api.createUser({
        age: parseInt(age),
        income: parseFloat(income),
        risk_tolerance: riskTolerance,
        retirement_years: parseInt(retirementYears)
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
  );
}
