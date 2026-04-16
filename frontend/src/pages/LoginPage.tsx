import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Tabs, Form, Input, Button, message } from 'antd';
import { UserOutlined, LockOutlined, KeyOutlined } from '@ant-design/icons';
import { useAuth } from '../hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loginWithToken, loading, error } = useAuth();
  const [tokenInput, setTokenInput] = useState('');

  const handlePasswordLogin = async (values: { username: string; password: string }) => {
    const ok = await login(values.username, values.password);
    if (ok) navigate('/');
    else message.error('登录失败');
  };

  const handleTokenLogin = async () => {
    if (!tokenInput.trim()) return;
    const ok = await loginWithToken(tokenInput.trim());
    if (ok) navigate('/');
    else message.error('Token 无效');
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card title="FastGPT 知识库管理" style={{ width: 400 }}>
        <Tabs
          items={[
            {
              key: 'password',
              label: '账号密码',
              children: (
                <Form onFinish={handlePasswordLogin} layout="vertical">
                  <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading} block>
                      登录
                    </Button>
                  </Form.Item>
                  {error && <div style={{ color: 'red', textAlign: 'center' }}>{error}</div>}
                </Form>
              ),
            },
            {
              key: 'token',
              label: '手动 Token',
              children: (
                <div>
                  <Input.TextArea
                    rows={3}
                    placeholder="粘贴 fastgpt_token"
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    prefix={<KeyOutlined />}
                  />
                  <Button
                    type="primary"
                    onClick={handleTokenLogin}
                    loading={loading}
                    style={{ marginTop: 16, width: '100%' }}
                  >
                    验证并登录
                  </Button>
                  {error && <div style={{ color: 'red', marginTop: 8, textAlign: 'center' }}>{error}</div>}
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
