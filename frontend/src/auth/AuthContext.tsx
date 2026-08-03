import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { login as loginRequest, setToken } from "../api/client";
import type { UserRole } from "../api/types";

interface DecodedUser {
  email: string;
  role: UserRole;
}

interface AuthContextValue {
  user: DecodedUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function decodeToken(token: string): DecodedUser | null {
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return { email: decoded.sub, role: decoded.role };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DecodedUser | null>(() => {
    const stored = localStorage.getItem("wraithlink_token");
    return stored ? decodeToken(stored) : null;
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      login: async (email: string, password: string) => {
        const token = await loginRequest(email, password);
        setToken(token);
        setUser(decodeToken(token));
      },
      logout: () => {
        setToken(null);
        setUser(null);
      },
    }),
    [user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
