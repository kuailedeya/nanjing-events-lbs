# -*- coding: utf-8 -*-
"""Create a dated local archive of the AI wool system.

Archives:
  - PostgreSQL dump (gzip)
  - project scripts/config (no .env)
  - Obsidian vault zip
  - CSV indexes and state.json
"""

import csv
import gzip
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT = Path(r"E:\usage\ai-intel-postgres")
VAULT = Path(r"E:\Note storage\IOT\AI 羊毛与编程动态")
ARCHIVE = PROJECT / "archive" / "2026-10-22"

sys.path.insert(0, str(PROJECT))
from daily_wool_job import connect  # noqa: E402


def query_counts():
    conn = connect()
    cur = conn.cursor()
    result = {}
    for key, sql in {
        "wool_items": "SELECT count(*) FROM wool_items",
        "news_items": "SELECT count(*) FROM news_items",
        "accounts": "SELECT count(*) FROM accounts",
        "daily_reports": "SELECT count(*) FROM daily_reports",
        "wool_candidates": "SELECT count(*) FROM wool_candidates",
        "candidate": "SELECT count(*) FROM wool_candidates WHERE status='candidate'",
        "promoted": "SELECT count(*) FROM wool_candidates WHERE status='promoted'",
        "rejected": "SELECT count(*) FROM wool_candidates WHERE status='rejected'",
        "promotion_ge_70": "SELECT count(*) FROM wool_candidates WHERE promotion_score >= 70",
        "score_ge_70": "SELECT count(*) FROM wool_candidates WHERE score >= 70",
        "high_signal_view": "SELECT count(*) FROM v_wool_candidates",
    }.items():
        cur.execute(sql)
        result[key] = cur.fetchone()[0]
    cur.execute("SELECT status, count(*) FROM wool_items GROUP BY status ORDER BY count(*) DESC")
    result["wool_status"] = dict(cur.fetchall())
    cur.close()
    conn.close()
    return result


def export_notes():
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT name, type, status, deadline, source, link, file_path "
        "FROM wool_items ORDER BY name"
    )
    with (ARCHIVE / "notes-index.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "type", "status", "deadline", "source", "link", "file_path"])
        writer.writerows(cur.fetchall())
    cur.close()
    conn.close()


def export_high_signal():
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, promotion_score, score, type, source_name, title, link, summary "
        "FROM v_wool_candidates ORDER BY promotion_score DESC, score DESC"
    )
    with (ARCHIVE / "candidates-high-signal.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "promotion_score", "score", "type", "source", "title", "link", "summary"])
        writer.writerows(cur.fetchall())
    cur.close()
    conn.close()


def dump_database():
    target = ARCHIVE / "db.sql.gz"
    cmd = [
        "docker", "compose", "exec", "-T", "postgres",
        "pg_dump", "-U", "ai_intel", "-d", "ai_intel",
        "--no-owner", "--no-privileges",
    ]
    with gzip.open(target, "wb") as out:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.stdout is not None
        shutil.copyfileobj(proc.stdout, out)
        err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        if proc.wait() != 0:
            raise RuntimeError(f"pg_dump failed: {err}")
    return target


def zip_project():
    target = ARCHIVE / "project.zip"
    names = [
        "daily_wool_job.py",
        "promote_candidates.py",
        "sync_to_postgres.py",
        "refresh_official_notes.py",
        "backfill_promotion_scores.py",
        "make_archive.py",
        "run_daily.bat",
        "sources.yaml",
        "docker-compose.yml",
        "README.md",
        ".gitignore",
    ]
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            path = PROJECT / name
            if path.exists():
                z.write(path, name)
    return target


def zip_vault():
    target = ARCHIVE / "obsidian-ai-wool.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in VAULT.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(VAULT))
    return target


def main():
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    counts = query_counts()
    export_notes()
    export_high_signal()
    db_path = dump_database()
    project_zip = zip_project()
    vault_zip = zip_vault()
    state = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "counts": counts,
        "archive_dir": str(ARCHIVE),
        "db_backup": str(db_path),
        "project_zip": str(project_zip),
        "vault_zip": str(vault_zip),
    }
    (ARCHIVE / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(state, ensure_ascii=False, indent=2))
    for path in [db_path, project_zip, vault_zip]:
        print(f"{path} | {path.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
