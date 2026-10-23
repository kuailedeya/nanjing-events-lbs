<template>
  <div class="py-16 px-6 flex flex-col items-center justify-center text-center animate-in fade-in duration-300">
    <!-- unDraw / Apple HIG 风格空间探索矢量插画 -->
    <div class="relative w-44 h-36 mb-5 select-none pointer-events-none">
      <svg class="w-full h-full" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <!-- 柔和背景圆弧雷达基底 -->
        <circle cx="100" cy="80" r="72" fill="#007AFF" fill-opacity="0.04" />
        <circle cx="100" cy="80" r="50" stroke="#007AFF" stroke-opacity="0.1" stroke-width="1.5" stroke-dasharray="3 3" />
        <circle cx="100" cy="80" r="28" stroke="#007AFF" stroke-opacity="0.18" stroke-width="1.5" />
        
        <!-- 空间经纬十字线 -->
        <line x1="100" y1="12" x2="100" y2="148" stroke="#007AFF" stroke-opacity="0.08" stroke-width="1" />
        <line x1="32" y1="80" x2="168" y2="80" stroke="#007AFF" stroke-opacity="0.08" stroke-width="1" />

        <template v-if="isFavoritesMode">
          <!-- 收藏夹为空插画：发光的 Apple 待去星标与书签卡片 -->
          <rect x="68" y="44" width="64" height="76" rx="14" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1.5" />
          <path d="M78 58h44M78 70h30M78 82h38" stroke="#CBD5E1" stroke-width="2" stroke-linecap="round" />
          <circle cx="120" cy="100" r="18" fill="#FFFBEB" stroke="#FDE68A" stroke-width="1.5" />
          <path d="M120 92.5l2.3 4.7 5.2.8-3.8 3.7.9 5.2-4.6-2.4-4.6 2.4.9-5.2-3.8-3.7 5.2-.8 2.3-4.7z" fill="#F59E0B" />
        </template>

        <template v-else>
          <!-- 搜索/筛选无结果插画：放大镜与空间点位折线 -->
          <circle cx="86" cy="66" r="28" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2" />
          <circle cx="86" cy="66" r="21" fill="#F8FAFC" />
          <path d="M86 52a14 14 0 0 1 14 14" stroke="#007AFF" stroke-width="2" stroke-linecap="round" />
          <path d="M106 86l24 24" stroke="#64748B" stroke-width="4" stroke-linecap="round" />
          <circle cx="145" cy="52" r="4.5" fill="#007AFF" />
          <circle cx="55" cy="105" r="3.5" fill="#34C759" />
          <circle cx="140" cy="115" r="3" fill="#FF9500" />
        </template>
      </svg>
    </div>

    <!-- 主标题与副文案 -->
    <h3 class="text-sm font-semibold text-slate-800 tracking-tight mb-1.5">
      {{ isFavoritesMode ? '待去清单暂无活动' : '未找到相关同城活动' }}
    </h3>
    <p class="text-xs text-slate-400 max-w-[240px] leading-relaxed mb-4">
      {{ isFavoritesMode ? '浏览地图精选列表，点击卡片底部的「待去」按钮即可收藏' : '尝试调整搜索关键词，或重置当前分类与时态过滤条件' }}
    </p>

    <!-- 快捷恢复按钮 -->
    <button
      @click="$emit('reset')"
      class="px-4 py-1.5 rounded-full text-xs font-medium bg-slate-900 hover:bg-slate-800 text-white shadow-sm transition-all duration-200 cursor-pointer active:scale-95 flex items-center gap-1.5"
    >
      <RefreshCw class="w-3 h-3 text-slate-300" />
      <span>{{ isFavoritesMode ? '查看全部活动' : '清除全部筛选' }}</span>
    </button>
  </div>
</template>

<script setup>
import { RefreshCw } from 'lucide-vue-next';

defineProps({
  isFavoritesMode: {
    type: Boolean,
    default: false
  }
});

defineEmits(['reset']);
</script>
