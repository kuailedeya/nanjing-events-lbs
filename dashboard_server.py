#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南京地区同城活动抓取与时空可视化系统 后端服务 (dashboard_server.py)
监听地址: http://127.0.0.1:8765
严格实现【表 5：后端接口层结构表（REST + 标准 GeoJSON + 空间半径检索 + Obsidian 双向同步）】
"""

import json
import re
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, quote, urlparse

import yaml

import nanjing_lbs_engine

BASE_DIR = Path(r"E:\usage")
SQLITE_PATH = BASE_DIR / "local.db"
VAULT_DIR = Path(r"E:\Note storage\IOT")
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
SYNC_SCRIPT = BASE_DIR / "social_obsidian_sync.py"

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



def get_all_events() -> List[Dict[str, Any]]:
    """读取 nj_events 全量数据，并与 Obsidian 笔记中的实时 YAML status 和要点列表合并"""
    if not SQLITE_PATH.exists():
        return []
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    nanjing_lbs_engine.ensure_nj_events_table(conn)
    rows = conn.execute("SELECT * FROM nj_events ORDER BY updated_at DESC").fetchall()
    conn.close()

    if not rows:
        return nanjing_lbs_engine.migrate_and_sync_all()

    items: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        obs_path = d.get("obsidian_path", "")
        md_file = VAULT_DIR / obs_path
        extra = {}
        try:
            extra = json.loads(d.get("extra_info") or "{}")
        except Exception:
            extra = {}
        tags = []
        try:
            tags = json.loads(d.get("tags") or "[]")
        except Exception:
            tags = []

        key_points = extra.get("key_points") or []
        status = d.get("status") or "待去/待薅"

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

        item = {
            "id": d["id"],
            "post_id": d["id"],
            "title": clean_text(d["title"]),
            "category": clean_text(d["category"]),
            "sub_category": clean_text(d.get("sub_category") or "综合"),
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
            "publish_date": extra.get("publish_date") or "2026-10-20",
            "key_points": [clean_text(kp) for kp in key_points if clean_text(kp)],
            "source_url": d.get("source_url") or "",
            "url": d.get("source_url") or "",
            "obsidian_path": obs_path,
            "obsidian_uri": f"obsidian://open?vault=IOT&file={quote(obs_path)}",
            "status": clean_text(status),
            "updated_at": d.get("updated_at") or "",
        }
        items.append(item)
    return items


def filter_events(items: List[Dict[str, Any]], query_params: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """支持按分类、南京11区、免费开关、状态、标签、关键词以及中心点球面半径 (lat/lng/radius_km) 过滤"""
    cat = (query_params.get("category") or ["ALL"])[0]
    dist = (query_params.get("district") or ["ALL"])[0]
    status = (query_params.get("status") or ["ALL"])[0]
    is_free_str = (query_params.get("is_free") or [""])[0].lower()
    tag = (query_params.get("tag") or [""])[0].strip()
    q = (query_params.get("q") or [""])[0].strip().lower()

    center_lng_s = (query_params.get("lng") or [""])[0]
    center_lat_s = (query_params.get("lat") or [""])[0]
    radius_s = (query_params.get("radius_km") or ["0"])[0]

    use_spatial = False
    center_lng, center_lat, radius_km = 118.7842, 32.0418, 0.0
    try:
        if center_lng_s and center_lat_s and float(radius_s) > 0:
            center_lng = float(center_lng_s)
            center_lat = float(center_lat_s)
            radius_km = float(radius_s)
            use_spatial = True
    except Exception:
        use_spatial = False

    out = []
    clean_cat = clean_text(cat)
    for it in items:
        if clean_cat not in ("ALL", "") and clean_text(it["category"]) != clean_cat:
            continue
        if dist not in ("ALL", "") and it["district"] != dist:
            continue
        if status not in ("ALL", "") and it["status"] != status:
            continue
        if is_free_str in ("1", "true", "yes") and not it["is_free"]:
            continue
        if tag and tag not in it.get("tags", []):
            continue
        if q:
            hay = " ".join(
                [
                    it["title"],
                    it["category"],
                    it["sub_category"],
                    it["district"],
                    it["address"],
                    it["benefit"],
                    it["action_guide"],
                    it["summary"],
                    it["author"],
                    " ".join(it.get("key_points") or []),
                ]
            ).lower()
            if q not in hay:
                continue

        d_km = nanjing_lbs_engine.haversine_km(center_lng, center_lat, it["lng"], it["lat"])
        it_copy = dict(it)
        it_copy["distance_km"] = d_km
        if use_spatial and d_km > radius_km:
            continue
        out.append(it_copy)
    return out


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


def compute_stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成统计分析所需的南京 11 区密度、类别占比、福利结构与时间轴数据"""
    dist_counts = {d: 0 for d in ALL_11_DISTRICTS}
    cat_counts: Dict[str, int] = {"南京展会": 0, "南京活动": 0, "羊毛福利": 0}
    sub_cat_counts: Dict[str, int] = {}
    date_counts: Dict[str, int] = {}
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

        btxt = it.get("benefit") or ""
        if any(k in btxt for k in ["免费", "免票"]):
            free_count += 1
        elif any(k in btxt for k in ["立减", "消费券", "0元", "0.01", "羊毛", "打卡", "礼"]):
            coupon_count += 1
        else:
            paid_count += 1

    return {
        "total": len(items),
        "districts": [{"name": k, "value": v, "center": nanjing_lbs_engine.NANJING_DISTRICTS.get(k, (118.7842, 32.0418))} for k, v in dist_counts.items()],
        "categories": [{"name": k, "value": v} for k, v in cat_counts.items()],
        "sub_categories": [{"name": k, "value": v} for k, v in sub_cat_counts.items()],
        "benefits": [
            {"name": "免费免票入场", "value": free_count},
            {"name": "立减消费券与羊毛", "value": coupon_count},
            {"name": "预约或早鸟购票", "value": paid_count},
        ],
        "timeline": [{"date": k, "count": v} for k, v in sorted(date_counts.items())],
    }


def update_item_status(post_id: str, new_status: str) -> bool:
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT obsidian_path FROM nj_events WHERE id = ?", (post_id,)
    ).fetchone()
    if not row:
        row = conn.execute(
            "SELECT obsidian_path FROM nanjing_deals_events WHERE post_id = ?", (post_id,)
        ).fetchone()
    if not row:
        conn.close()
        return False

    conn.execute("UPDATE nj_events SET status = ? WHERE id = ?", (new_status, post_id))
    conn.execute(
        "UPDATE nanjing_deals_events SET status = ? WHERE post_id = ?",
        (new_status, post_id),
    )
    conn.commit()
    conn.close()

    md_file = VAULT_DIR / row["obsidian_path"]
    if md_file.exists():
        try:
            txt = md_file.read_text(encoding="utf-8")
            txt = re.sub(r"(?m)^status:\s*.*$", f"status: {new_status}", txt, count=1)
            md_file.write_text(txt, encoding="utf-8")
        except Exception:
            pass
    return True


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qparams = parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            dist_index = FRONTEND_DIST / "index.html"
            html_file = dist_index if dist_index.exists() else (BASE_DIR / "dashboard.html")
            if html_file.exists():
                content = html_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
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
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json({"error": "Asset not found"}, 404)
            return

        if parsed.path in ("/api/events", "/api/items"):
            all_items = get_all_events()
            filtered = filter_events(all_items, qparams)
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

        if parsed.path == "/api/events/geojson":
            all_items = get_all_events()
            filtered = filter_events(all_items, qparams)
            self._send_json(to_geojson_feature_collection(filtered))
            return

        if parsed.path == "/api/stats":
            all_items = get_all_events()
            filtered = filter_events(all_items, qparams)
            self._send_json({"ok": True, "stats": compute_stats(filtered)})
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(raw_body)
        except Exception:
            payload = {}

        if parsed.path in ("/api/events/status", "/api/status"):
            post_id = payload.get("id") or payload.get("post_id") or ""
            status = payload.get("status", "待去/待薅")
            ok = update_item_status(post_id, status)
            self._send_json({"ok": ok, "id": post_id, "post_id": post_id, "status": status})
            return

        if parsed.path == "/api/scrape":
            keyword = payload.get("keyword", "").strip()
            limit = int(payload.get("limit", 2))
            cmd = [sys.executable, str(SYNC_SCRIPT), "--limit", str(limit)]
            if keyword:
                cmd.extend(["--keyword", keyword])
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, encoding="utf-8", timeout=45
                )
                nanjing_lbs_engine.migrate_and_sync_all()
                items = get_all_events()
                self._send_json(
                    {
                        "ok": proc.returncode == 0,
                        "stdout": proc.stdout[-600:],
                        "count": len(items),
                        "items": items,
                        "stats": compute_stats(items),
                    }
                )
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        self._send_json({"error": "Unknown endpoint"}, 404)


def main() -> None:
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"Nanjing LBS Visualization Server listening on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
