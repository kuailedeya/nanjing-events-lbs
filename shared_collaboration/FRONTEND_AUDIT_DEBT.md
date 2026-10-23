# 前端深度代码与交互审计报告 (Frontend Audit & Resolution Record)

本文档由前端工程师归纳沉淀，记录经过深挖发现的前端性能、移动端适配、时区容灾、包体积与 Apple HIG 交互规范层面的问题与已落地的重构修复成果。

---

## 一、 第二轮深挖与已解决的新技术债 (Second Wave Audit & Fixes)

### 1. 地图 Marker 远景文字严重重叠挤压 (LOD 层级缺失)
- **深挖定位**：当用户缩放地图至全城尺度（`zoom < 12`）时，74 个宽达 120px 的 Airbnb 药丸同时渲染在视野中，南京主城区标点重叠堆积，变成无法阅读的色块。
- **重构解决**：引入 **Marker Level of Detail (LOD)** 机制。
  - 在 Leaflet `zoomend` 监听缩放层级：`zoom < 12` 时，全局激活 `.map-zoomed-out` 类名，标点文字自动平滑收缩为 8px 紧凑圆形实体色彩圆点。
  - 当放大至街区层级（`zoom >= 12`）或鼠标悬停/聚焦时，标点物理展开为完整标题与价格胶囊。
- **效果**：大尺度视野极其清爽整洁，微观尺度信息丰富饱满。

### 2. URL 深度直达链接缺失 (Deep Linking)
- **深挖定位**：用户在抽屉中选定或打开某个活动详情时，浏览器 URL 无任何参数变化，无法将指定活动链接直接分享给好友，刷新页面后选中的活动状态丢失。
- **重构解决**：
  - 引入 URL 查询参数无刷新同步：展开活动时触发 `history.replaceState(null, '', '?id=' + item.id)`，关闭详情时自动清除参数。
  - 页面初次加载时自动解析 `?id=...`，匹配目标活动并以 800ms 视口偏置动画自动飞抵并滑出详情抽屉。
- **验证截图**：[24_deep_link_seed_all_01.png](file:///E:/usage/screenshots/24_deep_link_seed_all_01.png)（直接访问 `?id=seed_all_01` 成功自启）。

### 3. 时间轴视图下“标点-卡片”联动滚动失效 Bug
- **深挖定位**：`scrollToCard(itemId)` 原先硬编码寻找 `document.getElementById('card-' + itemId)`。但当用户切换至时间轴视图（`currentViewMode === 'timeline'`）时，卡片真实 ID 为 `'timeline-card-' + item.id`，导致地图标点点击后无法联动滚动右侧时间轴。
- **重构解决**：修复寻找逻辑为 `document.getElementById('card-' + itemId) || document.getElementById('timeline-card-' + itemId)`，保证两种视图下双向联动 100% 生效。

### 4. 局域网非 HTTPS 环境下“复制地址”崩溃
- **深挖定位**：`navigator.clipboard` 在非安全的 HTTP 局域网访问（如 `http://192.168.x.x:8765`）时为 `undefined`。移动端或内网访问点击“复制地址”会直接抛出未捕获的 `TypeError`。
- **重构解决**：编写 `fallbackCopyText`，当 `navigator.clipboard` 不可用时，降级使用透明临时 `<textarea>` 与 `document.execCommand('copy')` 完成剪贴板写入，全面保障内网体验。

### 5. 单日活动日历过滤与点数失真 Bug
- **深挖定位**：部分同城快闪活动仅有 `start_date` 而无 `end_date`。原逻辑 `it.start_date && it.end_date` 导致此类活动无法被日历过滤，而在 `calendarDays` 的 `!it.start_date || !it.end_date` 又会导致其被无差别记入 14 天的每一天。
- **重构解决**：统一为 `const s = it.start_date || it.end_date; const e = it.end_date || it.start_date;`，单日活动仅在对应当天生效并计入当日热度打点。

### 6. “午夜深色”模式下浮动面板反光刺眼
- **深挖定位**：用户切换至“午夜深色”底图（CartoDB DarkMatter）时，底图变为黑色，但上层的搜索岛、抽屉和内容卡片依然保留刺眼的纯白表面（`bg-white` / `bg-[#F5F5F7]`），夜间刺眼且不和谐。
- **重构解决**：在根容器监听 `mapStyleMode === 'dark'` 并派发 `.theme-dark`，为浮动岛、亚克力抽屉与卡片注入极深灰蓝色暗夜材质（`bg-slate-900/85`、`bg-slate-950/90`、`border-white/10`）。
- **验证截图**：[23_verified_theme_dark_glass.png](file:///E:/usage/screenshots/23_verified_theme_dark_glass.png)。

### 7. 待去清单与 Apple iCalendar (.ics) 闭环断裂
- **深挖定位**：前端收藏“待去”仅存在本地 `localStorage`，而后端已具备成熟的 `POST /api/events/status` 与 `GET /api/events/calendar.ics`（Apple 官方 RFC 5545 日历协议），两者未打通。
- **重构解决**：
  - 点击“待去/移出”时，异步向 `/api/events/status` 发送状态，持久化至后端 SQLite。
  - 在详情抽屉底栏增设 Apple iCalendar 快捷导出与订阅入口，用户可一键将行程导入 macOS / iOS 原生日历 Widget。

---

## 二、 第一轮已修复历史问题汇总

1. **移动端顶部 Floating Island 690px 严重溢出**：已通过流式自适应收敛至 329px。
2. **移动端 Bottom Sheet 空间挤压**：高度扩容至 58vh，Bento 封面调整为响应式 h-28/36。
3. **移动端控制岛雪藏**：新增 iOS Maps 风格侧边悬浮控制胶囊栈。
4. **窗口缩放与折叠缺少 `invalidateSize`**：已挂载防抖监听与动画延时重算。
5. **ECharts 首屏包膨胀至 1.41 MB**：改为动态按需懒加载，主包骤降至 50.67 kB。
6. **搜索输入无防抖**：已引入 180ms 防抖监听。
7. **中国本地时区 UTC 偏差 Bug**：已改用本地年月日构造器。
8. **Favicon 404 错误**：已补全 SVG / ICO 图标。
