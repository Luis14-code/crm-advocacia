import { create } from "zustand";
import { api, setTokens, clearTokens } from "../lib/api";

export const useAuth = create((set) => ({
  user: JSON.parse(localStorage.getItem("user") || "null"),
  loading: false,
  error: null,

  async login(email, senha) {
    set({ loading: true, error: null });
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: { email, senha },
      });
      setTokens({ access: data.access_token, refresh: data.refresh_token });
      localStorage.setItem("user", JSON.stringify(data.user));
      set({ user: data.user, loading: false });
      return true;
    } catch (e) {
      set({ error: e.message, loading: false });
      return false;
    }
  },

  logout() {
    clearTokens();
    localStorage.removeItem("user");
    set({ user: null });
  },
}));
