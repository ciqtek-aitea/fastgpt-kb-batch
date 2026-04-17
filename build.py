#!/usr/bin/env python3
"""构建脚本 — 构建前端 + 打包为可执行文件"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
STATIC = BACKEND / "app" / "static"


def build_frontend():
    """构建前端静态文件"""
    print("=== [1/3] 构建前端 ===")
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True)

    # 复制到后端 static 目录
    dist = FRONTEND / "dist"
    if STATIC.exists():
        shutil.rmtree(STATIC)
    shutil.copytree(dist, STATIC)
    print(f"前端已构建并复制到 {STATIC}")


def build_executable():
    """PyInstaller 打包"""
    print("=== [2/3] PyInstaller 打包 ===")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(ROOT / "fastgpt-kb-batch.spec"), "--noconfirm"],
        cwd=BACKEND,
        check=True,
    )
    print("打包完成！")


def main():
    if not (FRONTEND / "node_modules").exists():
        print("安装前端依赖...")
        subprocess.run(["npm", "install"], cwd=FRONTEND, check=True)

    build_frontend()

    if "--frontend-only" in sys.argv:
        print("仅构建前端，跳过打包")
        return

    # 优先使用 venv 中的 Python
    venv_python = BACKEND / "venv" / "bin" / "python"
    if venv_python.exists():
        print(f"使用 venv: {venv_python}")
        python = str(venv_python)
    else:
        python = sys.executable

    # 检查 PyInstaller
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("安装 PyInstaller...")
        subprocess.run([python, "-m", "pip", "install", "pyinstaller"], check=True)

    # 用 venv Python 执行打包
    subprocess.run(
        [python, "-m", "PyInstaller", str(ROOT / "fastgpt-kb-batch.spec"), "--noconfirm"],
        cwd=BACKEND,
        check=True,
    )
    print("打包完成！")

    # 输出文件位置
    exe_name = "fastgpt-kb-batch.exe" if sys.platform == "win32" else "fastgpt-kb-batch"
    exe_path = BACKEND / "dist" / exe_name
    print(f"\n=== [3/3] 完成 ===")
    print(f"可执行文件: {exe_path}")
    print(f"双击即可运行，自动打开浏览器")


if __name__ == "__main__":
    main()
