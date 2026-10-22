#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 Obsidian「AI 羊毛与编程动态」数据同步到 PostgreSQL。

数据源：
  E:\\Note storage\\IOT\\AI 羊毛与编程动态\\数据\\羊毛
  E:\\Note storage\\IOT\\AI 羊毛与编程动态\\数据\\动态
  E:\\Note storage\\IOT\\AI 羊毛与编程动态\\数据\\账号
  E:\\Note storage\\IOT\\AI 羊毛与编程动态\\日报

用法：
  python E:\\usage\\ai-intel-postgres\\sync_to_postgres.py
"""

import hashlib
import os
import re
from datetime import date, datetime
from pathlib import Path

import psycopg2
import yaml
from psycopg2.extras import execute_values

VAULT = Path(r"E:\Note storage\IOT")
ROOT = VAULT / "AI 羊毛与编程动态"
ENV_FILE = Path(__file__).with_name(".env")


def load_env() -> dict:
    env = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def read_note(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text, text
    fm_text = "".join(ch for ch in parts[1] if not (0x7F <= ord(ch) <= 0x9F))
    fm = yaml.safe_load(fm_text) or {}
    body = parts[2].lstrip("\n")
    return fm, body, text


def as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def as_int(value):
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None


def as_text(value):
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    s = str(value).strip()
    return s or None


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_callout(body: str, title: str):
    pattern = rf"> \[!note\] {re.escape(title)}\n((?:>.*\n?)*)"
    m = re.search(pattern, body)
    if not m:
        return None
    lines = []
    for line in m.group(1).splitlines():
        line = line[1:].lstrip() if line.startswith(">") else line
        if line:
            lines.append(line)
    return " ".join(lines).strip() or None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wool_items (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT,
    status          TEXT NOT NULL,
    deadline        DATE,
    source          TEXT,
    link            TEXT,
    details         TEXT,
    body_md         TEXT NOT NULL,
    file_path       TEXT NOT NULL UNIQUE,
    content_hash    CHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wool_status ON wool_items(status);
CREATE INDEX IF NOT EXISTS idx_wool_deadline ON wool_items(deadline);
CREATE INDEX IF NOT EXISTS idx_wool_name ON wool_items(name);

CREATE TABLE IF NOT EXISTS news_items (
    id              BIGSERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    topic           TEXT,
    published_date  DATE NOT NULL,
    engagement      INTEGER,
    source          TEXT,
    link            TEXT,
    summary         TEXT,
    body_md         TEXT NOT NULL,
    file_path       TEXT NOT NULL UNIQUE,
    content_hash    CHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_news_date ON news_items(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_news_topic ON news_items(topic);
CREATE INDEX IF NOT EXISTS idx_news_engagement ON news_items(engagement DESC);
CREATE INDEX IF NOT EXISTS idx_news_title ON news_items(title);

CREATE TABLE IF NOT EXISTS accounts (
    id              BIGSERIAL PRIMARY KEY,
    handle          TEXT NOT NULL,
    category        TEXT,
    link            TEXT,
    body_md         TEXT NOT NULL,
    file_path       TEXT NOT NULL UNIQUE,
    content_hash    CHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_accounts_category ON accounts(category);
CREATE INDEX IF NOT EXISTS idx_accounts_handle ON accounts(handle);

CREATE TABLE IF NOT EXISTS daily_reports (
    id              BIGSERIAL PRIMARY KEY,
    report_date     DATE NOT NULL UNIQUE,
    title           TEXT,
    file_path       TEXT NOT NULL UNIQUE,
    wool_total      INTEGER,
    news_total      INTEGER,
    wool_added      INTEGER,
    news_added      INTEGER,
    accounts        INTEGER,
    account_pool    INTEGER,
    candidates      INTEGER,
    updated_label   TEXT,
    content_md      TEXT NOT NULL,
    content_hash    CHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_reports(report_date DESC);

CREATE OR REPLACE VIEW v_wool_active AS
SELECT
    name, type, status, deadline, source, link, details,
    CASE status
        WHEN '即将截止' THEN 0
        WHEN '进行中' THEN 1
        WHEN '待核实' THEN 2
        ELSE 3
    END AS status_rank
FROM wool_items
WHERE status <> '已过期'
ORDER BY status_rank, deadline NULLS LAST, name;

CREATE OR REPLACE VIEW v_wool_deadlines AS
SELECT
    name, type, status, deadline,
    (deadline - CURRENT_DATE) AS days_left,
    source, link
FROM wool_items
WHERE deadline IS NOT NULL
  AND deadline >= CURRENT_DATE
  AND status <> '已过期'
ORDER BY deadline, name;

CREATE OR REPLACE VIEW v_news_recent AS
SELECT
    title, topic, published_date, engagement, source, link, summary
FROM news_items
ORDER BY published_date DESC, engagement DESC NULLS LAST;

CREATE OR REPLACE VIEW v_counts AS
SELECT
    (SELECT count(*) FROM wool_items) AS wool_items,
    (SELECT count(*) FROM news_items) AS news_items,
    (SELECT count(*) FROM accounts) AS accounts,
    (SELECT count(*) FROM daily_reports) AS daily_reports,
    (SELECT count(*) FROM wool_items WHERE status = '即将截止') AS wool_urgent,
    (SELECT count(*) FROM wool_items WHERE status = '进行中') AS wool_active;
"""


def sync_wool(cur):
    folder = ROOT / "数据" / "羊毛"
    rows = []
    for path in sorted(folder.glob("*.md")):
        try:
            fm, body, text = read_note(path)
        except Exception as exc:
            raise RuntimeError(f"读取羊毛笔记失败: {path}: {exc}") from exc
        rel = path.relative_to(VAULT).as_posix()
        rows.append((
            path.stem,
            as_text(fm.get("type")),
            as_text(fm.get("status")) or "待核实",
            as_date(fm.get("deadline")),
            as_text(fm.get("source")),
            as_text(fm.get("link")),
            as_text(fm.get("details")),
            body,
            rel,
            content_hash(text),
        ))
    if not rows:
        return 0
    execute_values(
        cur,
        """
        INSERT INTO wool_items
            (name, type, status, deadline, source, link, details,
             body_md, file_path, content_hash)
        VALUES %s
        ON CONFLICT (file_path) DO UPDATE SET
            name = EXCLUDED.name,
            type = EXCLUDED.type,
            status = EXCLUDED.status,
            deadline = EXCLUDED.deadline,
            source = EXCLUDED.source,
            link = EXCLUDED.link,
            details = EXCLUDED.details,
            body_md = EXCLUDED.body_md,
            content_hash = EXCLUDED.content_hash,
            updated_at = CASE
                WHEN wool_items.content_hash IS DISTINCT FROM EXCLUDED.content_hash
                THEN now() ELSE wool_items.updated_at END,
            synced_at = now()
        """,
        rows,
        page_size=100,
    )
    cur.execute(
        "DELETE FROM wool_items WHERE NOT (file_path = ANY(%s))",
        ([r[8] for r in rows],),
    )
    return len(rows)


def sync_news(cur):
    folder = ROOT / "数据" / "动态"
    rows = []
    for path in sorted(folder.glob("*.md")):
        fm, body, text = read_note(path)
        rel = path.relative_to(VAULT).as_posix()
        summary = as_text(fm.get("summary")) or extract_callout(body, "摘要")
        rows.append((
            path.stem,
            as_text(fm.get("topic")),
            as_date(fm.get("date")),
            as_int(fm.get("engagement")),
            as_text(fm.get("source")),
            as_text(fm.get("link")),
            summary,
            body,
            rel,
            content_hash(text),
        ))
    if not rows:
        return 0
    execute_values(
        cur,
        """
        INSERT INTO news_items
            (title, topic, published_date, engagement, source, link,
             summary, body_md, file_path, content_hash)
        VALUES %s
        ON CONFLICT (file_path) DO UPDATE SET
            title = EXCLUDED.title,
            topic = EXCLUDED.topic,
            published_date = EXCLUDED.published_date,
            engagement = EXCLUDED.engagement,
            source = EXCLUDED.source,
            link = EXCLUDED.link,
            summary = EXCLUDED.summary,
            body_md = EXCLUDED.body_md,
            content_hash = EXCLUDED.content_hash,
            updated_at = CASE
                WHEN news_items.content_hash IS DISTINCT FROM EXCLUDED.content_hash
                THEN now() ELSE news_items.updated_at END,
            synced_at = now()
        """,
        rows,
        page_size=100,
    )
    cur.execute(
        "DELETE FROM news_items WHERE NOT (file_path = ANY(%s))",
        ([r[8] for r in rows],),
    )
    return len(rows)


def sync_accounts(cur):
    folder = ROOT / "数据" / "账号"
    rows = []
    for path in sorted(folder.glob("*.md")):
        fm, body, text = read_note(path)
        rel = path.relative_to(VAULT).as_posix()
        rows.append((
            as_text(fm.get("handle")) or path.stem,
            as_text(fm.get("category")),
            as_text(fm.get("link")),
            body,
            rel,
            content_hash(text),
        ))
    if not rows:
        return 0
    execute_values(
        cur,
        """
        INSERT INTO accounts
            (handle, category, link, body_md, file_path, content_hash)
        VALUES %s
        ON CONFLICT (file_path) DO UPDATE SET
            handle = EXCLUDED.handle,
            category = EXCLUDED.category,
            link = EXCLUDED.link,
            body_md = EXCLUDED.body_md,
            content_hash = EXCLUDED.content_hash,
            updated_at = CASE
                WHEN accounts.content_hash IS DISTINCT FROM EXCLUDED.content_hash
                THEN now() ELSE accounts.updated_at END,
            synced_at = now()
        """,
        rows,
        page_size=100,
    )
    cur.execute(
        "DELETE FROM accounts WHERE NOT (file_path = ANY(%s))",
        ([r[4] for r in rows],),
    )
    return len(rows)


def sync_daily(cur):
    folder = ROOT / "日报"
    rows = []
    for path in sorted(folder.glob("*.md")):
        fm, body, text = read_note(path)
        rel = path.relative_to(VAULT).as_posix()
        rows.append((
            as_date(fm.get("date")),
            as_text(fm.get("title")) or path.stem,
            rel,
            as_int(fm.get("wool_total")),
            as_int(fm.get("news_total")),
            as_int(fm.get("wool_added")),
            as_int(fm.get("news_added")),
            as_int(fm.get("accounts")),
            as_int(fm.get("account_pool")),
            as_int(fm.get("candidates")),
            as_text(fm.get("updated")),
            text,
            content_hash(text),
        ))
    if not rows:
        return 0
    execute_values(
        cur,
        """
        INSERT INTO daily_reports
            (report_date, title, file_path, wool_total, news_total,
             wool_added, news_added, accounts, account_pool, candidates,
             updated_label, content_md, content_hash)
        VALUES %s
        ON CONFLICT (report_date) DO UPDATE SET
            title = EXCLUDED.title,
            file_path = EXCLUDED.file_path,
            wool_total = EXCLUDED.wool_total,
            news_total = EXCLUDED.news_total,
            wool_added = EXCLUDED.wool_added,
            news_added = EXCLUDED.news_added,
            accounts = EXCLUDED.accounts,
            account_pool = EXCLUDED.account_pool,
            candidates = EXCLUDED.candidates,
            updated_label = EXCLUDED.updated_label,
            content_md = EXCLUDED.content_md,
            content_hash = EXCLUDED.content_hash,
            updated_at = CASE
                WHEN daily_reports.content_hash IS DISTINCT FROM EXCLUDED.content_hash
                THEN now() ELSE daily_reports.updated_at END,
            synced_at = now()
        """,
        rows,
        page_size=50,
    )
    cur.execute(
        "DELETE FROM daily_reports WHERE NOT (file_path = ANY(%s))",
        ([r[2] for r in rows],),
    )
    return len(rows)


def main():
    env = load_env()
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=int(env.get("POSTGRES_PORT", "5433")),
        dbname=env.get("POSTGRES_DB", "ai_intel"),
        user=env.get("POSTGRES_USER", "ai_intel"),
        password=env["POSTGRES_PASSWORD"],
        connect_timeout=10,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
                n_wool = sync_wool(cur)
                n_news = sync_news(cur)
                n_accounts = sync_accounts(cur)
                n_daily = sync_daily(cur)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT count(*) FROM wool_items),
                    (SELECT count(*) FROM news_items),
                    (SELECT count(*) FROM accounts),
                    (SELECT count(*) FROM daily_reports)
            """)
            counts = cur.fetchone()
        print(f"synced wool={n_wool} news={n_news} accounts={n_accounts} daily={n_daily}")
        print(f"db counts: wool={counts[0]} news={counts[1]} accounts={counts[2]} daily={counts[3]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
