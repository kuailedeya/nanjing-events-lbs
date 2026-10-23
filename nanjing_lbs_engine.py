#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南京 11 行政区划与高德 GCJ-02 空间编码引擎 + nj_events 表同步模块 (nanjing_lbs_engine.py)
严格对齐《南京地区同城活动抓取与时空可视化系统》表 2 ~ 表 5 契约。
"""

import calendar
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

BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent))
SQLITE_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "local.db"))
VAULT_DIR = Path(os.environ.get("VAULT_DIR", r"E:\Note storage\IOT"))
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
    ("国博", "建邺区", 118.7265, 31.9986),
    ("元通", "建邺区", 118.7235, 31.9952),
    ("江苏大剧院", "建邺区", 118.7128, 32.0112),
    ("保利大剧院", "建邺区", 118.7042, 31.9921),
    ("保利大剧", "建邺区", 118.7042, 31.9921),
    ("奥体中心", "建邺区", 118.7248, 32.0082),
    ("金鹰世界", "建邺区", 118.7385, 32.0258),
    ("河西金鹰", "建邺区", 118.7385, 32.0258),
    ("华采天地", "建邺区", 118.7235, 31.9952),
    ("河西华采", "建邺区", 118.7235, 31.9952),
    ("南京眼", "建邺区", 118.6852, 31.9895),
    ("青奥村", "建邺区", 118.6925, 31.9882),
    ("金陵图书馆", "建邺区", 118.7165, 32.0053),
    ("鱼嘴湿地", "建邺区", 118.6632, 31.9715),
    ("南京国际展览中心", "玄武区", 118.8136, 32.0754),
    ("新庄国展中心", "玄武区", 118.8136, 32.0754),
    ("新庄国展", "玄武区", 118.8136, 32.0754),
    ("新庄", "玄武区", 118.8136, 32.0754),
    ("玄武湖", "玄武区", 118.7977, 32.0725),
    ("莲花广场", "玄武区", 118.8035, 32.0748),
    ("情侣园", "玄武区", 118.8162, 32.0721),
    ("太阳宫", "玄武区", 118.8125, 32.0682),
    ("金陵STYLE", "玄武区", 118.8125, 32.0682),
    ("白马公园", "玄武区", 118.8172, 32.0578),
    ("鸡鸣寺", "玄武区", 118.7986, 32.0601),
    ("红山森林动物园", "玄武区", 118.8024, 32.0942),
    ("玄武红山新城", "玄武区", 118.8110, 32.0965),
    ("南京博物院", "玄武区", 118.8245, 32.0402),
    ("南博", "玄武区", 118.8245, 32.0402),
    ("江苏省美术馆", "玄武区", 118.7958, 32.0451),
    ("省美术馆", "玄武区", 118.7958, 32.0451),
    ("省美", "玄武区", 118.7958, 32.0451),
    ("六朝博物馆", "玄武区", 118.7982, 32.0439),
    ("古生物博物馆", "玄武区", 118.7946, 32.0602),
    ("钟山风景区", "玄武区", 118.8482, 32.0586),
    ("中山陵", "玄武区", 118.8542, 32.0628),
    ("德基广场", "玄武区", 118.7848, 32.0435),
    ("德基", "玄武区", 118.7848, 32.0435),
    ("1912街区", "玄武区", 118.7972, 32.0448),
    ("1912", "玄武区", 118.7972, 32.0448),
    ("南京万象天地", "秦淮区", 118.7785, 32.0236),
    ("万象天地", "秦淮区", 118.7785, 32.0236),
    ("夫子庙", "秦淮区", 118.7892, 32.0205),
    ("老门东", "秦淮区", 118.7868, 32.0126),
    ("熙南里", "秦淮区", 118.7802, 32.0248),
    ("水游城", "秦淮区", 118.7885, 32.0258),
    ("水平方", "秦淮区", 118.7892, 32.0252),
    ("茂业天地", "秦淮区", 118.7882, 32.0232),
    ("中华门", "秦淮区", 118.7805, 32.0125),
    ("秦淮河", "秦淮区", 118.7912, 32.0195),
    ("大报恩寺", "秦淮区", 118.7836, 32.0092),
    ("新街口", "秦淮区", 118.7841, 32.0415),
    ("南京艺术学院", "鼓楼区", 118.7524, 32.0652),
    ("南艺", "鼓楼区", 118.7524, 32.0652),
    ("颐和路", "鼓楼区", 118.7658, 32.0631),
    ("阅江楼", "鼓楼区", 118.7426, 32.0945),
    ("清凉山", "鼓楼区", 118.7582, 32.0496),
    ("古林公园", "鼓楼区", 118.7538, 32.0672),
    ("紫峰大厦", "鼓楼区", 118.7788, 32.0592),
    ("鼓楼广场", "鼓楼区", 118.7792, 32.0595),
    ("金陵饭店", "鼓楼区", 118.7825, 32.0435),
    ("幕燕滨江", "栖霞区", 118.7915, 32.1268),
    ("燕子矶", "栖霞区", 118.8152, 32.1426),
    ("栖霞山", "栖霞区", 118.9625, 32.1592),
    ("仙林大学城", "栖霞区", 118.9182, 32.1086),
    ("仙林金鹰", "栖霞区", 118.9285, 32.1052),
    ("羊山公园", "栖霞区", 118.9325, 32.1082),
    ("万达茂", "栖霞区", 118.9586, 32.1165),
    ("江宁湖熟", "江宁区", 118.9624, 31.8365),
    ("湖熟菊花展", "江宁区", 118.9624, 31.8365),
    ("湖熟", "江宁区", 118.9624, 31.8365),
    ("百家湖", "江宁区", 118.8216, 31.9338),
    ("景枫中心", "江宁区", 118.8205, 31.9352),
    ("景枫", "江宁区", 118.8205, 31.9352),
    ("牛首山", "江宁区", 118.7458, 31.9162),
    ("园博园", "江宁区", 119.0352, 32.0548),
    ("汤山温泉", "江宁区", 119.0485, 32.0582),
    ("汤山", "江宁区", 119.0485, 32.0582),
    ("雨花客厅", "雨花台区", 118.7615, 31.9812),
    ("南京南站", "雨花台区", 118.7968, 31.9692),
    ("雨花台", "雨花台区", 118.7789, 31.9985),
    ("扬子江国际会议中心", "浦口区", 118.6912, 32.0885),
    ("江北图书馆", "浦口区", 118.6854, 32.0932),
    ("江北市民中心", "浦口区", 118.6872, 32.0915),
    ("江北地下城", "浦口区", 118.6854, 32.0932),
    ("研创园", "浦口区", 118.6352, 32.0258),
    ("南京北站", "浦口区", 118.6821, 32.1654),
    ("弘阳广场", "浦口区", 118.7235, 32.1385),
    ("桥北万象汇", "浦口区", 118.7215, 32.1412),
    ("江北万象汇", "浦口区", 118.7215, 32.1412),
    ("江北虹悦城", "浦口区", 118.6725, 32.0682),
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
    ("栖霞古寺", "栖霞区", 118.9615, 32.1582),
    ("龙江", "鼓楼区", 118.7385, 32.0525),
    ("新城市广场", "鼓楼区", 118.7385, 32.0525),
    ("汤山矿坑公园", "江宁区", 119.0415, 32.0465),
    ("三江学院", "雨花台区", 118.7625, 31.9685),
    ("浦口火车站", "浦口区", 118.7365, 32.0882),
    ("响堂村", "浦口区", 118.6125, 32.0725),
    ("响堂", "浦口区", 118.6125, 32.0725),
    ("平山森林公园", "六合区", 118.8925, 32.3852),
    ("无想山", "溧水区", 119.0412, 31.6025),
    ("郭兴庄园", "溧水区", 119.0125, 31.5825),
    ("高淳慢城", "高淳区", 118.9625, 31.3652),
    ("国际慢城", "高淳区", 118.9625, 31.3652),
    ("固城湖水慢城", "高淳区", 118.9215, 31.3052),
]


def _deterministic_jitter(seed_str: str) -> Tuple[float, float]:
    """生成稳定微偏移 (±0.0022° ≈ 200米)，防止同一场馆多场展会完全重叠在同一个像素点"""
    h = hashlib.md5(seed_str.encode("utf-8")).hexdigest()
    dx = ((int(h[:4], 16) / 65535.0) - 0.5) * 0.0044
    dy = ((int(h[4:8], 16) / 65535.0) - 0.5) * 0.0044
    return round(dx, 6), round(dy, 6)


def is_in_nanjing_bounds(lng: float, lat: float) -> bool:
    """南京行政区域及主客商圈合法坐标边界: 经度 118.2 ~ 119.4, 纬度 31.2 ~ 32.7"""
    return 118.2 <= lng <= 119.4 and 31.2 <= lat <= 32.7


_AMAP_GEOCODE_CACHE: Dict[str, Tuple[str, float, float, str]] = {}


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
        cache_key = address_text.strip()
        if cache_key in _AMAP_GEOCODE_CACHE:
            return _AMAP_GEOCODE_CACHE[cache_key]
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
                        lng_val, lat_val = float(lng_s), float(lat_s)
                        if is_in_nanjing_bounds(lng_val, lat_val):
                            dist = g.get("district") or "玄武区"
                            if isinstance(dist, list):
                                dist = "玄武区"
                            res = (dist, round(lng_val, 6), round(lat_val, 6), "amap_api")
                            _AMAP_GEOCODE_CACHE[cache_key] = res
                            return res
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


def parse_lifecycle_dates(
    event_time_text: str, publish_date: Optional[str] = None
) -> Tuple[str, str, str, str]:
    """
    从 event_time_text 提取结构化日期 start_date / end_date (YYYY-MM-DD)
    以及标准 ISO8601 起止时间戳 (start_iso, end_iso)
    使用 calendar 模块严格计算当月实际最大天数，杜绝 2月30日等非法日期。
    """
    txt = (event_time_text or "").strip()
    today_dt = datetime.date.today()
    pub = (publish_date or today_dt.isoformat())[:10]

    # 提取年份，优先正则匹配，次选 publish_date 前 4 位，兜底当前年份
    year_m = re.search(r"(202\d)年?", txt)
    if year_m:
        year = int(year_m.group(1))
    elif pub and pub[:4].isdigit():
        year = int(pub[:4])
    else:
        year = datetime.datetime.now().year

    def _format_safe_date(y: int, m: int, d: int) -> str:
        m_safe = max(1, min(12, m))
        _, max_day = calendar.monthrange(y, m_safe)
        d_safe = max(1, min(max_day, d))
        return f"{y}-{m_safe:02d}-{d_safe:02d}"

    # 模式1: 完整范围 M1月D1日 - M2月D2日 或 M1.D1 - M2.D2 或 M1/D1 - M2/D2
    m1 = re.findall(r"(\d{1,2})\s*[月./]\s*(\d{1,2})\s*日?", txt)
    if len(m1) >= 2:
        mon1, day1 = int(m1[0][0]), int(m1[0][1])
        mon2, day2 = int(m1[1][0]), int(m1[1][1])
        s_date = _format_safe_date(year, mon1, day1)
        e_date = _format_safe_date(year, mon2, day2)
        return s_date, e_date, f"{s_date}T09:00:00+08:00", f"{e_date}T18:00:00+08:00"

    # 模式2: 同月跨日 M月D1日 - D2日 (如 10月23日—25日, 10月15日-30日)
    m2 = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日?\s*[-—~至–]\s*(\d{1,2})\s*日?", txt)
    if m2:
        mon = int(m2.group(1))
        d1, d2 = int(m2.group(2)), int(m2.group(3))
        s_date = _format_safe_date(year, mon, d1)
        e_date = _format_safe_date(year, mon, d2)
        return s_date, e_date, f"{s_date}T09:00:00+08:00", f"{e_date}T18:00:00+08:00"

    # 模式3: 单日 M月D日 (如 10月18日, 10月23日)
    m3 = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日?", txt)
    if m3:
        mon = int(m3.group(1))
        d = int(m3.group(2))
        s_date = _format_safe_date(year, mon, d)
        if any(k in txt for k in ["起", "开园", "开展", "启幕", "开幕"]):
            mon_safe = max(1, min(12, mon))
            _, last_day = calendar.monthrange(year, mon_safe)
            e_date = _format_safe_date(year, mon_safe, last_day)
        else:
            e_date = s_date
        return s_date, e_date, f"{s_date}T09:00:00+08:00", f"{e_date}T20:00:00+08:00"

    # 模式4: 截止型 (如 10月31日截止)
    m4 = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日?\s*截止", txt)
    if m4:
        mon = int(m4.group(1))
        d = int(m4.group(2))
        s_date = _format_safe_date(year, mon, 1)
        e_date = _format_safe_date(year, mon, d)
        return s_date, e_date, f"{s_date}T00:00:00+08:00", f"{e_date}T23:59:59+08:00"

    # 兜底：基于发布日或默认当月
    if re.match(r"^\d{4}-\d{2}-\d{2}$", pub):
        s_date = pub
        try:
            dt_pub = datetime.date.fromisoformat(pub)
            _, last_d = calendar.monthrange(dt_pub.year, dt_pub.month)
            e_date = f"{dt_pub.year}-{dt_pub.month:02d}-{last_d:02d}"
        except Exception:
            _, last_d = calendar.monthrange(year, today_dt.month)
            e_date = f"{year}-{today_dt.month:02d}-{last_d:02d}"
    else:
        s_date = today_dt.isoformat()
        _, last_d = calendar.monthrange(today_dt.year, today_dt.month)
        e_date = f"{today_dt.year}-{today_dt.month:02d}-{last_d:02d}"
    return s_date, e_date, f"{s_date}T09:00:00+08:00", f"{e_date}T21:00:00+08:00"


def compute_lifecycle(
    start_date_str: str,
    end_date_str: str,
    now_date: Optional[datetime.date] = None,
) -> Tuple[int, str]:
    """
    动态计算活动生命周期与倒计时：
    - days_left: 距结束日期剩余天数（已结束为负数）
    - time_status:
        'expired': days_left < 0
        'upcoming': now_date < start_date
        'ending_soon': 0 <= days_left <= 3 (剩3天内即将截止)
        'ongoing': 进行中
    """
    if not now_date:
        now_date = datetime.date.today()
    try:
        s_date = datetime.date.fromisoformat(start_date_str[:10])
        e_date = datetime.date.fromisoformat(end_date_str[:10])
    except Exception:
        s_date = now_date
        e_date = now_date + datetime.timedelta(days=7)

    days_left = (e_date - now_date).days
    if days_left < 0:
        time_status = "expired"
    elif now_date < s_date:
        time_status = "upcoming"
    elif 0 <= days_left <= 3:
        time_status = "ending_soon"
    else:
        time_status = "ongoing"

    return days_left, time_status


def parse_start_end_iso(event_time_text: str, publish_date: str) -> Tuple[str, str]:
    """兼容旧接口的 ISO 时间提取封装"""
    _, _, start_iso, end_iso = parse_lifecycle_dates(event_time_text, publish_date)
    return start_iso, end_iso


def title_similarity_cjk(t1: str, t2: str) -> float:
    """计算中文标题的 2-gram Jaccard 相似度（去除常见无意义噪声词）"""
    clean1 = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", t1 or "")
    clean2 = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", t2 or "")
    stop_words = [
        "南京", "2026", "年", "活动", "展会", "推荐", "合集", "汇总",
        "攻略", "打卡", "落地", "系列", "近期", "国内", "全国", "江苏", "治愈暴击"
    ]
    for sw in stop_words:
        clean1 = clean1.replace(sw, "")
        clean2 = clean2.replace(sw, "")

    if not clean1 or not clean2:
        return 0.0
    if clean1 in clean2 or clean2 in clean1:
        return 1.0

    bg1 = set(clean1[i : i + 2] for i in range(len(clean1) - 1))
    bg2 = set(clean2[i : i + 2] for i in range(len(clean2) - 1))
    if not bg1 or not bg2:
        return 0.0
    return round(len(bg1 & bg2) / len(bg1 | bg2), 3)


def are_events_duplicate(item_a: Dict[str, Any], item_b: Dict[str, Any]) -> bool:
    """
    同场馆同活动智能去重判定：
    1. 场馆距离 <= 0.35km（允许 ±200m 防重叠抖动）或同区同具体地址
    2. 时间段重叠（两者的起止区间非互斥）
    3. 标题核心关键词 2-gram 相似度 >= 0.35 或相互包含
    """
    dist_km = haversine_km(item_a["lng"], item_a["lat"], item_b["lng"], item_b["lat"])
    generic_addrs = {
        "南京", "南京市", "江苏南京", "主城区", "线上", "同城", "南京同城",
        "全国", "线上app/全国通用", "线上app", "线上活动", "江苏省南京市"
    }
    addr_a = (item_a.get("address") or "").strip()
    addr_b = (item_b.get("address") or "").strip()
    same_address = False
    if len(addr_a) >= 4 and len(addr_b) >= 4:
        if addr_a.lower() not in generic_addrs and addr_b.lower() not in generic_addrs:
            same_address = (addr_a in addr_b) or (addr_b in addr_a)

    same_venue = (
        dist_km <= 0.35 and item_a.get("district") == item_b.get("district")
    ) or same_address
    if not same_venue:
        return False

    today_iso = datetime.date.today().isoformat()
    s_a = (item_a.get("start_date") or item_a.get("start_time") or today_iso)[:10]
    e_a = (item_a.get("end_date") or item_a.get("end_time") or today_iso)[:10]
    s_b = (item_b.get("start_date") or item_b.get("start_time") or today_iso)[:10]
    e_b = (item_b.get("end_date") or item_b.get("end_time") or today_iso)[:10]
    if e_a < s_b or e_b < s_a:
        return False

    sim = title_similarity_cjk(item_a.get("title", ""), item_b.get("title", ""))
    return sim >= 0.35


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
    category: str,
    sub_category: str,
    district: str,
    is_free: bool,
    platform: str,
    address: str,
    title: str = "",
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
    # 江北新区核心商圈与国家级新区自动聚类识别
    full_str = f"{address} {title}"
    if any(k in full_str for k in ["江北", "江北新区", "浦口", "研创园", "弘阳广场", "桥北", "南京北站", "扬子江"]):
        if "江北新区" not in tags:
            tags.append("江北新区")
    return tags


def haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """计算两个 GCJ-02 坐标点之间的球面距离（单位：公里），等价于 PostGIS ST_DistanceSphere"""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return round(2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def bounding_box_deg(lat: float, lng: float, radius_km: float) -> Tuple[float, float, float, float]:
    """计算中心点经纬度在给定半径 (公里) 下的包围盒 (min_lat, max_lat, min_lng, max_lng)"""
    dlat = radius_km / 111.0
    rad_lat = math.radians(lat)
    cos_lat = math.cos(rad_lat)
    if cos_lat < 0.001:
        cos_lat = 0.001
    dlng = radius_km / (111.0 * cos_lat)
    return round(lat - dlat, 6), round(lat + dlat, 6), round(lng - dlng, 6), round(lng + dlng, 6)


def get_db_connection(db_path: Path = SQLITE_PATH) -> sqlite3.Connection:
    """获取优化配置后的 SQLite 连接（WAL 模式 + 内存临时表 + 5s 忙锁等待）"""
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA cache_size = -64000;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn


def ensure_nj_events_table(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nj_events (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            category        TEXT NOT NULL,
            sub_category    TEXT NOT NULL,
            start_date      TEXT,
            end_date        TEXT,
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
            extra_sources   TEXT DEFAULT '[]',
            updated_at      TEXT NOT NULL
        )
        """
    )
    # 动态检查并兼容添加新字段
    existing_cols = [c[1] for c in conn.execute("PRAGMA table_info(nj_events)").fetchall()]
    if "start_date" not in existing_cols:
        conn.execute("ALTER TABLE nj_events ADD COLUMN start_date TEXT")
    if "end_date" not in existing_cols:
        conn.execute("ALTER TABLE nj_events ADD COLUMN end_date TEXT")
    if "extra_sources" not in existing_cols:
        conn.execute("ALTER TABLE nj_events ADD COLUMN extra_sources TEXT DEFAULT '[]'")

    # 创建 6 大时空与核心查询索引
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nj_events_district ON nj_events(district);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nj_events_category ON nj_events(category);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nj_events_status ON nj_events(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nj_events_coords ON nj_events(lat, lng);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nj_events_updated ON nj_events(updated_at DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nj_events_is_free ON nj_events(is_free);")
    conn.commit()


def migrate_and_sync_all() -> List[Dict[str, Any]]:
    """
    将 nanjing_deals_events 与 Obsidian 笔记全量同步升级至 nj_events 表：
    1. 解析生命周期精确起止日期 (start_date / end_date)
    2. 智能聚合去重 (Deduplication)：同场馆同时间段多笔记聚合为主条目，其余追加至 extra_sources
    3. 把 district / lng / lat / sub_category / start_date / end_date 写回每篇 Obsidian .md 的 YAML 属性
    4. 采用安全增量 Upsert 事务，严禁无条件删库或因外部文件丢失而连带删库。
    """
    conn = get_db_connection(SQLITE_PATH)
    ensure_nj_events_table(conn)

    vault_accessible = VAULT_DIR.exists()
    if not vault_accessible:
        print(f"[!] Warning: VAULT_DIR ({VAULT_DIR}) 不存在或脱机，跳过本地 Markdown 检查与回写，完全基于 SQLite 现有数据安全同步。")

    rows = conn.execute("SELECT * FROM nanjing_deals_events ORDER BY publish_date DESC").fetchall()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_candidates: List[Dict[str, Any]] = []
    seen_paths = set()
    seen_titles = set()
    noise_keywords = ("赵露思", "横店开机", "上海好物", "机器压平", "全国展会2026排期表(10-12月)", "盒马新疆季")

    for r in rows:
        d = dict(r)
        post_id = d["post_id"]
        title = d["title"]
        obsidian_path = d.get("obsidian_path") or ""
        md_file = VAULT_DIR / obsidian_path

        # 仅清理明确命中的非南京无意义纯噪声
        if any(nk in title for nk in noise_keywords):
            conn.execute("DELETE FROM nanjing_deals_events WHERE post_id = ?", (post_id,))
            if vault_accessible and md_file.exists():
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
        event_time_text = d.get("event_time") or "近期同城"
        address = d.get("location") or "南京主城区"
        benefit = d.get("benefit") or "免费/详见攻略"
        action_guide = d.get("action_guide") or "见要点说明"
        summary = d.get("summary") or title
        platform = d.get("platform") or "微信公众号"
        author = d.get("author") or "南京同城"
        publish_date = d.get("publish_date") or now_str[:10]
        source_url = d.get("url") or f"https://local.nanjing/{post_id}"
        obsidian_path = d.get("obsidian_path") or ""
        status = d.get("status") or "待去/待薅"

        # 安全读取 Obsidian 笔记（如 Vault 可访问且文件存在），绝不因文件缺失而删库
        key_points: List[str] = []
        if vault_accessible and md_file.exists():
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
        if not is_in_nanjing_bounds(lng, lat):
            base_lng, base_lat = NANJING_DISTRICTS.get(district, NANJING_DISTRICTS["玄武区"])
            dx, dy = _deterministic_jitter(post_id or title)
            lng, lat = round(base_lng + dx, 6), round(base_lat + dy, 6)
            geo_src = f"{geo_src}_bounded"

        sub_cat = infer_sub_category(category, title, benefit, summary)
        start_date, end_date, start_iso, end_iso = parse_lifecycle_dates(event_time_text, publish_date)
        is_free, price_num = extract_price_and_free(benefit, title, summary)
        tags_list = build_tags(category, sub_cat, district, is_free, platform, address, title)
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

        # 仅在 Vault 存在且文件可写时同步回写 YAML
        if vault_accessible and md_file.exists():
            try:
                txt = md_file.read_text(encoding="utf-8")
                m_yaml = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", txt, re.S)
                if m_yaml:
                    fm = yaml.safe_load(m_yaml.group(1)) or {}
                    body = m_yaml.group(2)
                    fm["district"] = district
                    fm["sub_category"] = sub_cat
                    fm["start_date"] = start_date
                    fm["end_date"] = end_date
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

        raw_candidates.append(
            {
                "id": post_id,
                "post_id": post_id,
                "title": title,
                "category": category,
                "sub_category": sub_cat,
                "start_date": start_date,
                "end_date": end_date,
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
                "extra_sources": [],
                "updated_at": now_str,
            }
        )

    # 智能多笔记聚合去重 (Deduplication)
    deduped_items: List[Dict[str, Any]] = []
    for cand in raw_candidates:
        matched = False
        for primary in deduped_items:
            if are_events_duplicate(primary, cand):
                matched = True
                source_meta = {
                    "post_id": cand["id"],
                    "title": cand["title"],
                    "platform": cand.get("platform", "微信公众号"),
                    "author": cand.get("author", "南京本地"),
                    "source_url": cand.get("source_url", ""),
                    "obsidian_path": cand.get("obsidian_path", ""),
                    "obsidian_uri": cand.get("obsidian_uri", ""),
                    "benefit": cand.get("benefit", ""),
                    "publish_date": cand.get("publish_date", ""),
                }
                primary.setdefault("extra_sources", []).append(source_meta)

                for kp in cand.get("key_points", []):
                    if kp not in primary["key_points"]:
                        primary["key_points"].append(kp)
                for tg in cand.get("tags", []):
                    if tg not in primary["tags"]:
                        primary["tags"].append(tg)
                break

        if not matched:
            cand.setdefault("extra_sources", [])
            deduped_items.append(cand)

    # 安全事务写入 SQLite nj_events (基于 Upsert，杜绝数据清空断档)
    with conn:
        for it in deduped_items:
            # 先行清理同 ID 或同 URL 的历史记录，彻底规避双唯一约束冲突
            conn.execute("DELETE FROM nj_events WHERE id = ? OR source_url = ?", (it["id"], it["source_url"]))
            conn.execute(
                """
                INSERT INTO nj_events (
                    id, title, category, sub_category, start_date, end_date, start_time, end_time,
                    event_time_text, district, address, lng, lat, geom, benefit, is_free, action_guide,
                    summary, tags, extra_info, source_url, obsidian_path, status, extra_sources, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_url) DO UPDATE SET
                    title=excluded.title,
                    category=excluded.category,
                    sub_category=excluded.sub_category,
                    start_date=excluded.start_date,
                    end_date=excluded.end_date,
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
                    extra_sources=excluded.extra_sources,
                    updated_at=excluded.updated_at
                """,
                (
                    it["id"],
                    it["title"],
                    it["category"],
                    it["sub_category"],
                    it["start_date"],
                    it["end_date"],
                    it["start_time"],
                    it["end_time"],
                    it["event_time_text"],
                    it["district"],
                    it["address"],
                    it["lng"],
                    it["lat"],
                    it["geom"],
                    it["benefit"],
                    1 if it["is_free"] else 0,
                    it["action_guide"],
                    it["summary"],
                    json.dumps(it["tags"], ensure_ascii=False),
                    json.dumps(it["extra_info"], ensure_ascii=False),
                    it["source_url"],
                    it["obsidian_path"],
                    it["status"],
                    json.dumps(it["extra_sources"], ensure_ascii=False),
                    now_str,
                ),
            )

    conn.close()
    return deduped_items


if __name__ == "__main__":
    import social_obsidian_sync
    items = migrate_and_sync_all()
    social_obsidian_sync.ObsidianSummaryDB().build_base_and_dashboard()
    print(f"[✓] 已同步生成 nj_events 空间数据表，共 {len(items)} 条南京活动/展会/羊毛记录（含南京11区划与 GCJ-02 经纬度）：")
    for it in items:
        print(f"  - [{it['district']:<4}] ({it['lng']:.6f}, {it['lat']:.6f}) | {it['category']} | {it['sub_category']} | {it['title']}")
