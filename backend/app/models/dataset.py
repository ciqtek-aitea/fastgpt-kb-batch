"""数据集相关 Pydantic 模型"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DatasetCreate(BaseModel):
    name: str
    type: Optional[str] = None
    parentId: Optional[str] = None
    intro: Optional[str] = None


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    intro: Optional[str] = None
    chunkSettings: Optional[dict] = None
