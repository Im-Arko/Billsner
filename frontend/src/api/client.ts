import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem("refresh_token");
      if (refresh && !error.config._retry) {
        error.config._retry = true;
        try {
          const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api(error.config);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export interface Expense {
  id: number;
  vendor_name: string | null;
  bill_number: string | null;
  total_amount: string | null;
  tax_amount: string | null;
  expense_date: string | null;
  currency: string;
  category_name: string | null;
  is_duplicate: boolean;
  classification_confidence: number | null;
  created_at: string;
}

export interface Summary {
  total_expenses: string;
  expense_count: number;
  by_category: Record<string, string>;
  by_vendor: Record<string, string>;
  monthly_trend: { year: number; month: number; total: number }[];
  duplicate_count: number;
  recent_bills: { id: number; filename: string; status: string; created_at: string }[];
}
