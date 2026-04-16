import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography, Button, Tag, Progress, Card, Empty, Spin,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';

const { Title } = Typography;

interface TaskInfo {
  taskId: string;
  datasetId: string;
  phase: string;
  current: number;
  total: number;
  message: string;
  fileProgress?: { name: string; sent: number; total: number; percent: number };
}

export default function TaskProgressPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const wsRefs = useRef<Record<string, WebSocket>>({});
  const [liveStatus, setLiveStatus] = useState<Record<string, TaskInfo>>({});

  // 加载任务列表
  useEffect(() => {
    fetch('/api/upload/tasks')
      .then((r) => r.json())
      .then((res) => {
        if (res.code === 200) {
          setTasks(res.data);
          const map: Record<string, TaskInfo> = {};
          for (const t of res.data) map[t.taskId] = t;
          setLiveStatus(map);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // 为进行中的任务建立 WebSocket 连接
  useEffect(() => {
    const activeTasks = tasks.filter((t) => t.phase && t.phase !== 'done');

    for (const task of activeTasks) {
      const tid = task.taskId;
      if (wsRefs.current[tid]) continue;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/upload/${tid}`);
      wsRefs.current[tid] = ws;

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          setLiveStatus((prev) => ({
            ...prev,
            [tid]: {
              taskId: tid,
              datasetId: prev[tid]?.datasetId || '',
              phase: msg.phase || '',
              current: msg.current || 0,
              total: msg.total || 0,
              message: msg.message || '',
              fileProgress: msg.fileProgress,
            },
          }));
        } catch { /* ignore */ }
      };
    }
  }, [tasks]);

  const mergedTasks = tasks.map((t) => liveStatus[t.taskId] || t);

  if (loading) return <Spin size="large" style={{ display: 'block', marginTop: 100 }} />;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} style={{ marginBottom: 16 }}>
        返回
      </Button>
      <Title level={3} style={{ marginTop: 0 }}>任务进度中心</Title>

      {mergedTasks.length === 0 ? (
        <Empty description="暂无上传任务" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {mergedTasks.map((task) => {
            const isDone = task.phase === 'done';
            const percent = task.total > 0 ? Math.round((task.current / task.total) * 100) : 0;
            const failMatch = task.message?.match(/失败\s+(\d+)/);
            const failed = failMatch ? parseInt(failMatch[1]) : 0;
            const success = Math.round(task.current) - failed;

            return (
              <Card
                key={task.taskId}
                size="small"
                hoverable
                onClick={() => navigate(`/dataset/${task.datasetId}`)}
                style={{ borderColor: isDone ? undefined : '#1677ff', borderWidth: isDone ? 1 : 2 }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Tag color={isDone ? (failed ? 'orange' : 'green') : 'blue'}>
                      {isDone ? '完成' : '上传中'}
                    </Tag>
                    <span style={{ fontSize: 13, color: '#666' }}>
                      {task.message || task.phase}
                    </span>
                  </div>
                  <span style={{ fontSize: 11, color: '#999', fontFamily: 'monospace' }}>
                    {task.taskId.slice(0, 8)}
                  </span>
                </div>

                <Progress
                  percent={percent}
                  status={isDone ? (failed ? 'exception' : 'success') : 'active'}
                  size="small"
                />

                {task.fileProgress && !isDone && (
                  <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                    当前文件: {task.fileProgress.name} ({task.fileProgress.percent}%)
                  </div>
                )}

                {isDone && (
                  <div style={{ marginTop: 4, display: 'flex', gap: 4 }}>
                    <Tag color="green" style={{ fontSize: 11 }}>成功: {success}</Tag>
                    {failed > 0 && <Tag color="red" style={{ fontSize: 11 }}>失败: {failed}</Tag>}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
