"""知识库集合相关 Pydantic 模型"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CollectionFolderCreate(BaseModel):
    name: str
    parentId: Optional[str] = None


class UploadOptions(BaseModel):
    trainingType: Optional[str] = "chunk"
    chunkSize: Optional[int] = 512
    autoIndexes: Optional[bool] = None
    indexPrefixTitle: Optional[bool] = None
    imageIndex: Optional[bool] = None


class BatchUploadRequest(BaseModel):
    datasetId: str
    localDir: str
    parentId: Optional[str] = None
    concurrency: Optional[int] = None
    options: Optional[UploadOptions] = None
