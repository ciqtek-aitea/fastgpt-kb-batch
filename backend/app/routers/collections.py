"""知识库集合路由"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.dependencies import get_current_token
from app.models.collection import CollectionFolderCreate, UploadOptions
from app.services import fastgpt_service

router = APIRouter(prefix="/datasets", tags=["collections"])


@router.get("/{dataset_id}/collections")
async def list_collections(
    dataset_id: str,
    token: str = Depends(get_current_token),
    parentId: str | None = Query(default=None),
    pageNum: int = Query(default=1),
    pageSize: int = Query(default=20),
    searchText: str | None = Query(default=None),
):
    """获取集合列表"""
    data = await fastgpt_service.list_collections(
        token,
        dataset_id=dataset_id,
        parent_id=parentId,
        page=pageNum,
        page_size=pageSize,
        search=searchText,
    )
    return {"code": 200, "data": data}


@router.post("/{dataset_id}/collections/folder")
async def create_folder(
    dataset_id: str,
    req: CollectionFolderCreate,
    token: str = Depends(get_current_token),
):
    """创建文件夹"""
    collection_id = await fastgpt_service.create_folder(
        token,
        dataset_id=dataset_id,
        name=req.name,
        parent_id=req.parentId,
    )
    return {"code": 200, "data": collection_id}


@router.put("/{dataset_id}/collections/{collection_id}")
async def rename_collection(
    dataset_id: str,
    collection_id: str,
    name: str = Form(...),
    token: str = Depends(get_current_token),
):
    """重命名集合"""
    await fastgpt_service.rename_collection(token, collection_id, name)
    return {"code": 200, "message": "重命名成功"}


@router.delete("/{dataset_id}/collections")
async def delete_collections(
    dataset_id: str,
    collectionIds: list[str] = Query(...),
    token: str = Depends(get_current_token),
):
    """批量删除集合"""
    await fastgpt_service.delete_collections(token, collectionIds)
    return {"code": 200, "message": "删除成功"}


@router.post("/{dataset_id}/collections/upload")
async def upload_file(
    dataset_id: str,
    token: str = Depends(get_current_token),
    file: UploadFile = File(...),
    parentId: Optional[str] = Form(default=None),
    trainingType: str = Form(default="chunk"),
    chunkSize: int = Form(default=512),
    autoIndexes: Optional[str] = Form(default=None),
    indexPrefixTitle: Optional[str] = Form(default=None),
    imageIndex: Optional[str] = Form(default=None),
):
    """单文件上传"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    file_bytes = await file.read()

    # 解析 autoIndexes（逗号分隔的字符串）
    parsed_auto_indexes = None
    if autoIndexes:
        parsed_auto_indexes = [x.strip() for x in autoIndexes.split(",") if x.strip()]

    collection_id = await fastgpt_service.upload_file(
        token=token,
        file_bytes=file_bytes,
        filename=file.filename,
        dataset_id=dataset_id,
        parent_id=parentId,
        training_type=trainingType,
        chunk_size=chunkSize,
        auto_indexes=parsed_auto_indexes,
        index_prefix_title=indexPrefixTitle.lower() == "true" if indexPrefixTitle else None,
        image_index=imageIndex.lower() == "true" if imageIndex else None,
    )

    return {"code": 200, "data": {"collectionId": collection_id}}


@router.post("/{dataset_id}/collections/{collection_id}/retrain")
async def retrain_collection(
    dataset_id: str,
    collection_id: str,
    autoIndexes: list[str] | None = None,
    token: str = Depends(get_current_token),
):
    """重新训练集合"""
    await fastgpt_service.retrain_collection(
        token,
        dataset_id=dataset_id,
        collection_id=collection_id,
        auto_indexes=autoIndexes,
    )
    return {"code": 200, "message": "重新训练已启动"}
