# -*- coding: utf-8 -*-
"""
Concurrency and race condition tests:
Validates thread safety under burst traffic, SQLite WAL mode, and mutex protection.
"""

from concurrent.futures import ThreadPoolExecutor
import pytest


def test_concurrent_sync_requests(api_client):
    """验证多个并发请求同时触发 /api/sync 时，线程池与互斥锁保护正常，无 DB 锁死 (500) 现象"""
    def do_sync(idx):
        return api_client.post_json("/api/sync", {"mode": "incremental"})

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(do_sync, range(6)))

    for status, data in results:
        assert status == 200
        assert data.get("ok") is True


def test_concurrent_event_clipping(api_client):
    """验证多线程并发进行结构化剪藏与双表 Upsert 入库时的事务安全性"""
    def do_clip(idx):
        payload = {
            "title": f"并发测试活动展会_{idx}",
            "raw_text": f"2026年11月{idx:02d}日 在南京河西金鹰世界举办测试集市，免票入场",
            "category": "🎉 南京活动",
            "location": "河西金鹰世界",
            "event_time": f"2026年11月{idx:02d}日"
        }
        return api_client.post_json("/api/events/clip", payload)

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(do_clip, range(1, 6)))

    for status, data in results:
        assert status == 200
        assert data.get("ok") is True
        assert "event" in data
