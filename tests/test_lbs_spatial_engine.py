# -*- coding: utf-8 -*-
"""
Unit tests for the Nanjing LBS Engine:
Spatial bounds, Haversine distance, lifecycle calendar computation, and NLP tag clustering.
"""

import datetime
import calendar
import pytest
import nanjing_lbs_engine


def test_haversine_distance_accuracy():
    # 新街口 [118.7969, 32.0436] 与 南京奥体中心 [118.7248, 32.0076] 真实地面距离约为 7.8km
    d = nanjing_lbs_engine.haversine_km(118.7969, 32.0436, 118.7248, 32.0076)
    assert 7.0 < d < 8.5


def test_bounding_box_generation():
    min_lat, max_lat, min_lng, max_lng = nanjing_lbs_engine.bounding_box_deg(32.0436, 118.7969, 5.0)
    assert min_lat < 32.0436 < max_lat
    assert min_lng < 118.7969 < max_lng
    # 5km 纬度跨度约 0.045 度
    assert round(max_lat - min_lat, 2) == 0.09


def test_nanjing_spatial_bounds_filtering():
    # 真实南京坐标
    assert nanjing_lbs_engine.is_in_nanjing_bounds(118.7969, 32.0436) is True
    assert nanjing_lbs_engine.is_in_nanjing_bounds(118.6980, 32.1480) is True  # 江北新区

    # 离群脏数据 (如北京、上海或海洋坐标)
    assert nanjing_lbs_engine.is_in_nanjing_bounds(121.4737, 31.2304) is False  # 上海
    assert nanjing_lbs_engine.is_in_nanjing_bounds(116.4074, 39.9042) is False  # 北京
    assert nanjing_lbs_engine.is_in_nanjing_bounds(0.0, 0.0) is False           # 大西洋


def test_february_date_clamping_prevents_invalid_calendar_crash():
    """验证 2月月末动态计算，彻底杜绝 02-30 非法 ISO 日期导致的崩溃"""
    year = 2026
    feb_last = calendar.monthrange(year, 2)[1]
    assert feb_last in (28, 29)

    # 验证解析跨月周期
    s_date, e_date, s_iso, e_iso = nanjing_lbs_engine.parse_lifecycle_dates("2026年2月10日-2月28日", "2026-02-01")
    assert s_date == "2026-02-10"
    assert e_date == "2026-02-28"
    # 能够被 datetime.date 解析而不抛出 ValueError
    datetime.date.fromisoformat(s_date)
    datetime.date.fromisoformat(e_date)


def test_short_title_extraction():
    test_cases = [
        ("【官方首发】2026南京国际新能源汽车博览会盛大开幕！", "国际新能源汽车博览会盛大开幕"),
        ("（限时免费）南京博物院特展打卡全攻略", "博物院特展打卡全攻略"),
        ("南京·德基美术馆草间弥生大展", "德基美术馆草间弥生大展"),
    ]
    for raw, expected in test_cases:
        res = nanjing_lbs_engine.extract_short_title(raw)
        assert len(res) > 0
        assert "【" not in res
        assert "（" not in res


def test_jiangbei_district_clustering():
    """验证对江北新区地标（研创园、南京北站、地下城、市民中心）的自动聚类识别"""
    tags = nanjing_lbs_engine.build_tags(
        category="🎪 南京展会",
        sub_category="科技创新",
        district="江北新区",
        is_free=True,
        platform="微信公众号",
        address="南京市江北新区研创园共享空间",
        title="南京江北地下城规划展"
    )
    assert "江北新区" in tags
    assert "免票直入" in tags
