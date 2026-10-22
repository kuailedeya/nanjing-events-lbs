# -*- coding: utf-8 -*-
"""重新抓取官方页面，清理自动提升笔记里的导航噪音。"""

import json
import re
from pathlib import Path

import requests

from daily_wool_job import TIMEOUT, USER_AGENT, connect, decode_response, parse_official


def yaml_str(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def main():
    conn = connect()
    updated = 0
    failed = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source_name, source_url, promoted_note_path
                FROM wool_candidates
                WHERE source_type = 'official'
                  AND status = 'promoted'
                  AND promoted_note_path IS NOT NULL
                """
            )
            rows = cur.fetchall()

        for row_id, source_name, source_url, note_path in rows:
            try:
                r = requests.get(source_url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
                r.raise_for_status()
                parsed = parse_official(decode_response(r), {"name": source_name, "url": source_url})
                if not parsed:
                    failed += 1
                    continue
                summary = (parsed[0].get("summary") or "").strip()
                if not summary:
                    failed += 1
                    continue
                path = Path(note_path)
                if not path.exists():
                    failed += 1
                    continue
                text = path.read_text(encoding="utf-8")
                parts = text.split("---", 2)
                if len(parts) < 3:
                    failed += 1
                    continue
                fm, body = parts[1], parts[2]
                fm = re.sub(r"(?m)^details:.*$", "details: " + yaml_str(summary), fm)
                body = re.sub(
                    r"> \[!note\] 备注\n(?:>.*\n)*",
                    "> [!note] 备注\n"
                    f"> {summary}\n"
                    "> 该条由候选池自动提升，领取前请核实活动是否仍有效。\n",
                    body,
                )
                path.write_text("---" + fm + "---" + body, encoding="utf-8")
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE wool_candidates SET summary=%s, updated_at=now() WHERE id=%s",
                            (summary, row_id),
                        )
                updated += 1
                print(f"~ {source_name}: {summary[:120]}")
            except Exception as exc:
                failed += 1
                print(f"! {source_name}: {exc}")

        print(json.dumps({"updated": updated, "failed": failed}, ensure_ascii=False))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
