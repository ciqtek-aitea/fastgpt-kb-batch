import { useState, useEffect } from 'react';

interface FileProgress {
  name: string;
  sent: number;
  total: number;
  percent: number;
}

interface UploadState {
  phase: string;
  current: number;
  total: number;
  percent: number;
  message: string;
  fileStatuses: { file: string; status: 'uploading' | 'done' | 'error'; percent?: number; error?: string }[];
  fileProgress: FileProgress | null;
  summary: { success: number; failed: number } | null;
}

export function useUploadProgress(taskId: string | null) {
  const [state, setState] = useState<UploadState>({
    phase: '',
    current: 0,
    total: 0,
    percent: 0,
    message: '',
    fileStatuses: [],
    fileProgress: null,
    summary: null,
  });

  useEffect(() => {
    if (!taskId) return;

    // 先从后端加载最新状态（用于恢复任务时）
    fetch(`/api/upload/status/${taskId}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.code === 200 && res.data) {
          const d = res.data;
          const total = d.total || 0;
          const current = d.current || 0;
          setState((prev) => ({
            ...prev,
            phase: d.phase || '',
            current,
            total,
            percent: total > 0 ? Math.round((current / total) * 100) : 0,
            message: d.message || '',
            fileProgress: d.fileProgress || null,
          }));
        }
      })
      .catch(() => {});

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/upload/${taskId}`;
    console.log('[UploadProgress] Connecting to:', wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[UploadProgress] WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const phase = msg.phase || '';
        const current = msg.current || 0;
        const total = msg.total || 0;
        const message = msg.message || '';
        const fileProgress: FileProgress | null = msg.fileProgress || null;

        setState((prev) => {
          const newStatuses = [...prev.fileStatuses];

          if (phase === 'uploading') {
            if (fileProgress) {
              // 单文件进度更新：更新对应文件的 percent
              const existing = newStatuses.find(s => s.file === fileProgress.name);
              if (existing) {
                existing.percent = fileProgress.percent;
                if (fileProgress.percent === 100 && existing.status === 'uploading') {
                  existing.status = 'done';
                }
              }
            } else if (message) {
              // 文件完成/失败消息
              const lastUploading = newStatuses.findIndex(s => s.status === 'uploading');
              if (lastUploading >= 0) {
                newStatuses[lastUploading] = { ...newStatuses[lastUploading], status: 'done', percent: 100 };
              }

              const successMatch = message.match(/已上传\s+\d+\/\d+:\s+(.+)/);
              const failMatch = message.match(/上传失败\s+(.+?):\s+(.+)/);

              if (successMatch) {
                newStatuses.push({ file: successMatch[1], status: 'done', percent: 100 });
              } else if (failMatch) {
                newStatuses.push({ file: failMatch[1], status: 'error', error: failMatch[2] });
              }
            }
          }

          // 整体进度（current 可能是浮点数）
          const percent = total > 0 ? Math.round((current / total) * 100) : 0;

          // 上传完成时
          let summary = prev.summary;
          if (phase === 'done') {
            const lastUploading = newStatuses.findIndex(s => s.status === 'uploading');
            if (lastUploading >= 0) {
              newStatuses[lastUploading] = { ...newStatuses[lastUploading], status: 'done', percent: 100 };
            }
            const failMatch = message.match(/失败\s+(\d+)/);
            const failed = failMatch ? parseInt(failMatch[1]) : 0;
            const success = Math.round(current) - failed;
            summary = { success, failed };
          }

          return {
            phase,
            current,
            total,
            percent,
            message,
            fileStatuses: newStatuses,
            fileProgress: fileProgress ?? prev.fileProgress,
            summary: summary ?? prev.summary,
          };
        });
      } catch (e) {
        console.error('[UploadProgress] Parse error:', e);
      }
    };

    ws.onerror = (e) => {
      console.error('[UploadProgress] WebSocket error:', e);
    };

    ws.onclose = (e) => {
      console.log('[UploadProgress] WebSocket closed:', e.code, e.reason);
    };

    return () => {
      ws.close();
    };
  }, [taskId]);

  return state;
}
