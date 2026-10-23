# -*- coding: utf-8 -*-
"""
Pytest configuration and shared fixtures for Nanjing Events LBS Backend.
Provides isolated ephemeral servers, clean SQLite databases, and proxy-immune HTTP clients.
"""

import os
import sys
import time
import socket
import tempfile
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pytest

# 确保项目根目录在 sys.path 中
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import nanjing_lbs_engine


def get_free_port() -> int:
    """动态获取操作系统分配的空闲本地端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestHttpClient:
    """代理免疫的轻量级测试 HTTP 客户端"""

    def __init__(self, base_url: str, default_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.default_token = default_token
        # 强制清空代理处理器，防止本地 Windows 抓包代理拦截 127.0.0.1
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @staticmethod
    def _safe_url(base_url: str, path: str) -> str:
        url = f"{base_url}{path}" if path.startswith("/") else f"{base_url}/{path}"
        parsed = urllib.parse.urlsplit(url)
        encoded_path = urllib.parse.quote(parsed.path, safe="/:@&=+$,-_.!~*'()")
        encoded_query = urllib.parse.quote(parsed.query, safe="/:@&=+$,-_.!~*'()")
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, encoded_path, encoded_query, parsed.fragment))

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        url = self._safe_url(self.base_url, path)
        req = urllib.request.Request(url)
        all_headers = {}
        if self.default_token:
            all_headers["Authorization"] = f"Bearer {self.default_token}"
        if headers:
            all_headers.update(headers)
        for k, v in all_headers.items():
            req.add_header(k, v)

        try:
            with self.opener.open(req, timeout=10) as resp:
                resp_headers = {k: v for k, v in resp.headers.items()}
                return resp.status, resp_headers, resp.read()
        except urllib.error.HTTPError as e:
            resp_headers = {k: v for k, v in e.headers.items()}
            try:
                body = e.read()
            except Exception:
                body = b""
            return e.code, resp_headers, body

    def get_json(self, path: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any]]:
        status, _, body = self.get(path, headers=headers)
        try:
            return status, json.loads(body.decode("utf-8"))
        except Exception:
            return status, {"raw": body.decode("utf-8", errors="replace")}

    def post(self, path: str, data: Any = None, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        url = self._safe_url(self.base_url, path)
        body_bytes = b""
        req_headers = {"Content-Type": "application/json"}
        if self.default_token:
            req_headers["Authorization"] = f"Bearer {self.default_token}"
        if headers:
            req_headers.update(headers)

        if isinstance(data, (dict, list)):
            body_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        elif isinstance(data, str):
            body_bytes = data.encode("utf-8")
        elif isinstance(data, bytes):
            body_bytes = data

        req = urllib.request.Request(url, data=body_bytes, method="POST")
        for k, v in req_headers.items():
            req.add_header(k, v)

        try:
            with self.opener.open(req, timeout=10) as resp:
                resp_headers = {k: v for k, v in resp.headers.items()}
                return resp.status, resp_headers, resp.read()
        except urllib.error.HTTPError as e:
            resp_headers = {k: v for k, v in e.headers.items()}
            try:
                body = e.read()
            except Exception:
                body = b""
            return e.code, resp_headers, body

    def post_json(self, path: str, data: Any = None, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any]]:
        status, _, body = self.post(path, data=data, headers=headers)
        try:
            return status, json.loads(body.decode("utf-8"))
        except Exception:
            return status, {"raw": body.decode("utf-8", errors="replace")}


@pytest.fixture(scope="session")
def live_server():
    """启动一个完全隔离且受控的后端服务子进程"""
    port = get_free_port()
    temp_dir = tempfile.TemporaryDirectory(prefix="nj_lbs_test_")
    db_file = Path(temp_dir.name) / "test_local.db"
    vault_dir = Path(temp_dir.name) / "test_vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    # 预初始化数据库表结构
    conn = nanjing_lbs_engine.get_db_connection(db_file)
    nanjing_lbs_engine.ensure_nj_events_table(conn)
    conn.close()

    test_token = "pytest-enterprise-token-2026"
    env = dict(os.environ)
    env.pop("http_proxy", None)
    env.pop("https_proxy", None)
    env.pop("HTTP_PROXY", None)
    env.pop("HTTPS_PROXY", None)
    env["DB_PATH"] = str(db_file)
    env["VAULT_DIR"] = str(vault_dir)
    env["DASHBOARD_API_TOKEN"] = test_token
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [sys.executable, str(REPO_ROOT / "dashboard_server.py"), "--host", "127.0.0.1", "--port", str(port)]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    base_url = f"http://127.0.0.1:{port}"
    client = TestHttpClient(base_url, default_token=test_token)

    # 健康检查等待服务就绪
    ready = False
    for _ in range(30):
        try:
            status, data = client.get_json("/api/health")
            if status == 200 and data.get("ok"):
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.2)

    if not ready:
        proc.terminate()
        temp_dir.cleanup()
        raise RuntimeError(f"Test server on port {port} failed to become ready within 6s.")

    yield {
        "base_url": base_url,
        "client": client,
        "token": test_token,
        "db_file": db_file,
        "vault_dir": vault_dir,
        "port": port,
    }

    # 销毁清理
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
    temp_dir.cleanup()


@pytest.fixture
def api_client(live_server):
    """默认携带有效 Authorization 凭证的测试客户端"""
    return live_server["client"]


@pytest.fixture
def unauthed_client(live_server):
    """不携带任何凭证的匿名客户端"""
    return TestHttpClient(live_server["base_url"], default_token=None)
