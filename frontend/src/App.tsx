import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Spin } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useState, useEffect } from 'react';
import LoginPage from './pages/LoginPage';
import DatasetListPage from './pages/DatasetListPage';
import DatasetDetailPage from './pages/DatasetDetailPage';
import TaskProgressPage from './pages/TaskProgressPage';
import { useAuth } from './hooks/useAuth';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { tryRestore } = useAuth();
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    const hasSession = localStorage.getItem('session_token');
    const hasCreds = localStorage.getItem('login_creds');
    if (!hasSession && !hasCreds) {
      setChecking(false);
      return;
    }
    tryRestore().then((ok) => {
      setAuthenticated(ok);
      setChecking(false);
    });
  }, []);

  if (checking) {
    return <Spin size="large" style={{ display: 'block', marginTop: '40vh' }} />;
  }
  if (!authenticated) return <Navigate to="/login" />;
  return <>{children}</>;
}

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<PrivateRoute><DatasetListPage /></PrivateRoute>} />
          <Route path="/tasks" element={<PrivateRoute><TaskProgressPage /></PrivateRoute>} />
          <Route path="/dataset/:id" element={<PrivateRoute><DatasetDetailPage /></PrivateRoute>} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
