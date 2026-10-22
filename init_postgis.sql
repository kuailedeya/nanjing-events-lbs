-- ============================================================================
-- 南京地区同城活动抓取与时空可视化系统 (Nanjing Events LBS Visualization)
-- PostgreSQL 15+ & PostGIS 3.4+ 核心表结构初始化脚本 (init_postgis.sql)
-- 坐标系约束：统一使用高德 GCJ-02 经纬度存储在 SRID 4326 容器中，确保前端高德地图零偏移
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS nj_events (
    id              VARCHAR(64) PRIMARY KEY,               -- 全局唯一主键 (wx_xxx / xhs_xxx)
    title           VARCHAR(255) NOT NULL,                 -- 清洗提炼后的情报标题
    category        VARCHAR(32)  NOT NULL,                 -- 顶层核心分类: 🎪 南京展会 | 🎉 南京活动 | 🐑 羊毛福利
    sub_category    VARCHAR(32)  DEFAULT '综合',           -- 细分子类: 展览/演出/市集/景区免票/消费券/立减金/打卡礼
    start_time      TIMESTAMPTZ,                           -- 活动/抢券开始时间 (ISO8601)
    end_time        TIMESTAMPTZ,                           -- 活动/抢券结束时间 (ISO8601)
    event_time_text VARCHAR(128) NOT NULL,                 -- 人类可读排期描述 (如 10月22日-10月24日)
    district        VARCHAR(32)  NOT NULL,                 -- 南京 11 个行政区划 (玄武区/秦淮区/建邺区...或 全城通用)
    address         TEXT         NOT NULL,                 -- 场馆名称与详细地址/线上渠道
    lng             DOUBLE PRECISION NOT NULL,             -- GCJ-02 经度
    lat             DOUBLE PRECISION NOT NULL,             -- GCJ-02 纬度
    geom            GEOGRAPHY(POINT, 4326) NOT NULL,       -- PostGIS 空间点对象 ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
    benefit         VARCHAR(128) NOT NULL,                 -- 门票/羊毛福利力度
    is_free         BOOLEAN      DEFAULT TRUE,             -- 是否免费/0元羊毛
    action_guide    VARCHAR(255) NOT NULL,                 -- 一句话报名/领券操作指引
    summary         TEXT         NOT NULL,                 -- 120字以内高密度省流总结 (严禁存原文长文)
    tags            TEXT[]       DEFAULT '{}',             -- 多维标签数组
    extra_info      JSONB        DEFAULT '{}'::jsonb,      -- 异构扩展字段 (platform, author, publish_date, key_points, price_num)
    source_url      TEXT         UNIQUE NOT NULL,          -- 原帖唯一 URL (幂等去重键)
    obsidian_path   TEXT         NOT NULL,                 -- 关联的 Obsidian 笔记相对路径
    status          VARCHAR(32)  DEFAULT '待去/待薅',      -- 状态: 待去/待薅 | 已打卡/已薅 | 已过期
    updated_at      TIMESTAMPTZ  DEFAULT NOW()             -- 最后更新时间
);

-- 空间 GIST 索引（加速 ST_DWithin 半径距离查询与 ST_AsGeoJSON 输出）
CREATE INDEX IF NOT EXISTS idx_nj_events_geom ON nj_events USING GIST (geom);

-- 常用多维检索索引
CREATE INDEX IF NOT EXISTS idx_nj_events_category ON nj_events (category);
CREATE INDEX IF NOT EXISTS idx_nj_events_district ON nj_events (district);
CREATE INDEX IF NOT EXISTS idx_nj_events_tags ON nj_events USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_nj_events_extra ON nj_events USING GIN (extra_info);

-- ============================================================================
-- 典型 PostGIS 空间半径查询与 GeoJSON 直出示例：
-- 查询建邺区南京国际博览中心 (118.7265, 31.9986) 半径 5000 米内的所有活动并输出 FeatureCollection
-- ============================================================================
/*
SELECT jsonb_build_object(
    'type', 'FeatureCollection',
    'features', COALESCE(jsonb_agg(
        jsonb_build_object(
            'type', 'Feature',
            'id', id,
            'geometry', ST_AsGeoJSON(geom)::jsonb,
            'properties', to_jsonb(nj_events.*) - 'geom'
        )
    ), '[]'::jsonb)
)
FROM nj_events
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(118.7265, 31.9986), 4326)::geography,
    5000
);
*/
