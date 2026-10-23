#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Airbnb / Apple Maps Spatial Exploration Layout for Nanjing Events LBS.
Features:
- Pure Apple Minimalist Design (macOS Sonoma & Airbnb Aesthetics)
- Right Floating Drawer: bg-[#F5F5F7]/85, backdrop-blur-2xl, rounded-[28px], border border-white/80, shadow-[0_20px_50px_rgba(0,0,0,0.1)]
- Top Floating Island: top-6 left-6, rounded-[22px], detached from edges, highly translucent, STRICT single-line flex-nowrap
- Bento Grid Cards: rounded-2xl, cover image rounded-xl, font-semibold text-slate-900
- 1. Zero Navigation: Completely removed all route planning/navigation buttons; replaced with [📍 定位] and [详情 >]
- 2. Map Capsule Markers: Single-layer highlight [bg-[#007AFF] text-white scale-110], zero popup double-shadow
- 3. Right Drawer Header: Fixed flex-shrink-0 header with [视野联动] switch, cards in independent overflow container
- 4. Data Insights Modal: Apple Bento modal with ECharts bar & ring charts + time distribution panel
- 5. Wishlist & Secondary Detail Modal: [复制地址] button, original source link, proximity-to-deadline sort
"""

import json
from pathlib import Path
import dashboard_server

OUT_HTML = Path(__file__).resolve().parent / "dashboard.html"

items = dashboard_server.get_all_events()
fallback_json = json.dumps(items, ensure_ascii=False)

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="zh-CN" class="h-full">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>南京同城活动 · 空间探索 · Apple Maps Layout</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
      font-variant-numeric: tabular-nums;
      -webkit-font-smoothing: antialiased;
    }
    .no-scrollbar::-webkit-scrollbar { display: none; }
    .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

    .amap-apple-filter .leaflet-tile {
      filter: grayscale(88%) brightness(103%) contrast(92%) !important;
    }

    .apple-marker {
      transform: translate(-50%, -100%);
      transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform;
      white-space: nowrap !important;
    }
    .apple-marker:hover {
      transform: translate(-50%, -108%) scale(1.08);
      z-index: 50 !important;
    }
    .apple-marker {
      transform: translate(-50%, -100%);
      transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .apple-marker:hover {
      transform: translate(-50%, -105%) scale(1.05);
      z-index: 500 !important;
    }
    .apple-marker.active {
      transform: translate(-50%, -108%) scale(1.12);
      z-index: 1000 !important;
    }
    .apple-marker.active .marker-pill {
      background-color: #020617 !important; /* bg-slate-950 */
      color: #ffffff !important;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.35), 0 2px 6px rgba(0, 0, 0, 0.2) !important;
      border-color: rgba(255, 255, 255, 0.2) !important;
    }
    .apple-marker.active .marker-name,
    .apple-marker.active .marker-price {
      color: #ffffff !important;
    }
    .apple-marker.active .marker-dot {
      background-color: #ffffff !important;
      box-shadow: 0 0 8px rgba(255, 255, 255, 0.8) !important;
    }
  </style>
</head>
<body class="h-full w-full overflow-hidden bg-[#F5F5F7] select-none text-slate-900">
  <div id="app" class="relative w-screen h-screen overflow-hidden font-sans antialiased">

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

    <!-- 2. 顶部：悬浮于地图左上方的通透圆角浮动岛屿 (严格单行无折行留白) -->
    <header class="absolute top-6 left-6 z-20 pointer-events-auto max-w-[calc(100vw-3rem)] md:max-w-[860px]">
      <div class="bg-white/85 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.08),0_1px_3px_rgba(0,0,0,0.03)] border border-white/80 p-1.5 sm:p-2 flex flex-nowrap items-center whitespace-nowrap gap-2 transition-all overflow-x-auto no-scrollbar">
        
        <!-- 紧凑搜索框 -->
        <div class="relative flex items-center w-36 sm:w-48 md:w-56 shrink-0">
          <svg class="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
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
            <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <!-- 类别滑动胶囊分段器 -->
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

        <!-- 线上/线下实体场馆独立切换 -->
        <div class="flex items-center p-0.5 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600 shrink-0">
          <button
            @click="venueFilter = 'ALL'"
            :class="[
              'px-2 py-1 rounded-lg transition-all text-xs cursor-pointer',
              venueFilter === 'ALL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="查看全部同城内容"
          >
            全览
          </button>
          <button
            @click="venueFilter = 'PHYSICAL'"
            :class="[
              'px-2 py-1 rounded-lg transition-all text-xs cursor-pointer flex items-center gap-1',
              venueFilter === 'PHYSICAL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="仅看有物理场馆定位的线下活动"
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
            title="仅看线上/全城通用银行与支付福利"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-[#34C759]"></span>
            <span>全城羊毛</span>
          </button>
        </div>

        <!-- ⭐ 待去清单(N) 快捷收藏过滤 -->
        <button
          @click="showFavoritesOnly = !showFavoritesOnly"
          :class="[
            'px-2.5 py-1.5 rounded-xl transition-all cursor-pointer flex items-center gap-1 text-xs font-medium shrink-0',
            showFavoritesOnly
              ? 'bg-amber-500 text-white shadow-sm font-semibold'
              : 'bg-black/[0.04] text-slate-700 hover:bg-black/[0.07]'
          ]"
          title="仅显示已加入待去清单的活动 (按截止最近排序)"
        >
          <svg class="w-3.5 h-3.5" :class="showFavoritesOnly ? 'fill-white text-white' : 'text-amber-500 fill-amber-500'" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
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
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>
          </svg>
          <span v-if="hasActiveFilter" class="w-1.5 h-1.5 rounded-full bg-[#34C759] absolute top-1 right-1"></span>
        </button>

        <!-- 增量同步按钮 -->
        <button
          @click="triggerSync"
          :disabled="isSyncing"
          class="p-1.5 rounded-xl text-slate-600 hover:bg-black/[0.04] transition-all cursor-pointer shrink-0"
          title="增量同步最新社媒情报"
        >
          <svg :class="['w-4 h-4', isSyncing ? 'animate-spin text-[#007AFF]' : '']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
          </svg>
        </button>

      </div>

      <!-- 下拉微质感 Popover 筛选器 -->
      <div
        v-if="showFilterPopover"
        class="mt-2 p-3 bg-white/90 backdrop-blur-2xl backdrop-saturate-150 rounded-[20px] shadow-[0_20px_50px_rgba(0,0,0,0.12)] border border-white/80 flex items-center gap-3 text-xs animate-in fade-in slide-in-from-top-2 duration-200 flex-wrap"
      >
        <!-- 时间维度筛选 -->
        <div class="flex items-center gap-1.5 text-slate-700">
          <svg class="w-3.5 h-3.5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
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

        <div class="flex items-center gap-1.5 text-slate-600">
          <svg class="w-3.5 h-3.5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
          </svg>
          <select v-model="selectedDistrict" @change="onDistrictChange" class="bg-transparent border-0 outline-none font-medium cursor-pointer text-slate-800 text-xs">
            <option value="ALL">全城区域 (11区)</option>
            <option v-for="d in districts" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>

        <div class="h-3.5 w-px bg-slate-200"></div>

        <div class="flex items-center gap-1.5 text-slate-600">
          <svg class="w-3.5 h-3.5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="3 11 22 2 13 21 11 13 3 11"/>
          </svg>
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
    
      <!-- 空间瞬移极简片区栏 (脱离抽屉，回归地图空间探索) -->
      <div class="mt-2 flex items-center gap-1.5 overflow-x-auto no-scrollbar pointer-events-auto">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-medium text-slate-500 bg-white/80 backdrop-blur-md border border-white/80 shadow-2xs shrink-0 flex items-center gap-1">
          <svg class="w-2.5 h-2.5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
          </svg>
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

    <!-- 3. 左下角：高德地图深度功能控制岛 -->
    <div class="absolute bottom-6 left-6 z-20 flex items-center gap-2 pointer-events-auto">
      
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

      <!-- 新街口中心辐射同心圈切换 -->
      <button
        @click="toggleRings"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showRings ? 'bg-slate-950 text-white border-slate-950 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
        title="在地图上显示新街口 3km/5km/10km 辐射同心圈"
      >
        <svg class="w-3.5 h-3.5" :class="showRings ? 'text-[#34C759]' : 'text-slate-400'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
        <span>辐射圈</span>
      </button>

      <!-- 🔥 活动热力分布图开关 -->
      <button
        @click="toggleHeatmap"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showHeatmap ? 'bg-slate-950 text-white border-slate-950 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
        title="在地图上叠加南京活动密度热力分布图"
      >
        <span class="w-2 h-2 rounded-full" :class="showHeatmap ? 'bg-[#FF3B30]' : 'bg-slate-400'"></span>
        <span>热力图</span>
      </button>

      <!-- 📊 数据统计可视化图表弹窗 (ECharts) -->
      <button
        @click="openStatsModal"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showStatsModal ? 'bg-slate-950 text-white border-slate-950 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
        title="查看南京各区与类型数据可视化统计"
      >
        <svg class="w-3.5 h-3.5" :class="showStatsModal ? 'text-white' : 'text-[#007AFF]'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
        <span>数据统计</span>
      </button>

      <!-- 一键复位新街口中心 -->
      <button
        @click="recenterMap"
        class="p-2.5 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-slate-700 hover:text-slate-950 hover:bg-white transition cursor-pointer"
        title="复位至新街口中心"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/>
        </svg>
      </button>

    </div>

    <!-- 4. 右侧：Airbnb 风格悬浮卡片抽屉 (Liquid Glass Frosted Sheet) -->
    <aside
      :class="[
        'z-20 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col pointer-events-auto fixed inset-x-0 bottom-0 max-h-[50vh] rounded-t-[28px] border-t border-white/80 shadow-[0_-10px_40px_rgba(0,0,0,0.12)] bg-[#F5F5F7]/95 backdrop-blur-2xl md:fixed md:top-6 md:right-6 md:bottom-6 md:left-auto md:w-[420px] md:max-h-none md:rounded-[28px] md:border md:border-white/80 md:shadow-[0_20px_50px_rgba(0,0,0,0.1)]',
        !drawerOpen ? 'translate-y-full md:translate-y-0 md:translate-x-[calc(100%+24px)]' : 'translate-y-0 md:translate-x-0'
      ]"
    >
      <div class="relative w-full h-full bg-[#F5F5F7]/85 backdrop-blur-2xl backdrop-saturate-150 rounded-[28px] border border-white/80 shadow-[0_20px_50px_rgba(0,0,0,0.1)] flex flex-col overflow-hidden">
        
                <!-- 固定头部：标题栏 + 视图切换 + 3维排序 + 横向14天日历条 (非溢出 Apple HIG 3 层轻薄布局) -->
        <div class="flex-shrink-0 z-10 bg-[#F5F5F7]/95 backdrop-blur-md border-b border-black/[0.04]">
          <!-- Tier 1: 标题 + [卡片/时间轴] 分段切换 + 折叠抽屉按钮 (从不溢出) -->
          <div class="px-4 pt-3 pb-1.5 flex items-center justify-between">
            <div class="flex items-center gap-1.5">
              <h2 class="text-xs font-semibold text-slate-900 tracking-tight">南京精选</h2>
              <span class="text-[11px] font-semibold text-slate-400 tabular-nums">({{ filteredEvents.length }})</span>
              <span v-if="showFavoritesOnly" class="ml-1 text-[9.5px] bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded-full font-semibold">待去清单</span>
            </div>

            <div class="flex items-center gap-1.5">
              <!-- 视图切换：卡片 vs 时间轴 -->
              <div class="inline-flex rounded-lg bg-black/[0.05] p-0.5 border border-black/[0.04]">
                <button
                  @click="currentViewMode = 'cards'"
                  class="px-2 py-0.5 rounded-md text-[10.5px] font-medium transition-all cursor-pointer flex items-center gap-1"
                  :class="currentViewMode === 'cards' ? 'bg-white text-slate-900 shadow-2xs font-semibold' : 'text-slate-500 hover:text-slate-800'"
                  title="卡片网格流"
                >
                  <svg class="w-3 h-3 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
                  </svg>
                  <span>卡片</span>
                </button>
                <button
                  @click="currentViewMode = 'timeline'"
                  class="px-2 py-0.5 rounded-md text-[10.5px] font-medium transition-all cursor-pointer flex items-center gap-1"
                  :class="currentViewMode === 'timeline' ? 'bg-white text-slate-900 shadow-2xs font-semibold' : 'text-slate-500 hover:text-slate-800'"
                  title="紧迫度时间轴"
                >
                  <svg class="w-3 h-3 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                  </svg>
                  <span>时间轴</span>
                </button>
              </div>

              <!-- 折叠按钮 -->
              <button
                @click="drawerOpen = !drawerOpen"
                class="w-6 h-6 rounded-md bg-black/[0.03] hover:bg-black/[0.06] text-slate-400 hover:text-slate-800 flex items-center justify-center transition cursor-pointer"
                :title="drawerOpen ? '收起抽屉' : '展开抽屉'"
              >
                <svg :class="['w-3.5 h-3.5 transition-transform duration-200', drawerOpen ? 'rotate-0' : 'rotate-180']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Tier 2: 3维排序胶囊 [距离 | 截止 | 最新] + 视野联动开关 -->
          <div class="px-4 py-1.5 flex items-center justify-between border-t border-black/[0.03] bg-black/[0.01]">
            <div class="inline-flex rounded-full bg-black/[0.04] p-0.5 border border-black/[0.04] text-[10.5px]">
              <button
                @click="sortMode = 'distance'"
                class="px-2.5 py-0.5 rounded-full transition-all cursor-pointer"
                :class="sortMode === 'distance' ? 'bg-white text-slate-900 font-semibold shadow-2xs' : 'text-slate-500 hover:text-slate-700'"
                title="按距离市中心由近到远排序"
              >
                距离最近
              </button>
              <button
                @click="sortMode = 'expiring'"
                class="px-2.5 py-0.5 rounded-full transition-all cursor-pointer"
                :class="sortMode === 'expiring' ? 'bg-white text-slate-900 font-semibold shadow-2xs' : 'text-slate-500 hover:text-slate-700'"
                title="按剩余截止天数排序"
              >
                即将截止
              </button>
              <button
                @click="sortMode = 'latest'"
                class="px-2.5 py-0.5 rounded-full transition-all cursor-pointer"
                :class="sortMode === 'latest' ? 'bg-white text-slate-900 font-semibold shadow-2xs' : 'text-slate-500 hover:text-slate-700'"
                title="按收录发布时间排序"
              >
                最新收录
              </button>
            </div>

            <button
              @click="toggleBoundsFilter"
              class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10.5px] font-medium transition-all cursor-pointer border"
              :class="boundsFilterEnabled ? 'bg-emerald-50 text-emerald-800 border-emerald-200/80 shadow-2xs' : 'bg-white/80 hover:bg-white text-slate-500 border-black/[0.04]'"
              title="开启后仅展示当前地图可视矩形范围内的线下活动"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="boundsFilterEnabled ? 'bg-[#34C759]' : 'bg-slate-300'"></span>
              <span>视野联动</span>
            </button>
          </div>

          <!-- Tier 3: 【未来14天横向滑动日历条】(紧凑高密设计，高度 36px) -->
          <div class="px-3 py-1.5 flex items-center gap-1 overflow-x-auto no-scrollbar border-t border-black/[0.03] bg-black/[0.015]">
            <button
              @click="selectedCalendarDate = null"
              :class="[
                'min-w-[38px] h-[36px] rounded-lg flex flex-col items-center justify-center px-1 cursor-pointer transition-all shrink-0 text-center',
                selectedCalendarDate === null
                  ? 'bg-slate-950 text-white shadow-xs font-semibold'
                  : 'bg-white/80 hover:bg-white text-slate-600 border border-black/[0.04]'
              ]"
              title="查看全部日期活动"
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
              :title="day.iso + ' (' + day.count + ' 个活动开放)'"
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

        <!-- 独立卡片滚动容器 (支持 卡片网格 与 ⏱️ 时间轴 双视图切换) -->
        <div class="flex-1 min-h-0 overflow-y-auto p-4 no-scrollbar" id="cards-container">
          <!-- 视图 A: Bento 卡片流 -->
          <div v-if="currentViewMode === 'cards'" class="space-y-4">
            <div
              v-for="item in filteredEvents"
              :key="item.id"
              :id="'card-' + item.id"
              @click="openDetail(item)" @mouseenter="activeEventId = item.id" @mouseleave="activeEventId = detailItem ? detailItem.id : null"
              :class="[
                'group bg-white rounded-2xl p-3.5 transition-all duration-300 cursor-pointer border flex flex-col',
                activeEventId === item.id
                  ? 'ring-2 ring-[#007AFF] border-transparent shadow-[0_16px_36px_rgba(0,122,255,0.16)] -translate-y-1'
                  : 'border-black/[0.04] shadow-[0_4px_16px_rgba(0,0,0,0.04)] hover:shadow-[0_12px_30px_rgba(0,0,0,0.08)] hover:-translate-y-1'
              ]"
            >
            <!-- Bento 封面图 -->
            <div class="relative w-full h-36 rounded-xl overflow-hidden mb-3 bg-slate-100 group-hover:scale-[1.01] transition-transform duration-300 shrink-0">
              <img
                :src="getEventCover(item)"
                :alt="item.title"
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

              <!-- 免票/福利徽标 -->
              <span class="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded-lg text-[11px] font-medium tracking-tight backdrop-blur-md bg-white/90 text-slate-800 flex items-center gap-1">
                <span class="font-semibold text-[#34C759]" v-if="item.is_free">免票直入</span>
                <span class="text-slate-700 font-medium" v-else>{{ item.benefit }}</span>
              </span>

              <span v-if="item.is_online" class="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded-lg text-[10px] font-semibold tracking-tight backdrop-blur-md bg-emerald-500/80 text-white">
                线上/全城
              </span>
            </div>

            <!-- 结构化时态小标签行 -->
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

            <!-- 地理元数据行 -->
            <div class="text-xs text-slate-500 space-y-1 mb-3">
              <div class="flex items-center gap-1.5 text-slate-600">
                <svg class="w-3.5 h-3.5 text-slate-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                </svg>
                <span class="truncate font-medium text-slate-800">{{ item.address }}</span>
                <span class="text-slate-300">·</span>
                <span class="shrink-0 text-slate-500 bg-black/[0.03] px-1.5 py-0.5 rounded text-[11px]">{{ item.district }}</span>
              </div>
            </div>

            <!-- 操作底栏：彻底去除导航！保留待去，改为【📍 定位】与【详情 >】 -->
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
                <svg class="w-3 h-3" :class="isFavorite(item.id) ? 'fill-amber-500 text-amber-500' : 'text-slate-400'" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
                <span>{{ isFavorite(item.id) ? '已待去' : '☆ 待去' }}</span>
              </button>

              <div class="flex items-center gap-1.5">
                <!-- 📍 定位：平滑聚焦高亮 Marker -->
                <button
                  @click.stop="focusEvent(item)"
                  class="text-slate-600 hover:text-[#007AFF] text-[11px] font-medium flex items-center gap-1 py-1 px-2 hover:bg-blue-50/50 rounded-lg transition-colors cursor-pointer"
                  title="在地图上平滑聚焦并高亮此标点"
                >
                  <svg class="w-3 h-3 text-slate-400 group-hover:text-[#007AFF]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                  </svg>
                  <span>定位</span>
                </button>

                <!-- 详情 >：滑出二级完整图文详情与原帖链接 -->
                <button
                  @click.stop="openDetail(item)"
                  class="text-slate-700 hover:text-slate-900 text-[11px] font-semibold flex items-center gap-0.5 py-1 px-2 hover:bg-black/[0.04] rounded-lg transition-colors cursor-pointer"
                  title="查看完整图文详情与原帖链接"
                >
                  <span>详情</span>
                  <svg class="w-3.5 h-3.5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 6"/>
                  </svg>
                </button>
              </div>
            </div>

          </div>\r\n        </div>\r\n\r\n        <!-- 视图 B: 【⏱️ 时间轴视图 (Timeline View)】 -->
          <div v-else class="space-y-6">
            <!-- 4 大吸顶分组 -->
            <div v-for="group in timelineGroups" :key="group.id" class="relative">
              <!-- Sticky 吸顶组头 -->
              <div class="sticky top-0 z-20 py-1.5 px-3 rounded-xl bg-[#F5F5F7]/95 backdrop-blur-md border border-black/[0.04] shadow-2xs mb-3 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full" :class="group.dotColor"></span>
                  <span class="text-xs font-bold text-slate-800 tracking-tight">{{ group.title }}</span>
                  <span class="text-[10px] text-slate-400 font-normal">· {{ group.desc }}</span>
                </div>
                <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full tabular-nums" :class="group.badgeClass">
                  {{ group.items.length }} 场
                </span>
              </div>

              <!-- 分组下卡片条目 (带像素级贯通纵向导轨) -->
              <div class="relative pl-7 space-y-3">
                <!-- 本组连续纵向发光引导线 (位于 left-2.5，即 10px 处，居中对齐节点) -->
                <div class="absolute left-[10px] top-3 bottom-3 w-[2px] bg-slate-300 rounded-full pointer-events-none"></div>

                <div
                  v-for="item in group.items"
                  :key="item.id"
                  :id="'timeline-card-' + item.id"
                  @click="openDetail(item)" @mouseenter="activeEventId = item.id" @mouseleave="activeEventId = detailItem ? detailItem.id : null"
                  :class="[
                    'group relative bg-white rounded-2xl p-3 transition-all duration-300 cursor-pointer border flex flex-col',
                    activeEventId === item.id
                      ? 'ring-2 ring-[#007AFF] border-transparent shadow-[0_16px_36px_rgba(0,122,255,0.16)] -translate-y-0.5'
                      : 'border-black/[0.04] shadow-[0_3px_12px_rgba(0,0,0,0.03)] hover:shadow-[0_10px_24px_rgba(0,0,0,0.06)] hover:-translate-y-0.5'
                  ]"
                >
                  <!-- 时间轴发光小节点 (居中穿在引导线上: left 10px - 28px = -18px, 宽度 12px -> left: -23px, 5px~17px 完美居中 11px) -->
                  <div
                    class="absolute -left-[23px] top-4 w-3 h-3 rounded-full border-2 border-white shadow-xs z-10 ring-2 ring-black/[0.04]"
                    :class="group.nodeColor"
                  ></div>

                  <div class="flex gap-3">
                    <!-- 缩略图 -->
                    <div class="relative w-20 h-20 rounded-xl overflow-hidden bg-slate-100 shrink-0">
                      <img :src="getEventCover(item)" :alt="item.title" loading="lazy" class="w-full h-full object-cover rounded-xl" />
                      <span class="absolute bottom-1 left-1 px-1.5 py-0.2 rounded text-[9px] font-semibold backdrop-blur-md bg-black/60 text-white tabular-nums">
                        {{ item.distance_km }}km
                      </span>
                    </div>

                    <!-- 信息体 -->
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

                </div>
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

    <!-- 5. 活动二级详情抽屉面板 (彻底移除导航，增加复制地址与原帖链接) -->
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
        <div class="w-[420px] md:w-[480px] h-full bg-white/95 backdrop-blur-3xl shadow-[0_25px_70px_rgba(0,0,0,0.2)] border-l border-white/80 flex flex-col overflow-hidden">
          
          <!-- 详情顶部大图 -->
          <div class="relative w-full h-56 bg-slate-100 shrink-0 overflow-hidden">
            <img
              :src="getEventCover(detailItem)"
              :alt="detailItem.title"
              class="w-full h-full object-cover"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-black/20"></div>

            <!-- 关闭按钮 -->
            <button
              @click="closeDetail"
              class="absolute top-4 right-4 w-8 h-8 rounded-full bg-black/40 hover:bg-black/60 backdrop-blur-md text-white flex items-center justify-center transition-all cursor-pointer shadow-sm"
              title="关闭详情 (ESC)"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>

            <!-- 顶部浮标 -->
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

            <!-- 封面底部信息 -->
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

          <!-- 详情正文滚动区域 -->
          <div class="flex-1 overflow-y-auto p-5 space-y-4 no-scrollbar text-xs">
            
            <!-- 具体场馆文本地址卡片 (配 [复制地址] 按钮，绝无导航按钮) -->
            <div class="bg-black/[0.025] rounded-xl p-3 border border-black/[0.04] flex items-center justify-between gap-3">
              <div class="flex items-start gap-2.5 min-w-0">
                <svg class="w-4 h-4 text-[#007AFF] shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                </svg>
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-slate-900 truncate">{{ detailItem.address }}</div>
                  <div class="text-[11px] text-slate-400 mt-0.5">{{ detailItem.district }} · 距新街口 {{ detailItem.distance_km }} km</div>
                </div>
              </div>
              <button
                @click="copyAddress(detailItem.address)"
                class="shrink-0 px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 rounded-lg border border-black/[0.08] shadow-xs text-[11px] font-medium flex items-center gap-1 cursor-pointer transition-all"
                title="复制场馆地址"
              >
                <span>{{ copiedAddress ? '✓ 已复制' : '复制地址' }}</span>
              </button>
            </div>

            <!-- 核心优惠/权益模块 -->
            <!-- 门票与权益：绿色微质感卡片 -->
            <div class="bg-emerald-50/70 rounded-xl p-3 border border-emerald-200/60 flex items-center gap-2 text-emerald-900">
              <span class="w-2 h-2 rounded-full bg-[#34C759] shrink-0"></span>
              <span class="text-xs font-semibold">{{ detailItem.benefit || (detailItem.is_free ? '免票直入' : '详见活动原帖说明') }}</span>
            </div>

            <!-- 举办时间：图标+文本直接表达 -->
            <div class="bg-black/[0.025] rounded-xl p-3 border border-black/[0.04] flex items-center gap-2.5 text-slate-700">
              <svg class="w-4 h-4 text-slate-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              <span class="font-medium text-xs">{{ detailItem.event_time_text }}</span>
            </div>

            <!-- 简介正文：纯白实体 Apple Card -->
            <div class="text-slate-700 leading-relaxed bg-white rounded-xl p-4 border border-black/[0.04] shadow-xs text-xs">
              {{ detailItem.summary || detailItem.title }}
            </div>

          </div>

          <!-- 底部操作按钮 (去导航闭环) -->
          <div class="p-4 border-t border-black/[0.04] bg-white/60 backdrop-blur-md flex items-center gap-2.5 shrink-0">
            <!-- 待去清单 -->
            <button
              @click="toggleFavorite(detailItem)"
              :class="[
                'flex-1 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-sm',
                isFavorite(detailItem.id)
                  ? 'bg-amber-500 text-white shadow-amber-500/20'
                  : 'bg-black/[0.05] hover:bg-black/[0.08] text-slate-800'
              ]"
            >
              <span>{{ isFavorite(detailItem.id) ? '已在清单' : '加入待去' }}</span>
            </button>

            <!-- 前往原平台查看链接 -->
            <a
              :href="detailItem.source_url || detailItem.obsidian_uri || '#'"
              target="_blank"
              class="flex-1 py-2.5 rounded-xl text-xs font-semibold bg-[#007AFF] hover:bg-[#0071EB] text-white transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-sm text-center"
            >
              <span>前往原平台查看</span>
            </a>

            <!-- Obsidian 本地笔记深链 -->
            <a
              v-if="detailItem.obsidian_uri"
              :href="detailItem.obsidian_uri"
              class="p-2.5 rounded-xl bg-black/[0.05] hover:bg-black/[0.08] text-slate-700 transition-all cursor-pointer"
              title="在本地 Obsidian 查看双向链接笔记"
            >
              <svg class="w-4 h-4 text-slate-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
              </svg>
            </a>
          </div>

        </div>
      </div>
    </transition>

    <!-- 6. 📊 数据洞察可视化图表弹窗 (ECharts Apple Bento 风格居中模态框) -->
    <div
      v-if="showStatsModal"
      class="fixed inset-0 z-50 bg-black/35 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200 pointer-events-auto"
      @click.self="closeStatsModal"
    >
      <div class="relative w-full max-w-4xl bg-white/95 backdrop-blur-3xl rounded-[28px] border border-white/80 shadow-[0_25px_70px_rgba(0,0,0,0.25)] p-6 flex flex-col max-h-[92vh] overflow-hidden">
        <div class="flex items-center justify-between pb-4 border-b border-black/[0.05] shrink-0">
          <div class="flex items-center gap-2">
            <h2 class="text-base font-semibold text-slate-900 tracking-tight">南京活动概览</h2>
            <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700">{{ filteredEvents.length }} 场</span>
          </div>
          <button
            @click="closeStatsModal"
            class="w-8 h-8 rounded-full bg-black/[0.04] hover:bg-black/[0.08] text-slate-600 flex items-center justify-center transition cursor-pointer"
            title="关闭 (ESC)"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto pt-4 space-y-4 no-scrollbar">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- ① 各行政区活动密度柱状图 -->
            <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex flex-col">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-semibold text-slate-900">各行政区活动密度分布</span>
                <span class="text-[11px] text-slate-400">单位: 场次</span>
              </div>
              <div id="district-chart" class="w-full h-56"></div>
            </div>

            <!-- ② 活动类型占比环形饼图 -->
            <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex flex-col">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-semibold text-slate-900">活动类型占比结构</span>
                <span class="text-[11px] text-slate-400">分类分布</span>
              </div>
              <div id="category-chart" class="w-full h-56"></div>
            </div>
          </div>

          <!-- ③ 活动时间分布 -->
          <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-semibold text-slate-900">活动时空时态分布阶段</span>
              <span class="text-[11px] text-slate-400">时态生命周期</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div class="bg-slate-50/80 rounded-xl p-3.5 border border-black/[0.03] flex flex-col">
                <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span>进行中 / 已开展</span>
                  <span class="font-semibold text-slate-900 tabular-nums">{{ timeStats.ongoing }} 场</span>
                </div>
                <div class="text-xl font-bold text-slate-900 tabular-nums">{{ timeStats.ongoingPercent }}%</div>
                <div class="w-full h-1.5 bg-slate-200 rounded-full mt-2.5 overflow-hidden">
                  <div class="h-full bg-[#34C759] rounded-full" :style="{ width: timeStats.ongoingPercent + '%' }"></div>
                </div>
              </div>

              <div class="bg-slate-50/80 rounded-xl p-3.5 border border-black/[0.03] flex flex-col">
                <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span>即将截止 (剩≤3天)</span>
                  <span class="font-semibold text-slate-900 tabular-nums">{{ timeStats.expiring }} 场</span>
                </div>
                <div class="text-xl font-bold text-slate-900 tabular-nums">{{ timeStats.expiringPercent }}%</div>
                <div class="w-full h-1.5 bg-slate-200 rounded-full mt-2.5 overflow-hidden">
                  <div class="h-full bg-[#FF9500] rounded-full" :style="{ width: timeStats.expiringPercent + '%' }"></div>
                </div>
              </div>

              <div class="bg-slate-50/80 rounded-xl p-3.5 border border-black/[0.03] flex flex-col">
                <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span>长期 / 后续开展</span>
                  <span class="font-semibold text-slate-900 tabular-nums">{{ timeStats.upcoming }} 场</span>
                </div>
                <div class="text-xl font-bold text-slate-900 tabular-nums">{{ timeStats.upcomingPercent }}%</div>
                <div class="w-full h-1.5 bg-slate-200 rounded-full mt-2.5 overflow-hidden">
                  <div class="h-full bg-[#007AFF] rounded-full" :style="{ width: timeStats.upcomingPercent + '%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <script>
    const { createApp, ref, computed, watch, onMounted, nextTick } = Vue;

    const INITIAL_EVENTS = __INITIAL_EVENTS__;
    const XINJIEKOU = [118.7842, 32.0418];

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

    const ZONE_TELEPORTS = [
      { label: '全城', coords: [118.7842, 32.0418], zoom: 12 },
      { label: '新街口/鼓楼', coords: [118.7842, 32.0418], zoom: 14 },
      { label: '老门东/秦淮', coords: [118.7981, 32.0112], zoom: 14 },
      { label: '河西/建邺', coords: [118.7327, 32.0045], zoom: 14 },
      { label: '仙林大学城', coords: [118.9189, 32.1065], zoom: 13 },
      { label: '江宁百家湖', coords: [118.8258, 31.9328], zoom: 13 },
    ];

    const THEME_IMAGE_POOLS = {
      art: [
        'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1518998053901-5348d3961a04?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1561214115-f2f134cc4912?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1544967082-d9d25d867d66?w=600&auto=format&fit=crop&q=80'
      ],
      heritage: [
        'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1548013146-72479768bada?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1563089145-599997674d42?w=600&auto=format&fit=crop&q=80'
      ],
      music: [
        'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=600&auto=format&fit=crop&q=80'
      ],
      market_outdoor: [
        'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1510312305653-8ed496efae75?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&auto=format&fit=crop&q=80'
      ],
      food: [
        'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1544025162-d76694265947?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1563245372-f21724e3856d?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&auto=format&fit=crop&q=80'
      ],
      tech_pop: [
        'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=600&auto=format&fit=crop&q=80'
      ],
      finance_perks: [
        'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1556742049-0a67c5574f73?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=600&auto=format&fit=crop&q=80'
      ],
      nature_park: [
        'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1508873696983-2df5703bc20d?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1534188753412-3e26d0d618d6?w=600&auto=format&fit=crop&q=80',
        'https://images.unsplash.com/photo-1473448912268-2022ce9509d8?w=600&auto=format&fit=crop&q=80'
      ]
    };

    function hashStr(s) {
      if (!s) return 0;
      let h = 0;
      for (let i = 0; i < s.length; i++) {
        h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
      }
      return Math.abs(h);
    }

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

    createApp({
      setup() {
        const events = ref([]);
        const activeCategory = ref('ALL');
        const venueFilter = ref('ALL');
        const boundsFilterEnabled = ref(false);
        const mapBounds = ref(null);
        const timeFilter = ref('ALL');
        const selectedDistrict = ref('ALL');
        const radiusFilter = ref(0);
        const freeOnly = ref(false);
        const showFavoritesOnly = ref(false);
        const searchQuery = ref('');
        const activeEventId = ref(null);
        const detailItem = ref(null);
        const copiedAddress = ref(false);
        const drawerOpen = ref(true);
        const isSyncing = ref(false);
        const showFilterPopover = ref(false);
        const showRings = ref(false);
        const showHeatmap = ref(false);
        const showStatsModal = ref(false);
        const mapStyleMode = ref('standard');
        const activeZoneLabel = ref('全城');
        const currentViewMode = ref('cards'); // 'cards' | 'timeline'
        const sortMode = ref('distance');    // 'distance' (默认主城优先) | 'expiring' | 'latest'
        const selectedCalendarDate = ref(null); // 'YYYY-MM-DD' 单日筛选

        // 未来 14 天横向滑动日历条
        const calendarDays = computed(() => {
          const days = [];
          const base = new Date('2026-10-23T00:00:00');
          const weekMap = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
          for (let i = 0; i < 14; i++) {
            const d = new Date(base.getTime() + i * 86400000);
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const dayNum = String(d.getDate()).padStart(2, '0');
            const iso = `${y}-${m}-${dayNum}`;
            const label = i === 0 ? '今天' : (i === 1 ? '明天' : weekMap[d.getDay()]);

            const count = events.value.filter(it => {
              if (!it.start_date || !it.end_date) return true;
              return it.start_date <= iso && iso <= it.end_date;
            }).length;

            const dots = count === 0 ? 0 : (count > 15 ? 3 : (count > 5 ? 2 : 1));

            days.push({
              iso,
              label,
              dateNum: d.getDate(),
              count,
              dots
            });
          }
          return days;
        });

        function selectCalendarDay(iso) {
          if (selectedCalendarDate.value === iso) {
            selectedCalendarDate.value = null;
          } else {
            selectedCalendarDate.value = iso;
          }
        }

        const favoriteIds = ref(JSON.parse(localStorage.getItem('nanjing_favorites') || '[]'));

        let districtChartInstance = null;
        let categoryChartInstance = null;

        const mapModes = [
          { id: 'standard', label: '高德全彩', color: '#007AFF' },
          { id: 'satellite', label: '高清卫星', color: '#10B981' },
          { id: 'apple', label: '苹果浅灰', color: '#64748B' },
          { id: 'dark', label: '午夜深色', color: '#0F172A' }
        ];

        const timeFilterOptions = [
          { value: 'ALL', label: '全部时间' },
          { value: 'TODAY', label: '今日' },
          { value: 'WEEKEND', label: '本周末' },
          { value: 'EXPIRING', label: '即将截止' }
        ];

        const zoneTeleports = ZONE_TELEPORTS;

        let leafletMap = null;
        let baseTileLayer = null;
        let satelliteOverlayLayer = null;
        let leafletMarkersGroup = null;
        let ringsGroup = null;
        let heatLayer = null;

        const districts = [
          '玄武区', '秦淮区', '建邺区', '鼓楼区', '栖霞区',
          '雨花台区', '江宁区', '浦口区', '六合区', '溧水区', '高淳区'
        ];

        function cleanString(str) {
          if (!str) return '';
          return String(str).replace(/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}\\uFE0F]/gu, '').trim();
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

        function isOnlineEvent(item) {
          const hay = (item.title + ' ' + (item.address || '') + ' ' + (item.benefit || '')).toLowerCase();
          return hay.includes('银行') || hay.includes('立减金') || hay.includes('消费券') || 
                 item.district === '全城通用' || item.address === '全城通用' || 
                 (Math.abs(item.lng - XINJIEKOU[0]) < 0.001 && Math.abs(item.lat - XINJIEKOU[1]) < 0.001 && item.category === '羊毛福利');
        }

        function normalize(item) {
          const lng = Number(item.lng || 118.7842);
          const lat = Number(item.lat || 32.0418);
          const dist = item.distance_km != null 
            ? Number(item.distance_km) 
            : haversineDistance(XINJIEKOU[0], XINJIEKOU[1], lng, lat);
          
          const obsPath = item.obsidian_path || '';
          const obsUri = obsPath ? `obsidian://open?vault=IOT&file=${encodeURIComponent(obsPath)}` : '';

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
            summary: cleanString(item.summary || item.action_guide || ''),
            source_url: item.source_url || item.url || '',
            obsidian_uri: obsUri,
            lng,
            lat,
            distance_km: Number(dist.toFixed(1))
          };
        }

                function getEventCover(item) {
          if (!item) return '';
          if (COVER_MAP[item.id]) return COVER_MAP[item.id];
          const hay = (item.title + ' ' + (item.summary || '') + ' ' + (item.category || '')).toLowerCase();
          const hash = hashStr(item.id || item.title || 'event');

          let pool = THEME_IMAGE_POOLS.nature_park;
          if (/螃蟹|美食|小吃|糕团|采摘|吃|鲜蟹|果蔬/.test(hay)) {
            pool = THEME_IMAGE_POOLS.food;
          } else if (/老街|古镇|汉服|非遗|戏曲|民国|寺庙|大板巷|夫子庙|大报恩寺|熙南里/.test(hay)) {
            pool = THEME_IMAGE_POOLS.heritage;
          } else if (/艺术|画展|美术馆|雕塑|特展|双年展|展览|书画|工艺|文物|博物院/.test(hay)) {
            pool = THEME_IMAGE_POOLS.art;
          } else if (/音乐|草坪|乐队|演出|交响|民谣|黑胶|打铁花|演唱会/.test(hay)) {
            pool = THEME_IMAGE_POOLS.music;
          } else if (/市集|咖啡|露营|天台|户外|野餐|徒步|登山|自驾|慢生活/.test(hay)) {
            pool = THEME_IMAGE_POOLS.market_outdoor;
          } else if (/潮玩|星星人|漫展|acg|科技|极客|车展|数码|vr|黑科技/.test(hay)) {
            pool = THEME_IMAGE_POOLS.tech_pop;
          } else if (/银行|立减金|消费券|数币|红包|1分钱|乘车码|补贴|免费券|省钱|体育券/.test(hay)) {
            pool = THEME_IMAGE_POOLS.finance_perks;
          } else if (/动物园|红山|菊花|红叶|秋季|森林|水杉|湿地|公园|湖熟/.test(hay)) {
            pool = THEME_IMAGE_POOLS.nature_park;
          } else if (item.category === '南京展会') {
            pool = THEME_IMAGE_POOLS.art;
          } else if (item.category === '羊毛福利') {
            pool = THEME_IMAGE_POOLS.finance_perks;
          }

          return pool[hash % pool.length];
        }

        const categoryOptions = [
          { value: 'ALL', label: '全部' },
          { value: '南京展会', label: '展会' },
          { value: '南京活动', label: '活动' },
          { value: '羊毛福利', label: '福利' }
        ];

        const hasActiveFilter = computed(() => {
          return selectedDistrict.value !== 'ALL' || radiusFilter.value > 0 || freeOnly.value || timeFilter.value !== 'ALL' || venueFilter.value !== 'ALL';
        });

        function resetFilters() {
          selectedDistrict.value = 'ALL';
          radiusFilter.value = 0;
          freeOnly.value = false;
          timeFilter.value = 'ALL';
          venueFilter.value = 'ALL';
          boundsFilterEnabled.value = false;
          showFavoritesOnly.value = false;
        }

                function getMarkerShortName(title) {
          if (!title) return '精选活动';
          let clean = title.trim();

          // 1. 去除括号、书名号、引号
          clean = clean.replace(/【.*?】|\[.*?\]|（.*?）|\(.*?\)|《.*?》|“.*?”|”|‘|’/g, ' ').trim();

          // 2. 经典地标/场馆优先匹配 (避免将场馆截断)
          const LANDMARKS = [
            '德基广场', '江苏省美术馆', '红山动物园', '老门东', '夫子庙', 
            '熙南里', '金陵STYLE', '牛首山', '华采天地', '江苏大剧院', 
            '南京眼', '玄武湖', '鸡鸣寺', '珍珠泉', '水墨大埝', '老山森林', 
            '金鹰世界', '龙江新城市', '南京博览中心', '南京市博', '江宁织造'
          ];
          for (const lm of LANDMARKS) {
            if (clean.includes(lm)) {
              return lm;
            }
          }

          // 3. 识别前缀并跳过情绪营销词 (治愈暴击|、重磅官宣！、人机battle！等)
          const sepMatch = clean.match(/^([^\s|｜:：!！·]{2,10})[|｜:：!！·]\s*(.+)$/);
          if (sepMatch) {
            const p = sepMatch[1].trim();
            const rem = sepMatch[2].trim();
            if (/暴击|必看|重磅|速领|快抢|周末|震撼|免票|官宣|合集|推荐|打卡|绝美|全部|福利/.test(p) && rem.length >= 2) {
              clean = rem;
            } else if (/battle/i.test(p)) {
              clean = rem.length >= 2 ? rem : p.replace(/battle/i, '');
            } else if (rem.length >= 3 && rem.length <= 12) {
              clean = rem;
            } else {
              clean = p;
            }
          }

          // 4. 去除无实质意义的通用营销修饰与前缀
          clean = clean.replace(/^(?:2026年?|2025年?|南京市?|华东|首届|第[一二三四五六七八九十0-9]+届|中国(?:\(南京\))?)/g, '').trim();
          clean = clean.replace(/APP/gi, '').trim();

          // 5. 精准核心词汇识别
          if (clean.includes('星星人')) return '星星人展';
          if (clean.includes('苏韵华章')) return '苏韵华章展';
          if (clean.includes('水墨画')) return '水墨双年展';
          if (clean.includes('新能源汽车') || clean.includes('车展')) return '新能源车展';
          if (clean.includes('ACG') || clean.includes('动漫')) return 'ACG动漫节';
          if (clean.includes('珠宝')) return '国际珠宝展';
          if (clean.includes('菊花')) return '湖熟菊花节';
          if (clean.includes('红叶')) return '栖霞红叶节';
          if (clean.includes('建行') || clean.includes('建设银行')) return '建行商圈立减';
          if (clean.includes('工行') || clean.includes('工商银行')) return '工行乘车立减';
          if (clean.includes('农行') || clean.includes('农业银行')) return '农行数币红包';
          if (clean.includes('我的南京') || clean.includes('宁体汇')) return '我的南京体育券';
          if (clean.includes('云闪付')) return '云闪付消费券';
          if (clean.includes('支付宝') || clean.includes('骑行')) return '支付宝骑行周卡';
          if (clean.includes('阅江楼')) return '阅江楼登高节';
          if (clean.includes('颐和路')) return '颐和路漫步';
          if (clean.includes('天生桥') || clean.includes('打铁花')) return '天生桥打铁花';
          if (clean.includes('螃蟹') || clean.includes('固城湖')) return '固城湖螃蟹节';
          if (clean.includes('慢城')) return '高淳慢城自驾';
          if (clean.includes('浦口火车站') || clean.includes('百年复古')) return '浦口复古市集';
          if (clean.includes('数字艺术') || clean.includes('沉浸式')) return '数字艺术展';
          if (clean.includes('雨花茶') || clean.includes('非遗')) return '雨花茶非遗展';
          if (clean.includes('旧书') || clean.includes('盲盒')) return '旧书盲盒市集';
          if (clean.includes('排期表') || clean.includes('展会排期')) return '10月展讯排期';

          // 6. 截取首部，避免截断英语单词或汉字词组
          clean = clean.split(/[|｜:：!！·]/)[0].trim();
          if (clean.length > 8) {
            let sub = clean.slice(0, 8);
            if (clean[7] && clean[7].match(/[a-zA-Z]/) && clean[8] && clean[8].match(/[a-zA-Z]/)) {
              const alphaMatch = sub.match(/[a-zA-Z]+$/);
              if (alphaMatch && alphaMatch.index >= 2) {
                sub = sub.slice(0, alphaMatch.index);
              }
            }
            clean = sub;
          }
          return clean.trim() || '同城活动';
        }

        function getMarkerPriceLabel(item) {
          if (item.is_free) return '免票';
          const b = item.benefit || '';
          if (b.includes('免费') || b.includes('免票')) return '免票';
          if (b.includes('立减')) return '立减';
          if (b.includes('消费券')) return '领券';
          if (b.includes('打卡') || b.includes('赠')) return '礼遇';
          if (b.includes('福利') || b.includes('羊毛')) return '福利';
          return '精选';
        }

        function getStatusInfo(item) {
          const t = item.event_time_text || '';
          if (t.includes('10.22') || t.includes('10-22') || t.includes('今') || t.includes('剩3天')) {
            return {
              label: '进行中 · 剩3天',
              bg: 'bg-amber-50 text-amber-800 border-amber-200/50'
            };
          }
          if (t.includes('周末') || t.includes('周六') || t.includes('周日')) {
            return {
              label: '本周末特惠',
              bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/50'
            };
          }
          if (t.includes('长期') || t.includes('10月') || t.includes('剩9天')) {
            return {
              label: '火热进行中',
              bg: 'bg-blue-50 text-blue-800 border-blue-200/50'
            };
          }
          return {
            label: '近期有效',
            bg: 'bg-slate-100 text-slate-700 border-black/[0.04]'
          };
        }

        function getDaysRemainingScore(item) {
          const text = (item.event_time_text + ' ' + item.title).toLowerCase();
          if (text.includes('10.22') || text.includes('今日') || text.includes('剩1天')) return 1;
          if (text.includes('10.23') || text.includes('剩3天')) return 2;
          if (text.includes('周末') || text.includes('10.25')) return 3;
          if (text.includes('10.31') || text.includes('剩9天')) return 4;
          return 10;
        }

        function isFavorite(id) {
          return favoriteIds.value.includes(id);
        }

        function toggleFavorite(item) {
          const idx = favoriteIds.value.indexOf(item.id);
          if (idx >= 0) {
            favoriteIds.value.splice(idx, 1);
          } else {
            favoriteIds.value.push(item.id);
          }
          localStorage.setItem('nanjing_favorites', JSON.stringify(favoriteIds.value));
        }

        function copyAddress(address) {
          if (!address) return;
          navigator.clipboard.writeText(address);
          copiedAddress.value = true;
          setTimeout(() => { copiedAddress.value = false; }, 2000);
        }

        function toggleBoundsFilter() {
          boundsFilterEnabled.value = !boundsFilterEnabled.value;
          if (boundsFilterEnabled.value && leafletMap) {
            mapBounds.value = leafletMap.getBounds();
          }
        }

        const filteredEvents = computed(() => {
          let list = events.value.filter(it => {
            if (!it || !it.id || !it.title || !it.title.trim()) return false;
            if (showFavoritesOnly.value && !isFavorite(it.id)) return false;
            if (activeCategory.value !== 'ALL' && it.category !== activeCategory.value) return false;
            
            const isOnline = isOnlineEvent(it);
            if (venueFilter.value === 'PHYSICAL' && isOnline) return false;
            if (venueFilter.value === 'ONLINE' && !isOnline) return false;

            if (boundsFilterEnabled.value && !isOnline && mapBounds.value && venueFilter.value !== 'ONLINE') {
              if (!mapBounds.value.contains([it.lat, it.lng])) return false;
            }

            if (selectedDistrict.value !== 'ALL' && it.district !== selectedDistrict.value) return false;
            if (freeOnly.value && !it.is_free) return false;
            if (radiusFilter.value > 0 && it.distance_km > radiusFilter.value) return false;

            if (timeFilter.value === 'TODAY') {
              const status = getStatusInfo(it);
              if (!status.label.includes('进行中') && !it.event_time_text.includes('10.22')) return false;
            } else if (timeFilter.value === 'WEEKEND') {
              const status = getStatusInfo(it);
              if (!status.label.includes('周末') && !it.event_time_text.includes('周末')) return false;
            } else if (timeFilter.value === 'EXPIRING') {
              const status = getStatusInfo(it);
              if (!status.label.includes('剩')) return false;
            }

                      if (selectedCalendarDate.value) {
              const targetIso = selectedCalendarDate.value;
              if (it.start_date && it.end_date) {
                if (!(it.start_date <= targetIso && targetIso <= it.end_date)) return false;
              }
            }

            if (searchQuery.value) {
              const q = searchQuery.value.toLowerCase();
              const hay = [it.title, it.category, it.district, it.address, it.benefit].join(' ').toLowerCase();
              if (!hay.includes(q)) return false;
            }
            return true;
          });

          // 去重清洗
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

          // 多维排序（默认距离最近优先，彻底解决 83km 高淳活动霸占榜首问题）
          let result = [];
          if (showFavoritesOnly.value) {
            result = uniqueList.sort((a, b) => getDaysRemainingScore(a) - getDaysRemainingScore(b));
          } else if (sortMode.value === 'distance') {
            result = uniqueList.sort((a, b) => a.distance_km - b.distance_km);
          } else if (sortMode.value === 'expiring') {
            result = uniqueList.sort((a, b) => getDaysRemainingScore(a) - getDaysRemainingScore(b));
          } else if (sortMode.value === 'latest') {
            result = uniqueList.sort((a, b) => new Date(b.publish_date || '2026-10-01') - new Date(a.publish_date || '2026-10-01'));
          } else {
            result = uniqueList.sort((a, b) => a.distance_km - b.distance_km);
          }
          return result;
        });

        // ⏱️ 时间轴视图 4 大吸顶分组 (Sticky Timeline Groups)
        const timelineGroups = computed(() => {
          const list = filteredEvents.value;
          const todayIso = '2026-10-23';

          const focusItems = [];     // 1. 今日与本周末焦点
          const expiringItems = [];  // 2. 即将截止 (7天内结束)
          const upcomingItems = [];  // 3. 近期即将开始 (未开展预告)
          const longtermItems = [];  // 4. 跨月长线活动 (展期 > 30天)

          list.forEach(item => {
            const sDate = item.start_date || '2026-10-01';
            const eDate = item.end_date || '2026-10-31';
            const daysLeft = item.days_left != null ? item.days_left : getDaysRemainingScore(item);
            const timeText = item.event_time_text || '';

            const startObj = new Date(sDate);
            const endObj = new Date(eDate);
            const durationDays = Math.round((endObj - startObj) / (86400000));

            // 未开展预告
            if (sDate > todayIso && !timeText.includes('进行中')) {
              upcomingItems.push(item);
              return;
            }

            // 今日/本周末焦点
            const isTodayWeekend = (
              timeText.includes('今日') || 
              timeText.includes('10.23') ||
              timeText.includes('周末') || 
              timeText.includes('周六') || 
              timeText.includes('周日') ||
              daysLeft <= 2
            );

            if (isTodayWeekend) {
              focusItems.push(item);
              return;
            }

            // 即将截止 (7天内结束)
            if (daysLeft > 0 && daysLeft <= 7) {
              expiringItems.push(item);
              return;
            }

            // 跨月长线常设活动 (展期 > 30天)
            if (durationDays >= 30 || timeText.includes('常设') || timeText.includes('长期')) {
              longtermItems.push(item);
              return;
            }

            if (daysLeft <= 14) {
              expiringItems.push(item);
            } else {
              longtermItems.push(item);
            }
          });

          return [
            {
              id: 'focus',
              title: '近期焦点',
              desc: '',
              items: focusItems,
              dotColor: 'bg-[#FF3B30]',
              nodeColor: 'bg-[#FF3B30]',
              badgeClass: 'bg-red-50 text-red-700 border border-red-200/50'
            },
            {
              id: 'expiring',
              title: '即将结束',
              desc: '',
              items: expiringItems,
              dotColor: 'bg-[#FF9500]',
              nodeColor: 'bg-[#FF9500]',
              badgeClass: 'bg-amber-50 text-amber-800 border border-amber-200/50'
            },
            {
              id: 'upcoming',
              title: '即将开始',
              desc: '',
              items: upcomingItems,
              dotColor: 'bg-[#007AFF]',
              nodeColor: 'bg-[#007AFF]',
              badgeClass: 'bg-blue-50 text-blue-700 border border-blue-200/50'
            },
            {
              id: 'longterm',
              title: '常设展览',
              desc: '',
              items: longtermItems,
              dotColor: 'bg-[#34C759]',
              nodeColor: 'bg-[#34C759]',
              badgeClass: 'bg-emerald-50 text-emerald-800 border border-emerald-200/50'
            }
          ].filter(g => g.items.length > 0);
        });

        const timeStats = computed(() => {
          let ongoing = 0, expiring = 0, upcoming = 0;
          const total = filteredEvents.value.length || 1;
          filteredEvents.value.forEach(it => {
            const status = getStatusInfo(it).label;
            if (status.includes('剩3天') || status.includes('本周末')) expiring++;
            else if (status.includes('剩9天') || status.includes('进行中') || status.includes('火热')) ongoing++;
            else upcoming++;
          });
          return {
            ongoing, expiring, upcoming,
            ongoingPercent: Math.round((ongoing / total) * 100),
            expiringPercent: Math.round((expiring / total) * 100),
            upcomingPercent: Math.round((upcoming / total) * 100)
          };
        });

        function escapeHtml(str) {
          if (str == null) return '';
          return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
        }

        function getMarkerDotColor(category) {
          if (category === '南京展会') return '#FF9500';
          if (category === '羊毛福利') return '#34C759';
          return '#007AFF';
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

          if (mapStyleMode.value === 'dark') {
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
            baseTileLayer = L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
              subdomains: ['1', '2', '3', '4'],
              maxZoom: 18,
              minZoom: 9
            }).addTo(leafletMap);
          }
        }

        function toggleHeatmap() {
          showHeatmap.value = !showHeatmap.value;
          if (!leafletMap) return;

          if (heatLayer) {
            leafletMap.removeLayer(heatLayer);
            heatLayer = null;
          }

          if (showHeatmap.value && typeof L.heatLayer === 'function') {
            const heatPoints = filteredEvents.value.map(it => [it.lat, it.lng, 0.85]);
            heatLayer = L.heatLayer(heatPoints, {
              radius: 35,
              blur: 25,
              maxZoom: 15,
              gradient: {
                0.2: '#007AFF',
                0.5: '#34C759',
                0.8: '#FF9500',
                1.0: '#FF3B30'
              }
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
            activeZoneLabel.value = '全城';
            leafletMap.flyTo([XINJIEKOU[1], XINJIEKOU[0]], 12, {
              duration: 0.8,
              easeLinearity: 0.25
            });
          }
        }

        function teleportToZone(zone) {
          activeZoneLabel.value = zone.label;
          if (leafletMap) {
            leafletMap.flyTo([zone.coords[1], zone.coords[0]], zone.zoom, {
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

                // 持久化 MarkerMap (0 DOM 重建，仅 Diff 更新)
        const markerMap = new Map();

        function syncMarkers() {
          if (!leafletMap || !leafletMarkersGroup) return;

          const currentList = filteredEvents.value;
          const newIds = new Set(currentList.map(it => it.id));

          // 1. 删除离开可视列表的 Marker
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
            const shortName = escapeHtml(item.short_title || getMarkerShortName(item.title));
            const priceLabel = escapeHtml(getMarkerPriceLabel(item));
            const safeTitle = escapeHtml(item.title);
            const safeId = escapeHtml(item.id);

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
            if (el) el.classList.remove('active');
          }

          if (newId && markerMap.has(newId)) {
            const newMarker = markerMap.get(newId);
            newMarker.setZIndexOffset(1000);
            const el = newMarker.getElement();
            if (el) el.classList.add('active');
          }
        });


        function flyToWithOffset(lat, lng, zoom = 15) {
          if (!leafletMap) return;
          const isDesktop = window.innerWidth >= 768;
          const targetZoom = zoom || leafletMap.getZoom();
          const pt = leafletMap.project([lat, lng], targetZoom);
          let offsetX = 0, offsetY = 0;
          if (isDesktop && drawerOpen.value) {
            offsetX = 210;
          } else if (!isDesktop && drawerOpen.value) {
            offsetY = window.innerHeight * 0.25;
          }
          const offsetPt = L.point(pt.x + offsetX, pt.y + offsetY);
          const centerLatLng = leafletMap.unproject(offsetPt, targetZoom);
          leafletMap.flyTo(centerLatLng, targetZoom, { duration: 0.8, easeLinearity: 0.25 });
        }

        function focusEvent(item) {
          activeEventId.value = item.id;
          flyToWithOffset(item.lat, item.lng, 15);
        }

        function openDetail(item) {
          activeEventId.value = item.id;
          detailItem.value = item;
          flyToWithOffset(item.lat, item.lng, 15);
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

        function openStatsModal() {
          showStatsModal.value = true;
          nextTick(() => {
            initECharts();
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

        function initECharts() {
          const distEl = document.getElementById('district-chart');
          const catEl = document.getElementById('category-chart');
          if (!distEl || !catEl || typeof echarts === 'undefined') return;

          const districtCounts = {};
          districts.forEach(d => { districtCounts[d] = 0; });
          filteredEvents.value.forEach(it => {
            if (districtCounts[it.district] !== undefined) districtCounts[it.district]++;
          });

          if (districtChartInstance) districtChartInstance.dispose();
          districtChartInstance = echarts.init(distEl);
          districtChartInstance.setOption({
            tooltip: { trigger: 'axis' },
            grid: { top: 20, right: 15, bottom: 25, left: 35 },
            xAxis: {
              type: 'category',
              data: Object.keys(districtCounts).map(d => d.replace('区', '')),
              axisLabel: { color: '#64748b', fontSize: 10, interval: 0 }
            },
            yAxis: { type: 'value', minInterval: 1 },
            series: [{
              type: 'bar',
              data: Object.values(districtCounts),
              barWidth: 14,
              itemStyle: {
                borderRadius: [6, 6, 0, 0],
                color: '#007AFF'
              }
            }]
          });

          const catCounts = { '南京展会': 0, '南京活动': 0, '羊毛福利': 0 };
          filteredEvents.value.forEach(it => {
            if (catCounts[it.category] !== undefined) catCounts[it.category]++;
          });

          if (categoryChartInstance) categoryChartInstance.dispose();
          categoryChartInstance = echarts.init(catEl);
          categoryChartInstance.setOption({
            tooltip: { trigger: 'item' },
            legend: { bottom: 0, icon: 'circle', textStyle: { fontSize: 11 } },
            series: [{
              type: 'pie',
              radius: ['45%', '72%'],
              center: ['50%', '45%'],
              itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
              label: { show: false },
              data: [
                { value: catCounts['南京展会'], name: '南京展会', itemStyle: { color: '#FF9500' } },
                { value: catCounts['南京活动'], name: '南京活动', itemStyle: { color: '#007AFF' } },
                { value: catCounts['羊毛福利'], name: '羊毛福利', itemStyle: { color: '#34C759' } }
              ]
            }]
          });
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
          events.value = INITIAL_EVENTS.map(normalize);
          nextTick(() => { syncMarkers(); });
        }

        watch(filteredEvents, () => {
          syncMarkers();
          if (showHeatmap.value && leafletMap && typeof L.heatLayer === 'function') {
            if (heatLayer) leafletMap.removeLayer(heatLayer);
            const heatPoints = filteredEvents.value.map(it => [it.lat, it.lng, 0.85]);
            heatLayer = L.heatLayer(heatPoints, {
              radius: 35,
              blur: 25,
              maxZoom: 15,
              gradient: { 0.2: '#007AFF', 0.5: '#34C759', 0.8: '#FF9500', 1.0: '#FF3B30' }
            }).addTo(leafletMap);
          }
        });

        window.addEventListener('keydown', (e) => {
          if (e.key === 'Escape') {
            if (detailItem.value) closeDetail();
            if (showStatsModal.value) closeStatsModal();
          }
        });

        onMounted(() => {
          loadData();
          nextTick(() => {
            initMap();
          });
        });

        return {
          events,
          filteredEvents,
          categoryOptions,
          activeCategory,
          venueFilter,
          boundsFilterEnabled,
          timeFilter,
          timeFilterOptions,
          zoneTeleports,
          activeZoneLabel,
          districts,
          selectedDistrict,
          radiusFilter,
          freeOnly,
          showFavoritesOnly,
          favoriteIds,
          isFavorite,
          toggleFavorite,
          copyAddress,
          copiedAddress,
                    toggleBoundsFilter,
          currentViewMode,
          sortMode,
          selectedCalendarDate,
          calendarDays,
          selectCalendarDay,
          timelineGroups,
          hasActiveFilter,
          searchQuery,
          activeEventId,
          detailItem,
          drawerOpen,
          isSyncing,
          showFilterPopover,
          showRings,
          showHeatmap,
          showStatsModal,
          mapStyleMode,
          mapModes,
          timeStats,
          getMarkerDotColor,
          getMarkerShortName,
          getMarkerPriceLabel,
          getStatusInfo,
          getEventCover,
          focusEvent,
          openDetail,
          closeDetail,
          openStatsModal,
          closeStatsModal,
          triggerSync,
          resetFilters,
          setMapMode,
          toggleRings,
          toggleHeatmap,
          recenterMap,
          teleportToZone,
          onDistrictChange
        };
      }
    }).mount('#app');
  </script>
</body>
</html>
"""

def main():
    content = HTML_CONTENT.replace("__INITIAL_EVENTS__", fallback_json)
    OUT_HTML.write_text(content, encoding="utf-8")
    print(f"Full-Featured Gaode Spatial Studio generated: {OUT_HTML} ({len(content)} bytes)")

if __name__ == "__main__":
    main()
