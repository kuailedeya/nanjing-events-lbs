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

    <!-- 2. 顶部：悬浮于地图左上方的通透圆角浮动岛屿 (Floating Island) -->
    <header class="absolute top-6 left-6 z-20 pointer-events-auto max-w-[820px] transition-all">
      <div class="bg-white/85 backdrop-blur-2xl backdrop-saturate-150 rounded-[24px] shadow-[0_20px_50px_rgba(0,0,0,0.08),0_1px_3px_rgba(0,0,0,0.03)] border border-white/80 p-2 sm:p-2.5 flex items-center gap-2 transition-all flex-wrap">
        
        <!-- Airbnb 风格搜索框 -->
        <div class="relative flex items-center min-w-[190px] flex-1">
          <Search class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索南京活动、展会、地标或场馆..."
            class="w-full pl-9 pr-7 py-2 bg-black/[0.04] focus:bg-white rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 outline-none border border-transparent focus:border-black/[0.08] focus:ring-4 focus:ring-[#007AFF]/12 transition-all duration-200"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="absolute right-2.5 text-slate-400 hover:text-slate-600 p-1 cursor-pointer transition-colors"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- 分类滑动胶囊分段器 (全部 / 展会 / 活动 / 福利) -->
        <div class="flex items-center p-1 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600 shrink-0">
          <button
            v-for="cat in categoryOptions"
            :key="cat.value"
            @click="activeCategory = cat.value"
            :class="[
              'px-3 py-1 rounded-lg transition-all duration-200 text-xs cursor-pointer',
              activeCategory === cat.value
                ? 'bg-white text-slate-900 shadow-[0_2px_6px_rgba(0,0,0,0.1),0_1px_2px_rgba(0,0,0,0.06)] font-semibold'
                : 'text-slate-500 hover:text-slate-900'
            ]"
          >
            {{ cat.label }}
          </button>
        </div>

        <!-- 线上/线下区分胶囊切换器 (解决线上活动堆积新街口问题) -->
        <div class="flex items-center p-1 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600 shrink-0">
          <button
            @click="venueFilter = 'ALL'"
            :class="[
              'px-2.5 py-1 rounded-lg transition-all text-xs cursor-pointer',
              venueFilter === 'ALL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="全部活动与福利"
          >
            全览
          </button>
          <button
            @click="venueFilter = 'PHYSICAL'"
            :class="[
              'px-2.5 py-1 rounded-lg transition-all text-xs cursor-pointer flex items-center gap-1',
              venueFilter === 'PHYSICAL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="仅看有明确物理场馆的线下活动"
          >
            <Building2 class="w-3 h-3 text-[#007AFF]" />
            <span>线下实体</span>
          </button>
          <button
            @click="venueFilter = 'ONLINE'"
            :class="[
              'px-2.5 py-1 rounded-lg transition-all text-xs cursor-pointer flex items-center gap-1',
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
            'px-3 py-1.5 rounded-xl transition-all cursor-pointer flex items-center gap-1.5 text-xs font-medium shrink-0',
            showFavoritesOnly
              ? 'bg-amber-500 text-white shadow-sm font-semibold'
              : 'bg-black/[0.04] text-slate-700 hover:bg-black/[0.07]'
          ]"
          title="仅显示加入待去清单的活动"
        >
          <Star class="w-3.5 h-3.5" :class="showFavoritesOnly ? 'fill-white text-white' : 'text-amber-500 fill-amber-500'" />
          <span>待去清单</span>
          <span class="text-[11px] tabular-nums font-bold opacity-90">({{ favoriteIds.length }})</span>
        </button>

        <!-- 极简高级筛选按钮 -->
        <button
          @click="showFilterPopover = !showFilterPopover"
          :class="[
            'p-2 rounded-xl transition-all cursor-pointer relative shrink-0',
            hasActiveFilter 
              ? 'bg-slate-900 text-white shadow-sm' 
              : 'text-slate-600 hover:bg-black/[0.04]'
          ]"
          title="筛选范围与时间维度"
        >
          <SlidersHorizontal class="w-4 h-4" />
          <span v-if="hasActiveFilter" class="w-1.5 h-1.5 rounded-full bg-[#34C759] absolute top-1.5 right-1.5"></span>
        </button>

        <!-- 增量同步按钮 -->
        <button
          @click="triggerSync"
          :disabled="isSyncing"
          class="p-2 rounded-xl text-slate-600 hover:bg-black/[0.04] transition-all cursor-pointer shrink-0"
          title="增量同步最新社媒情报"
        >
          <RefreshCw :class="['w-4 h-4', isSyncing ? 'animate-spin text-[#007AFF]' : '']" />
        </button>

      </div>

      <!-- 下拉微质感 Popover 筛选器 (含时间维度与区域微调) -->
      <div
        v-if="showFilterPopover"
        class="mt-2.5 p-3.5 bg-white/90 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.12)] border border-white/80 flex items-center gap-3 text-xs animate-in fade-in slide-in-from-top-2 duration-200 flex-wrap"
      >
        <!-- 时间维度筛选 (全部时间 / 今日 / 本周末 / 即将截止) -->
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
          <select
            v-model="selectedDistrict"
            @change="onDistrictChange"
            class="bg-transparent border-0 outline-none font-medium cursor-pointer text-slate-800 text-xs"
          >
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

        <!-- 仅看免票 -->
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

    <!-- 3. 左下角：macOS Sonoma 悬浮 Dock 控制台 (含4模切换、辐射圈与🔥热力图) -->
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
        
        <!-- 抽屉头部 (Mac 风格标题栏与展开/折叠) -->
        <div class="px-5 pt-4 pb-2.5 flex items-center justify-between border-b border-black/[0.04]">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold text-slate-900 tracking-tight">南京精选探索</h2>
            <span class="text-xs font-semibold text-slate-400 tabular-nums">({{ filteredEvents.length }})</span>
            <span v-if="showFavoritesOnly" class="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-full font-semibold">收藏视图</span>
          </div>

          <button
            @click="drawerOpen = !drawerOpen"
            class="w-7 h-7 rounded-lg bg-white/70 hover:bg-white text-slate-500 hover:text-slate-900 flex items-center justify-center transition shadow-sm cursor-pointer"
            :title="drawerOpen ? '收起抽屉' : '展开抽屉'"
          >
            <ChevronRight :class="['w-4 h-4 transition-transform duration-200', drawerOpen ? 'rotate-0' : 'rotate-180']" />
          </button>
        </div>

        <!-- 南京核心片区瞬移胶囊栏 (全城 / 新街口 / 老门东 / 河西 / 仙林 / 江宁) -->
        <div class="px-4 py-2 border-b border-black/[0.03] bg-black/[0.015] flex items-center gap-1.5 overflow-x-auto no-scrollbar shrink-0">
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

        <!-- Bento Grid 活动卡片瀑布流 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar" id="cards-container">
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

              <!-- 悬浮在封面右下方的线上/线下属性 -->
              <span class="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded-lg text-[10px] font-medium tracking-tight backdrop-blur-md bg-black/40 text-white flex items-center gap-1">
                <Building2 class="w-3 h-3" v-if="!item.is_online" />
                <Globe class="w-3 h-3 text-emerald-400" v-else />
                <span>{{ item.is_online ? '线上/全城' : '线下场馆' }}</span>
              </span>
            </div>

            <!-- 结构化时间状态标签 (进行中 / 本周末 / 剩X天) -->
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

            <!-- 操作底栏：状态核销 + 收藏 + 导航 + 详情按钮 -->
            <div class="pt-2.5 border-t border-black/[0.04] flex items-center justify-between mt-auto" @click.stop>
              <!-- 收藏按钮 (加入待去清单) -->
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
                <span>{{ isFavorite(item.id) ? '已待去' : '待去' }}</span>
              </button>

              <div class="flex items-center gap-2">
                <!-- 高德原生路线规划导航 -->
                <a
                  :href="getAmapNaviUrl(item)"
                  target="_blank"
                  @click.stop
                  class="text-slate-500 hover:text-[#007AFF] text-[11px] font-medium flex items-center gap-1 py-1 px-2 hover:bg-black/[0.04] rounded-lg transition-colors"
                  title="调用高德地图进行真实路线规划导航"
                >
                  <Navigation2 class="w-3 h-3 text-slate-400 group-hover:text-[#007AFF]" />
                  <span>导航</span>
                </a>

                <!-- 查看详情入口 -->
                <button
                  @click.stop="openDetail(item)"
                  class="text-[11px] text-[#007AFF] hover:text-[#0051a8] font-semibold flex items-center gap-0.5 py-1 px-2 hover:bg-[#007AFF]/10 rounded-lg transition-colors cursor-pointer"
                  title="展开完整活动图文与规则详情"
                >
                  <span>详情</span>
                  <ChevronRight class="w-3 h-3" />
                </button>
              </div>
            </div>

          </div>

          <!-- 空状态 -->
          <div v-if="filteredEvents.length === 0" class="py-20 text-center text-xs text-slate-400 space-y-2">
            <div class="text-sm text-slate-500 font-medium">暂无匹配的同城活动</div>
            <div v-if="showFavoritesOnly">待去清单为空，可以在卡片上点击“★ 待去”添加收藏</div>
            <button
              v-if="hasActiveFilter || showFavoritesOnly || venueFilter !== 'ALL' || timeFilter !== 'ALL'"
              @click="resetAllFilters"
              class="text-[#007AFF] hover:underline cursor-pointer"
            >
              清空所有过滤条件
            </button>
          </div>
        </div>

      </div>
    </aside>

    <!-- 5. 二级详情模态框/抽屉 (Activity Detail Sheet) -->
    <div
      v-if="detailItem"
      class="fixed inset-0 z-40 bg-black/25 backdrop-blur-xs flex justify-end transition-opacity duration-300"
      @click.self="closeDetail"
    >
      <div
        class="w-[420px] md:w-[480px] h-full bg-white/95 backdrop-blur-3xl shadow-[0_25px_70px_rgba(0,0,0,0.2)] border-l border-white/80 flex flex-col overflow-hidden animate-in slide-in-from-right duration-300"
      >
        <!-- 详情面板顶部标题栏 -->
        <div class="px-6 py-4 flex items-center justify-between border-b border-black/[0.06] bg-white/80 backdrop-blur-md">
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
            
            <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between text-white">
              <span class="px-2.5 py-1 rounded-lg backdrop-blur-md bg-white/20 text-xs font-medium">
                {{ detailItem.is_free ? '免票直入' : detailItem.benefit }}
              </span>
              <span class="px-2.5 py-1 rounded-lg backdrop-blur-md bg-black/40 text-xs font-medium tabular-nums">
                距新街口 {{ detailItem.distance_km }} km
              </span>
            </div>
          </div>

          <!-- 完整标题 -->
          <h2 class="text-lg font-bold text-slate-900 leading-snug tracking-tight">
            {{ detailItem.title }}
          </h2>

          <!-- 核心属性卡片 -->
          <div class="bg-black/[0.025] rounded-2xl p-4 space-y-2.5 border border-black/[0.04] text-xs">
            <div class="flex items-start gap-2.5 text-slate-700">
              <MapPin class="w-4 h-4 text-[#007AFF] shrink-0 mt-0.5" />
              <div>
                <div class="font-semibold text-slate-900">{{ detailItem.address }}</div>
                <div class="text-slate-400 text-[11px]">行政归属: {{ detailItem.district }} · {{ detailItem.is_online ? '线上无物理实体' : '线下实体场馆' }}</div>
              </div>
            </div>

            <div class="h-px bg-black/[0.04]"></div>

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
              <p class="whitespace-pre-line">{{ detailItem.summary || '暂无详细介绍文本，请点击底部导航前往现场或查看原帖情报。' }}</p>
              <div v-if="detailItem.action_guide" class="mt-3 p-3 bg-emerald-50/70 border border-emerald-100 rounded-lg text-emerald-900 text-[11px]">
                <div class="font-bold mb-1">💡 打卡/羊毛攻略指南:</div>
                <div>{{ detailItem.action_guide }}</div>
              </div>
            </div>
          </div>

          <!-- 知识库双向关联信息 -->
          <div v-if="detailItem.obsidian_path" class="text-[11px] text-slate-400 flex items-center gap-1.5">
            <FileText class="w-3.5 h-3.5 text-slate-400" />
            <span>本地知识库双向文档: {{ detailItem.obsidian_path }}</span>
          </div>

        </div>

        <!-- 底部大按钮操作区 (3个高质感 Apple 操作按钮) -->
        <div class="p-5 border-t border-black/[0.06] bg-white/90 backdrop-blur-md flex items-center gap-2.5">
          <!-- 1. 待去清单切换按钮 -->
          <button
            @click="toggleFavorite(detailItem)"
            :class="[
              'flex-1 py-3 px-3 rounded-2xl font-semibold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-sm',
              isFavorite(detailItem.id)
                ? 'bg-amber-500 text-white hover:bg-amber-600'
                : 'bg-black/[0.05] hover:bg-black/[0.08] text-slate-800'
            ]"
          >
            <Star class="w-4 h-4" :class="isFavorite(detailItem.id) ? 'fill-white text-white' : 'text-slate-600'" />
            <span>{{ isFavorite(detailItem.id) ? '已在待去清单' : '加入待去清单' }}</span>
          </button>

          <!-- 2. 高德路线导航按钮 -->
          <a
            :href="getAmapNaviUrl(detailItem)"
            target="_blank"
            class="flex-1 py-3 px-3 rounded-2xl font-semibold text-xs bg-[#007AFF] hover:bg-[#0062cc] text-white flex items-center justify-center gap-1.5 transition-all shadow-sm shadow-[#007AFF]/25 cursor-pointer"
          >
            <Navigation class="w-4 h-4" />
            <span>高德导航 ↗</span>
          </a>

          <!-- 3. 打开原帖或 Obsidian 笔记按钮 -->
          <a
            :href="detailItem.obsidian_uri"
            target="_blank"
            class="py-3 px-3.5 rounded-2xl font-semibold text-xs bg-slate-900 hover:bg-black text-white flex items-center justify-center gap-1.5 transition-all shadow-sm cursor-pointer"
            title="在 Obsidian 中打开"
          >
            <FileText class="w-4 h-4" />
            <span>笔记</span>
          </a>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue';
import L from 'leaflet';
import {
  Search, SlidersHorizontal, RefreshCw,
  ChevronRight, ExternalLink, MapPin, Navigation,
  Navigation2, X, CircleDot, LocateFixed, Clock,
  Compass, FileText, Star, Flame, Calendar, Building2,
  Globe, Sparkles
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

// 新增：线上/线下区分筛选 ('ALL' | 'PHYSICAL' | 'ONLINE')
const venueFilter = ref('ALL');

// 新增：时间维度筛选 ('ALL' | 'TODAY' | 'WEEKEND' | 'EXPIRING')
const timeFilter = ref('ALL');
const timeFilterOptions = [
  { value: 'ALL', label: '全部时间' },
  { value: 'TODAY', label: '今日' },
  { value: 'WEEKEND', label: '本周末' },
  { value: 'EXPIRING', label: '即将截止' }
];

// 新增：待去清单收藏夹 (localStorage)
const favoriteIds = ref(JSON.parse(localStorage.getItem('nanjing_favorites') || '[]'));
const showFavoritesOnly = ref(false);

// 新增：二级活动详情面板
const detailItem = ref(null);

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
  const obsUri = obsPath ? `obsidian://open?vault=IOT&file=${encodeURIComponent(obsPath)}` : '#';

  const titleStr = cleanString(item.title);
  const addrStr = cleanString(item.address || item.location || '南京市内');
  const distStr = cleanString(item.district || '玄武区');

  // 判断是否为线上/全城通用活动
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
  showFavoritesOnly.value = false;
  searchQuery.value = '';
  activeZoneId.value = 'all';
  resetFilters();
}

function getAmapNaviUrl(item) {
  return `https://uri.amap.com/marker?position=${item.lng},${item.lat}&name=${encodeURIComponent(item.title)}&coordinate=gaode`;
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

// 核心过滤计算
const filteredEvents = computed(() => {
  return events.value.filter(it => {
    // 收藏夹筛选
    if (showFavoritesOnly.value && !isFavorite(it.id)) return false;
    
    // 类别筛选
    if (activeCategory.value !== 'ALL' && it.category !== activeCategory.value) return false;
    
    // 线上/线下筛选
    if (venueFilter.value === 'PHYSICAL' && it.is_online) return false;
    if (venueFilter.value === 'ONLINE' && !it.is_online) return false;

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
  }).sort((a, b) => a.distance_km - b.distance_km);
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

function getStatusClass(status) {
  if (status === '已完成') return 'bg-emerald-50 text-emerald-800 border border-emerald-200/50';
  if (status === '已过期') return 'bg-rose-50 text-rose-800 border border-rose-200/50';
  return 'bg-slate-100 text-slate-700 border border-black/[0.04]';
}

function getStatusDotClass(status) {
  if (status === '已完成') return 'bg-[#34C759]';
  if (status === '已过期') return 'bg-[#FF3B30]';
  return 'bg-slate-400';
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

// 渲染升级后的精细胶囊标点 (彩色圆点 + 6字活动名 + 价格/免票标签)
function syncMarkers() {
  if (!leafletMap || !leafletMarkersGroup) return;
  leafletMarkersGroup.clearLayers();

  filteredEvents.value.forEach(item => {
    const dotColor = getMarkerDotColor(item.category);
    const shortName = getMarkerShortName(item.title);
    const priceTag = getMarkerPriceLabel(item);
    const isActive = activeEventId.value === item.id;

    const iconHtml = `
      <div class="airbnb-marker ${isActive ? 'active' : ''}" id="leaf-marker-${item.id}">
        <div class="marker-pill inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full cursor-pointer whitespace-nowrap shadow-md">
          <span class="marker-dot w-2 h-2 rounded-full shrink-0" style="background-color: ${isActive ? '#ffffff' : dotColor}"></span>
          <span class="font-semibold text-xs tracking-tight shrink-0 marker-title">${shortName}</span>
          <span class="text-[10px] opacity-40 shrink-0">|</span>
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

    marker.on('click', () => {
      openDetail(item);
    });

    marker.addTo(leafletMarkersGroup);
  });
}

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

// 支持按 ESC 关闭详情面板
function handleKeyDown(e) {
  if (e.key === 'Escape' && detailItem.value) {
    closeDetail();
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
  loadData();
  nextTick(() => {
    initMap();
  });
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

/* 激活选中态：Airbnb 纯黑高亮药丸 (全息反白) */
.airbnb-marker.active {
  transform: translate(-50%, -114%) scale(1.15);
  z-index: 60 !important;
}

.airbnb-marker.active .marker-pill {
  background-color: #0f172a !important;
  color: #ffffff !important;
  border-color: #0f172a !important;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.38), 0 4px 10px rgba(15, 23, 42, 0.2) !important;
}

.airbnb-marker.active .marker-tag {
  color: #ffffff !important;
}
</style>
