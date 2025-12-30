import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Define types for your data
export interface User {
  id: number;
  supabase_user_id: string;
  age: number;
  income: number;
  risk_tolerance: string;
  retirement_years: number;
  ai_analysis?: string;
}

export interface UserCreate {
  supabase_user_id: string;
  age: number;
  income: number;
  risk_tolerance: string;
  retirement_years: number;
}

export interface Holding {
  id: number;
  ticker: string;
  shares: number;
  avg_price: number;
}

export interface HoldingCreate {
  ticker: string;
  shares: number;
  avg_price: number;
}

export interface PortfolioHolding {
  ticker: string;
  shares: number;
  avg_price: number;
  current_price: number;
  current_value: number;
  gain_loss: number;
  gain_loss_pct: number;
  sector: string | null;
}

export interface PortfolioAnalysis {
  total_value: number;
  holdings: PortfolioHolding[];
  ai_analysis: string;
  user_profile: {
    age: number;
    risk_tolerance: string;
    retirement_years: number;
  };
}

export const api = {
  createUser: (userData: UserCreate) => 
    axios.post<User>(`${API_URL}/api/users`, userData),
  
  getUser: (userId: number) => 
    axios.get<User>(`${API_URL}/api/users/${userId}`),
  
  getUserBySupabaseId: (supabaseUserId: string) =>
    axios.get<User>(`${API_URL}/api/users/supabase/${supabaseUserId}`),
  
  addHolding: (userId: number, holdingData: HoldingCreate) => 
    axios.post<Holding>(`${API_URL}/api/users/${userId}/holdings`, holdingData),
  
  updateHolding: (userId: number, holdingId: number, holdingData: Partial<HoldingCreate>) =>
    axios.patch<Holding>(`${API_URL}/api/users/${userId}/holdings/${holdingId}`, holdingData),
  
  getHoldings: (userId: number) => 
    axios.get<Holding[]>(`${API_URL}/api/users/${userId}/holdings`),
  
  deleteHolding: (userId: number, holdingId: number) => 
    axios.delete(`${API_URL}/api/users/${userId}/holdings/${holdingId}`),
  
  analyzePortfolio: (userId: number) => 
    axios.get<PortfolioAnalysis>(`${API_URL}/api/users/${userId}/analysis`),
  
  getStockPrice: (ticker: string) => 
    axios.get(`${API_URL}/api/stocks/${ticker}`)
};