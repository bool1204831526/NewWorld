from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
PY38 = Path(r"C:\miniconda\envs\py3.8\python.exe")


def npm_command() -> str:
    candidates = ["npm.cmd", "npm.exe", "npm"] if os.name == "nt" else ["npm"]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("未找到 npm。请确认 Node.js 已安装，并且 npm 在 PATH 中。")


def run(command: List[str], cwd: Path) -> None:
    subprocess.check_call(command, cwd=str(cwd))


def spawn(command: List[str], cwd: Path) -> subprocess.Popen:
    if os.name == "nt":
        return subprocess.Popen(command, cwd=str(cwd), creationflags=subprocess.CREATE_NEW_CONSOLE)
    return subprocess.Popen(command, cwd=str(cwd))


def spawn_npm(args: List[str], cwd: Path) -> subprocess.Popen:
    npm = npm_command()
    if os.name == "nt":
        command = ["cmd.exe", "/k", npm] + args
    else:
        command = [npm] + args
    return spawn(command, cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description="启动 NewWorld 前后端开发服务")
    parser.add_argument("--install", action="store_true", help="启动前安装后端和前端依赖")
    args = parser.parse_args()

    if not PY38.exists():
        print(f"未找到 Python 3.8 环境：{PY38}", file=sys.stderr)
        return 1
    if not BACKEND.exists() or not FRONTEND.exists():
        print("请在 NewWorld 项目根目录运行该脚本。", file=sys.stderr)
        return 1

    npm = npm_command()

    if args.install:
        print("安装后端依赖...")
        run([str(PY38), "-m", "pip", "install", "-r", "requirements-dev.txt"], BACKEND)
        print("安装前端依赖...")
        run([npm, "install"], FRONTEND)

    print("启动后端...")
    spawn([str(PY38), "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"], BACKEND)

    print("启动前端...")
    spawn_npm(["run", "dev"], FRONTEND)

    print()
    print("后端 API: http://127.0.0.1:8000")
    print("后端文档: http://127.0.0.1:8000/docs")
    print("前端工作台: http://127.0.0.1:5173")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
