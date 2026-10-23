# -*- coding: utf-8 -*-
"""
Security regression tests covering OWASP Top 10 vulnerabilities:
SSRF, Path Traversal, Timing Attacks, Denial of Service (DoS), Parameter Tampering.
"""

import pytest


def test_unauthenticated_post_rejected(unauthed_client):
    """验证未提供鉴权凭证的敏感写操作被严格阻断 (401)"""
    status, _, _ = unauthed_client.post("/api/events/clip", data={"title": "Unauthorized"})
    assert status == 401

    status, _, _ = unauthed_client.post("/api/events/status", data={"id": "test", "status": "fake"})
    assert status == 401

    status, _, _ = unauthed_client.post("/api/cache/clear")
    assert status == 401


def test_invalid_bearer_token_rejected(unauthed_client):
    """验证无效或伪造的 Bearer 令牌被拦截"""
    headers = {"Authorization": "Bearer invalid-tampered-token-12345"}
    status, _, _ = unauthed_client.post("/api/cache/clear", headers=headers)
    assert status == 401


def test_static_directory_traversal_blocked(api_client):
    """验证静态文件路由下的目录穿越逃逸尝试被拦截 (403/404)"""
    traversal_paths = [
        "/assets/../local.db",
        "/assets/..%2Flocal.db",
        "/assets/..\\..\\Windows\\System32\\cmd.exe",
        "/assets/....//....//etc/passwd",
    ]
    for path in traversal_paths:
        status, _, _ = api_client.get(path)
        assert status in (403, 404), f"Traversal path {path} was not blocked, got {status}"


def test_ssrf_disallowed_domain_blocked(api_client):
    """验证图片代理阻断非白名单域名的 SSRF 请求 (403)"""
    evil_urls = [
        "https://attacker.internal/evil.jpg",
        "https://evil-hacker.com/image.png",
        "http://google.com/logo.png",
    ]
    for u in evil_urls:
        status, _, _ = api_client.get(f"/api/proxy/image?url={u}")
        assert status == 403


def test_ssrf_port_and_userinfo_evasion_blocked(api_client):
    """验证图片代理对端口扫描与 UserInfo 凭证逃逸的拦截"""
    # 非标准端口 (如试图内网端口探测)
    status_port, _, _ = api_client.get("/api/proxy/image?url=https://qpic.cn:8080/test.jpg")
    assert status_port == 403

    # UserInfo 混淆 (http://user@target)
    status_user, _, _ = api_client.get("/api/proxy/image?url=https://admin:pass@qpic.cn/test.jpg")
    assert status_user == 400


def test_ssrf_private_and_loopback_ip_blocked(api_client):
    """验证图片代理阻断对本地回环或内网私有 IP 的直连探测 (403)"""
    internal_ips = [
        "https://127.0.0.1/test.jpg",
        "https://169.254.169.254/latest/meta-data/",
        "https://192.168.1.1/router.jpg",
        "https://10.0.0.1/admin.png",
    ]
    for target in internal_ips:
        status, _, _ = api_client.get(f"/api/proxy/image?url={target}")
        assert status == 403


def test_malformed_json_returns_400(api_client):
    """验证畸形 JSON 请求体被拦截并返回 400，绝不产生未捕获 500"""
    bad_bodies = [
        b'{"title": "incomplete',
        b'not-a-json-string',
        b'{"key": undefined}',
        b'[1, 2, 3]',  # 不是对象字典
    ]
    for body in bad_bodies:
        status, _, _ = api_client.post("/api/events/clip", data=body)
        assert status == 400


def test_invalid_utf8_binary_payload_returns_400(api_client):
    """验证非 UTF-8 二进制模糊测试报文被优雅捕获为 400"""
    fuzz_bytes = b"\xff\xfe\x00\x01\x80\x90\xaa"
    status, _, _ = api_client.post("/api/events/clip", data=fuzz_bytes)
    assert status == 400


def test_parameter_tampering_returns_400(api_client):
    """验证非法参数输入（如畸形经纬度、非法半径）被拦截为 400"""
    tampered_urls = [
        "/api/events/nearby?lat=invalid_string&lng=118.7969&radius=5",
        "/api/events/nearby?lat=32.0436&lng=NaN&radius=5",
        "/api/events/nearby?lat=32.0436&lng=118.7969&radius=abc",
    ]
    for u in tampered_urls:
        status, _, _ = api_client.get(u)
        assert status == 400


def test_payload_too_large_returns_413(api_client):
    """验证超出 10MB 请求体上限的 DoS 请求被拒绝 (413)"""
    headers = {"Content-Length": str(15 * 1024 * 1024)}  # 15MB
    status, _, _ = api_client.post("/api/events/clip", data=b"", headers=headers)
    assert status == 413
