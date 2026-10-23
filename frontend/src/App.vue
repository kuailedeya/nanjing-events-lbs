<template>
  <div :class="['relative w-screen h-screen overflow-hidden select-none font-sans antialiased transition-colors duration-300', mapStyleMode === 'dark' ? 'theme-dark bg-slate-950 text-slate-100' : 'bg-[#F5F5F7] text-slate-900']">
    
    <!-- 1. 全屏底图 (原生 GCJ-02 火星坐标) -->
    <div 
      id="map-container" 
      :class="[
        'absolute inset-0 w-full h-full z-0 transition-all duration-300',
        mapStyleMode === 'apple' ? 'amap-apple-filter' : ''
      ]"
    >
      <div id="leaflet-map" class="w-full h-full"></div>
    </div>

    <!-- 2. 顶部：悬浮于地图左上方的通透圆角浮动岛屿 (Floating Island，严格单行无留白) -->
    <header class="absolute top-3 left-3 right-3 sm:right-auto md:top-6 md:left-6 z-20 pointer-events-auto max-w-full md:max-w-[720px]">
      <div class="bg-white/85 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.08),0_1px_3px_rgba(0,0,0,0.03)] border border-white/80 p-1.5 sm:p-2 flex items-center justify-between gap-1.5 sm:gap-2 transition-all">
        
        <!-- Airbnb 风格紧凑搜索框 -->
        <div class="relative flex items-center flex-1 sm:flex-initial sm:w-44 md:w-56 shrink min-w-0">
          <Search class="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索活动、展会、地标..."
            class="w-full pl-8 pr-6 py-1.5 bg-black/[0.04] focus:bg-white rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 outline-none border border-transparent focus:border-black/[0.08] focus:ring-4 focus:ring-[#007AFF]/12 transition-all duration-200"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="absolute right-2 text-slate-400 hover:text-slate-600 p-0.5 cursor-pointer transition-colors"
            title="清空搜索"
            aria-label="清空搜索"
          >
            <X class="w-3 h-3" />
          </button>
        </div>

        <!-- 分类滑动胶囊分段器 (全部 / 展会 / 活动 / 福利) -->
        <div class="flex items-center p-0.5 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600 shrink-0">
          <button
            v-for="cat in categoryOptions"
            :key="cat.value"
            @click="activeCategory = cat.value"
            :class="[
              'px-1.5 sm:px-2.5 py-1 rounded-lg transition-all text-[11px] sm:text-xs cursor-pointer',
              activeCategory === cat.value
                ? 'bg-white text-slate-900 shadow-[0_2px_6px_rgba(0,0,0,0.1)] font-semibold'
                : 'text-slate-500 hover:text-slate-900'
            ]"
          >
            {{ cat.label }}
          </button>
        </div>

        <!-- 线上/线下实体场馆切换器 (大屏展示，移动端融入 Filter Popover) -->
        <div class="hidden lg:flex items-center p-0.5 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600 shrink-0">
          <button
            @click="venueFilter = 'ALL'"
            :class="[
              'px-2 py-1 rounded-lg transition-all text-xs cursor-pointer',
              venueFilter === 'ALL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
          >
            全览
          </button>
          <button
            @click="venueFilter = 'PHYSICAL'"
            :class="[
              'px-2 py-1 rounded-lg transition-all text-xs cursor-pointer flex items-center gap-1',
              venueFilter === 'PHYSICAL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-[#007AFF]"></span>
            <span>线下实体</span>
          </button>
          <button
            @click="venueFilter = 'ONLINE'"
            :class="[
              'px-2 py-1 rounded-lg transition-all text-xs cursor-pointer flex items-center gap-1',
              venueFilter === 'ONLINE' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-[#34C759]"></span>
            <span>全城羊毛</span>
          </button>
        </div>

        <!-- 待去清单快捷过滤 (平板以上大屏展示，移动端融入 Filter Popover) -->
        <button
          @click="showFavoritesOnly = !showFavoritesOnly"
          :class="[
            'hidden md:flex px-2.5 py-1.5 rounded-xl transition-all cursor-pointer items-center gap-1 text-xs font-medium shrink-0',
            showFavoritesOnly
              ? 'bg-amber-500 text-white shadow-sm font-semibold'
              : 'bg-black/[0.04] text-slate-700 hover:bg-black/[0.07]'
          ]"
        >
          <Star class="w-3.5 h-3.5" :class="showFavoritesOnly ? 'fill-white text-white' : 'text-amber-500 fill-amber-500'" />
          <span>待去</span>
          <span class="text-[11px] tabular-nums font-bold opacity-90">({{ favoriteIds.length }})</span>
        </button>

        <!-- 极简区域筛选下拉按钮 -->
        <button
          @click="showFilterPopover = !showFilterPopover"
          :class="[
            'p-1.5 rounded-xl transition-all cursor-pointer relative shrink-0',
            hasActiveFilter ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:bg-black/[0.04]'
          ]"
          title="高级筛选"
        >
          <Filter class="w-4 h-4" />
          <span v-if="hasActiveFilter" class="w-1.5 h-1.5 rounded-full bg-[#34C759] absolute top-1 right-1"></span>
        </button>

        <!-- 增量同步按钮 -->
        <button
          @click="triggerSync"
          :disabled="isSyncing"
          class="p-1.5 rounded-xl text-slate-600 hover:bg-black/[0.04] transition-all cursor-pointer shrink-0"
          title="增量同步"
        >
          <RefreshCw :class="['w-4 h-4', isSyncing ? 'animate-spin text-[#007AFF]' : '']" />
        </button>
      </div>

      <!-- 下拉微质感 Popover 筛选器 -->
      <div
        v-if="showFilterPopover"
        class="mt-2 p-3 bg-white/90 backdrop-blur-2xl backdrop-saturate-150 rounded-[20px] shadow-[0_20px_50px_rgba(0,0,0,0.12)] border border-white/80 flex items-center gap-3 text-xs animate-in fade-in slide-in-from-top-2 duration-200 flex-wrap"
      >
        <!-- 移动端额外融入：场馆全览/线下/羊毛切换 -->
        <div class="flex lg:hidden items-center p-0.5 bg-black/[0.04] rounded-lg text-xs font-medium text-slate-600">
          <button
            @click="venueFilter = 'ALL'"
            :class="['px-2 py-0.5 rounded-md text-[11px] transition-all cursor-pointer', venueFilter === 'ALL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500']"
          >全览</button>
          <button
            @click="venueFilter = 'PHYSICAL'"
            :class="['px-2 py-0.5 rounded-md text-[11px] transition-all cursor-pointer flex items-center gap-1', venueFilter === 'PHYSICAL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500']"
          ><span class="w-1.5 h-1.5 rounded-full bg-[#007AFF]"></span>线下</button>
          <button
            @click="venueFilter = 'ONLINE'"
            :class="['px-2 py-0.5 rounded-md text-[11px] transition-all cursor-pointer flex items-center gap-1', venueFilter === 'ONLINE' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500']"
          ><span class="w-1.5 h-1.5 rounded-full bg-[#34C759]"></span>羊毛</button>
        </div>

        <!-- 移动端额外融入：待去清单过滤 -->
        <button
          @click="showFavoritesOnly = !showFavoritesOnly"
          :class="[
            'flex md:hidden px-2 py-1 rounded-lg text-xs font-medium transition cursor-pointer items-center gap-1',
            showFavoritesOnly ? 'bg-amber-500 text-white shadow-sm font-semibold' : 'text-slate-700 bg-black/[0.04]'
          ]"
        >
          <Star class="w-3 h-3" :class="showFavoritesOnly ? 'fill-white text-white' : 'text-amber-500 fill-amber-500'" />
          <span class="text-[11px]">待去 ({{ favoriteIds.length }})</span>
        </button>

        <div class="flex items-center gap-1.5 text-slate-700">
          <Calendar class="w-3.5 h-3.5 text-slate-400" />
          <div class="flex items-center gap-1 bg-black/[0.04] p-0.5 rounded-lg">
            <button
              v-for="tf in timeFilterOptions"
              :key="tf.value"
              @click="timeFilter = tf.value"
              :class="[
                'px-2 py-0.5 rounded-md text-[11px] transition-all cursor-pointer',
                timeFilter === tf.value ? 'bg-white text-slate-900 font-semibold shadow-xs' : 'text-slate-500 hover:text-slate-800'
              ]"
            >
              {{ tf.label }}
            </button>
          </div>
        </div>

        <div class="h-3.5 w-px bg-slate-200"></div>

        <div class="flex items-center gap-1.5 text-slate-600">
          <MapPin class="w-3.5 h-3.5 text-slate-400" />
          <select v-model="selectedDistrict" @change="onDistrictChange" class="bg-transparent border-0 outline-none font-medium cursor-pointer text-slate-800 text-xs">
            <option value="ALL">全城区域 (含江北新区)</option>
            <option v-for="d in districts" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>

        <div class="h-3.5 w-px bg-slate-200"></div>

        <div class="flex items-center gap-1.5 text-slate-600">
          <Navigation class="w-3.5 h-3.5 text-slate-400" />
          <select v-model="radiusFilter" class="bg-transparent border-0 outline-none font-medium cursor-pointer text-slate-800 text-xs">
            <option :value="0">全城距离</option>
            <option :value="3">3 km 内</option>
            <option :value="5">5 km 内</option>
            <option :value="10">10 km 内</option>
            <option :value="20">20 km 内</option>
          </select>
        </div>

        <div class="h-3.5 w-px bg-slate-200"></div>

        <button
          @click="freeOnly = !freeOnly"
          :class="[
            'px-2.5 py-1 rounded-lg text-xs font-medium transition cursor-pointer flex items-center gap-1.5',
            freeOnly ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'
          ]"
        >
          <span :class="['w-1.5 h-1.5 rounded-full', freeOnly ? 'bg-[#34C759]' : 'bg-slate-300']"></span>
          仅看免费
        </button>

        <button
          v-if="hasActiveFilter"
          @click="resetFilters"
          class="ml-auto text-[11px] text-[#007AFF] hover:underline font-semibold cursor-pointer"
        >
          重置
        </button>
      </div>

      <!-- 空间瞬移片区栏 (通透圆角白胶囊) -->
      <div class="mt-2 flex items-center gap-1.5 overflow-x-auto no-scrollbar pointer-events-auto">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-medium text-slate-500 bg-white/80 backdrop-blur-md border border-white/80 shadow-2xs shrink-0 flex items-center gap-1">
          <Compass class="w-2.5 h-2.5 text-slate-400" />
          <span>瞬移</span>
        </span>
        <button
          v-for="zone in zoneTeleports"
          :key="zone.label"
          @click="teleportToZone(zone)"
          :class="[
            'px-2.5 py-0.5 rounded-full text-[10.5px] font-medium whitespace-nowrap transition-all cursor-pointer shrink-0 backdrop-blur-md border',
            activeZoneLabel === zone.label
              ? 'bg-slate-950 text-white font-semibold shadow-xs border-slate-950'
              : 'bg-white/80 hover:bg-white text-slate-700 border-white/80 shadow-2xs'
          ]"
        >
          {{ zone.label }}
        </button>
      </div>
    </header>

    <!-- 3. 左下角：底图与可视化控制岛 (桌面端) -->
    <div class="hidden sm:flex absolute bottom-6 left-6 z-20 items-center gap-2 pointer-events-auto">
      <!-- 地图模式切换胶囊 -->
      <div class="bg-white/80 backdrop-blur-2xl backdrop-saturate-150 p-1 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 flex items-center gap-1 text-xs">
        <button
          v-for="mode in mapModes"
          :key="mode.id"
          @click="setMapMode(mode.id)"
          :class="[
            'px-3 py-1.5 rounded-xl font-medium transition-all cursor-pointer flex items-center gap-1.5 text-xs',
            mapStyleMode === mode.id
              ? 'bg-slate-950 text-white font-semibold shadow-[0_2px_8px_rgba(0,0,0,0.15)]'
              : 'text-slate-600 hover:text-slate-900 hover:bg-black/[0.03]'
          ]"
        >
          <span class="w-2 h-2 rounded-full" :style="{ backgroundColor: mode.color }"></span>
          <span>{{ mode.label }}</span>
        </button>
      </div>

      <!-- 新街口中心辐射同心圈切换 (使用标准 SVG 图标) -->
      <button
        @click="toggleRings"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showRings ? 'bg-slate-950 text-white border-slate-950 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
      >
        <Disc class="w-3.5 h-3.5" :class="showRings ? 'text-[#34C759]' : 'text-slate-400'" />
        <span>辐射圈</span>
      </button>

      <!-- 热力分布图开关 (统一使用 bg-slate-950 激活态) -->
      <button
        @click="toggleHeatmap"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showHeatmap ? 'bg-slate-950 text-white border-slate-950 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
      >
        <Flame class="w-3.5 h-3.5" :class="showHeatmap ? 'text-[#FF3B30]' : 'text-slate-400'" />
        <span>热力图</span>
      </button>

      <!-- 数据洞察图表弹窗 -->
      <button
        @click="openStatsModal"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showStatsModal ? 'bg-slate-950 text-white border-slate-950 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
      >
        <BarChart3 class="w-3.5 h-3.5" :class="showStatsModal ? 'text-white' : 'text-[#007AFF]'" />
        <span>概览统计</span>
      </button>

      <!-- 一键复位新街口中心 -->
      <button
        @click="recenterMap"
        class="p-2.5 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-slate-700 hover:text-slate-950 hover:bg-white transition cursor-pointer"
        title="复位新街口"
        aria-label="复位新街口"
      >
        <Crosshair class="w-4 h-4" />
      </button>
    </div>

    <!-- 3b. 移动端浮动操作岛 (Floating Controls Stack, Apple Maps 风格) -->
    <div class="sm:hidden absolute top-20 right-3 z-20 flex flex-col items-center gap-2 pointer-events-auto">
      <button
        @click="recenterMap"
        class="w-9 h-9 rounded-full bg-white/90 backdrop-blur-md shadow-md border border-white/80 flex items-center justify-center text-slate-700 active:scale-95 transition"
        title="复位新街口"
        aria-label="复位新街口"
      >
        <Crosshair class="w-4 h-4" />
      </button>

      <button
        @click="cycleMapMode"
        class="w-9 h-9 rounded-full bg-white/90 backdrop-blur-md shadow-md border border-white/80 flex items-center justify-center active:scale-95 transition"
        title="切换底图"
        aria-label="切换底图"
      >
        <span class="w-3 h-3 rounded-full" :style="{ backgroundColor: currentMapModeColor }"></span>
      </button>

      <button
        @click="toggleRings"
        :class="[
          'w-9 h-9 rounded-full backdrop-blur-md shadow-md border transition flex items-center justify-center active:scale-95',
          showRings ? 'bg-slate-950 text-white border-slate-950' : 'bg-white/90 text-slate-700 border-white/80'
        ]"
        title="辐射圈"
        aria-label="辐射圈"
      >
        <Disc class="w-4 h-4" :class="showRings ? 'text-[#34C759]' : 'text-slate-400'" />
      </button>

      <button
        @click="toggleHeatmap"
        :class="[
          'w-9 h-9 rounded-full backdrop-blur-md shadow-md border transition flex items-center justify-center active:scale-95',
          showHeatmap ? 'bg-slate-950 text-white border-slate-950' : 'bg-white/90 text-slate-700 border-white/80'
        ]"
        title="热力图"
        aria-label="热力图"
      >
        <Flame class="w-4 h-4" :class="showHeatmap ? 'text-[#FF3B30]' : 'text-slate-400'" />
      </button>

      <button
        @click="openStatsModal"
        class="w-9 h-9 rounded-full bg-white/90 backdrop-blur-md shadow-md border border-white/80 flex items-center justify-center text-slate-700 active:scale-95 transition"
        title="统计洞察"
        aria-label="统计洞察"
      >
        <BarChart3 class="w-4 h-4 text-[#007AFF]" />
      </button>
    </div>

    <!-- 4. 响应式抽屉面板 (移动端 Bottom Sheet + 桌面端右侧 Liquid Glass 悬浮抽屉) -->
    <aside
      :class="[
        'z-20 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col pointer-events-auto',
        // 移动端 (< 768px): 贴底上拉 Bottom Sheet，支持半屏 (52vh) 与全览 (86vh) 双档流畅切换
        'fixed inset-x-0 bottom-0 md:h-auto rounded-t-[28px] border-t border-white/80 shadow-[0_-10px_40px_rgba(0,0,0,0.12)] bg-[#F5F5F7]/95 backdrop-blur-2xl',
        mobileSheetExpanded ? 'max-h-[86vh] h-[86vh]' : 'max-h-[52vh] h-[52vh]',
        // 桌面端 (>= 768px): 右侧悬浮亚克力抽屉
        'md:fixed md:top-6 md:right-6 md:bottom-6 md:left-auto md:w-[420px] md:max-h-none md:rounded-[28px] md:border md:border-white/80 md:shadow-[0_20px_50px_rgba(0,0,0,0.1)]',
        !drawerOpen ? 'translate-y-full md:translate-y-0 md:translate-x-[calc(100%+24px)]' : 'translate-y-0 md:translate-x-0'
      ]"
    >
      <div class="relative w-full h-full flex flex-col overflow-hidden">
        
        <!-- 移动端把手 (Pull Handle - 点击平滑升降高度) -->
        <button
          @click="mobileSheetExpanded = !mobileSheetExpanded"
          class="w-full flex items-center justify-center py-2.5 md:hidden shrink-0 cursor-pointer focus:outline-none"
          :title="mobileSheetExpanded ? '收起面板 (半屏)' : '展开面板 (全屏)'"
        >
          <div class="w-10 h-1 bg-slate-300 hover:bg-slate-400 rounded-full transition-colors"></div>
        </button>

        <!-- 固定头部：非溢出 Apple HIG 3 层轻薄布局 -->
        <div class="flex-shrink-0 z-10 bg-[#F5F5F7]/95 backdrop-blur-md border-b border-black/[0.04]">
          <!-- Tier 1: 标题 + [卡片/时间轴] 分段切换 + 折叠抽屉按钮 -->
          <div class="px-4 pt-2.5 pb-1.5 flex items-center justify-between">
            <div class="flex items-center gap-1.5">
              <h2 class="text-xs font-semibold text-slate-900 tracking-tight">南京精选</h2>
              <span class="text-[11px] font-semibold text-slate-400 tabular-nums">({{ filteredEvents.length }})</span>
            </div>

            <div class="flex items-center gap-2">
              <!-- 视图分段器 -->
              <div class="flex items-center p-0.5 bg-black/[0.05] rounded-lg text-[11px] font-medium">
                <button
                  @click="currentViewMode = 'cards'"
                  :class="[
                    'px-2 py-0.5 rounded-md transition-all cursor-pointer flex items-center gap-1',
                    currentViewMode === 'cards' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
                  ]"
                >
                  <Layers class="w-3 h-3" />
                  <span>卡片</span>
                </button>
                <button
                  @click="currentViewMode = 'timeline'"
                  :class="[
                    'px-2 py-0.5 rounded-md transition-all cursor-pointer flex items-center gap-1',
                    currentViewMode === 'timeline' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
                  ]"
                >
                  <Clock class="w-3 h-3" />
                  <span>时间轴</span>
                </button>
              </div>

              <!-- 折叠抽屉按钮 -->
              <button
                @click="drawerOpen = false"
                class="hidden md:flex p-1 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-black/[0.05] transition cursor-pointer"
                title="折叠列表"
                aria-label="折叠列表"
              >
                <ChevronRight class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Tier 2: 3 维极简排序胶囊 -->
          <div class="px-4 py-1 flex items-center justify-between">
            <div class="flex items-center p-0.5 bg-black/[0.04] rounded-lg text-[10.5px] font-medium">
              <button
                v-for="s in sortOptions"
                :key="s.value"
                @click="sortBy = s.value"
                :class="[
                  'px-2 py-0.5 rounded-md transition-all cursor-pointer whitespace-nowrap',
                  sortBy === s.value ? 'bg-white text-slate-950 font-semibold shadow-xs' : 'text-slate-500 hover:text-slate-900'
                ]"
              >
                {{ s.label }}
              </button>
            </div>
          </div>

          <!-- Tier 3: 14 天横向滑动日历条 -->
          <div class="px-3 py-1.5 flex items-center gap-1 overflow-x-auto no-scrollbar border-t border-black/[0.03] bg-black/[0.015]">
            <button
              @click="selectedCalendarDate = null"
              :class="[
                'min-w-[38px] h-[36px] rounded-lg flex flex-col items-center justify-center px-1 cursor-pointer transition-all shrink-0 text-center',
                selectedCalendarDate === null
                  ? 'bg-slate-950 text-white shadow-xs font-semibold'
                  : 'bg-white/80 hover:bg-white text-slate-600 border border-black/[0.04]'
              ]"
            >
              <span class="text-[9px] opacity-75 leading-none">全周期</span>
              <span class="text-[11px] font-bold leading-tight mt-0.5">全部</span>
            </button>

            <button
              v-for="day in calendarDays"
              :key="day.iso"
              @click="selectCalendarDay(day.iso)"
              :class="[
                'min-w-[40px] h-[36px] rounded-lg flex flex-col items-center justify-between py-1 px-1 cursor-pointer transition-all shrink-0 text-center',
                selectedCalendarDate === day.iso
                  ? 'bg-[#007AFF] text-white shadow-xs font-semibold scale-102'
                  : (day.count > 0 ? 'bg-white/90 hover:bg-white text-slate-800 border border-black/[0.04]' : 'bg-black/[0.02] text-slate-400 border border-transparent')
              ]"
            >
              <span class="text-[9px] leading-none" :class="selectedCalendarDate === day.iso ? 'text-white/90' : 'text-slate-400'">
                {{ day.label }}
              </span>
              <span class="text-[12px] font-bold tabular-nums leading-none">
                {{ day.dateNum }}
              </span>
              <div class="flex items-center gap-0.5 h-1">
                <span
                  v-for="i in day.dots"
                  :key="i"
                  class="w-1 h-1 rounded-full"
                  :class="selectedCalendarDate === day.iso ? 'bg-white' : (i === 1 ? 'bg-[#007AFF]' : (i === 2 ? 'bg-[#34C759]' : 'bg-[#FF9500]'))"
                ></span>
              </div>
            </button>
          </div>
        </div>

        <!-- 独立卡片滚动容器 (0 DOM 销毁重建，仅更新 activeEventId) -->
        <div class="flex-1 min-h-0 overflow-y-auto p-4 no-scrollbar" id="cards-container">
          <!-- 视图 A: Bento 卡片流 -->
          <div v-if="currentViewMode === 'cards'" class="space-y-4">
            <article
              v-for="item in filteredEvents"
              :key="item.id"
              :id="'card-' + item.id"
              tabindex="0"
              @click="openDetail(item)"
              @keydown.enter="openDetail(item)"
              @keydown.space.prevent="openDetail(item)"
              @mouseenter="activeEventId = item.id"
              @mouseleave="activeEventId = detailItem ? detailItem.id : null"
              :class="[
                'group bg-white rounded-2xl p-3 sm:p-3.5 transition-all duration-300 cursor-pointer border flex flex-col focus:outline-none focus:ring-2 focus:ring-[#007AFF]',
                activeEventId === item.id
                  ? 'ring-2 ring-[#007AFF] border-transparent shadow-[0_16px_36px_rgba(0,122,255,0.16)] -translate-y-1'
                  : 'border-black/[0.04] shadow-[0_4px_16px_rgba(0,0,0,0.04)] hover:shadow-[0_12px_30px_rgba(0,0,0,0.08)] hover:-translate-y-1'
              ]"
            >
              <!-- Bento 封面图 (移动端高度自适应 h-28，桌面端 h-36) -->
              <div class="relative w-full h-28 sm:h-32 md:h-36 rounded-xl overflow-hidden mb-2.5 sm:mb-3 bg-slate-100 group-hover:scale-[1.01] transition-transform duration-300 shrink-0">
                <img
                  :src="getEventCover(item)"
                  :alt="item.title"
                  @error="handleImageError"
                  loading="lazy"
                  class="w-full h-full object-cover rounded-xl"
                />
                <div class="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-black/10"></div>
                
                <!-- 类别胶囊 -->
                <span class="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-tight backdrop-blur-md bg-white/90 shadow-sm flex items-center gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: getMarkerDotColor(item.category) }"></span>
                  <span class="text-slate-800">{{ item.category }}</span>
                </span>

                <!-- 距离标签 -->
                <span class="absolute top-2.5 right-2.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium tracking-tight backdrop-blur-md bg-black/50 text-white tabular-nums flex items-center gap-1">
                  <span>{{ item.distance_km }} km</span>
                  <span class="text-white/60">·</span>
                  <span class="text-white/80">新街口</span>
                </span>

                <!-- 免票直入徽标 -->
                <span class="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded-lg text-[11px] font-medium tracking-tight backdrop-blur-md bg-white/90 text-slate-800 flex items-center gap-1">
                  <span class="font-semibold text-[#34C759]" v-if="item.is_free">免票直入</span>
                  <span class="text-slate-700 font-medium" v-else>{{ item.benefit }}</span>
                </span>
              </div>

              <!-- 时态与时间行 -->
              <div class="mb-1.5 flex items-center gap-2">
                <span
                  :class="[
                    'px-2 py-0.5 rounded-md text-[10px] font-semibold tracking-tight border inline-flex items-center gap-1',
                    getStatusInfo(item).bg
                  ]"
                >
                  <span>{{ getStatusInfo(item).label }}</span>
                </span>
                <span class="text-[11px] text-slate-400 truncate">{{ item.event_time_text }}</span>
              </div>

              <!-- 主标题 -->
              <h3 class="text-sm font-semibold text-slate-900 leading-snug tracking-[-0.01em] group-hover:text-[#007AFF] transition-colors mb-2 line-clamp-2">
                {{ item.title }}
              </h3>

              <!-- 地址元数据 -->
              <div class="text-xs text-slate-500 space-y-1 mb-3">
                <div class="flex items-center gap-1.5 text-slate-600">
                  <MapPin class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span class="truncate font-medium text-slate-800">{{ item.address }}</span>
                  <span class="text-slate-300">·</span>
                  <span class="shrink-0 text-slate-500 bg-black/[0.03] px-1.5 py-0.5 rounded text-[11px]">{{ item.district }}</span>
                </div>
              </div>

              <!-- 操作底栏 -->
              <div class="pt-2.5 border-t border-black/[0.04] flex items-center justify-between mt-auto" @click.stop>
                <button
                  @click.stop="toggleFavorite(item)"
                  :class="[
                    'px-2.5 py-1 rounded-full text-[11px] font-medium transition-all flex items-center gap-1 cursor-pointer',
                    isFavorite(item.id)
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
                  ]"
                >
                  <Star class="w-3 h-3" :class="isFavorite(item.id) ? 'fill-amber-500 text-amber-500' : 'text-slate-400'" />
                  <span>{{ isFavorite(item.id) ? '已待去' : '待去' }}</span>
                </button>

                <div class="flex items-center gap-1.5">
                  <button
                    @click.stop="focusEvent(item)"
                    class="text-slate-600 hover:text-[#007AFF] text-[11px] font-medium flex items-center gap-1 py-1 px-2 hover:bg-blue-50/50 rounded-lg transition-colors cursor-pointer"
                  >
                    <Navigation class="w-3 h-3 text-slate-400 group-hover:text-[#007AFF]" />
                    <span>定位</span>
                  </button>

                  <button
                    @click.stop="openDetail(item)"
                    class="text-slate-700 hover:text-slate-900 text-[11px] font-semibold flex items-center gap-0.5 py-1 px-2 hover:bg-black/[0.04] rounded-lg transition-colors cursor-pointer"
                  >
                    <span>详情</span>
                    <ChevronRight class="w-3.5 h-3.5 text-slate-400" />
                  </button>
                </div>
              </div>
            </article>
          </div>

          <!-- 视图 B: 时间轴视图 (克制分组标题，彻底移除营销冗余文案) -->
          <div v-else class="space-y-6">
            <div v-for="group in timelineGroups" :key="group.id" class="relative">
              <!-- 吸顶分组头 -->
              <div class="sticky top-0 z-20 py-1.5 px-3 rounded-xl bg-[#F5F5F7]/95 backdrop-blur-md border border-black/[0.04] shadow-2xs mb-3 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full" :class="group.dotColor"></span>
                  <span class="text-xs font-bold text-slate-800 tracking-tight">{{ group.title }}</span>
                </div>
                <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full tabular-nums" :class="group.badgeClass">
                  {{ group.items.length }} 场
                </span>
              </div>

              <!-- 列表纵向导轨 -->
              <div class="relative pl-7 space-y-3">
                <div class="absolute left-[10px] top-3 bottom-3 w-[2px] bg-slate-300 rounded-full pointer-events-none"></div>

                <article
                  v-for="item in group.items"
                  :key="item.id"
                  :id="'timeline-card-' + item.id"
                  tabindex="0"
                  @click="openDetail(item)"
                  @keydown.enter="openDetail(item)"
                  @keydown.space.prevent="openDetail(item)"
                  @mouseenter="activeEventId = item.id"
                  @mouseleave="activeEventId = detailItem ? detailItem.id : null"
                  :class="[
                    'group relative bg-white rounded-2xl p-3 transition-all duration-300 cursor-pointer border flex flex-col focus:outline-none focus:ring-2 focus:ring-[#007AFF]',
                    activeEventId === item.id
                      ? 'ring-2 ring-[#007AFF] border-transparent shadow-[0_16px_36px_rgba(0,122,255,0.16)] -translate-y-0.5'
                      : 'border-black/[0.04] shadow-[0_3px_12px_rgba(0,0,0,0.03)] hover:shadow-[0_10px_24px_rgba(0,0,0,0.06)] hover:-translate-y-0.5'
                  ]"
                >
                  <div
                    class="absolute -left-[23px] top-4 w-3 h-3 rounded-full border-2 border-white shadow-xs z-10 ring-2 ring-black/[0.04]"
                    :class="group.nodeColor"
                  ></div>

                  <div class="flex gap-3">
                    <div class="relative w-20 h-20 rounded-xl overflow-hidden bg-slate-100 shrink-0">
                      <img :src="getEventCover(item)" :alt="item.title" @error="handleImageError" loading="lazy" class="w-full h-full object-cover rounded-xl" />
                      <span class="absolute bottom-1 left-1 px-1.5 py-0.2 rounded text-[9px] font-semibold backdrop-blur-md bg-black/60 text-white tabular-nums">
                        {{ item.distance_km }}km
                      </span>
                    </div>

                    <div class="flex-1 min-w-0 flex flex-col justify-between">
                      <div>
                        <div class="flex items-center gap-1.5 mb-1">
                          <span :class="['px-1.5 py-0.2 rounded text-[9.5px] font-semibold border', getStatusInfo(item).bg]">
                            {{ getStatusInfo(item).label }}
                          </span>
                          <span class="text-[10px] text-slate-400 truncate">{{ item.event_time_text }}</span>
                        </div>
                        <h4 class="text-xs font-semibold text-slate-900 group-hover:text-[#007AFF] transition-colors line-clamp-2 leading-snug">
                          {{ item.title }}
                        </h4>
                      </div>

                      <div class="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-black/[0.03] mt-2" @click.stop>
                        <span class="font-medium truncate max-w-[130px] text-slate-600">{{ item.address }}</span>
                        <div class="flex items-center gap-2">
                          <span class="text-[#34C759] font-medium" v-if="item.is_free">免票</span>
                          <span class="text-slate-600 font-medium" v-else>{{ item.benefit }}</span>
                          <button @click.stop="focusEvent(item)" class="text-[#007AFF] font-medium hover:underline text-[10.5px]">定位</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              </div>
            </div>
          </div>

          <EmptyState
            v-if="filteredEvents.length === 0"
            :is-favorites-mode="showFavoritesOnly"
            @reset="resetFilters"
          />
        </div>
      </div>
    </aside>

    <!-- 浮动展开按钮 (当抽屉被折叠时) -->
    <button
      v-if="!drawerOpen"
      @click="drawerOpen = true"
      class="fixed bottom-6 right-6 z-20 px-3.5 py-2.5 rounded-full bg-slate-950 text-white shadow-lg flex items-center gap-2 text-xs font-semibold hover:bg-slate-800 transition cursor-pointer"
    >
      <Layers class="w-4 h-4 text-[#007AFF]" />
      <span>展开精选 ({{ filteredEvents.length }})</span>
    </button>

    <!-- 5. 活动二级详情抽屉 (彻底移除“门票说明/规则简介”等冗余标签，纯靠布局说话) -->
    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 translate-x-8"
      enter-to-class="opacity-100 translate-x-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-x-0"
      leave-to-class="opacity-0 translate-x-8"
    >
      <div
        v-if="detailItem"
        class="fixed inset-0 z-40 bg-black/25 backdrop-blur-xs flex justify-end transition-opacity duration-300 pointer-events-auto"
        @click.self="closeDetail"
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label="活动详情"
          class="w-full sm:w-[420px] md:w-[460px] h-full bg-white/95 backdrop-blur-3xl shadow-[0_25px_70px_rgba(0,0,0,0.2)] border-l border-white/80 flex flex-col overflow-hidden"
        >
          
          <!-- 封面大图 -->
          <div class="relative w-full h-56 bg-slate-100 shrink-0 overflow-hidden">
            <img
              :src="getEventCover(detailItem)"
              :alt="detailItem.title"
              @error="handleImageError"
              class="w-full h-full object-cover"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-black/20"></div>

            <button
              @click="closeDetail"
              class="absolute top-4 right-4 w-8 h-8 rounded-full bg-black/40 hover:bg-black/60 backdrop-blur-md text-white flex items-center justify-center transition-all cursor-pointer shadow-sm"
              title="关闭详情 (ESC)"
              aria-label="关闭详情 (ESC)"
            >
              <X class="w-4 h-4" />
            </button>

            <div class="absolute top-4 left-4 flex items-center gap-2">
              <span class="px-2.5 py-1 rounded-full text-xs font-semibold backdrop-blur-md bg-white/95 text-slate-800 shadow-xs flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: getMarkerDotColor(detailItem.category) }"></span>
                <span>{{ detailItem.category }}</span>
              </span>
              <span
                :class="[
                  'px-2.5 py-1 rounded-full text-xs font-semibold backdrop-blur-md shadow-xs',
                  getStatusInfo(detailItem).bg
                ]"
              >
                {{ getStatusInfo(detailItem).label }}
              </span>
            </div>

            <div class="absolute bottom-4 left-4 right-4 text-white">
              <div class="text-[11px] font-medium text-white/80 mb-1 flex items-center gap-2">
                <span>{{ detailItem.district }}</span>
                <span>·</span>
                <span>距新街口 {{ detailItem.distance_km }} km</span>
              </div>
              <h2 class="text-base font-bold leading-snug tracking-tight text-white line-clamp-2">
                {{ detailItem.title }}
              </h2>
            </div>
          </div>

          <!-- 详情正文：纯排版说话，杜绝表单说明性废标签 -->
          <div class="flex-1 overflow-y-auto p-5 space-y-3.5 no-scrollbar text-xs">
            
            <!-- 场馆与复制地址 -->
            <div class="bg-black/[0.025] rounded-xl p-3 border border-black/[0.04] flex items-center justify-between gap-3">
              <div class="flex items-start gap-2.5 min-w-0">
                <MapPin class="w-4 h-4 text-[#007AFF] shrink-0 mt-0.5" />
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-slate-900 truncate">{{ detailItem.address }}</div>
                  <div class="text-[11px] text-slate-400 mt-0.5">{{ detailItem.district }} · 距新街口 {{ detailItem.distance_km }} km</div>
                </div>
              </div>
              <button
                @click="copyAddress(detailItem.address)"
                class="shrink-0 px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 rounded-lg border border-black/[0.08] shadow-xs text-[11px] font-medium flex items-center gap-1 cursor-pointer transition-all"
              >
                <Check v-if="copiedAddress" class="w-3 h-3 text-[#34C759]" />
                <Copy v-else class="w-3 h-3 text-slate-400" />
                <span>{{ copiedAddress ? '已复制' : '复制地址' }}</span>
              </button>
            </div>

            <!-- 门票权益：绿色实体微卡片 -->
            <div class="bg-emerald-50/70 rounded-xl p-3 border border-emerald-200/60 flex items-center gap-2 text-emerald-900">
              <span class="w-2 h-2 rounded-full bg-[#34C759] shrink-0"></span>
              <span class="text-xs font-semibold">{{ detailItem.benefit || (detailItem.is_free ? '免票直入' : '详见活动原帖说明') }}</span>
            </div>

            <!-- 时间日程：图标+文本直接表达 -->
            <div class="bg-black/[0.025] rounded-xl p-3 border border-black/[0.04] flex items-center gap-2.5 text-slate-700">
              <Calendar class="w-4 h-4 text-slate-400 shrink-0" />
              <span class="font-medium text-xs">{{ detailItem.event_time_text }}</span>
            </div>

            <!-- 规则简介：纯白实体 Apple Card -->
            <div class="text-slate-700 leading-relaxed bg-white rounded-xl p-4 border border-black/[0.04] shadow-xs text-xs">
              {{ detailItem.summary || detailItem.title }}
            </div>
          </div>

          <!-- 底部操作底栏 -->
          <div class="p-4 border-t border-black/[0.04] bg-white/60 backdrop-blur-md flex items-center gap-2.5 shrink-0">
            <button
              @click="toggleFavorite(detailItem)"
              :class="[
                'flex-1 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-sm',
                isFavorite(detailItem.id)
                  ? 'bg-amber-500 text-white'
                  : 'bg-black/[0.05] hover:bg-black/[0.08] text-slate-800'
              ]"
            >
              <Star class="w-3.5 h-3.5" :class="isFavorite(detailItem.id) ? 'fill-white text-white' : 'text-slate-500'" />
              <span>{{ isFavorite(detailItem.id) ? '已在清单' : '加入待去' }}</span>
            </button>

            <a
              :href="detailItem.source_url || detailItem.obsidian_uri || '#'"
              target="_blank"
              class="flex-1 py-2.5 rounded-xl text-xs font-semibold bg-[#007AFF] hover:bg-[#0071EB] text-white transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-sm text-center"
            >
              <span>前往原平台查看</span>
              <ExternalLink class="w-3.5 h-3.5" />
            </a>

            <a
              href="/api/events/calendar.ics"
              download="nanjing-events.ics"
              class="p-2.5 rounded-xl bg-black/[0.05] hover:bg-black/[0.08] text-slate-700 transition-all cursor-pointer"
              title="导出到 Apple 日历 (iCalendar)"
            >
              <Calendar class="w-4 h-4 text-slate-600" />
            </a>

            <a
              v-if="detailItem.obsidian_uri"
              :href="detailItem.obsidian_uri"
              class="p-2.5 rounded-xl bg-black/[0.05] hover:bg-black/[0.08] text-slate-700 transition-all cursor-pointer"
              title="在 Obsidian 中打开"
            >
              <FileText class="w-4 h-4 text-slate-600" />
            </a>
          </div>

        </div>
      </div>
    </transition>

    <!-- 6. 概览统计模态框 (纯粹数据呈现，删除自嗨 ECharts 标签与冗余公文腔) -->
    <div
      v-if="showStatsModal"
      class="fixed inset-0 z-50 bg-black/35 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200 pointer-events-auto"
      @click.self="closeStatsModal"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="南京活动概览统计"
        class="relative w-full max-w-4xl bg-white/95 backdrop-blur-3xl rounded-[28px] border border-white/80 shadow-[0_25px_70px_rgba(0,0,0,0.25)] p-6 flex flex-col max-h-[92vh] overflow-hidden"
      >
        <div class="flex items-center justify-between pb-4 border-b border-black/[0.05] shrink-0">
          <div class="flex items-center gap-2">
            <h2 class="text-base font-semibold text-slate-900 tracking-tight">南京活动概览</h2>
            <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700">{{ filteredEvents.length }} 场</span>
          </div>
          <button
            @click="closeStatsModal"
            class="w-8 h-8 rounded-full bg-black/[0.04] hover:bg-black/[0.08] text-slate-600 flex items-center justify-center transition cursor-pointer"
            aria-label="关闭统计概览 (ESC)"
            title="关闭统计概览 (ESC)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto pt-4 space-y-6 no-scrollbar">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-xs">
              <h3 class="text-xs font-semibold text-slate-700 mb-2">区域分布</h3>
              <div id="district-chart" class="w-full h-64"></div>
            </div>
            <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-xs">
              <h3 class="text-xs font-semibold text-slate-700 mb-2">类别分布</h3>
              <div id="category-chart" class="w-full h-64"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 7. 轻量级 Apple 胶囊 Toast 提示 -->
    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-4"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-4"
    >
      <div v-if="toastMessage" class="fixed top-6 left-1/2 -translate-x-1/2 z-50 pointer-events-none">
        <div class="px-4 py-2 rounded-full bg-slate-900/90 text-white text-xs font-medium shadow-[0_10px_30px_rgba(0,0,0,0.2)] backdrop-blur-md border border-white/10 flex items-center gap-2">
          <span class="w-1.5 h-1.5 rounded-full" :class="toastType === 'error' ? 'bg-[#FF3B30]' : (toastType === 'success' ? 'bg-[#34C759]' : 'bg-[#007AFF]')"></span>
          <span>{{ toastMessage }}</span>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import L from 'leaflet';
import 'leaflet.heat';
import {
  Search, X, Building2, Globe, Star, Sparkles, Filter, RefreshCw,
  Calendar, Clock, MapPin, Navigation, ChevronRight, ChevronLeft, ChevronUp, ChevronDown,
  Layers, Flame, BarChart3, Crosshair, ExternalLink, Copy, Check, FileText, Disc, Compass
} from 'lucide-vue-next';
import { resolveEventCover } from './utils/covers.js';
import EmptyState from './components/EmptyState.vue';

// 城市中心常量 (南京新街口原点)
const XINJIEKOU = [118.7969, 32.0436]; // [lng, lat]

const DISTRICT_CENTERS = {
  '玄武区': [118.7977, 32.0482],
  '秦淮区': [118.7981, 32.0163],
  '建邺区': [118.7327, 32.0045],
  '鼓楼区': [118.7697, 32.0663],
  '栖霞区': [118.8806, 32.0945],
  '雨花台区': [118.7799, 31.9884],
  '江宁区': [118.8399, 31.9526],
  '浦口区': [118.6280, 32.0588],
  '六合区': [118.8413, 32.3421],
  '溧水区': [119.0287, 31.6531],
  '高淳区': [118.8758, 31.3271],
  '江北新区': [118.6980, 32.1480]
};

// 安全 Storage 存取防崩溃保护
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function safeGetFavorites() {
  try {
    const raw = localStorage.getItem('nj_lbs_favs');
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function safeSetFavorites(ids) {
  try {
    localStorage.setItem('nj_lbs_favs', JSON.stringify(ids));
  } catch (e) {}
}

// 状态变量
const events = ref([]);
const activeEventId = ref(null);
const detailItem = ref(null);
const currentViewMode = ref('cards');
const drawerOpen = ref(true);
const mobileSheetExpanded = ref(false);
const searchQuery = ref('');
const debouncedSearch = ref('');
let searchTimer = null;
watch(searchQuery, (val) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    debouncedSearch.value = (val || '').trim();
  }, 180);
});

const activeCategory = ref('ALL');
const venueFilter = ref('ALL');
const showFavoritesOnly = ref(false);
const showFilterPopover = ref(false);
const showStatsModal = ref(false);
const isSyncing = ref(false);
const copiedAddress = ref(false);
const timeFilter = ref('ALL');
const selectedDistrict = ref('ALL');
const radiusFilter = ref(0);
const freeOnly = ref(false);
const selectedCalendarDate = ref(null);
const sortBy = ref('distance');
const activeZoneLabel = ref('全城');
const favoriteIds = ref(safeGetFavorites());

// 地图图层状态
const mapStyleMode = ref('standard');
const showRings = ref(false);
const showHeatmap = ref(false);

// Toast
const toastMessage = ref('');
const toastType = ref('info');
let toastTimer = null;

function showToast(msg, type = 'info') {
  toastMessage.value = msg;
  toastType.value = type;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastMessage.value = '';
  }, 2500);
}

// 通用精简短标题算法 (剥离营销前缀感叹词与括号，严格词边界，绝不截断英文单词)
function extractShortTitle(title) {
  if (!title) return '同城活动';
  let t = String(title).replace(/[\(（【\[][^\)）】\]]*[\)）】\]]/g, ' ');
  t = t.replace(/^(?:202[4-9]年?|南京(?:市)?|华东|首届|第[一二三四五六七八九十0-9]+届|中国(?:\(南京\))?)/g, '').trim();
  t = t.replace(/^[^\s|｜:：!！·]{1,6}[|｜:：!！·]\s*/, '').trim();
  const parts = t.split(/[|｜:：!！·\s\-_—/]+/).filter(Boolean);
  let candidate = parts[0] || t;
  if (candidate.length < 2 && parts.length > 1) {
    candidate = parts[1];
  }
  if (candidate.length > 8) {
    const sub = candidate.slice(0, 8);
    const alphaMatch = sub.match(/[a-zA-Z]+$/);
    if (alphaMatch && alphaMatch.index >= 3) {
      candidate = sub.slice(0, alphaMatch.index);
    } else {
      candidate = sub;
    }
  }
  return candidate.trim() || '同城活动';
}

function getMarkerPriceLabel(item) {
  if (item.is_free) return '免票';
  const b = item.benefit || '';
  if (b.includes('免费') || b.includes('免票')) return '免票';
  if (b.includes('立减')) return '立减';
  if (b.includes('消费券')) return '领券';
  if (b.includes('打卡') || b.includes('赠')) return '礼遇';
  return '精选';
}

function getMarkerDotColor(category) {
  if (category === '南京展会') return '#FF9500';
  if (category === '羊毛福利') return '#34C759';
  return '#007AFF';
}

function getEventCover(item) {
  return resolveEventCover(item);
}

function getStatusInfo(item) {
  const tl = item.days_left;
  if (tl !== undefined && tl !== null) {
    if (tl <= 0) return { label: '已结束', bg: 'bg-slate-100 text-slate-500 border-slate-200' };
    if (tl <= 3) return { label: `剩${tl}天`, bg: 'bg-red-50 text-red-700 border-red-200/60' };
    if (tl <= 7) return { label: `剩${tl}天`, bg: 'bg-amber-50 text-amber-700 border-amber-200/60' };
  }
  return { label: '进行中', bg: 'bg-blue-50 text-blue-700 border-blue-200/60' };
}

// 选项配置
const categoryOptions = [
  { label: '全部', value: 'ALL' },
  { label: '展会', value: '南京展会' },
  { label: '活动', value: '南京活动' },
  { label: '福利', value: '羊毛福利' }
];

const timeFilterOptions = [
  { label: '全部', value: 'ALL' },
  { label: '周末', value: 'WEEKEND' },
  { label: '近7天', value: '7DAYS' },
  { label: '常设', value: 'LONGTERM' }
];

const sortOptions = [
  { label: '距离最近', value: 'distance' },
  { label: '即将截止', value: 'days_left' },
  { label: '最新收录', value: 'newest' }
];

const mapModes = [
  { id: 'standard', label: '高德全彩', color: '#007AFF' },
  { id: 'satellite', label: '高清卫星', color: '#34C759' },
  { id: 'apple', label: '苹果浅灰', color: '#8E8E93' },
  { id: 'dark', label: '午夜深色', color: '#1C1C1E' }
];

const districts = Object.keys(DISTRICT_CENTERS);

const zoneTeleports = [
  { label: '全城', coords: XINJIEKOU, zoom: 12 },
  { label: '新街口/鼓楼', coords: [118.7969, 32.0436], zoom: 14 },
  { label: '老门东/秦淮', coords: [118.7981, 32.0163], zoom: 15 },
  { label: '河西/建邺', coords: [118.7327, 32.0045], zoom: 14 },
  { label: '仙林大学城', coords: [118.9288, 32.1025], zoom: 14 },
  { label: '江宁百家湖', coords: [118.8258, 31.9325], zoom: 14 },
  { label: '江北核心区', coords: [118.6980, 32.1480], zoom: 14 }
];

function cycleMapMode() {
  const ids = mapModes.map(m => m.id);
  const curIdx = ids.indexOf(mapStyleMode.value);
  const nextIdx = (curIdx + 1) % ids.length;
  setMapMode(ids[nextIdx]);
}

const currentMapModeColor = computed(() => {
  const cur = mapModes.find(m => m.id === mapStyleMode.value);
  return cur ? cur.color : '#007AFF';
});

const hasActiveFilter = computed(() => {
  return timeFilter.value !== 'ALL' || selectedDistrict.value !== 'ALL' || radiusFilter.value > 0 || freeOnly.value;
});

function resetFilters() {
  timeFilter.value = 'ALL';
  selectedDistrict.value = 'ALL';
  radiusFilter.value = 0;
  freeOnly.value = false;
  venueFilter.value = 'ALL';
  showFavoritesOnly.value = false;
  searchQuery.value = '';
  debouncedSearch.value = '';
}

// 距离测算辅助函数
function calcDistance(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return Math.round(R * c * 10) / 10;
}

// 14 天滑动日历 (采用本地真实时区格式化，彻底消除 UTC+8 凌晨日期漂移)
const calendarDays = computed(() => {
  const days = [];
  const today = new Date();
  const weekMap = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  for (let i = 0; i < 14; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dayNum = String(d.getDate()).padStart(2, '0');
    const iso = `${y}-${m}-${dayNum}`;
    const count = events.value.filter(it => {
      const s = it.start_date || it.end_date;
      const e = it.end_date || it.start_date;
      if (!s && !e) return false;
      return (s || '') <= iso && (e || s) >= iso;
    }).length;
    days.push({
      iso,
      dateNum: d.getDate(),
      label: i === 0 ? '今天' : (i === 1 ? '明天' : weekMap[d.getDay()]),
      count,
      dots: count > 8 ? 3 : (count > 0 ? 2 : 0)
    });
  }
  return days;
});

function selectCalendarDay(iso) {
  selectedCalendarDate.value = selectedCalendarDate.value === iso ? null : iso;
}

// 数据筛选与排序 (支持防抖多字段检索与江北新区聚类)
const filteredEvents = computed(() => {
  let list = events.value.filter(it => {
    if (activeCategory.value !== 'ALL' && it.category !== activeCategory.value) return false;
    if (venueFilter.value === 'PHYSICAL' && it.is_online) return false;
    if (venueFilter.value === 'ONLINE' && !it.is_online) return false;
    if (showFavoritesOnly.value && !favoriteIds.value.includes(it.id)) return false;
    if (selectedDistrict.value !== 'ALL' && it.district !== selectedDistrict.value) return false;
    if (freeOnly.value && !it.is_free) return false;
    if (radiusFilter.value > 0 && it.distance_km > radiusFilter.value) return false;
    if (selectedCalendarDate.value) {
      const s = it.start_date || it.end_date;
      const e = it.end_date || it.start_date;
      if (s && e) {
        if (s > selectedCalendarDate.value || e < selectedCalendarDate.value) return false;
      }
    }
    if (debouncedSearch.value) {
      const q = debouncedSearch.value.toLowerCase();
      const match = (it.title || '').toLowerCase().includes(q) ||
                    (it.short_title || '').toLowerCase().includes(q) ||
                    (it.address || '').toLowerCase().includes(q) ||
                    (it.district || '').toLowerCase().includes(q) ||
                    (it.summary || '').toLowerCase().includes(q) ||
                    (Array.isArray(it.tags) && it.tags.some(t => t.toLowerCase().includes(q)));
      if (!match) return false;
    }
    return true;
  });

  list.sort((a, b) => {
    if (sortBy.value === 'distance') return (a.distance_km || 999) - (b.distance_km || 999);
    if (sortBy.value === 'days_left') return (a.days_left || 999) - (b.days_left || 999);
    return b.id - a.id;
  });

  return list;
});

// 时间轴分组 (彻底剔除营销废话)
const timelineGroups = computed(() => {
  const focus = [];
  const expiring = [];
  const upcoming = [];
  const longterm = [];

  filteredEvents.value.forEach(item => {
    const days = item.days_left ?? 99;
    if (days <= 3) {
      focus.push(item);
    } else if (days <= 7) {
      expiring.push(item);
    } else if (item.event_time_text?.includes('常设') || item.days_left > 30) {
      longterm.push(item);
    } else {
      upcoming.push(item);
    }
  });

  return [
    { id: 'focus', title: '近期焦点', items: focus, dotColor: 'bg-[#FF3B30]', nodeColor: 'bg-[#FF3B30]', badgeClass: 'bg-red-50 text-red-700' },
    { id: 'expiring', title: '即将结束', items: expiring, dotColor: 'bg-[#FF9500]', nodeColor: 'bg-[#FF9500]', badgeClass: 'bg-amber-50 text-amber-700' },
    { id: 'upcoming', title: '即将开始', items: upcoming, dotColor: 'bg-[#007AFF]', nodeColor: 'bg-[#007AFF]', badgeClass: 'bg-blue-50 text-blue-700' },
    { id: 'longterm', title: '常设展览', items: longterm, dotColor: 'bg-[#34C759]', nodeColor: 'bg-[#34C759]', badgeClass: 'bg-emerald-50 text-emerald-700' }
  ].filter(g => g.items.length > 0);
});

// ==========================================
// 地图核心架构与持久化 MarkerMap (0 DOM 重绘)
// ==========================================
let leafletMap = null;
let baseTileLayer = null;
let satelliteOverlayLayer = null;
let leafletMarkersGroup = null;
let ringsGroup = null;
let heatmapLayer = null;
let mapResizeObserver = null;

// 持久化 Map: eventId -> L.marker
const markerMap = new Map();

// 视口偏置投影 FlyTo (解决右侧抽屉遮挡点位问题)
function flyToWithOffset(lat, lng, zoom = 15) {
  if (!leafletMap) return;
  const isDesktop = window.innerWidth >= 768;
  const targetZoom = zoom || leafletMap.getZoom();
  const pt = leafletMap.project([lat, lng], targetZoom);
  
  let offsetX = 0;
  let offsetY = 0;
  if (isDesktop && drawerOpen.value) {
    // 桌面端抽屉宽 420px，将中心向右平移 210px，使点位落在左侧可视地图视觉中心
    offsetX = 210;
  } else if (!isDesktop && drawerOpen.value) {
    // 移动端 Bottom Sheet 高度约 50vh，将中心向下平移，使点位落在上方可视区域
    offsetY = window.innerHeight * 0.25;
  }
  
  const offsetPt = L.point(pt.x + offsetX, pt.y + offsetY);
  const centerLatLng = leafletMap.unproject(offsetPt, targetZoom);
  leafletMap.flyTo(centerLatLng, targetZoom, {
    duration: 0.8,
    easeLinearity: 0.25
  });
}

function initMap() {
  const container = document.getElementById('leaflet-map');
  if (!container || leafletMap) return;

  leafletMap = L.map('leaflet-map', {
    center: [XINJIEKOU[1], XINJIEKOU[0]],
    zoom: 12,
    zoomControl: false,
    attributionControl: false
  });

  applyMapLayer();

  leafletMarkersGroup = L.layerGroup().addTo(leafletMap);
  ringsGroup = L.layerGroup().addTo(leafletMap);

  function updateZoomLOD() {
    const mapBox = document.getElementById('map-container');
    if (mapBox && leafletMap) {
      if (leafletMap.getZoom() < 12) {
        mapBox.classList.add('map-zoomed-out');
      } else {
        mapBox.classList.remove('map-zoomed-out');
      }
    }
  }
  leafletMap.on('zoomend', updateZoomLOD);
  updateZoomLOD();

  // 采用原生 ResizeObserver 监听容器，彻底替代脆弱的 setTimeout，保障动画与视口切换时 0 灰色断层
  if (typeof ResizeObserver !== 'undefined' && container) {
    mapResizeObserver = new ResizeObserver(() => {
      if (leafletMap) {
        leafletMap.invalidateSize({ debounceMoveEvents: true });
      }
    });
    mapResizeObserver.observe(container);
  }

  syncMarkersDiff();
}

// 原生原生图层切换 (午夜深色采用 CartoDB DarkMatter，彻底告别偏色 CSS 滤镜)
function setMapMode(modeId) {
  mapStyleMode.value = modeId;
  applyMapLayer();
}

function applyMapLayer() {
  if (!leafletMap) return;

  if (baseTileLayer) leafletMap.removeLayer(baseTileLayer);
  if (satelliteOverlayLayer) leafletMap.removeLayer(satelliteOverlayLayer);
  satelliteOverlayLayer = null;

  if (mapStyleMode.value === 'dark') {
    // 原生午夜深色瓦片 (CartoDB DarkMatter)
    baseTileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', {
      subdomains: 'abcd',
      maxZoom: 19,
      minZoom: 8
    }).addTo(leafletMap);
  } else if (mapStyleMode.value === 'satellite') {
    baseTileLayer = L.tileLayer('https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}', {
      subdomains: ['1', '2', '3', '4'],
      maxZoom: 18,
      minZoom: 8
    }).addTo(leafletMap);

    satelliteOverlayLayer = L.tileLayer('https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
      subdomains: ['1', '2', '3', '4'],
      maxZoom: 18,
      minZoom: 8
    }).addTo(leafletMap);
  } else {
    // 高德全彩 / 苹果浅灰 (标准 GCJ-02 原生瓦片)
    baseTileLayer = L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
      subdomains: ['1', '2', '3', '4'],
      maxZoom: 18,
      minZoom: 9
    }).addTo(leafletMap);
  }
}

// 增量 Diff 同步标点 (列表数据变化时才增删，0 全量重绘)
function syncMarkersDiff() {
  if (!leafletMap || !leafletMarkersGroup) return;

  const currentList = filteredEvents.value;
  const newIds = new Set(currentList.map(it => it.id));

  // 1. 删除不再显示的 Marker
  for (const [id, marker] of markerMap.entries()) {
    if (!newIds.has(id)) {
      leafletMarkersGroup.removeLayer(marker);
      markerMap.delete(id);
    }
  }

  // 2. 坐标防重合径向散开
  const coordBuckets = {};
  const JITTER_STEP = 0.0022;

  currentList.forEach(item => {
    const rawLat = Number(item.lat);
    const rawLng = Number(item.lng);
    const bucketKey = Math.round(rawLat * 200) + '_' + Math.round(rawLng * 200);
    const countInBucket = coordBuckets[bucketKey] || 0;
    coordBuckets[bucketKey] = countInBucket + 1;

    // 若已存在于 Map 中，则保留，不进行 DOM 重建
    if (markerMap.has(item.id)) return;

    let finalLat = rawLat;
    let finalLng = rawLng;
    if (countInBucket > 0) {
      const angle = (countInBucket * (2 * Math.PI / 6)) + (countInBucket * 0.2);
      const radius = JITTER_STEP * (0.8 + 0.3 * Math.floor(countInBucket / 6));
      finalLat = rawLat + Math.sin(angle) * radius;
      finalLng = rawLng + Math.cos(angle) * radius * 1.15;
    }

    const dotColor = getMarkerDotColor(item.category);
    const shortName = escapeHtml(item.short_title || extractShortTitle(item.title));
    const priceLabel = escapeHtml(getMarkerPriceLabel(item));
    const safeTitle = escapeHtml(item.title);
    const safeId = escapeHtml(item.id);

    // Airbnb 胶囊打点 + 无障碍 A11y (防 DOM-XSS)
    const iconHtml = `
      <div class="apple-marker" id="leaf-marker-${safeId}" tabindex="0" role="button" aria-label="${safeTitle} - ${priceLabel}">
        <div class="marker-pill inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full shadow-[0_2px_8px_rgba(0,0,0,0.08),0_1px_2px_rgba(0,0,0,0.04)] border border-black/[0.06] font-medium text-[11px] whitespace-nowrap cursor-pointer transition-all duration-300 bg-white/95 text-slate-800 hover:bg-white hover:shadow-md">
          <span class="marker-dot w-2 h-2 rounded-full shrink-0" style="background-color: ${dotColor}"></span>
          <span class="marker-name font-semibold truncate max-w-[76px] text-slate-900">${shortName}</span>
          <span class="marker-price text-[10px] font-medium text-slate-500 hidden sm:inline">· ${priceLabel}</span>
        </div>
      </div>
    `;

    const customIcon = L.divIcon({
      html: iconHtml,
      className: 'bg-transparent border-0',
      iconSize: [0, 0],
      iconAnchor: [0, 0]
    });

    const marker = L.marker([finalLat, finalLng], { icon: customIcon });

    marker.on('click', () => {
      openDetail(item);
    });

    // 键盘无障碍支持 (Enter / Space 激活)
    nextTick(() => {
      const el = marker.getElement();
      if (el) {
        el.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openDetail(item);
          }
        });
      }
    });

    marker.addTo(leafletMarkersGroup);
    markerMap.set(item.id, marker);
  });
}

// 监听 activeEventId：仅通过 ClassList 极速切换 active，实现 0 DOM 重绘、60fps 满帧
watch(activeEventId, (newId, oldId) => {
  if (oldId && markerMap.has(oldId)) {
    const oldMarker = markerMap.get(oldId);
    oldMarker.setZIndexOffset(0);
    const el = oldMarker.getElement();
    if (el) el.classList.remove('active', 'marker-active');
  }

  if (newId && markerMap.has(newId)) {
    const newMarker = markerMap.get(newId);
    newMarker.setZIndexOffset(1000);
    const el = newMarker.getElement();
    if (el) el.classList.add('active', 'marker-active');
  }
});

// 监听 filteredEvents 变化时才触发 Diff 同步
watch(filteredEvents, () => {
  syncMarkersDiff();
  if (showHeatmap.value && heatmapLayer) {
    const heatPoints = filteredEvents.value.map(it => [it.lat, it.lng, 0.85]);
    heatmapLayer.setLatLngs(heatPoints);
  }
});

// 空间交互
function focusEvent(item) {
  activeEventId.value = item.id;
  flyToWithOffset(item.lat, item.lng, 15);
}

function openDetail(item) {
  activeEventId.value = item.id;
  detailItem.value = item;
  flyToWithOffset(item.lat, item.lng, 15);
  scrollToCard(item.id);
  try {
    const url = new URL(window.location.href);
    url.searchParams.set('id', item.id);
    window.history.replaceState(null, '', url.toString());
  } catch (e) {}
}

function closeDetail() {
  detailItem.value = null;
  try {
    const url = new URL(window.location.href);
    url.searchParams.delete('id');
    window.history.replaceState(null, '', url.toString());
  } catch (e) {}
}

function scrollToCard(itemId) {
  const el = document.getElementById('card-' + itemId) || document.getElementById('timeline-card-' + itemId);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function teleportToZone(zone) {
  activeZoneLabel.value = zone.label;
  if (leafletMap) {
    flyToWithOffset(zone.coords[1], zone.coords[0], zone.zoom);
  }
}

function recenterMap() {
  activeZoneLabel.value = '全城';
  flyToWithOffset(XINJIEKOU[1], XINJIEKOU[0], 12);
}

function onDistrictChange() {
  if (selectedDistrict.value in DISTRICT_CENTERS) {
    const center = DISTRICT_CENTERS[selectedDistrict.value];
    flyToWithOffset(center[1], center[0], 13);
  }
}

function toggleRings() {
  showRings.value = !showRings.value;
  if (!ringsGroup) return;
  ringsGroup.clearLayers();

  if (showRings.value) {
    const center = [XINJIEKOU[1], XINJIEKOU[0]];
    L.circle(center, { radius: 3000, color: '#007AFF', weight: 1.5, dashArray: '4 4', fillOpacity: 0.04 }).addTo(ringsGroup);
    L.circle(center, { radius: 5000, color: '#34C759', weight: 1.5, dashArray: '6 6', fillOpacity: 0.03 }).addTo(ringsGroup);
    L.circle(center, { radius: 10000, color: '#FF9500', weight: 1.5, dashArray: '8 8', fillOpacity: 0.02 }).addTo(ringsGroup);
  }
}

async function toggleHeatmap() {
  showHeatmap.value = !showHeatmap.value;
  if (!leafletMap) return;

  if (heatmapLayer) {
    leafletMap.removeLayer(heatmapLayer);
    heatmapLayer = null;
  }

  if (showHeatmap.value) {
    const heatPoints = filteredEvents.value.map(it => [it.lat, it.lng, 0.85]);
    heatmapLayer = L.heatLayer(heatPoints, {
      radius: 35,
      blur: 25,
      maxZoom: 15,
      gradient: { 0.2: '#007AFF', 0.5: '#34C759', 0.8: '#FF9500', 1.0: '#FF3B30' }
    }).addTo(leafletMap);
  }
}

// 待去清单收藏
function isFavorite(id) {
  return favoriteIds.value.includes(id);
}

function toggleFavorite(item) {
  const idx = favoriteIds.value.indexOf(item.id);
  const isNowFav = idx === -1;
  if (!isNowFav) {
    favoriteIds.value.splice(idx, 1);
    showToast('已移出待去清单');
  } else {
    favoriteIds.value.push(item.id);
    showToast('已加入待去清单', 'success');
  }
  safeSetFavorites(favoriteIds.value);

  // 异步同步至后端 SQLite 数据库，驱动 Apple iCal (.ics) 日历订阅实时生效
  try {
    fetch('/api/events/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: item.id,
        status: isNowFav ? '待去/已想去' : '已移出'
      })
    }).catch(() => {});
  } catch (e) {}
}

function handleImageError(e) {
  // 彻底阻断降级图片网络异常导致的无限递归死循环
  e.target.onerror = null;
  e.target.src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240" viewBox="0 0 400 240"><rect width="400" height="240" fill="%23f1f5f9"/><circle cx="200" cy="105" r="24" fill="%23e2e8f0"/><path d="M190 100l8 8 14-14" stroke="%2394a3b8" stroke-width="2.5" fill="none" stroke-linecap="round"/><text x="50%" y="155" font-family="system-ui,-apple-system" font-size="12" font-weight="500" fill="%2394a3b8" text-anchor="middle">暂无图片预览</text></svg>';
}

function fallbackCopyText(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand('copy');
  } catch (e) {}
  document.body.removeChild(ta);
}

function copyAddress(addr) {
  const text = addr || '南京市';
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopyText(text));
  } else {
    fallbackCopyText(text);
  }
  copiedAddress.value = true;
  showToast('场馆地址已复制到剪贴板', 'success');
  setTimeout(() => { copiedAddress.value = false; }, 2000);
}

// 数据加载与同步
function normalizeEvent(it) {
  const dist = it.distance_km || calcDistance(XINJIEKOU[1], XINJIEKOU[0], Number(it.lat || 32.0436), Number(it.lng || 118.7969));
  return {
    ...it,
    id: it.id || it.post_id,
    distance_km: dist,
    short_title: it.short_title || extractShortTitle(it.title),
    is_online: it.is_online !== undefined ? it.is_online : (it.address?.includes('全城') || it.address?.includes('线上') || it.category === '羊毛福利')
  };
}

function checkDeepLink() {
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const targetId = urlParams.get('id');
    if (targetId) {
      const match = events.value.find(e => String(e.id) === String(targetId));
      if (match) {
        nextTick(() => openDetail(match));
      }
    }
  } catch (e) {}
}

async function loadData() {
  try {
    const res = await fetch('/api/events');
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.items) && data.items.length) {
        events.value = data.items.map(normalizeEvent);
        checkDeepLink();
        return;
      }
    }
  } catch (e) {}

  // Fallback to static initial_events.json
  try {
    const fallbackRes = await fetch('./initial_events.json');
    if (fallbackRes.ok) {
      const fallbackData = await fallbackRes.json();
      if (Array.isArray(fallbackData) && fallbackData.length) {
        events.value = fallbackData.map(normalizeEvent);
        checkDeepLink();
        return;
      }
    }
  } catch (e) {
    showToast('连接本地服务失败，正以离线模式运行', 'error');
  }
}

async function triggerSync() {
  if (isSyncing.value) return;
  isSyncing.value = true;
  try {
    const res = await fetch('/api/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'incremental' })
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.items) && data.items.length) {
        events.value = data.items.map(normalizeEvent);
        showToast(`已增量更新 ${data.items.length} 条同城活动`, 'success');
      } else {
        showToast('已是最新数据', 'info');
      }
    } else {
      showToast('增量同步接口响应异常', 'error');
    }
  } catch (e) {
    showToast('网络同步未成功，请检查后端运行状态', 'error');
  }
  isSyncing.value = false;
}

// 统计模态框 (ECharts)
let districtChartInstance = null;
let categoryChartInstance = null;

function openStatsModal() {
  showStatsModal.value = true;
  nextTick(() => {
    initCharts();
  });
}

function closeStatsModal() {
  showStatsModal.value = false;
  if (districtChartInstance) {
    districtChartInstance.dispose();
    districtChartInstance = null;
  }
  if (categoryChartInstance) {
    categoryChartInstance.dispose();
    categoryChartInstance = null;
  }
}

let echartsLib = null;
async function getEcharts() {
  if (!echartsLib) {
    const mod = await import('./utils/echarts.js');
    echartsLib = mod.default;
  }
  return echartsLib;
}

async function initCharts() {
  const distEl = document.getElementById('district-chart');
  const catEl = document.getElementById('category-chart');
  if (!distEl || !catEl) return;

  const echarts = await getEcharts();
  if (!showStatsModal.value) return;
  const distCounts = {};
  districts.forEach(d => { distCounts[d] = 0; });
  const catCounts = { '南京展会': 0, '南京活动': 0, '羊毛福利': 0 };

  filteredEvents.value.forEach(it => {
    if (it.district in distCounts) distCounts[it.district]++;
    if (it.category in catCounts) catCounts[it.category]++;
  });

  if (districtChartInstance) districtChartInstance.dispose();
  districtChartInstance = echarts.init(distEl);
  districtChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: districts, axisLabel: { interval: 0, rotate: 30, fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ data: districts.map(d => distCounts[d]), type: 'bar', itemStyle: { color: '#007AFF', borderRadius: [4, 4, 0, 0] } }]
  });

  if (categoryChartInstance) categoryChartInstance.dispose();
  categoryChartInstance = echarts.init(catEl);
  categoryChartInstance.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      data: [
        { value: catCounts['南京展会'], name: '南京展会', itemStyle: { color: '#FF9500' } },
        { value: catCounts['南京活动'], name: '南京活动', itemStyle: { color: '#007AFF' } },
        { value: catCounts['羊毛福利'], name: '羊毛福利', itemStyle: { color: '#34C759' } }
      ]
    }]
  });
}

// 全局键盘监听 (Escape 键关闭弹窗)
function handleGlobalKeydown(e) {
  if (e.key === 'Escape') {
    if (showStatsModal.value) {
      closeStatsModal();
    } else if (detailItem.value) {
      closeDetail();
    } else if (showFilterPopover.value) {
      showFilterPopover.value = false;
    }
  }
}

function handleWindowResize() {
  if (districtChartInstance) districtChartInstance.resize();
  if (categoryChartInstance) categoryChartInstance.resize();
  if (leafletMap) leafletMap.invalidateSize();
}

watch(drawerOpen, () => {
  nextTick(() => {
    if (leafletMap) leafletMap.invalidateSize();
  });
});

watch(mobileSheetExpanded, () => {
  nextTick(() => {
    if (leafletMap) leafletMap.invalidateSize();
  });
});

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown);
  window.addEventListener('resize', handleWindowResize);
  initMap();
  loadData();
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown);
  window.removeEventListener('resize', handleWindowResize);
  if (mapResizeObserver) {
    mapResizeObserver.disconnect();
    mapResizeObserver = null;
  }
  if (leafletMap) {
    leafletMap.remove();
    leafletMap = null;
  }
});
</script>
