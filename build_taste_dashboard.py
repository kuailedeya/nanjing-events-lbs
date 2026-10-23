#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate E:\\usage\\dashboard.html using Taste-Skill v2.1 No-Sidebar Spatial Viewer Architecture.
- NO left admin sidebar, NO top breadcrumb bar (Zero Vue-Element-Admin bloat)
- Zero emojis, zero rainbow colors, zero gradients, zero resting shadows
- Full-bleed centered canvas (max-width 1360px) with 48px header, unified KPI strip,
  Interactive GCJ-02 Spatial Map + District/Benefit SVG Charts, and Interactive Event Ledger.
"""

import json
from pathlib import Path
import dashboard_server

OUT_HTML = Path(__file__).resolve().parent / "dashboard.html"

items = dashboard_server.get_all_events()
fallback_json = json.dumps(items, ensure_ascii=False)

HTML_Part1 = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>南京同城活动与时空可视化系统 · Nanjing LBS Viewer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://webapi.amap.com/loader.js"></script>
  <script src="/assets/charts.js"></script>
  <style>
    :root {
      --ground: #000000;
      --surface: #111111;
      --raised: #1e1e1e;
      --active: #262626;
      --border: #1a1a1a;
      --rule: #161616;
      --control: #383838;
      --text: #ffffff;
      --muted: #b4b4b4;
      --faint: #949494;
      --accent: #f2b33d;
      --primary: #ffffff;
      --primary-ink: #000000;
      --positive: #3fc07a;
      --negative: #e5566f;
      --warning: #f2b33d;
      --chart-1: #f2b33d;
      --chart-2: #b4b4b4;
      --chart-3: #6b6b6b;
      --chart-muted: #333333;
      --chart-mark: #ffffff;
      --chart-span: 0.12;
      --grid: #222222;
      --axis-ink: #949494;
      --ink: #ffffff;
      --pill-positive-bg: #172a1d;
      --pill-positive-ink: #3fc07a;
      --pill-negative-bg: #2c1a20;
      --pill-negative-ink: #e5566f;
      --pill-warning-bg: #2b2414;
      --pill-warning-ink: #f2b33d;
      --pill-neutral-bg: #222222;
      --pill-neutral-ink: #ffffff;
      --radius-card: 16px;
      --radius-control: 999px;
      --gap: 16px;
      --pad: 24px;
      --card-pad: 20px;
      --control-height: 32px;
      --font: "Inter", -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
      --fs-title: 20px;
      --fs-section: 15px;
      --fs-kpi: 26px;
      --fs-body: 14px;
      --fs-small: 12px;
    }

    html[data-theme="light"] {
      --ground: #f9fafb;
      --surface: #ffffff;
      --raised: #f3f4f6;
      --active: #eaecef;
      --border: #e8e8e8;
      --rule: #f1f2f3;
      --control: #d1d5db;
      --text: #111111;
      --muted: #5f6368;
      --faint: #6b6b6b;
      --accent: #d97706;
      --primary: #1d1f20;
      --primary-ink: #ffffff;
      --positive: #247b50;
      --negative: #c4242a;
      --warning: #92400e;
      --chart-1: #d97706;
      --chart-2: #5f6368;
      --chart-3: #9ca3af;
      --chart-muted: #d1d5db;
      --chart-mark: #111111;
      --chart-span: 0.06;
      --grid: #e5e7eb;
      --axis-ink: #5f6368;
      --ink: #111111;
      --pill-positive-bg: #dcfae5;
      --pill-positive-ink: #04250e;
      --pill-negative-bg: #ffedea;
      --pill-negative-ink: #831c1e;
      --pill-warning-bg: #fffbeb;
      --pill-warning-ink: #92400e;
      --pill-neutral-bg: #eeeeee;
      --pill-neutral-ink: #1f2937;
    }

    *, *::before, *::after { box-sizing: border-box; }
    html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
    body {
      margin: 0;
      background: var(--ground);
      color: var(--text);
      font-family: var(--font);
      font-size: var(--fs-body);
      line-height: 20px;
      font-variant-numeric: tabular-nums;
      -webkit-font-smoothing: antialiased;
    }
    h1, h2, h3, h4, p, figure, ul, ol, dl, dd { margin: 0; }
    ul, ol { padding: 0; list-style: none; }
    button, input, select { font: inherit; color: inherit; font-variant-numeric: tabular-nums; }
    a { color: inherit; text-decoration: none; }
    :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    .num, table, .kpi-value { font-variant-numeric: tabular-nums; }

    /* No-Sidebar Archetype (§3.1): 48px top bar + centered column */
    .top-strip {
      border-bottom: 1px solid var(--border);
      background: var(--ground);
    }
    .top-inner {
      max-width: 1360px;
      margin: 0 auto;
      min-height: 54px;
      padding: 8px var(--pad);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }
    .brand-cluster {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .brand-id {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand-mark {
      width: 20px;
      height: 20px;
      border-radius: 5px;
      background: var(--surface);
      border: 1px solid var(--control);
      display: grid;
      place-items: center;
      flex: none;
    }
    .brand-mark svg { width: 12px; height: 12px; stroke: var(--accent); stroke-width: 1.8; fill: none; }
    .brand-id h1 {
      font-size: 18px;
      line-height: 24px;
      font-weight: 600;
      letter-spacing: -0.01em;
      white-space: nowrap;
    }
    .segmented {
      display: inline-flex;
      padding: 2px;
      border-radius: var(--radius-control);
      background: var(--surface);
      border: 1px solid var(--border);
    }
    .segmented button {
      height: 28px;
      padding: 0 10px;
      border: 0;
      border-radius: var(--radius-control);
      background: transparent;
      color: var(--muted);
      font-size: 13px;
      cursor: pointer;
      white-space: nowrap;
      transition: background-color 150ms ease, color 150ms ease;
    }
    .segmented button[aria-pressed="true"] {
      background: var(--raised);
      color: var(--text);
      font-weight: 500;
    }

    .toolbar-cluster {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }
    .search-box {
      position: relative;
      width: 168px;
    }
    .search-box svg {
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      width: 13px;
      height: 13px;
      stroke: var(--faint);
      stroke-width: 1.5;
      fill: none;
    }
    .search-input {
      width: 100%;
      height: var(--control-height);
      padding: 0 10px 0 30px;
      border-radius: var(--radius-control);
      border: 1px solid var(--control);
      background: var(--surface);
      color: var(--text);
      font-size: 13px;
    }
    .search-input::placeholder { color: var(--faint); }
    .select-ctrl {
      height: var(--control-height);
      padding: 0 10px;
      border-radius: var(--radius-control);
      border: 1px solid var(--control);
      background: var(--surface);
      color: var(--text);
      font-size: 13px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      height: var(--control-height);
      padding: 0 12px;
      border-radius: var(--radius-control);
      border: 1px solid var(--control);
      background: var(--surface);
      color: var(--text);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: background-color 150ms ease, color 150ms ease;
    }
    .btn:hover { background: var(--raised); }
    .btn.primary {
      background: var(--primary);
      color: var(--primary-ink);
      border-color: transparent;
    }

    /* Main Centered Canvas */
    .canvas {
      max-width: 1360px;
      margin: 0 auto;
      padding: 18px var(--pad) 32px;
      display: grid;
      gap: var(--gap);
    }

    /* Finding + Freshness Subbar */
    .finding-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      font-size: 13px;
      color: var(--muted);
    }
    .finding-meta {
      font-size: 12px;
      color: var(--faint);
    }

    /* Divided KPI Strip */
    .kpis {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-card);
    }
    .kpi {
      padding: 14px var(--card-pad);
      min-width: 0;
    }
    .kpi + .kpi { border-left: 1px solid var(--border); }
    .kpi-label { font-size: 13px; color: var(--muted); }
    .kpi-value {
      margin-top: 4px;
      font-size: var(--fs-kpi);
      line-height: 30px;
      font-weight: 500;
      color: var(--text);
      font-variant-numeric: tabular-nums;
    }
    .kpi-value.lead { font-size: 30px; font-weight: 600; }
    .kpi-unit { font-size: 13px; color: var(--muted); font-weight: 400; margin-left: 4px; }
    .kpi-note { margin-top: 4px; font-size: 12px; color: var(--faint); }
    .kpi-note .pos { color: var(--positive); }

    /* Spatial Workbench Grid: 7fr Left (Map + Charts) + 5fr Right (Nearest Priority Queue) */
    .workbench-grid {
      display: grid;
      grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
      gap: var(--gap);
      align-items: stretch;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-card);
      padding: var(--card-pad);
      min-width: 0;
      display: flex;
      flex-direction: column;
    }
    .panel-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }
    .panel-head h2 {
      font-size: var(--fs-section);
      line-height: 20px;
      font-weight: 600;
    }
    .panel-meta { font-size: 12px; color: var(--faint); }

    .spatial-split {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
      gap: var(--gap);
      flex: 1;
    }
    .map-stage {
      position: relative;
      min-height: 280px;
      border-radius: 8px;
      background: var(--raised);
      overflow: hidden;
      border: 1px solid var(--border);
    }
    #amap-container {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      filter: grayscale(100%) contrast(108%);
    }
    #spatial-svg-stage {
      position: relative;
      z-index: 2;
      width: 100%;
      height: 100%;
      min-height: 280px;
      display: block;
    }
    .map-caption {
      position: absolute;
      left: 10px;
      bottom: 10px;
      z-index: 3;
      padding: 4px 10px;
      border-radius: var(--radius-control);
      background: var(--surface);
      border: 1px solid var(--border);
      font-size: 12px;
      color: var(--muted);
    }
    .chart-box {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-width: 0;
    }

    /* Priority Queue Rows */
    .rail-list { display: grid; flex: 1; }
    .rail-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 12px;
      padding: 9px 0;
      border-bottom: 1px solid var(--rule);
      cursor: pointer;
    }
    .rail-row:first-child { padding-top: 2px; }
    .rail-row:last-child { border-bottom: 0; }
    .rail-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .rail-sub {
      margin-top: 2px;
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .rail-dist {
      text-align: right;
      font-size: 13px;
      font-weight: 500;
      color: var(--text);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .rail-dist span {
      display: block;
      font-size: 12px;
      font-weight: 400;
      color: var(--faint);
    }

    /* Ledger Table */
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
    th {
      height: 36px;
      padding: 0 12px;
      text-align: left;
      font-weight: 400;
      font-size: 12px;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }
    td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--rule);
      vertical-align: baseline;
      font-size: 14px;
    }
    tbody tr:last-child td { border-bottom: 0; }
    tbody tr[aria-selected="true"] td { background: var(--active); }
    th.n, td.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
    td.nowrap, th.nowrap { white-space: nowrap; }
    .cell-title {
      font-weight: 500;
      color: var(--text);
      max-width: 40ch;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: block;
    }
    .cell-sub {
      font-size: 12px;
      color: var(--muted);
      margin-top: 2px;
      max-width: 44ch;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: block;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      height: 22px;
      padding: 0 8px;
      border-radius: var(--radius-control);
      font-size: 12px;
      font-weight: 500;
      background: var(--pill-neutral-bg);
      color: var(--pill-neutral-ink);
      white-space: nowrap;
      flex: none;
    }
    .pill.pos { background: var(--pill-positive-bg); color: var(--pill-positive-ink); }
    .pill.warn { background: var(--pill-warning-bg); color: var(--pill-warning-ink); }
    .pill.neg { background: var(--pill-negative-bg); color: var(--pill-negative-ink); }

    .row-action {
      border: 1px solid var(--control);
      background: transparent;
      color: var(--text);
      height: 24px;
      padding: 0 10px;
      border-radius: var(--radius-control);
      font-size: 12px;
      cursor: pointer;
      white-space: nowrap;
      flex: none;
    }
    .row-action:hover { background: var(--raised); }

    @media (max-width: 1024px) {
      .workbench-grid, .spatial-split { grid-template-columns: minmax(0, 1fr); }
      .col-hide-tablet { display: none; }
    }
    @media (max-width: 860px) {
      .top-inner, .canvas { padding-left: 16px; padding-right: 16px; }
      .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .kpi + .kpi { border-left: 0; }
      .kpi:nth-child(2n) { border-left: 1px solid var(--border); }
      .kpi:nth-child(n+3) { border-top: 1px solid var(--border); }
    }
    @media (max-width: 640px) {
      .col-hide-mobile { display: none; }
      .panel { padding: 16px; }
      .table-wrap { overflow-x: hidden; }
      th, td { padding: 10px 6px; }
      .cell-title, .cell-sub, .rail-title, .rail-sub {
        white-space: normal;
        max-width: 100%;
        word-break: break-word;
      }
      .search-box { width: 100%; }
    }
  </style>
</head>
"""
HTML_Part2 = """<body>
  <header class="top-strip">
    <div class="top-inner">
      <div class="brand-cluster">
        <div class="brand-id">
          <div class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 16 16"><path d="M8 1.5L14 5v6l-6 3.5L2 11V5L8 1.5z"/><circle cx="8" cy="8" r="2"/></svg>
          </div>
          <h1>南京同城活动与时空分布总览</h1>
        </div>

        <div class="segmented" role="group" aria-label="活动类别筛选">
          <button type="button" aria-pressed="true" data-seg="ALL" onclick="setCategory('ALL')">全部 15</button>
          <button type="button" aria-pressed="false" data-seg="南京展会" onclick="setCategory('南京展会')">南京展会 7</button>
          <button type="button" aria-pressed="false" data-seg="南京活动" onclick="setCategory('南京活动')">南京活动 5</button>
          <button type="button" aria-pressed="false" data-seg="羊毛福利" onclick="setCategory('羊毛福利')">羊毛福利 3</button>
        </div>
      </div>

      <div class="toolbar-cluster">
        <div class="search-box">
          <svg viewBox="0 0 16 16"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg>
          <input type="search" id="q-input" class="search-input" placeholder="检索场馆、活动或福利..." oninput="applyFilters()" />
        </div>

        <select id="district-select" class="select-ctrl" aria-label="行政区划筛选" onchange="applyFilters()">
          <option value="ALL">全部行政区 (11区)</option>
          <option value="玄武区">玄武区</option>
          <option value="秦淮区">秦淮区</option>
          <option value="建邺区">建邺区</option>
          <option value="鼓楼区">鼓楼区</option>
          <option value="栖霞区">栖霞区</option>
          <option value="雨花台区">雨花台区</option>
          <option value="江宁区">江宁区</option>
          <option value="浦口区">浦口区</option>
          <option value="六合区">六合区</option>
          <option value="溧水区">溧水区</option>
          <option value="高淳区">高淳区</option>
          <option value="全城通用">全城通用</option>
        </select>

        <select id="radius-select" class="select-ctrl" aria-label="新街口球面半径筛选" onchange="applyFilters()">
          <option value="0">全城范围</option>
          <option value="3">新街口 3 km 圈</option>
          <option value="5">新街口 5 km 圈</option>
          <option value="10">新街口 10 km 圈</option>
          <option value="20">新街口 20 km 圈</option>
        </select>

        <button type="button" class="btn" id="free-toggle" aria-pressed="false" onclick="toggleFreeOnly()">仅看免费</button>
        <button type="button" class="btn" id="theme-btn" onclick="toggleTheme()">切换浅色</button>
        <button type="button" class="btn primary" id="scrape-btn" onclick="triggerScrape()">增量抓取同步</button>
      </div>
    </div>
  </header>

  <main class="canvas">
    <div class="finding-bar">
      <p id="finding-line">玄武、建邺与秦淮三区合计占比 60.0%（9 项），当前命中 15 项活动中 11 项支持免票直接入场</p>
      <span class="finding-meta" id="freshness-stamp">空间基准: 新街口 GCJ-02 (118.7842E, 32.0418N) · SQLite + Obsidian 双向同步</span>
    </div>

    <section class="kpis" aria-label="核心指标概览">
      <div class="kpi">
        <div class="kpi-label">当前命中活动总数</div>
        <div class="kpi-value lead"><span id="kpi-total">15</span><span class="kpi-unit">项</span></div>
        <div class="kpi-note" id="kpi-total-note">覆盖南京 7 个行政片区</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">免票直入场次</div>
        <div class="kpi-value"><span id="kpi-free">11</span><span class="kpi-unit">项</span></div>
        <div class="kpi-note"><span class="pos" id="kpi-free-pct">73.3%</span> 免门票 · 另有 2 项消费券</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">大型场馆展会排期</div>
        <div class="kpi-value"><span id="kpi-pending">7</span><span class="kpi-unit">场</span></div>
        <div class="kpi-note" id="kpi-pending-note">集中在建邺与玄武两大展馆群</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">新街口平均球面距离</div>
        <div class="kpi-value"><span id="kpi-avg-dist">5.7</span><span class="kpi-unit">km</span></div>
        <div class="kpi-note" id="kpi-dist-note">5 km 圈内共 9 项近期活动</div>
      </div>
    </section>

    <div class="workbench-grid">
      <section class="panel" aria-label="空间坐标与行政区活动密度">
        <div class="panel-head">
          <h2>南京 11 区空间坐标分布与行政区密度对比</h2>
          <span class="panel-meta" id="spatial-meta">点击坐标点或柱形图可联动定位下方台账</span>
        </div>
        <div class="spatial-split">
          <div class="map-stage">
            <div id="amap-container"></div>
            <svg id="spatial-svg-stage" viewBox="0 0 460 280" role="img" aria-label="南京活动 GCJ-02 空间坐标分布图"></svg>
            <div class="map-caption" id="map-caption">GCJ-02 空间投影 · 点击坐标点定位台账</div>
          </div>
          <div class="chart-box">
            <div>
              <div class="panel-head" style="margin-bottom:6px">
                <h3 style="font-size:13px;font-weight:500;color:var(--muted)">各行政区活动数量分布 (项)</h3>
                <span class="panel-meta" id="dist-chart-meta">最高分布: 玄武 / 建邺 / 秦淮 / 全城 (3 项)</span>
              </div>
              <div id="chart-districts" style="min-height:165px"></div>
            </div>
            <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--rule)">
              <div class="panel-head" style="margin-bottom:6px">
                <h3 style="font-size:13px;font-weight:500;color:var(--muted)">准入门槛与票务结构</h3>
                <span class="panel-meta">按福利类型统计</span>
              </div>
              <div id="chart-benefits"></div>
            </div>
          </div>
        </div>
      </section>

      <section class="panel" aria-label="近期焦点排期队列">
        <div class="panel-head">
          <h2>近期优先排期队列</h2>
          <span class="panel-meta" id="queue-meta">按距新街口由近及远排列</span>
        </div>
        <div class="rail-list" id="priority-queue"></div>
      </section>
    </div>

    <section class="panel" aria-label="南京活动空间台账明细">
      <div class="panel-head">
        <h2>活动空间台账与 Obsidian 状态核销</h2>
        <span class="panel-meta" id="table-summary">当前显示 15 条记录 · 点击状态胶囊可实时写回 SQLite 与 Obsidian</span>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>活动与场馆名称</th>
              <th class="nowrap col-hide-tablet">分类与细类</th>
              <th class="col-hide-mobile">准入条件与排期</th>
              <th class="n col-hide-tablet">采集日期</th>
              <th class="n">新街口距离与坐标</th>
              <th class="n">状态与归档</th>
            </tr>
          </thead>
          <tbody id="ledger-tbody"></tbody>
        </table>
      </div>
    </section>
  </main>

  <script>
    const FALLBACK_ITEMS = __FALLBACK_JSON__;
    const XINJIEKOU = { lng: 118.7842, lat: 32.0418 };
    const STATUS_ORDER = ["待去/待薅", "已完成", "已过期"];

    let allItems = [];
    let filteredItems = [];
    let state = {
      category: "ALL",
      district: "ALL",
      radiusKm: 0,
      freeOnly: false,
      q: "",
      selectedId: null
    };
    let amapInstance = null;
    let amapMarkers = [];

    function stripEmoji(str) {
      if (!str) return "";
      return String(str).replace(/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}\\uFE0F]/gu, "").trim();
    }

    function shortTitle(str, maxLen = 18) {
      const s = stripEmoji(str).replace(/\\s+/g, " ");
      return s.length > maxLen ? s.slice(0, maxLen) + "…" : s;
    }

    function haversineKm(lng1, lat1, lng2, lat2) {
      const toRad = (d) => (d * Math.PI) / 180;
      const R = 6371.0;
      const dLat = toRad(lat2 - lat1);
      const dLng = toRad(lng2 - lng1);
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    function normalizeItem(raw) {
      const lng = Number(raw.lng || 118.7842);
      const lat = Number(raw.lat || 32.0418);
      const distKm = raw.distance_km != null ? Number(raw.distance_km) : haversineKm(XINJIEKOU.lng, XINJIEKOU.lat, lng, lat);
      return {
        ...raw,
        id: raw.id || raw.post_id,
        full_title: stripEmoji(raw.title),
        title: shortTitle(raw.title, 18),
        category: stripEmoji(raw.category || "南京活动"),
        sub_category: stripEmoji(raw.sub_category || "综合"),
        district: stripEmoji(raw.district || "玄武区"),
        address: shortTitle(raw.address || raw.location || "南京市内", 16),
        benefit: shortTitle(raw.benefit || "详见原文", 14),
        event_time_text: shortTitle(raw.event_time_text || raw.event_time || raw.publish_date || "近期有效", 16),
        status: stripEmoji(raw.status || "待去/待薅"),
        lng,
        lat,
        distance_km: Number(distKm.toFixed(2))
      };
    }

    async function loadEvents() {
      try {
        const res = await fetch("/api/events");
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.items) && data.items.length) {
            allItems = data.items.map(normalizeItem);
            applyFilters();
            return;
          }
        }
      } catch (e) {}
      allItems = FALLBACK_ITEMS.map(normalizeItem);
      applyFilters();
    }

    function setCategory(cat) {
      state.category = cat;
      document.querySelectorAll("[data-seg]").forEach((b) => {
        b.setAttribute("aria-pressed", b.getAttribute("data-seg") === cat ? "true" : "false");
      });
      applyFilters();
    }

    function toggleFreeOnly() {
      state.freeOnly = !state.freeOnly;
      const btn = document.getElementById("free-toggle");
      btn.setAttribute("aria-pressed", state.freeOnly ? "true" : "false");
      btn.style.borderColor = state.freeOnly ? "var(--accent)" : "var(--control)";
      applyFilters();
    }

    function applyFilters() {
      state.district = document.getElementById("district-select").value;
      state.radiusKm = Number(document.getElementById("radius-select").value || 0);
      state.q = (document.getElementById("q-input").value || "").trim().toLowerCase();

      filteredItems = allItems.filter((it) => {
        if (state.category !== "ALL" && it.category !== state.category) return false;
        if (state.district !== "ALL" && it.district !== state.district) return false;
        if (state.freeOnly && !it.is_free) return false;
        if (state.radiusKm > 0 && it.distance_km > state.radiusKm) return false;
        if (state.q) {
          const hay = [it.full_title, it.category, it.sub_category, it.district, it.address, it.benefit, it.summary].join(" ").toLowerCase();
          if (!hay.includes(state.q)) return false;
        }
        return true;
      });

      updateCountsAndKpis();
      renderCharts();
      renderSpatialSvg();
      renderPriorityQueue();
      renderTable();
      syncAmapMarkers();
    }

    function updateCountsAndKpis() {
      const cAll = allItems.length;
      const cEx = allItems.filter((x) => x.category === "南京展会").length;
      const cEv = allItems.filter((x) => x.category === "南京活动").length;
      const cDe = allItems.filter((x) => x.category === "羊毛福利").length;

      const segAll = document.querySelector('[data-seg="ALL"]');
      const segEx = document.querySelector('[data-seg="南京展会"]');
      const segEv = document.querySelector('[data-seg="南京活动"]');
      const segDe = document.querySelector('[data-seg="羊毛福利"]');
      if (segAll) segAll.textContent = `全部 ${cAll}`;
      if (segEx) segEx.textContent = `南京展会 ${cEx}`;
      if (segEv) segEv.textContent = `南京活动 ${cEv}`;
      if (segDe) segDe.textContent = `羊毛福利 ${cDe}`;

      const total = filteredItems.length;
      const directFreeCnt = filteredItems.filter((x) => (x.benefit || "").includes("免费") || (x.benefit || "").includes("免票")).length;
      const exhibitCnt = filteredItems.filter((x) => x.category === "南京展会").length;
      const within5km = filteredItems.filter((x) => x.distance_km <= 5.0).length;
      const avgDist = total ? (filteredItems.reduce((s, x) => s + x.distance_km, 0) / total).toFixed(1) : "0.0";
      const distSet = new Set(filteredItems.map((x) => x.district));

      document.getElementById("kpi-total").textContent = total;
      document.getElementById("kpi-total-note").textContent = total ? `覆盖南京 ${distSet.size} 个行政片区` : "当前筛选条件下无匹配项";
      document.getElementById("kpi-free").textContent = directFreeCnt;
      document.getElementById("kpi-free-pct").textContent = total ? `${((directFreeCnt / total) * 100).toFixed(1)}%` : "0.0%";
      document.getElementById("kpi-pending").textContent = exhibitCnt;
      document.getElementById("kpi-avg-dist").textContent = avgDist;
      document.getElementById("kpi-dist-note").textContent = `5 km 圈内共 ${within5km} 项近期活动`;
      document.getElementById("finding-line").textContent = `玄武、建邺与秦淮三区合计占比 60.0%（9 项），当前命中 ${total} 项活动中 ${directFreeCnt} 项支持免票直接入场`;
    }

    function renderCharts() {
      if (!window.Charts) return;
      const distOrder = ["玄武区", "建邺区", "秦淮区", "全城通用", "鼓楼区", "栖霞区", "江宁区", "雨花台区"];
      const counts = distOrder.map((d) => filteredItems.filter((x) => x.district === d).length);
      const maxVal = Math.max(0, ...counts);
      const topIndices = counts.map((v, i) => (v === maxVal && v > 0 ? i : -1)).filter((i) => i >= 0);

      const topNames = topIndices.map((i) => distOrder[i].replace("全城通用", "全城").replace("区", "")).join(" / ");
      document.getElementById("dist-chart-meta").textContent = maxVal > 0 ? `最高分布: ${topNames} (${maxVal} 项)` : "暂无分布数据";

      const distEl = document.getElementById("chart-districts");
      Charts.bars(distEl, {
        labels: distOrder.map((d) => d.replace("全城通用", "全城").replace("雨花台区", "雨花").replace("区", "")),
        values: counts,
        height: 160,
        highlight: topIndices.length ? topIndices : [0],
        format: Charts.fmt.int
      });

      let freeTicket = 0, coupon = 0, paid = 0;
      filteredItems.forEach((it) => {
        const b = it.benefit || "";
        if (b.includes("免费") || b.includes("免票")) freeTicket++;
        else if (b.includes("立减") || b.includes("券") || b.includes("0元") || b.includes("0.01") || b.includes("礼")) coupon++;
        else paid++;
      });

      const benEl = document.getElementById("chart-benefits");
      Charts.barList(
        benEl,
        [
          { label: "立减消费券与打卡礼", value: coupon },
          { label: "免费免票直接入场", value: freeTicket },
          { label: "预约或早鸟票入场", value: paid }
        ],
        { thin: true, format: (v) => `${v} 项` }
      );
    }

    function renderSpatialSvg() {
      const svgEl = document.getElementById("spatial-svg-stage");
      if (!svgEl) return;
      const w = 460, h = 280;
      const minLng = 118.68, maxLng = 118.92;
      const minLat = 31.96, maxLat = 32.13;
      const project = (lng, lat) => {
        const x = 36 + ((lng - minLng) / (maxLng - minLng)) * (w - 72);
        const y = h - 32 - ((lat - minLat) / (maxLat - minLat)) * (h - 60);
        return [Math.max(24, Math.min(w - 24, x)), Math.max(24, Math.min(h - 28, y))];
      };

      const [cx, cy] = project(XINJIEKOU.lng, XINJIEKOU.lat);
      let html = `
        <line x1="24" y1="${cy.toFixed(1)}" x2="${w - 24}" y2="${cy.toFixed(1)}" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3" />
        <line x1="${cx.toFixed(1)}" y1="20" x2="${cx.toFixed(1)}" y2="${h - 24}" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3" />
        <circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="52" fill="none" stroke="var(--grid)" stroke-width="1" />
        <circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="96" fill="none" stroke="var(--grid)" stroke-width="1" stroke-dasharray="4 4" />
        <text x="${(cx + 6).toFixed(1)}" y="${(cy - 6).toFixed(1)}" font-size="11" fill="var(--faint)">新街口原点</text>
      `;

      filteredItems.forEach((it, idx) => {
        const [px, py] = project(it.lng, it.lat);
        const isSel = state.selectedId ? it.id === state.selectedId : idx === 0;
        const fill = isSel ? "var(--accent)" : "var(--text)";
        const r = isSel ? 5.5 : 4;
        const labelShort = it.district.replace("区", "");
        html += `
          <g style="cursor:pointer" onclick="focusEvent('${it.id}')">
            <title>${it.title} (${it.district} · ${it.distance_km.toFixed(1)} km)</title>
            <circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="${r}" fill="${fill}" stroke="var(--surface)" stroke-width="1.5" />
            ${isSel ? `<text x="${Math.min(w - 110, px + 8).toFixed(1)}" y="${(py + 4).toFixed(1)}" font-size="11" font-weight="600" fill="var(--accent)">${labelShort} · ${it.title.slice(0, 8)}</text>` : ""}
          </g>
        `;
      });

      svgEl.innerHTML = html;
    }

    function renderPriorityQueue() {
      const box = document.getElementById("priority-queue");
      const sorted = [...filteredItems].sort((a, b) => a.distance_km - b.distance_km).slice(0, 6);
      if (!sorted.length) {
        box.innerHTML = `<div style="padding:24px 0;color:var(--muted);font-size:13px">当前筛选范围内暂无待办活动。</div>`;
        return;
      }
      box.innerHTML = sorted
        .map(
          (it) => `
        <div class="rail-row" onclick="focusEvent('${it.id}')">
          <div style="min-width:0">
            <div class="rail-title">${it.title}</div>
            <div class="rail-sub">${it.district} · ${it.benefit}</div>
          </div>
          <div class="rail-dist">
            ${it.distance_km.toFixed(1)} km
            <span>${it.sub_category}</span>
          </div>
        </div>
      `
        )
        .join("");
    }

    function statusPillClass(st) {
      if (st === "已完成") return "pill pos";
      if (st === "已过期") return "pill neg";
      return "pill";
    }

    function renderTable() {
      const tbody = document.getElementById("ledger-tbody");
      document.getElementById("table-summary").textContent = `当前显示 ${filteredItems.length} 条记录 · 点击状态胶囊可实时写回 SQLite 与 Obsidian`;
      if (!filteredItems.length) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:28px">未找到符合筛选条件的南京同城活动。</td></tr>`;
        return;
      }
      tbody.innerHTML = filteredItems
        .map((it) => {
          const selected = state.selectedId === it.id ? 'aria-selected="true"' : "";
          const dateText = (it.publish_date || "2026-10-20").slice(0, 10);
          return `
          <tr id="row-${it.id}" ${selected} onclick="focusEvent('${it.id}')">
            <td>
              <span class="cell-title">${it.title}</span>
              <span class="cell-sub">${it.district} · ${it.address}</span>
            </td>
            <td class="nowrap col-hide-tablet">
              <span>${it.category}</span>
              <span class="cell-sub">${it.sub_category}</span>
            </td>
            <td class="col-hide-mobile">
              <span>${it.benefit}</span>
              <span class="cell-sub">${it.event_time_text}</span>
            </td>
            <td class="n col-hide-tablet">${dateText}</td>
            <td class="n">
              <span>${it.distance_km.toFixed(2)} km</span>
              <span class="cell-sub" style="margin-left:auto">${it.lng.toFixed(3)}E, ${it.lat.toFixed(3)}N</span>
            </td>
            <td class="n">
              <div style="display:inline-flex;align-items:center;justify-content:flex-end;gap:6px">
                <button type="button" class="${statusPillClass(it.status)}" style="border:0;cursor:pointer" onclick="event.stopPropagation(); cycleStatus('${it.id}')">${it.status}</button>
                <a class="row-action col-hide-mobile" href="${it.obsidian_uri}" onclick="event.stopPropagation()" style="display:inline-flex;align-items:center">笔记</a>
              </div>
            </td>
          </tr>
        `;
        })
        .join("");
    }

    function focusEvent(id) {
      state.selectedId = id;
      renderSpatialSvg();
      renderTable();
      const target = allItems.find((x) => x.id === id);
      if (target) {
        document.getElementById("map-caption").textContent = `已定位: ${target.district} · ${target.title.slice(0, 12)} (${target.lng.toFixed(4)}, ${target.lat.toFixed(4)})`;
        if (amapInstance) {
          try { amapInstance.setCenter([target.lng, target.lat]); } catch (e) {}
        }
      }
    }

    async function cycleStatus(id) {
      const item = allItems.find((x) => x.id === id);
      if (!item) return;
      const idx = STATUS_ORDER.indexOf(item.status);
      const nextStatus = STATUS_ORDER[(idx + 1) % STATUS_ORDER.length];
      item.status = nextStatus;
      applyFilters();
      try {
        await fetch("/api/events/status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, status: nextStatus })
        });
      } catch (e) {}
    }

    async function triggerScrape() {
      const btn = document.getElementById("scrape-btn");
      const orig = btn.textContent;
      btn.textContent = "正在同步...";
      btn.disabled = true;
      try {
        const res = await fetch("/api/scrape", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ limit: 2 })
        });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.items) && data.items.length) {
            allItems = data.items.map(normalizeItem);
            applyFilters();
          }
        }
      } catch (e) {}
      btn.textContent = orig;
      btn.disabled = false;
    }

    function toggleTheme() {
      const html = document.documentElement;
      const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
      html.setAttribute("data-theme", next);
      document.getElementById("theme-btn").textContent = next === "dark" ? "切换浅色" : "切换深色";
      renderCharts();
      renderSpatialSvg();
    }

    function initAmapOptional() {
      if (!window.AMapLoader) return;
      const savedKey = localStorage.getItem("NJ_AMAP_KEY") || "";
      if (!savedKey) return;
      window.AMapLoader.load({ key: savedKey, version: "2.0" })
        .then((AMap) => {
          amapInstance = new AMap.Map("amap-container", {
            viewMode: "2D",
            zoom: 11,
            center: [XINJIEKOU.lng, XINJIEKOU.lat],
            mapStyle: "amap://styles/dark"
          });
          syncAmapMarkers();
        })
        .catch(() => {});
    }

    function syncAmapMarkers() {
      if (!amapInstance || !window.AMap) return;
      amapInstance.remove(amapMarkers);
      amapMarkers = filteredItems.map((it) => {
        const marker = new window.AMap.Marker({
          position: [it.lng, it.lat],
          title: it.title
        });
        marker.on("click", () => focusEvent(it.id));
        amapInstance.add(marker);
        return marker;
      });
    }

    window.addEventListener("DOMContentLoaded", () => {
      loadEvents();
      initAmapOptional();
    });
  </script>
</body>
</html>
"""

full_html = HTML_Part1 + HTML_Part2.replace("__FALLBACK_JSON__", fallback_json)
OUT_HTML.write_text(full_html, encoding="utf-8")
print("Generated no-sidebar dashboard.html, bytes:", OUT_HTML.stat().st_size)
