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
    apiClient.post<User>(`/api/users`, userData),
  
  getUser: (userId: number) => 
    apiClient.get<User>(`/api/users/${userId}`),
  
  getUserBySupabaseId: () =>
    apiClient.get<User>(`/api/users/me`),
  
  addHolding: (holdingData: HoldingCreate) => 
    apiClient.post<Holding>(`/api/holdings`, holdingData),
  
  getHoldings: () => 
    apiClient.get<Holding[]>(`/api/holdings`),
  
  deleteHolding: (holdingId: number) => 
    apiClient.delete(`/api/holdings/${holdingId}`),
  
  analyzePortfolio: () => 
    apiClient.get<PortfolioAnalysis>(`/api/analysis`),
  
  getStockPrice: (ticker: string) => 
    apiClient.get(`/api/stocks/${ticker}`)
};
