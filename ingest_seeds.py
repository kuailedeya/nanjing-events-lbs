# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, r"E:\usage")
import social_obsidian_sync
import nanjing_lbs_engine
from nanjing_seeds import NANJING_COMPREHENSIVE_SEEDS

def run():
    print(f"[*] 开始将 {len(NANJING_COMPREHENSIVE_SEEDS)} 条全域基准情报注入 Obsidian 结构化数据库...")
    db = social_obsidian_sync.ObsidianSummaryDB()
    for s in NANJING_COMPREHENSIVE_SEEDS:
        db.save_record(s)

    print("[*] 正在生成 Obsidian 原生 Bases 数据库与 Markdown 总览表...")
    db.build_base_and_dashboard()

    print("[*] 正在执行南京 LBS 空间引擎全量同步与智能去重...")
    items = nanjing_lbs_engine.migrate_and_sync_all()
    print(f"[✓] 同步完成！当前数据库有效高精度活动总数: {len(items)} 条")

    # 统计 11 行政区分布
    district_counts = {}
    for it in items:
        dist = it.get("district", "未归类")
        district_counts[dist] = district_counts.get(dist, 0) + 1

    print("[*] 各行政区分布统计:")
    for dist, count in sorted(district_counts.items(), key=lambda x: -x[1]):
        print(f"    - {dist}: {count} 条")

if __name__ == "__main__":
    run()
