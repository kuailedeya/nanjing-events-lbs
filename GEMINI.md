# 项目交互与前端设计规范 (Apple HIG & Airbnb 空间探索美学)

本项目（以及未来所有相关的前端与交互界面设计）必须严格遵守 **Apple HIG (macOS Sonoma / iOS 26) 与 Airbnb 空间探索** 核心设计系统，坚决拒绝套用任何粗糙传统的后台管理模板（如 Vue-Element-Admin 等大侧边栏与面包屑布局）。

---

## 一、 核心布局架构 (Airbnb / Apple Maps 空间探索模型)

1. **拒绝传统后台管理结构**：
   - 严禁出现沉重的左侧多级导航树、顶部小面包屑和复杂表格嵌套。
   - 整体架构固定为：**100% 全屏交互地图底图 + 左上方通透浮动岛（Floating Island）+ 右侧悬浮磨砂抽屉（Liquid Glass Sheet）+ 左下角控制 Dock**。
2. **两层材质纪律 (Layer Discipline)**：
   - **功能控制层 (Liquid Glass)**：仅在悬浮抽屉、顶部搜索岛、分段切换器、底部 Dock 上使用磨砂亚克力（毛玻璃）。
   - **内容数据层 (Solid Surface)**：卡片、列表行、详情弹窗等内容容器必须使用纯白实体（`bg-white`），**严禁在内容卡片上滥用毛玻璃**，确保文字清晰度与层次对比。

---

## 二、 关键组件精确参数规范

### 1. 右侧悬浮抽屉面板 (Right Floating Drawer)
- **定位**：`absolute top-6 right-6 bottom-6 z-20`（脱离贴边，具备四边留白）。
- **尺寸**：`w-[380px] md:w-[440px]`。
- **材质**：`bg-[#F5F5F7]/85`（macOS 磨砂亚克力）、`backdrop-blur-2xl`、`backdrop-saturate-150`。
- **轮廓与高光**：圆角升级为 `rounded-[28px]`，边框采用细微白边 `border border-white/80`。
- **阴影**：大范围柔和弥散阴影 `shadow-[0_20px_50px_rgba(0,0,0,0.1)]`。

### 2. 顶部筛选栏 (Top Floating Island)
- **定位**：`absolute top-6 left-6 z-20`，最大宽度 `max-w-[660px]`。
- **轮廓**：通透圆角浮动岛屿 `rounded-[22px]`，脱离屏幕死板边缘。
- **材质**：`bg-white/80 backdrop-blur-2xl border border-white/80 shadow-[0_20px_50px_rgba(0,0,0,0.08)]`。
- **控件**：内置极简搜索框 + iOS 滑动胶囊分段器（`rounded-xl bg-black/[0.04]` 轨道，白色滑块高亮）。

### 3. Bento Grid 潮流活动卡片 (Content Cards)
- **卡片容器**：`bg-white rounded-2xl p-3.5 border border-black/[0.04] shadow-[0_4px_16px_rgba(0,0,0,0.04)]`。
  - 悬停动效：`hover:shadow-[0_12px_30px_rgba(0,0,0,0.08)] hover:-translate-y-1 transition-all duration-300`。
  - 选中激活态：`ring-2 ring-[#007AFF] border-transparent shadow-[0_16px_36px_rgba(0,122,255,0.16)] -translate-y-1`。
- **封面图规范**：
  - 容器尺寸：`relative w-full h-36 rounded-xl overflow-hidden mb-3 bg-slate-100`。
  - 悬浮徽标：左上角磨砂类别胶囊（`backdrop-blur-md bg-white/90` 带实体类别圆点）；右上角深色距离胶囊（`bg-black/50 text-white font-variant-numeric: tabular-nums`）；左下角免票直入徽标。
- **标题排版**：严格采用 `font-semibold text-slate-900 leading-snug tracking-[-0.01em]`，两行省略截断（`line-clamp-2`）。
- **信息与操作底栏**：地点与行政区微胶囊、状态即时切换胶囊、高德官方 URI 导航、Obsidian 双向笔记深链。

### 4. Airbnb 药丸打点 (Marker Pills)
- **默认态**：横向紧凑纯白药丸胶囊（`white-space: nowrap`），包含 8px 实体类别圆点与加粗字重标签。
- **选中激活态**：瞬间反色为纯黑胶囊（`bg-slate-950 text-white`），辅以物理弹簧放大动效（`cubic-bezier(0.34, 1.56, 0.64, 1)`）。
- **双向联动**：点击右侧卡片，地图以 800ms 平滑飞向目标并弹出气泡；点击地图打点，右侧列表平滑滚动到对应卡片并激活聚焦。

---

## 三、 高德地图深度空间工程规范

1. **默认高德全彩**：接入国内官方无 Key 瓦片集群（`webrd01~04.is.autonavi.com`），确保原生 GCJ-02 火星坐标精准对准，<20ms 超低延迟。
2. **4 模地图引擎**：底栏提供高德全彩（默认）、高清遥感卫星实景、苹果浅灰（Whitesmoke）、午夜深色（Midnight）四种模式。
3. **空间雷达同心圈**：支持在城市原点（如新街口）动态展开 3km 核心圈、5km 主城圈、10km 绕城圈同心分析。

---

## 四、 视觉降噪与色彩纪律

- **色彩预算 ≤ 3%**：97% 的界面由中性黑灰白构成，严格禁止彩虹渐变和随意使用装饰性彩色大色块。
- **苹果语义系统色**：
  - 激活/重点：系统蓝 `#007AFF`
  - 免费/福利/成功：系统绿 `#34C759`
  - 展会/预警：系统橙 `#FF9500`
  - 过期/警示：系统红 `#FF3B30`
- **零 Emoji 表情**：严禁在正式 UI 文本、标题与操作按钮中使用 Emoji，所有视觉符号必须由 Lucide 图标提供。
- **文案与微标签降噪 (Microcopy & Label Discipline)**：Avoid unnecessary secondary labels and descriptions. Let the layout do the explaining. Avoid unnecessary supporting text, descriptive copy, and redundant UI microcopy. 严禁冗余的辅助文字与次级解释性微标签，用界面本身的排版层级、对比与留白来解释功能。
