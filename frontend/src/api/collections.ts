import api from './client';

export interface BrowseResult {
  path: string;
  parent: string | null;
  directories: { name: string; path: string; itemCount: number }[];
  files: { name: string; path: string; size: number }[];
}

export interface UploadPreview {
  totalFiles: number;
  totalSize: number;
}

/** 浏览本地目录 */
export async function browseDirectory(path: string): Promise<BrowseResult> {
  const resp = await api.get<{ code: number; data: BrowseResult }>('/fs/browse', { params: { path } });
  return resp.data.data;
}

/** 预览上传文件 */
export async function previewUpload(
  datasetId: string,
  directories: string[],
  files: string[],
): Promise<UploadPreview> {
  const resp = await api.post<{ code: number; data: UploadPreview }>('/upload/preview', {
    datasetId, directories, files,
  });
  return resp.data.data;
}

/** 启动批量上传 */
export async function startBatchUpload(
  datasetId: string,
  directories: string[],
  files: string[],
) {
  const resp = await api.post('/upload/start', { datasetId, directories, files });
  return resp.data.data;
}
