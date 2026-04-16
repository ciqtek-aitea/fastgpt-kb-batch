export interface Dataset {
  _id: string;
  name: string;
  type: 'folder' | 'dataset' | 'websiteDataset';
  intro?: string;
  permission?: { isOwner: boolean };
  vectorModel?: { model: string };
  agentModel?: { model: string };
}

export interface Collection {
  _id: string;
  name: string;
  type: 'folder' | 'virtual' | 'link';
  parentId?: string;
  dataAmount?: number;
  trainingAmount?: number;
}

export interface CollectionListResult {
  list: Collection[];
  total: number;
}

export interface UploadOptions {
  trainingType?: string;
  chunkSize?: number;
  autoIndexes?: boolean;
  indexPrefixTitle?: boolean;
  imageIndex?: boolean;
}

export interface BatchUploadRequest {
  localDir: string;
  parentId?: string;
  concurrency?: number;
  options?: UploadOptions;
}

export interface ScanResult {
  dirs: string[];
  files: { path: string; name: string; dir: string; size: number }[];
  totalSize: number;
}

export interface UploadProgress {
  type: 'phase' | 'file_start' | 'file_done' | 'file_error' | 'progress' | 'folder_created' | 'summary';
  phase?: string;
  message?: string;
  file?: string;
  index?: number;
  total?: number;
  success?: boolean;
  error?: string;
  current?: number;
  percent?: number;
  path?: string;
  id?: string;
  errors?: string[];
  elapsed?: number;
}
