/**
 * Local Bento Grid cover asset resolver.
 * High-definition 16:9 (640x360) images harvested and optimized locally (55 verified assets).
 * Matches event categories, topics, and landmarks with zero external network reliance.
 */

export const EXHIBITION_COVERS = [
  '/covers/exhibition_museum_01.jpg',
  '/covers/exhibition_art_01.jpg',
  '/covers/exhibition_modern_gallery_02.jpg',
  '/covers/exhibition_sculpture_01.jpg',
  '/covers/exhibition_sculpture_02.jpg',
  '/covers/exhibition_painting_01.jpg',
  '/covers/exhibition_painting_02.jpg',
  '/covers/exhibition_digital_01.jpg',
  '/covers/exhibition_digital_02.jpg',
  '/covers/exhibition_ceramic_01.jpg',
  '/covers/exhibition_relics_02.jpg',
  '/covers/exhibition_photo_01.jpg',
  '/covers/exhibition_photography_02.jpg',
  '/covers/exhibition_design_01.jpg',
  '/covers/exhibition_fashion_02.jpg',
  '/covers/exhibition_calligraphy_02.jpg'
];

export const ACTIVITY_COVERS = [
  '/covers/activity_concert_01.jpg',
  '/covers/activity_rock_01.jpg',
  '/covers/activity_rock_festival_02.jpg',
  '/covers/activity_livehouse_indie_02.jpg',
  '/covers/activity_orchestra_classical_02.jpg',
  '/covers/activity_theater_01.jpg',
  '/covers/activity_theater_musical_02.jpg',
  '/covers/activity_market_01.jpg',
  '/covers/activity_night_market_food_02.jpg',
  '/covers/activity_camping_01.jpg',
  '/covers/activity_outdoor_glamping_02.jpg',
  '/covers/activity_cosplay_01.jpg',
  '/covers/activity_anime_comic_02.jpg',
  '/covers/activity_jazz_01.jpg',
  '/covers/activity_comedy_club_02.jpg',
  '/covers/activity_dance_01.jpg',
  '/covers/activity_cycling_01.jpg',
  '/covers/activity_skate_street_02.jpg'
];

export const BENEFIT_COVERS = [
  '/covers/benefit_coffee_01.jpg',
  '/covers/benefit_specialty_pourover_02.jpg',
  '/covers/benefit_bookstore_01.jpg',
  '/covers/benefit_vintage_book_02.jpg',
  '/covers/benefit_bakery_01.jpg',
  '/covers/benefit_croissant_bakery_02.jpg',
  '/covers/benefit_dessert_01.jpg',
  '/covers/benefit_matcha_tea_02.jpg',
  '/covers/benefit_beer_01.jpg',
  '/covers/benefit_cocktail_bar_02.jpg',
  '/covers/benefit_flower_01.jpg',
  '/covers/benefit_pottery_01.jpg',
  '/covers/benefit_diy_woodwork_02.jpg',
  '/covers/benefit_lifestyle_01.jpg'
];

export const LANDMARK_COVERS = {
  xinjiekou: '/covers/landmark_xinjiekou_01.jpg',
  xuanwu: '/covers/landmark_xuanwu_01.jpg',
  qinhuai: '/covers/landmark_qinhuai_01.jpg',
  theater: '/covers/landmark_theater_01.jpg',
  olympic: '/covers/landmark_olympic_01.jpg',
  deji: '/covers/landmark_deji_museum_02.jpg',
  niushou: '/covers/landmark_niushou_mountain_02.jpg'
};

export function resolveEventCover(item) {
  if (!item) return EXHIBITION_COVERS[0];
  
  // If item already has a clean local cover or custom valid URL, preserve it
  if (item.cover_url && !item.cover_url.includes('photo-1579783902614-a3fb3927b675')) {
    return item.cover_url;
  }

  const text = `${item.title || ''} ${item.summary || ''} ${item.address || ''}`;

  // 1. Landmark & District Specifics
  if (text.includes('德基')) return LANDMARK_COVERS.deji;
  if (text.includes('新街口')) return LANDMARK_COVERS.xinjiekou;
  if (text.includes('玄武湖') || text.includes('情侣园')) return LANDMARK_COVERS.xuanwu;
  if (text.includes('夫子庙') || text.includes('秦淮') || text.includes('老门东')) return LANDMARK_COVERS.qinhuai;
  if (text.includes('牛首山')) return LANDMARK_COVERS.niushou;
  if (text.includes('大剧院') || text.includes('歌剧院')) return LANDMARK_COVERS.theater;
  if (text.includes('奥体') || text.includes('青奥')) return LANDMARK_COVERS.olympic;

  // 2. Keyword & Topic Specifics
  if (text.includes('手冲') || text.includes('冷萃')) return '/covers/benefit_specialty_pourover_02.jpg';
  if (text.includes('咖啡') || text.includes('拿铁')) return '/covers/benefit_coffee_01.jpg';
  if (text.includes('先锋书店') || text.includes('古籍') || text.includes('图书馆')) return '/covers/benefit_vintage_book_02.jpg';
  if (text.includes('书店') || text.includes('阅读')) return '/covers/benefit_bookstore_01.jpg';
  if (text.includes('可颂') || text.includes('欧包') || text.includes('面包')) return '/covers/benefit_croissant_bakery_02.jpg';
  if (text.includes('烘焙') || text.includes('甜品') || text.includes('蛋糕')) return '/covers/benefit_bakery_01.jpg';
  if (text.includes('抹茶') || text.includes('茶道') || text.includes('喝茶')) return '/covers/benefit_matcha_tea_02.jpg';
  if (text.includes('鸡尾酒') || text.includes('特调') || text.includes('Bar')) return '/covers/benefit_cocktail_bar_02.jpg';
  if (text.includes('精酿') || text.includes('酒') || text.includes('微醺')) return '/covers/benefit_beer_01.jpg';
  if (text.includes('木作') || text.includes('木工')) return '/covers/benefit_diy_woodwork_02.jpg';
  if (text.includes('陶艺') || text.includes('手作') || text.includes('拉坯')) return '/covers/benefit_pottery_01.jpg';
  if (text.includes('花') || text.includes('植') || text.includes('花市')) return '/covers/benefit_flower_01.jpg';

  if (text.includes('音乐节') || text.includes('户外音乐')) return '/covers/activity_rock_festival_02.jpg';
  if (text.includes('摇滚') || text.includes('Livehouse') || text.includes('乐队')) return '/covers/activity_livehouse_indie_02.jpg';
  if (text.includes('交响') || text.includes('管弦') || text.includes('爱乐')) return '/covers/activity_orchestra_classical_02.jpg';
  if (text.includes('音乐会') || text.includes('演唱会')) return '/covers/activity_concert_01.jpg';
  if (text.includes('戏剧') || text.includes('音乐剧')) return '/covers/activity_theater_musical_02.jpg';
  if (text.includes('话剧') || text.includes('剧场') || text.includes('舞台剧')) return '/covers/activity_theater_01.jpg';
  if (text.includes('夜市') || text.includes('小吃') || text.includes('逛吃')) return '/covers/activity_night_market_food_02.jpg';
  if (text.includes('市集') || text.includes('摆摊')) return '/covers/activity_market_01.jpg';
  if (text.includes('露营') || text.includes('天幕') || text.includes('帐篷')) return '/covers/activity_outdoor_glamping_02.jpg';
  if (text.includes('漫展') || text.includes('Cosplay') || text.includes('次元') || text.includes('动漫')) return '/covers/activity_anime_comic_02.jpg';
  if (text.includes('脱口秀') || text.includes('喜剧')) return '/covers/activity_comedy_club_02.jpg';
  if (text.includes('爵士')) return '/covers/activity_jazz_01.jpg';
  if (text.includes('滑板') || text.includes('街头')) return '/covers/activity_skate_street_02.jpg';
  if (text.includes('街舞') || text.includes('跳舞')) return '/covers/activity_dance_01.jpg';
  if (text.includes('骑行') || text.includes('夜跑') || text.includes('马拉松')) return '/covers/activity_cycling_01.jpg';

  if (text.includes('书法') || text.includes('碑帖') || text.includes('水墨')) return '/covers/exhibition_calligraphy_02.jpg';
  if (text.includes('国宝') || text.includes('青铜') || text.includes('文物') || text.includes('南博') || text.includes('博物馆')) return '/covers/exhibition_relics_02.jpg';
  if (text.includes('画廊') || text.includes('当代艺术')) return '/covers/exhibition_modern_gallery_02.jpg';
  if (text.includes('油画') || text.includes('美术馆') || text.includes('画展')) return '/covers/exhibition_painting_02.jpg';
  if (text.includes('雕塑') || text.includes('装置')) return '/covers/exhibition_sculpture_02.jpg';
  if (text.includes('光影') || text.includes('沉浸式') || text.includes('新媒体')) return '/covers/exhibition_digital_02.jpg';
  if (text.includes('陶瓷') || text.includes('紫砂') || text.includes('器物')) return '/covers/exhibition_ceramic_01.jpg';
  if (text.includes('摄影') || text.includes('影像') || text.includes('照片展')) return '/covers/exhibition_photography_02.jpg';
  if (text.includes('时装') || text.includes('服饰') || text.includes('纺织')) return '/covers/exhibition_fashion_02.jpg';
  if (text.includes('设计') || text.includes('建筑')) return '/covers/exhibition_design_01.jpg';

  // 3. Category Fallback with Deterministic Hash
  const hash = Math.abs(String(item.id || '').split('').reduce((a, b) => (a << 5) - a + b.charCodeAt(0), 0));
  if (item.category === '南京展会') {
    return EXHIBITION_COVERS[hash % EXHIBITION_COVERS.length];
  }
  if (item.category === '羊毛福利') {
    return BENEFIT_COVERS[hash % BENEFIT_COVERS.length];
  }
  return ACTIVITY_COVERS[hash % ACTIVITY_COVERS.length];
}
