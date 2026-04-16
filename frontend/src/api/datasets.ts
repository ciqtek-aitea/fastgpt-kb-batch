import api from './client';
import type { Dataset } from '../types';

export async function listDatasets(params?: { parentId?: string; type?: string; searchKey?: string }) {
  const resp = await api.get<{ data: Dataset[] }>('/datasets', { params });
  return resp.data.data;
}

export async function createDataset(data: { name: string; type?: string; parentId?: string; intro?: string }) {
  const resp = await api.post<{ data: string }>('/datasets', data);
  return resp.data.data;
}

export async function getDataset(id: string) {
  const resp = await api.get<{ data: Dataset }>(`/datasets/${id}`);
  return resp.data.data;
}

export async function updateDataset(id: string, data: { name?: string; intro?: string }) {
  await api.put(`/datasets/${id}`, data);
}

export async function deleteDataset(id: string) {
  await api.delete(`/datasets/${id}`);
}
