import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  type ReactNode,
} from "react";
import { api, getErrorMessage } from "../api/client";

// ── Types ─────────────────────────────────────────────────────────────────────
interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
}

type AuthAction =
  | { type: "LOADING" }
  | { type: "SET_USER"; payload: User }
  | { type: "CLEAR" }
  | { type: "ERROR"; payload: string };

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

// ── Reducer ───────────────────────────────────────────────────────────────────
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "LOADING":  return { ...state, loading: true, error: null };
    case "SET_USER": return { user: action.payload, loading: false, error: null };
    case "CLEAR":    return { user: null, loading: false, error: null };
    case "ERROR":    return { ...state, loading: false, error: action.payload };
    default:         return state;
  }
}

// ── Context ───────────────────────────────────────────────────────────────────
const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, {
    user: null,
    loading: true,
    error: null,
  });

  const fetchMe = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) { dispatch({ type: "CLEAR" }); return; }

    dispatch({ type: "LOADING" });
    try {
      const { data } = await api.get<User>("/auth/me");
      dispatch({ type: "SET_USER", payload: data });
    } catch {
      localStorage.clear();
      dispatch({ type: "CLEAR" });
    }
  }, []);

  useEffect(() => { fetchMe(); }, [fetchMe]);

  const login = async (email: string, password: string) => {
    dispatch({ type: "LOADING" });
    try {
      const { data } = await api.post("/auth/login", { email, password });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      await fetchMe();
    } catch (err) {
      dispatch({ type: "ERROR", payload: getErrorMessage(err, "Login failed") });
      throw err;
    }
  };

  const register = async (email: string, password: string, fullName?: string) => {
    dispatch({ type: "LOADING" });
    try {
      await api.post("/auth/register", { email, password, full_name: fullName });
      await login(email, password);
    } catch (err) {
      dispatch({ type: "ERROR", payload: getErrorMessage(err, "Registration failed") });
      throw err;
    }
  };

  const logout = () => {
    localStorage.clear();
    dispatch({ type: "CLEAR" });
  };

  const clearError = () => dispatch({ type: "ERROR", payload: "" });

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, clearError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
