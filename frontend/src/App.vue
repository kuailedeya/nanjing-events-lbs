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

    <!-- 2. 顶部：通透圆角浮动岛屿 (Floating Island Suspended in Upper-Left) -->
    <header class="absolute top-6 left-6 z-20 pointer-events-auto max-w-[660px]">
      <div class="bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.08),0_1px_3px_rgba(0,0,0,0.03)] border border-white/80 p-2 sm:p-2.5 flex items-center gap-2.5 transition-all">
        
        <!-- Airbnb 风格搜索框 -->
        <div class="flex-1 relative flex items-center min-w-[200px]">
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

        <!-- macOS Sonoma 风格滑动胶囊分段器 (Segmented Pills) -->
        <div class="flex items-center p-1 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600 shrink-0">
          <button
            v-for="cat in categoryOptions"
            :key="cat.value"
            @click="activeCategory = cat.value"
            :class="[
              'px-3.5 py-1 rounded-lg transition-all duration-200 text-xs cursor-pointer',
              activeCategory === cat.value
                ? 'bg-white text-slate-900 shadow-[0_2px_6px_rgba(0,0,0,0.1),0_1px_2px_rgba(0,0,0,0.06)] font-semibold'
                : 'text-slate-500 hover:text-slate-900'
            ]"
          >
            {{ cat.label }}
          </button>
        </div>

        <!-- 极简筛选抽屉按钮 (带有高亮状态) -->
        <button
          @click="showFilterPopover = !showFilterPopover"
          :class="[
            'p-2 rounded-xl transition-all cursor-pointer relative',
            hasActiveFilter 
              ? 'bg-slate-900 text-white shadow-sm' 
              : 'text-slate-600 hover:bg-black/[0.04]'
          ]"
          title="筛选范围与行政区"
        >
          <SlidersHorizontal class="w-4 h-4" />
          <span v-if="hasActiveFilter" class="w-1.5 h-1.5 rounded-full bg-[#34C759] absolute top-1.5 right-1.5"></span>
        </button>

        <!-- 增量同步按钮 -->
        <button
          @click="triggerSync"
          :disabled="isSyncing"
          class="p-2 rounded-xl text-slate-600 hover:bg-black/[0.04] transition-all cursor-pointer"
          title="增量同步最新社媒情报"
        >
          <RefreshCw :class="['w-4 h-4', isSyncing ? 'animate-spin text-[#007AFF]' : '']" />
        </button>

      </div>

      <!-- 下拉微质感 Popover 筛选器 -->
      <div
        v-if="showFilterPopover"
        class="mt-2.5 p-3.5 bg-white/85 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-white/80 flex items-center gap-3 text-xs animate-in fade-in slide-in-from-top-2 duration-200"
      >
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
    </header>

    <!-- 3. 左下角：macOS Sonoma 悬浮 Dock 控制台 (Gaode Map Studio Dock) -->
    <div class="absolute bottom-6 left-6 z-20 flex items-center gap-2 pointer-events-auto">
      
      <!-- 地图模式切换胶囊 (全彩 / 卫星 / 浅灰 / 午夜) -->
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
        
        <!-- 抽屉头部 (Mac 风格标题栏) -->
        <div class="px-5 pt-4 pb-3 flex items-center justify-between border-b border-black/[0.04]">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold text-slate-900 tracking-tight">南京精选探索</h2>
            <span class="text-xs font-semibold text-slate-400 tabular-nums">({{ filteredEvents.length }})</span>
          </div>

          <button
            @click="drawerOpen = !drawerOpen"
            class="w-7 h-7 rounded-lg bg-white/70 hover:bg-white text-slate-500 hover:text-slate-900 flex items-center justify-center transition shadow-sm cursor-pointer"
            :title="drawerOpen ? '收起抽屉' : '展开抽屉'"
          >
            <ChevronRight :class="['w-4 h-4 transition-transform duration-200', drawerOpen ? 'rotate-0' : 'rotate-180']" />
          </button>
        </div>

        <!-- Bento Grid 活动卡片瀑布流 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar" id="cards-container">
          <div
            v-for="item in filteredEvents"
            :key="item.id"
            :id="'card-' + item.id"
            @click="focusEvent(item)"
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
              <div class="absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-black/10"></div>
              
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
            </div>

            <!-- 主标题 (严格 font-semibold text-slate-900，潮流探索排版) -->
            <h3 class="text-sm font-semibold text-slate-900 leading-snug tracking-[-0.01em] group-hover:text-[#007AFF] transition-colors mb-2 line-clamp-2">
              {{ item.title }}
            </h3>

            <!-- 地理与时间元数据行 -->
            <div class="text-xs text-slate-500 space-y-1 mb-3">
              <div class="flex items-center gap-1.5 text-slate-600">
                <MapPin class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span class="truncate font-medium text-slate-800">{{ item.address }}</span>
                <span class="text-slate-300">·</span>
                <span class="shrink-0 text-slate-500 bg-black/[0.03] px-1.5 py-0.5 rounded text-[11px]">{{ item.district }}</span>
              </div>
              <div class="flex items-center gap-1.5 text-slate-400 text-[11px]">
                <Clock class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>{{ item.event_time_text }}</span>
              </div>
            </div>

            <!-- 操作底栏：状态核销胶囊 + 高德导航 + Obsidian 笔记 -->
            <div class="pt-2.5 border-t border-black/[0.04] flex items-center justify-between mt-auto">
              <!-- 状态切换胶囊 (点击即时写回 SQLite + Obsidian) -->
              <button
                @click.stop="cycleStatus(item)"
                :class="[
                  'px-2.5 py-1 rounded-full text-[11px] font-medium transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs',
                  getStatusClass(item.status)
                ]"
                title="点击切换核销状态并同步至 Obsidian"
              >
                <span :class="['w-1.5 h-1.5 rounded-full', getStatusDotClass(item.status)]"></span>
                <span>{{ item.status }}</span>
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

                <!-- Obsidian 笔记跳转 -->
                <a
                  :href="item.obsidian_uri"
                  @click.stop
                  class="text-slate-400 hover:text-slate-900 text-[11px] font-medium flex items-center gap-1 py-1 px-2 hover:bg-black/[0.04] rounded-lg transition-colors"
                  title="在本地 Obsidian 查看笔记"
                >
                  <FileText class="w-3 h-3 text-slate-400" />
                  <span>笔记</span>
                </a>
              </div>
            </div>

          </div>

          <!-- 空状态 -->
          <div v-if="filteredEvents.length === 0" class="py-20 text-center text-xs text-slate-400">
            暂无匹配的同城活动
          </div>
        </div>

      </div>
    </aside>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue';
import L from 'leaflet';
import {
  Search, SlidersHorizontal, RefreshCw,
  ChevronRight, ExternalLink, MapPin, Navigation,
  Navigation2, X, CircleDot, LocateFixed, Clock,
  Compass, FileText
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

  return {
    ...item,
    id: item.id || item.post_id,
    title: cleanString(item.title),
    category: cleanString(item.category || '南京活动'),
    district: cleanString(item.district || '玄武区'),
    address: cleanString(item.address || item.location || '南京市内'),
    benefit: cleanString(item.benefit || '免费入场'),
    event_time_text: cleanString(item.event_time_text || item.event_time || item.publish_date || '近期有效'),
    status: cleanString(item.status || '待去/待薅'),
    obsidian_uri: obsUri,
    lng,
    lat,
    distance_km: Number(dist.toFixed(1))
  };
}

const categoryOptions = [
  { value: 'ALL', label: '全部' },
  { value: '南京展会', label: '展会' },
  { value: '南京活动', label: '活动' },
  { value: '羊毛福利', label: '福利' }
];

const hasActiveFilter = computed(() => {
  return selectedDistrict.value !== 'ALL' || radiusFilter.value > 0 || freeOnly.value;
});

function resetFilters() {
  selectedDistrict.value = 'ALL';
  radiusFilter.value = 0;
  freeOnly.value = false;
}

function getAmapNaviUrl(item) {
  return `https://uri.amap.com/marker?position=${item.lng},${item.lat}&name=${encodeURIComponent(item.title)}&coordinate=gaode`;
}

const filteredEvents = computed(() => {
  return events.value.filter(it => {
    if (activeCategory.value !== 'ALL' && it.category !== activeCategory.value) return false;
    if (selectedDistrict.value !== 'ALL' && it.district !== selectedDistrict.value) return false;
    if (freeOnly.value && !it.is_free) return false;
    if (radiusFilter.value > 0 && it.distance_km > radiusFilter.value) return false;
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase();
      const hay = [it.title, it.category, it.district, it.address, it.benefit].join(' ').toLowerCase();
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

function recenterMap() {
  if (leafletMap) {
    leafletMap.flyTo([XINJIEKOU[1], XINJIEKOU[0]], 12, {
      duration: 0.8,
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

// 渲染真实 Airbnb 风格价格/打点胶囊
function syncMarkers() {
  if (!leafletMap || !leafletMarkersGroup) return;
  leafletMarkersGroup.clearLayers();

  filteredEvents.value.forEach(item => {
    const dotColor = getMarkerDotColor(item.category);
    const label = item.is_free ? '免费' : (item.benefit ? item.benefit.slice(0, 4) : '活动');
    const isActive = activeEventId.value === item.id;

    // Airbnb 纯白药丸胶囊 (激活时反色黑底高亮)
    const iconHtml = `
      <div class="airbnb-marker ${isActive ? 'active' : ''}" id="leaf-marker-${item.id}">
        <div class="marker-pill inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full cursor-pointer whitespace-nowrap">
          <span class="marker-dot w-2 h-2 rounded-full shrink-0" style="background-color: ${isActive ? '#ffffff' : dotColor}"></span>
          <span class="font-bold text-xs tracking-tight shrink-0">${label}</span>
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

    marker.bindPopup(`
      <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; min-width: 190px; padding: 2px;">
        <div style="font-size: 13px; font-weight: 600; color: #0f172a; margin-bottom: 4px; line-height: 1.3;">${item.title}</div>
        <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">${item.address} · ${item.distance_km} km</div>
        <div style="display: flex; gap: 6px;">
          <a href="${getAmapNaviUrl(item)}" target="_blank" style="flex: 1; text-align: center; background: #007AFF; color: #fff; padding: 5px 8px; border-radius: 8px; font-size: 11px; text-decoration: none; font-weight: 600;">高德导航 ↗</a>
        </div>
      </div>
    `, {
      closeButton: false,
      offset: [0, -18]
    });

    marker.on('click', () => {
      activeEventId.value = item.id;
      scrollToCard(item.id);
    });

    marker.addTo(leafletMarkersGroup);
  });
}

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

function scrollToCard(itemId) {
  const el = document.getElementById('card-' + itemId);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

async function cycleStatus(item) {
  const order = ['待去/待薅', '已完成', '已过期'];
  const curIdx = order.indexOf(item.status);
  const nextStatus = order[(curIdx + 1) % order.length];
  item.status = nextStatus;

  try {
    await fetch(`/api/events/${item.id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: nextStatus })
    });
  } catch (e) {}
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
});

onMounted(() => {
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

/* Airbnb 经典药丸 Marker 样式与物理弹簧动画 */
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

.airbnb-marker:hover .marker-pill {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18), 0 2px 6px rgba(0, 0, 0, 0.08);
}

/* 激活选中态：Airbnb 纯黑反色高亮 */
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

/* Leaflet 自定义 Popup 质感 */
.leaflet-popup-content-wrapper {
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(20px) !important;
  border-radius: 16px !important;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.04) !important;
  border: 1px solid rgba(0, 0, 0, 0.06) !important;
}
.leaflet-popup-tip {
  background: rgba(255, 255, 255, 0.95) !important;
}
</style>
