#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南京地区同城活动抓取与时空可视化系统 生产级高性能后端服务 (dashboard_server.py)
监听地址: 0.0.0.0:8765 (支持本地与全局域网设备跨端实时访问)
核心架构升级 (v2.5.0-enterprise):
  1. 活动生命周期引擎 (Lifecycle Engine)：
     - 结构化提取 start_date 与 end_date (YYYY-MM-DD)
     - 动态计算 days_left 与 time_status ('upcoming' / 'ongoing' / 'ending_soon' / 'expired')
     - 默认自动过滤已结束 (expired) 活动，支持 include_expired=1 与 time_status 过滤
  2. 同场馆同活动智能去重与多笔记聚合 (Deduplication)：
     - 聚合命中同场馆坐标 + 时间窗口重叠 + 标题核心相似的多篇笔记
     - 汇总为单一主条目并在 extra_sources 中返回所有原笔记与链接
  3. 原生 Apple 日历订阅接口 (RFC 5545 iCalendar)：
     - GET /api/events/calendar.ics，供 iOS / macOS 系统原生实时订阅“待去/待薅”日历
  4. 单条活动快速智能剪藏接口：
     - POST /api/events/clip，接收社媒文本秒级智能提炼、落库与 Obsidian 原子同步
  5. 内存级线程安全事件缓存 (TTL 15s + 事件驱动主动失效)
  6. 完整 CORS 全开放跨域支持 (Origin: *, Preflight 204)
"""

import calendar
import datetime
import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse

import yaml

import nanjing_lbs_engine
import social_obsidian_sync

# 核心路径配置 (解耦环境变量与跨平台支持，支持 Docker 容器化挂载)
BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent))
SQLITE_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "local.db"))
VAULT_DIR = Path(os.environ.get("VAULT_DIR", r"E:\Note storage\IOT"))
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", BASE_DIR / "frontend" / "dist"))
SYNC_SCRIPT = Path(os.environ.get("SYNC_SCRIPT", BASE_DIR / "social_obsidian_sync.py"))

SERVER_START_TIME = time.time()
SERVER_VERSION = "2.5.0-enterprise"

# 安全与流量防护配置
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB 请求体上限，防 DoS OOM 攻击
MAX_IMAGE_PROXY_BYTES = 10 * 1024 * 1024  # 10MB 图片代理抓取上限
API_TOKEN = os.environ.get("DASHBOARD_API_TOKEN", "").strip()
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    if o.strip()
]

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """严格阻断 HTTP 301/302 重定向，防止利用开放重定向绕过 SSRF 白名单逃逸至内网"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

IMAGE_PROXY_OPENER = urllib.request.build_opener(NoRedirectHandler)

# 并发同步节流互斥锁
SYNC_MUTEX = threading.Lock()
LAST_SYNC_TIME = 0.0


def safe_float(val: Any, default: float, name: str = "") -> Tuple[float, Optional[str]]:
    if val is None or val == "":
        return default, None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default, f"参数 '{name}' 必须为有限有效数值 (当前值: '{val}')"
        return f, None
    except (ValueError, TypeError):
        return default, f"参数 '{name}' 必须为有效浮点数 (当前值: '{val}')"


def safe_int(val: Any, default: int, name: str = "") -> Tuple[int, Optional[str]]:
    if val is None or val == "":
        return default, None
    try:
        return int(val), None
    except (ValueError, TypeError):
        return default, f"参数 '{name}' 必须为有效整数 (当前值: '{val}')"

ALL_11_DISTRICTS = [
    "玄武区",
    "秦淮区",
    "建邺区",
    "鼓楼区",
    "栖霞区",
    "雨花台区",
    "江宁区",
    "浦口区",
    "六合区",
    "溧水区",
    "高淳区",
    "全城通用",
]

EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff\u2600-\u27bf\ufe0f]+")


def clean_text(val: Any) -> str:
    if not val:
        return ""
    return EMOJI_RE.sub("", str(val)).strip()


def extract_short_title(title: str) -> str:
    """提取 4~8 字精炼短标题，通用分词无硬编码特判，严格遵循词边界"""
    if not title:
        return "同城活动"
    t = clean_text(title)
    # 1. 去除无实质意义的括号内容 (如 "(南京)", "【南京】", "（第二期）")
    t = re.sub(r"[\(（【\[][^\)）】\]]*[\)）】\]]", " ", t)
    # 2. 去除年份、行政区、通用行政组织与前缀
    t = re.sub(r"^(?:202[4-9]年?|南京(?:市)?|华东|首届|第[一二三四五六七八九十0-9]+届|中国(?:\(南京\))?)", "", t).strip()
    # 3. 去除前缀营销词与分隔符 (如 "重磅|", "必看·", "速领！")
    t = re.sub(r"^[^\s|｜:：!！·]{1,6}[|｜:：!！·]\s*", "", t).strip()
    # 4. 按常见分隔符切分第一核心段落
    parts = [p.strip() for p in re.split(r"[|｜:：!！·\s\-_—/]+", t) if p.strip()]
    candidate = parts[0] if parts else t
    if len(candidate) < 2 and len(parts) > 1:
        candidate = parts[1]
    # 5. 长度规范：最多 8 字符，若截断落在英文词中则安全回退
    if len(candidate) > 8:
        if bool(re.search(r"[a-zA-Z]", candidate[7:9])):
            sub = candidate[:8]
            m = re.search(r"[a-zA-Z]+$", sub)
            if m and m.start() >= 3:
                candidate = sub[:m.start()]
            else:
                candidate = sub
        else:
            candidate = candidate[:8]
    return candidate.strip() or "同城活动"


# ==============================================================================
# 1. 监控与指标度量 (Metrics Tracker)
# ==============================================================================
class MetricsTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.status_updates = 0
        self.sync_jobs_count = 0
        self.clips_count = 0

    def record_request(self):
        with self._lock:
            self.total_requests += 1

    def record_cache_hit(self):
        with self._lock:
            self.cache_hits += 1

    def record_cache_miss(self):
        with self._lock:
            self.cache_misses += 1

    def record_status_update(self):
        with self._lock:
            self.status_updates += 1

    def record_sync_job(self):
        with self._lock:
            self.sync_jobs_count += 1

    def record_clip(self):
        with self._lock:
            self.clips_count += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            hit_rate = 0.0
            total_cache_queries = self.cache_hits + self.cache_misses
            if total_cache_queries > 0:
                hit_rate = round(self.cache_hits / total_cache_queries * 100, 2)
            return {
                "total_requests": self.total_requests,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate_pct": hit_rate,
                "status_updates": self.status_updates,
                "sync_jobs_count": self.sync_jobs_count,
                "clips_count": self.clips_count,
            }


METRICS = MetricsTracker()


# ==============================================================================
# 2. 统计计算器 (Compute Stats)
# ==============================================================================
def get_fallback_dates(now_date: Optional[datetime.date] = None) -> Tuple[str, str]:
    """根据当前运行时动态计算兜底的起止日期区间 (当前自然月第一天与最后一天)"""
    d = now_date or datetime.date.today()
    s = d.isoformat()
    _, last_day = calendar.monthrange(d.year, d.month)
    e = f"{d.year}-{d.month:02d}-{last_day:02d}"
    return s, e


def compute_stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成统计分析所需的南京 11 区密度、类别占比、福利结构、生命周期分布与时间轴数据"""
    dist_counts = {d: 0 for d in ALL_11_DISTRICTS}
    cat_counts: Dict[str, int] = {"南京展会": 0, "南京活动": 0, "羊毛福利": 0}
    sub_cat_counts: Dict[str, int] = {}
    date_counts: Dict[str, int] = {}
    lifecycle_counts: Dict[str, int] = {
        "upcoming": 0,
        "ongoing": 0,
        "ending_soon": 0,
        "expired": 0,
    }
    free_count = 0
    coupon_count = 0
    paid_count = 0
    today_iso = datetime.date.today().isoformat()

    for it in items:
        d = it.get("district") or "玄武区"
        dist_counts[d] = dist_counts.get(d, 0) + 1
        c = clean_text(it.get("category") or "南京活动")
        cat_counts[c] = cat_counts.get(c, 0) + 1
        sc = clean_text(it.get("sub_category") or "综合")
        sub_cat_counts[sc] = sub_cat_counts.get(sc, 0) + 1
        pdate = (it.get("publish_date") or today_iso)[-5:]
        date_counts[pdate] = date_counts.get(pdate, 0) + 1

        ts = it.get("time_status") or "ongoing"
        lifecycle_counts[ts] = lifecycle_counts.get(ts, 0) + 1

        btxt = it.get("benefit") or ""
        if any(k in btxt for k in ["免费", "免票"]):
            free_count += 1
        elif any(k in btxt for k in ["立减", "消费券", "0元", "0.01", "羊毛", "打卡", "礼"]):
            coupon_count += 1
        else:
            paid_count += 1

    return {
        "total": len(items),
        "districts": [
            {
                "name": k,
                "value": v,
                "center": nanjing_lbs_engine.NANJING_DISTRICTS.get(k, (118.7842, 32.0418)),
            }
            for k, v in dist_counts.items()
        ],
        "categories": [{"name": k, "value": v} for k, v in cat_counts.items()],
        "sub_categories": [{"name": k, "value": v} for k, v in sub_cat_counts.items()],
        "lifecycle": [
            {"name": "即将截止 (剩≤3天)", "key": "ending_soon", "value": lifecycle_counts["ending_soon"]},
            {"name": "火热进行中", "key": "ongoing", "value": lifecycle_counts["ongoing"]},
            {"name": "即将开始", "key": "upcoming", "value": lifecycle_counts["upcoming"]},
            {"name": "已结束", "key": "expired", "value": lifecycle_counts["expired"]},
        ],
        "benefits": [
            {"name": "免费免票入场", "value": free_count},
            {"name": "立减消费券与羊毛", "value": coupon_count},
            {"name": "预约或早鸟购票", "value": paid_count},
        ],
        "timeline": [{"date": k, "count": v} for k, v in sorted(date_counts.items())],
    }


def to_geojson_feature_collection(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """将活动列表组装为标准 PostGIS ST_AsGeoJSON 兼容的 FeatureCollection"""
    features = []
    for it in items:
        props = {k: v for k, v in it.items() if k != "geom"}
        features.append(
            {
                "type": "Feature",
                "id": it["id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [it["lng"], it["lat"]],
                },
                "properties": props,
            }
        )
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "GCJ-02"}},
        "count": len(features),
        "features": features,
    }


# ==============================================================================
# 3. 线程安全高性能事件缓存管理器 (Event Cache Manager)
# ==============================================================================
class EventCacheManager:
    """
    内存级事件高速缓存：
    - TTL 设定为 15 秒（兼顾实时性与极速响应）
    - 提供 O(1) 字典检索 (id_map)
    - 动态挂载生命周期倒计时 (days_left / time_status)
    - 当状态变更、同步完成、新剪藏产生时主动触发 invalidate()
    """

    def __init__(self, ttl: float = 15.0):
        self.ttl = ttl
        self._lock = threading.RLock()
        self._timestamp: float = 0.0
        self._items: List[Dict[str, Any]] = []
        self._id_map: Dict[str, Dict[str, Any]] = {}
        self._stats: Optional[Dict[str, Any]] = None
        self._geojson: Optional[Dict[str, Any]] = None

    def invalidate(self) -> None:
        with self._lock:
            self._timestamp = 0.0

    def get_all(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        now = time.time()
        with self._lock:
            if not force_refresh and (now - self._timestamp < self.ttl) and self._items:
                METRICS.record_cache_hit()
                return self._items

            METRICS.record_cache_miss()
            self._load_from_storage()
            return self._items

    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        self.get_all()
        with self._lock:
            return self._id_map.get(item_id)

    def get_stats(self) -> Dict[str, Any]:
        self.get_all()
        with self._lock:
            if self._stats is None:
                self._stats = compute_stats(self._items)
            return self._stats

    def get_geojson(self) -> Dict[str, Any]:
        self.get_all()
        with self._lock:
            if self._geojson is None:
                self._geojson = to_geojson_feature_collection(self._items)
            return self._geojson

    def get_info(self) -> Dict[str, Any]:
        with self._lock:
            age = round(time.time() - self._timestamp, 2) if self._timestamp > 0 else -1.0
            return {
                "count": len(self._items),
                "age_seconds": age,
                "ttl_seconds": self.ttl,
                "is_warm": self._timestamp > 0 and (time.time() - self._timestamp < self.ttl),
            }

    def _load_from_storage(self) -> None:
        """
        从 SQLite 高性能装载全量结构化数据：
        纯基于 SQLite 本地数据库索引查询，彻底消除在锁内逐个读写磁盘 Markdown 文件的性能阻塞与雪崩风险。
        """
        if not SQLITE_PATH.exists():
            with self._lock:
                self._items = []
                self._id_map = {}
                self._stats = None
                self._geojson = None
                self._timestamp = time.time()
            return

        conn = nanjing_lbs_engine.get_db_connection(SQLITE_PATH)
        nanjing_lbs_engine.ensure_nj_events_table(conn)
        try:
            rows = conn.execute("SELECT * FROM nj_events ORDER BY updated_at DESC").fetchall()
        finally:
            conn.close()

        if not rows:
            new_items = nanjing_lbs_engine.migrate_and_sync_all()
            new_id_map = {it["id"]: it for it in new_items}
            new_stats = compute_stats(new_items)
            new_geojson = to_geojson_feature_collection(new_items)
            with self._lock:
                self._items = new_items
                self._id_map = new_id_map
                self._stats = new_stats
                self._geojson = new_geojson
                self._timestamp = time.time()
            return

        items: List[Dict[str, Any]] = []
        id_map: Dict[str, Dict[str, Any]] = {}
        today = datetime.date.today()

        for r in rows:
            d = dict(r)
            obs_path = d.get("obsidian_path", "")
            extra: Dict[str, Any] = {}
            try:
                extra = json.loads(d.get("extra_info") or "{}")
            except Exception:
                extra = {}
            tags: List[str] = []
            try:
                tags = json.loads(d.get("tags") or "[]")
            except Exception:
                tags = []
            extra_sources: List[Dict[str, Any]] = []
            try:
                extra_sources = json.loads(d.get("extra_sources") or "[]")
            except Exception:
                extra_sources = []

            key_points = extra.get("key_points") or []
            status = d.get("status") or "待去/待薅"
            event_time_text = clean_text(d.get("event_time_text") or "")
            publish_date = extra.get("publish_date") or today.isoformat()

            # 提取与计算生命周期起止日期及倒计时
            start_date = d.get("start_date") or ""
            end_date = d.get("end_date") or ""
            if not start_date or not end_date:
                start_date, end_date, _, _ = nanjing_lbs_engine.parse_lifecycle_dates(
                    event_time_text, publish_date
                )
            days_left, time_status = nanjing_lbs_engine.compute_lifecycle(
                start_date, end_date, now_date=today
            )

            item = {
                "id": d["id"],
                "post_id": d["id"],
                "title": clean_text(d["title"]),
                "short_title": extract_short_title(d["title"]),
                "category": clean_text(d["category"]),
                "sub_category": clean_text(d.get("sub_category") or "综合"),
                "start_date": start_date,
                "end_date": end_date,
                "days_left": days_left,
                "time_status": time_status,
                "start_time": d.get("start_time") or "",
                "end_time": d.get("end_time") or "",
                "event_time": event_time_text,
                "event_time_text": event_time_text,
                "district": clean_text(d.get("district") or "玄武区"),
                "address": clean_text(d.get("address") or ""),
                "location": clean_text(d.get("address") or ""),
                "lng": float(d.get("lng") or 118.7977),
                "lat": float(d.get("lat") or 32.0482),
                "geom": d.get("geom") or "",
                "benefit": clean_text(d.get("benefit") or ""),
                "is_free": bool(d.get("is_free", 1)),
                "action_guide": clean_text(d.get("action_guide") or ""),
                "summary": clean_text(d.get("summary") or ""),
                "tags": [clean_text(t) for t in tags if clean_text(t)],
                "extra_info": extra,
                "platform": clean_text(extra.get("platform") or "微信公众号"),
                "author": clean_text(extra.get("author") or "南京本地"),
                "publish_date": publish_date,
                "key_points": [clean_text(kp) for kp in key_points if clean_text(kp)] or [clean_text(d.get("summary") or "")],
                "source_url": d.get("source_url") or "",
                "url": d.get("source_url") or "",
                "obsidian_path": obs_path,
                "obsidian_uri": f"obsidian://open?vault=IOT&file={quote(obs_path)}",
                "status": clean_text(status),
                "extra_sources": extra_sources,
                "updated_at": d.get("updated_at") or "",
            }
            items.append(item)
            id_map[item["id"]] = item

        computed_stats = compute_stats(items)
        computed_geojson = to_geojson_feature_collection(items)

        # 最小化锁持有窗口：在完成全部内存运算后快速切换引用指针
        with self._lock:
            self._items = items
            self._id_map = id_map
            self._stats = computed_stats
            self._geojson = computed_geojson
            self._timestamp = time.time()


EVENT_CACHE = EventCacheManager(ttl=15.0)


def get_all_events() -> List[Dict[str, Any]]:
    """便捷外部调用方法：获取全量事件列表"""
    return EVENT_CACHE.get_all()


# ==============================================================================
# 4. 异步任务管理器 (Background Sync & Scraping Manager)
# ==============================================================================
class SyncTaskManager:
    """负责执行爬虫与数据库同步的后台线程池管理器"""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="nj_sync")
        self._lock = threading.Lock()
        self._current_job: Dict[str, Any] = {
            "job_id": None,
            "status": "idle",
            "type": None,
            "start_time": None,
            "end_time": None,
            "duration_sec": 0.0,
            "message": "暂无运行中的任务",
            "error": None,
            "items_count": 0,
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            snap = dict(self._current_job)
            if snap["status"] == "running" and snap["start_time"]:
                st = datetime.datetime.fromisoformat(snap["start_time"]).timestamp()
                snap["duration_sec"] = round(time.time() - st, 1)
            return snap

    def submit_job(self, mode: str = "incremental", keyword: str = "", limit: int = 2) -> Dict[str, Any]:
        with self._lock:
            if self._current_job["status"] == "running":
                return {
                    "ok": False,
                    "error": "已有同步或采集任务正在运行中，请等待其完成",
                    "job": dict(self._current_job),
                }

            job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            start_iso = datetime.datetime.now().isoformat()
            self._current_job = {
                "job_id": job_id,
                "status": "running",
                "type": mode,
                "start_time": start_iso,
                "end_time": None,
                "duration_sec": 0.0,
                "message": f"任务已启动 ({mode})",
                "error": None,
                "items_count": 0,
            }
            METRICS.record_sync_job()

        self._executor.submit(self._worker, job_id, mode, keyword, limit)
        return {
            "ok": True,
            "message": "同步任务已成功提交至后台",
            "job_id": job_id,
            "status": "running",
        }

    def _worker(self, job_id: str, mode: str, keyword: str, limit: int) -> None:
        t0 = time.time()
        timeout_sec = int(os.environ.get("SYNC_SUBPROCESS_TIMEOUT", "180"))
        try:
            if mode == "full" or keyword:
                cmd = [sys.executable, str(SYNC_SCRIPT), "--limit", str(limit)]
                if keyword:
                    cmd.extend(["--keyword", keyword])
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout_sec
                )
                if proc.returncode != 0:
                    err_snippet = (proc.stderr or proc.stdout or "").strip()[-300:]
                    print(f"[!] Warning: 抓取子进程退出码非零 ({proc.returncode}): {err_snippet}", flush=True)

            nanjing_lbs_engine.migrate_and_sync_all()
            EVENT_CACHE.invalidate()
            items = EVENT_CACHE.get_all(force_refresh=True)

            with self._lock:
                self._current_job.update(
                    {
                        "status": "completed",
                        "end_time": datetime.datetime.now().isoformat(),
                        "duration_sec": round(time.time() - t0, 2),
                        "message": f"同步完成，共更新入库 {len(items)} 条活动",
                        "items_count": len(items),
                        "error": None,
                    }
                )
        except Exception as e:
            err_msg = str(e)
            if isinstance(e, subprocess.TimeoutExpired):
                err_msg = f"抓取子进程执行超时 ({timeout_sec}秒)"
            with self._lock:
                self._current_job.update(
                    {
                        "status": "failed",
                        "end_time": datetime.datetime.now().isoformat(),
                        "duration_sec": round(time.time() - t0, 2),
                        "message": f"任务执行失败: {err_msg}",
                        "error": err_msg,
                    }
                )


SYNC_MANAGER = SyncTaskManager()


# ==============================================================================
# 5. 内置每日 12:00 定时抓取调度器 (Daily 12:00 Scheduler)
# ==============================================================================
class DailyScheduler(threading.Thread):
    """
    内置每日定时抓取调度器：
    每天 12:00:00 自动触发全量社媒活动爬取、LBS空间库同步与缓存预热
    """

    def __init__(self, target_hour: int = 12, target_minute: int = 0):
        super().__init__(daemon=True, name="DailySchedulerThread")
        self.target_hour = target_hour
        self.target_minute = target_minute
        self.last_run_time: Optional[str] = None
        self.next_run_dt: datetime.datetime = self._calc_next_run()

    def _calc_next_run(self) -> datetime.datetime:
        now = datetime.datetime.now()
        target = now.replace(
            hour=self.target_hour, minute=self.target_minute, second=0, microsecond=0
        )
        if target <= now:
            target += datetime.timedelta(days=1)
        return target

    def get_info(self) -> Dict[str, Any]:
        now = datetime.datetime.now()
        sec_left = max(0, int((self.next_run_dt - now).total_seconds()))
        return {
            "enabled": True,
            "cron_time": f"{self.target_hour:02d}:{self.target_minute:02d}",
            "next_run": self.next_run_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "last_run": self.last_run_time,
            "seconds_until_next_run": sec_left,
        }

    def run(self) -> None:
        while True:
            try:
                now = datetime.datetime.now()
                if now >= self.next_run_dt:
                    self.last_run_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        f"[{self.last_run_time}] [DailyScheduler] 触发每日 {self.target_hour:02d}:{self.target_minute:02d} 定时抓取与同步...",
                        flush=True,
                    )
                    SYNC_MANAGER.submit_job(mode="full", limit=3)
                    self.next_run_dt = self._calc_next_run()
            except Exception as e:
                print(f"[DailyScheduler] 定时调度运行异常 (已自动恢复守护): {e}", flush=True)
            time.sleep(20)


DAILY_SCHEDULER = DailyScheduler(target_hour=12, target_minute=0)


# ==============================================================================
# 6. 原子化 Obsidian 与 SQLite 更新引擎 (Atomic Status Updater)
# ==============================================================================
def update_item_status(post_id: str, new_status: str) -> Tuple[bool, str]:
    """更新活动状态，原子化重写 Obsidian Markdown YAML 并主动失效缓存"""
    METRICS.record_status_update()
    conn = nanjing_lbs_engine.get_db_connection(SQLITE_PATH)
    try:
        row = conn.execute("SELECT obsidian_path FROM nj_events WHERE id = ?", (post_id,)).fetchone()
        if not row:
            row = conn.execute(
                "SELECT obsidian_path FROM nanjing_deals_events WHERE post_id = ?", (post_id,)
            ).fetchone()

        if not row:
            return False, "未找到对应的活动记录 (ID 不存在)"

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conn:
            conn.execute(
                "UPDATE nj_events SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, now_str, post_id),
            )
            conn.execute(
                "UPDATE nanjing_deals_events SET status = ? WHERE post_id = ?",
                (new_status, post_id),
            )
    finally:
        conn.close()

    obs_path = (row["obsidian_path"] or "").strip()
    if obs_path and VAULT_DIR.exists():
        try:
            resolved_vault = VAULT_DIR.resolve()
            safe_rel = obs_path.lstrip("/\\")
            md_file = (resolved_vault / safe_rel).resolve()
            # 严格防止路径逃逸（如 ../../windows 或 /etc/passwd）
            if md_file.is_relative_to(resolved_vault) and md_file.exists():
                txt = md_file.read_text(encoding="utf-8")
                m_yaml = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", txt, re.S)
                if m_yaml:
                    fm = yaml.safe_load(m_yaml.group(1)) or {}
                    body = m_yaml.group(2)
                    fm["status"] = new_status
                    fm["updated_at"] = now_str
                    new_yaml = yaml.safe_dump(
                        fm, allow_unicode=True, sort_keys=False, default_flow_style=False
                    ).strip()
                    new_content = f"---\n{new_yaml}\n---\n\n{body.lstrip()}"
                else:
                    new_content = f"---\nstatus: {new_status}\nupdated_at: '{now_str}'\n---\n\n{txt}"

                with tempfile.NamedTemporaryFile(
                    "w", dir=md_file.parent, delete=False, encoding="utf-8"
                ) as tf:
                    tf.write(new_content)
                    temp_name = tf.name
                os.replace(temp_name, md_file)
        except Exception:
            pass

    EVENT_CACHE.invalidate()
    return True, "状态更新成功"


# ==============================================================================
# 6. 单条活动快速智能剪藏引擎 (Event Clip Engine)
# ==============================================================================
def clip_event(payload: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    单条社媒笔记快速智能剪藏：
    1. 接收 title, raw_text, source_url
    2. 自动分类并提取时间、地点、门票、操作指南与要点
    3. 自动匹配南京地标并进行 GCJ-02 坐标编码
    4. 原子化写入 Obsidian Markdown 文件与 SQLite 双表
    5. 立即失效缓存并返回全新活动对象
    """
    METRICS.record_clip()
    title = clean_text(payload.get("title") or "")
    if not title:
        return False, "活动标题不能为空", None

    raw_text = payload.get("raw_text") or title
    source_url = (payload.get("source_url") or "").strip()
    category_hint = (payload.get("category") or "").strip()
    platform = clean_text(payload.get("platform") or "社媒剪藏")
    author = clean_text(payload.get("author") or "南京本地速递")
    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    publish_date = (payload.get("publish_date") or now_dt.strftime("%Y-%m-%d"))[:10]

    # 1. 自动分类与结构化干货提炼
    cat = social_obsidian_sync.classify_item(title, raw_text, hint_cat=category_hint)
    fields = social_obsidian_sync.extract_structured_fields(title, raw_text, cat, platform)
    event_time_text = fields.get("event_time") or "2026年近期"
    location = fields.get("location") or "南京市主城区"
    benefit = fields.get("benefit") or "详见要点"
    action_guide = fields.get("action_guide") or "免预约直接前往现场"
    summary = fields.get("summary") or title
    key_points = fields.get("key_points") or [summary]

    # 2. 空间地理编码与生命周期解析
    district, lng, lat, geo_src = nanjing_lbs_engine.geocode_nanjing(location, title, summary)
    sub_cat = nanjing_lbs_engine.infer_sub_category(cat, title, benefit, summary)
    start_date, end_date, start_iso, end_iso = nanjing_lbs_engine.parse_lifecycle_dates(
        event_time_text, publish_date
    )
    days_left, time_status = nanjing_lbs_engine.compute_lifecycle(start_date, end_date)
    is_free, price_num = nanjing_lbs_engine.extract_price_and_free(benefit, title, summary)
    tags_list = nanjing_lbs_engine.build_tags(cat, sub_cat, district, is_free, platform, location, title)
    geom_wkt = f"POINT({lng} {lat})"

    # 3. 生成全局唯一 post_id
    post_id = f"clip_{hashlib.md5((title + source_url + event_time_text).encode('utf-8')).hexdigest()[:12]}"
    if not source_url:
        source_url = f"https://local.nanjing/clip/{post_id}"

    # 4. 生成规范 Obsidian Markdown 文件 (原子写入，脱机时容错降级)
    safe_name = social_obsidian_sync.sanitize_filename(f"[{cat[2:] if len(cat) > 2 else cat}] {title}")
    rel_path = f"05_社媒情报库/{safe_name}.md"
    md_file = VAULT_DIR / rel_path

    fm_data = {
        "category": cat,
        "title": title,
        "event_time": event_time_text,
        "location": location,
        "district": district,
        "sub_category": sub_cat,
        "benefit": benefit,
        "action_guide": action_guide,
        "summary": summary,
        "start_date": start_date,
        "end_date": end_date,
        "lng": lng,
        "lat": lat,
        "is_free": is_free,
        "platform": platform,
        "author": author,
        "publish_date": publish_date,
        "status": "待去/待薅",
        "url": source_url,
        "updated_at": now_str,
    }
    yaml_header = yaml.safe_dump(
        fm_data, allow_unicode=True, sort_keys=False, default_flow_style=False
    ).strip()
    bullets_md = "\n".join(f"- {pt}" for pt in key_points)
    md_content = f"""---
{yaml_header}
---

# {title}

| 字段 | 提炼内容 |
| :--- | :--- |
| **🏷️ 情报类别** | `{cat}` · `{sub_cat}` |
| **⏰ 举办/截止时间** | **{event_time_text}** ({start_date} ~ {end_date}) |
| **📍 场馆/地点/渠道** | `{location}` ({district}) |
| **💰 门票/福利力度** | **{benefit}** |
| **🚀 参与/领取方式** | {action_guide} |
| **🌐 来源平台与账号** | {platform} · `{author}` |
| **🔗 原文报名/领券链接** | [点击直达原帖]({source_url}) |

## 📋 核心要点总结（AI 提炼）

{bullets_md}
"""
    if VAULT_DIR.exists():
        try:
            md_file.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", dir=md_file.parent, delete=False, encoding="utf-8") as tf:
                tf.write(md_content)
                temp_name = tf.name
            os.replace(temp_name, md_file)
        except Exception as e:
            print(f"[!] Warning: 剪藏写入 Obsidian Markdown 文件失败 ({e})，降级为仅入库 SQLite", flush=True)
    else:
        print("[!] Warning: VAULT_DIR 不存在或未挂载，跳过 Markdown 写入，直接存入 SQLite", flush=True)

    extra_obj = {
        "platform": platform,
        "author": author,
        "publish_date": publish_date,
        "key_points": key_points,
        "price_num": price_num,
        "geocode_source": geo_src,
        "likes": 0,
    }

    # 5. 双表安全事务入库
    conn = nanjing_lbs_engine.get_db_connection(SQLITE_PATH)
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO nanjing_deals_events
                (post_id, category, title, event_time, location, benefit, action_guide,
                 summary, platform, author, publish_date, likes, status, url, obsidian_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    cat,
                    title,
                    event_time_text,
                    location,
                    benefit,
                    action_guide,
                    summary,
                    platform,
                    author,
                    publish_date,
                    0,
                    "待去/待薅",
                    source_url,
                    rel_path,
                ),
            )

            # 先行清理同 ID 或同 URL 的历史记录，彻底规避双唯一约束冲突
            conn.execute("DELETE FROM nj_events WHERE id = ? OR source_url = ?", (post_id, source_url))
            conn.execute(
                """
                INSERT INTO nj_events (
                    id, title, category, sub_category, start_date, end_date, start_time, end_time,
                    event_time_text, district, address, lng, lat, geom, benefit, is_free, action_guide,
                    summary, tags, extra_info, source_url, obsidian_path, status, extra_sources, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    title,
                    cat,
                    sub_cat,
                    start_date,
                    end_date,
                    start_iso,
                    end_iso,
                    event_time_text,
                    district,
                    location,
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
                    rel_path,
                    "待去/待薅",
                    "[]",
                    now_str,
                ),
            )
    finally:
        conn.close()

    # 6. 失效缓存
    EVENT_CACHE.invalidate()
    new_event = EVENT_CACHE.get_by_id(post_id)
    return True, "活动已成功剪藏并同步至 Obsidian 与地图库", new_event


# ==============================================================================
# 7. Apple 日历订阅格式生成器 (RFC 5545 iCalendar Feed)
# ==============================================================================
def generate_ical_feed(events: List[Dict[str, Any]]) -> str:
    """生成原生兼容 iOS / macOS 日历的 RFC 5545 iCalendar 标准订阅流"""
    now_dt = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Nanjing Events LBS//Activity Calendar//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:南京待去与羊毛清单",
        "X-WR-CALDESC:南京同城活动、精选展会与羊毛福利订阅 (LBS Intelligence)",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "BEGIN:VTIMEZONE",
        "TZID:Asia/Shanghai",
        "X-LIC-LOCATION:Asia/Shanghai",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0800",
        "TZOFFSETTO:+0800",
        "TZNAME:CST",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for ev in events:
        ev_id = ev.get("id") or ev.get("post_id") or "event"
        title = clean_text(ev.get("title") or "未命名活动")
        venue = clean_text(ev.get("address") or ev.get("location") or "南京市")
        district = ev.get("district") or "玄武区"
        loc_str = f"{venue} ({district})" if district not in venue else venue

        benefit = ev.get("benefit") or "详见攻略"
        cat = ev.get("category") or "南京活动"
        sub_cat = ev.get("sub_category") or "综合"
        days_left = ev.get("days_left", 0)
        time_status = ev.get("time_status", "ongoing")
        status_cn = {
            "upcoming": f"即将开始 (剩 {days_left} 天)",
            "ending_soon": f"即将截止 (剩 {days_left} 天)",
            "ongoing": f"进行中 (剩 {days_left} 天)",
            "expired": "已结束",
        }.get(time_status, "")

        fb_s, fb_e = get_fallback_dates()
        s_date_raw = (ev.get("start_date") or fb_s)[:10].replace("-", "")
        e_date_raw = (ev.get("end_date") or fb_e)[:10].replace("-", "")
        dtstart = f"{s_date_raw}T090000"
        dtend = f"{e_date_raw}T180000"

        summary_txt = clean_text(ev.get("summary") or "")
        key_points = ev.get("key_points") or []
        obs_uri = ev.get("obsidian_uri") or ""
        src_url = ev.get("source_url") or ""

        desc_parts = [
            f"【{cat} · {sub_cat}】",
            f"时效状态: {status_cn}",
            f"门票福利: {benefit}",
            f"举办时间: {ev.get('event_time_text') or ev.get('event_time') or ''}",
            f"活动地点: {loc_str}",
            "",
            f"核心总结: {summary_txt}",
        ]
        if key_points:
            desc_parts.append("要点干货:")
            for kp in key_points[:4]:
                desc_parts.append(f"- {clean_text(kp)}")
        if obs_uri:
            desc_parts.append(f"\nObsidian 笔记: {obs_uri}")
        if src_url:
            desc_parts.append(f"原文链接: {src_url}")

        extra_sources = ev.get("extra_sources") or []
        if extra_sources:
            desc_parts.append(f"\n关联同场笔记 ({len(extra_sources)}篇):")
            for es in extra_sources:
                desc_parts.append(f"- {es.get('title')} ({es.get('platform')})")

        escaped_title = title.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
        escaped_loc = loc_str.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
        escaped_desc = "\\n".join(
            p.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,") for p in desc_parts
        )

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{ev_id}@nanjing-events-lbs",
                f"DTSTAMP:{now_dt}",
                f"DTSTART;TZID=Asia/Shanghai:{dtstart}",
                f"DTEND;TZID=Asia/Shanghai:{dtend}",
                f"SUMMARY:{'【免费】' if ev.get('is_free') else ''}{escaped_title}",
                f"LOCATION:{escaped_loc}",
                f"DESCRIPTION:{escaped_desc}",
                f"URL:{obs_uri or src_url}",
                f"CATEGORIES:{cat},{sub_cat}",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ==============================================================================
# 8. 多维空间过滤引擎 (Multi-dimensional Spatial Filter)
# ==============================================================================
def filter_events(items: List[Dict[str, Any]], query_params: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    高精度多维过滤引擎：
    - 支持分类 (category)、南京11区 (district)、状态 (status)、免费 (is_free)、标签 (tag)、全文检索 (q)
    - 动态按当日计算生命周期 (days_left / time_status)
    - 默认过滤 expired 已结束活动，除非显式传入 include_expired=1
    - 支持 time_status 过滤 ('ending_soon', 'ongoing', 'upcoming', 'expired')
    - 空间包围盒粗筛 + Haversine 精确距离计算
    - 排序处理 (sort_by: distance, days_left, updated_at, title; order: asc, desc)
    """
    today = datetime.date.today()
    cat = (query_params.get("category") or ["ALL"])[0]
    dist = (query_params.get("district") or ["ALL"])[0]
    status = (query_params.get("status") or ["ALL"])[0]
    is_free_str = (query_params.get("is_free") or [""])[0].lower()
    tag = (query_params.get("tag") or [""])[0].strip()
    q = (query_params.get("q") or [""])[0].strip().lower()

    include_expired = (query_params.get("include_expired") or ["0"])[0].lower() in ("1", "true", "yes")
    time_status_filter = (query_params.get("time_status") or ["ALL"])[0].strip().lower()

    center_lng_s = (query_params.get("lng") or [""])[0]
    center_lat_s = (query_params.get("lat") or [""])[0]
    radius_s = (query_params.get("radius_km") or ["0"])[0]

    use_spatial = False
    center_lng, center_lat, radius_km = 118.7842, 32.0418, 0.0
    min_lat, max_lat, min_lng, max_lng = -90.0, 90.0, -180.0, 180.0

    try:
        if center_lng_s and center_lat_s and float(radius_s) > 0:
            center_lng = float(center_lng_s)
            center_lat = float(center_lat_s)
            radius_km = float(radius_s)
            min_lat, max_lat, min_lng, max_lng = nanjing_lbs_engine.bounding_box_deg(
                center_lat, center_lng, radius_km
            )
            use_spatial = True
    except Exception:
        use_spatial = False

    sort_by = (query_params.get("sort_by") or [""])[0].strip().lower()
    order = (query_params.get("order") or ["asc"])[0].strip().lower()

    out: List[Dict[str, Any]] = []
    clean_cat = clean_text(cat)

    for it in items:
        # 1. 动态挂载/刷新生命周期状态
        fb_s, fb_e = get_fallback_dates(today)
        days_left, time_status = nanjing_lbs_engine.compute_lifecycle(
            it.get("start_date") or fb_s,
            it.get("end_date") or fb_e,
            now_date=today,
        )
        it_copy = dict(it)
        it_copy["days_left"] = days_left
        it_copy["time_status"] = time_status

        # 2. 过期自动过滤规则
        if not include_expired and time_status == "expired":
            continue

        # 3. 指定时间状态过滤
        if time_status_filter not in ("all", "") and time_status != time_status_filter:
            continue

        # 4. 常规维度过滤
        if clean_cat not in ("ALL", "") and clean_text(it_copy["category"]) != clean_cat:
            continue
        if dist not in ("ALL", "") and it_copy["district"] != dist:
            continue
        if status not in ("ALL", "") and it_copy["status"] != status:
            continue
        if is_free_str in ("1", "true", "yes") and not it_copy["is_free"]:
            continue
        if tag and tag not in it_copy.get("tags", []):
            continue

        # 5. 空间包围盒粗筛
        if use_spatial:
            if not (min_lat <= it_copy["lat"] <= max_lat and min_lng <= it_copy["lng"] <= max_lng):
                continue

        # 6. 全文检索
        if q:
            hay = " ".join(
                [
                    it_copy["title"],
                    it_copy["category"],
                    it_copy["sub_category"],
                    it_copy["district"],
                    it_copy["address"],
                    it_copy["benefit"],
                    it_copy["action_guide"],
                    it_copy["summary"],
                    it_copy["author"],
                    " ".join(it_copy.get("key_points") or []),
                ]
            ).lower()
            if q not in hay:
                continue

        d_km = nanjing_lbs_engine.haversine_km(center_lng, center_lat, it_copy["lng"], it_copy["lat"])
        if use_spatial and d_km > radius_km:
            continue

        it_copy["distance_km"] = d_km
        out.append(it_copy)

    # 排序处理
    if sort_by == "distance":
        out.sort(key=lambda x: x.get("distance_km", 9999.0), reverse=(order == "desc"))
    elif sort_by == "days_left":
        out.sort(key=lambda x: x.get("days_left", 9999), reverse=(order == "desc"))
    elif sort_by == "updated_at":
        out.sort(key=lambda x: x.get("updated_at", ""), reverse=(order == "desc"))
    elif sort_by == "title":
        out.sort(key=lambda x: x.get("title", ""), reverse=(order == "desc"))
    elif order in ("desc", "reverse", "逆序"):
        out.reverse()

    return out


# ==============================================================================
# 9. 参数化 SQLite 空间与多维检索引擎 (Indexed Query Engine)
# ==============================================================================
def query_events_from_db(query_params: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    通过参数化 SQL 查询直接命中 SQLite 索引（district, category, status, lat/lng 空间包围盒），
    大幅降低内存消耗并加速多维时空检索。
    """
    today = datetime.date.today()
    cat = (query_params.get("category") or ["ALL"])[0].strip()
    dist = (query_params.get("district") or ["ALL"])[0].strip()
    status = (query_params.get("status") or ["ALL"])[0].strip()
    is_free_str = (query_params.get("is_free") or [""])[0].lower()
    tag = (query_params.get("tag") or [""])[0].strip()
    q = (query_params.get("q") or [""])[0].strip()

    include_expired = (query_params.get("include_expired") or ["0"])[0].lower() in ("1", "true", "yes")
    time_status_filter = (query_params.get("time_status") or ["ALL"])[0].strip().lower()

    center_lng_s = (query_params.get("lng") or [""])[0]
    center_lat_s = (query_params.get("lat") or [""])[0]
    radius_s = (query_params.get("radius_km") or ["0"])[0]

    use_spatial = False
    center_lng, center_lat, radius_km = 118.7842, 32.0418, 0.0
    min_lat, max_lat, min_lng, max_lng = -90.0, 90.0, -180.0, 180.0

    try:
        if center_lng_s and center_lat_s and float(radius_s) > 0:
            center_lng = float(center_lng_s)
            center_lat = float(center_lat_s)
            radius_km = float(radius_s)
            min_lat, max_lat, min_lng, max_lng = nanjing_lbs_engine.bounding_box_deg(
                center_lat, center_lng, radius_km
            )
            use_spatial = True
    except Exception:
        use_spatial = False

    sort_by = (query_params.get("sort_by") or [""])[0].strip().lower()
    order = (query_params.get("order") or ["asc"])[0].strip().lower()

    sql_parts = ["SELECT * FROM nj_events WHERE 1=1"]
    sql_args: List[Any] = []

    clean_cat = clean_text(cat)
    if clean_cat and clean_cat != "ALL":
        sql_parts.append("AND category = ?")
        sql_args.append(clean_cat)
    if dist and dist != "ALL":
        sql_parts.append("AND district = ?")
        sql_args.append(dist)
    if status and status != "ALL":
        sql_parts.append("AND status = ?")
        sql_args.append(status)
    if is_free_str in ("1", "true", "yes"):
        sql_parts.append("AND is_free = 1")
    elif is_free_str in ("0", "false", "no"):
        sql_parts.append("AND is_free = 0")

    # 空间包围盒粗筛直接下推至索引 idx_nj_events_coords (lat, lng)
    if use_spatial:
        sql_parts.append("AND (lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?)")
        sql_args.extend([min_lat, max_lat, min_lng, max_lng])

    # 关键词检索下推至 SQL 参数化 LIKE
    if q:
        sql_parts.append(
            "AND (title LIKE ? OR summary LIKE ? OR address LIKE ? OR action_guide LIKE ? OR benefit LIKE ?)"
        )
        wildcard = f"%{q}%"
        sql_args.extend([wildcard, wildcard, wildcard, wildcard, wildcard])

    sql_parts.append("ORDER BY updated_at DESC")
    full_sql = " ".join(sql_parts)

    conn = nanjing_lbs_engine.get_db_connection(SQLITE_PATH)
    try:
        rows = conn.execute(full_sql, sql_args).fetchall()
    finally:
        conn.close()

    out: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        obs_path = d.get("obsidian_path", "")
        try:
            extra = json.loads(d.get("extra_info") or "{}")
        except Exception:
            extra = {}
        try:
            tags = json.loads(d.get("tags") or "[]")
        except Exception:
            tags = []
        try:
            extra_sources = json.loads(d.get("extra_sources") or "[]")
        except Exception:
            extra_sources = []

        start_date = d.get("start_date") or ""
        end_date = d.get("end_date") or ""
        days_left, time_status = nanjing_lbs_engine.compute_lifecycle(
            start_date, end_date, now_date=today
        )

        if not include_expired and time_status == "expired":
            continue
        if time_status_filter not in ("all", "") and time_status != time_status_filter:
            continue
        if tag and tag not in tags:
            continue

        item = {
            "id": d["id"],
            "post_id": d["id"],
            "title": clean_text(d["title"]),
            "short_title": extract_short_title(d["title"]),
            "category": clean_text(d["category"]),
            "sub_category": clean_text(d.get("sub_category") or "综合"),
            "start_date": start_date,
            "end_date": end_date,
            "days_left": days_left,
            "time_status": time_status,
            "start_time": d.get("start_time") or "",
            "end_time": d.get("end_time") or "",
            "event_time": clean_text(d.get("event_time_text") or ""),
            "event_time_text": clean_text(d.get("event_time_text") or ""),
            "district": clean_text(d.get("district") or "玄武区"),
            "address": clean_text(d.get("address") or ""),
            "location": clean_text(d.get("address") or ""),
            "lng": float(d.get("lng") or 118.7977),
            "lat": float(d.get("lat") or 32.0482),
            "geom": d.get("geom") or "",
            "benefit": clean_text(d.get("benefit") or ""),
            "is_free": bool(d.get("is_free", 1)),
            "action_guide": clean_text(d.get("action_guide") or ""),
            "summary": clean_text(d.get("summary") or ""),
            "tags": [clean_text(t) for t in tags if clean_text(t)],
            "extra_info": extra,
            "platform": clean_text(extra.get("platform") or "微信公众号"),
            "author": clean_text(extra.get("author") or "南京本地"),
            "publish_date": extra.get("publish_date") or today.isoformat(),
            "key_points": [clean_text(kp) for kp in (extra.get("key_points") or []) if clean_text(kp)] or [clean_text(d.get("summary") or "")],
            "source_url": d.get("source_url") or "",
            "url": d.get("source_url") or "",
            "obsidian_path": obs_path,
            "obsidian_uri": f"obsidian://open?vault=IOT&file={quote(obs_path)}",
            "status": clean_text(d.get("status") or "待去/待薅"),
            "extra_sources": extra_sources,
            "updated_at": d.get("updated_at") or "",
        }

        d_km = nanjing_lbs_engine.haversine_km(center_lng, center_lat, item["lng"], item["lat"])
        if use_spatial and d_km > radius_km:
            continue
        item["distance_km"] = d_km
        out.append(item)

    if sort_by == "distance":
        out.sort(key=lambda x: x.get("distance_km", 9999.0), reverse=(order == "desc"))
    elif sort_by == "days_left":
        out.sort(key=lambda x: x.get("days_left", 9999), reverse=(order == "desc"))
    elif sort_by == "updated_at":
        out.sort(key=lambda x: x.get("updated_at", ""), reverse=(order == "desc"))
    elif sort_by == "title":
        out.sort(key=lambda x: x.get("title", ""), reverse=(order == "desc"))
    elif order in ("desc", "reverse", "逆序"):
        out.reverse()

    return out


# ==============================================================================
# 10. HTTP 协议处理器 (DashboardHandler)
# ==============================================================================
class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "*")
        if "*" in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", "*")
        elif origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        elif ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGINS[0])
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, X-API-Key, If-None-Match")
        self.send_header("Access-Control-Expose-Headers", "ETag, Content-Length")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send_json(
        self, data: Any, status: int = 200, check_etag: bool = False, cache_seconds: int = 60
    ) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        if check_etag and status == 200:
            etag = f'"{hashlib.md5(body).hexdigest()}"'
            cache_control = (
                f"public, max-age={cache_seconds}, must-revalidate"
                if cache_seconds > 0
                else "public, max-age=0, must-revalidate"
            )
            if_none_match = self.headers.get("If-None-Match", "").strip()
            if if_none_match == etag:
                self.send_response(304)
                self._send_cors_headers()
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", cache_control)
                self.end_headers()
                return
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", cache_control)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_auth(self) -> bool:
        if not API_TOKEN:
            return True
        auth_hdr = self.headers.get("Authorization", "").strip()
        api_key_hdr = self.headers.get("X-API-Key", "").strip()
        token = ""
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()
        elif auth_hdr:
            token = auth_hdr
        elif api_key_hdr:
            token = api_key_hdr
        if not token:
            return False
        # 使用恒定时间对比防范计时侧信道攻击 (CWE-208)
        return hmac.compare_digest(token.encode("utf-8"), API_TOKEN.encode("utf-8"))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        try:
            self._handle_get()
        except Exception as e:
            self._send_json({"ok": False, "error": f"Internal Server Error: {str(e)}"}, 500)

    def _handle_get(self) -> None:
        METRICS.record_request()
        parsed = urlparse(self.path)
        qparams = parse_qs(parsed.query)

        # ----------------------------------------------------------------------
        # 1. 静态资源路由 (Static Assets & SPA Frontpage, 严格防路径穿越)
        # ----------------------------------------------------------------------
        if parsed.path in ("/", "/index.html"):
            dist_index = FRONTEND_DIST / "index.html"
            html_file = dist_index if dist_index.exists() else (BASE_DIR / "dashboard.html")
            if html_file.exists():
                content = html_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self._send_cors_headers()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json({"error": "UI index not found"}, 404)
            return

        if parsed.path in ("/favicon.ico", "/favicon.svg"):
            fav = FRONTEND_DIST / parsed.path.lstrip("/")
            if not fav.exists():
                fav = BASE_DIR / "frontend" / "public" / parsed.path.lstrip("/")
            if fav.exists():
                content = fav.read_bytes()
                mime = "image/x-icon" if parsed.path.endswith(".ico") else "image/svg+xml"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self._send_cors_headers()
                self.send_header("Cache-Control", "public, max-age=604800")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if parsed.path.startswith("/assets/"):
            filename = parsed.path[len("/assets/"):].lstrip("/")
            safe_target: Optional[Path] = None

            # 遍历静态资源候选目录并严格验证路径必须在对应目录下
            for base_dir in (FRONTEND_DIST / "assets", BASE_DIR / "assets"):
                try:
                    candidate = (base_dir / filename).resolve()
                    base_resolved = base_dir.resolve()
                    if candidate.is_relative_to(base_resolved) and candidate.is_file() and candidate.exists():
                        safe_target = candidate
                        break
                except Exception:
                    continue

            if not safe_target:
                # 若包含 .. 或路径遍历逃逸，返回 403 Forbidden
                if ".." in filename or "/." in filename or "\\." in filename:
                    self._send_json({"error": "Forbidden: Path traversal detected"}, 403)
                else:
                    self._send_json({"error": "Asset not found"}, 404)
                return

            content = safe_target.read_bytes()
            mime = "application/octet-stream"
            fn_lower = safe_target.name.lower()
            if fn_lower.endswith(".js"):
                mime = "application/javascript; charset=utf-8"
            elif fn_lower.endswith(".css"):
                mime = "text/css; charset=utf-8"
            elif fn_lower.endswith(".svg"):
                mime = "image/svg+xml"
            elif fn_lower.endswith(".png"):
                mime = "image/png"
            elif fn_lower.endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            elif fn_lower.endswith(".ico"):
                mime = "image/x-icon"
            elif fn_lower.endswith(".json"):
                mime = "application/json; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self._send_cors_headers()
            self.send_header("Cache-Control", "public, max-age=604800")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # ----------------------------------------------------------------------
        # 1.1 防盗链跨源图片代理 (GET /api/proxy/image?url=...)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/proxy/image":
            target_url = (qparams.get("url") or [""])[0].strip()
            if not target_url or not target_url.startswith(("http://", "https://")):
                self._send_json({"ok": False, "error": "Invalid or missing image URL"}, 400)
                return

            try:
                parsed_target = urlparse(target_url)
            except Exception:
                self._send_json({"ok": False, "error": "Malformed image URL"}, 400)
                return

            # 禁止 userinfo 混淆 (如 http://user@host)
            if parsed_target.username or parsed_target.password:
                self._send_json({"ok": False, "error": "UserInfo credentials in URL not permitted"}, 400)
                return

            # 严格限制端口 (仅放行 80 与 443)
            port = parsed_target.port
            if port and port not in (80, 443):
                self._send_json({"ok": False, "error": f"Port {port} not permitted for image proxy"}, 403)
                return

            allowed_hosts = (
                "qpic.cn",
                "weixin.qq.com",
                "xhscdn.com",
                "xiaohongshu.com",
                "unsplash.com",
                "amap.com",
            )
            target_host = (parsed_target.hostname or "").lower()
            if not target_host or not any(target_host == h or target_host.endswith("." + h) for h in allowed_hosts):
                self._send_json({"ok": False, "error": "Target host not permitted by SSRF policy"}, 403)
                return

            # 阻断私有/回环/内网保留 IP (防 DNS Rebinding 与伪造内网 IP)
            try:
                ip_obj = ipaddress.ip_address(target_host)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    self._send_json({"ok": False, "error": "Private or loopback IP not permitted"}, 403)
                    return
            except ValueError:
                pass

            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                }
                if "qpic.cn" in target_host or "weixin" in target_host:
                    headers["Referer"] = "https://mp.weixin.qq.com/"
                elif "xhscdn" in target_host or "xiaohongshu" in target_host:
                    headers["Referer"] = "https://www.xiaohongshu.com/"

                req = urllib.request.Request(target_url, headers=headers)
                # 使用自定义 NoRedirectHandler 打开，阻断通过 302 重定向逃逸至内网
                with IMAGE_PROXY_OPENER.open(req, timeout=8) as resp:
                    raw_ct = resp.headers.get("Content-Type", "image/jpeg")
                    # 限流防 OOM：最多读取 MAX_IMAGE_PROXY_BYTES (10MB)
                    img_data = resp.read(MAX_IMAGE_PROXY_BYTES + 1)
                    if len(img_data) > MAX_IMAGE_PROXY_BYTES:
                        self._send_json({"ok": False, "error": "Image payload exceeds maximum allowed size (10MB)"}, 413)
                        return

                # CRLF 清洗与合法 MIME 类型校验，防御 HTTP 响应拆分注入
                clean_ct = raw_ct.split(";")[0].strip().lower()
                clean_ct = re.sub(r"[\r\n]", "", clean_ct)
                if not re.match(r"^image\/[a-z0-9\+\-\.]+$", clean_ct):
                    clean_ct = "image/jpeg"

                etag = f'"{hashlib.md5(img_data).hexdigest()}"'
                if_none_match = self.headers.get("If-None-Match", "").strip()
                if if_none_match == etag:
                    self.send_response(304)
                    self._send_cors_headers()
                    self.send_header("ETag", etag)
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    return

                self.send_response(200)
                self.send_header("Content-Type", clean_ct)
                self._send_cors_headers()
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.send_header("Content-Length", str(len(img_data)))
                self.end_headers()
                self.wfile.write(img_data)
            except Exception as e:
                self._send_json({"ok": False, "error": f"Image proxy failed: {str(e)}"}, 502)
            return

        # ----------------------------------------------------------------------
        # 2. 系统健康探针与运行时监控 (GET /api/health)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/health":
            db_size = SQLITE_PATH.stat().st_size if SQLITE_PATH.exists() else 0
            all_items = EVENT_CACHE.get_all()
            self._send_json(
                {
                    "ok": True,
                    "service": "nanjing-events-lbs-backend",
                    "version": SERVER_VERSION,
                    "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
                    "database": {
                        "connected": SQLITE_PATH.exists(),
                        "path": str(SQLITE_PATH),
                        "journal_mode": "wal",
                        "size_bytes": db_size,
                        "events_count": len(all_items),
                    },
                    "cache": EVENT_CACHE.get_info(),
                    "metrics": METRICS.snapshot(),
                    "sync_worker": SYNC_MANAGER.get_status(),
                    "daily_scheduler": DAILY_SCHEDULER.get_info(),
                    "lan_ips": get_local_ips(),
                }
            )
            return

        # ----------------------------------------------------------------------
        # 3. Apple 日历订阅接口 (GET /api/events/calendar.ics)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/events/calendar.ics":
            all_items = EVENT_CACHE.get_all()
            include_all = (qparams.get("all") or ["0"])[0].lower() in ("1", "true")
            include_expired = (qparams.get("include_expired") or ["0"])[0].lower() in ("1", "true")

            selected = []
            today = datetime.date.today()
            fb_s, fb_e = get_fallback_dates(today)
            for it in all_items:
                days_left, time_status = nanjing_lbs_engine.compute_lifecycle(
                    it.get("start_date") or fb_s,
                    it.get("end_date") or fb_e,
                    now_date=today,
                )
                if not include_all and it.get("status") != "待去/待薅":
                    continue
                if not include_expired and time_status == "expired":
                    continue

                it_c = dict(it)
                it_c["days_left"] = days_left
                it_c["time_status"] = time_status
                selected.append(it_c)

            ical_content = generate_ical_feed(selected).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", 'inline; filename="nanjing_events.ics"')
            self._send_cors_headers()
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Content-Length", str(len(ical_content)))
            self.end_headers()
            self.wfile.write(ical_content)
            return

        # ----------------------------------------------------------------------
        # 4. 异步任务与定时调度状态轮询 (GET /api/sync/status)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/sync/status":
            self._send_json(
                {
                    "ok": True,
                    "task": SYNC_MANAGER.get_status(),
                    "scheduler": DAILY_SCHEDULER.get_info(),
                }
            )
            return

        # ----------------------------------------------------------------------
        # 5. 单条活动详情检索 (GET /api/events/<id>)
        # ----------------------------------------------------------------------
        if (
            parsed.path.startswith("/api/events/")
            and not parsed.path.endswith(("/geojson", "/nearby", "/status", "/calendar.ics"))
        ):
            event_id = parsed.path.replace("/api/events/", "").strip("/")
            item = EVENT_CACHE.get_by_id(event_id)
            if item:
                item_c = dict(item)
                fb_s, fb_e = get_fallback_dates()
                d_left, t_stat = nanjing_lbs_engine.compute_lifecycle(
                    item_c.get("start_date") or fb_s,
                    item_c.get("end_date") or fb_e,
                )
                item_c["days_left"] = d_left
                item_c["time_status"] = t_stat
                self._send_json({"ok": True, "event": item_c, "item": item_c})
            else:
                self._send_json({"ok": False, "error": f"活动 '{event_id}' 不存在"}, 404)
            return

        # ----------------------------------------------------------------------
        # 6. 空间邻近半径专业检索 (GET /api/events/nearby)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/events/nearby":
            center_lng, err_lng = safe_float((qparams.get("lng") or ["118.7842"])[0], 118.7842, "lng")
            center_lat, err_lat = safe_float((qparams.get("lat") or ["32.0418"])[0], 32.0418, "lat")
            raw_radius = qparams.get("radius_km") or qparams.get("radius") or ["5.0"]
            radius_km, err_rad = safe_float(raw_radius[0], 5.0, "radius_km")
            limit, err_lim = safe_int((qparams.get("limit") or ["20"])[0], 20, "limit")

            for err in (err_lng, err_lat, err_rad, err_lim):
                if err:
                    self._send_json({"ok": False, "error": err}, 400)
                    return

            radius_km = max(0.1, min(radius_km, 100.0))
            limit = max(1, min(limit, 200))

            qparams_copy = dict(qparams)
            qparams_copy["lng"] = [str(center_lng)]
            qparams_copy["lat"] = [str(center_lat)]
            qparams_copy["radius_km"] = [str(radius_km)]
            qparams_copy["sort_by"] = ["distance"]
            qparams_copy["order"] = ["asc"]

            # 直接下推至参数化 SQLite 空间包围盒粗筛，再进行精确计算
            filtered = query_events_from_db(qparams_copy)
            limited = filtered[:limit]

            self._send_json(
                {
                    "ok": True,
                    "center": {"lng": center_lng, "lat": center_lat},
                    "radius_km": radius_km,
                    "count": len(limited),
                    "total_in_radius": len(filtered),
                    "items": limited,
                    "events": limited,
                },
                check_etag=True,
            )
            return

        # ----------------------------------------------------------------------
        # 7. 多维活动检索与分页列表 (GET /api/events | /api/items)
        # ----------------------------------------------------------------------
        if parsed.path in ("/api/events", "/api/items"):
            filtered = query_events_from_db(qparams)
            all_items_count = len(EVENT_CACHE.get_all())

            page_s = (qparams.get("page") or [""])[0]
            if page_s.isdigit() and int(page_s) >= 1:
                page = int(page_s)
                page_size, _ = safe_int((qparams.get("page_size") or ["20"])[0], 20, "page_size")
                page_size = max(1, min(page_size, 100))
                total_count = len(filtered)
                total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                page_items = filtered[start_idx:end_idx]

                self._send_json(
                    {
                        "ok": True,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": total_pages,
                        "filtered_total": total_count,
                        "total": all_items_count,
                        "count": len(page_items),
                        "items": page_items,
                        "stats": compute_stats(filtered),
                    },
                    check_etag=True,
                )
            else:
                self._send_json(
                    {
                        "ok": True,
                        "count": len(filtered),
                        "total": all_items_count,
                        "items": filtered,
                        "stats": compute_stats(filtered),
                    },
                    check_etag=True,
                )
            return

        # ----------------------------------------------------------------------
        # 8. PostGIS 兼容标准 GeoJSON (GET /api/events/geojson)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/events/geojson":
            filtered = query_events_from_db(qparams)
            self._send_json(to_geojson_feature_collection(filtered), check_etag=True)
            return

        # ----------------------------------------------------------------------
        # 9. 图表统计数据 (GET /api/stats)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/stats":
            filtered = query_events_from_db(qparams)
            self._send_json({"ok": True, "stats": compute_stats(filtered)}, check_etag=True)
            return

        self._send_json({"error": f"Endpoint '{parsed.path}' not found"}, 404)

    def do_POST(self) -> None:
        try:
            self._handle_post()
        except Exception as e:
            self._send_json({"ok": False, "error": f"Internal Server Error: {str(e)}"}, 500)

    def _handle_post(self) -> None:
        METRICS.record_request()
        parsed = urlparse(self.path)

        # 1. 严格防 DoS 与 Content-Length 上限检查
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            self._send_json({"ok": False, "error": "Invalid Content-Length header"}, 400)
            return

        if length < 0 or length > MAX_BODY_SIZE:
            self._send_json(
                {"ok": False, "error": f"Payload Too Large (最大允许 {MAX_BODY_SIZE} 字节，收到 {length} 字节)"},
                413,
            )
            return

        # 2. 敏感写操作鉴权拦截
        if not self._check_auth():
            if 0 < length <= MAX_BODY_SIZE:
                try:
                    self.rfile.read(length)
                except Exception:
                    pass
            self._send_json(
                {"ok": False, "error": "Unauthorized: 未提供有效凭证 (Bearer Token 或 X-API-Key 错误)"},
                401,
            )
            return

        # 3. 严格防畸形编码与安全 JSON 解析
        try:
            raw_bytes = self.rfile.read(length) if length > 0 else b"{}"
            raw_body = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            self._send_json({"ok": False, "error": "Request body must be valid UTF-8 string"}, 400)
            return

        try:
            payload = json.loads(raw_body) if raw_body.strip() else {}
            if not isinstance(payload, dict):
                self._send_json({"ok": False, "error": "JSON payload must be a key-value object"}, 400)
                return
        except json.JSONDecodeError as e:
            self._send_json({"ok": False, "error": f"Malformed JSON payload: {e.msg}"}, 400)
            return

        # ----------------------------------------------------------------------
        # 1. 单条活动快速智能剪藏 (POST /api/events/clip)
        # ----------------------------------------------------------------------
        if parsed.path in ("/api/events/clip", "/api/clip"):
            ok, msg, new_event = clip_event(payload)
            if ok:
                self._send_json({"ok": True, "message": msg, "event": new_event})
            else:
                self._send_json({"ok": False, "error": msg}, 400)
            return

        # ----------------------------------------------------------------------
        # 2. 单条状态更新 (POST /api/events/status | /api/status)
        # ----------------------------------------------------------------------
        if parsed.path in ("/api/events/status", "/api/status") or (
            parsed.path.startswith("/api/events/") and parsed.path.endswith("/status")
        ):
            post_id = payload.get("id") or payload.get("post_id") or ""
            if not post_id and parsed.path.startswith("/api/events/"):
                parts = parsed.path.strip("/").split("/")
                if len(parts) >= 3:
                    post_id = parts[2]
            status = payload.get("status", "待去/待薅")
            ok, msg = update_item_status(post_id, status)
            self._send_json({"ok": ok, "message": msg, "id": post_id, "post_id": post_id, "status": status})
            return

        # ----------------------------------------------------------------------
        # 3. 批量状态更新 (POST /api/events/batch_status)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/events/batch_status":
            ids = payload.get("ids") or []
            status = payload.get("status", "已去/已打卡")
            if not isinstance(ids, list) or not ids:
                self._send_json({"ok": False, "error": "请提供待更新的活动 id 列表 (ids: [...])"}, 400)
                return
            success_count = 0
            for pid in ids:
                ok, _ = update_item_status(pid, status)
                if ok:
                    success_count += 1
            self._send_json({"ok": True, "updated_count": success_count, "status": status})
            return

        # ----------------------------------------------------------------------
        # 4. 极速同步与全量后台采集 (POST /api/sync | /api/scrape)
        # ----------------------------------------------------------------------
        if parsed.path in ("/api/scrape", "/api/sync"):
            mode = payload.get("mode", "incremental").strip()
            keyword = payload.get("keyword", "").strip()
            limit, _ = safe_int(payload.get("limit", 2), 2, "limit")
            limit = max(1, min(limit, 50))
            is_async = bool(payload.get("async", False))

            if mode == "incremental" and not keyword and not is_async:
                global LAST_SYNC_TIME
                acquired = SYNC_MUTEX.acquire(blocking=False)
                if not acquired:
                    items = EVENT_CACHE.get_all()
                    self._send_json(
                        {
                            "ok": True,
                            "mode": "incremental_fast",
                            "message": "同步正在执行中，已返回当前最新数据",
                            "count": len(items),
                            "items": items,
                            "stats": compute_stats(items),
                        }
                    )
                    return
                try:
                    now_ts = time.time()
                    if now_ts - LAST_SYNC_TIME < 3.0:
                        items = EVENT_CACHE.get_all()
                    else:
                        nanjing_lbs_engine.migrate_and_sync_all()
                        EVENT_CACHE.invalidate()
                        items = EVENT_CACHE.get_all(force_refresh=True)
                        LAST_SYNC_TIME = time.time()
                finally:
                    SYNC_MUTEX.release()

                self._send_json(
                    {
                        "ok": True,
                        "mode": "incremental_fast",
                        "count": len(items),
                        "items": items,
                        "stats": compute_stats(items),
                    }
                )
                return

            res = SYNC_MANAGER.submit_job(mode=mode, keyword=keyword, limit=limit)
            self._send_json(res)
            return

        # ----------------------------------------------------------------------
        # 5. 手动缓存清除与预热 (POST /api/cache/clear)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/cache/clear":
            EVENT_CACHE.invalidate()
            items = EVENT_CACHE.get_all(force_refresh=True)
            self._send_json({"ok": True, "message": "缓存已成功清空并重载", "count": len(items)})
            return

        self._send_json({"error": "Unknown endpoint"}, 404)


# ==============================================================================
# 11. 带有限长线程池与 Socket 超时保护的高性能服务器 (Bounded Server)
# ==============================================================================
class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """带有限长线程池 (max_workers=32) 与 Socket 超时保护 (15s) 的生产级服务器"""

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass,
        max_workers: int = 32,
        socket_timeout: float = 15.0,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.max_workers = max_workers
        self.socket_timeout = socket_timeout
        self._semaphore = threading.BoundedSemaphore(max_workers)

    def process_request(self, request, client_address):
        try:
            request.settimeout(self.socket_timeout)
        except Exception:
            pass

        if not self._semaphore.acquire(blocking=True, timeout=5.0):
            try:
                msg = b'HTTP/1.1 503 Service Unavailable\r\nRetry-After: 5\r\nContent-Type: application/json; charset=utf-8\r\n\r\n{"ok":false,"error":"Server overloaded"}\n'
                request.sendall(msg)
                request.shutdown(socket.SHUT_WR)
            except Exception:
                pass
            finally:
                self.close_request(request)
            return

        threading.Thread(
            target=self._process_request_bounded,
            args=(request, client_address),
            daemon=True,
            name=f"HTTPWorker_{int(time.time()*1000)%100000}",
        ).start()

    def _process_request_bounded(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.close_request(request)
            self._semaphore.release()


def get_local_ips() -> List[str]:
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Nanjing LBS Platform Backend")
    parser.add_argument(
        "--host", default=os.environ.get("HOST", "0.0.0.0"), help="Host address to bind"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8765")),
        help="Port to listen on",
    )
    args = parser.parse_args()

    host = args.host
    port = args.port

    # 启动前执行一次数据库表结构与索引自检
    try:
        conn = nanjing_lbs_engine.get_db_connection(SQLITE_PATH)
        nanjing_lbs_engine.ensure_nj_events_table(conn)
        conn.close()
    except Exception as e:
        print(f"[!] Warning: 数据库初始自检异常: {e}", flush=True)

    server = BoundedThreadingHTTPServer(
        (host, port), DashboardHandler, max_workers=32, socket_timeout=15.0
    )
    lan_ips = get_local_ips()
    # 启动每日 12:00 抓取调度器后台线程
    DAILY_SCHEDULER.start()

    print("=" * 64, flush=True)
    print(f"  Nanjing LBS Platform Backend ({SERVER_VERSION})", flush=True)
    print(f"  - Bind Address:  {host}:{port}", flush=True)
    print(f"  - Local URL:     http://127.0.0.1:{port}", flush=True)
    for ip in lan_ips:
        print(f"  - LAN URL:       http://{ip}:{port}", flush=True)
    print(
        f"  - Daily Schedule: Every day at 12:00:00 (Next: {DAILY_SCHEDULER.next_run_dt.strftime('%Y-%m-%d %H:%M:%S')})",
        flush=True,
    )
    print(
        "  - Lifecycle:     start_date / end_date / days_left / time_status Auto-Filter",
        flush=True,
    )
    print("  - Deduplication: Smart Venue & Time Clustering -> extra_sources", flush=True)
    print(f"  - Apple iCal:    http://127.0.0.1:{port}/api/events/calendar.ics", flush=True)
    print("  - Quick Clip:    POST /api/events/clip (Structured Auto-Extraction)", flush=True)
    if API_TOKEN:
        print("  - Auth Status:   Enabled (Bearer Token / X-API-Key Protection)", flush=True)
    else:
        print(
            "  - Auth Notice:   DASHBOARD_API_TOKEN is not set (Running in Open Dev Mode)",
            flush=True,
        )
    print(f"  - Workers Pool:  Bounded 32 Worker Threads (Socket Timeout: 15s)", flush=True)
    print(f"  - Max Body Size: {MAX_BODY_SIZE // (1024 * 1024)} MB (Anti-DoS Protected)", flush=True)
    print("=" * 64, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
