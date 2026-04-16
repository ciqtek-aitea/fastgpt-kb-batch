"""数据集路由"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_token
from app.models.dataset import DatasetCreate, DatasetUpdate
from app.services import fastgpt_service

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("")
async def list_datasets(
    token: str = Depends(get_current_token),
    parentId: str | None = None,
    type: str | None = None,
    searchKey: str | None = None,
):
    """获取数据集列表"""
    data = await fastgpt_service.list_datasets(
        token, parent_id=parentId, type_=type, search_key=searchKey
    )
    return {"code": 200, "data": data}


@router.post("")
async def create_dataset(
    req: DatasetCreate,
    token: str = Depends(get_current_token),
):
    """创建数据集"""
    dataset_id = await fastgpt_service.create_dataset(
        token,
        name=req.name,
        type_=req.type,
        parent_id=req.parentId,
        intro=req.intro,
    )
    return {"code": 200, "data": dataset_id}


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    token: str = Depends(get_current_token),
):
    """获取数据集详情"""
    data = await fastgpt_service.get_dataset(token, dataset_id)
    return {"code": 200, "data": data}


@router.put("/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    req: DatasetUpdate,
    token: str = Depends(get_current_token),
):
    """更新数据集"""
    await fastgpt_service.update_dataset(
        token,
        dataset_id=dataset_id,
        name=req.name,
        intro=req.intro,
        chunk_settings=req.chunkSettings,
    )
    return {"code": 200, "message": "更新成功"}


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    token: str = Depends(get_current_token),
):
    """删除数据集"""
    await fastgpt_service.delete_dataset(token, dataset_id)
    return {"code": 200, "message": "删除成功"}
