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
      // 持久化凭证用于自动恢复
      localStorage.setItem('login_creds', JSON.stringify({ username, password }));
      return true;
    } catch (e: any) {
      setError(e.response?.data?.detail || '登录失败');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const loginWithToken = useCallback(async (token: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post('/auth/token', { token });
      const sessionToken = resp.data.token;
      localStorage.setItem('session_token', sessionToken);
      return true;
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Token 无效');
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

  /** 尝试用已保存的凭证自动恢复登录 */
  const tryRestore = useCallback(async (): Promise<boolean> => {
    const sessionToken = localStorage.getItem('session_token');
    if (sessionToken) {
      // 先检查现有 session 是否有效
      const valid = await check();
      if (valid) return true;
    }

    // session 失效，尝试用保存的凭证重新登录
    const credsStr = localStorage.getItem('login_creds');
    if (!credsStr) return false;

    try {
      const { username, password } = JSON.parse(credsStr);
      const ok = await login(username, password);
      return ok;
    } catch {
      return false;
    }
  }, [check, login]);

  return { login, loginWithToken, logout, check, tryRestore, loading, error };
}
