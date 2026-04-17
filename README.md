# FastGPT 知识库批量上传工具

将本地文件和文件夹批量上传到 [FastGPT](https://services.ciqtek.com) 知识库的桌面工具。支持增量上传、大文件断点续传、失败自动重试，PyInstaller 打包为单文件可执行程序，双击即用。

<!-- 截图占位符
![主界面](docs/screenshot-main.png)
![上传进度](docs/screenshot-progress.png)
-->

## 功能特性

- **账号登录** — 用户名密码登录 FastGPT 平台
- **知识库选择** — 登录后选择目标知识库
- **文件浏览** — 浏览本地文件系统，多选目录和文件
- **批量上传** — S3 presigned URL 直传，支持大文件
- **增量上传** — 自动跳过已有文件，复用已有文件夹结构
- **失败重试** — 单文件失败自动重试 5 次，完成后展示失败列表，支持一键重试
- **实时进度** — WebSocket 推送上传进度
- **任务中心** — 查看所有上传任务的历史和状态

## 快速开始

### 从 Release 下载（推荐）

前往 [Releases](https://github.com/ciqtek-aitea/fastgpt-kb-batch/releases) 下载对应平台的可执行文件，双击运行即可。

- macOS（Apple Silicon）：`fastgpt-kb-batch-macos`
- Windows（x64）：`fastgpt-kb-batch-windows.exe`

### 开发模式

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main

# 前端（另一个终端）
cd frontend
npm install
npm run dev
```

或使用一键启动脚本：

```bash
bash run.sh
```

启动后访问 http://localhost:5173。

### 生产构建

```bash
python3 build.py
```

构建产物位于 `backend/dist/fastgpt-kb-batch`（macOS）或 `backend/dist/fastgpt-kb-batch.exe`（Windows）。

仅构建前端（不打包）：

```bash
python3 build.py --frontend-only
```

### CI 自动构建

推送 `v*` 格式的 tag 触发 GitHub Actions 自动构建并发布 Release：

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 技术架构

```
├── frontend/          # React 前端
├── backend/           # FastAPI 后端
│   └── app/
│       ├── routers/   # API 路由（认证、数据集、上传、文件系统）
│       ├── services/  # 业务逻辑（FastGPT 交互、上传服务）
│       ├── models/    # 数据模型
│       ├── ws/        # WebSocket 进度推送
│       └── static/    # 前端构建产物（生产模式）
├── build.py           # 构建脚本
├── fastgpt-kb-batch.spec  # PyInstaller 配置
├── run.sh             # 一键开发启动脚本
└── .github/workflows/build.yml  # CI
```

| 层级 | 技术栈 |
|------|--------|
| 前端 | React 19, Vite 8, Ant Design 6, TypeScript |
| 后端 | FastAPI, uvicorn, httpx, websockets, Pydantic |
| 构建 | PyInstaller（macOS arm64 + Windows x64） |

## License

MIT
