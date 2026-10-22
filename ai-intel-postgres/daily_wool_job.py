#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日羊毛候选采集任务。

流程：
  1. 读取 sources.yaml
  2. 抓取 GitHub 清单 / Hacker News / Dev.to / RSS / 官方定价页
  3. 规范化 URL、去重、评分、写入 wool_candidates
  4. 记录 wool_sources 与 daily_jobs

只写 PostgreSQL，不直接写 Obsidian。
高分候选由 promote_candidates.py 生成笔记，再由 sync_to_postgres.py 同步。
"""

import argparse
import hashlib
import json
import re
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import feedparser
import psycopg2
import requests
import yaml
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from psycopg2.extras import Json, execute_values

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

BASE = Path(__file__).resolve().parent
SOURCES_FILE = BASE / "sources.yaml"
ENV_FILE = BASE / ".env"
TIMEOUT = 20
USER_AGENT = "ai-intel-wool-bot/1.0 (local research; contact: local)"
MAX_TEXT = 600

FREE_TERMS = [
    "free", "free tier", "free plan", "free trial", "free credits", "credits",
    "credit", "giveaway", "student", "students", "education", "edu", "discount",
    "coupon", "promo", "trial", "open source", "open-source", "self-hosted",
    "self hosted", "no cost", "no card", "lifetime deal", "startup credits",
    "cloud credits", "api credits", "gpu credits", "免费", "白嫖", "限免", "额度",
    "学生", "教育", "开源", "折扣", "优惠", "试用", "领取", "赠送",
]
AI_TERMS = [
    "ai", "llm", "gpt", "claude", "openai", "anthropic", "gemini", "deepseek",
    "qwen", "gpu", "api", "cloud", "database", "hosting", "developer", "coding",
    "agent", "copilot", "cursor", "ollama", "huggingface", "model", "inference",
    "vector", "embedding", "rag", "mcp", "sdk", "framework", "serverless",
]
NEGATIVE_TERMS = [
    "hiring", "job opening", "salary", "buy now", "for sale", "sponsored",
    "webinar replay", "podcast episode", "newsletter issue", "case study",
]

WOOL_TYPES = {"免费额度", "学生优惠", "限时免费", "免费云资源", "折扣", "活动", "免费课程"}
STRONG_WOOL_TERMS = [
    "credit", "credits", "free tier", "free plan", "free usage", "free quota",
    "quota", "token", "student", "students", "education", "edu", "giveaway",
    "hackathon", "contest", "challenge", "coupon", "promo code", "discount",
    "trial", "free trial", "grant", "startup program", "free api", "free gpu",
    "free hosting", "free database", "free cloud", "free course", "free ebook",
    "免费", "额度", "学生", "教育", "限时", "领取", "赠送", "兑换码", "优惠",
    "折扣", "试用", "抽奖", "比赛", "白嫖",
]
INFRA_TERMS = [
    "api", "gpu", "cloud", "hosting", "database", "server", "storage", "compute",
    "model", "llm", "ai", "agent", "developer", "coding", "token", "inference",
]

SKIP_URL_PATTERNS = [
    r"^(?:mailto|tel|javascript|data):",
    r"(?:twitter|x)\.com/(?:intent|share|home|i/)",
    r"github\.com/(?:login|signup|features|sponsors|marketplace|settings)",
    r"(?:shields\.io|badgen\.net|img\.shields\.io|travis-ci|circleci|codecov|coveralls)",
    r"(?:opencollective|patreon|buymeacoffee|ko-fi)\.com",
    r"\.(?:png|jpg|jpeg|gif|svg|webp|ico|css|js|woff2?)(?:[?#]|$)",
    r"^(?:https?://)?(?:localhost|127\.0\.0\.1|0\.0\.0\.0)",
]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wool_candidates (
    id                  BIGSERIAL PRIMARY KEY,
    title               TEXT NOT NULL,
    type                TEXT,
    status              TEXT NOT NULL DEFAULT 'candidate',
    source_name         TEXT,
    source_type         TEXT,
    source_url          TEXT,
    link                TEXT,
    summary             TEXT,
    canonical_url       TEXT,
    url_hash            CHAR(64) NOT NULL UNIQUE,
    score               INTEGER NOT NULL DEFAULT 0,
    promotion_score     INTEGER NOT NULL DEFAULT 0,
    published_at        DATE,
    raw                 JSONB,
    promoted_note_path  TEXT,
    promoted_at         TIMESTAMPTZ,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wool_candidates_status ON wool_candidates(status);
CREATE INDEX IF NOT EXISTS idx_wool_candidates_score ON wool_candidates(score DESC);
CREATE INDEX IF NOT EXISTS idx_wool_candidates_source ON wool_candidates(source_name);
CREATE INDEX IF NOT EXISTS idx_wool_candidates_published ON wool_candidates(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_wool_candidates_promoted ON wool_candidates(promoted_note_path);
ALTER TABLE wool_candidates ADD COLUMN IF NOT EXISTS promotion_score INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_wool_candidates_promotion ON wool_candidates(promotion_score DESC);

CREATE TABLE IF NOT EXISTS wool_sources (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    url             TEXT NOT NULL DEFAULT '',
    enabled         BOOLEAN NOT NULL DEFAULT true,
    last_fetch_at   TIMESTAMPTZ,
    last_status     TEXT,
    last_error      TEXT,
    last_count      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, url)
);

CREATE TABLE IF NOT EXISTS daily_jobs (
    id              BIGSERIAL PRIMARY KEY,
    job_name        TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',
    stats           JSONB,
    error           TEXT
);
CREATE INDEX IF NOT EXISTS idx_daily_jobs_started ON daily_jobs(started_at DESC);

CREATE OR REPLACE VIEW v_candidate_counts AS
SELECT
    count(*) AS total,
    count(*) FILTER (WHERE status = 'candidate') AS candidates,
    count(*) FILTER (WHERE status = 'promoted') AS promoted,
    count(*) FILTER (WHERE status = 'rejected') AS rejected,
    count(*) FILTER (WHERE status = 'expired') AS expired,
    count(*) FILTER (WHERE score >= 70) AS high_score,
    round(avg(score)::numeric, 1) AS avg_score,
    max(score) AS max_score
FROM wool_candidates;

CREATE OR REPLACE VIEW v_candidate_sources AS
SELECT
    source_name,
    source_type,
    count(*) AS items,
    round(avg(score)::numeric, 1) AS avg_score,
    max(score) AS max_score,
    max(last_seen_at) AS last_seen
FROM wool_candidates
GROUP BY source_name, source_type
ORDER BY items DESC;

CREATE OR REPLACE VIEW v_wool_candidates AS
SELECT
    id, title, type, source_name, source_type, link, summary,
    score, promotion_score, published_at, first_seen_at, last_seen_at
FROM wool_candidates
WHERE status = 'candidate'
  AND promotion_score >= 70
  AND score >= 70
  AND source_type IN ('official', 'github', 'hn', 'rss')
  AND type = ANY(ARRAY[
      '免费额度', '学生优惠', '限时免费', '免费云资源',
      '折扣', '活动', '免费课程', '免费工具'
  ])
  AND (
      source_type = 'official'
      OR (title || ' ' || coalesce(summary, '')) !~* (
          'pricing review|review 2026| vs |alternatives|how to|guide|playbook|'
          'bill|costs?|salary|hiring|go rogue|now available|available on|'
          'calculator|dashboard|tracker|track|burning|audit|consumes|best|tutorial|'
          'legit|testing|test|pricing|discontinue|discontinued|ending|shutting|'
          'ask hn|musk|election|voters|lawsuit|settles|is the new|air alert|'
          'built on|marketing asset|gaming|gamers?|game|spinning ring|christmas|retry script|architecting|architecture'
      )
  )
  AND (
      source_type IN ('official', 'github')
      OR title ~* (
          'free\\s+(credits?|tier|plan|trial|api|gpu|hosting|database|cloud|container|'
          'maus?|users?|seats?|requests?|storage|usage|domain|ssl|email|course|'
          'bootcamp|certification|tool|app|service|startup pack)'
          '|free.*credits?|credits?.*free|credits?\\s+never\\s+expire|passes|'
          'student\\s*.*\\s*(free|discount|offer|credit|credits|plan|pack|benefit|trial)|'
          '(free|discount|offer|credit|credits|plan|pack|benefit|trial)\\s*.*\\s*student|'
          'giveaway|coupon|promo code|no credit card'
      )
  )
  AND (title || ' ' || coalesce(summary, '')) ~* (
      'api|cloud|gpu|database|hosting|server|developer|coding|code|program|software|'
      'ai\\b|llm|model|token|student|education|github|saas|platform|devops|data|'
      'web|domain|email|auth|monitor|storage|open source|self-hosted'
  )
ORDER BY promotion_score DESC, score DESC, published_at DESC NULLS LAST;
"""


def load_env() -> dict:
    env = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def connect():
    env = load_env()
    return psycopg2.connect(
        host="127.0.0.1",
        port=int(env.get("POSTGRES_PORT", "5433")),
        dbname=env.get("POSTGRES_DB", "ai_intel"),
        user=env.get("POSTGRES_USER", "ai_intel"),
        password=env["POSTGRES_PASSWORD"],
        connect_timeout=10,
    )


def clean_text(value, limit=MAX_TEXT):
    if value is None:
        return ""
    s = str(value)
    try:
        if "<" in s or "&" in s:
            s = BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
    except Exception:
        pass
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    s = "".join(ch for ch in s if not (0x7F <= ord(ch) <= 0x9F))
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`>#|]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def canonicalize_url(url):
    if not url:
        return None
    url = str(url).strip()
    if url.startswith("//"):
        url = "https:" + url
    try:
        p = urlparse(url)
    except Exception:
        return None
    if p.scheme not in ("http", "https") or not p.netloc:
        return None
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/") or "/"
    query = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
        and k.lower() not in {"ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid"}
    ]
    return urlunparse((p.scheme, host, path, "", urlencode(query), ""))


def skip_url(url):
    if not url:
        return True
    low = url.lower()
    return any(re.search(pattern, low, re.I) for pattern in SKIP_URL_PATTERNS)


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def http_get(url, **kwargs):
    """带简单退避的 GET，缓解 HN/Dev.to/Reddit 的 429。"""
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, **kwargs)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    if last_error:
        raise last_error
    return response


def as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, time.struct_time):
        return date(*value[:3])
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, time.struct_time):
        return datetime(*value[:6])
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def infer_type(text):
    t = text.lower()
    if any(k in t for k in ["student", "education", "edu ", "学生", "教育", "校园"]):
        return "学生优惠"
    if any(k in t for k in ["hackathon", "giveaway", "contest", "challenge", "黑客松", "比赛", "抽奖"]):
        return "活动"
    if any(k in t for k in ["course", "ebook", "book", "tutorial", "课程", "教程", "电子书"]):
        return "免费课程"
    if any(k in t for k in ["credit", "credits", "quota", "token", "free tier", "free plan", "额度", "token"]):
        return "免费额度"
    if any(k in t for k in ["trial", "limited time", "ends", "限时", "试用"]):
        return "限时免费"
    if any(k in t for k in ["hosting", "cloud", "vps", "server", "托管", "云服务"]):
        return "免费云资源"
    if any(k in t for k in ["open source", "open-source", "self-hosted", "self hosted", "开源", "自托管"]):
        return "开源"
    if any(k in t for k in ["discount", "coupon", "promo", "折扣", "优惠", "优惠码"]):
        return "折扣"
    if any(k in t for k in ["tool", "api", "sdk", "framework", "工具", "接口"]):
        return "免费工具"
    return "待分类"


def score_candidate(title, summary, source_type, published_at):
    text = f"{title} {summary}".lower()
    score = 10
    if any(term in text for term in FREE_TERMS):
        score += 30
    if any(term in text for term in AI_TERMS):
        score += 15
    if "$" in text or "usd" in text or "美元" in text:
        score += 8
    if source_type == "official":
        score += 20
    elif source_type == "github":
        score += 10
    elif source_type in {"hn", "rss", "devto"}:
        score += 5
    if any(term in text for term in NEGATIVE_TERMS):
        score -= 25
    if published_at:
        days = (date.today() - published_at).days
        if days <= 7:
            score += 20
        elif days <= 30:
            score += 15
        elif days <= 90:
            score += 8
        elif days <= 365:
            score += 3
        elif days > 730:
            score -= 10
    if "show hn" in text or "launch" in text:
        score += 10
    if "expired" in text or "ended" in text or "closed" in text:
        score -= 30
    return max(0, min(100, score))


def promotion_score_candidate(title, summary, type_name, source_type, published_at):
    """更严格的“羊毛”分数，用来决定是否值得写进 Obsidian。"""
    text = f"{title} {summary}".lower()
    score = 0
    strong = any(term in text for term in STRONG_WOOL_TERMS)
    if strong:
        score += 55
    if type_name in WOOL_TYPES:
        score += 20
    if source_type == "official":
        score += 15
    elif source_type == "github":
        score += 8
    if any(term in text for term in INFRA_TERMS):
        score += 10
    if "$" in text or "usd" in text or "美元" in text:
        score += 8
    if published_at:
        days = (date.today() - published_at).days
        if days <= 30:
            score += 8
        elif days > 730:
            score -= 10
    if "show hn" in text and not strong:
        score -= 20
    if any(term in text for term in NEGATIVE_TERMS):
        score -= 30
    if any(term in text for term in ["expired", "ended", "closed"]):
        score -= 40
    return max(0, min(100, score))


def make_candidate(title, link, summary, source_name, source_type, source_url, published_at=None, raw=None):
    title = clean_text(title, 200)
    summary = clean_text(summary, MAX_TEXT)
    if not title:
        return None
    canonical = canonicalize_url(link)
    if not canonical or skip_url(canonical):
        return None
    text = f"{title} {summary}"
    type_name = infer_type(text)
    return {
        "title": title,
        "type": type_name,
        "source_name": source_name,
        "source_type": source_type,
        "source_url": canonicalize_url(source_url) or source_url,
        "link": canonical,
        "summary": summary or None,
        "canonical_url": canonical,
        "url_hash": text_hash(canonical),
        "score": score_candidate(title, summary, source_type, published_at),
        "promotion_score": promotion_score_candidate(title, summary, type_name, source_type, published_at),
        "published_at": published_at,
        "raw": raw or {},
    }


def parse_markdown(text, source):
    candidates = []
    heading = ""
    for line in text.splitlines():
        h = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if h:
            heading = clean_text(h.group(1), 120)
            continue
        for match in re.finditer(r"\[([^\]]{2,200})\]\((https?://[^)\s]+)\)", line):
            if match.start() > 0 and line[match.start() - 1] == "!":
                continue
            title = clean_text(match.group(1), 200)
            link = match.group(2)
            tail = clean_text(line[match.end():].strip(" -–—:|"), 400)
            summary = " · ".join(x for x in [heading, tail] if x)
            candidate = make_candidate(
                title, link, summary, source["name"], "github",
                source.get("_resolved_url", ""), None,
                {"repo": source.get("repo"), "path": source.get("path"), "heading": heading},
            )
            if candidate:
                candidates.append(candidate)
    return candidates


def parse_hn(data, query, source_url):
    candidates = []
    for hit in data.get("hits", []):
        title = hit.get("title") or hit.get("story_title") or ""
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        published = as_date(hit.get("created_at"))
        points = hit.get("points") or 0
        comments = hit.get("num_comments") or 0
        summary = f"HN 讨论 {points} points / {comments} comments"
        story = clean_text(hit.get("story_text") or "", 300)
        if story:
            summary += f" · {story}"
        candidate = make_candidate(
            title, link, summary, "Hacker News", "hn", source_url, published,
            {"objectID": hit.get("objectID"), "query": query, "points": points},
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def parse_devto(articles, source_url):
    candidates = []
    for item in articles:
        title = item.get("title") or ""
        link = item.get("url") or ""
        published = as_date(item.get("published_at"))
        tags = ", ".join(item.get("tag_list") or [])
        summary = clean_text(item.get("description") or "", 400)
        if tags:
            summary = f"{summary} · tags: {tags}" if summary else f"tags: {tags}"
        candidate = make_candidate(
            title, link, summary, "Dev.to", "devto", source_url, published,
            {"id": item.get("id"), "tags": item.get("tag_list")},
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def parse_rss(text, source):
    feed = feedparser.parse(text)
    candidates = []
    for entry in feed.entries[:200]:
        title = entry.get("title") or ""
        link = entry.get("link") or ""
        summary = clean_text(entry.get("summary") or entry.get("description") or "", 500)
        published = as_date(entry.get("published_parsed") or entry.get("updated_parsed") or entry.get("published"))
        candidate = make_candidate(
            title, link, summary, source["name"], "rss", source["url"], published,
            {"feed_title": clean_text(feed.feed.get("title") or "", 120)},
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def parse_official(html, source):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "", 200)
    meta = soup.find("meta", attrs={"name": "description"})
    meta_desc = clean_text(meta.get("content") if meta else "", 500)

    keywords = ["free", "credit", "credits", "student", "trial", "free tier", "免费", "额度", "学生"]
    paragraphs = []
    seen = set()
    for tag in soup.find_all(["p", "li"]):
        text = clean_text(tag.get_text(" ", strip=True), 320)
        low = text.lower()
        if len(text) < 25 or not any(k in low for k in keywords):
            continue
        key = text[:120]
        if key in seen:
            continue
        seen.add(key)
        paragraphs.append(text)
        if len(paragraphs) >= 4:
            break

    summary = " · ".join(paragraphs)
    if not summary:
        summary = meta_desc
    if not summary:
        text = clean_text(soup.get_text(" ", strip=True), 3000)
        low = text.lower()
        snippets = []
        for term in keywords:
            idx = low.find(term)
            if idx >= 0:
                snippets.append(text[max(0, idx - 120): idx + 280])
            if len(snippets) >= 2:
                break
        summary = " · ".join(snippets)

    candidate = make_candidate(
        title or source["name"], source["url"], summary, source["name"], "official",
        source["url"], None, {"official_page": source["url"]},
    )
    return [candidate] if candidate else []


def fetch_github(source):
    repo = source["repo"]
    paths = []
    for path in [source.get("path"), "README.md", "readme.md"]:
        if path and path not in paths:
            paths.append(path)
    last_error = None
    for branch in ["main", "master"]:
        for path in paths:
            url = f"https://raw.githubusercontent.com/{repo}/{branch}/{quote(path)}"
            try:
                r = http_get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
                if r.status_code == 200 and len(r.text) > 100:
                    source["_resolved_url"] = url
                    return r.text, url
            except Exception as exc:
                last_error = str(exc)
    raise RuntimeError(last_error or "not found")


def fetch_hn(query):
    url = "https://hn.algolia.com/api/v1/search"
    r = http_get(
        url,
        params={"query": query, "tags": "story", "hitsPerPage": 1000, "page": 0},
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return parse_hn(r.json(), query, f"https://hn.algolia.com/?q={quote(query)}")


def fetch_devto(tag):
    url = "https://dev.to/api/articles"
    r = http_get(
        url,
        params={"tag": tag, "per_page": 1000, "page": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return parse_devto(r.json(), f"https://dev.to/t/{tag}")


def fetch_rss(source):
    r = http_get(source["url"], headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return parse_rss(r.content, source)


def decode_response(response):
    """优先按 UTF-8 解码，避免官方站错误的 ISO-8859-1 charset 造成乱码。"""
    try:
        return response.content.decode("utf-8")
    except UnicodeDecodeError:
        return response.content.decode(response.apparent_encoding or "utf-8", errors="replace")


def fetch_official(source):
    r = http_get(source["url"], headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return parse_official(decode_response(r), source)


def run_task(kind, source):
    if kind == "github":
        text, url = fetch_github(source)
        candidates = parse_markdown(text, source)
        return source["name"], "github", url, candidates, None
    if kind == "hn":
        candidates = fetch_hn(source)
        return "Hacker News", "hn", f"https://hn.algolia.com/?q={quote(source)}", candidates, None
    if kind == "devto":
        candidates = fetch_devto(source)
        return "Dev.to", "devto", f"https://dev.to/t/{source}", candidates, None
    if kind == "rss":
        candidates = fetch_rss(source)
        return source["name"], "rss", source["url"], candidates, None
    if kind == "official":
        candidates = fetch_official(source)
        return source["name"], "official", source["url"], candidates, None
    raise ValueError(kind)


def upsert_candidates(cur, candidates):
    if not candidates:
        return 0, 0
    rows = []
    seen = set()
    for c in candidates:
        h = c["url_hash"]
        if h in seen:
            continue
        seen.add(h)
        rows.append((
            c["title"], c["type"], "candidate", c["source_name"], c["source_type"],
            c["source_url"], c["link"], c["summary"], c["canonical_url"], c["url_hash"],
            c["score"], c["promotion_score"], c["published_at"],
            Json(c["raw"], dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
        ))
    if not rows:
        return 0, 0
    execute_values(
        cur,
        """
        INSERT INTO wool_candidates
            (title, type, status, source_name, source_type, source_url, link,
             summary, canonical_url, url_hash, score, promotion_score, published_at, raw)
        VALUES %s
        ON CONFLICT (url_hash) DO UPDATE SET
            last_seen_at = now(),
            updated_at = now(),
            score = GREATEST(wool_candidates.score, EXCLUDED.score),
            promotion_score = GREATEST(wool_candidates.promotion_score, EXCLUDED.promotion_score),
            summary = COALESCE(NULLIF(EXCLUDED.summary, ''), wool_candidates.summary),
            type = CASE
                WHEN wool_candidates.type = '待分类' THEN EXCLUDED.type
                ELSE wool_candidates.type
            END,
            published_at = COALESCE(wool_candidates.published_at, EXCLUDED.published_at),
            source_name = COALESCE(wool_candidates.source_name, EXCLUDED.source_name),
            source_type = COALESCE(wool_candidates.source_type, EXCLUDED.source_type),
            source_url = COALESCE(wool_candidates.source_url, EXCLUDED.source_url)
        """,
        rows,
        page_size=200,
    )
    # execute_values 不容易拿逐行状态，这里用总数近似；精确新增数由任务前后 count 差值补充
    return len(rows), 0


def upsert_source(cur, name, source_type, url, status, count, error=None):
    cur.execute(
        """
        INSERT INTO wool_sources (name, source_type, url, last_fetch_at, last_status, last_error, last_count)
        VALUES (%s, %s, %s, now(), %s, %s, %s)
        ON CONFLICT (name, url) DO UPDATE SET
            last_fetch_at = now(),
            last_status = EXCLUDED.last_status,
            last_error = EXCLUDED.last_error,
            last_count = EXCLUDED.last_count,
            updated_at = now()
        """,
        (name, source_type, url or "", status, error, count),
    )


def harvest(config, workers=8, limit_sources=None):
    tasks = []
    for item in config.get("github", []):
        tasks.append(("github", item))
    for item in config.get("hn_queries", []):
        tasks.append(("hn", item))
    for item in config.get("devto_tags", []):
        tasks.append(("devto", item))
    for item in config.get("rss", []):
        tasks.append(("rss", item))
    for item in config.get("official", []):
        tasks.append(("official", item))
    if limit_sources:
        tasks = tasks[:limit_sources]

    stats = {
        "tasks": len(tasks),
        "ok": 0,
        "failed": 0,
        "raw_candidates": 0,
        "upserted": 0,
        "errors": [],
        "by_type": {},
    }
    pending = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(run_task, kind, source): (kind, source) for kind, source in tasks}
        for idx, future in enumerate(as_completed(futures), 1):
            kind, source = futures[future]
            try:
                name, stype, url, candidates, error = future.result()
                pending.extend(candidates)
                stats["raw_candidates"] += len(candidates)
                stats["ok"] += 1
                stats["by_type"][stype] = stats["by_type"].get(stype, 0) + len(candidates)
                with_conn = None
                # 每 5000 条落一次库，避免一次性占用太多内存
                if len(pending) >= 5000:
                    with_conn = connect()
                    try:
                        with with_conn:
                            with with_conn.cursor() as cur:
                                n, _ = upsert_candidates(cur, pending)
                                stats["upserted"] += n
                                upsert_source(cur, name, stype, url, "ok", len(candidates))
                    finally:
                        with_conn.close()
                    pending = []
                else:
                    with_conn = connect()
                    try:
                        with with_conn:
                            with with_conn.cursor() as cur:
                                upsert_source(cur, name, stype, url, "ok", len(candidates))
                    finally:
                        with_conn.close()
            except Exception as exc:
                stats["failed"] += 1
                err = f"{kind}:{source}: {exc}"[:1000]
                stats["errors"].append(err)
                name = source.get("name") if isinstance(source, dict) else str(source)
                url = source.get("url") if isinstance(source, dict) else ""
                try:
                    conn = connect()
                    try:
                        with conn:
                            with conn.cursor() as cur:
                                upsert_source(cur, name or kind, kind, url or "", "failed", 0, str(exc)[:1000])
                    finally:
                        conn.close()
                except Exception:
                    pass
            if idx % 20 == 0:
                print(f"  {idx}/{len(tasks)} sources, raw={stats['raw_candidates']}, upserted={stats['upserted']}, failed={stats['failed']}", flush=True)

    if pending:
        conn = connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    n, _ = upsert_candidates(cur, pending)
                    stats["upserted"] += n
        finally:
            conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=50000, help="目标候选总数，仅用于报告")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit-sources", type=int, default=0)
    parser.add_argument("--sources", default=str(SOURCES_FILE))
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.sources).read_text(encoding="utf-8")) or {}
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
                cur.execute(
                    "INSERT INTO daily_jobs (job_name, status) VALUES ('wool_harvest', 'running') RETURNING id"
                )
                job_id = cur.fetchone()[0]
    finally:
        conn.close()

    started = time.time()
    try:
        stats = harvest(config, workers=args.workers, limit_sources=args.limit_sources or None)
        conn = connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM wool_candidates")
                    total = cur.fetchone()[0]
                    stats["total_candidates"] = total
                    stats["elapsed_sec"] = round(time.time() - started, 1)
                    stats["target"] = args.target
                    stats["target_reached"] = total >= args.target
                    job_status = "failed" if stats.get("ok", 0) == 0 else (
                        "ok" if stats["failed"] == 0 else "partial"
                    )
                    cur.execute(
                        "UPDATE daily_jobs SET finished_at = now(), status = %s, stats = %s WHERE id = %s",
                        (job_status, Json(stats), job_id),
                    )
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM v_candidate_counts")
                counts = cur.fetchone()
        finally:
            conn.close()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        print("candidate counts:", counts)
        if stats.get("ok", 0) == 0:
            print("all sources failed; skip promotion", file=sys.stderr)
            raise SystemExit(2)
    except Exception as exc:
        conn = connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE daily_jobs SET finished_at = now(), status = 'failed', error = %s WHERE id = %s",
                        (str(exc)[:2000], job_id),
                    )
        finally:
            conn.close()
        raise


if __name__ == "__main__":
    main()
