import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography, Spin, message, Card, Button, Progress, Tag, Alert, Modal,
  Breadcrumb as AntBreadcrumb, Checkbox, Input,
} from 'antd';
import {
  UploadOutlined, ArrowLeftOutlined, FolderOpenOutlined,
  DeleteOutlined, RightOutlined, FileOutlined,
} from '@ant-design/icons';
import { getDataset } from '../api/datasets';
import { browseDirectory, startBatchUpload } from '../api/collections';
import type { BrowseResult } from '../api/collections';
import { useUploadProgress } from '../hooks/useUploadProgress';
import type { Dataset } from '../types';

interface SelectedItem {
  type: 'dir' | 'file';
  path: string;
  name: string;
  extra?: string;
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [loading, setLoading] = useState(true);

  // 已选
  const [selectedItems, setSelectedItems] = useState<SelectedItem[]>([]);

  // 浏览器
  const [browserOpen, setBrowserOpen] = useState(false);
  const [browserPath, setBrowserPath] = useState('~');
  const [browserData, setBrowserData] = useState<BrowseResult | null>(null);
  const [browserLoading, setBrowserLoading] = useState(false);
  const [checkedPaths, setCheckedPaths] = useState<Set<string>>(new Set());

  // 上传
  const [taskId, setTaskId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const uploadState = useUploadProgress(taskId);

  useEffect(() => {
    if (!id) return;
    getDataset(id)
      .then(setDataset)
      .catch(() => message.error('加载知识库失败'))
      .finally(() => setLoading(false));
  }, [id]);

  const loadBrowser = async (path: string) => {
    setBrowserLoading(true);
    try {
      const data = await browseDirectory(path);
      setBrowserData(data);
      setBrowserPath(data.path);
    } catch {
      message.error('无法访问该目录');
    } finally {
      setBrowserLoading(false);
    }
  };

  const openBrowser = () => {
    setBrowserOpen(true);
    loadBrowser('~');
  };

  const toggleCheck = (path: string) => {
    setCheckedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path); else next.add(path);
      return next;
    });
  };

  const confirmSelection = () => {
    const newItems: SelectedItem[] = [];
    for (const dir of browserData?.directories || []) {
      if (checkedPaths.has(dir.path) && !selectedItems.some((s) => s.path === dir.path)) {
        newItems.push({ type: 'dir', path: dir.path, name: dir.name, extra: `${dir.itemCount} 项` });
      }
    }
    for (const file of browserData?.files || []) {
      if (checkedPaths.has(file.path) && !selectedItems.some((s) => s.path === file.path)) {
        newItems.push({ type: 'file', path: file.path, name: file.name, extra: formatSize(file.size) });
      }
    }
    const merged = [...selectedItems, ...newItems];
    setSelectedItems(merged);
    setBrowserOpen(false);
    setCheckedPaths(new Set());
  };

  const handleRemove = (path: string) => {
    setSelectedItems((prev) => prev.filter((s) => s.path !== path));
  };

  const handleUpload = async () => {
    if (!id || selectedItems.length === 0) return;
    setUploading(true);

    // 先调后端获取 taskId
    try {
      const result = await startBatchUpload(
        id,
        selectedItems.filter((s) => s.type === 'dir').map((s) => s.path),
        selectedItems.filter((s) => s.type === 'file').map((s) => s.path),
      );
      // 设置 taskId 触发 WebSocket 连接，后端会等 1 秒再开始
      setTaskId(result.taskId);
    } catch (e: any) {
      message.error(e.response?.data?.message || '启动上传失败');
      setUploading(false);
    }
  };

  const isUploading = uploading && taskId;
  const isDone = uploadState.phase === 'done';

  if (loading) return <Spin size="large" style={{ display: 'block', marginTop: 100 }} />;
  if (!dataset) return <div>知识库不存在</div>;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} style={{ marginBottom: 16 }}>
        返回
      </Button>
      <Typography.Title level={3} style={{ marginTop: 0 }}>{dataset.name}</Typography.Title>
      {dataset.intro && <Typography.Paragraph type="secondary">{dataset.intro}</Typography.Paragraph>}

      {/* 已选内容 */}
      <Card
        title={<span><FolderOpenOutlined /> 选择上传内容</span>}
        style={{ marginBottom: 16 }}
        extra={
          selectedItems.length > 0 && !isUploading ? (
            <Button size="small" danger onClick={() => setSelectedItems([])}>清空</Button>
          ) : null
        }
      >
        <Button icon={<FolderOpenOutlined />} onClick={openBrowser} disabled={!!isUploading} block>
          浏览文件（支持多选目录和文件）
        </Button>

        {selectedItems.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {selectedItems.map((s) => (
              <div
                key={s.path}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  background: '#fafafa', border: '1px solid #f0f0f0',
                  borderRadius: 6, padding: '6px 12px', marginBottom: 4, fontSize: 13,
                }}
              >
                <span>
                  {s.type === 'dir'
                    ? <FolderOpenOutlined style={{ color: '#faad14', marginRight: 8 }} />
                    : <FileOutlined style={{ color: '#1677ff', marginRight: 8 }} />}
                  <b>{s.name}</b>
                  <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>{s.extra}</span>
                </span>
                {!isUploading && (
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => handleRemove(s.path)} />
                )}
              </div>
            ))}
            {selectedItems.length > 0 && (
              <Alert
                style={{ marginTop: 8 }}
                type="info"
                showIcon={false}
                message={`已选 ${selectedItems.filter((s) => s.type === 'dir').length} 个目录, ${selectedItems.filter((s) => s.type === 'file').length} 个文件`}
              />
            )}
          </div>
        )}
      </Card>

      {/* 上传 */}
      <Button
        type="primary"
        icon={<UploadOutlined />}
        size="large"
        block
        onClick={handleUpload}
        loading={uploading && !taskId}
        disabled={selectedItems.length === 0 || !!isUploading}
      >
        开始上传
      </Button>

      {/* 进度 */}
      {isUploading && (
        <Card style={{ marginTop: 16 }} size="small">
          <div style={{ marginBottom: 8 }}>
            <Tag color={isDone ? (uploadState.summary?.failed ? 'orange' : 'green') : 'blue'}>
              {isDone ? '完成' : '上传中'}
            </Tag>
            {uploadState.message && <span style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>{uploadState.message}</span>}
          </div>
          <Progress
            percent={uploadState.percent}
            status={isDone ? (uploadState.summary?.failed ? 'exception' : 'success') : 'active'}
          />
          {/* 单文件进度 */}
          {uploadState.fileProgress && !isDone && (
            <div style={{ marginTop: 4, fontSize: 12, color: '#888' }}>
              <Progress
                size="small"
                percent={uploadState.fileProgress.percent}
                format={() => `${uploadState.fileProgress!.percent}%`}
                style={{ marginBottom: 0 }}
              />
            </div>
          )}
          {uploadState.fileStatuses.length > 0 && (
            <div style={{ maxHeight: 200, overflow: 'auto', fontSize: 12, marginTop: 8 }}>
              {uploadState.fileStatuses.map((f, i) => (
                <div key={i} style={{ padding: '2px 0', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Tag color={f.status === 'done' ? 'green' : f.status === 'error' ? 'red' : 'processing'} style={{ fontSize: 11, flexShrink: 0 }}>
                    {f.status === 'done' ? '成功' : f.status === 'error' ? '失败' : `${f.percent ?? 0}%`}
                  </Tag>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.file}</span>
                  {f.error && <span style={{ color: 'red', flexShrink: 0 }}>{f.error}</span>}
                </div>
              ))}
            </div>
          )}
          {uploadState.summary && (
            <div style={{ marginTop: 8 }}>
              <Tag color="green">成功: {uploadState.summary.success}</Tag>
              {uploadState.summary.failed > 0 && <Tag color="red">失败: {uploadState.summary.failed}</Tag>}
            </div>
          )}
          {isDone && (
            <Button
              style={{ marginTop: 12 }}
              block
              onClick={() => { setUploading(false); setTaskId(null); setSelectedItems([]); }}
            >
              重新上传
            </Button>
          )}
        </Card>
      )}

      {/* 目录浏览器弹窗 */}
      <Modal
        title="浏览文件"
        open={browserOpen}
        onCancel={() => { setBrowserOpen(false); setCheckedPaths(new Set()); }}
        onOk={confirmSelection}
        okText={`确认选择 (${checkedPaths.size})`}
        width={600}
      >
        <Input
          value={browserPath}
          onChange={(e) => setBrowserPath(e.target.value)}
          onPressEnter={() => loadBrowser(browserPath)}
          addonAfter={<Button size="small" type="link" onClick={() => loadBrowser(browserPath)}>前往</Button>}
          style={{ marginBottom: 12 }}
        />

        {browserData && (
          <AntBreadcrumb
            style={{ marginBottom: 12 }}
            items={[
              ...(browserData.path === '/' ? [] : [{ title: <a onClick={() => loadBrowser('/')}>/</a> }]),
              ...browserData.path.split('/').filter(Boolean).map((part, i, arr) => {
                const fullPath = '/' + arr.slice(0, i + 1).join('/');
                return { title: i === arr.length - 1 ? part : <a onClick={() => loadBrowser(fullPath)}>{part}</a> };
              }),
            ]}
          />
        )}

        {browserData?.parent && (
          <div
            style={{ padding: '6px 12px', cursor: 'pointer', borderBottom: '1px solid #f0f0f0', color: '#666', fontSize: 13 }}
            onClick={() => loadBrowser(browserData.parent!)}
          >
            <ArrowLeftOutlined style={{ marginRight: 8 }} />返回上级
          </div>
        )}

        <div style={{ maxHeight: 380, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 4 }}>
          {browserLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
          ) : (
            <>
              {/* 文件夹 */}
              {(browserData?.directories || []).map((dir) => (
                <div
                  key={dir.path}
                  style={{
                    display: 'flex', alignItems: 'center', padding: '6px 12px',
                    borderBottom: '1px solid #f5f5f5', fontSize: 13,
                    background: checkedPaths.has(dir.path) ? '#e6f4ff' : undefined,
                  }}
                >
                  <Checkbox
                    checked={checkedPaths.has(dir.path)}
                    onChange={() => toggleCheck(dir.path)}
                    style={{ marginRight: 8 }}
                  />
                  <FolderOpenOutlined style={{ color: '#faad14', marginRight: 8 }} />
                  <span style={{ flex: 1 }}>{dir.name}</span>
                  <span style={{ color: '#999', fontSize: 12, marginRight: 8 }}>{dir.itemCount} 项</span>
                  <Button type="text" size="small" icon={<RightOutlined />} onClick={() => loadBrowser(dir.path)} />
                </div>
              ))}
              {/* 文件 */}
              {(browserData?.files || []).map((file) => (
                <div
                  key={file.path}
                  style={{
                    display: 'flex', alignItems: 'center', padding: '6px 12px',
                    borderBottom: '1px solid #f5f5f5', fontSize: 13,
                    background: checkedPaths.has(file.path) ? '#e6f4ff' : undefined,
                  }}
                >
                  <Checkbox
                    checked={checkedPaths.has(file.path)}
                    onChange={() => toggleCheck(file.path)}
                    style={{ marginRight: 8 }}
                  />
                  <FileOutlined style={{ color: '#1677ff', marginRight: 8 }} />
                  <span style={{ flex: 1 }}>{file.name}</span>
                  <span style={{ color: '#999', fontSize: 12 }}>{formatSize(file.size)}</span>
                </div>
              ))}
            </>
          )}
        </div>

        {checkedPaths.size > 0 && (
          <Alert style={{ marginTop: 8 }} type="info" showIcon={false} message={`已勾选 ${checkedPaths.size} 项`} />
        )}
      </Modal>
    </div>
  );
}
