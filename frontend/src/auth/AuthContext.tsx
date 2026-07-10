import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useMutation } from "@apollo/client/react";
import { LoginDocument } from "../generated/graphql";
import {
  clearSession,
  getSession,
  saveSession,
  type Session,
} from "./tokenStore";

type AuthContextValue = {
  session: Session | null;
  isAdmin: boolean;
  loggingIn: boolean;
  /** Returns an error message on failure, or null on success. */
  login: (username: string, password: string) => Promise<string | null>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => getSession());
  const [loginMutation, { loading: loggingIn }] = useMutation(LoginDocument);

  const login = useCallback(
    async (username: string, password: string): Promise<string | null> => {
      try {
        const { data } = await loginMutation({
          variables: { username, password },
        });
        const payload = data?.login;
        if (payload?.token && payload.username) {
          const next: Session = {
            token: payload.token,
            username: payload.username,
            expiresAt: payload.expiresAt ?? null,
          };
          saveSession(next);
          setSession(next);
          return null;
        }
        return payload?.error ?? "Login failed.";
      } catch (err) {
        return err instanceof Error ? err.message : "Login failed.";
      }
    },
    [loginMutation],
  );

  const logout = useCallback(() => {
    clearSession();
    setSession(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ session, isAdmin: session !== null, loggingIn, login, logout }),
    [session, loggingIn, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
