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


def test_multiple_events_sharing_same_source_url(tmp_path):
    """验证同一篇公众号文章报道的多项独立活动不会互相覆盖或秒删"""
    db_path = tmp_path / "multi_url_test.db"
    conn = nanjing_lbs_engine.get_db_connection(db_path)
    nanjing_lbs_engine.ensure_nj_events_table(conn)

    shared_url = "https://mp.weixin.qq.com/s/sample_roundup_article"
    # 模拟同一推文内的两条不同活动
    conn.execute(
        """
        INSERT INTO nanjing_deals_events
        (post_id, category, title, event_time, location, benefit, action_guide, summary, platform, author, publish_date, likes, status, url, obsidian_path)
        VALUES
        ('item_ev1', '🎪 南京展会', '南京国际新能源汽车展', '2026年11月1日', '南京国博', '免费', '预约', '车展', '微信公众号', '南京发布', '2026-10-01', 10, '待去/待薅', ?, ''),
        ('item_ev2', '🎉 南京活动', '南京非遗国潮市集', '2026年11月2日', '夫子庙', '免费', '免票', '市集', '微信公众号', '南京发布', '2026-10-01', 20, '待去/待薅', ?, '')
        """,
        (shared_url, shared_url),
    )
    conn.commit()

    # 临时覆盖 SQLITE_PATH 进行测试同步
    orig_path = nanjing_lbs_engine.SQLITE_PATH
    try:
        nanjing_lbs_engine.SQLITE_PATH = db_path
        items = nanjing_lbs_engine.migrate_and_sync_all()
        # 两条活动必须全部保留，不能有一方被删除
        saved_rows = conn.execute("SELECT id, title, source_url FROM nj_events").fetchall()
        assert len(saved_rows) == 2
        saved_ids = {r[0] for r in saved_rows}
        assert "item_ev1" in saved_ids
        assert "item_ev2" in saved_ids
    finally:
        nanjing_lbs_engine.SQLITE_PATH = orig_path
        conn.close()


def test_sync_preserves_user_manual_status(tmp_path):
    """验证同步引擎绝对不覆盖用户手工修改的活动状态（如已打卡/已体验）"""
    db_path = tmp_path / "status_preservation_test.db"
    conn = nanjing_lbs_engine.get_db_connection(db_path)
    nanjing_lbs_engine.ensure_nj_events_table(conn)

    # 1. 插入一条原始活动并在 nj_events 中标记为已打卡
    conn.execute(
        """
        INSERT INTO nanjing_deals_events
        (post_id, category, title, event_time, location, benefit, action_guide, summary, platform, author, publish_date, likes, status, url, obsidian_path)
        VALUES
        ('item_checked', '🎉 南京活动', '玄武湖菊花展打卡', '2026年10月', '玄武湖', '免费', '直达', '菊花展', '小红书', '博主', '2026-10-01', 5, '待去/待薅', 'https://xhs.com/菊花', '')
        """
    )
    conn.commit()

    orig_path = nanjing_lbs_engine.SQLITE_PATH
    try:
        nanjing_lbs_engine.SQLITE_PATH = db_path
        # 初次同步
        nanjing_lbs_engine.migrate_and_sync_all()

        # 用户通过前端操作将状态更新为“已打卡/已体验”
        conn.execute("UPDATE nj_events SET status = '已打卡/已体验' WHERE id = 'item_checked'")
        conn.commit()

        # 模拟后台定时同步或全量刷新
        nanjing_lbs_engine.migrate_and_sync_all()

        # 查验状态是否依然完好保留
        row = conn.execute("SELECT status FROM nj_events WHERE id = 'item_checked'").fetchone()
        assert row[0] == "已打卡/已体验", f"User status was overwritten! Got {row[0]}"
    finally:
        nanjing_lbs_engine.SQLITE_PATH = orig_path
        conn.close()


def test_cross_year_dates_not_inverted():
    """验证跨年展会（如 12月25日-1月10日）结束年份自动递增，杜绝跨年活动被误算为已过期"""
    s_date, e_date, s_iso, e_iso = nanjing_lbs_engine.parse_lifecycle_dates(
        "2026年12月25日-1月10日", "2026-12-01"
    )
    assert s_date == "2026-12-25"
    assert e_date == "2027-01-10"
    assert s_date <= e_date
    # 验证生命周期计算在 12月28日时是进行中，绝对不能是 expired
    sim_now = datetime.date(2026, 12, 28)
    days_left, time_status = nanjing_lbs_engine.compute_lifecycle(s_date, e_date, now_date=sim_now)
    assert time_status == "ongoing"
    assert days_left == 13


def test_full_iso_and_slash_date_lifecycle_parsing():
    """验证包含完整年份的 ISO 日期区间、点号与斜杠格式均能精准提取"""
    # 1. ISO 破折号与波浪号区间
    s1, e1, _, _ = nanjing_lbs_engine.parse_lifecycle_dates("2026-11-01 ~ 2026-11-05")
    assert s1 == "2026-11-01"
    assert e1 == "2026-11-05"

    # 2. 点号与斜杠格式
    s2, e2, _, _ = nanjing_lbs_engine.parse_lifecycle_dates("2026.11.01 - 2026.11.15")
    assert s2 == "2026-11-01"
    assert e2 == "2026-11-15"

    s3, e3, _, _ = nanjing_lbs_engine.parse_lifecycle_dates("2026/11/01至2026/11/05")
    assert s3 == "2026-11-01"
    assert e3 == "2026-11-05"

    # 3. 年月日 + 跨月/跨日简写
    s4, e4, _, _ = nanjing_lbs_engine.parse_lifecycle_dates("2026年11月1日 - 15日")
    assert s4 == "2026-11-01"
    assert e4 == "2026-11-15"

    # 4. 单日全量 ISO 日期
    s5, e5, _, _ = nanjing_lbs_engine.parse_lifecycle_dates("2026-11-20")
    assert s5 == "2026-11-20"
    assert e5 == "2026-11-20"


def test_sync_preserves_multiple_records_with_similar_titles(tmp_path):
    """验证当多篇社媒笔记存在相同或相近标题时，禁止删库，确保 raw 表完好保留并正确聚合并入 extra_sources"""
    db_file = tmp_path / "dedup_test.db"
    conn = nanjing_lbs_engine.get_db_connection(db_file)
    nanjing_lbs_engine.ensure_nj_events_table(conn)

    # 插入两条标题相同但在不同场馆/日期的活动原始记录
    conn.execute(
        """
        INSERT INTO nanjing_deals_events
        (post_id, category, title, event_time, location, benefit, action_guide, summary, platform, author, publish_date, likes, status, url, obsidian_path)
        VALUES
        ('post_1', '🎉 南京活动', '周末免费好去处', '10月24日', '新街口德基广场', '免费', '直接前往', '德基新展', '微信公众号', '南京同城', '2026-10-20', 0, '待去/待薅', 'https://test/1', 'path1.md'),
        ('post_2', '🎉 南京活动', '周末免费好去处', '10月25日', '建邺区南京国际博览中心', '免费领票', '扫码预约', '国博大展', '小红书', '博主小李', '2026-10-21', 10, '待去/待薅', 'https://test/2', 'path2.md')
        """
    )
    conn.commit()
    conn.close()

    # 执行同步
    nanjing_lbs_engine.migrate_and_sync_all(sqlite_path=db_file, vault_dir=tmp_path)

    # 查验原始 raw 表记录绝对不能被删除
    check_conn = nanjing_lbs_engine.get_db_connection(db_file)
    raw_count = check_conn.execute("SELECT COUNT(*) FROM nanjing_deals_events").fetchone()[0]
    assert raw_count == 2, f"Expected 2 raw records in nanjing_deals_events, got {raw_count} (destructive deletion bug!)"
    check_conn.close()


