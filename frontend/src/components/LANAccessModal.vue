<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-md animate-in fade-in duration-200"
    role="dialog"
    aria-modal="true"
    aria-label="局域网与移动设备访问指南"
    @click.self="close"
    @keydown.esc="close"
  >
    <div
      class="relative w-full max-w-md bg-[#F5F5F7]/95 backdrop-blur-2xl backdrop-saturate-150 rounded-[28px] border border-white/80 shadow-[0_25px_60px_rgba(0,0,0,0.18)] p-5 sm:p-6 overflow-hidden flex flex-col gap-4 text-slate-900"
    >
      <!-- 头部：标题与关闭按钮 -->
      <div class="flex items-center justify-between pb-3 border-b border-black/[0.05]">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-xl bg-[#007AFF]/10 flex items-center justify-center text-[#007AFF]">
            <Smartphone class="w-4 h-4" />
          </div>
          <div>
            <h3 class="text-sm font-semibold tracking-tight text-slate-900">局域网与手机访问</h3>
            <p class="text-[11px] text-slate-500 font-medium">同一 WiFi 下免输 IP 即刻直达</p>
          </div>
        </div>
        <button
          @click="close"
          class="p-1.5 rounded-full text-slate-400 hover:text-slate-800 hover:bg-black/[0.05] transition-colors cursor-pointer"
          aria-label="关闭弹窗"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- 核心方案 1: 短域名免输 IP (主推) -->
      <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-xs flex flex-col gap-2.5">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
            <Wifi class="w-3.5 h-3.5 text-[#007AFF]" />
            <span>短域名直达 (无需输入 IP)</span>
          </span>
          <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#34C759]/10 text-[#34C759]">
            推荐
          </span>
        </div>

        <div class="flex items-center justify-between gap-2 p-2.5 bg-slate-50 rounded-xl border border-black/[0.04]">
          <div class="flex flex-col min-w-0">
            <span class="font-mono text-sm font-bold text-slate-900 tracking-tight truncate">{{ shortUrl }}</span>
            <span class="text-[10.5px] text-slate-500 font-medium">手机 Safari / Chrome 地址栏直接输入</span>
          </div>
          <button
            @click="copyText(shortUrl, 'short')"
            class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-white hover:bg-slate-100 text-slate-700 border border-black/[0.06] shadow-2xs transition-all cursor-pointer flex items-center gap-1 shrink-0"
          >
            <Check v-if="copiedType === 'short'" class="w-3.5 h-3.5 text-[#34C759]" />
            <Copy v-else class="w-3.5 h-3.5 text-slate-400" />
            <span>{{ copiedType === 'short' ? '已复制' : '复制' }}</span>
          </button>
        </div>

        <!-- 备选短域名胶囊 -->
        <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar pt-1 text-[11px]">
          <span class="text-slate-400 shrink-0">备选:</span>
          <button
            v-for="d in altDomains"
            :key="d"
            @click="copyText(d, d)"
            class="px-2 py-0.5 rounded-md bg-black/[0.03] hover:bg-black/[0.06] text-slate-700 font-mono text-[10.5px] cursor-pointer transition shrink-0"
            :title="'点击复制 ' + d"
          >
            {{ d }}
          </button>
        </div>
      </div>

      <!-- 核心方案 2: 手机扫码直达 -->
      <div class="bg-white rounded-2xl p-4 border border-black/[0.04] shadow-xs flex items-center gap-4">
        <div class="w-24 h-24 sm:w-28 sm:h-28 rounded-xl bg-slate-50 p-1.5 border border-black/[0.06] flex items-center justify-center shrink-0">
          <img
            v-if="qrDataUrl"
            :src="qrDataUrl"
            alt="手机扫码访问二维码"
            class="w-full h-full object-contain rounded-lg"
          />
          <div v-else class="text-[10px] text-slate-400">生成中...</div>
        </div>
        <div class="flex flex-col justify-between py-1 min-w-0">
          <div>
            <h4 class="text-xs font-semibold text-slate-900 tracking-tight flex items-center gap-1 mb-1">
              <QrCode class="w-3.5 h-3.5 text-[#007AFF]" />
              <span>手机相机扫一扫</span>
            </h4>
            <p class="text-[11px] text-slate-500 font-medium leading-relaxed">
              支持 iPhone 自带相机、微信、各大安卓浏览器扫码，轻点通知即刻打开探索地图。
            </p>
          </div>
          <div class="pt-2 flex items-center gap-2">
            <span class="text-[10px] text-slate-400 tabular-nums">IP: {{ lanIp }}</span>
          </div>
        </div>
      </div>

      <!-- 底部安全提示 -->
      <div class="text-[11px] text-slate-500 font-medium flex items-center justify-between px-1">
        <span>支持 iPhone / iPad / Android / Mac / PC</span>
        <button
          @click="openDirect"
          class="text-[#007AFF] hover:underline flex items-center gap-0.5 cursor-pointer"
        >
          <span>在新标签页打开</span>
          <ExternalLink class="w-3 h-3" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { Smartphone, Wifi, QrCode, X, Copy, Check, ExternalLink } from 'lucide-vue-next';
import QRCode from 'qrcode';

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close']);

const lanInfo = ref(null);
const copiedType = ref('');
const qrDataUrl = ref('');

const shortUrl = computed(() => {
  if (lanInfo.value && lanInfo.value.recommended_url) {
    return lanInfo.value.recommended_url;
  }
  return 'http://nj.local';
});

const lanIp = computed(() => {
  return lanInfo.value ? lanInfo.value.primary_ip : '127.0.0.1';
});

const altDomains = computed(() => {
  if (!lanInfo.value) return ['http://panda.local', 'http://panda'];
  return (lanInfo.value.recommended_urls || [])
    .filter(u => u !== shortUrl.value)
    .slice(0, 3);
});

async function fetchLanInfo() {
  try {
    const res = await fetch('/api/lan/info');
    if (res.ok) {
      const data = await res.json();
      if (data.ok) {
        lanInfo.value = data;
        generateQrCode(data.recommended_ip_url || data.recommended_url || shortUrl.value);
      }
    }
  } catch (e) {
    // 离线或异常降级
    generateQrCode('http://nj.local');
  }
}

async function generateQrCode(url) {
  try {
    qrDataUrl.value = await QRCode.toDataURL(url, {
      margin: 1,
      width: 240,
      color: {
        dark: '#0f172a',
        light: '#ffffff'
      }
    });
  } catch (e) {
    console.error('QR code generation failed:', e);
  }
}

function copyText(text, type) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text);
    copiedType.value = type;
    setTimeout(() => {
      copiedType.value = '';
    }, 2000);
  }
}

function openDirect() {
  window.open(shortUrl.value, '_blank');
}

function close() {
  emit('close');
}

watch(
  () => props.isOpen,
  (val) => {
    if (val) {
      fetchLanInfo();
    }
  }
);

onMounted(() => {
  fetchLanInfo();
});
</script>
