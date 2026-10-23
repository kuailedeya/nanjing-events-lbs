/**
 * Modular ECharts loader for Vite tree-shaking
 * Only loads BarChart, PieChart, GridComponent, TooltipComponent, and CanvasRenderer.
 * Reduces bundle size from 1.14 MB down to ~200 kB.
 */
import * as echarts from 'echarts/core';
import { BarChart, PieChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  CanvasRenderer
]);

export default echarts;
