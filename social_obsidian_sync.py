#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
南京活动 · 南京展会 · 羊毛福利 -> Obsidian 纯结构化数据库采集与提炼引擎 (social_obsidian_sync.py)

设计原则（严格遵循用户要求）：
1. 【不存长篇原文、不存无用配图】：
   抓取微信公众号与小红书页面后，仅在内存中解析正文，自动提炼为结构化数据库字段：
   - 类别 (category): 🎪 南京展会 | 🎉 南京活动 | 🐑 羊毛福利
   - 举办/截止时间 (event_time): 自动提取具体日期范围（如 10月22日-10月24日、周末开放、10月31日截止）
   - 地点/渠道 (location): 自动识别南京场馆/商圈（南京国际博览中心、新庄国展中心、万象天地、夫子庙等）或线上领券APP
   - 门票/福利力度 (benefit): 自动提取免费/票价/立减金额/周边福利
   - 参与/领取方式 (action_guide): 一句话操作路径（免预约直达 / 预登记领票 / 发小红书话题领礼 / APP搜索口令）
   - 一句话总结 (summary) + 3~5 条核心干货要点 (key_points)
2. 【纯数据库架构】：
   - Obsidian 原生 Bases 数据库：`05_社媒情报库/社媒情报数据库.base`（含：全部总表 / 🎪 南京展会 / 🎉 南京活动 / 🐑 羊毛福利 四大视图）
   - 可视化总览表：`05_社媒情报库/_社媒情报总览.md`（直接以结构化表格展示所有字段，打开即看，无需点进单篇笔记）
   - 本地 SQLite 数据库：`E:\usage\local.db` (`nanjing_deals_events` 表)
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
import yaml
from bs4 import BeautifulSoup

BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent))
DEFAULT_VAULT_DIR = Path(os.environ.get("VAULT_DIR", r"E:\Note storage\IOT"))
DEFAULT_DB_FOLDER_NAME = "05_社媒情报库"
DEFAULT_SQLITE_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "local.db"))

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# 南京常见展馆、地标与商圈词典
NANJING_LOCATIONS = [
    "南京国际博览中心",
    "南京国际展览中心",
    "新庄国展中心",
    "扬子江国际会议中心",
    "南京空港国际博览中心",
    "南京万象天地",
    "德基广场",
    "新街口",
    "夫子庙",
    "老门东",
    "秦淮河",
    "玄武湖",
    "红山森林动物园",
    "玄武红山新城",
    "凤栖湖",
    "钟山风景区",
    "燕子矶公园",
    "幕燕滨江",
    "阅江楼",
    "江宁湖熟",
    "南京博物院",
    "江苏省美术馆",
    "南京艺术学院美术馆",
    "金陵图书馆",
    "江北图书馆",
    "熙南里",
    "百家湖",
    "仙林大学城",
    "河西金鹰",
    "景枫中心",
]

ONLINE_CHANNELS = [
    "我的南京APP",
    "我的南京",
    "宁体汇",
    "支付宝",
    "微信支付",
    "微信立减金",
    "云闪付",
    "建行APP",
    "建设银行",
    "工商银行",
    "工行",
    "农业银行",
    "农行",
    "中国银行",
    "中行",
    "招商银行",
    "招行",
    "交通银行",
    "交行",
    "小红书话题打卡",
    "小红书APP",
    "京东",
    "美团",
    "携程",
]


def sanitize_filename(name: str, max_len: int = 42) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t#^\[\]]+', "_", name).strip(" ._")
    cleaned = re.sub(r"_+", "_", cleaned)
    return (cleaned[:max_len].rstrip(" ._")) or "未命名条目"


def parse_count(val: Any) -> int:
    if isinstance(val, int):
        return val
    if not val:
        return 0
    s = str(val).strip().replace(",", "").replace("+", "")
    try:
        if "万" in s or "w" in s.lower():
            num = float(re.sub(r"[^\d.]", "", s))
            return int(num * 10000)
        m = re.search(r"\d+", s)
        return int(m.group(0)) if m else 0
    except Exception:
        return 0


def classify_item(title: str, text: str, hint_cat: str = "") -> str:
    """精准归类为三大核心库：🎪 南京展会 | 🎉 南京活动 | 🐑 羊毛福利"""
    t_lower = title.lower()
    combined = f"{title} {text[:400]}".lower()
    # 标题明确是市集/开放日/景区免票/周末活动 -> 南京活动
    if any(k in t_lower for k in ["市集", "开放日", "免票", "周末免费", "菊花展", "歌会", "街唱", "嘉年华", "音乐节"]):
        return "🎉 南京活动"
    if any(k in combined for k in ["羊毛", "立减金", "消费券", "返现", "数币红包", "刷卡金", "月月刷", "省钱", "0.1元", "1元", "优惠券"]):
        if not any(k in t_lower for k in ["博览会", "展览会", "车展", "糖酒会", "塑料展", "电动车展"]):
            return "🐑 羊毛福利"
    if any(k in t_lower for k in ["展会", "博览会", "展览会", "交易会", "博览中心", "展览中心", "糖酒会", "车展", "塑料展", "电动车展", "漫展", "珠宝展", "看展", "艺术展", "首展", "特展"]):
        return "🎪 南京展会"
    if hint_cat in ("🎪 南京展会", "🎉 南京活动", "🐑 羊毛福利"):
        return hint_cat
    if any(k in combined for k in ["南京", "周末", "活动", "市集", "演出", "景区", "夫子庙", "玄武湖"]):
        return "🎉 南京活动"
    return "🐑 羊毛福利"


def extract_structured_fields(title: str, raw_text: str, category: str, platform: str) -> Dict[str, Any]:
    """
    核心提炼器：从原始乱序正文中提炼结构化数据库字段与 3-5 条核心干货要点，丢弃长篇废话！
    返回字段：
      - event_time: 活动/展会时间或羊毛截止期
      - location: 南京场馆/地点或线上领取渠道
      - benefit: 门票/优惠/羊毛力度
      - action_guide: 参与/领取方式
      - summary: 70字以内一句话核心总结（供数据库表格直接阅读）
      - key_points: List[str] 3-5条结构化要点
    """
    clean_text = re.sub(r"!\[.*?\]\(.*?\)", "", raw_text)
    clean_text = re.sub(r"https?://\S+", "", clean_text)
    lines = [re.sub(r"\s+", " ", ln).strip(" *#-|>·") for ln in clean_text.splitlines()]
    lines = [ln for ln in lines if len(ln) >= 4 and not any(noise in ln for noise in ["未经授权", "不得搬抄", "追究其法律责任", "点击蓝字关注", "向下滑动查看", "长按识别二维码"])]
    joined = " | ".join(lines)

    # 1. 提取时间 (event_time)
    event_time = "近期进行中"
    time_patterns = [
        r"((?:202\d年?)?\d{1,2}月\d{1,2}日?\s*[-~至—–]\s*(?:\d{1,2}月)?\d{1,2}日?)",
        r"(\d{1,2}月\d{1,2}日\s*[-~至—–]\s*(?:\d{1,2}月)?\d{1,2}日)",
        r"(10/\d{1,2}\s*[-~至]\s*10/\d{1,2})",
        r"(10\.\d{1,2}\s*[-~至]\s*10\.\d{1,2})",
        r"(\d{1,2}月\d{1,2}日(?:起|开园|开幕|开展|截止))",
        r"(每周[五六日末]+(?:晚|上午|下午)?)",
        r"(\d{1,2}月\d{1,2}日)",
    ]
    for pat in time_patterns:
        m = re.search(pat, f"{title} {joined}")
        if m:
            event_time = m.group(1).strip()
            break

    # 2. 提取地点/渠道 (location)
    found_locs: List[str] = []
    for loc in NANJING_LOCATIONS:
        if loc in f"{title} {joined}" and loc not in found_locs:
            found_locs.append(loc)
    if not found_locs:
        for ch in ONLINE_CHANNELS:
            if ch.lower() in f"{title} {joined}".lower() and ch not in found_locs:
                found_locs.append(ch)
    if not found_locs:
        # 尝试匹配 xx区xx路xx号
        addr_m = re.search(r"((?:南京市?)?(?:玄武|秦淮|建邺|鼓楼|栖霞|雨花台|江宁|浦口|六合|溧水|高淳)区[^\s，。；|]{2,14})", joined)
        if addr_m:
            found_locs.append(addr_m.group(1))
    location = " / ".join(found_locs[:2]) if found_locs else ("南京同城" if "南京" in f"{title} {joined}" else "线上APP/全国通用")

    # 3. 提取费用/福利力度 (benefit)
    benefit = "详见要点"
    benefit_patterns = [
        r"(\d+\s*[-~至]\s*\d+\s*元(?:立减金|消费券|红包|支付券)?)",
        r"((?:领|抽|返现|立减|满减|保底)\s*\d+(?:\.\d+)?\s*元[^\s，。；|]{0,8})",
        r"(免费(?:对外开放|开放|入场|免票|参观|领[^\s，。；|]{1,6})?)",
        r"(0元[^\s，。；|]{1,8})",
        r"(门票\s*[:：]?\s*免费)",
        r"(打卡赢好礼|免费领周边|免费领集章卡|送礼物|特价福利)",
    ]
    for pat in benefit_patterns:
        m = re.search(pat, f"{title} {joined}")
        if m:
            benefit = m.group(1).strip()
            break
    if benefit == "详见要点":
        if "免费" in f"{title} {joined}" or "免票" in f"{title} {joined}":
            benefit = "免费参与 / 免门票"
        elif category == "🎪 南京展会":
            benefit = "预登记免费领票"
        elif category == "🐑 羊毛福利":
            benefit = "限时立减/领券福利"
        else:
            benefit = "线下打卡体验"

    # 4. 提取操作/参与方式 (action_guide)
    action_guide = "直接前往或点击原文链接查看"
    if "无需预约" in joined or "免预约" in joined or "直接前往" in joined:
        action_guide = "免预约，直接前往现场打卡"
    elif "小红书" in joined and ("话题" in joined or "笔记" in joined or "打卡" in joined):
        topic_m = re.search(r"(#[^#\s，。]{2,18})", joined)
        topic_str = f"带话题 {topic_m.group(1)} " if topic_m else "带指定话题"
        action_guide = f"现场拍照{topic_str}发小红书笔记，至服务台领福利"
    elif "预登记" in joined or "报名" in joined or "预约" in joined:
        action_guide = "需提前在公众号/小程序预登记或报名入场"
    elif any(k in joined for k in ["手机银行", "APP", "搜索", "支付宝", "微信支付", "云闪付"]):
        path_m = re.search(r"((?:入口路径|活动入口|路径)\s*[:：]\s*[^|。；]{4,45})", joined)
        if path_m:
            action_guide = path_m.group(1).strip()
        else:
            action_guide = f"打开 {location} 搜索对应活动报名领取"

    # 5. 提炼 3-5 条高密度结构化要点 (key_points)
    key_points: List[str] = []
    for ln in lines:
        if len(ln) < 8 or ln == title:
            continue
        # 优先挑选含日期、地点、金额、展览名、福利规则的干货行
        if any(
            w in ln
            for w in [
                "10月", "10/", "10.", "时间", "地点", "场馆", "博览中心", "展览中心",
                "免费", "门票", "立减", "红包", "消费券", "入口", "打卡", "首展",
                "特展", "市集", "歌会", "菊花", "电动车", "塑料展", "糖酒会", "银行",
            ]
        ):
            short_ln = ln[:95] + ("..." if len(ln) > 95 else "")
            if short_ln not in key_points:
                key_points.append(short_ln)
        if len(key_points) >= 5:
            break

    if not key_points:
        for ln in lines[:4]:
            short_ln = ln[:95] + ("..." if len(ln) > 95 else "")
            if short_ln not in key_points:
                key_points.append(short_ln)

    # 6. 生成一句话核心总结（直接呈现在数据库表格列中）
    first_pt = key_points[0][:42] if key_points else title[:42]
    summary = f"【{location}】{benefit}（{event_time}）— {first_pt}"
    summary = re.sub(r"\s+", " ", summary)[:85]

    return {
        "event_time": event_time,
        "location": location,
        "benefit": benefit,
        "action_guide": action_guide,
        "summary": summary,
        "key_points": key_points[:5],
    }


class NanjingDealScraper:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://weixin.sogou.com/",
            }
        )

    def resolve_sogou_wechat_url(self, sogou_href: str) -> str:
        if sogou_href.startswith("http") and "mp.weixin.qq.com" in sogou_href:
            return sogou_href
        b = random.randint(0, 99)
        a_idx = sogou_href.find("url=")
        a_char = (
            sogou_href[a_idx + 4 + 21 + b]
            if (a_idx != -1 and len(sogou_href) > a_idx + 4 + 21 + b)
            else "a"
        )
        full_link = (
            sogou_href if sogou_href.startswith("http") else f"https://weixin.sogou.com{sogou_href}"
        ) + f"&k={b}&h={a_char}"

        if not self.session.cookies.get("SUV"):
            self.session.cookies.set("SUV", str(int(random.random() * 1e16)), domain=".sogou.com")

        try:
            r = self.session.get(
                full_link,
                headers={"Referer": "https://weixin.sogou.com/"},
                timeout=10,
            )
            parts = re.findall(r"url\s*\+=\s*'([^']*)'", r.text)
            mp_url = "".join(parts).replace("@", "")
            return mp_url if mp_url.startswith("http") else full_link
        except Exception:
            return full_link

    def fetch_wechat_text(self, mp_url: str, fallback_snippet: str = "") -> str:
        """在内存中抓取公众号文字用于提炼总结（同时兼容普通图文 #js_content 与小绿书图片消息 #js_image_desc）"""
        try:
            r = self.session.get(mp_url, timeout=10)
            soup = BeautifulSoup(r.text, "lxml")
            # 校验是否被重定向到了过期旧文 (动态支持 SYNC_LOOKBACK_DAYS，默认 180 天)
            lookback_days = int(os.environ.get("SYNC_LOOKBACK_DAYS", "180"))
            min_valid_ts = int(time.time()) - (lookback_days * 86400)
            ct_m = re.search(r'\bvar\s+ct\s*=\s*["\'](\d{10})["\']', r.text)
            if ct_m and int(ct_m.group(1)) < min_valid_ts:
                return fallback_snippet

            parts: List[str] = []
            for sel in ("#js_content", "#js_image_desc", "meta[property='og:description']"):
                el = soup.select_one(sel)
                if el:
                    txt = el.get("content", "") if el.name == "meta" else el.get_text("\n", strip=True)
                    if txt and len(txt.strip()) > 10:
                        parts.append(txt.strip())
            return "\n".join(parts) if parts else fallback_snippet
        except Exception:
            return fallback_snippet

    def scrape_wechat_by_queries(self, query_plan: List[Tuple[str, str]], per_query_limit: int = 3) -> List[Dict[str, Any]]:
        """按预设的【南京展会 / 南京活动 / 羊毛福利】主题词检索近期微信公众号并提炼为结构化记录"""
        records: List[Dict[str, Any]] = []
        seen_titles = set()

        for hint_cat, query in query_plan:
            search_url = f"https://weixin.sogou.com/weixin?type=2&query={quote(query)}"
            try:
                r = self.session.get(search_url, timeout=10)
                if not self.session.cookies.get("SUV"):
                    self.session.cookies.set("SUV", str(int(random.random() * 1e16)), domain=".sogou.com")
                soup = BeautifulSoup(r.text, "lxml")
            except Exception:
                continue

            count = 0
            for li in soup.select("ul.news-list li"):
                ts_m = re.search(r"timeConvert\(['\"](\d{10})['\"]\)", str(li))
                ts = int(ts_m.group(1)) if ts_m else 0
                # 动态滑动窗口过滤，保留近期有效信息，剔除陈旧历史
                lookback_days = int(os.environ.get("SYNC_LOOKBACK_DAYS", "180"))
                min_valid_ts = int(time.time()) - (lookback_days * 86400)
                if ts < min_valid_ts:
                    continue

                h3_a = li.select_one("h3 a")
                if not h3_a:
                    continue
                title = h3_a.get_text(strip=True)
                # 过滤无关的政务/老年义工/外地纯广告
                if any(bad in title for bad in ["义工", "老年公寓", "疫情", "确诊", "贵阳", "成都", "深圳", "上海", "昆山", "北京", "广州"]):
                    continue
                norm_title = re.sub(r"\W+", "", title)[:16]
                if norm_title in seen_titles:
                    continue
                seen_titles.add(norm_title)

                href = h3_a.get("href", "")
                snippet_el = li.select_one("p.txt-info")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                acc_el = li.select_one(".s-p .all-time-y2") or li.select_one(".s-p a.account")
                author = acc_el.get_text(strip=True) if acc_el else "微信公众号"
                pub_date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

                mp_url = self.resolve_sogou_wechat_url(href)
                raw_text = self.fetch_wechat_text(mp_url, fallback_snippet=snippet)
                full_source_text = f"{snippet}\n{raw_text}"

                # 如果包含“小红书”打卡/同步攻略，标记平台为“小红书+公众号联动”或根据内容归属
                platform = "小红书" if ("小红书" in query or "小红书" in title) else "微信公众号"
                category = classify_item(title, full_source_text, hint_cat=hint_cat)
                extracted = extract_structured_fields(title, full_source_text, category, platform)

                records.append(
                    {
                        "post_id": "item_" + hashlib.md5(norm_title.encode("utf-8")).hexdigest()[:12],
                        "title": title,
                        "platform": platform,
                        "category": category,
                        "author": author,
                        "publish_date": pub_date,
                        "event_time": extracted["event_time"],
                        "location": extracted["location"],
                        "benefit": extracted["benefit"],
                        "action_guide": extracted["action_guide"],
                        "summary": extracted["summary"],
                        "key_points": extracted["key_points"],
                        "likes": 0,
                        "url": mp_url,
                    }
                )
                count += 1
                time.sleep(0.3)
                if count >= per_query_limit:
                    break

        return records

    def scrape_xiaohongshu_deals_and_events(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        从小红书发现页/旅行/美食频道并发采样最新(2026)笔记，筛选【展览/活动/探店/羊毛/省钱】相关笔记，
        深入详情页提取正文后总结为结构化数据库条目（不保存原文与图片）。
        """
        channels = ["homefeed.travel_v3", "homefeed.food_v3", "homefeed_recommend"]

        def _fetch_batch(idx: int) -> List[Dict[str, Any]]:
            ch = channels[idx % len(channels)]
            url = (
                "https://www.xiaohongshu.com/explore"
                if ch == "homefeed_recommend"
                else f"https://www.xiaohongshu.com/explore?channel_id={ch}"
            )
            try:
                r = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"},
                    timeout=8,
                )
                m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>", r.text, re.S)
                if not m:
                    return []
                data = json.loads(m.group(1).replace("undefined", "null"))
                return data.get("feed", {}).get("feeds", [])
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=6) as ex:
            batches = list(ex.map(_fetch_batch, range(12)))

        seen_ids = set()
        candidates: List[Dict[str, Any]] = []
        target_kws = [
            "南京", "江苏", "展", "活动", "免费", "羊毛", "福利", "券", "打卡",
            "周末", "市集", "博物馆", "门票", "9.9", "0元", "白嫖", "省钱",
            "攻略", "便宜", "平价", "特价", "补贴", "减", "送", "划算",
        ]

        for feeds in batches:
            for f in feeds:
                nid = f.get("id", "")
                if not nid or nid in seen_ids:
                    continue
                try:
                    lookback_days = int(os.environ.get("SYNC_LOOKBACK_DAYS", "180"))
                    min_valid_ts = int(time.time()) - (lookback_days * 86400)
                    if len(nid) >= 8 and int(nid[:8], 16) < min_valid_ts:
                        continue
                except Exception:
                    pass
                seen_ids.add(nid)
                title = f.get("noteCard", {}).get("displayTitle") or ""
                if any(k in title for k in target_kws):
                    candidates.append(f)

        # 若标题精确命中不足 limit，则从 travel/food 频道补充高赞攻略笔记
        if len(candidates) < limit:
            all_valid = [f for feeds in batches for f in feeds if f.get("id") in seen_ids and f not in candidates]
            candidates.extend(all_valid[: limit - len(candidates)])

        records: List[Dict[str, Any]] = []
        for f in candidates[:limit]:
            nid = f.get("id", "")
            xsec = f.get("xsecToken", "")
            nc = f.get("noteCard", {})
            title = nc.get("displayTitle") or f"小红书笔记_{nid[:8]}"
            author = nc.get("user", {}).get("nickname") or "小红书博主"
            likes = parse_count(nc.get("interactInfo", {}).get("likedCount", 0))
            try:
                pub_date = datetime.datetime.fromtimestamp(int(nid[:8], 16)).strftime("%Y-%m-%d")
            except Exception:
                pub_date = datetime.date.today().strftime("%Y-%m-%d")

            detail_url = f"https://www.xiaohongshu.com/explore/{nid}?xsec_token={quote(xsec)}&xsec_source=pc_feed"
            desc = title
            ip_loc = ""
            try:
                rd = self.session.get(detail_url, timeout=10)
                md = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>", rd.text, re.S)
                if md:
                    dd = json.loads(md.group(1).replace("undefined", "null"))
                    nd = dd.get("note", {}).get("noteDetailMap", {}).get(nid, {}).get("note", {})
                    if nd:
                        desc = nd.get("desc") or title
                        ip_loc = nd.get("ipLocation") or ""
                        likes = parse_count(nd.get("interactInfo", {}).get("likedCount", likes))
            except Exception:
                pass

            category = classify_item(title, desc, hint_cat="🐑 羊毛福利")
            extracted = extract_structured_fields(title, desc, category, "小红书")
            if ip_loc and extracted["location"] == "线上APP/全国通用":
                extracted["location"] = f"{ip_loc} / 小红书"

            records.append(
                {
                    "post_id": f"xhs_{nid}",
                    "title": title,
                    "platform": "小红书",
                    "category": category,
                    "author": author,
                    "publish_date": pub_date,
                    "event_time": extracted["event_time"],
                    "location": extracted["location"],
                    "benefit": extracted["benefit"],
                    "action_guide": extracted["action_guide"],
                    "summary": extracted["summary"],
                    "key_points": extracted["key_points"],
                    "likes": likes,
                    "url": detail_url,
                }
            )
            time.sleep(0.25)

        return records


class ObsidianSummaryDB:
    def __init__(
        self,
        vault_dir: Path = DEFAULT_VAULT_DIR,
        db_folder_name: str = DEFAULT_DB_FOLDER_NAME,
        sqlite_path: Path = DEFAULT_SQLITE_PATH,
    ) -> None:
        self.vault_dir = vault_dir
        self.db_folder_name = db_folder_name
        self.db_root = vault_dir / db_folder_name
        self.expo_dir = self.db_root / "南京展会"
        self.event_dir = self.db_root / "南京活动"
        self.deal_dir = self.db_root / "羊毛福利"
        self.sqlite_path = sqlite_path

        try:
            for d in (self.expo_dir, self.event_dir, self.deal_dir):
                d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"[!] Warning: Vault 目录不可直接访问 ({e})，以 SQLite 降级模式工作", flush=True)
        self._init_sqlite()

    def _init_sqlite(self) -> None:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        conn.execute("DROP TABLE IF EXISTS social_posts")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nanjing_deals_events (
                post_id TEXT PRIMARY KEY,
                category TEXT,
                title TEXT,
                event_time TEXT,
                location TEXT,
                benefit TEXT,
                action_guide TEXT,
                summary TEXT,
                platform TEXT,
                author TEXT,
                publish_date TEXT,
                likes INTEGER,
                status TEXT,
                url TEXT,
                obsidian_path TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def save_record(self, rec: Dict[str, Any]) -> str:
        """写入纯结构化摘要卡（绝不写入长篇原文与外部图片！）"""
        cat = rec["category"]
        if "展会" in cat:
            sub_dir = self.expo_dir
        elif "活动" in cat:
            sub_dir = self.event_dir
        else:
            sub_dir = self.deal_dir

        safe_title = sanitize_filename(rec["title"], max_len=36)
        filename = f"{rec['publish_date']}_{safe_title}.md"
        file_path = sub_dir / filename
        rel_path = f"{self.db_folder_name}/{sub_dir.name}/{filename}"

        frontmatter = {
            "title": rec["title"],
            "category": cat,
            "event_time": rec["event_time"],
            "location": rec["location"],
            "benefit": rec["benefit"],
            "action_guide": rec["action_guide"],
            "summary": rec["summary"],
            "platform": rec["platform"],
            "author": rec["author"],
            "publish_date": rec["publish_date"],
            "likes": int(rec.get("likes", 0)),
            "status": "待去/待薅",
            "url": rec["url"],
            "tags": [
                "南京情报库",
                f"类型/{sub_dir.name}",
                f"来源/{rec['platform']}",
            ],
        }

        yaml_str = yaml.safe_dump(
            frontmatter,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ).strip()

        bullets_md = "\n".join(f"- {pt}" for pt in rec.get("key_points", []))
        if not bullets_md:
            bullets_md = f"- {rec['summary']}"

        # 纯结构化卡片，不含任何长文与外部图片链接（避免触发插件下载垃圾图片）
        md_content = f"""---
{yaml_str}
---

# {rec['title']}

| 字段 | 提炼内容 |
| :--- | :--- |
| **🏷️ 情报类别** | `{cat}` |
| **⏰ 举办/截止时间** | **{rec['event_time']}** |
| **📍 场馆/地点/渠道** | `{rec['location']}` |
| **💰 门票/福利力度** | **{rec['benefit']}** |
| **🚀 参与/领取方式** | {rec['action_guide']} |
| **🌐 来源平台与账号** | {rec['platform']} · `{rec['author']}`（发布于 `{rec['publish_date']}`） |
| **🔗 原文报名/领券链接** | [点击直达原帖]({rec['url']}) |

## 📋 核心要点总结（AI 提炼，已剔除原文废话）

{bullets_md}
"""
        try:
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(md_content, encoding="utf-8")
        except OSError:
            pass

        try:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        conn = sqlite3.connect(self.sqlite_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        try:
            with conn:
                existing_st = conn.execute(
                    "SELECT status FROM nanjing_deals_events WHERE post_id = ?", (rec["post_id"],)
                ).fetchone()
                safe_status = existing_st[0] if (existing_st and existing_st[0]) else "待去/待薅"
                conn.execute(
                    """
                    INSERT INTO nanjing_deals_events
                    (post_id, category, title, event_time, location, benefit, action_guide,
                     summary, platform, author, publish_date, likes, status, url, obsidian_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(post_id) DO UPDATE SET
                        category=excluded.category,
                        title=excluded.title,
                        event_time=excluded.event_time,
                        location=excluded.location,
                        benefit=excluded.benefit,
                        action_guide=excluded.action_guide,
                        summary=excluded.summary,
                        platform=excluded.platform,
                        author=excluded.author,
                        publish_date=excluded.publish_date,
                        likes=excluded.likes,
                        status=excluded.status,
                        url=excluded.url,
                        obsidian_path=excluded.obsidian_path
                    """,
                    (
                        rec["post_id"],
                        cat,
                        rec["title"],
                        rec["event_time"],
                        rec["location"],
                        rec["benefit"],
                        rec["action_guide"],
                        rec["summary"],
                        rec["platform"],
                        rec["author"],
                        rec["publish_date"],
                        int(rec.get("likes", 0)),
                        safe_status,
                        rec["url"],
                        rel_path,
                    ),
                )
        finally:
            conn.close()
        return rel_path

    def build_base_and_dashboard(self) -> None:
        """生成 Obsidian 原生 `.base` 数据库文件与一屏总览表 `_社媒情报总览.md`"""
        base_file = self.db_root / "社媒情报数据库.base"
        base_yaml = f"""filters:
  and:
    - 'file.inFolder("{self.db_folder_name}")'
    - 'file.ext == "md"'
    - 'file.name != "_社媒情报总览"'

properties:
  file.name:
    displayName: "📌 活动/展会/羊毛名称"
  category:
    displayName: "🏷️ 类别"
  event_time:
    displayName: "⏰ 举办/截止时间"
  location:
    displayName: "📍 地点/领取渠道"
  benefit:
    displayName: "💰 门票/福利力度"
  action_guide:
    displayName: "🚀 怎么参加/怎么薅"
  status:
    displayName: "✅ 状态"
  platform:
    displayName: "🌐 来源"
  publish_date:
    displayName: "📅 发布日"
  url:
    displayName: "🔗 链接"

views:
  - type: table
    name: "📊 全部汇总（直接看表无需点开）"
    order:
      - category
      - file.name
      - event_time
      - location
      - benefit
      - action_guide
      - status
      - platform
      - url
    sort:
      - property: publish_date
        direction: DESC
  - type: table
    name: "🎪 南京展会排期"
    filters:
      and:
        - 'category == "🎪 南京展会"'
    order:
      - file.name
      - event_time
      - location
      - benefit
      - action_guide
      - status
      - url
    sort:
      - property: publish_date
        direction: DESC
  - type: table
    name: "🎉 南京同城活动"
    filters:
      and:
        - 'category == "🎉 南京活动"'
    order:
      - file.name
      - event_time
      - location
      - benefit
      - action_guide
      - status
      - url
    sort:
      - property: publish_date
        direction: DESC
  - type: table
    name: "🐑 羊毛与消费券"
    filters:
      and:
        - 'category == "🐑 羊毛福利"'
    order:
      - file.name
      - benefit
      - location
      - event_time
      - action_guide
      - platform
      - status
      - url
    sort:
      - property: publish_date
        direction: DESC
"""
        vault_accessible = self.vault_dir.exists()
        if vault_accessible:
            try:
                base_file.write_text(base_yaml, encoding="utf-8")
            except OSError:
                pass

        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        all_rows = conn.execute(
            "SELECT * FROM nanjing_deals_events ORDER BY publish_date DESC"
        ).fetchall()
        conn.close()

        vault_accessible = self.vault_dir.exists()
        rows = []
        for r in all_rows:
            obs_p = r["obsidian_path"] or ""
            # 只有当 Vault 目录存在且文件确实存在时正常关联；若脱机或文件未落盘，安全保留记录，绝不盲目删库
            if not vault_accessible or not obs_p or (self.vault_dir / obs_p).exists():
                rows.append(r)

        expos = [r for r in rows if r["category"] == "🎪 南京展会"]
        events = [r for r in rows if r["category"] == "🎉 南京活动"]
        deals = [r for r in rows if r["category"] == "🐑 羊毛福利"]
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        def _render_table(items: List[sqlite3.Row]) -> str:
            if not items:
                return "_暂无记录_"
            lines = [
                "| 名称 (点击看要点卡) | ⏰ 举办/截止时间 | 📍 地点/渠道 | 💰 门票/福利力度 | 🚀 怎么参加/怎么薅 | 来源 | 原帖 |",
                "| :--- | :---: | :---: | :---: | :--- | :---: | :---: |",
            ]
            for r in items:
                obs_p = r["obsidian_path"] or ""
                link_target = obs_p[:-3] if obs_p.endswith(".md") else obs_p
                short_t = r["title"].replace("|", "｜")[:28]
                lines.append(
                    f"| [[{link_target}\\|{short_t}]] | **{r['event_time']}** | `{r['location']}` | **{r['benefit']}** | {(r['action_guide'] or '')[:36]} | {r['platform']} | [直达]({r['url']}) |"
                )
            return "\n".join(lines)

        dashboard_md = f"""---
title: "南京展会 · 同城活动 · 羊毛福利 数据库总表"
updated_at: "{now_str}"
tags:
  - 南京情报库/总表
  - 数据库/Bases
---

# 🗂️ 南京展会 · 同城活动 · 羊毛福利 数据库总表

> [!success] 零长文、纯总结数据库模式（直接看表即可）
> 已自动把微信公众号与小红书的长文提炼为 **`⏰ 时间` + `📍 地点/渠道` + `💰 门票/福利` + `🚀 参加/领取方式`** 结构化字段，**不存原文废话、不存广告图片**。

<div style="display:flex; gap:12px; flex-wrap:wrap; margin:12px 0;">
<div style="flex:1; min-width:150px; padding:12px 16px; border-radius:10px; background:#1e1b2e; border-left:4px solid #8b5cf6; color:#ede9fe;">
<b>🎪 南京近期展会</b><br/><span style="font-size:22px; font-weight:700;">{len(expos)} 场</span><br/><span style="font-size:12px; opacity:.8;">河西国博 / 新庄国展 / 美术馆</span>
</div>
<div style="flex:1; min-width:150px; padding:12px 16px; border-radius:10px; background:#14241b; border-left:4px solid #10b981; color:#d1fae5;">
<b>🎉 南京同城活动</b><br/><span style="font-size:22px; font-weight:700;">{len(events)} 个</span><br/><span style="font-size:12px; opacity:.8;">周末免费活动 / 市集 / 景区免票</span>
</div>
<div style="flex:1; min-width:150px; padding:12px 16px; border-radius:10px; background:#261912; border-left:4px solid #f59e0b; color:#fef3c7;">
<b>🐑 羊毛与消费券</b><br/><span style="font-size:22px; font-weight:700;">{len(deals)} 条</span><br/><span style="font-size:12px; opacity:.8;">立减金 / 消费券 / 小红书打卡礼</span>
</div>
</div>

---

## 🗄️ 交互式数据库视图（Obsidian Native `Bases`）

![[{self.db_folder_name}/社媒情报数据库.base]]

---

## 🎪 一、南京近期展会排期表（{len(expos)}）

{_render_table(expos)}

---

## 🎉 二、南京地区周末与免费活动表（{len(events)}）

{_render_table(events)}

---

## 🐑 三、近期羊毛福利与消费券表（{len(deals)}）

{_render_table(deals)}

---

## ⚡ 命令行一键更新数据库

```powershell
# 一键抓取最新【南京展会 + 南京活动 + 羊毛福利】并提炼写入 Obsidian 数据库
python social_obsidian_sync.py
```
"""
        if vault_accessible:
            try:
                (self.db_root / "_社媒情报总览.md").write_text(dashboard_md, encoding="utf-8")
            except OSError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="南京活动 · 南京展会 · 羊毛福利 -> Obsidian 结构化总结数据库")
    parser.add_argument("--keyword", "-k", type=str, default="", help="附加自定义搜索词（默认自动扫描南京展会+南京活动+羊毛三大主题）")
    parser.add_argument("--limit", "-n", type=int, default=3, help="每个主题抓取条数")
    parser.add_argument("--vault", type=str, default=str(DEFAULT_VAULT_DIR), help="Obsidian 仓库路径")
    parser.add_argument("--db-path", type=str, default=str(DEFAULT_SQLITE_PATH), help="SQLite 数据库文件路径")
    args = parser.parse_args()

    scraper = NanjingDealScraper()
    db = ObsidianSummaryDB(vault_dir=Path(args.vault), sqlite_path=Path(args.db_path))

    # 1. 优先注入/维护南京全域 11 行政区基准精选情报集 (52+ 条)
    try:
        from nanjing_seeds import NANJING_COMPREHENSIVE_SEEDS, COMPREHENSIVE_QUERY_PLAN
        print(f"[*] 正在核验并维护南京全域基准情报库 ({len(NANJING_COMPREHENSIVE_SEEDS)} 条)...")
        for seed in NANJING_COMPREHENSIVE_SEEDS:
            db.save_record(seed)
        default_plan = list(COMPREHENSIVE_QUERY_PLAN)
    except Exception as e:
        print(f"[!] 基准情报集加载提示: {e}")
        _cur_dt = datetime.datetime.now()
        _y = _cur_dt.year
        _m = _cur_dt.month
        default_plan: List[Tuple[str, str]] = [
            ("🎪 南京展会", f"{_y} 南京 {_m}月 展会 排期 博览中心"),
            ("🎪 南京展会", f"{_y} 南京 电动车展 塑料展 电商交易会 {_m}月"),
            ("🎪 南京展会", "南京 万象天地 艺术首展 免费"),
            ("🎉 南京活动", "南京 本周末 免费活动 漫展 市集"),
            ("🎉 南京活动", f"南京 {_m}月 免费开放日 景区 免票 周末"),
            ("🎉 南京活动", f"南京 菊花展 夫子庙 市集 {_m}月"),
            ("🐑 羊毛福利", f"{_y} 南京 文博会 薅羊毛 小红书"),
            ("🐑 羊毛福利", f"{_m}月 羊毛 合集 消费券 立减金"),
            ("🐑 羊毛福利", f"小红书 羊毛 免费 {_m}月 立减金"),
        ]
    if args.keyword:
        default_plan.insert(0, ("🎉 南京活动", args.keyword))

    print("[*] 正在抓取并提炼【微信公众号 & 小红书联动】的南京展会、南京同城活动与羊毛福利...")
    wx_records = scraper.scrape_wechat_by_queries(default_plan, per_query_limit=args.limit)
    for rec in wx_records:
        p = db.save_record(rec)
        print(f"  [+] [{rec['category']}] {rec['title']} -> ⏰ {rec['event_time']} | 📍 {rec['location']} | 💰 {rec['benefit']}")

    print("[*] 正在从小红书并发采样最新同城/探店/羊毛笔记并提炼总结...")
    xhs_records = scraper.scrape_xiaohongshu_deals_and_events(limit=4)
    for rec in xhs_records:
        p = db.save_record(rec)
        print(f"  [+] [{rec['category']}] (小红书) {rec['title']} -> 📍 {rec['location']} | 💰 {rec['benefit']}")

    db.build_base_and_dashboard()
    try:
        import nanjing_lbs_engine
        nanjing_lbs_engine.migrate_and_sync_all()
    except Exception as e:
        print(f"[!] LBS 空间同步提示: {e}")
    print(f"[✓] 全部提炼完成！共入库 {len(wx_records) + len(xhs_records)} 条纯结构化摘要记录。")


if __name__ == "__main__":
    main()
