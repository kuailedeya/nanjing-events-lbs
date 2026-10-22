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

import datetime
import hashlib
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
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse

import yaml

import nanjing_lbs_engine
import social_obsidian_sync

# 核心路径配置
BASE_DIR = Path(r"E:\usage")
SQLITE_PATH = BASE_DIR / "local.db"
VAULT_DIR = Path(r"E:\Note storage\IOT")
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
SYNC_SCRIPT = BASE_DIR / "social_obsidian_sync.py"

SERVER_START_TIME = time.time()
SERVER_VERSION = "2.5.0-enterprise"

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

    for it in items:
        d = it.get("district") or "玄武区"
        dist_counts[d] = dist_counts.get(d, 0) + 1
        c = clean_text(it.get("category") or "南京活动")
        cat_counts[c] = cat_counts.get(c, 0) + 1
        sc = clean_text(it.get("sub_category") or "综合")
        sub_cat_counts[sc] = sub_cat_counts.get(sc, 0) + 1
        pdate = (it.get("publish_date") or "2026-10-20")[-5:]
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
        """从 SQLite 及 Obsidian Markdown 笔记中装载全量结构化数据"""
        if not SQLITE_PATH.exists():
            self._items = []
            self._id_map = {}
            self._stats = None
            self._geojson = None
            self._timestamp = time.time()
            return

        conn = nanjing_lbs_engine.get_db_connection(SQLITE_PATH)
        nanjing_lbs_engine.ensure_nj_events_table(conn)
        rows = conn.execute("SELECT * FROM nj_events ORDER BY updated_at DESC").fetchall()
        conn.close()

        if not rows:
            self._items = nanjing_lbs_engine.migrate_and_sync_all()
            self._id_map = {it["id"]: it for it in self._items}
            self._stats = compute_stats(self._items)
            self._geojson = to_geojson_feature_collection(self._items)
            self._timestamp = time.time()
            return

        items: List[Dict[str, Any]] = []
        id_map: Dict[str, Dict[str, Any]] = {}
        today = datetime.date.today()

        for r in rows:
            d = dict(r)
            obs_path = d.get("obsidian_path", "")
            md_file = VAULT_DIR / obs_path
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

            # 仅在 Obsidian 文件存在且有必要时读取最新 status
            if md_file.exists():
                try:
                    txt = md_file.read_text(encoding="utf-8")
                    m_yaml = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
                    if m_yaml:
                        fm = yaml.safe_load(m_yaml.group(1)) or {}
                        if fm.get("status"):
                            status = fm["status"]
                    if not key_points:
                        for ln in txt.splitlines():
                            if ln.strip().startswith("- "):
                                key_points.append(ln.strip()[2:].strip())
                except Exception:
                    pass

            event_time_text = clean_text(d.get("event_time_text") or "")
            publish_date = extra.get("publish_date") or "2026-10-20"

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
                "key_points": [clean_text(kp) for kp in key_points if clean_text(kp)],
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

        self._items = items
        self._id_map = id_map
        self._stats = compute_stats(items)
        self._geojson = to_geojson_feature_collection(items)
        self._timestamp = time.time()


EVENT_CACHE = EventCacheManager(ttl=15.0)


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
        try:
            if mode == "full" or keyword:
                cmd = [sys.executable, str(SYNC_SCRIPT), "--limit", str(limit)]
                if keyword:
                    cmd.extend(["--keyword", keyword])
                subprocess.run(
                    cmd, capture_output=True, text=True, encoding="utf-8", timeout=60, check=True
                )

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
            with self._lock:
                self._current_job.update(
                    {
                        "status": "failed",
                        "end_time": datetime.datetime.now().isoformat(),
                        "duration_sec": round(time.time() - t0, 2),
                        "message": f"任务执行失败: {str(e)}",
                        "error": str(e),
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
            now = datetime.datetime.now()
            if now >= self.next_run_dt:
                self.last_run_time = now.strftime("%Y-%m-%d %H:%M:%S")
                print(
                    f"[{self.last_run_time}] [DailyScheduler] 触发每日 {self.target_hour:02d}:{self.target_minute:02d} 定时抓取与同步...",
                    flush=True,
                )
                SYNC_MANAGER.submit_job(mode="full", limit=3)
                self.next_run_dt = self._calc_next_run()
            time.sleep(20)


DAILY_SCHEDULER = DailyScheduler(target_hour=12, target_minute=0)


# ==============================================================================
# 6. 原子化 Obsidian 与 SQLite 更新引擎 (Atomic Status Updater)
# ==============================================================================
def update_item_status(post_id: str, new_status: str) -> Tuple[bool, str]:
    """更新活动状态，原子化重写 Obsidian Markdown YAML 并主动失效缓存"""
    METRICS.record_status_update()
    conn = nanjing_lbs_engine.get_db_connection(SQLITE_PATH)
    row = conn.execute("SELECT obsidian_path FROM nj_events WHERE id = ?", (post_id,)).fetchone()
    if not row:
        row = conn.execute(
            "SELECT obsidian_path FROM nanjing_deals_events WHERE post_id = ?", (post_id,)
        ).fetchone()

    if not row:
        conn.close()
        return False, "未找到对应的活动记录 (ID 不存在)"

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE nj_events SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, now_str, post_id),
    )
    conn.execute(
        "UPDATE nanjing_deals_events SET status = ? WHERE post_id = ?",
        (new_status, post_id),
    )
    conn.commit()
    conn.close()

    obs_path = row["obsidian_path"]
    md_file = VAULT_DIR / obs_path
    if md_file.exists():
        try:
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
    tags_list = nanjing_lbs_engine.build_tags(cat, sub_cat, district, is_free, platform, location)
    geom_wkt = f"POINT({lng} {lat})"

    # 3. 生成全局唯一 post_id
    post_id = f"clip_{hashlib.md5((title + source_url + event_time_text).encode('utf-8')).hexdigest()[:12]}"
    if not source_url:
        source_url = f"https://local.nanjing/clip/{post_id}"

    # 4. 生成规范 Obsidian Markdown 文件 (原子写入)
    safe_name = social_obsidian_sync.sanitize_filename(f"[{cat[2:] if len(cat) > 2 else cat}] {title}")
    rel_path = f"05_社媒情报库/{safe_name}.md"
    md_file = VAULT_DIR / rel_path
    md_file.parent.mkdir(parents=True, exist_ok=True)

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
    try:
        with tempfile.NamedTemporaryFile("w", dir=md_file.parent, delete=False, encoding="utf-8") as tf:
            tf.write(md_content)
            temp_name = tf.name
        os.replace(temp_name, md_file)
    except Exception as e:
        return False, f"Obsidian 文件写入失败: {str(e)}", None

    extra_obj = {
        "platform": platform,
        "author": author,
        "publish_date": publish_date,
        "key_points": key_points,
        "price_num": price_num,
        "geocode_source": geo_src,
        "likes": 0,
    }

    # 5. 双表入库
    conn = nanjing_lbs_engine.get_db_connection(SQLITE_PATH)
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

    conn.execute(
        """
        INSERT OR REPLACE INTO nj_events (
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
    conn.commit()
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
    now_dt = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
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

        s_date_raw = (ev.get("start_date") or "2026-10-01")[:10].replace("-", "")
        e_date_raw = (ev.get("end_date") or "2026-10-31")[:10].replace("-", "")
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
        days_left, time_status = nanjing_lbs_engine.compute_lifecycle(
            it.get("start_date") or "2026-10-01",
            it.get("end_date") or "2026-10-31",
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

    return out


# ==============================================================================
# 9. HTTP 协议处理器 (DashboardHandler)
# ==============================================================================
class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self) -> None:
        METRICS.record_request()
        parsed = urlparse(self.path)
        qparams = parse_qs(parsed.query)

        # ----------------------------------------------------------------------
        # 1. 静态资源路由 (Static Assets & SPA Frontpage)
        # ----------------------------------------------------------------------
        if parsed.path in ("/", "/index.html"):
            dist_index = FRONTEND_DIST / "index.html"
            html_file = dist_index if dist_index.exists() else (BASE_DIR / "dashboard.html")
            if html_file.exists():
                content = html_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json({"error": "UI index not found"}, 404)
            return

        if parsed.path.startswith("/assets/"):
            filename = parsed.path.replace("/assets/", "")
            target_file = FRONTEND_DIST / "assets" / filename
            if not target_file.exists():
                target_file = BASE_DIR / "assets" / filename
            if target_file.exists() and target_file.is_file():
                content = target_file.read_bytes()
                mime = "application/octet-stream"
                if filename.endswith(".js"):
                    mime = "application/javascript; charset=utf-8"
                elif filename.endswith(".css"):
                    mime = "text/css; charset=utf-8"
                elif filename.endswith(".svg"):
                    mime = "image/svg+xml"
                elif filename.endswith(".png"):
                    mime = "image/png"
                elif filename.endswith(".ico"):
                    mime = "image/x-icon"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=604800")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json({"error": "Asset not found"}, 404)
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
            # 默认订阅所有“待去/待薅”且未过期的活动
            include_all = (qparams.get("all") or ["0"])[0].lower() in ("1", "true")
            include_expired = (qparams.get("include_expired") or ["0"])[0].lower() in ("1", "true")

            selected = []
            today = datetime.date.today()
            for it in all_items:
                days_left, time_status = nanjing_lbs_engine.compute_lifecycle(
                    it.get("start_date") or "2026-10-01",
                    it.get("end_date") or "2026-10-31",
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
            self.send_header("Access-Control-Allow-Origin", "*")
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
                # 动态刷新生命周期
                item_c = dict(item)
                d_left, t_stat = nanjing_lbs_engine.compute_lifecycle(
                    item_c.get("start_date") or "2026-10-01",
                    item_c.get("end_date") or "2026-10-31",
                )
                item_c["days_left"] = d_left
                item_c["time_status"] = t_stat
                self._send_json({"ok": True, "event": item_c})
            else:
                self._send_json({"ok": False, "error": f"活动 '{event_id}' 不存在"}, 404)
            return

        # ----------------------------------------------------------------------
        # 6. 空间邻近半径专业检索 (GET /api/events/nearby)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/events/nearby":
            center_lng = float((qparams.get("lng") or ["118.7842"])[0])
            center_lat = float((qparams.get("lat") or ["32.0418"])[0])
            radius_km = float((qparams.get("radius_km") or ["5.0"])[0])
            limit = int((qparams.get("limit") or ["20"])[0])

            qparams_copy = dict(qparams)
            qparams_copy["lng"] = [str(center_lng)]
            qparams_copy["lat"] = [str(center_lat)]
            qparams_copy["radius_km"] = [str(radius_km)]
            qparams_copy["sort_by"] = ["distance"]
            qparams_copy["order"] = ["asc"]

            all_items = EVENT_CACHE.get_all()
            filtered = filter_events(all_items, qparams_copy)
            limited = filtered[:limit]

            self._send_json(
                {
                    "ok": True,
                    "center": {"lng": center_lng, "lat": center_lat},
                    "radius_km": radius_km,
                    "count": len(limited),
                    "total_in_radius": len(filtered),
                    "items": limited,
                }
            )
            return

        # ----------------------------------------------------------------------
        # 7. 多维活动检索与分页列表 (GET /api/events | /api/items)
        # ----------------------------------------------------------------------
        if parsed.path in ("/api/events", "/api/items"):
            all_items = EVENT_CACHE.get_all()
            filtered = filter_events(all_items, qparams)

            page_s = (qparams.get("page") or [""])[0]
            if page_s.isdigit() and int(page_s) >= 1:
                page = int(page_s)
                page_size = int((qparams.get("page_size") or ["20"])[0])
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
                        "total": len(all_items),
                        "count": len(page_items),
                        "items": page_items,
                        "stats": compute_stats(filtered),
                    }
                )
            else:
                self._send_json(
                    {
                        "ok": True,
                        "count": len(filtered),
                        "total": len(all_items),
                        "items": filtered,
                        "stats": compute_stats(filtered),
                    }
                )
            return

        # ----------------------------------------------------------------------
        # 8. PostGIS 兼容标准 GeoJSON (GET /api/events/geojson)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/events/geojson":
            all_items = EVENT_CACHE.get_all()
            filtered = filter_events(all_items, qparams)
            self._send_json(to_geojson_feature_collection(filtered))
            return

        # ----------------------------------------------------------------------
        # 9. 图表统计数据 (GET /api/stats)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/stats":
            all_items = EVENT_CACHE.get_all()
            filtered = filter_events(all_items, qparams)
            self._send_json({"ok": True, "stats": compute_stats(filtered)})
            return

        self._send_json({"error": f"Endpoint '{parsed.path}' not found"}, 404)

    def do_POST(self) -> None:
        METRICS.record_request()
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(raw_body)
        except Exception:
            payload = {}

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
            limit = int(payload.get("limit", 2))
            is_async = bool(payload.get("async", False))

            if mode == "incremental" and not keyword and not is_async:
                nanjing_lbs_engine.migrate_and_sync_all()
                EVENT_CACHE.invalidate()
                items = EVENT_CACHE.get_all(force_refresh=True)
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
    port = 8765
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    lan_ips = get_local_ips()
    # 启动每日 12:00 抓取调度器后台线程
    DAILY_SCHEDULER.start()

    print("=" * 64, flush=True)
    print(f"  Nanjing LBS Platform Backend ({SERVER_VERSION})", flush=True)
    print(f"  - Bind Address:  0.0.0.0:{port}", flush=True)
    print(f"  - Local URL:     http://127.0.0.1:{port}", flush=True)
    for ip in lan_ips:
        print(f"  - LAN URL:       http://{ip}:{port}", flush=True)
    print(f"  - Daily Schedule: Every day at 12:00:00 (Next: {DAILY_SCHEDULER.next_run_dt.strftime('%Y-%m-%d %H:%M:%S')})", flush=True)
    print("  - Lifecycle:     start_date / end_date / days_left / time_status Auto-Filter", flush=True)
    print("  - Deduplication: Smart Venue & Time Clustering -> extra_sources", flush=True)
    print(f"  - Apple iCal:    http://127.0.0.1:{port}/api/events/calendar.ics", flush=True)
    print("  - Quick Clip:    POST /api/events/clip (Structured Auto-Extraction)", flush=True)
    print("  - CORS Status:   Fully Enabled (*, GET, POST, OPTIONS, PUT, DELETE)", flush=True)
    print("=" * 64, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
