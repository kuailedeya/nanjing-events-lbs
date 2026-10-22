#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Airbnb / Apple Maps Spatial Exploration Layout for Nanjing Events LBS.
Features:
- Pure Apple Minimalist Design (macOS Sonoma & Airbnb Aesthetics)
- Right Floating Drawer: bg-[#F5F5F7]/85, backdrop-blur-2xl, rounded-[28px], border border-white/80, shadow-[0_20px_50px_rgba(0,0,0,0.1)]
- Top Floating Island: top-6 left-6, rounded-[22px], detached from edges, highly translucent
- Bento Grid Cards: rounded-2xl, cover image rounded-xl, font-semibold text-slate-900
- 1. Rich Map Capsule Markers: [彩色圆点 + 6字精简活动名 + 价格/免票标签]
- 2. Card Status Badges & Online/Physical Separation
- 3. Core District Teleport & Time Filtering
- 4. Secondary Activity Detail Sheet
- 5. Wishlist / Favorites & Heatmap Layer
"""

import json
from pathlib import Path
import dashboard_server

OUT_HTML = Path(r"E:\usage\dashboard.html")

items = dashboard_server.get_all_events()
fallback_json = json.dumps(items, ensure_ascii=False)

HTML_CONTENT = """<!DOCTYPE html>
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

    .amap-dark-filter .leaflet-tile {
      filter: invert(100%) hue-rotate(180deg) brightness(88%) contrast(95%) !important;
    }

    .apple-marker {
      transform: translate(-50%, -100%);
      transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform;
      white-space: nowrap !important;
    }
    .apple-marker:hover {
      transform: translate(-50%, -108%) scale(1.08);
      z-index: 50 !important;
    }
    .apple-marker.active {
      transform: translate(-50%, -114%) scale(1.15);
      z-index: 60 !important;
    }
    .apple-marker.active .marker-pill {
      background-color: #0f172a !important;
      color: #ffffff !important;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.35), 0 4px 10px rgba(15, 23, 42, 0.2) !important;
      border-color: #0f172a !important;
    }
    .apple-marker.active .marker-name {
      color: #ffffff !important;
    }
    .apple-marker.active .marker-divider {
      color: rgba(255, 255, 255, 0.3) !important;
    }
    .apple-marker.active .marker-price {
      color: #34C759 !important;
    }
    .apple-marker.active .marker-dot {
      background-color: #ffffff !important;
    }

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
</head>
<body class="h-full w-full overflow-hidden bg-[#F5F5F7] select-none text-slate-900">
  <div id="app" class="relative w-screen h-screen overflow-hidden font-sans antialiased">

    <!-- 1. 全屏底图底层 (高德官方全量图源，原生 GCJ-02 火星坐标) -->
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
    <header class="absolute top-6 left-6 z-20 pointer-events-auto max-w-[760px] flex flex-col gap-2.5">
      <div class="bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.08),0_1px_3px_rgba(0,0,0,0.03)] border border-white/80 p-2 sm:p-2.5 flex items-center gap-2.5 transition-all">
        
        <!-- 搜索框 -->
        <div class="flex-1 relative flex items-center min-w-[180px]">
          <svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
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
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <!-- 类别滑动胶囊分段器 -->
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

        <!-- 线上/线下实体场馆独立切换 -->
        <div class="flex items-center p-1 bg-black/[0.04] rounded-xl text-xs font-medium text-slate-600 shrink-0">
          <button
            @click="venueFilter = 'ALL'"
            :class="[
              'px-2.5 py-1 rounded-lg transition-all text-xs cursor-pointer',
              venueFilter === 'ALL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="查看全部同城内容"
          >
            全览
          </button>
          <button
            @click="venueFilter = 'PHYSICAL'"
            :class="[
              'px-2.5 py-1 rounded-lg transition-all text-xs cursor-pointer flex items-center gap-1',
              venueFilter === 'PHYSICAL' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-500 hover:text-slate-900'
            ]"
            title="仅看有物理场馆定位的线下活动，剔除线上银行羊毛堆叠"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-[#007AFF]"></span>
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
            <span class="w-1.5 h-1.5 rounded-full bg-[#34C759]"></span>
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
            'p-2 rounded-xl transition-all cursor-pointer relative shrink-0',
            hasActiveFilter ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:bg-black/[0.04]'
          ]"
          title="筛选范围与时间维度"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>
          </svg>
          <span v-if="hasActiveFilter" class="w-1.5 h-1.5 rounded-full bg-[#34C759] absolute top-1.5 right-1.5"></span>
        </button>

        <!-- 增量同步 -->
        <button
          @click="triggerSync"
          :disabled="isSyncing"
          class="p-2 rounded-xl text-slate-600 hover:bg-black/[0.04] transition-all cursor-pointer shrink-0"
          title="增量同步最新社媒情报"
        >
          <svg :class="['w-4 h-4', isSyncing ? 'animate-spin text-[#007AFF]' : '']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
          </svg>
        </button>

      </div>

      <!-- 南京核心片区瞬移胶囊栏 -->
      <div class="bg-white/70 backdrop-blur-xl rounded-[18px] p-1.5 shadow-[0_8px_24px_rgba(0,0,0,0.06)] border border-white/70 flex items-center gap-1 overflow-x-auto no-scrollbar">
        <span class="text-[11px] font-semibold text-slate-400 px-2 shrink-0">片区瞬移:</span>
        <button
          v-for="zone in zoneTeleports"
          :key="zone.label"
          @click="teleportToZone(zone)"
          :class="[
            'px-2.5 py-1 rounded-xl text-xs font-medium transition-all cursor-pointer whitespace-nowrap shrink-0',
            activeZoneLabel === zone.label
              ? 'bg-slate-900 text-white shadow-xs font-semibold'
              : 'text-slate-600 hover:bg-black/[0.04] hover:text-slate-900'
          ]"
        >
          {{ zone.label }}
        </button>
      </div>

      <!-- 下拉微质感 Popover 筛选器 (含时间维度与区域微调) -->
      <div
        v-if="showFilterPopover"
        class="p-3.5 bg-white/90 backdrop-blur-2xl backdrop-saturate-150 rounded-[22px] shadow-[0_20px_50px_rgba(0,0,0,0.12)] border border-white/80 flex items-center gap-3 text-xs animate-in fade-in slide-in-from-top-2 duration-200 flex-wrap"
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

      <!-- 🔥 活动热力分布图开关 -->
      <button
        @click="toggleHeatmap"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showHeatmap ? 'bg-orange-600 text-white border-orange-600 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
        title="在地图上叠加活动密度热力分布图"
      >
        <span class="w-2 h-2 rounded-full" :class="showHeatmap ? 'bg-white' : 'bg-orange-500'"></span>
        <span>热力分布</span>
      </button>

      <!-- 新街口中心辐射同心圈切换 -->
      <button
        @click="toggleRings"
        :class="[
          'px-3 py-2 bg-white/80 backdrop-blur-2xl backdrop-saturate-150 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.9)] border border-white/80 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer',
          showRings ? 'bg-slate-950 text-white border-slate-950 shadow-md' : 'text-slate-700 hover:bg-white'
        ]"
        title="在地图上显示新街口 3km/5km/10km 辐射同心圈"
      >
        <span class="w-3.5 h-3.5 flex items-center justify-center font-bold" :class="showRings ? 'text-[#34C759]' : 'text-slate-400'">◎</span>
        <span>辐射圈</span>
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
            <span v-if="showFavoritesOnly" class="text-[11px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200/50">待去清单模式</span>
          </div>

          <button
            @click="drawerOpen = !drawerOpen"
            class="w-7 h-7 rounded-lg bg-white/70 hover:bg-white text-slate-500 hover:text-slate-900 flex items-center justify-center transition shadow-sm cursor-pointer"
            :title="drawerOpen ? '收起抽屉' : '展开抽屉'"
          >
            <svg :class="['w-4 h-4 transition-transform duration-200', drawerOpen ? 'rotate-0' : 'rotate-180']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
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
            <!-- Bento 封面图 -->
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

              <!-- 悬浮在封面右上方的待去清单星标 -->
              <button
                @click.stop="toggleFavorite(item)"
                class="absolute top-2.5 right-2.5 p-1.5 rounded-full backdrop-blur-md transition-all cursor-pointer shadow-sm"
                :class="isFavorited(item.id) ? 'bg-amber-500 text-white' : 'bg-black/40 text-white/80 hover:bg-black/60 hover:text-white'"
                :title="isFavorited(item.id) ? '从待去清单移除' : '加入待去清单'"
              >
                <svg class="w-3.5 h-3.5" :class="isFavorited(item.id) ? 'fill-white' : ''" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
              </button>

              <!-- 悬浮在封面左下方的免票/福利徽标 -->
              <span class="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded-lg text-[11px] font-medium tracking-tight backdrop-blur-md bg-white/90 text-slate-800 flex items-center gap-1">
                <span class="font-semibold text-[#34C759]" v-if="item.is_free">免票直入</span>
                <span class="text-slate-700 font-medium" v-else>{{ item.benefit }}</span>
              </span>

              <!-- 封面右下角距离标签 -->
              <span class="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded-lg text-[11px] font-medium tracking-tight backdrop-blur-md bg-black/60 text-white tabular-nums">
                {{ item.distance_km }} km
              </span>
            </div>

            <!-- 结构化时态徽标行 -->
            <div class="flex items-center gap-1.5 mb-1.5">
              <span
                :class="[
                  'px-2 py-0.5 rounded-md text-[10px] font-semibold tracking-tight inline-flex items-center gap-1',
                  getStatusInfo(item).badgeClass
                ]"
              >
                <span class="w-1 h-1 rounded-full" :class="getStatusInfo(item).dotClass"></span>
                <span>{{ getStatusInfo(item).label }}</span>
              </span>

              <span
                v-if="isOnlineEvent(item)"
                class="px-1.5 py-0.5 rounded-md text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/50"
              >
                线上/全城通用
              </span>
            </div>

            <!-- 主标题 (潮流探索排版) -->
            <h3 class="text-sm font-semibold text-slate-900 leading-snug tracking-[-0.01em] group-hover:text-[#007AFF] transition-colors mb-2 line-clamp-2">
              {{ item.title }}
            </h3>

            <!-- 地理与时间元数据行 -->
            <div class="text-xs text-slate-500 space-y-1 mb-3">
              <div class="flex items-center gap-1.5 text-slate-600">
                <svg class="w-3.5 h-3.5 text-slate-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                </svg>
                <span class="truncate font-medium text-slate-800">{{ item.address }}</span>
                <span class="text-slate-300">·</span>
                <span class="shrink-0 text-slate-500 bg-black/[0.03] px-1.5 py-0.5 rounded text-[11px]">{{ item.district }}</span>
              </div>
              <div class="flex items-center gap-1.5 text-slate-400 text-[11px]">
                <svg class="w-3.5 h-3.5 text-slate-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
                <span>{{ item.event_time_text }}</span>
              </div>
            </div>

            <!-- 操作底栏：详情 + 状态核销 + 高德导航 -->
            <div class="pt-2.5 border-t border-black/[0.04] flex items-center justify-between mt-auto">
              <!-- 状态切换胶囊 -->
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

              <div class="flex items-center gap-1">
                <!-- 打开详情卡片抽屉 -->
                <button
                  @click.stop="openDetail(item)"
                  class="text-slate-600 hover:text-slate-900 text-[11px] font-semibold flex items-center gap-1 py-1 px-2 hover:bg-black/[0.04] rounded-lg transition-colors cursor-pointer"
                  title="查看完整图文详情与攻略"
                >
                  <svg class="w-3 h-3 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                  </svg>
                  <span>详情</span>
                </button>

                <!-- 高德原生路线规划导航 -->
                <a
                  :href="getAmapNaviUrl(item)"
                  target="_blank"
                  @click.stop
                  class="text-[#007AFF] hover:underline text-[11px] font-medium flex items-center gap-1 py-1 px-2 hover:bg-blue-50/50 rounded-lg transition-colors"
                  title="调用高德地图进行真实路线规划导航"
                >
                  <svg class="w-3 h-3 text-[#007AFF]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="12 2 19 21 12 17 5 21 12 2"/>
                  </svg>
                  <span>导航</span>
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

    <!-- 5. 活动二级详情抽屉面板 (Liquid Glass Secondary Detail Sheet) -->
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
        class="absolute top-6 right-6 bottom-6 z-30 w-[380px] md:w-[480px] bg-white/90 backdrop-blur-2xl backdrop-saturate-150 rounded-[28px] border border-white/80 shadow-[0_24px_60px_rgba(0,0,0,0.18)] flex flex-col overflow-hidden pointer-events-auto"
      >
        <!-- 详情面板顶部大图 -->
        <div class="relative w-full h-56 bg-slate-100 shrink-0 overflow-hidden">
          <img
            :src="getEventCover(detailItem)"
            :alt="detailItem.title"
            class="w-full h-full object-cover"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-black/20"></div>

          <!-- 关闭按钮 -->
          <button
            @click="detailItem = null"
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
                getStatusInfo(detailItem).badgeClass
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
        <div class="flex-1 overflow-y-auto p-5 space-y-5 no-scrollbar text-xs">
          
          <!-- 核心优惠/权益模块 -->
          <div class="bg-black/[0.03] rounded-2xl p-3.5 border border-black/[0.04] space-y-2">
            <div class="text-[11px] font-semibold text-slate-400">门票与权益说明</div>
            <div class="text-sm font-semibold text-emerald-600 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-[#34C759]"></span>
              <span>{{ detailItem.benefit }}</span>
            </div>
          </div>

          <!-- 时间与具体位置 -->
          <div class="space-y-3">
            <div class="text-[11px] font-semibold text-slate-400">活动时空信息</div>
            
            <div class="flex items-start gap-2.5 text-slate-700">
              <svg class="w-4 h-4 text-slate-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
              <div>
                <div class="font-medium text-slate-900">举办周期与时间</div>
                <div class="text-slate-500 mt-0.5">{{ detailItem.event_time_text }}</div>
              </div>
            </div>

            <div class="flex items-start gap-2.5 text-slate-700">
              <svg class="w-4 h-4 text-slate-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
              </svg>
              <div>
                <div class="font-medium text-slate-900">具体场馆与地址</div>
                <div class="text-slate-500 mt-0.5">{{ detailItem.address }}</div>
                <div class="text-[11px] text-slate-400 font-mono mt-0.5">GCJ-02: {{ detailItem.lng }}, {{ detailItem.lat }}</div>
              </div>
            </div>
          </div>

          <!-- 攻略与详细规则正文 -->
          <div class="space-y-2">
            <div class="text-[11px] font-semibold text-slate-400">活动简介与规则正文</div>
            <div class="text-slate-700 leading-relaxed bg-white rounded-xl p-3.5 border border-black/[0.04] shadow-xs">
              {{ detailItem.description || detailItem.title + '。更多详情请在各官方公众号及线下服务台咨询。' }}
            </div>
          </div>

          <!-- 要点速览 (Key Points) -->
          <div v-if="detailItem.key_points && detailItem.key_points.length" class="space-y-2">
            <div class="text-[11px] font-semibold text-slate-400">情报要点提炼</div>
            <ul class="space-y-1.5 pl-1">
              <li
                v-for="(kp, kpidx) in detailItem.key_points"
                :key="kpidx"
                class="flex items-start gap-2 text-slate-700"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-[#007AFF] mt-1.5 shrink-0"></span>
                <span>{{ kp }}</span>
              </li>
            </ul>
          </div>

        </div>

        <!-- 底部三大高质感操作按钮 -->
        <div class="p-4 border-t border-black/[0.04] bg-white/60 backdrop-blur-md flex items-center gap-2.5">
          <!-- 加入/移出待去清单 -->
          <button
            @click="toggleFavorite(detailItem)"
            :class="[
              'flex-1 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-sm',
              isFavorited(detailItem.id)
                ? 'bg-amber-500 text-white shadow-amber-500/20'
                : 'bg-black/[0.05] hover:bg-black/[0.08] text-slate-800'
            ]"
          >
            <svg class="w-4 h-4" :class="isFavorited(detailItem.id) ? 'fill-white text-white' : 'text-amber-500 fill-amber-500'" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
            <span>{{ isFavorited(detailItem.id) ? '已在清单' : '加入待去' }}</span>
          </button>

          <!-- 高德地图直达导航 -->
          <a
            :href="getAmapNaviUrl(detailItem)"
            target="_blank"
            class="flex-1 py-2.5 rounded-xl text-xs font-semibold bg-[#007AFF] hover:bg-[#0071EB] text-white transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-sm shadow-blue-500/20 text-center"
          >
            <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 19 21 12 17 5 21 12 2"/>
            </svg>
            <span>高德导航</span>
          </a>

          <!-- Obsidian 本地笔记深链 -->
          <a
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
    </transition>

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
      { label: '老门东/秦淮', coords: [118.7981, 32.0112], zoom: 15 },
      { label: '河西/建邺', coords: [118.7327, 32.0045], zoom: 14 },
      { label: '仙林大学城', coords: [118.9189, 32.1065], zoom: 14 },
      { label: '江宁百家湖', coords: [118.8258, 31.9328], zoom: 14 },
    ];

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
        const timeFilter = ref('ALL');
        const selectedDistrict = ref('ALL');
        const radiusFilter = ref(0);
        const freeOnly = ref(false);
        const showFavoritesOnly = ref(false);
        const searchQuery = ref('');
        const activeEventId = ref(null);
        const detailItem = ref(null);
        const drawerOpen = ref(true);
        const isSyncing = ref(false);
        const showFilterPopover = ref(false);
        const showRings = ref(false);
        const showHeatmap = ref(false);
        const mapStyleMode = ref('standard');
        const activeZoneLabel = ref('全城');

        const favoriteIds = ref(JSON.parse(localStorage.getItem('nanjing_favorites') || '[]'));

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

        function getEventCover(item) {
          if (!item) return '';
          if (COVER_MAP[item.id]) return COVER_MAP[item.id];
          if (item.category === '南京展会') return 'https://images.unsplash.com/photo-1518998053901-5348d3961a04?w=600&auto=format&fit=crop&q=80';
          if (item.category === '羊毛福利') return 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=600&auto=format&fit=crop&q=80';
          return 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=80';
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
          showFavoritesOnly.value = false;
        }

        function getAmapNaviUrl(item) {
          return `https://uri.amap.com/marker?position=${item.lng},${item.lat}&name=${encodeURIComponent(item.title)}&coordinate=gaode`;
        }

        function getMarkerShortName(title) {
          if (!title) return '精选活动';
          let clean = title.replace(/【.*?】|\\[.*?\\]|（.*?）|\\(.*?\\)|南京/g, '').trim();
          if (clean.length > 6) return clean.slice(0, 6);
          return clean || '活动';
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
          if (t.includes('10.22') || t.includes('10-22') || t.includes('今')) {
            return {
              label: '进行中 · 剩3天',
              badgeClass: 'bg-amber-50 text-amber-800 border border-amber-200/50',
              dotClass: 'bg-amber-500'
            };
          }
          if (t.includes('周末') || t.includes('周六') || t.includes('周日')) {
            return {
              label: '本周末特惠',
              badgeClass: 'bg-emerald-50 text-emerald-800 border border-emerald-200/50',
              dotClass: 'bg-[#34C759]'
            };
          }
          if (t.includes('长期') || t.includes('10月')) {
            return {
              label: '火热进行中',
              badgeClass: 'bg-blue-50 text-blue-800 border border-blue-200/50',
              dotClass: 'bg-[#007AFF]'
            };
          }
          return {
            label: '近期有效',
            badgeClass: 'bg-slate-100 text-slate-700 border border-black/[0.04]',
            dotClass: 'bg-slate-400'
          };
        }

        function isFavorited(id) {
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

        const filteredEvents = computed(() => {
          return events.value.filter(it => {
            if (showFavoritesOnly.value && !isFavorited(it.id)) return false;
            if (activeCategory.value !== 'ALL' && it.category !== activeCategory.value) return false;
            
            if (venueFilter.value === 'PHYSICAL' && isOnlineEvent(it)) return false;
            if (venueFilter.value === 'ONLINE' && !isOnlineEvent(it)) return false;

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

        function toggleHeatmap() {
          showHeatmap.value = !showHeatmap.value;
          if (!leafletMap) return;

          if (heatLayer) {
            leafletMap.removeLayer(heatLayer);
            heatLayer = null;
          }

          if (showHeatmap.value && typeof L.heatLayer === 'function') {
            const heatPoints = filteredEvents.value.map(it => [it.lat, it.lng, it.is_free ? 0.9 : 0.6]);
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

        function syncMarkers() {
          if (!leafletMap || !leafletMarkersGroup) return;
          leafletMarkersGroup.clearLayers();

          filteredEvents.value.forEach(item => {
            const dotColor = getMarkerDotColor(item.category);
            const shortName = getMarkerShortName(item.title);
            const priceLabel = getMarkerPriceLabel(item);
            const isActive = activeEventId.value === item.id;

            const iconHtml = `
              <div class="apple-marker ${isActive ? 'active' : ''}" id="leaf-marker-${item.id}">
                <div class="marker-pill inline-flex items-center gap-1.5 bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-full shadow-[0_4px_14px_rgba(0,0,0,0.12),0_1px_3px_rgba(0,0,0,0.06)] border border-black/[0.06] hover:scale-105 transition-all duration-200 font-medium text-xs text-slate-800 whitespace-nowrap cursor-pointer">
                  <span class="marker-dot w-2 h-2 rounded-full shrink-0" style="background-color: ${dotColor}"></span>
                  <span class="marker-name font-semibold text-slate-900">${shortName}</span>
                  <span class="marker-divider text-slate-300">|</span>
                  <span class="marker-price text-[11px] font-semibold text-[#34C759]">${priceLabel}</span>
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
              <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; min-width: 180px; padding: 2px;">
                <div style="font-size: 13px; font-weight: 600; color: #0f172a; margin-bottom: 4px; line-height: 1.3;">${item.title}</div>
                <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">${item.address} · ${item.distance_km} km</div>
                <div style="display: flex; gap: 6px;">
                  <a href="${getAmapNaviUrl(item)}" target="_blank" style="flex: 1; text-align: center; background: #007AFF; color: #fff; padding: 4px 8px; border-radius: 8px; font-size: 11px; text-decoration: none; font-weight: 500;">高德导航 ↗</a>
                </div>
              </div>
            `, {
              closeButton: false,
              offset: [0, -18]
            });

            marker.on('click', () => {
              activeEventId.value = item.id;
              openDetail(item);
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

        function openDetail(item) {
          detailItem.value = item;
          focusEvent(item);
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
          events.value = INITIAL_EVENTS.map(normalize);
          nextTick(() => { syncMarkers(); });
        }

        watch(filteredEvents, () => {
          syncMarkers();
          if (showHeatmap.value && leafletMap && typeof L.heatLayer === 'function') {
            if (heatLayer) leafletMap.removeLayer(heatLayer);
            const heatPoints = filteredEvents.value.map(it => [it.lat, it.lng, it.is_free ? 0.9 : 0.6]);
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
        });

        // ESC 键关闭详情面板
        window.addEventListener('keydown', (e) => {
          if (e.key === 'Escape' && detailItem.value) {
            detailItem.value = null;
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
          isFavorited,
          toggleFavorite,
          hasActiveFilter,
          searchQuery,
          activeEventId,
          detailItem,
          drawerOpen,
          isSyncing,
          showFilterPopover,
          showRings,
          showHeatmap,
          mapStyleMode,
          mapModes,
          getMarkerDotColor,
          getMarkerShortName,
          getMarkerPriceLabel,
          getStatusInfo,
          isOnlineEvent,
          getStatusClass,
          getStatusDotClass,
          getAmapNaviUrl,
          getEventCover,
          focusEvent,
          openDetail,
          cycleStatus,
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
