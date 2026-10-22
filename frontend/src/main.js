import { createApp } from 'vue';
import ArcoVue from '@arco-design/web-vue';
import '@arco-design/web-vue/dist/arco.css';
import VueAMap, { initAMapApiLoader } from '@vuemap/vue-amap';
import '@vuemap/vue-amap/dist/style.css';
import 'leaflet/dist/leaflet.css';

import './style.css';
import App from './App.vue';

// 检查是否有用户配置的高德 Key
const savedKey = localStorage.getItem('NJ_AMAP_KEY') || '';
const savedSec = localStorage.getItem('NJ_AMAP_SEC') || '';

if (savedKey) {
  if (savedSec) {
    window._AMapSecurityConfig = { securityJsCode: savedSec };
  }
  try {
    initAMapApiLoader({
      key: savedKey,
      securityJsCode: savedSec,
      plugins: ['AMap.MarkerCluster', 'AMap.ToolBar', 'AMap.Scale']
    });
  } catch (e) {
    console.warn('AMap loader initialization skipped:', e);
  }
}

const app = createApp(App);
app.use(ArcoVue);
app.use(VueAMap);
app.mount('#app');
