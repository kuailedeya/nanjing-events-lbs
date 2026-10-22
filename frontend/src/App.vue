<template>
  <div class="relative w-screen h-screen overflow-hidden bg-[#F5F5F7] select-none text-slate-900 font-sans antialiased">
    
    <!-- 1. 全屏底图 (高德官方全量图源，原生 GCJ-02 火星坐标) -->
    <div 
      id="map-container" 
      :class="[
        'absolute inset-0 w-full h-full z-0 transition-all duration-300',
        mapStyleMode === 'apple' ? 'amap-apple-filter' : '',
        mapStyleMode === 'dark' ? 'amap-dark-filter' : ''
      ]"
    >
      <div id="leaflet-map" class="w-full h-full"></div>
    </div>

    <!-- 2. 顶部：悬浮于地图左上方的通透圆角浮动岛屿 (Floating Island，严格单行无留白) -->
    <header class="absolute top-6 left-6 z-20 pointer-events-auto max-w-[calc(100vw-3rem)] md:max-w-[860px]">
      <div class="bg-white/85 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.08),0_1px_3px_rgba(0,0,0,0.03)] border border-white/80 p-1.5 sm:p-2 flex flex-nowrap items-center whitespace-nowrap gap-2 transition-all overflow-x-auto no-scrollbar">
        
        <!-- Airbnb 风格紧凑搜索框 -->
        <div class="relative flex items-center w-36 sm:w-48 md:w-56 shrink-0">
          <Search class="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索南京活动、展会、地标..."
            class="w-full pl-8 pr-6 py-1.5 bg-black/[0.04] focus:bg-white rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 outline-none border border-transparent focus:border-black/[0.08] focus:ring-4 focus:ring-[#007AFF]/12 transition-all duration-200"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="absolute right-2 text-slate-400 hover:text-slate-600 p-0.5 cursor-pointer transition-colors"
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
              'px-2.5 py-1 rounded-lg transition-all text-xs cursor-pointer',
              activeCategory === cat.value
                ? 'bg-white text-slate-900 shadow-[0_2px_6px_rgba(0,0,0,0.1)] font-semibold'
                : 'text-slate-500 hover:text-slate-900'
            ]"
          >
            {{ cat.label }}
          </button>
        </div>

        <!-- 线上/线下实体场馆切换器 (解决无物理地址羊毛堆叠新街口问题) -->
        <div class="flex items-center p-0.5 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600 shrink-0">
          <button
            @click="venueFilter = 'ALL'"
            :class="[
              'px-2 py-1 rounded-lg transition-all text-xs cursor-pointer',
              venueFilter === 'ALL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="全部活动与福利"
          >
            全览
          </button>
          <button
            @click="venueFilter = 'PHYSICAL'"
            :class="[
              'px-2 py-1 rounded-lg transition-all text-xs cursor-pointer flex items-center gap-1',
              venueFilter === 'PHYSICAL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="仅看有实体物理场馆的线下活动"
          >
            <Building2 class="w-3 h-3 text-[#007AFF]" />
            <span>线下实体</span>
          </button>
          <button
            @click="venueFilter = 'ONLINE'"
            :class="[
              'px-2 py-1 rounded-lg transition-all text-xs cursor-pointer flex items-center gap-1',
              venueFilter === 'ONLINE' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="仅看线上/全城通用银行与支付福利"
          >
            <Globe class="w-3 h-3 text-[#34C759]" />
            <span>全城羊毛</span>
          </button>
        </div>

        <!-- ⭐ 待去清单(N) 快捷收藏夹过滤按钮 -->
        <button
          @click="showFavoritesOnly = !showFavoritesOnly"
          :class="[
            'px-2.5 py-1.5 rounded-xl transition-all cursor-pointer flex items-center gap-1 text-xs font-medium shrink-0',
            showFavoritesOnly
              ? 'bg-amber-500 text-white shadow-sm font-semibold'
              : 'bg-black/[0.04] text-slate-700 hover:bg-black/[0.07]'
          ]"
          title="仅显示已加入待去清单的活动（按距离截止最近排序）"
        >
          <Star class="w-3.5 h-3.5" :class="showFavoritesOnly ? 'fill-white text-white' : 'text-amber-500 fill-amber-500'" />
          <span>待去清单</span>
          <span class="text-[11px] tabular-nums font-bold opacity-90">({{ favoriteIds.length }})</span>
        </button>

        <!-- 极简高级筛选按钮 -->
        <button
          @click="showFilterPopover = !showFilterPopover"
          :class="[
            'p-1.5 rounded-xl transition-all cursor-pointer relative shrink-0',
            hasActiveFilter ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:bg-black/[0.04]'
          ]"
          title="筛选范围与时间维度"
        >
          <SlidersHorizontal class="w-4 h-4" />
          <span v-if="hasActiveFilter" class="w-1.5 h-1.5 rounded-full bg-[#34C759] absolute top-1 right-1"></span>
        </button>

        <!-- 增量同步按钮 -->
        <button
          @click="triggerSync"
          :disabled="isSyncing"
          class="p-1.5 rounded-xl text-slate-600 hover:bg-black/[0.04] transition-all cursor-pointer shrink-0"
          title="增量同步最新社媒情报"
        >
          <RefreshCw :class="['w-4 h-4', isSyncing ? 'animate-spin text-[#007AFF]' : '']" />
        </button>

      </div>

      <!-- 下拉微质感 Popover 筛选器 (含时间维度与区域微调) -->
      <div
        v-if="showFilterPopover"
        class="mt-2 p-3 bg-white/90 backdrop-blur-2xl backdrop-saturate-150 rounded-[20px] shadow-[0_20px_50px_rgba(0,0,0,0.12)] border border-white/80 flex items-center gap-3 text-xs animate-in fade-in slide-in-from-top-2 duration-200 flex-wrap"
      >
        <!-- 时间维度筛选 -->
        <div class="flex items-center gap-1.5 text-slate-700">
          <Calendar class="w-3.5 h-3.5 text-slate-400" />
          <span class="font-medium text-slate-500">时间:</span>
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

        <!-- 行政区筛选 -->
        <div class="flex items-center gap-1.5 text-slate-600">
          <MapPin class="w-3.5 h-3.5 text-slate-400" />
          <select v-model="selectedDistrict" @change="onDistrictChange" class="bg-transparent border-0 outline-none font-medium cursor-pointer text-slate-800 text-xs">
            <option value="ALL">全城区域 (11区)</option>
            <option v-for="d in districts" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>

        <div class="h-3.5 w-px bg-slate-200"></div>

        <!-- 空间半径筛选 -->
        <div class="flex items-center gap-1.5 text-slate-600">
          <Compass class="w-3.5 h-3.5 text-slate-400" />
          <select v-model="radiusFilter" class="bg-transparent border-0 outline-none font-medium cursor-pointer text-slate-800 text-xs">
            <option :value="0">全城距离</option>
            <option :value="3">3 km 内 (核心商圈)</option>
            <option :value="5">5 km 内 (主城生活圈)</option>
            <option :value="10">10 km 内 (绕城圈)</option>
            <option :value="20">20 km 内 (都市圈)</option>
          </select>
        </div>

        <div class="h-3.5 w-px bg-slate-200"></div>

        <!-- 仅看免费 -->
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
          重置筛选
        </button>
      </div>
    </header>

    <!-- 3. 左下角：macOS 悬浮 Dock 控制台 (含4模底图、辐射圈、热力图与📊数据统计) -->
    <div class="absolute bottom-6 left-6 z-20 flex items-center gap-2 pointer-events-auto">
      
      <!-- 地图底图模式切换胶囊 (全彩 / 卫星 / 浅灰 / 午夜) -->
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

      <!-- 新街口中心辐射同心圈切换 -->
      <button
        @click="toggleRings"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showRings ? 'bg-slate-950 text-white border-slate-950 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
        title="在地图上显示新街口 3km/5km/10km 辐射同心圈"
      >
        <CircleDot class="w-3.5 h-3.5" :class="showRings ? 'text-[#34C759]' : 'text-slate-400'" />
        <span>辐射圈</span>
      </button>

      <!-- 🔥 活动热力分布图开关 -->
      <button
        @click="toggleHeatmap"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showHeatmap ? 'bg-rose-950 text-rose-100 border-rose-900 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
        title="在地图上叠加南京活动密度热力图"
      >
        <Flame class="w-3.5 h-3.5" :class="showHeatmap ? 'text-[#FF3B30] fill-[#FF3B30]' : 'text-slate-400'" />
        <span>热力图</span>
      </button>

      <!-- 📊 数据统计可视化图表弹窗 (ECharts) -->
      <button
        @click="openStatsModal"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showStatsModal ? 'bg-[#007AFF] text-white border-[#007AFF] shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
        title="查看南京活动多维数据洞察 (ECharts 空间图表)"
      >
        <BarChart3 class="w-3.5 h-3.5" :class="showStatsModal ? 'text-white' : 'text-[#007AFF]'" />
        <span>数据统计</span>
      </button>

      <!-- 一键复位新街口中心 -->
      <button
        @click="recenterMap"
        class="p-2.5 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-slate-700 hover:text-slate-950 hover:bg-white transition cursor-pointer"
        title="复位至新街口中心"
      >
        <LocateFixed class="w-4 h-4" />
      </button>

    </div>

    <!-- 4. 右侧：Airbnb 风格悬浮卡片抽屉 (Liquid Glass Frosted Sheet) -->
    <aside
      :class="[
        'absolute top-6 right-6 bottom-6 z-20 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col pointer-events-auto',
        drawerOpen
          ? 'w-[380px] md:w-[440px] translate-x-0'
          : 'w-12 translate-x-[calc(100%-2.5rem)]'
      ]"
    >
      <div class="relative w-full h-full bg-[#F5F5F7]/85 backdrop-blur-2xl backdrop-saturate-150 rounded-[28px] border border-white/80 shadow-[0_20px_50px_rgba(0,0,0,0.1)] flex flex-col overflow-hidden">
        
        <!-- 固定头部：标题栏 + 视野联动开关 + 瞬移栏 (flex-shrink-0 绝对防穿模) -->
        <div class="flex-shrink-0 z-10 bg-[#F5F5F7]/95 backdrop-blur-md">
          <!-- 标题栏与展开/折叠 -->
          <div class="px-5 pt-4 pb-2.5 flex items-center justify-between border-b border-black/[0.04]">
            <div class="flex items-center gap-2">
              <h2 class="text-sm font-semibold text-slate-900 tracking-tight">南京精选探索</h2>
              <span class="text-xs font-semibold text-slate-400 tabular-nums">({{ filteredEvents.length }})</span>
              
              <!-- 苹果风“视野联动”微开关 -->
              <button
                @click="toggleBoundsFilter"
                class="ml-1.5 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium transition-all cursor-pointer"
                :class="boundsFilterEnabled ? 'bg-emerald-50 text-emerald-800 border border-emerald-200/60 shadow-2xs' : 'bg-black/[0.04] text-slate-500 hover:text-slate-700'"
                title="开启后仅展示当前地图可视矩形范围内的线下活动"
              >
                <span class="w-1.5 h-1.5 rounded-full transition-colors" :class="boundsFilterEnabled ? 'bg-[#34C759]' : 'bg-slate-300'"></span>
                <span>视野联动</span>
              </button>

              <span v-if="showFavoritesOnly" class="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-full font-semibold">待去清单</span>
            </div>

            <button
              @click="drawerOpen = !drawerOpen"
              class="w-7 h-7 rounded-lg bg-white/70 hover:bg-white text-slate-500 hover:text-slate-900 flex items-center justify-center transition shadow-sm cursor-pointer"
              :title="drawerOpen ? '收起抽屉' : '展开抽屉'"
            >
              <ChevronRight :class="['w-4 h-4 transition-transform duration-200', drawerOpen ? 'rotate-0' : 'rotate-180']" />
            </button>
          </div>

          <!-- 南京核心片区瞬移胶囊栏 -->
          <div class="px-4 py-2 border-b border-black/[0.03] bg-black/[0.015] flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            <span class="text-[10px] text-slate-400 font-medium shrink-0 flex items-center gap-0.5">
              <Sparkles class="w-3 h-3 text-[#007AFF]" />
              <span>瞬移:</span>
            </span>
            <button
              v-for="zone in teleportZones"
              :key="zone.id"
              @click="teleportToZone(zone)"
              :class="[
                'px-2.5 py-1 rounded-full text-[11px] font-medium whitespace-nowrap transition-all cursor-pointer shrink-0',
                activeZoneId === zone.id
                  ? 'bg-slate-950 text-white font-semibold shadow-xs'
                  : 'bg-white/80 hover:bg-white text-slate-600 border border-black/[0.04]'
              ]"
            >
              {{ zone.name }}
            </button>
          </div>
        </div>

        <!-- 独立卡片滚动容器 (flex-1 min-h-0 overflow-y-auto，彻底消除顶部残缺与穿模) -->
        <div class="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 no-scrollbar" id="cards-container">
          <div
            v-for="item in filteredEvents"
            :key="item.id"
            :id="'card-' + item.id"
            @click="openDetail(item)"
            :class="[
              'group bg-white rounded-2xl p-3.5 transition-all duration-300 cursor-pointer border flex flex-col',
              activeEventId === item.id
                ? 'ring-2 ring-[#007AFF] border-transparent shadow-[0_16px_36px_rgba(0,122,255,0.16)] -translate-y-1'
                : 'border-black/[0.04] shadow-[0_4px_16px_rgba(0,0,0,0.04)] hover:shadow-[0_12px_30px_rgba(0,0,0,0.08)] hover:-translate-y-1'
            ]"
          >
            <!-- Bento 封面图 (高颜值潮流探索封面，带圆角优化 rounded-xl) -->
            <div class="relative w-full h-36 rounded-xl overflow-hidden mb-3 bg-slate-100 group-hover:scale-[1.01] transition-transform duration-300 shrink-0">
              <img
                :src="getEventCover(item)"
                :alt="item.title"
                loading="lazy"
                class="w-full h-full object-cover rounded-xl"
              />
              <div class="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-black/10"></div>
              
              <!-- 悬浮在封面左上方的类别胶囊 -->
              <span class="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-tight backdrop-blur-md bg-white/90 shadow-sm flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: getMarkerDotColor(item.category) }"></span>
                <span class="text-slate-800">{{ item.category }}</span>
              </span>

              <!-- 悬浮在封面右上方的距离标签 -->
              <span class="absolute top-2.5 right-2.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium tracking-tight backdrop-blur-md bg-black/50 text-white tabular-nums flex items-center gap-1">
                <span>{{ item.distance_km }} km</span>
                <span class="text-white/60">·</span>
                <span class="text-white/80">新街口</span>
              </span>

              <!-- 悬浮在封面左下方的免票/福利徽标 -->
              <span class="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded-lg text-[11px] font-medium tracking-tight backdrop-blur-md bg-white/90 text-slate-800 flex items-center gap-1">
                <span class="font-semibold text-[#34C759]" v-if="item.is_free">免票直入</span>
                <span class="text-slate-700 font-medium" v-else>{{ item.benefit }}</span>
              </span>

              <!-- 线上/全城微标 -->
              <span v-if="item.is_online" class="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded-lg text-[10px] font-semibold tracking-tight backdrop-blur-md bg-emerald-500/80 text-white">
                线上/全城
              </span>
            </div>

            <!-- 结构化时态小标签行 (根据日期自动计算时态状态) -->
            <div class="mb-1.5 flex items-center gap-2">
              <span
                :class="[
                  'px-2 py-0.5 rounded-md text-[10px] font-semibold tracking-tight border inline-flex items-center gap-1',
                  getStatusInfo(item).bg
                ]"
              >
                <Clock class="w-3 h-3 shrink-0" />
                <span>{{ getStatusInfo(item).label }}</span>
              </span>
              <span class="text-[11px] text-slate-400 truncate">{{ item.event_time_text }}</span>
            </div>

            <!-- 主标题 (严格 font-semibold text-slate-900，潮流探索排版) -->
            <h3 class="text-sm font-semibold text-slate-900 leading-snug tracking-[-0.01em] group-hover:text-[#007AFF] transition-colors mb-2 line-clamp-2">
              {{ item.title }}
            </h3>

            <!-- 地理元数据行 -->
            <div class="text-xs text-slate-500 space-y-1 mb-3">
              <div class="flex items-center gap-1.5 text-slate-600">
                <MapPin class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span class="truncate font-medium text-slate-800">{{ item.address }}</span>
                <span class="text-slate-300">·</span>
                <span class="shrink-0 text-slate-500 bg-black/[0.03] px-1.5 py-0.5 rounded text-[11px]">{{ item.district }}</span>
              </div>
            </div>

            <!-- 操作底栏：彻底去除导航！左侧保留待去，右侧改为【📍 定位】与【详情 >】 -->
            <div class="pt-2.5 border-t border-black/[0.04] flex items-center justify-between mt-auto" @click.stop>
              <!-- 收藏待去清单切换按钮 -->
              <button
                @click.stop="toggleFavorite(item)"
                :class="[
                  'px-2.5 py-1 rounded-full text-[11px] font-medium transition-all flex items-center gap-1 cursor-pointer',
                  isFavorite(item.id)
                    ? 'bg-amber-50 text-amber-800 border border-amber-200'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
                ]"
                :title="isFavorite(item.id) ? '已在待去清单，点击取消' : '加入待去清单'"
              >
                <Star class="w-3 h-3" :class="isFavorite(item.id) ? 'fill-amber-500 text-amber-500' : 'text-slate-400'" />
                <span>{{ isFavorite(item.id) ? '已待去' : '☆ 待去' }}</span>
              </button>

              <div class="flex items-center gap-1.5">
                <!-- 📍 定位：平滑聚焦并高亮该 Marker -->
                <button
                  @click.stop="focusEvent(item)"
                  class="text-slate-600 hover:text-[#007AFF] text-[11px] font-medium flex items-center gap-1 py-1 px-2 hover:bg-blue-50/50 rounded-lg transition-colors cursor-pointer"
                  title="在地图上平滑聚焦并高亮定位"
                >
                  <MapPin class="w-3 h-3 text-slate-400 group-hover:text-[#007AFF]" />
                  <span>定位</span>
                </button>

                <!-- 详情 >：滑出二级完整图文详情与原帖链接 -->
                <button
                  @click.stop="openDetail(item)"
                  class="text-slate-700 hover:text-slate-900 text-[11px] font-semibold flex items-center gap-0.5 py-1 px-2 hover:bg-black/[0.04] rounded-lg transition-colors cursor-pointer"
                  title="查看完整图文详情与原帖链接"
                >
                  <span>详情</span>
                  <ChevronRight class="w-3.5 h-3.5 text-slate-400" />
                </button>
              </div>
            </div>

          </div>

          <!-- 空状态 -->
          <div v-if="filteredEvents.length === 0" class="py-20 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
            <Compass class="w-8 h-8 text-slate-300" />
            <span>当前筛选条件下暂无活动</span>
            <button
              @click="resetAllFilters"
              class="text-[#007AFF] hover:underline font-semibold text-xs mt-1 cursor-pointer"
            >
              清空所有过滤条件
            </button>
          </div>
        </div>

      </div>
    </aside>

    <!-- 5. 二级详情抽屉/模态框 (Activity Detail Sheet，彻底移除导航，增加复制地址与原帖链接) -->
    <div
      v-if="detailItem"
      class="fixed inset-0 z-40 bg-black/25 backdrop-blur-xs flex justify-end transition-opacity duration-300 pointer-events-auto"
      @click.self="closeDetail"
    >
      <div
        class="w-[420px] md:w-[480px] h-full bg-white/95 backdrop-blur-3xl shadow-[0_25px_70px_rgba(0,0,0,0.2)] border-l border-white/80 flex flex-col overflow-hidden animate-in slide-in-from-right duration-300"
      >
        <!-- 详情面板顶部标题栏 -->
        <div class="px-6 py-4 flex items-center justify-between border-b border-black/[0.06] bg-white/80 backdrop-blur-md shrink-0">
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold" :class="getCategoryBadgeClass(detailItem.category)">
              {{ detailItem.category }}
            </span>
            <span
              :class="[
                'px-2 py-0.5 rounded-md text-[10px] font-semibold tracking-tight border inline-flex items-center gap-1',
                getStatusInfo(detailItem).bg
              ]"
            >
              {{ getStatusInfo(detailItem).label }}
            </span>
          </div>

          <button
            @click="closeDetail"
            class="w-8 h-8 rounded-full bg-black/[0.05] hover:bg-black/[0.1] text-slate-600 flex items-center justify-center transition cursor-pointer"
            title="关闭详情 (ESC)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- 详情滚动正文 -->
        <div class="flex-1 overflow-y-auto p-6 space-y-5 no-scrollbar">
          
          <!-- 大图封面 (Hero Image) -->
          <div class="relative w-full h-52 rounded-2xl overflow-hidden bg-slate-100 shadow-md shrink-0">
            <img
              :src="getEventCover(detailItem)"
              :alt="detailItem.title"
              class="w-full h-full object-cover"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/10"></div>
            
            <div class="absolute bottom-3.5 left-4 right-4 text-white">
              <div class="text-[11px] opacity-80 mb-0.5 font-medium flex items-center gap-2">
                <span>{{ detailItem.district }}</span>
                <span>·</span>
                <span>距新街口 {{ detailItem.distance_km }} km</span>
              </div>
              <h2 class="text-base font-bold leading-tight line-clamp-2">
                {{ detailItem.title }}
              </h2>
            </div>
          </div>

          <!-- 具体场馆文本地址卡片 (配 [复制地址] 按钮，绝无导航按钮) -->
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
              title="复制场馆具体地址"
            >
              <Check v-if="copiedAddress" class="w-3 h-3 text-[#34C759]" />
              <Copy v-else class="w-3 h-3 text-slate-500" />
              <span>{{ copiedAddress ? '已复制' : '复制地址' }}</span>
            </button>
          </div>

          <!-- 时间与权益板块 -->
          <div class="bg-black/[0.025] rounded-2xl p-4 space-y-2.5 border border-black/[0.04] text-xs">
            <div class="flex items-start gap-2.5 text-slate-700">
              <Clock class="w-4 h-4 text-[#34C759] shrink-0 mt-0.5" />
              <div>
                <div class="font-semibold text-slate-900">{{ detailItem.event_time_text }}</div>
                <div class="text-slate-400 text-[11px]">时态状态: {{ getStatusInfo(detailItem).label }}</div>
              </div>
            </div>

            <div class="h-px bg-black/[0.04]"></div>

            <div class="flex items-start gap-2.5 text-slate-700">
              <Sparkles class="w-4 h-4 text-[#FF9500] shrink-0 mt-0.5" />
              <div>
                <div class="font-semibold text-slate-900">{{ detailItem.benefit }}</div>
                <div class="text-slate-400 text-[11px]">发布方: {{ detailItem.author || '南京同城社媒情报' }} ({{ detailItem.platform || '公众号' }})</div>
              </div>
            </div>
          </div>

          <!-- 活动详情正文与活动指引 (Summary / Action Guide) -->
          <div class="space-y-3">
            <h3 class="text-xs font-bold text-slate-900 tracking-wider uppercase flex items-center gap-1.5">
              <span>活动简介与入场要点</span>
            </h3>
            <div class="text-xs text-slate-600 leading-relaxed space-y-2 bg-white rounded-xl p-4 border border-black/[0.04]">
              <p class="whitespace-pre-line">{{ detailItem.summary || '暂无详细介绍文本，请点击底部按钮前往原帖查看详情。' }}</p>
              <div v-if="detailItem.action_guide" class="mt-3 p-3 bg-emerald-50/70 border border-emerald-100 rounded-lg text-emerald-900 text-[11px]">
                <div class="font-bold mb-1">打卡/羊毛攻略指南:</div>
                <div>{{ detailItem.action_guide }}</div>
              </div>
            </div>
          </div>

          <!-- 本地知识库双向文档 -->
          <div v-if="detailItem.obsidian_path" class="text-[11px] text-slate-400 flex items-center gap-1.5">
            <FileText class="w-3.5 h-3.5 text-slate-400" />
            <span>知识库文档: {{ detailItem.obsidian_path }}</span>
          </div>

        </div>

        <!-- 底部大按钮操作区 (纯检索/收藏闭环，彻底去除导航) -->
        <div class="p-5 border-t border-black/[0.06] bg-white/90 backdrop-blur-md flex items-center gap-2.5 shrink-0">
          <!-- 待去清单切换按钮 -->
          <button
            @click="toggleFavorite(detailItem)"
            :class="[
              'flex-1 py-3 px-3 rounded-2xl font-semibold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-sm',
              isFavorite(detailItem.id)
                ? 'bg-amber-500 text-white shadow-amber-500/20'
                : 'bg-black/[0.05] hover:bg-black/[0.08] text-slate-800'
            ]"
          >
            <Star class="w-4 h-4" :class="isFavorite(detailItem.id) ? 'fill-white text-white' : 'text-amber-500 fill-amber-500'" />
            <span>{{ isFavorite(detailItem.id) ? '已在待去清单' : '加入待去清单' }}</span>
          </button>

          <!-- 前往原平台查看链接 -->
          <a
            :href="detailItem.source_url || detailItem.obsidian_uri || '#'"
            target="_blank"
            class="flex-1 py-3 px-3 rounded-2xl font-semibold text-xs bg-[#007AFF] hover:bg-[#0071EB] text-white flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-sm text-center"
            title="在原平台或知识库中查看完整原文"
          >
            <ExternalLink class="w-4 h-4" />
            <span>前往原平台查看</span>
          </a>

          <!-- Obsidian 知识库深链 -->
          <a
            v-if="detailItem.obsidian_uri"
            :href="detailItem.obsidian_uri"
            target="_blank"
            class="py-3 px-3.5 rounded-2xl font-semibold text-xs bg-slate-900 hover:bg-black text-white flex items-center justify-center gap-1.5 transition-all shadow-sm cursor-pointer"
            title="在 Obsidian 中打开双向笔记"
          >
            <FileText class="w-4 h-4" />
            <span>笔记</span>
          </a>
        </div>

      </div>
    </div>

    <!-- 6. 📊 数据洞察可视化图表弹窗 (ECharts Apple Bento 风格居中模态框) -->
    <div
      v-if="showStatsModal"
      class="fixed inset-0 z-50 bg-black/35 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200 pointer-events-auto"
      @click.self="closeStatsModal"
    >
      <div class="relative w-full max-w-4xl bg-white/95 backdrop-blur-3xl rounded-[28px] border border-white/80 shadow-[0_25px_70px_rgba(0,0,0,0.25)] p-6 flex flex-col max-h-[92vh] overflow-hidden">
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between pb-4 border-b border-black/[0.05] shrink-0">
          <div>
            <div class="flex items-center gap-2">
              <BarChart3 class="w-5 h-5 text-[#007AFF]" />
              <h2 class="text-base font-semibold text-slate-900 tracking-tight">南京活动 · 数据洞察全景</h2>
              <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-[#007AFF] border border-blue-200/50">ECharts 可视化分析</span>
            </div>
            <p class="text-xs text-slate-500 mt-1">当前已精准收录 {{ filteredEvents.length }} 项同城活动，涵盖 11 个行政区与各主流社媒情报</p>
          </div>
          <button
            @click="closeStatsModal"
            class="w-8 h-8 rounded-full bg-black/[0.04] hover:bg-black/[0.08] text-slate-600 flex items-center justify-center transition cursor-pointer"
            title="关闭 (ESC)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- Bento 栅格图表主体 -->
        <div class="flex-1 overflow-y-auto pt-4 space-y-4 no-scrollbar">
          <!-- 上排：各行政区柱状图 + 活动类型环形饼图 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- ① 南京各行政区活动密度柱状图 -->
            <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex flex-col">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-semibold text-slate-900">各行政区活动密度分布</span>
                <span class="text-[11px] text-slate-400">单位: 场次</span>
              </div>
              <div ref="districtChartRef" class="w-full h-56"></div>
            </div>

            <!-- ② 活动类型占比环形饼图 -->
            <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex flex-col">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-semibold text-slate-900">活动类型占比结构</span>
                <span class="text-[11px] text-slate-400">分类分布</span>
              </div>
              <div ref="categoryChartRef" class="w-full h-56"></div>
            </div>
          </div>

          <!-- 下排：③ 活动时间分布（进行中 vs 即将开始 vs 即将截止）统计面板 -->
          <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-semibold text-slate-900">活动时空时态分布阶段</span>
              <span class="text-[11px] text-slate-400">时态生命周期</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <!-- 进行中 / 已开展 -->
              <div class="bg-slate-50/80 rounded-xl p-3.5 border border-black/[0.03] flex flex-col">
                <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span class="flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-[#34C759]"></span>
                    <span>进行中 / 已开展</span>
                  </span>
                  <span class="font-semibold text-slate-900 tabular-nums">{{ timeStats.ongoing }} 场</span>
                </div>
                <div class="text-xl font-bold text-slate-900 tabular-nums">{{ timeStats.ongoingPercent }}%</div>
                <div class="w-full h-1.5 bg-slate-200 rounded-full mt-2.5 overflow-hidden">
                  <div class="h-full bg-[#34C759] rounded-full transition-all duration-500" :style="{ width: timeStats.ongoingPercent + '%' }"></div>
                </div>
              </div>

              <!-- 即将截止 (剩≤3天) -->
              <div class="bg-slate-50/80 rounded-xl p-3.5 border border-black/[0.03] flex flex-col">
                <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span class="flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-[#FF9500]"></span>
                    <span>即将截止 (剩≤3天)</span>
                  </span>
                  <span class="font-semibold text-slate-900 tabular-nums">{{ timeStats.expiring }} 场</span>
                </div>
                <div class="text-xl font-bold text-slate-900 tabular-nums">{{ timeStats.expiringPercent }}%</div>
                <div class="w-full h-1.5 bg-slate-200 rounded-full mt-2.5 overflow-hidden">
                  <div class="h-full bg-[#FF9500] rounded-full transition-all duration-500" :style="{ width: timeStats.expiringPercent + '%' }"></div>
                </div>
              </div>

              <!-- 即将开始 / 长期规划 -->
              <div class="bg-slate-50/80 rounded-xl p-3.5 border border-black/[0.03] flex flex-col">
                <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span class="flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-[#007AFF]"></span>
                    <span>长期 / 后续开展</span>
                  </span>
                  <span class="font-semibold text-slate-900 tabular-nums">{{ timeStats.upcoming }} 场</span>
                </div>
                <div class="text-xl font-bold text-slate-900 tabular-nums">{{ timeStats.upcomingPercent }}%</div>
                <div class="w-full h-1.5 bg-slate-200 rounded-full mt-2.5 overflow-hidden">
                  <div class="h-full bg-[#007AFF] rounded-full transition-all duration-500" :style="{ width: timeStats.upcomingPercent + '%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import L from 'leaflet';
import * as echarts from 'echarts';
import {
  Search, SlidersHorizontal, RefreshCw,
  ChevronRight, ExternalLink, MapPin, X, CircleDot, LocateFixed, Clock,
  Compass, FileText, Star, Flame, Calendar, Building2,
  Globe, Sparkles, BarChart3, Copy, Check
} from 'lucide-vue-next';

// 南京新街口原点 (高德 GCJ-02)
const XINJIEKOU = [118.7842, 32.0418];

// 南京各行政区视觉巡航焦点
const DISTRICT_CENTERS = {
  '玄武区': [118.7979, 32.0486],
  '秦淮区': [118.7981, 32.0112],
  '建邺区': [118.7327, 32.0045],
  '鼓楼区': [118.7699, 32.0672],
  '栖霞区': [118.8807, 32.0963],
  '雨花台区': [118.7799, 31.9886],
  '江宁区': [118.8399, 31.9526],
  '浦口区': [118.6280, 32.0588],
  '六合区': [118.8413, 32.3426],
  '溧水区': [119.0287, 31.6531],
  '高淳区': [118.9926, 31.3271]
};

// 南京 6 大核心片区瞬移热区
const teleportZones = [
  { id: 'all', name: '全城', center: [118.7969, 32.0602], zoom: 12 },
  { id: 'xinjiekou', name: '新街口/鼓楼', center: [118.7842, 32.0418], zoom: 14 },
  { id: 'laomendong', name: '老门东/秦淮', center: [118.7981, 32.0112], zoom: 14 },
  { id: 'hexi', name: '河西/建邺', center: [118.7327, 32.0045], zoom: 14 },
  { id: 'xianlin', name: '仙林大学城', center: [118.9180, 32.1050], zoom: 13 },
  { id: 'jiangning', name: '江宁百家湖', center: [118.8399, 31.9526], zoom: 13 }
];
const activeZoneId = ref('all');

// 精选高颜值封面图映射库 (潮流探索 Bento 风格)
const COVER_MAP = {
  'wx_fd0cb00e9b69': 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600&auto=format&fit=crop&q=80',
  'wx_d164747d9f7e': 'https://images.unsplash.com/photo-1563089145-599997674d42?w=600&auto=format&fit=crop&q=80',
  'wx_e4b0c708103d': 'https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=600&auto=format&fit=crop&q=80',
  'wx_1bb8674ef2fc': 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=600&auto=format&fit=crop&q=80',
  'wx_f6842d9b3baa': 'https://images.unsplash.com/photo-1511578314322-379afb476865?w=600&auto=format&fit=crop&q=80',
  'wx_d34b11ebd354': 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=600&auto=format&fit=crop&q=80',
  'wx_b05c2f95dc4b': 'https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=600&auto=format&fit=crop&q=80',
  'xhs_79a2d4ef64ea': 'https://images.unsplash.com/photo-1513151233558-d860c5398176?w=600&auto=format&fit=crop&q=80',
  'wx_56f253fb4639': 'https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&auto=format&fit=crop&q=80',
  'wx_77ab536a4b13': 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=80',
  'wx_33b3d2e52c0c': 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&auto=format&fit=crop&q=80',
  'wx_0e91fefd7f2a': 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&auto=format&fit=crop&q=80',
  'wx_5e855d59f61b': 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=600&auto=format&fit=crop&q=80',
  'wx_3131ff6067bc': 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=600&auto=format&fit=crop&q=80',
  'wx_4751840a2974': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&auto=format&fit=crop&q=80'
};

function getEventCover(item) {
  if (!item) return '';
  if (COVER_MAP[item.id]) return COVER_MAP[item.id];
  if (item.category === '南京展会') return 'https://images.unsplash.com/photo-1518998053901-5348d3961a04?w=600&auto=format&fit=crop&q=80';
  if (item.category === '羊毛福利') return 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=600&auto=format&fit=crop&q=80';
  return 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=80';
}

const events = ref([]);
const activeCategory = ref('ALL');
const selectedDistrict = ref('ALL');
const radiusFilter = ref(0);
const freeOnly = ref(false);
const searchQuery = ref('');
const activeEventId = ref(null);
const drawerOpen = ref(true);
const isSyncing = ref(false);
const showFilterPopover = ref(false);
const showRings = ref(false);
const showHeatmap = ref(false);
const showStatsModal = ref(false);

// 线上/线下区分筛选 ('ALL' | 'PHYSICAL' | 'ONLINE')
const venueFilter = ref('ALL');

// 视野联动筛选 ('false' | 'true')
const boundsFilterEnabled = ref(false);
const mapBounds = ref(null);

// 时间维度筛选 ('ALL' | 'TODAY' | 'WEEKEND' | 'EXPIRING')
const timeFilter = ref('ALL');
const timeFilterOptions = [
  { value: 'ALL', label: '全部时间' },
  { value: 'TODAY', label: '今日' },
  { value: 'WEEKEND', label: '本周末' },
  { value: 'EXPIRING', label: '即将截止' }
];

// 待去清单收藏夹 (持久化至 localStorage)
const favoriteIds = ref(JSON.parse(localStorage.getItem('nanjing_favorites') || '[]'));
const showFavoritesOnly = ref(false);

// 二级活动详情面板
const detailItem = ref(null);
const copiedAddress = ref(false);

// ECharts DOM 引用与实例
const districtChartRef = ref(null);
const categoryChartRef = ref(null);
let districtChartInstance = null;
let categoryChartInstance = null;

// 地图模式：默认 standard (高德全彩标准)
const mapStyleMode = ref('standard');

const mapModes = [
  { id: 'standard', label: '高德全彩', color: '#007AFF' },
  { id: 'satellite', label: '高清卫星', color: '#10B981' },
  { id: 'apple', label: '苹果浅灰', color: '#64748B' },
  { id: 'dark', label: '午夜深色', color: '#0F172A' }
];

let leafletMap = null;
let baseTileLayer = null;
let satelliteOverlayLayer = null;
let leafletMarkersGroup = null;
let ringsGroup = null;
let heatmapLayer = null;

const districts = [
  '玄武区', '秦淮区', '建邺区', '鼓楼区', '栖霞区',
  '雨花台区', '江宁区', '浦口区', '六合区', '溧水区', '高淳区'
];

function cleanString(str) {
  if (!str) return '';
  return String(str).replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\uFE0F]/gu, '').trim();
}

function haversineDistance(lng1, lat1, lng2, lat2) {
  const toRad = (d) => (d * Math.PI) / 180;
  const R = 6371.0;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function normalize(item) {
  const lng = Number(item.lng || 118.7842);
  const lat = Number(item.lat || 32.0418);
  const dist = item.distance_km != null
    ? Number(item.distance_km)
    : haversineDistance(XINJIEKOU[0], XINJIEKOU[1], lng, lat);

  const obsPath = item.obsidian_path || '';
  const obsUri = obsPath ? `obsidian://open?vault=IOT&file=${encodeURIComponent(obsPath)}` : '';

  const titleStr = cleanString(item.title);
  const addrStr = cleanString(item.address || item.location || '南京市内');
  const distStr = cleanString(item.district || '玄武区');

  const isOnline = distStr === '全城通用' || 
                   addrStr.includes('微信') || 
                   addrStr.includes('线上') || 
                   titleStr.includes('建行') || 
                   titleStr.includes('支付') || 
                   titleStr.includes('立减金') || 
                   titleStr.includes('月月刷');

  return {
    ...item,
    id: item.id || item.post_id,
    title: titleStr,
    category: cleanString(item.category || '南京活动'),
    district: distStr,
    address: addrStr,
    benefit: cleanString(item.benefit || '免费入场'),
    event_time_text: cleanString(item.event_time_text || item.event_time || item.publish_date || '近期有效'),
    status: cleanString(item.status || '待去/待薅'),
    summary: cleanString(item.summary || item.action_guide || ''),
    action_guide: cleanString(item.action_guide || ''),
    author: cleanString(item.author || ''),
    platform: cleanString(item.platform || ''),
    source_url: item.source_url || item.url || '',
    obsidian_path: obsPath,
    obsidian_uri: obsUri,
    is_online: isOnline,
    lng,
    lat,
    distance_km: Number(dist.toFixed(1))
  };
}

// 提取 6 字以内的精简标点名称
function getMarkerShortName(title) {
  if (!title) return '活动';
  if (title.includes('星星人')) return '星星人首展';
  if (title.includes('文房四宝')) return '文房四宝展';
  if (title.includes('糖酒会')) return '全国糖酒会';
  if (title.includes('菊花展')) return '湖熟菊花展';
  if (title.includes('夫子庙')) return '夫子庙市集';
  if (title.includes('月月刷')) return '建行月月刷';
  if (title.includes('立减金')) return '建行立减金';
  if (title.includes('双11')) return '双11支付券';
  if (title.includes('4大景区') || title.includes('长江矶石')) return '长江矶石洞';
  if (title.includes('免费开放') || title.includes('免门票')) return '全城景区免票';
  if (title.includes('全国展会')) return '全国展会排期';
  if (title.includes('江苏展会')) return '江苏展会排期';
  if (title.includes('展会排期')) return '10月展会排期';
  if (title.includes('特色活动')) return '特色活动推荐';
  
  const clean = title.replace(/[\[\]【】|()（）!！?？,，、\s]/g, '');
  return clean.slice(0, 6);
}

// 提取精简价格/免费标签
function getMarkerPriceLabel(item) {
  if (item.is_free) return '免票';
  if (item.benefit) {
    if (item.benefit.includes('免') || item.benefit.includes('免费')) return '免票';
    if (item.benefit.includes('立减') || item.benefit.includes('券')) return '福利';
    if (item.benefit.includes('0元') || item.benefit.includes('0.01')) return '羊毛';
    return item.benefit.slice(0, 2);
  }
  return '活动';
}

// 计算结构化时间状态标签 (进行中 / 本周末 / 剩X天)
function getStatusInfo(item) {
  const text = (item.event_time_text + ' ' + item.title + ' ' + item.benefit).toLowerCase();
  
  if (text.includes('10.23') || text.includes('23日') || text.includes('10.22-10.24')) {
    return {
      label: '进行中 · 剩3天',
      bg: 'bg-amber-50 text-amber-700 border-amber-200/60'
    };
  }
  if (text.includes('周末') || text.includes('10.24') || text.includes('10.25') || text.includes('24日') || text.includes('25日')) {
    return {
      label: '本周末特惠',
      bg: 'bg-amber-50 text-amber-700 border-amber-200/60'
    };
  }
  if (text.includes('10月31日') || text.includes('10.31') || text.includes('10-31') || text.includes('11月')) {
    return {
      label: '进行中 · 剩9天',
      bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/60'
    };
  }
  return {
    label: '火热进行中',
    bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/60'
  };
}

// 截止时间紧急程度评分 (用于待去清单按最近截止排序)
function getDaysRemainingScore(item) {
  const text = (item.event_time_text + ' ' + item.title).toLowerCase();
  if (text.includes('10.22') || text.includes('今日') || text.includes('剩1天')) return 1;
  if (text.includes('10.23') || text.includes('剩3天')) return 2;
  if (text.includes('周末') || text.includes('10.25')) return 3;
  if (text.includes('10.31') || text.includes('剩9天')) return 4;
  return 10;
}

const categoryOptions = [
  { value: 'ALL', label: '全部' },
  { value: '南京展会', label: '展会' },
  { value: '南京活动', label: '活动' },
  { value: '羊毛福利', label: '福利' }
];

const hasActiveFilter = computed(() => {
  return selectedDistrict.value !== 'ALL' || radiusFilter.value > 0 || freeOnly.value || timeFilter.value !== 'ALL';
});

function resetFilters() {
  selectedDistrict.value = 'ALL';
  radiusFilter.value = 0;
  freeOnly.value = false;
  timeFilter.value = 'ALL';
}

function resetAllFilters() {
  activeCategory.value = 'ALL';
  venueFilter.value = 'ALL';
  boundsFilterEnabled.value = false;
  showFavoritesOnly.value = false;
  searchQuery.value = '';
  activeZoneId.value = 'all';
  resetFilters();
}

// 待去清单收藏功能
function isFavorite(id) {
  return favoriteIds.value.includes(id);
}

function toggleFavorite(item) {
  const idx = favoriteIds.value.indexOf(item.id);
  if (idx > -1) {
    favoriteIds.value.splice(idx, 1);
  } else {
    favoriteIds.value.push(item.id);
  }
  localStorage.setItem('nanjing_favorites', JSON.stringify(favoriteIds.value));
}

// 复制场馆具体地址
function copyAddress(address) {
  if (!address) return;
  navigator.clipboard.writeText(address);
  copiedAddress.value = true;
  setTimeout(() => {
    copiedAddress.value = false;
  }, 2000);
}

// 视野联动切换
function toggleBoundsFilter() {
  boundsFilterEnabled.value = !boundsFilterEnabled.value;
  if (boundsFilterEnabled.value && leafletMap) {
    mapBounds.value = leafletMap.getBounds();
  }
}

// 核心过滤计算 (支持数据清洗去重、视野联动、待去清单时间排序)
const filteredEvents = computed(() => {
  let list = events.value.filter(it => {
    // 基础脏数据过滤
    if (!it || !it.id || !it.title || !it.title.trim()) return false;

    // 收藏夹筛选
    if (showFavoritesOnly.value && !isFavorite(it.id)) return false;
    
    // 类别筛选
    if (activeCategory.value !== 'ALL' && it.category !== activeCategory.value) return false;
    
    // 线上/线下实体筛选
    if (venueFilter.value === 'PHYSICAL' && it.is_online) return false;
    if (venueFilter.value === 'ONLINE' && !it.is_online) return false;

    // 视野联动筛选 (只对线下实体生效，全城羊毛不受视野限制)
    if (boundsFilterEnabled.value && !it.is_online && mapBounds.value && venueFilter.value !== 'ONLINE') {
      if (!mapBounds.value.contains([it.lat, it.lng])) {
        return false;
      }
    }

    // 时间维度筛选
    if (timeFilter.value !== 'ALL') {
      const statusText = getStatusInfo(it).label;
      if (timeFilter.value === 'TODAY' && !statusText.includes('进行中')) return false;
      if (timeFilter.value === 'WEEKEND' && !statusText.includes('周末')) return false;
      if (timeFilter.value === 'EXPIRING' && !statusText.includes('剩')) return false;
    }

    // 行政区与空间半径
    if (selectedDistrict.value !== 'ALL' && it.district !== selectedDistrict.value) return false;
    if (freeOnly.value && !it.is_free) return false;
    if (radiusFilter.value > 0 && it.distance_km > radiusFilter.value) return false;

    // 搜索关键词
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase();
      const hay = [it.title, it.category, it.district, it.address, it.benefit, it.summary].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }

    return true;
  });

  // 去重清洗：防止同名活动重合堆叠 (例如重复的万象天地星星人)
  const seen = new Set();
  const uniqueList = [];
  for (const it of list) {
    const shortName = getMarkerShortName(it.title);
    const key = `${shortName}_${it.district}_${Math.round(it.lat * 100)}`;
    if (!seen.has(key)) {
      seen.add(key);
      uniqueList.push(it);
    }
  }

  // 排序规则：若在待去清单模式，按“距离截止最近”排；普通模式按距离新街口排
  if (showFavoritesOnly.value) {
    return uniqueList.sort((a, b) => getDaysRemainingScore(a) - getDaysRemainingScore(b));
  }
  return uniqueList.sort((a, b) => a.distance_km - b.distance_km);
});

// 计算时间分布统计数据
const timeStats = computed(() => {
  let ongoing = 0;
  let expiring = 0;
  let upcoming = 0;
  const total = filteredEvents.value.length || 1;

  filteredEvents.value.forEach(it => {
    const status = getStatusInfo(it).label;
    if (status.includes('剩3天') || status.includes('本周末')) {
      expiring++;
    } else if (status.includes('剩9天') || status.includes('进行中') || status.includes('火热')) {
      ongoing++;
    } else {
      upcoming++;
    }
  });

  return {
    ongoing,
    expiring,
    upcoming,
    ongoingPercent: Math.round((ongoing / total) * 100),
    expiringPercent: Math.round((expiring / total) * 100),
    upcomingPercent: Math.round((upcoming / total) * 100)
  };
});

function getMarkerDotColor(category) {
  if (category === '南京展会') return '#FF9500';
  if (category === '羊毛福利') return '#34C759';
  return '#007AFF';
}

function getCategoryBadgeClass(category) {
  if (category === '南京展会') return 'bg-amber-500/10 text-amber-700';
  if (category === '羊毛福利') return 'bg-emerald-500/10 text-emerald-700';
  return 'bg-blue-500/10 text-blue-700';
}

// 初始化高德官方底图
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

  // 监听视野移动与缩放以驱动视野联动
  const handleMapMove = () => {
    if (boundsFilterEnabled.value && leafletMap) {
      mapBounds.value = leafletMap.getBounds();
    }
  };
  leafletMap.on('moveend', handleMapMove);
  leafletMap.on('zoomend', handleMapMove);

  syncMarkers();
}

function setMapMode(modeId) {
  mapStyleMode.value = modeId;
  applyMapLayer();
}

function applyMapLayer() {
  if (!leafletMap) return;

  if (baseTileLayer) leafletMap.removeLayer(baseTileLayer);
  if (satelliteOverlayLayer) leafletMap.removeLayer(satelliteOverlayLayer);

  if (mapStyleMode.value === 'satellite') {
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
    baseTileLayer = L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
      subdomains: ['1', '2', '3', '4'],
      maxZoom: 18,
      minZoom: 9
    }).addTo(leafletMap);
  }
}

// 辐射圈功能
function toggleRings() {
  showRings.value = !showRings.value;
  if (!ringsGroup) return;
  ringsGroup.clearLayers();

  if (showRings.value) {
    const center = [XINJIEKOU[1], XINJIEKOU[0]];
    L.circle(center, {
      radius: 3000,
      color: '#007AFF',
      weight: 1.5,
      dashArray: '4 4',
      fillOpacity: 0.04
    }).bindTooltip("3km 核心商圈", { permanent: false, direction: 'top' }).addTo(ringsGroup);

    L.circle(center, {
      radius: 5000,
      color: '#10B981',
      weight: 1.5,
      dashArray: '6 6',
      fillOpacity: 0.03
    }).bindTooltip("5km 主城圈", { permanent: false, direction: 'top' }).addTo(ringsGroup);

    L.circle(center, {
      radius: 10000,
      color: '#F59E0B',
      weight: 1.5,
      dashArray: '8 8',
      fillOpacity: 0.02
    }).bindTooltip("10km 绕城圈", { permanent: false, direction: 'top' }).addTo(ringsGroup);
  }
}

// 🔥 热力图功能 (leaflet.heat)
async function toggleHeatmap() {
  showHeatmap.value = !showHeatmap.value;
  if (!leafletMap) return;

  if (heatmapLayer) {
    leafletMap.removeLayer(heatmapLayer);
    heatmapLayer = null;
  }

  if (showHeatmap.value) {
    try {
      window.L = L;
      await import('leaflet.heat');
      const heatPoints = filteredEvents.value.map(it => [it.lat, it.lng, 0.85]);
      heatmapLayer = L.heatLayer(heatPoints, {
        radius: 38,
        blur: 24,
        maxZoom: 15,
        gradient: {
          0.2: '#007AFF',
          0.4: '#10B981',
          0.7: '#FF9500',
          1.0: '#FF3B30'
        }
      }).addTo(leafletMap);
    } catch (e) {
      console.error('Heatmap load error:', e);
    }
  }
}

function recenterMap() {
  activeZoneId.value = 'all';
  if (leafletMap) {
    leafletMap.flyTo([XINJIEKOU[1], XINJIEKOU[0]], 12, {
      duration: 0.8,
      easeLinearity: 0.25
    });
  }
}

// 南京核心片区瞬移
function teleportToZone(zone) {
  activeZoneId.value = zone.id;
  if (leafletMap) {
    leafletMap.flyTo([zone.center[1], zone.center[0]], zone.zoom, {
      duration: 0.85,
      easeLinearity: 0.25
    });
  }
}

function onDistrictChange() {
  if (selectedDistrict.value in DISTRICT_CENTERS && leafletMap) {
    const center = DISTRICT_CENTERS[selectedDistrict.value];
    leafletMap.flyTo([center[1], center[0]], 13, {
      duration: 0.9,
      easeLinearity: 0.25
    });
  }
}

// 渲染地图胶囊标点 (彻底移除 Popup 双影覆盖，选中时高亮自身，待去清单下仅显示收藏标点)
function syncMarkers() {
  if (!leafletMap || !leafletMarkersGroup) return;
  leafletMarkersGroup.clearLayers();

  filteredEvents.value.forEach(item => {
    const dotColor = getMarkerDotColor(item.category);
    const shortName = getMarkerShortName(item.title);
    const priceTag = getMarkerPriceLabel(item);
    const isActive = activeEventId.value === item.id;

    // 选中时 Marker 自身直接转为纯苹果蓝白字高亮态，绝无白黑重叠双影
    const iconHtml = `
      <div class="airbnb-marker ${isActive ? 'active' : ''}" id="leaf-marker-${item.id}">
        <div class="marker-pill inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full cursor-pointer whitespace-nowrap shadow-md ${isActive ? 'bg-[#007AFF] text-white ring-2 ring-white/90 scale-110 z-50' : 'bg-white/95 text-slate-800'}">
          <span class="marker-dot w-2 h-2 rounded-full shrink-0" style="background-color: ${isActive ? '#ffffff' : dotColor}"></span>
          <span class="font-semibold text-xs tracking-tight shrink-0 marker-title ${isActive ? 'text-white' : 'text-slate-900'}">${shortName}</span>
          <span class="text-[10px] shrink-0 ${isActive ? 'text-white/40' : 'text-slate-300'}">|</span>
          <span class="text-[11px] font-bold shrink-0 marker-tag ${isActive ? 'text-white' : (item.is_free ? 'text-[#34C759]' : 'text-slate-600')}">${priceTag}</span>
        </div>
      </div>
    `;

    const customIcon = L.divIcon({
      html: iconHtml,
      className: 'bg-transparent border-0',
      iconSize: [0, 0],
      iconAnchor: [0, 0]
    });

    const marker = L.marker([item.lat, item.lng], { icon: customIcon });

    // 点击标点直接定位高亮并滑出详情，绝不额外弹窗覆盖
    marker.on('click', () => {
      openDetail(item);
    });

    marker.addTo(leafletMarkersGroup);
  });
}

// 聚焦标点 (右侧卡片【📍 定位】触发)
function focusEvent(item) {
  activeEventId.value = item.id;
  if (leafletMap) {
    leafletMap.flyTo([item.lat, item.lng], 15, {
      duration: 0.8,
      easeLinearity: 0.25
    });
  }
  syncMarkers();
}

// 打开二级完整详情
function openDetail(item) {
  activeEventId.value = item.id;
  detailItem.value = item;
  if (leafletMap) {
    leafletMap.flyTo([item.lat, item.lng], 15, {
      duration: 0.8,
      easeLinearity: 0.25
    });
  }
  syncMarkers();
  scrollToCard(item.id);
}

function closeDetail() {
  detailItem.value = null;
}

function scrollToCard(itemId) {
  const el = document.getElementById('card-' + itemId);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

// 打开数据统计可视化模态框 (ECharts Bento 布局)
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

function initCharts() {
  if (!districtChartRef.value || !categoryChartRef.value) return;

  // 1. 各行政区数据统计
  const districtCounts = {};
  districts.forEach(d => { districtCounts[d] = 0; });
  filteredEvents.value.forEach(it => {
    if (districtCounts[it.district] !== undefined) {
      districtCounts[it.district]++;
    }
  });

  const distNames = Object.keys(districtCounts);
  const distValues = Object.values(districtCounts);

  if (districtChartInstance) districtChartInstance.dispose();
  districtChartInstance = echarts.init(districtChartRef.value);
  districtChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'rgba(0, 0, 0, 0.05)',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 12 },
      extraCssText: 'box-shadow: 0 8px 24px rgba(0,0,0,0.12); border-radius: 12px;'
    },
    grid: { top: 20, right: 15, bottom: 25, left: 35 },
    xAxis: {
      type: 'category',
      data: distNames.map(d => d.replace('区', '')),
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
      axisTick: { show: false },
      axisLabel: { color: '#64748b', fontSize: 10, interval: 0 }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.04)', type: 'dashed' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 }
    },
    series: [{
      type: 'bar',
      data: distValues,
      barWidth: 14,
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#007AFF' },
          { offset: 1, color: '#5AC8FA' }
        ])
      }
    }]
  });

  // 2. 活动类型占比环形图
  const catCounts = { '南京展会': 0, '南京活动': 0, '羊毛福利': 0 };
  filteredEvents.value.forEach(it => {
    if (catCounts[it.category] !== undefined) {
      catCounts[it.category]++;
    }
  });

  if (categoryChartInstance) categoryChartInstance.dispose();
  categoryChartInstance = echarts.init(categoryChartRef.value);
  categoryChartInstance.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'rgba(0, 0, 0, 0.05)',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 12 },
      formatter: '{b}: {c} 场 ({d}%)',
      extraCssText: 'box-shadow: 0 8px 24px rgba(0,0,0,0.12); border-radius: 12px;'
    },
    legend: {
      bottom: 0,
      icon: 'circle',
      textStyle: { color: '#64748b', fontSize: 11 }
    },
    series: [{
      type: 'pie',
      radius: ['45%', '72%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#ffffff',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold',
          color: '#0f172a'
        }
      },
      data: [
        { value: catCounts['南京展会'] || 0, name: '南京展会', itemStyle: { color: '#FF9500' } },
        { value: catCounts['南京活动'] || 0, name: '南京活动', itemStyle: { color: '#007AFF' } },
        { value: catCounts['羊毛福利'] || 0, name: '羊毛福利', itemStyle: { color: '#34C759' } }
      ]
    }]
  });
}

function handleResize() {
  if (districtChartInstance) districtChartInstance.resize();
  if (categoryChartInstance) categoryChartInstance.resize();
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
        events.value = data.items.map(normalize);
        syncMarkers();
      }
    }
  } catch (e) {}
  isSyncing.value = false;
}

async function loadData() {
  try {
    const res = await fetch('/api/events');
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.items) && data.items.length) {
        events.value = data.items.map(normalize);
        nextTick(() => { syncMarkers(); });
        return;
      }
    }
  } catch (e) {}
}

watch(filteredEvents, () => {
  syncMarkers();
  if (showHeatmap.value && heatmapLayer) {
    const heatPoints = filteredEvents.value.map(it => [it.lat, it.lng, 0.85]);
    heatmapLayer.setLatLngs(heatPoints);
  }
});

// 支持按 ESC 关闭所有模态框
function handleKeyDown(e) {
  if (e.key === 'Escape') {
    if (detailItem.value) closeDetail();
    if (showStatsModal.value) closeStatsModal();
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
  window.addEventListener('resize', handleResize);
  loadData();
  nextTick(() => {
    initMap();
  });
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown);
  window.removeEventListener('resize', handleResize);
  if (districtChartInstance) districtChartInstance.dispose();
  if (categoryChartInstance) categoryChartInstance.dispose();
});
</script>

<style>
/* 高德官方底图 Apple Whitesmoke 极简滤镜调色 */
.amap-apple-filter .leaflet-tile {
  filter: grayscale(88%) brightness(103%) contrast(92%) !important;
}

/* 高德官方底图 Midnight 午夜深色滤镜调色 */
.amap-dark-filter .leaflet-tile {
  filter: invert(100%) hue-rotate(180deg) brightness(88%) contrast(95%) !important;
}

/* Airbnb 升级版打点胶囊与物理弹簧动画 */
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
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.airbnb-marker:hover {
  transform: translate(-50%, -108%) scale(1.08);
  z-index: 50 !important;
}

.airbnb-marker:hover .marker-pill {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18), 0 2px 6px rgba(0, 0, 0, 0.08);
  border-color: rgba(0, 122, 255, 0.3);
}

/* 激活选中态：纯苹果蓝高亮药丸 (彻底杜绝双影) */
.airbnb-marker.active {
  transform: translate(-50%, -114%) scale(1.15);
  z-index: 60 !important;
}

.airbnb-marker.active .marker-pill {
  background-color: #007AFF !important;
  color: #ffffff !important;
  border-color: #007AFF !important;
  box-shadow: 0 14px 32px rgba(0, 122, 255, 0.4), 0 4px 10px rgba(0, 122, 255, 0.2) !important;
}

.airbnb-marker.active .marker-title,
.airbnb-marker.active .marker-tag {
  color: #ffffff !important;
}
</style>
