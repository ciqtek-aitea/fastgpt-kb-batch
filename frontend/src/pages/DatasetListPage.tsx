import { useState, useEffect } from 'react';
import { Card, Empty, Spin, Row, Col, Breadcrumb, Input, Button, Tag } from 'antd';
import {
  BookOutlined,
  FolderOutlined,
  SearchOutlined,
  LogoutOutlined,
  CloudUploadOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { listDatasets } from '../api/datasets';
import { useAuth } from '../hooks/useAuth';
import type { Dataset } from '../types';

export default function DatasetListPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [folderPath, setFolderPath] = useState<{ id: string; name: string }[]>([]);
  const currentParentId = searchParams.get('parentId') || undefined;

  const fetchDatasets = async (parentId?: string) => {
    setLoading(true);
    try {
      const data = await listDatasets({ parentId });
      if (!parentId) {
        const folders = data.filter((d) => d.type === 'folder');
        const childrenResults = await Promise.all(
          folders.map((f) => listDatasets({ parentId: f._id }).catch(() => []))
        );
        const inFolderIds = new Set(childrenResults.flat().map((d) => d._id));
        const looseDatasets = data.filter((d) => d.type !== 'folder' && !inFolderIds.has(d._id));
        setDatasets([...folders, ...looseDatasets]);
      } else {
        setDatasets(data);
      }
    } catch {
      setDatasets([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets(currentParentId);
  }, [currentParentId]);

  const handleItemClick = (ds: Dataset) => {
    if (ds.type === 'folder') {
      setFolderPath((prev) => [...prev, { id: ds._id, name: ds.name }]);
      setSearchParams({ parentId: ds._id });
    } else {
      navigate(`/dataset/${ds._id}`);
    }
  };

  const handleBreadcrumbClick = (index: number) => {
    if (index === -1) {
      setFolderPath([]);
      setSearchParams({});
    } else {
      const newPath = folderPath.slice(0, index + 1);
      setFolderPath(newPath);
      setSearchParams({ parentId: newPath[index].id });
    }
  };

  const filtered = search
    ? datasets.filter((d) => d.name.toLowerCase().includes(search.toLowerCase()))
    : datasets;

  const getIcon = (ds: Dataset) => {
    if (ds.type === 'folder') {
      return <FolderOutlined style={{ fontSize: 24, color: '#faad14' }} />;
    }
    return <BookOutlined style={{ fontSize: 24, color: '#1677ff' }} />;
  };

  // 获取活跃上传任务
  const getActiveUploads = (): Record<string, string> => {
    try {
      return JSON.parse(localStorage.getItem('active_uploads') || '{}');
    } catch {
      return {};
    }
  };

  if (loading) return <Spin size="large" style={{ display: 'block', marginTop: 100 }} />;

  const activeUploads = getActiveUploads();

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Breadcrumb
          items={[
            { title: <a onClick={() => handleBreadcrumbClick(-1)}>知识库</a> },
            ...folderPath.map((f, i) => ({
              title: i === folderPath.length - 1 ? f.name : <a onClick={() => handleBreadcrumbClick(i)}>{f.name}</a>,
            })),
          ]}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Input
          prefix={<SearchOutlined />}
          placeholder="搜索"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 200 }}
          allowClear
        />
        <Button icon={<UnorderedListOutlined />} onClick={() => navigate('/tasks')}>进度中心</Button>
        <Button icon={<LogoutOutlined />} onClick={logout}>退出</Button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <Empty description="暂无内容" />
      ) : (
        <Row gutter={[16, 16]}>
          {filtered.map((ds) => (
            <Col key={ds._id} xs={24} sm={12} md={8} lg={6}>
              <Card
                hoverable
                onClick={() => handleItemClick(ds)}
                style={activeUploads[ds._id] ? { borderColor: '#1677ff', borderWidth: 2 } : undefined}
              >
                <Card.Meta
                  avatar={getIcon(ds)}
                  title={
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {ds.name}
                      {activeUploads[ds._id] && (
                        <Tag color="blue" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
                          <CloudUploadOutlined /> 上传中
                        </Tag>
                      )}
                    </span>
                  }
                  description={ds.intro || (ds.type === 'folder' ? '文件夹' : ds.vectorModel?.model)}
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}
