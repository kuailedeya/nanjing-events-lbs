"""
Batch 2 asset harvester: downloads 28 additional high-resolution photos
covering niche exhibition, livehouse, cafes, Nanjing landmarks, and lifestyle.
"""
import io
import json
import shutil
import urllib.request
import urllib.parse
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_COVERS_DIR = BASE_DIR / "frontend" / "public" / "covers"
DIST_COVERS_DIR = BASE_DIR / "frontend" / "dist" / "covers"
ASSETS_COVERS_DIR = BASE_DIR / "assets" / "covers"

for d in (PUBLIC_COVERS_DIR, DIST_COVERS_DIR, ASSETS_COVERS_DIR):
    d.mkdir(parents=True, exist_ok=True)

TARGET_WIDTH = 640
TARGET_HEIGHT = 360
TARGET_ASPECT = TARGET_WIDTH / TARGET_HEIGHT

BATCH2_TASKS = [
    # 展会美术馆
    ("exhibition_modern_gallery_02", "Contemporary art gallery white cube"),
    ("exhibition_sculpture_02", "Marble sculpture museum art"),
    ("exhibition_digital_02", "Immersive light tunnel digital art"),
    ("exhibition_painting_02", "Impressionist oil painting gallery"),
    ("exhibition_relics_02", "Chinese bronze artifact museum"),
    ("exhibition_photography_02", "Photography exhibition prints gallery"),
    ("exhibition_fashion_02", "Fashion design exhibition garment"),
    ("exhibition_calligraphy_02", "Chinese calligraphy scroll ink"),

    # 活动演出
    ("activity_rock_festival_02", "Rock festival stage crowd hands"),
    ("activity_livehouse_indie_02", "Livehouse music stage guitar microphone"),
    ("activity_orchestra_classical_02", "Symphony orchestra concert hall"),
    ("activity_night_market_food_02", "Asian night market street food stalls"),
    ("activity_anime_comic_02", "Anime convention booth cosplay"),
    ("activity_outdoor_glamping_02", "Glamping tent lights forest night"),
    ("activity_skate_street_02", "Skatepark skateboarding urban"),
    ("activity_comedy_club_02", "Standup comedy microphone spotlight"),
    ("activity_theater_musical_02", "Theater stage red curtains lights"),

    # 羊毛福利与生活
    ("benefit_specialty_pourover_02", "Pour over coffee dripper kettle"),
    ("benefit_croissant_bakery_02", "Fresh baked croissants pastry bakery"),
    ("benefit_matcha_tea_02", "Matcha green tea bowl whisk"),
    ("benefit_vintage_book_02", "Spiral staircase library bookstore books"),
    ("benefit_cocktail_bar_02", "Craft cocktail glass bar lounge"),
    ("benefit_diy_woodwork_02", "Woodworking workshop tools craft"),
    ("benefit_florist_bouquet_02", "Florist flower bouquet fresh shop"),

    # 南京地标拓展
    ("landmark_purple_mountain_02", "Sun Yat-sen Mausoleum Nanjing"),
    ("landmark_ming_city_wall_02", "Nanjing City Wall Ming Dynasty"),
    ("landmark_deji_museum_02", "Deji Plaza Nanjing architecture"),
    ("landmark_niushou_mountain_02", "Niushoushan Nanjing palace")
]

FALLBACK_PICSUM = [
    "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518998053901-5348d3961a04?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=800&q=80"
]

def search_wikimedia(query: str):
    url = (
        "https://commons.wikimedia.org/w/api.php?action=query&format=json"
        f"&generator=search&gsrsearch={urllib.parse.quote(query)}"
        "&gsrnamespace=6&gsrlimit=5&prop=imageinfo&iiprop=url|thumburl&iiurlwidth=960"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NanjingLBS/1.0 (https://github.com/kuailedeya/nanjing-events-lbs)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid, pinfo in pages.items():
                ii = pinfo.get("imageinfo", [])
                if ii:
                    thumb = ii[0].get("thumburl") or ii[0].get("url")
                    if thumb and not thumb.lower().endswith((".svg", ".tif", ".tiff", ".pdf", ".ogg", ".webm")):
                        return thumb
    except Exception as e:
        print(f"  [Wikimedia Error] {query}: {e}")
    return None

def crop_and_save(image_bytes: bytes, out_path: Path):
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        w, h = img.size
        curr_aspect = w / h
        if curr_aspect > TARGET_ASPECT:
            new_w = int(h * TARGET_ASPECT)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / TARGET_ASPECT)
            top = max(0, int((h - new_h) * 0.35))
            img = img.crop((0, top, w, top + new_h))
        img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        img.save(out_path, "JPEG", quality=84, progressive=True, optimize=True)

def main():
    print(f"Starting batch 2 harvest of {len(BATCH2_TASKS)} assets...")
    saved = 0
    for idx, (key, query) in enumerate(BATCH2_TASKS):
        fn = f"{key}.jpg"
        target_public = PUBLIC_COVERS_DIR / fn
        if target_public.exists() and target_public.stat().st_size > 5000:
            print(f"[{idx+1}/{len(BATCH2_TASKS)}] {fn} already exists.")
            shutil.copy2(target_public, DIST_COVERS_DIR / fn)
            shutil.copy2(target_public, ASSETS_COVERS_DIR / fn)
            saved += 1
            continue

        print(f"[{idx+1}/{len(BATCH2_TASKS)}] Harvesting '{key}'...")
        thumb_url = search_wikimedia(query)
        image_bytes = None
        if thumb_url:
            try:
                req = urllib.request.Request(thumb_url, headers={"User-Agent": "NanjingLBS/1.0"})
                with urllib.request.urlopen(req, timeout=12) as r:
                    image_bytes = r.read()
            except Exception as e:
                print(f"  -> Download failed: {e}")

        if not image_bytes or len(image_bytes) < 3000:
            fb = FALLBACK_PICSUM[idx % len(FALLBACK_PICSUM)]
            try:
                req = urllib.request.Request(fb, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=12) as r:
                    image_bytes = r.read()
            except Exception as e:
                print(f"  -> Fallback failed: {e}")

        if image_bytes:
            try:
                crop_and_save(image_bytes, target_public)
                shutil.copy2(target_public, DIST_COVERS_DIR / fn)
                shutil.copy2(target_public, ASSETS_COVERS_DIR / fn)
                print(f"  ✓ Saved {fn} ({target_public.stat().st_size // 1024} KB)")
                saved += 1
            except Exception as e:
                print(f"  ✗ Pillow error for {fn}: {e}")
        else:
            print(f"  ✗ Failed to obtain {fn}")

    print(f"\nBatch 2 finished: {saved}/{len(BATCH2_TASKS)} saved.")

if __name__ == "__main__":
    main()
