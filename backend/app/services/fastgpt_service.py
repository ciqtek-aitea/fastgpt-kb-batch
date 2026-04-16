"""FastGPT API 服务层 — 所有与 FastGPT 后端的交互都通过此模块"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.parse

import httpx

from app.config import API_BASE

# ---------------------------------------------------------------------------
# 通用请求工具
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_RETRY_DELAY = 2  # 秒


def _headers(token: str) -> dict:
    return {"Cookie": f"fastgpt_token={token}"}


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    token: str | None = None,
    **kwargs,
) -> dict:
    """带重试的统一请求函数"""
    headers = kwargs.pop("headers", {})
    if token:
        headers.update(_headers(token))

    last_exc: Exception | None = None
    for _ in range(_MAX_RETRIES):
        try:
            resp = await client.request(method, url, headers=headers, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_exc = exc
            import asyncio

            await asyncio.sleep(_RETRY_DELAY)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------


async def login_password(username: str, password: str) -> str:
    """使用账号密码登录，返回 fastgpt_token"""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        # 1. preLogin
        pre_resp = await _request_with_retry(
            client,
            "GET",
            "/support/user/account/preLogin",
            params={"username": username},
        )
        if pre_resp.get("code") != 200:
            raise Exception(f"preLogin 失败: {pre_resp}")
        code = pre_resp["data"]["code"]

        # 2. sha256(明文密码)
        hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()

        # 3. loginByPassword
        login_resp = await _request_with_retry(
            client,
            "POST",
            "/support/user/account/loginByPassword",
            json={"username": username, "password": hashed, "code": code},
        )
        if login_resp.get("code") != 200:
            raise Exception(f"loginByPassword 失败: {login_resp}")

        # 从响应头提取 token
        # httpx 不直接暴露 Set-Cookie，需要从 raw headers 读取
        set_cookie = login_resp.get("set-cookie", "") or ""
        # 实际上 httpx 会把 set-cookie 放到 resp.headers 的 set-cookie 中
        # 但 _request_with_retry 返回的是 json，我们重新发一次请求拿 header
        # 更好的方式：直接使用底层 client 拿响应头
        pass

    # 重新请求以获取 Set-Cookie header
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client2:
        pre_resp2 = await client2.get(
            "/support/user/account/preLogin", params={"username": username}
        )
        pre_data2 = pre_resp2.json()
        code2 = pre_data2["data"]["code"]
        hashed2 = hashlib.sha256(password.encode("utf-8")).hexdigest()
        login_resp2 = await client2.post(
            "/support/user/account/loginByPassword",
            json={"username": username, "password": hashed2, "code": code2},
        )
        login_resp2.raise_for_status()

        # 从响应头中提取 fastgpt_token
        token = None
        # httpx 把 set-cookie 放在响应头中
        for cookie_header in login_resp2.headers.get_list("set-cookie"):
            if "fastgpt_token=" in cookie_header:
                token = cookie_header.split("fastgpt_token=")[1].split(";")[0]
                break

        if not token:
            raise Exception("登录成功但未获取到 fastgpt_token")

    return token


async def validate_token(token: str) -> bool:
    """验证 token 是否有效"""
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            resp = await _request_with_retry(
                client,
                "GET",
                "/support/user/team/plan/getTeamPlanStatus",
                params={"maxQuantity": "1"},
                token=token,
            )
            return resp.get("code") == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 数据集 (Dataset)
# ---------------------------------------------------------------------------


async def list_datasets(
    token: str,
    parent_id: str | None = None,
    type_: str | None = None,
    search_key: str | None = None,
) -> list[dict]:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        body: dict = {}
        if parent_id:
            body["parentId"] = parent_id
        if type_:
            body["type"] = type_
        if search_key:
            body["searchKey"] = search_key
        resp = await _request_with_retry(
            client, "POST", "/core/dataset/list", json=body, token=token
        )
        if resp.get("code") != 200:
            raise Exception(f"获取数据集列表失败: {resp}")
        return resp.get("data", [])


async def create_dataset(
    token: str,
    name: str,
    type_: str | None = None,
    parent_id: str | None = None,
    intro: str | None = None,
) -> str:
    """创建数据集，返回 dataset_id"""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        body: dict = {"name": name}
        if type_:
            body["type"] = type_
        if parent_id:
            body["parentId"] = parent_id
        if intro:
            body["intro"] = intro
        resp = await _request_with_retry(
            client, "POST", "/core/dataset/create", json=body, token=token
        )
        if resp.get("code") != 200:
            raise Exception(f"创建数据集失败: {resp}")
        return resp.get("data", "")


async def get_dataset(token: str, dataset_id: str) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        resp = await _request_with_retry(
            client,
            "GET",
            "/core/dataset/detail",
            params={"id": dataset_id},
            token=token,
        )
        if resp.get("code") != 200:
            raise Exception(f"获取数据集详情失败: {resp}")
        return resp.get("data", {})


async def update_dataset(
    token: str,
    dataset_id: str,
    name: str | None = None,
    intro: str | None = None,
    chunk_settings: dict | None = None,
) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        body: dict = {"id": dataset_id}
        if name is not None:
            body["name"] = name
        if intro is not None:
            body["intro"] = intro
        if chunk_settings is not None:
            body["chunkSettings"] = chunk_settings
        resp = await _request_with_retry(
            client, "POST", "/core/dataset/update", json=body, token=token
        )
        if resp.get("code") != 200:
            raise Exception(f"更新数据集失败: {resp}")


async def delete_dataset(token: str, dataset_id: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        resp = await _request_with_retry(
            client,
            "DELETE",
            "/core/dataset/delete",
            params={"id": dataset_id},
            token=token,
        )
        if resp.get("code") != 200:
            raise Exception(f"删除数据集失败: {resp}")


# ---------------------------------------------------------------------------
# 集合 (Collection)
# ---------------------------------------------------------------------------


async def list_collections(
    token: str,
    dataset_id: str,
    parent_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
) -> dict:
    """返回 {list: [...], total: int}"""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        body: dict = {
            "datasetId": dataset_id,
            "parentId": parent_id or "",
            "pageNum": page,
            "pageSize": page_size,
        }
        if search:
            body["searchText"] = search
        resp = await _request_with_retry(
            client,
            "POST",
            "/core/dataset/collection/listV2",
            json=body,
            token=token,
        )
        if resp.get("code") != 200:
            raise Exception(f"获取集合列表失败: {resp}")
        return resp.get("data", {"list": [], "total": 0})


async def create_folder(
    token: str,
    dataset_id: str,
    name: str,
    parent_id: str | None = None,
) -> str:
    """创建文件夹，返回 collection_id"""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        body: dict = {
            "datasetId": dataset_id,
            "name": name,
            "type": "folder",
        }
        if parent_id:
            body["parentId"] = parent_id
        resp = await _request_with_retry(
            client,
            "POST",
            "/core/dataset/collection/create",
            json=body,
            token=token,
        )
        if resp.get("code") != 200:
            raise Exception(f"创建文件夹失败: {resp}")
        return resp.get("data", "")


async def rename_collection(token: str, collection_id: str, name: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        resp = await _request_with_retry(
            client,
            "PUT",
            "/core/dataset/collection/update",
            json={"id": collection_id, "name": name},
            token=token,
        )
        if resp.get("code") != 200:
            raise Exception(f"重命名集合失败: {resp}")


async def delete_collections(token: str, collection_ids: list[str]) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        resp = await _request_with_retry(
            client,
            "POST",
            "/core/dataset/collection/delete",
            json={"collectionIds": collection_ids},
            token=token,
        )
        if resp.get("code") != 200:
            raise Exception(f"删除集合失败: {resp}")


async def retrain_collection(
    token: str,
    dataset_id: str,
    collection_id: str,
    auto_indexes: list[str] | None = None,
    **kwargs,
) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        body: dict = {
            "datasetId": dataset_id,
            "collectionId": collection_id,
        }
        if auto_indexes:
            body["autoIndexes"] = auto_indexes
        body.update(kwargs)
        resp = await _request_with_retry(
            client,
            "POST",
            "/core/dataset/collection/create/reTrainingCollection",
            json=body,
            token=token,
        )
        if resp.get("code") != 200:
            raise Exception(f"重新训练集合失败: {resp}")


# ---------------------------------------------------------------------------
# 文件上传 (multipart 手工构造)
# ---------------------------------------------------------------------------


async def upload_file(
    token: str,
    file_bytes: bytes,
    filename: str,
    dataset_id: str,
    parent_id: str | None = None,
    training_type: str = "chunk",
    chunk_size: int = 512,
    auto_indexes: list[str] | None = None,
    index_prefix_title: bool | None = None,
    image_index: bool | None = None,
) -> str:
    """上传文件到 FastGPT，返回 collection_id"""
    url = f"{API_BASE}/core/dataset/collection/create/localFile"

    # RFC 5987 编码文件名
    encoded_filename = urllib.parse.quote(filename, safe="")

    # 构建 data JSON
    data_obj: dict = {
        "datasetId": dataset_id,
        "trainingType": training_type,
        "chunkSize": chunk_size,
    }
    if parent_id:
        data_obj["parentId"] = parent_id
    if auto_indexes:
        data_obj["autoIndexes"] = auto_indexes
    if index_prefix_title is not None:
        data_obj["indexPrefixTitle"] = index_prefix_title
    if image_index is not None:
        data_obj["imageIndex"] = image_index

    data_json = json.dumps(data_obj, ensure_ascii=False)

    # 手工构造 multipart/form-data
    boundary = "----WebKitFormBoundary" + os.urandom(16).hex()

    parts: list[bytes] = []

    # file part
    parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8")
    )
    parts.append(file_bytes)
    parts.append(b"\r\n")

    # data part
    parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="data"\r\n'
        f"Content-Type: application/json\r\n\r\n".encode("utf-8")
    )
    parts.append(data_json.encode("utf-8"))
    parts.append(b"\r\n")

    # closing boundary
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)

    headers = {
        "Cookie": f"fastgpt_token={token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }

    last_exc: Exception | None = None
    for _ in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, content=body, headers=headers)
                resp.raise_for_status()
                result = resp.json()
                if result.get("code") != 200:
                    raise Exception(f"上传文件失败: {result}")
                return result.get("data", {}).get("collectionId", "")
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_exc = exc
            import asyncio

            await asyncio.sleep(_RETRY_DELAY)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# S3 直传上传（presigned URL） — 支持大文件，绕过 nginx body size 限制
# ---------------------------------------------------------------------------


async def _get_presigned_upload_url(token: str, filename: str, dataset_id: str) -> dict:
    """获取数据集 S3 预签名上传 URL

    返回: {url, key, headers, maxSize}
    """
    url = f"{API_BASE}/core/dataset/presignDatasetFilePostUrl"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            json={"filename": filename, "datasetId": dataset_id},
            headers=_headers(token),
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 200:
            raise Exception(f"获取上传 URL 失败: {result}")
        return result["data"]


async def _upload_to_s3(
    presigned_url: str,
    file_bytes: bytes,
    extra_headers: dict,
    file_progress_fn=None,
) -> None:
    """直接上传文件到 S3（使用预签名 URL，支持分块进度回调）"""
    total = len(file_bytes)
    chunk_size = 1024 * 1024  # 1MB 分块

    async def content_stream():
        for offset in range(0, total, chunk_size):
            chunk = file_bytes[offset:offset + chunk_size]
            if file_progress_fn:
                sent = min(offset + chunk_size, total)
                await file_progress_fn(sent, total)
            yield chunk

    headers = {**extra_headers, "Content-Length": str(total)}
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.put(presigned_url, content=content_stream(), headers=headers)
        resp.raise_for_status()


async def _create_collection_by_file_id(
    token: str,
    file_id: str,
    dataset_id: str,
    filename: str,
    parent_id: str | None = None,
    training_type: str = "chunk",
    chunk_size: int = 512,
    auto_indexes: bool = True,
    index_prefix_title: bool = True,
    image_index: bool = True,
) -> str:
    """通过 fileId 创建集合（文件已上传到 S3）"""
    url = f"{API_BASE}/core/dataset/collection/create/fileId"
    body: dict = {
        "datasetId": dataset_id,
        "fileId": file_id,
        "trainingType": training_type,
        "chunkSize": chunk_size,
        "autoIndexes": auto_indexes,
        "indexPrefixTitle": index_prefix_title,
        "imageIndex": image_index,
    }
    if parent_id:
        body["parentId"] = parent_id

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=body, headers=_headers(token))
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 200:
            raise Exception(f"创建集合失败: {result}")
        return result.get("data", {}).get("collectionId", "")


async def upload_file_via_s3(
    token: str,
    file_bytes: bytes,
    filename: str,
    dataset_id: str,
    parent_id: str | None = None,
    training_type: str = "chunk",
    chunk_size: int = 512,
    auto_indexes: bool = True,
    index_prefix_title: bool = True,
    image_index: bool = True,
    file_progress_fn=None,
) -> str:
    """三步上传文件到 FastGPT（S3 直传，支持大文件）

    1. 获取数据集 S3 预签名 URL
    2. 直接 PUT 文件到 S3（支持分块进度回调）
    3. 通过 fileId 创建集合

    file_progress_fn: async (bytes_sent, bytes_total) -> None
    """
    presign = await _get_presigned_upload_url(token, filename, dataset_id)

    # 检查文件大小
    max_size = presign.get("maxSize", 0)
    if max_size and len(file_bytes) > max_size:
        raise Exception(f"文件 {filename} 大小 {len(file_bytes) / 1024 / 1024:.1f}MB 超过限制 {max_size / 1024 / 1024:.0f}MB")

    # 上传到 S3（带进度回调）
    await _upload_to_s3(presign["url"], file_bytes, presign.get("headers", {}), file_progress_fn)

    # 创建集合
    return await _create_collection_by_file_id(
        token=token,
        file_id=presign["key"],
        dataset_id=dataset_id,
        filename=filename,
        parent_id=parent_id,
        training_type=training_type,
        chunk_size=chunk_size,
        auto_indexes=auto_indexes,
        index_prefix_title=index_prefix_title,
        image_index=image_index,
    )
