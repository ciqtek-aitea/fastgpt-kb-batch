import { useState, useCallback } from 'react';
import api from '../api/client';

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post('/auth/login', { username, password });
      const token = resp.data.token;
      localStorage.setItem('session_token', token);
      localStorage.setItem('login_creds', JSON.stringify({ username, password }));
      return true;
    } catch (e: any) {
      setError(e.response?.data?.detail || '登录失败');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('session_token');
    localStorage.removeItem('login_creds');
    window.location.href = '/login';
  }, []);

  const check = useCallback(async () => {
    try {
      const resp = await api.get('/auth/check');
      return resp.data.valid;
    } catch {
      return false;
    }
  }, []);

  const tryRestore = useCallback(async (): Promise<boolean> => {
    const sessionToken = localStorage.getItem('session_token');
    if (sessionToken) {
      const valid = await check();
      if (valid) return true;
    }

    const credsStr = localStorage.getItem('login_creds');
    if (!credsStr) return false;

    try {
      const { username, password } = JSON.parse(credsStr);
      return await login(username, password);
    } catch {
      return false;
    }
  }, [check, login]);

  return { login, logout, check, tryRestore, loading, error };
}
