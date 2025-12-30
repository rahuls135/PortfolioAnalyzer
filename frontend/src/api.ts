import axios from 'axios';
import { supabase } from './supabase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_URL,
});

apiClient.interceptors.request.use(async (config) => {
  const {
    data: { session },
  } = await supabase.auth.getSession();

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
  
  getUserBySupabaseId: (supabaseUserId: string) =>
    apiClient.get<User>(`/api/users/supabase/${supabaseUserId}`),
  
  addHolding: (holdingData: HoldingCreate) => 
    apiClient.post<Holding>(`/api/holdings`, holdingData),
  
  updateHolding: (userId: number, holdingId: number, holdingData: Partial<HoldingCreate>) =>
    apiClient.patch<Holding>(`/api/users/${userId}/holdings/${holdingId}`, holdingData),
  
  getHoldings: (userId: number) => 
    apiClient.get<Holding[]>(`/api/users/${userId}/holdings`),
  
  deleteHolding: (userId: number, holdingId: number) => 
    apiClient.delete(`/api/users/${userId}/holdings/${holdingId}`),
  
  analyzePortfolio: (userId: number) => 
    apiClient.get<PortfolioAnalysis>(`/api/users/${userId}/analysis`),
  
  getStockPrice: (ticker: string) => 
    apiClient.get(`/api/stocks/${ticker}`)
};
