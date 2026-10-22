# AI 情报 PostgreSQL

把 Obsidian「AI 羊毛与编程动态」的数据同步到本地 PostgreSQL。Obsidian 仍是编辑源，PostgreSQL 是可查询、可接 BI / API 的镜像。

## 连接信息

| 项 | 值 |
|---|---|
| Host | `127.0.0.1` |
| Port | `5433` |
| Database | `ai_intel` |
| User | `ai_intel` |
| Password | 见同目录 `.env` 的 `POSTGRES_PASSWORD` |
| 容器名 | `ai-intel-postgres` |

连接串模板：

```text
postgresql://ai_intel:<password>@127.0.0.1:5433/ai_intel
```

密码在 `E:\usage\ai-intel-postgres\.env`，不要提交到 Git。

## 启动 / 停止

```powershell
cd E:\usage\ai-intel-postgres
docker compose up -d
docker compose ps
docker compose logs -f postgres
docker compose stop
```

只开放本机访问（`127.0.0.1:5433`），局域网其他机器连不上。

## 同步数据

Obsidian 里的笔记更新后，执行：

```powershell
python E:\usage\ai-intel-postgres\sync_to_postgres.py
```

脚本会：

1. 自动建表、建索引、建视图；
2. 读取 `E:\Note storage\IOT\AI 羊毛与编程动态` 下的羊毛、动态、账号、日报；
3. 以文件路径为唯一键做 upsert，重复执行不会产生重复行；
4. 用内容哈希判断是否真的变化，未变化时保留原 `updated_at`。

依赖：Python 3.10+，以及 `pip install psycopg2-binary pyyaml requests feedparser beautifulsoup4`。

## 候选池与每日任务

Obsidian 只保留高置信、可核验的羊毛；全量候选放在 PostgreSQL，避免 10 万级 `.md` 拖慢 Bases 和搜索。

```powershell
# 手动采集一轮（247 个源/查询，写入 wool_candidates）
python E:\usage\ai-intel-postgres\daily_wool_job.py --target 50000

# 把高分候选提升为 Obsidian 笔记（默认 20 条/天）
python E:\usage\ai-intel-postgres\promote_candidates.py --limit 20

# 同步回 PostgreSQL
python E:\usage\ai-intel-postgres\sync_to_postgres.py
```

每日 08:00 的 Windows 计划任务 `AI Wool Daily` 会依次执行上面三步，入口是：

```text
E:\usage\ai-intel-postgres\run_daily.bat
```

查看任务：

```powershell
Get-ScheduledTask -TaskName 'AI Wool Daily'
Get-ScheduledTaskInfo -TaskName 'AI Wool Daily'
```

日志：`E:\usage\ai-intel-postgres\logs\daily_wool.log`。

采集源配置在 `sources.yaml`，可以增删 GitHub 清单、HN 搜索词、Dev.to 标签、RSS 和官方页面。单个源失败只会记录错误，不会中断整轮。

> 如果整轮 **0 个源成功**，`daily_wool_job.py` 会以退出码 2 结束，`run_daily.bat` 跳过提升，避免拿旧候选充数；但仍会同步现有 Obsidian 数据。

> 101,289 条是候选档案，不等于 10 万条都能领。`promotion_score` 达到阈值的条目才会进入 Obsidian，且默认标为「待核实」。

## 存档

2026-10-22 的系统快照（含数据库 dump、脚本包、Obsidian 整库、交接提示词）：

```text
E:\usage\ai-intel-postgres\archive\2026-10-22\
```

浏览器打开：`file:///E:/usage/ai-intel-postgres/archive/2026-10-22/index.html`

重建存档：

```powershell
python E:\usage\ai-intel-postgres\make_archive.py
```

## 表

| 表 | 内容 | 唯一键 |
|---|---|---|
| `wool_items` | Obsidian 中精选的羊毛 / 免费额度 / 学生优惠 | `file_path` |
| `wool_candidates` | 全量候选档案，含评分、来源、提升状态 | `url_hash` |
| `wool_sources` | 采集源状态、上次抓取时间、错误 | `(name, url)` |
| `daily_jobs` | 每日采集任务日志与统计 | `id` |
| `news_items` | AI 编程、模型、Agent 动态 | `file_path` |
| `accounts` | 信源账号池 | `file_path` |
| `daily_reports` | 每日报告，含完整 Markdown | `report_date` |

每条记录同时保留：

- 结构化字段（状态、截止日、主题、互动数等）
- `body_md` / `content_md`：原始笔记正文
- `content_hash`：用于增量同步
- `created_at` / `updated_at` / `synced_at`

## 视图

| 视图 | 用途 |
|---|---|
| `v_counts` | 各表总数、即将截止数、进行中数量 |
| `v_wool_active` | 未过期羊毛，按紧急程度和截止日排序 |
| `v_wool_deadlines` | 有明确截止日、且未过期的羊毛，带剩余天数 |
| `v_news_recent` | 动态按日期、互动量倒序 |
| `v_candidate_counts` | 候选池总数、高分、已提升、平均分 |
| `v_candidate_sources` | 各采集源的候选数量、平均分、最近抓取 |
| `v_wool_candidates` | 高置信、科技相关的候选（`promotion_score >= 70`），按分数排序 |

## 常用查询

```sql
-- 总览
SELECT * FROM v_counts;

-- 最近要截止的羊毛
SELECT name, status, deadline, days_left
FROM v_wool_deadlines
ORDER BY deadline
LIMIT 20;

-- 按状态统计
SELECT status, count(*)
FROM wool_items
GROUP BY status
ORDER BY count(*) DESC;

-- 按主题看动态
SELECT topic, count(*)
FROM news_items
GROUP BY topic
ORDER BY count(*) DESC;

-- 搜索动态标题 / 摘要
SELECT title, topic, published_date, engagement, link
FROM news_items
WHERE title ILIKE '%Claude%' OR summary ILIKE '%Claude%'
ORDER BY published_date DESC, engagement DESC;

-- 最新日报的统计字段
SELECT report_date, title, wool_total, news_total, wool_added, news_added
FROM daily_reports
ORDER BY report_date DESC;

-- 候选池总览
SELECT * FROM v_candidate_counts;

-- 高置信候选
SELECT * FROM v_wool_candidates LIMIT 30;

-- 采集源健康度
SELECT * FROM v_candidate_sources LIMIT 20;

-- 最近一次采集任务
SELECT job_name, started_at, finished_at, status, stats
FROM daily_jobs
ORDER BY started_at DESC
LIMIT 5;
```

## 进入 psql

```powershell
docker exec -it ai-intel-postgres psql -U ai_intel -d ai_intel
```

退出：`\q`

## 备份

```powershell
docker exec ai-intel-postgres pg_dump -U ai_intel -d ai_intel -Fc -f /tmp/ai_intel.dump
docker cp ai-intel-postgres:/tmp/ai_intel.dump .\ai_intel.dump
```

恢复：

```powershell
docker cp .\ai_intel.dump ai-intel-postgres:/tmp/ai_intel.dump
docker exec -it ai-intel-postgres pg_restore -U ai_intel -d ai_intel --clean --if-exists /tmp/ai_intel.dump
```

## 说明

- 这是本机开发库，密码和端口只适合本机使用。
- 如果以后要换成远程 PostgreSQL，改 `sync_to_postgres.py` 顶部的连接参数，或加 `DATABASE_URL` 支持。
- 不建议直接改数据库里的记录；下一次同步会以 Obsidian 文件为准覆盖对应字段。
