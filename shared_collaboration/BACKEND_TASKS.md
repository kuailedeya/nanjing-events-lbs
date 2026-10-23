# 前后端协作工作规范与后端任务清单 (Frontend-Backend Collaboration)

## 1. 接口协议与契约 (API Contract)

### `GET /api/events`
前端已全面升级至 Apple HIG & Airbnb 空间探索系统，标点性能依赖精炼短标题与结构化字段。
返回的每个活动条目应包含以下字段：
- `id`: 唯一标识 (string / int)
- `title`: 完整标题
- `short_title`: 4~8 字精炼短标题（剥离营销前缀、括号和感叹词，遵循词边界，不截断英文单词）
- `category`: `南京展会` | `羊毛福利` | `南京活动`
- `sub_category`: 次级分类
- `start_date`: `YYYY-MM-DD`
- `end_date`: `YYYY-MM-DD`
- `days_left`: 剩余天数 (int)
- `time_status`: 状态标签 (如 `进行中`, `即将截止`, `常设展期`)
- `district`: 行政区 (如 `玄武区`, `鼓楼区`, `秦淮区`)
- `address`: 线下场馆真实物理地址
- `lat`: 纬度 (GCJ-02 火星坐标)
- `lng`: 经度 (GCJ-02 火星坐标)
- `is_free`: 1 (免费) 或 0 (收费)
- `benefit`: 门票/福利优惠说明 (如 `公共艺术区免费参观`, `立减10元`)
- `event_time_text`: 规范展示时间文本
- `summary`: 150字以内纯文本摘要
- `source_url`: 原文出处链接
- `obsidian_uri`: Obsidian 双向链接协议

### `POST /api/sync`
- 请求体：`{ "mode": "incremental" }`
- 响应：`{ "ok": true, "items": [...], "message": "增量同步完成" }` 或 `{ "ok": false, "error": "错误说明" }`
- 前端会捕获错误并通过 Apple HIG 胶囊 Toast 给予用户优雅反馈。

## 2. 后端待办任务 (Pending Backend Tasks for Backend Agent)
- [x] 在 `dashboard_server.py` 中增加 `extract_short_title` 并在事件对象中返回 `short_title` 字段。
- [x] 确保 SQLite 增量同步时自动清洗脏数据（去除重复活动、矫正火星坐标偏移至具体商圈，过滤超出南京行政边界的离群脏坐标）。
- [x] 确保 `/api/events` 支持 ETag 与 `If-None-Match`，在数据未变更时返回 `304 Not Modified`，并携带 `Cache-Control: public, max-age=60` 提升前台二次加载速度。
- [x] 为爬取的跨源活动海报增加轻量级防盗链图片代理（`GET /api/proxy/image?url=...` 防 SSRF 与防盗链白名单），防止小红书/微信公众号外链触发 403 碎图。
- [x] 补充对“江北新区”行政区划与商圈标签的聚类识别与自动打标。
