# -*- coding: utf-8 -*-
"""
把 PostgreSQL 候选池里的高置信“羊毛”提升为 Obsidian 笔记。

只提升以下来源：
  - 官方定价/免费额度页
  - GitHub 免费清单
  - Hacker News / RSS 中明确包含 credit、giveaway、student、free tier 等信号的条目

Dev.to 的“测评/对比/省钱教程”默认不提升，避免污染 Obsidian。

用法：
  python promote_candidates.py --limit 30
  python promote_candidates.py --limit 10 --dry-run
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from psycopg2.extras import RealDictCursor

from daily_wool_job import connect

VAULT_WOOL_DIR = Path(r"E:\Note storage\IOT\AI 羊毛与编程动态\数据\羊毛")

WOOL_TYPES = ("免费额度", "学生优惠", "限时免费", "免费云资源", "折扣", "活动", "免费课程", "免费工具")
TRUSTED_GITHUB_SOURCES = {
    "free-for-dev",
    "public-apis",
    "awesome-selfhosted",
    "free-programming-books-langs",
    "free-programming-books-subjects",
    "free-courses-en",
    "free-courses-zh",
    "free-certifications",
    "awesome-courses",
    "computer-science",
}
OFFER_TITLE_RE = re.compile(
    r"("
    r"\bfree\s+(credits?|tier|plan|trial|api|gpu|hosting|database|cloud|container|"
    r"maus?|users?|seats?|requests?|storage|usage|domain|ssl|email|course|bootcamp|"
    r"certification|tool|app|service|startup pack)\b"
    r"|\bfree\b.{0,30}\b(tools?|apps?|services?)\b"
    r"|\bfree\b.{0,80}\bcredits?\b"
    r"|\bcredits?\b.{0,80}\bfree\b"
    r"|\bcredits?\s+never\s+expire\b"
    r"|\bpasses\b"
    r"|\bstudent(s)?\b.{0,40}\b(free|discount|offer|credit|credits|plan|pack|benefit|trial)\b"
    r"|\b(free|discount|offer|credit|credits|plan|pack|benefit|trial)\b.{0,40}\bstudent(s)?\b"
    r"|\bgiveaway\b|\bcoupon\b|\bpromo code\b|\bno credit card\b"
    r")",
    re.I,
)
HARD_BLOCK_RE = re.compile(
    r"\b(review|vs\.?|alternatives?|comparison|compare|guide|how to|tutorial|"
    r"playbook|pricing|cost|costs|bill|salary|hiring|launch)\b",
    re.I,
)
# 这些词说明条目是“测评/工具/事故/教程”，不是可直接领取的羊毛，直接跳过。
ABSOLUTE_BLOCK_RE = re.compile(
    r"\b(playbook|calculator|calculators|dashboard|tracker|track|burning|burn|"
    r"audit|audits|consumes?|rogue|bill|bills|salary|hiring|best|guide|"
    r"tutorial|how to|legit|testing|test|review|pricing|complete cost|"
    r"discontinue|discontinued|ending|shutting|removes?|ask hn|musk|election|"
    r"voters|lawsuit|settles|is the new|air alert|built on|marketing asset|"
    r"gaming|gamers?|game|spinning ring|christmas|retry script|architecting|architecture)\b",
    re.I,
)
TECH_RE = re.compile(
    r"\b(ai|llm|model|token|code|coding|developer|api|cloud|gpu|database|hosting|"
    r"server|saas|devops|github|open source|self-hosted|data|web|domain|auth|email|"
    r"monitor|storage|programming|software|agent|mcp|infra|platform)\b",
    re.I,
)
EXPLICIT_WOOL_RE = re.compile(
    r"(free credits|free tier|free plan|free cloud|free container|free maus?|"
    r"free users?|credits never expire|giveaway|student(s)?|coupon|promo code|"
    r"no credit card|passes)",
    re.I,
)
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(title: str) -> str:
    name = INVALID_FILENAME.sub(" ", title)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if len(name) > 80:
        name = name[:80].rstrip()
    return name or "未命名羊毛"


def yaml_str(value: str) -> str:
    value = "".join(ch for ch in str(value or "") if not (0x7F <= ord(ch) <= 0x9F))
    return json.dumps(value, ensure_ascii=False)


def note_exists_with_link(path: Path, link: str) -> bool:
    if not path.exists():
        return False
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except Exception:
        return False
    return f"link: {yaml_str(link)}" in head or f'link: "{link}"' in head


def render_note(row: dict) -> str:
    title = row.get("display_title") or row["title"]
    summary = (row["summary"] or "").strip()
    summary = "".join(ch for ch in summary if not (0x7F <= ord(ch) <= 0x9F))
    source = row["source_name"] or "候选池"
    link = row["link"]
    type_name = row["type"] if row["type"] in WOOL_TYPES else "免费额度"
    extra = ""
    if summary:
        extra = f"> [!note] 备注\n> {summary}\n"
    return f"""---
type: {yaml_str(type_name)}
status: "待核实"
deadline:
source: {yaml_str(source)}
link: {yaml_str(link)}
details: {yaml_str(summary)}
tags:
  - AI羊毛/条目
candidate_id: {row["id"]}
promotion_score: {row["promotion_score"]}
---

# {title}

- 类型：{type_name}
- 状态：待核实
- 截止：未标注
- 来源：{source}
- 原文：[打开]({link})

{extra}> 该条由候选池自动提升，领取前请核实活动是否仍有效。

## 相关

- [[羊毛库]]
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--min-score", type=int, default=70)
    parser.add_argument("--include-devto", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    VAULT_WOOL_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    created = 0
    duplicates = 0
    skipped = 0
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, title, type, source_name, source_type, link, summary,
                       score, promotion_score, published_at
                FROM wool_candidates
                WHERE status = 'candidate'
                  AND promotion_score >= %s
                  AND link IS NOT NULL
                  AND type = ANY(%s)
                ORDER BY
                  CASE source_type
                    WHEN 'official' THEN 0
                    WHEN 'hn' THEN 1
                    WHEN 'github' THEN 2
                    WHEN 'rss' THEN 3
                    ELSE 4
                  END,
                  promotion_score DESC,
                  score DESC,
                  published_at DESC NULLS LAST
                LIMIT 1000
                """,
                (args.min_score, list(WOOL_TYPES)),
            )
            rows = cur.fetchall()

        for row in rows:
            if created >= args.limit:
                break
            source_type = row["source_type"]
            text = f"{row['title']} {row['summary'] or ''}"

            if source_type == "github" and row["source_name"] not in TRUSTED_GITHUB_SOURCES:
                skipped += 1
                continue
            if source_type == "devto" and not args.include_devto:
                skipped += 1
                continue
            if source_type in {"hn", "rss", "devto"}:
                if ABSOLUTE_BLOCK_RE.search(row["title"]):
                    skipped += 1
                    continue
                if source_type in {"hn", "rss"} and not TECH_RE.search(text):
                    skipped += 1
                    continue
                if not OFFER_TITLE_RE.search(row["title"]):
                    skipped += 1
                    continue
                if HARD_BLOCK_RE.search(row["title"]) and not EXPLICIT_WOOL_RE.search(text):
                    skipped += 1
                    continue
            if source_type not in {"official", "github", "hn", "rss", "devto"}:
                skipped += 1
                continue

            if source_type == "official":
                row["display_title"] = row["source_name"] or row["title"]
            else:
                row["display_title"] = row["title"]

            link = row["link"]
            # 已存在于羊毛库：只标记候选，不重复建笔记
            with conn.cursor() as cur:
                cur.execute("SELECT file_path FROM wool_items WHERE link = %s LIMIT 1", (link,))
                existing = cur.fetchone()
            if existing:
                if not args.dry_run:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE wool_candidates SET status='promoted', "
                                "promoted_note_path=%s, promoted_at=now(), updated_at=now() "
                                "WHERE id=%s",
                                (existing[0], row["id"]),
                            )
                duplicates += 1
                continue

            base = safe_filename(row["display_title"])
            path = VAULT_WOOL_DIR / f"{base}.md"
            if path.exists() and not note_exists_with_link(path, link):
                suffix = hashlib.sha256(link.encode("utf-8")).hexdigest()[:6]
                path = VAULT_WOOL_DIR / f"{base} - {suffix}.md"
            if note_exists_with_link(path, link):
                if not args.dry_run:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE wool_candidates SET status='promoted', "
                                "promoted_note_path=%s, promoted_at=now(), updated_at=now() "
                                "WHERE id=%s",
                                (str(path), row["id"]),
                            )
                duplicates += 1
                continue

            print(f"+ {row['promotion_score']:>3} | {row['type']} | {row['display_title'][:80]} -> {path.name}")
            if args.dry_run:
                created += 1
                continue

            path.write_text(render_note(row), encoding="utf-8")
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE wool_candidates SET status='promoted', "
                        "promoted_note_path=%s, promoted_at=now(), updated_at=now() "
                        "WHERE id=%s",
                        (str(path), row["id"]),
                    )
            created += 1

        print(
            json.dumps(
                {
                    "created": created,
                    "duplicates": duplicates,
                    "skipped": skipped,
                    "limit": args.limit,
                    "dry_run": args.dry_run,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
