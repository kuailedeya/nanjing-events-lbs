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

## 二、 第三轮深挖：现代化自动化测试、无障碍 (WCAG 2.1 AA) 与性能重构

### 1. 现代化自动化测试体系与武器装备升级
- **深挖定位**：原有测试依赖手工点选或静态判断，缺少端到端自动化模拟与现代无障碍可访问性审计。
- **重构解决**：
  - 引入 Microsoft `@playwright/test` 与 Deque Labs `@axe-core/playwright`。
  - 建立双视口环境自动化覆盖：桌面端 Desktop Chrome (1440×900) 与移动端 Mobile iPhone (390×844)。
  - 覆盖无障碍审计、空间交互（防抖搜索、URL 深度链接、全键盘导航、深色底图切换）、移动端触控防溢出共 20 项测试，100% 自动化通过。

### 2. WCAG 4.1.2 按钮非法嵌套（Button Nesting Violation）
- **深挖定位**：`@axe-core` 截获 Bento 卡片使用了 `<div role="button" tabindex="0">`，但其内部操作底栏直接包含了“待去收藏”、“定位”、“详情”原生 `<button>`，导致屏幕阅读器无障碍树解析冲突。
- **重构解决**：将外层卡片容器重构为独立语义化 `<article tabindex="0">`，支持全卡片 Tab 聚焦与 Enter 键唤起，同时允许内部子按钮独立导航。

### 3. 纯图标按钮缺少可访问文本（Discernible Text）
- **深挖定位**：概览统计模态框关闭按钮、搜索清空按钮、底图切换控制胶囊缺少可辨识文本。
- **重构解决**：全量补齐 `aria-label` 与 `title` 提示（如 `aria-label="关闭统计概览 (ESC)"`、`aria-label="清空搜索"`）。

### 4. ECharts 按需 Tree-Shaking 瘦身 53%
- **深挖定位**：全量打包 `echarts` 导致单 chunk 体积高达 1,135 kB。
- **网络调研与解决**：创建 `frontend/src/utils/echarts.js`，通过 `echarts/core` 仅注册 `BarChart`、`PieChart`、`GridComponent`、`TooltipComponent` 与 `CanvasRenderer`。产物体积从 1,135 kB 直降至 524 kB（削减超过 611 kB，降幅 53%，gzip 仅 180 kB），并且作为动态 chunk 仅在打开统计模态框时异步下载。

### 5. 原生 ResizeObserver 替换 Leaflet 地图 setTimeout 轮询
- **深挖定位**：移动端抽屉上下拉伸或桌面端抽屉折叠时，使用 `setTimeout(350)` 调用 `map.invalidateSize()`，导致动画过程中出现灰色切片断层。
- **网络调研与解决**：通过原生 `ResizeObserver` 监听地图容器元素，动态精准重算尺寸，并在 `onUnmounted` 中安全解绑断开，杜绝内存泄漏。

### 6. 图片加载异常降级死循环阻断
- **深挖定位**：`handleImageError` 将 `img.src` 重新指向远程 Unsplash 图片，在弱网或离线环境下会无限触发 `@error` 循环卡死浏览器。
- **重构解决**：在错误回调中设置 `e.target.onerror = null`，并采用高保真内联 SVG Data URI（Apple 浅灰极简风格）进行本地离线自适应兜底。

---

## 三、 第一轮已修复历史问题汇总

1. **移动端顶部 Floating Island 690px 严重溢出**：已通过流式自适应收敛至 329px。
2. **移动端 Bottom Sheet 空间挤压**：高度扩容至 58vh，Bento 封面调整为响应式 h-28/36。
3. **移动端控制岛雪藏**：新增 iOS Maps 风格侧边悬浮控制胶囊栈。
4. **窗口缩放与折叠缺少 `invalidateSize`**：已挂载防抖监听与动画延时重算。
5. **ECharts 首屏包膨胀至 1.41 MB**：改为动态按需懒加载，主包骤降至 50.67 kB。
6. **搜索输入无防抖**：已引入 180ms 防抖监听。
7. **中国本地时区 UTC 偏差 Bug**：已改用本地年月日构造器。
8. **Favicon 404 错误**：已补全 SVG / ICO 图标。
