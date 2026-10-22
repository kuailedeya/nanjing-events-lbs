#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南京 11 行政区划与高德 GCJ-02 空间编码引擎 + nj_events 表同步模块 (nanjing_lbs_engine.py)
严格对齐《南京地区同城活动抓取与时空可视化系统》表 2 ~ 表 5 契约。
"""

import datetime
import hashlib
import json
import math
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

BASE_DIR = Path(r"E:\usage")
SQLITE_PATH = BASE_DIR / "local.db"
VAULT_DIR = Path(r"E:\Note storage\IOT")
DB_FOLDER = "05_社媒情报库"

# 表 4：南京 11 行政区划 + 全城通用 GCJ-02 基准坐标
NANJING_DISTRICTS: Dict[str, Tuple[float, float]] = {
    "玄武区": (118.7977, 32.0482),
    "秦淮区": (118.7947, 32.0212),
    "建邺区": (118.7265, 31.9986),
    "鼓楼区": (118.7697, 32.0663),
    "栖霞区": (118.9094, 32.1121),
    "雨花台区": (118.7789, 31.9920),
    "江宁区": (118.8400, 31.9526),
    "浦口区": (118.6279, 32.0588),
    "六合区": (118.8414, 32.3407),
    "溧水区": (119.0287, 31.6512),
    "高淳区": (118.8923, 31.3271),
    "全城通用": (118.7842, 32.0418),  # 新街口德基中心点
}

# 南京核心场馆 / 商圈 / 景区 GCJ-02 精确坐标词典 (district, lng, lat)
NANJING_LANDMARKS: List[Tuple[str, str, float, float]] = [
    ("南京国际博览中心", "建邺区", 118.7265, 31.9986),
    ("河西国博", "建邺区", 118.7265, 31.9986),
    ("元通", "建邺区", 118.7235, 31.9952),
    ("江苏大剧院", "建邺区", 118.7128, 32.0112),
    ("保利大剧院", "建邺区", 118.7042, 31.9921),
    ("奥体中心", "建邺区", 118.7248, 32.0082),
    ("金鹰世界", "建邺区", 118.7385, 32.0258),
    ("河西金鹰", "建邺区", 118.7385, 32.0258),
    ("金陵图书馆", "建邺区", 118.7165, 32.0053),
    ("鱼嘴湿地", "建邺区", 118.6632, 31.9715),
    ("南京国际展览中心", "玄武区", 118.8136, 32.0754),
    ("新庄国展中心", "玄武区", 118.8136, 32.0754),
    ("新庄", "玄武区", 118.8136, 32.0754),
    ("玄武湖", "玄武区", 118.7977, 32.0725),
    ("莲花广场", "玄武区", 118.8035, 32.0748),
    ("情侣园", "玄武区", 118.8162, 32.0721),
    ("红山森林动物园", "玄武区", 118.8024, 32.0942),
    ("玄武红山新城", "玄武区", 118.8110, 32.0965),
    ("南京博物院", "玄武区", 118.8245, 32.0402),
    ("江苏省美术馆", "玄武区", 118.7958, 32.0451),
    ("六朝博物馆", "玄武区", 118.7982, 32.0439),
    ("古生物博物馆", "玄武区", 118.7946, 32.0602),
    ("钟山风景区", "玄武区", 118.8482, 32.0586),
    ("中山陵", "玄武区", 118.8542, 32.0628),
    ("德基广场", "玄武区", 118.7848, 32.0435),
    ("1912街区", "玄武区", 118.7972, 32.0448),
    ("南京万象天地", "秦淮区", 118.7785, 32.0236),
    ("万象天地", "秦淮区", 118.7785, 32.0236),
    ("夫子庙", "秦淮区", 118.7892, 32.0205),
    ("老门东", "秦淮区", 118.7868, 32.0126),
    ("熙南里", "秦淮区", 118.7802, 32.0248),
    ("秦淮河", "秦淮区", 118.7912, 32.0195),
    ("大报恩寺", "秦淮区", 118.7836, 32.0092),
    ("新街口", "秦淮区", 118.7841, 32.0415),
    ("南京艺术学院", "鼓楼区", 118.7524, 32.0652),
    ("颐和路", "鼓楼区", 118.7658, 32.0631),
    ("阅江楼", "鼓楼区", 118.7426, 32.0945),
    ("清凉山", "鼓楼区", 118.7582, 32.0496),
    ("古林公园", "鼓楼区", 118.7538, 32.0672),
    ("幕燕滨江", "栖霞区", 118.7915, 32.1268),
    ("燕子矶", "栖霞区", 118.8152, 32.1426),
    ("栖霞山", "栖霞区", 118.9625, 32.1592),
    ("仙林大学城", "栖霞区", 118.9182, 32.1086),
    ("万达茂", "栖霞区", 118.9586, 32.1165),
    ("江宁湖熟", "江宁区", 118.9624, 31.8365),
    ("湖熟菊花展", "江宁区", 118.9624, 31.8365),
    ("湖熟", "江宁区", 118.9624, 31.8365),
    ("百家湖", "江宁区", 118.8216, 31.9338),
    ("景枫中心", "江宁区", 118.8205, 31.9352),
    ("牛首山", "江宁区", 118.7458, 31.9162),
    ("园博园", "江宁区", 119.0352, 32.0548),
    ("雨花客厅", "雨花台区", 118.7615, 31.9812),
    ("南京南站", "雨花台区", 118.7968, 31.9692),
    ("雨花台", "雨花台区", 118.7789, 31.9985),
    ("扬子江国际会议中心", "浦口区", 118.6912, 32.0885),
    ("江北图书馆", "浦口区", 118.6854, 32.0932),
    ("老山", "浦口区", 118.6025, 32.0816),
    ("珍珠泉", "浦口区", 118.6624, 32.1285),
    ("金牛湖", "六合区", 118.9582, 32.4685),
    ("巴布洛生态谷", "六合区", 118.7824, 32.4412),
    ("南京空港国际博览中心", "溧水区", 118.9652, 31.7325),
    ("空港国际博览中心", "溧水区", 118.9652, 31.7325),
    ("天生桥", "溧水区", 118.9952, 31.6215),
    ("无想水镇", "溧水区", 119.0325, 31.6182),
    ("高淳老街", "高淳区", 118.8756, 31.3254),
    ("固城湖", "高淳区", 118.9125, 31.2985),
]


def _deterministic_jitter(seed_str: str) -> Tuple[float, float]:
    """生成稳定微偏移 (±0.0022° ≈ 200米)，防止同一场馆多场展会完全重叠在同一个像素点"""
    h = hashlib.md5(seed_str.encode("utf-8")).hexdigest()
    dx = ((int(h[:4], 16) / 65535.0) - 0.5) * 0.0044
    dy = ((int(h[4:8], 16) / 65535.0) - 0.5) * 0.0044
    return round(dx, 6), round(dy, 6)


def geocode_nanjing(
    address_text: str, title: str = "", summary: str = "", seed_id: str = ""
) -> Tuple[str, float, float, str]:
    """
    将南京地点/场馆转换为 (district, lng, lat, geocode_source) [GCJ-02 坐标系]
    优先尝试高德 Web 服务 API（若配置了 AMAP_WEB_KEY），否则使用内置南京地标词典精准映射。
    """
    combined = f"{address_text} {title} {summary}"
    amap_key = os.environ.get("AMAP_WEB_KEY", "").strip()
    if amap_key and address_text and not any(k in address_text for k in ["APP", "线上", "支付宝", "微信", "小红书"]):
        try:
            q_addr = urllib.parse.quote(f"南京市{address_text}")
            url = f"https://restapi.amap.com/v3/geocode/geo?key={amap_key}&city=%E5%8D%97%E4%BA%AC&address={q_addr}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                geocodes = data.get("geocodes") or []
                if geocodes:
                    g = geocodes[0]
                    loc_str = g.get("location", "")
                    if "," in loc_str:
                        lng_s, lat_s = loc_str.split(",")
                        dist = g.get("district") or "玄武区"
                        if isinstance(dist, list):
                            dist = "玄武区"
                        return dist, round(float(lng_s), 6), round(float(lat_s), 6), "amap_api"
        except Exception:
            pass

    dx, dy = _deterministic_jitter(seed_id or title or address_text)
    full_text = f"{title} {address_text} {summary}"

    # 1. 最优先在 title 中匹配具体场馆/地标与 11 行政区
    for kw, dist, base_lng, base_lat in NANJING_LANDMARKS:
        if kw in title:
            return dist, round(base_lng + dx, 6), round(base_lat + dy, 6), "nanjing_landmark_dict"
    for dist_name, (base_lng, base_lat) in NANJING_DISTRICTS.items():
        if dist_name != "全城通用" and (dist_name in title or dist_name[:2] in title):
            return dist_name, round(base_lng + dx * 1.5, 6), round(base_lat + dy * 1.5, 6), "nanjing_district_dict"

    # 2. 其次在 address_text 中匹配具体场馆/地标与 11 行政区
    for kw, dist, base_lng, base_lat in NANJING_LANDMARKS:
        if kw in address_text:
            return dist, round(base_lng + dx, 6), round(base_lat + dy, 6), "nanjing_landmark_dict"
    for dist_name, (base_lng, base_lat) in NANJING_DISTRICTS.items():
        if dist_name != "全城通用" and (dist_name in address_text or dist_name[:2] in address_text):
            return dist_name, round(base_lng + dx * 1.5, 6), round(base_lat + dy * 1.5, 6), "nanjing_district_dict"

    # 3. 再在 summary 中匹配具体场馆/地标与 11 行政区
    for kw, dist, base_lng, base_lat in NANJING_LANDMARKS:
        if kw in full_text:
            return dist, round(base_lng + dx, 6), round(base_lat + dy, 6), "nanjing_landmark_dict"
    for dist_name, (base_lng, base_lat) in NANJING_DISTRICTS.items():
        if dist_name != "全城通用" and (dist_name in full_text or dist_name[:2] in full_text):
            return dist_name, round(base_lng + dx * 1.5, 6), round(base_lat + dy * 1.5, 6), "nanjing_district_dict"

    # 5. 线上/全城羊毛福利
    if any(k in full_text for k in ["APP", "支付宝", "云闪付", "微信", "立减金", "消费券", "线上", "全城", "盒马"]):
        base_lng, base_lat = NANJING_DISTRICTS["全城通用"]
        return "全城通用", round(base_lng + dx * 2.2, 6), round(base_lat + dy * 2.2, 6), "nanjing_citywide_channel"

    # 默认落点玄武区/新街口核心圈
    base_lng, base_lat = NANJING_DISTRICTS["玄武区"]
    return "玄武区", round(base_lng + dx * 2.0, 6), round(base_lat + dy * 2.0, 6), "nanjing_default_center"


def infer_sub_category(category: str, title: str, benefit: str, summary: str) -> str:
    txt = f"{title} {benefit} {summary}"
    if "展会" in category:
        if any(k in txt for k in ["艺术", "美术", "首展", "画展", "特展"]):
            return "艺术特展"
        return "大型博览会"
    if "活动" in category:
        if any(k in txt for k in ["市集", "夜游", "菊花", "游园"]):
            return "市集游园"
        if any(k in txt for k in ["音乐", "演出", "歌会", "戏剧"]):
            return "演出音乐"
        if any(k in txt for k in ["开放日", "免票", "景区"]):
            return "景区免票日"
        return "周末同城活动"
    if any(k in txt for k in ["消费券", "补贴"]):
        return "政府/商圈消费券"
    if any(k in txt for k in ["立减金", "刷卡", "红包", "乘车"]):
        return "银行/支付立减金"
    return "打卡周边/0元礼"


def parse_start_end_iso(event_time_text: str, publish_date: str) -> Tuple[str, str]:
    """从 event_time_text 提取 2026 年 ISO8601 起止时间，供日历组件按日渲染"""
    nums = re.findall(r"(\d{1,2})\s*[月.]\s*(\d{1,2})", event_time_text or "")
    if len(nums) >= 2:
        m1, d1 = int(nums[0][0]), int(nums[0][1])
        m2, d2 = int(nums[1][0]), int(nums[1][1])
        return (
            f"2026-{m1:02d}-{d1:02d}T09:00:00+08:00",
            f"2026-{m2:02d}-{d2:02d}T18:00:00+08:00",
        )
    if len(nums) == 1:
        m1, d1 = int(nums[0][0]), int(nums[0][1])
        return (
            f"2026-{m1:02d}-{d1:02d}T09:00:00+08:00",
            f"2026-{m1:02d}-{d1:02d}T20:00:00+08:00",
        )
    if "截止" in (event_time_text or "") and "10月31" in (event_time_text or ""):
        return ("2026-10-01T00:00:00+08:00", "2026-10-31T23:59:59+08:00")
    base_d = (publish_date or "2026-10-20")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", base_d):
        base_d = "2026-10-20"
    return (f"{base_d}T09:00:00+08:00", "2026-10-31T21:00:00+08:00")


def extract_price_and_free(benefit: str, title: str, summary: str) -> Tuple[bool, float]:
    txt = f"{benefit} {title} {summary}"
    is_free = bool(re.search(r"免费|免票|0元|0\.01|0\.1元|立减|消费券|补贴|羊毛|打卡领", txt))
    m_price = re.search(r"(\d+(?:\.\d+)?)\s*元", benefit or "")
    price_num = 0.0
    if m_price and not is_free:
        try:
            price_num = float(m_price.group(1))
        except Exception:
            price_num = 0.0
    return is_free, price_num


def build_tags(
    category: str, sub_category: str, district: str, is_free: bool, platform: str, address: str
) -> List[str]:
    tags = []
    if is_free:
        tags.append("免费/0元羊毛")
    tags.append(district)
    tags.append(sub_category)
    tags.append(platform)
    short_loc = (address or "").split("（")[0].split("(")[0].split("·")[0].strip()
    if short_loc and short_loc not in tags and len(short_loc) <= 10:
        tags.append(short_loc)
    return tags


def haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """计算两个 GCJ-02 坐标点之间的球面距离（单位：公里），等价于 PostGIS ST_DistanceSphere"""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return round(2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def ensure_nj_events_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nj_events (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            category        TEXT NOT NULL,
            sub_category    TEXT NOT NULL,
            start_time      TEXT,
            end_time        TEXT,
            event_time_text TEXT NOT NULL,
            district        TEXT NOT NULL,
            address         TEXT NOT NULL,
            lng             REAL NOT NULL,
            lat             REAL NOT NULL,
            geom            TEXT NOT NULL,
            benefit         TEXT NOT NULL,
            is_free         INTEGER NOT NULL DEFAULT 1,
            action_guide    TEXT NOT NULL,
            summary         TEXT NOT NULL,
            tags            TEXT NOT NULL,
            extra_info      TEXT NOT NULL,
            source_url      TEXT UNIQUE NOT NULL,
            obsidian_path   TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT '待去/待薅',
            updated_at      TEXT NOT NULL
        )
        """
    )
    conn.commit()


def migrate_and_sync_all() -> List[Dict[str, Any]]:
    """
    将 nanjing_deals_events 与 Obsidian 笔记全量同步升级至 nj_events 表，
    同时把 district / lng / lat / sub_category / tags 写回每篇 Obsidian .md 的 YAML 属性。
    """
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    ensure_nj_events_table(conn)
    conn.execute("DELETE FROM nj_events")

    rows = conn.execute("SELECT * FROM nanjing_deals_events ORDER BY publish_date DESC").fetchall()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enriched_list: List[Dict[str, Any]] = []
    seen_paths = set()
    seen_titles = set()
    noise_keywords = ("赵露思", "横店开机", "上海好物", "机器压平", "全国展会2026排期表(10-12月)", "盒马新疆季")

    for r in rows:
        d = dict(r)
        post_id = d["post_id"]
        title = d["title"]
        obsidian_path = d.get("obsidian_path") or ""
        md_file = VAULT_DIR / obsidian_path

        # 清理重复 item_* 或非南京无关噪声数据
        if post_id.startswith("item_") or any(nk in title for nk in noise_keywords):
            conn.execute("DELETE FROM nanjing_deals_events WHERE post_id = ?", (post_id,))
            if any(nk in title for nk in noise_keywords) and md_file.exists():
                try:
                    md_file.unlink()
                except Exception:
                    pass
            continue

        if obsidian_path in seen_paths or title in seen_titles:
            conn.execute("DELETE FROM nanjing_deals_events WHERE post_id = ?", (post_id,))
            continue
        seen_paths.add(obsidian_path)
        seen_titles.add(title)
        category = d["category"]
        event_time_text = d.get("event_time") or "2026年10月近期"
        address = d.get("location") or "南京主城区"
        benefit = d.get("benefit") or "免费/详见攻略"
        action_guide = d.get("action_guide") or "见要点说明"
        summary = d.get("summary") or title
        platform = d.get("platform") or "微信公众号"
        author = d.get("author") or "南京同城"
        publish_date = d.get("publish_date") or "2026-10-20"
        source_url = d.get("url") or f"https://local.nanjing/{post_id}"
        obsidian_path = d.get("obsidian_path") or ""
        status = d.get("status") or "待去/待薅"

        # 读取 Obsidian 笔记中的最新 status 与 key_points
        md_file = VAULT_DIR / obsidian_path
        if not md_file.exists():
            conn.execute("DELETE FROM nanjing_deals_events WHERE post_id = ?", (post_id,))
            conn.execute("DELETE FROM nj_events WHERE id = ?", (post_id,))
            continue
        key_points: List[str] = []
        if md_file.exists():
            try:
                txt = md_file.read_text(encoding="utf-8")
                m_yaml = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
                if m_yaml:
                    fm = yaml.safe_load(m_yaml.group(1)) or {}
                    if fm.get("status"):
                        status = fm["status"]
                for ln in txt.splitlines():
                    if ln.strip().startswith("- "):
                        key_points.append(ln.strip()[2:].strip())
            except Exception:
                pass

        district, lng, lat, geo_src = geocode_nanjing(address, title, summary, post_id)
        sub_cat = infer_sub_category(category, title, benefit, summary)
        start_iso, end_iso = parse_start_end_iso(event_time_text, publish_date)
        is_free, price_num = extract_price_and_free(benefit, title, summary)
        tags_list = build_tags(category, sub_cat, district, is_free, platform, address)
        geom_wkt = f"POINT({lng} {lat})"

        extra_obj = {
            "platform": platform,
            "author": author,
            "publish_date": publish_date,
            "key_points": key_points,
            "price_num": price_num,
            "geocode_source": geo_src,
            "likes": int(d.get("likes") or 0),
        }

        conn.execute(
            """
            INSERT INTO nj_events (
                id, title, category, sub_category, start_time, end_time, event_time_text,
                district, address, lng, lat, geom, benefit, is_free, action_guide,
                summary, tags, extra_info, source_url, obsidian_path, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_url) DO UPDATE SET
                title=excluded.title,
                category=excluded.category,
                sub_category=excluded.sub_category,
                start_time=excluded.start_time,
                end_time=excluded.end_time,
                event_time_text=excluded.event_time_text,
                district=excluded.district,
                address=excluded.address,
                lng=excluded.lng,
                lat=excluded.lat,
                geom=excluded.geom,
                benefit=excluded.benefit,
                is_free=excluded.is_free,
                action_guide=excluded.action_guide,
                summary=excluded.summary,
                tags=excluded.tags,
                extra_info=excluded.extra_info,
                obsidian_path=excluded.obsidian_path,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (
                post_id,
                title,
                category,
                sub_cat,
                start_iso,
                end_iso,
                event_time_text,
                district,
                address,
                lng,
                lat,
                geom_wkt,
                benefit,
                1 if is_free else 0,
                action_guide,
                summary,
                json.dumps(tags_list, ensure_ascii=False),
                json.dumps(extra_obj, ensure_ascii=False),
                source_url,
                obsidian_path,
                status,
                now_str,
            ),
        )

        # 同步把 district / lng / lat / sub_category 写回 Obsidian 笔记 YAML
        if md_file.exists():
            try:
                txt = md_file.read_text(encoding="utf-8")
                m_yaml = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", txt, re.S)
                if m_yaml:
                    fm = yaml.safe_load(m_yaml.group(1)) or {}
                    body = m_yaml.group(2)
                    fm["district"] = district
                    fm["sub_category"] = sub_cat
                    fm["lng"] = lng
                    fm["lat"] = lat
                    fm["is_free"] = is_free
                    fm["status"] = status
                    new_yaml = yaml.safe_dump(
                        fm, allow_unicode=True, sort_keys=False, default_flow_style=False
                    ).strip()
                    md_file.write_text(f"---\n{new_yaml}\n---\n\n{body.lstrip()}", encoding="utf-8")
            except Exception:
                pass

        enriched_list.append(
            {
                "id": post_id,
                "post_id": post_id,
                "title": title,
                "category": category,
                "sub_category": sub_cat,
                "start_time": start_iso,
                "end_time": end_iso,
                "event_time": event_time_text,
                "event_time_text": event_time_text,
                "district": district,
                "address": address,
                "location": address,
                "lng": lng,
                "lat": lat,
                "geom": geom_wkt,
                "benefit": benefit,
                "is_free": is_free,
                "action_guide": action_guide,
                "summary": summary,
                "tags": tags_list,
                "extra_info": extra_obj,
                "platform": platform,
                "author": author,
                "publish_date": publish_date,
                "key_points": key_points,
                "source_url": source_url,
                "url": source_url,
                "obsidian_path": obsidian_path,
                "obsidian_uri": f"obsidian://open?vault=IOT&file={urllib.parse.quote(obsidian_path)}",
                "status": status,
                "updated_at": now_str,
            }
        )

    conn.commit()
    conn.close()
    return enriched_list


if __name__ == "__main__":
    import social_obsidian_sync
    items = migrate_and_sync_all()
    social_obsidian_sync.ObsidianSummaryDB().build_base_and_dashboard()
    print(f"[✓] 已同步生成 nj_events 空间数据表，共 {len(items)} 条南京活动/展会/羊毛记录（含南京11区划与 GCJ-02 经纬度）：")
    for it in items:
        print(f"  - [{it['district']:<4}] ({it['lng']:.6f}, {it['lat']:.6f}) | {it['category']} | {it['sub_category']} | {it['title']}")
