import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, User } from "../api/client";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem("documind_token")) {
      setLoading(false);
      return;
    }
    api.me().then(setUser).catch(() => localStorage.removeItem("documind_token")).finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    async login(email, password) {
      const result = await api.login({ email, password });
      localStorage.setItem("documind_token", result.access_token);
      setUser(result.user);
    },
    async register(email, password, fullName) {
      const result = await api.register({ email, password, full_name: fullName });
      localStorage.setItem("documind_token", result.access_token);
      setUser(result.user);
    },
    logout() {
      localStorage.removeItem("documind_token");
      setUser(null);
    },
  }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
