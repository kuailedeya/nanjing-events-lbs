# -*- coding: utf-8 -*-
"""一次性回填 wool_candidates.promotion_score。"""

from psycopg2.extras import execute_values

from daily_wool_job import connect, promotion_score_candidate


def main():
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "ALTER TABLE wool_candidates "
                    "ADD COLUMN IF NOT EXISTS promotion_score INTEGER NOT NULL DEFAULT 0"
                )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, summary, type, source_type, published_at "
                "FROM wool_candidates"
            )
            rows = cur.fetchall()

        updates = []
        for row_id, title, summary, type_name, source_type, published_at in rows:
            score = promotion_score_candidate(
                title or "", summary or "", type_name or "", source_type or "", published_at
            )
            updates.append((row_id, score))

        with conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    UPDATE wool_candidates AS w
                    SET promotion_score = v.promotion_score
                    FROM (VALUES %s) AS v(id, promotion_score)
                    WHERE w.id = v.id
                    """,
                    updates,
                    page_size=2000,
                )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT promotion_score, count(*) FROM wool_candidates "
                "GROUP BY promotion_score ORDER BY promotion_score DESC"
            )
            dist = cur.fetchall()
        print(f"backfilled {len(updates)} rows")
        print("promotion_score distribution (score, count):")
        for score, count in dist:
            print(f"  {score}: {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
