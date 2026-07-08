import type { User } from "../../lib/auth";

export type AuthResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
};

export type AuthContextValue = {
  user: User | null;
  loading: boolean;
  loginWithGoogle: (credential: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};
