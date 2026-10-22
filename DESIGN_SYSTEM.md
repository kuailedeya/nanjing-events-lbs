# Apple HIG & Airbnb 空间探索设计系统规范 (Design System Specification)

> **版本**：2026.1 (macOS Sonoma & Airbnb Spatial Architecture)  
> **适用范围**：本仓库所有前端界面、时空数据可视化、生活与活动探索类产品、地图 LBS 探索工具。  
> **核心原则**：以 **Apple HIG 官方规范** 与 **Airbnb 空间探索美学** 为唯一设计标准，坚决淘汰粗糙低质的传统后台管理系统结构。

---

## 一、 核心架构：空间探索布局模型 (Spatial Exploration Architecture)

传统后台管理系统（如基于 Element UI / Ant Design 的 Admin 模板）具有冗长死板的左侧纵向菜单树、顶部面包屑以及大表格，在展示城市时空、地标探索或生活类情报时体验极其痛苦。

本设计系统统一采用 **Airbnb / Apple Maps 空间探索模型**：

```
┌────────────────────────────────────────────────────────────────────────┐
│  [ 搜索 Nanjing 活动... ] [ 全部 | 展会 | 活动 | 福利 ] [ 筛选 ] [ 同步 ]   │ ← 悬浮浮动岛 (Floating Island)
├─────────────────────────────────────────────────┬──────────────────────┤
│                                                 │ 南京精选探索 (15)  [>] │
│                                                 ├──────────────────────┤
│                 全屏高德地图底层                  │ ┌──────────────────┐ │
│           (默认官方全彩 · 原生 GCJ-02 火星坐标)     │ │ 潮流封面图 (16:9) │ │
│                                                 │ ├──────────────────┤ │
│                 ● 免费 (Airbnb 胶囊打点)          │ │ [南京展会] 1.9km │ │
│                 ● 活动 (白底彩色微点)             │ │ 星星人华东首展   │ │
│                 ● 选中激活 (纯黑反色胶囊)         │ │ 秦淮区 · 万象天地 │ │
│                                                 │ │ [待去] [导航][笔记]│ │
│                                                 │ └──────────────────┘ │
├─────────────────────────────────────────────────┴──────────────────────┤
│ [ ● 高德全彩 | ● 高清卫星 | ● 苹果浅灰 | ● 午夜深色 ]  [ 辐射圈 ] [ 定位 ]    │ ← 磨砂控制 Dock
└────────────────────────────────────────────────────────────────────────┘
```

### 1. 两层材质分层纪律 (Two-Layer Discipline)
* **功能层 (Liquid Glass 磨砂亚克力)**：
  * 仅用于全局悬浮容器：右侧抽屉面板、左上角浮动搜索岛、左下角控制 Dock、下拉过滤浮层。
  * 核心特征：强毛玻璃折射背景底图，高透光率与大范围环境光弥散阴影，营造“漂浮在地图上”的轻盈质感。
* **内容层 (Solid Apple Card 实体白卡)**：
  * **严禁在卡片、正文、列表项等内容容器上使用毛玻璃**。
  * 必须使用实体纯白背景（`bg-white`）搭配超细微外框（`border-black/[0.04]`）和微浮动阴影（`shadow-[0_4px_16px_rgba(0,0,0,0.04)]`），确保文本的高对比度与极致清晰度。

---

## 二、 关键组件与 Tailwind 代码配方

### 1. 右侧悬浮抽屉面板 (Right Floating Drawer Panel)
* **视觉定位**：脱离贴边，具备舒适的四周边距呼吸感。
* **Tailwind 配置**：
```html
<aside class="absolute top-6 right-6 bottom-6 w-[380px] md:w-[440px] z-20 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col pointer-events-auto">
  <div class="relative w-full h-full bg-[#F5F5F7]/85 backdrop-blur-2xl backdrop-saturate-150 rounded-[28px] border border-white/80 shadow-[0_20px_50px_rgba(0,0,0,0.1)] flex flex-col overflow-hidden">
    <!-- 标题栏与卡片滚动流 -->
  </div>
</aside>
```
* **核心参数**：
  * 背景：`bg-[#F5F5F7]/85`
  * 滤镜：`backdrop-blur-2xl backdrop-saturate-150`
  * 圆角：`rounded-[28px]`
  * 边框：`border border-white/80`
  * 阴影：`shadow-[0_20px_50px_rgba(0,0,0,0.1)]`

### 2. 顶部筛选栏 (Top Floating Island)
* **视觉定位**：悬浮于地图左上方，四边留白，不霸占整行。
* **Tailwind 配置**：
```html
<header class="absolute top-6 left-6 z-20 pointer-events-auto max-w-[660px]">
  <div class="bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.08),0_1px_3px_rgba(0,0,0,0.03)] border border-white/80 p-2 sm:p-2.5 flex items-center gap-2.5 transition-all">
    <!-- 搜索框 + iOS 胶囊分段器 + 过滤按钮 + 刷新按钮 -->
  </div>
</header>
```
* **iOS 胶囊分段器 (Segmented Pills)**：
  - 外层滑轨：`p-1 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600`
  - 选中项（白色滑块）：`bg-white text-slate-900 shadow-[0_2px_6px_rgba(0,0,0,0.1)] font-semibold`
  - 未选中项：`text-slate-500 hover:text-slate-900`

### 3. Bento Grid 潮流活动卡片 (Content Cards)
* **卡片容器**：
```html
<div class="group bg-white rounded-2xl p-3.5 transition-all duration-300 cursor-pointer border border-black/[0.04] shadow-[0_4px_16px_rgba(0,0,0,0.04)] hover:shadow-[0_12px_30px_rgba(0,0,0,0.08)] hover:-translate-y-1 flex flex-col">
  <!-- 1. 潮流封面图 (16:9) -->
  <div class="relative w-full h-36 rounded-xl overflow-hidden mb-3 bg-slate-100 group-hover:scale-[1.01] transition-transform duration-300 shrink-0">
    <img src="..." class="w-full h-full object-cover rounded-xl" />
    <div class="absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-black/10"></div>
    
    <!-- 左上角悬浮类别徽标 -->
    <span class="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-full text-[11px] font-semibold backdrop-blur-md bg-white/90 shadow-sm flex items-center gap-1.5">
      <span class="w-1.5 h-1.5 rounded-full" style="background-color: #FF9500;"></span>
      <span class="text-slate-800">南京展会</span>
    </span>

    <!-- 右上角悬浮等宽距离标签 -->
    <span class="absolute top-2.5 right-2.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium backdrop-blur-md bg-black/50 text-white tabular-nums">
      1.9 km · 新街口
    </span>

    <!-- 左下角免票直入徽标 -->
    <span class="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded-lg text-[11px] font-medium backdrop-blur-md bg-white/90 text-slate-800">
      <span class="font-semibold text-[#34C759]">免票直入</span>
    </span>
  </div>

  <!-- 2. 主标题 (严格 font-semibold text-slate-900) -->
  <h3 class="text-sm font-semibold text-slate-900 leading-snug tracking-[-0.01em] group-hover:text-[#007AFF] transition-colors mb-2 line-clamp-2">
    南京万象天地星星人农场系列主题展华东首展
  </h3>

  <!-- 3. 地理与时间行 -->
  <div class="text-xs text-slate-500 space-y-1 mb-3">
    <div class="flex items-center gap-1.5 text-slate-600">
      <MapPin class="w-3.5 h-3.5 text-slate-400 shrink-0" />
      <span class="truncate font-medium text-slate-800">南京万象天地</span>
      <span class="text-slate-300">·</span>
      <span class="shrink-0 text-slate-500 bg-black/[0.03] px-1.5 py-0.5 rounded text-[11px]">秦淮区</span>
    </div>
  </div>

  <!-- 4. 操作底栏 -->
  <div class="pt-2.5 border-t border-black/[0.04] flex items-center justify-between mt-auto">
    <!-- 状态切换胶囊 -->
    <button class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-all flex items-center gap-1.5 bg-slate-100 text-slate-700">
      <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
      <span>待去/待薅</span>
    </button>
    <div class="flex items-center gap-2">
      <a href="..." class="text-slate-500 hover:text-[#007AFF] text-[11px] font-medium flex items-center gap-1">高德导航 ↗</a>
      <a href="..." class="text-slate-400 hover:text-slate-900 text-[11px] font-medium flex items-center gap-1">笔记 ↗</a>
    </div>
  </div>
</div>
```

### 4. Airbnb 药丸打点 (Marker Pills)
* **默认态 (Inactive)**：纯白悬浮药丸胶囊（`white-space: nowrap`），带语义彩色小圆点（6px~8px）。
* **激活态 (Active)**：纯黑反色高亮胶囊（`bg-slate-950 text-white`），带有物理弹簧放大动效。
* **CSS 规范**：
```css
.airbnb-marker {
  transform: translate(-50%, -100%);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  will-change: transform;
  white-space: nowrap !important;
}

.airbnb-marker .marker-pill {
  white-space: nowrap !important;
  display: inline-flex !important;
  align-items: center !important;
  background-color: rgba(255, 255, 255, 0.96);
  color: #0f172a;
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.06);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.airbnb-marker:hover {
  transform: translate(-50%, -108%) scale(1.08);
  z-index: 50 !important;
}

.airbnb-marker.active {
  transform: translate(-50%, -114%) scale(1.15);
  z-index: 60 !important;
}

.airbnb-marker.active .marker-pill {
  background-color: #0f172a !important;
  color: #ffffff !important;
  border-color: #0f172a !important;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.35), 0 4px 10px rgba(15, 23, 42, 0.2) !important;
}
```

---

## 三、 高德地图深度空间工程规范

1. **官方瓦片集群与无 Key 接入**：
   - 标准矢量全彩底图：`https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}`（subdomains: `['1', '2', '3', '4']`）。
   - 高清卫星遥感底图：`https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}`。
   - 卫星透明路网标注图层：`https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}`。
2. **原生 GCJ-02 坐标系**：
   - 数据存储与地图坐标完全统一采用 GCJ-02 火星坐标，避免坐标系转换抖动或偏差。
3. **4 模地图切换机制**：
   - `standard` (高德全彩)：默认标准彩色，展现丰富地貌与城市路网。
   - `satellite` (高清卫星)：实景卫星底图 + 半透明道路标注。
   - `apple` (苹果浅灰)：CSS 滤镜调色 `grayscale(88%) brightness(103%) contrast(92%)`。
   - `dark` (午夜深色)：CSS 滤镜调色 `invert(100%) hue-rotate(180deg) brightness(88%) contrast(95%)`。
4. **空间分析雷达辐射圈**：
   - 以中心点（如新街口）为基准绘制 3km（核心商圈）、5km（主城生活圈）、10km（绕城圈）虚线同心圆。
5. **官方 URI 导航生态**：
   - 直通 `https://uri.amap.com/marker?position={lng},{lat}&name={title}&coordinate=gaode`，支持移动端直接唤起高德地图 App 进行自驾/公交路线规划。

---

## 四、 视觉降噪与色彩纪律

1. **色彩预算严格 ≤ 3%**：
   - 页面 97% 区域由白、黑、苹果浅灰（`#F5F5F7`、`#0F172A`、`#64748B`）等中性色掌控。
   - 绝不使用大面积花哨背景色、强彩虹渐变。
2. **Apple 官方语义系统色**：
   - 系统蓝 (`#007AFF`)：聚焦激活、主要交互、路线规划。
   - 系统绿 (`#34C759`)：免费直入、福利、核销成功。
   - 系统橙 (`#FF9500`)：艺术展会、特别活动。
   - 系统红 (`#FF3B30`)：已过期状态、危险移除。
3. **数字等宽排版**：
   - 所有距离、价格、倒计时、活动计数等数字必须声明 `font-variant-numeric: tabular-nums`，确保排列对齐。
4. **零 Emoji 纪律**：
   - 严禁在正式标题、导航栏与操作按钮中插入 Emoji 表情，统一采用 Lucide Icons 精简矢量图标。
