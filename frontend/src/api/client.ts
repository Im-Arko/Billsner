import axios, { type AxiosError } from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor ───────────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Response interceptor – token refresh ─────────────────────────────────────
let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

function processQueue(token: string) {
  refreshQueue.forEach((cb) => cb(token));
  refreshQueue = [];
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean };

    if (error.response?.status === 401 && original && !original._retry) {
      const refresh = localStorage.getItem("refresh_token");
      if (!refresh) {
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue this request until the refresh completes
        return new Promise((resolve) => {
          refreshQueue.push((token) => {
            original.headers!.Authorization = `Bearer ${token}`;
            resolve(api(original));
          });
        });
      }

      original._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh_token: refresh,
        });
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
        processQueue(data.access_token);
        return api(original);
      } catch {
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ── Helper – extract a human-readable error message ──────────────────────────
export function getErrorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).join(", ");
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

// ── Types ─────────────────────────────────────────────────────────────────────
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
  recent_bills: { id: number; filename: string; status: string; created_at: string; error_message?: string | null }[];
}
