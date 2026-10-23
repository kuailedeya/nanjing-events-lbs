# -*- coding: utf-8 -*-
"""
Integration tests for all Nanjing Events LBS REST APIs.
Validates 100% backward compatibility, schema adherence, and lifecycle status.
"""

import json
import pytest


def test_health_check(api_client):
    status, data = api_client.get_json("/api/health")
    assert status == 200
    assert data["ok"] is True
    assert data["service"] == "nanjing-events-lbs-backend"
    assert "version" in data
    assert "database" in data
    assert data["database"]["journal_mode"] == "wal"


def test_spa_root_and_favicons(api_client):
    # 根路由应当托管并返回 HTML SPA 单页
    status, headers, body = api_client.get("/")
    assert status == 200
    assert "text/html" in headers.get("Content-Type", "")
    assert b"<html" in body.lower()

    # Favicon 应当正常返回
    status_ico, _, _ = api_client.get("/favicon.ico")
    assert status_ico in (200, 304)

    status_svg, _, _ = api_client.get("/favicon.svg")
    assert status_svg in (200, 304)


def test_events_list_and_schema(api_client):
    status, data = api_client.get_json("/api/events")
    assert status == 200
    assert data["ok"] is True
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)

    if data["items"]:
        item = data["items"][0]
        # 严格验证前端依赖的核心字段契约
        required_fields = [
            "id", "title", "short_title", "category", "sub_category",
            "start_date", "end_date", "days_left", "time_status",
            "district", "address", "lng", "lat", "is_free", "benefit"
        ]
        for field in required_fields:
            assert field in item, f"Missing required contract field: {field}"
        assert isinstance(item["short_title"], str)
        assert len(item["short_title"]) > 0


def test_events_pagination(api_client):
    status, data = api_client.get_json("/api/events?page=1&page_size=5")
    assert status == 200
    assert data["ok"] is True
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5
    assert "total_pages" in data
    assert "filtered_total" in data


def test_events_multidimensional_filtering(api_client):
    # 免费活动筛选
    status, free_data = api_client.get_json("/api/events?is_free=1")
    assert status == 200
    for it in free_data.get("items", []):
        assert it["is_free"] is True

    # 行政区筛选
    status, dist_data = api_client.get_json("/api/events?district=玄武区")
    assert status == 200
    for it in dist_data.get("items", []):
        assert it["district"] == "玄武区"

    # 分类筛选
    status, cat_data = api_client.get_json("/api/events?category=🎪 南京展会")
    assert status == 200
    for it in cat_data.get("items", []):
        assert it["category"] == "🎪 南京展会"


def test_events_nearby_spatial_query(api_client):
    # 新街口坐标 [lat: 32.0436, lng: 118.7969] 5公里范围内活动
    status, data = api_client.get_json("/api/events/nearby?lat=32.0436&lng=118.7969&radius=5")
    assert status == 200
    assert data["ok"] is True
    assert "events" in data or "items" in data
    events_list = data.get("events") or data.get("items")
    assert isinstance(events_list, list)
    for ev in events_list:
        assert "distance_km" in ev
        assert ev["distance_km"] <= 5.05  # 允许轻微浮点截断余量


def test_apple_ical_feed_compliance(api_client):
    status, headers, body = api_client.get("/api/events/calendar.ics")
    assert status == 200
    assert "text/calendar" in headers.get("Content-Type", "")
    ics_text = body.decode("utf-8")
    assert "BEGIN:VCALENDAR" in ics_text
    assert "PRODID:-//Nanjing Events LBS" in ics_text
    assert "X-WR-TIMEZONE:Asia/Shanghai" in ics_text
    assert "END:VCALENDAR" in ics_text
    # 换行符必须包含 CRLF 标准
    assert "\r\n" in ics_text


def test_etag_and_caching(api_client):
    status, headers, _ = api_client.get("/api/events")
    assert status == 200
    etag = headers.get("ETag")
    assert etag is not None

    # 发送 If-None-Match 条件请求应当秒级返回 304 Not Modified
    status_304, _, _ = api_client.get("/api/events", headers={"If-None-Match": etag})
    assert status_304 == 304


def test_event_clip_and_status_update(api_client):
    # 剪藏一条新活动
    clip_payload = {
        "title": "南京夫子庙金秋非遗国潮市集",
        "raw_text": "2026年11月01日-11月10日 在秦淮区夫子庙大成殿广场举办非遗手作市集，免费入场体验",
        "category": "🎉 南京活动",
        "location": "南京夫子庙大成殿",
        "event_time": "2026年11月01日-11月10日",
        "benefit": "免费入场"
    }
    status, res = api_client.post_json("/api/events/clip", clip_payload)
    assert status == 200
    assert res["ok"] is True
    event_obj = res.get("event")
    assert event_obj is not None
    event_id = event_obj["id"]

    # 更新该活动状态为已打卡
    update_payload = {"id": event_id, "status": "已打卡/已体验"}
    status_up, res_up = api_client.post_json("/api/events/status", update_payload)
    assert status_up == 200
    assert res_up["ok"] is True

    # 查验单条详情
    status_detail, detail_data = api_client.get_json(f"/api/events/{event_id}")
    assert status_detail == 200
    item_detail = detail_data.get("item") or detail_data.get("event")
    assert item_detail is not None
    assert item_detail["status"] == "已打卡/已体验"


def test_cache_clear(api_client):
    status, data = api_client.post_json("/api/cache/clear")
    assert status == 200
    assert data["ok"] is True
    assert "message" in data
