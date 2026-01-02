import axios from 'axios';
import { supabase } from './supabase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_URL,
});

apiClient.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();

  console.log("Interceptor running. Token:", session?.access_token);

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }

  return config;
});


// Define types for your data
export interface User {
  id: number;
  supabase_user_id: string;
  age: number;
  income: number;
  risk_tolerance: string;
  risk_assessment_mode: string;
  retirement_years: number;
  obligations_amount?: number;
  ai_analysis?: string;
}

export interface UserCreate {
  age: number;
  income: number;
  risk_tolerance?: string;
  risk_assessment_mode?: string;
  retirement_years: number;
  obligations_amount?: number;
}

export interface UserUpdate {
  age?: number;
  income?: number;
  risk_tolerance?: string;
  risk_assessment_mode?: string;
  retirement_years?: number;
  obligations_amount?: number;
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

export interface HoldingBulkRequest {
  mode: 'merge' | 'replace';
  holdings: HoldingCreate[];
}

export interface TickerValidation {
  ticker: string;
  valid: boolean;
}

export interface PortfolioHolding extends Holding {
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
  metrics: {
    sector_allocation: Array<{ sector: string; value: number; pct: number }>;
    top_holdings: Array<{ ticker: string; value: number; pct: number }>;
    concentration_top3_pct: number;
    diversification_score: number;
  };
  user_profile: {
    age: number;
    risk_tolerance: string;
    risk_assessment_mode?: string;
    retirement_years: number;
    obligations_amount?: number;
  };
  analysis_meta: {
    cached: boolean;
    last_analysis_at: string | null;
    next_available_at: string | null;
    cooldown_remaining_seconds: number;
  };
}

export const api = {
  createUser: (userData: UserCreate) => 
    apiClient.post<User>(`/api/users`, userData),
  
  getUser: (userId: number) => 
    apiClient.get<User>(`/api/users/${userId}`),
  
  getProfile: () =>
    apiClient.get<User>(`/api/users/me`),

  updateProfile: (userData: UserUpdate) =>
    apiClient.patch<User>(`/api/users/me`, userData),
  
  addHolding: (holdingData: HoldingCreate) => 
    apiClient.post<Holding>(`/api/holdings`, holdingData),

  updateHolding: (holdingId: number, data: { ticker: string; shares: number; avg_price: number }) => 
    apiClient.patch(`/api/holdings/${holdingId}`, data),
  
  getHoldings: () => 
    apiClient.get<Holding[]>(`/api/holdings`),
  
  deleteHolding: (holdingId: number) => 
    apiClient.delete(`/api/holdings/${holdingId}`),

  bulkUpsertHoldings: (payload: HoldingBulkRequest) =>
    apiClient.post<Holding[]>(`/api/holdings/bulk`, payload),

  validateTicker: (ticker: string) =>
    apiClient.get<TickerValidation>(`/api/tickers/validate/${ticker}`),
  
  analyzePortfolio: () => 
    apiClient.get<PortfolioAnalysis>(`/api/analysis`),
  
  getStockPrice: (ticker: string) => 
    apiClient.get(`/api/stocks/${ticker}`)
};
