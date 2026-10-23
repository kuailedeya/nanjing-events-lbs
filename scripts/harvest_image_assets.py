"""
Script to harvest and optimize local high-resolution cover images
from Wikimedia Commons and verified open stock repositories.
Crops all images to standard 16:9 Bento card aspect ratio (640x360).
"""
import os
import sys
import io
import json
import shutil
import urllib.request
import urllib.parse
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_COVERS_DIR = BASE_DIR / "frontend" / "public" / "covers"
ASSETS_COVERS_DIR = BASE_DIR / "assets" / "covers"

PUBLIC_COVERS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_COVERS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_WIDTH = 640
TARGET_HEIGHT = 360
TARGET_ASPECT = TARGET_WIDTH / TARGET_HEIGHT

ASSET_TASKS = [
    # 1. 南京展会 (Exhibitions & Art Galleries)
    ("exhibition_museum_01", "Nanjing Museum"),
    ("exhibition_art_01", "Art gallery exhibition interior"),
    ("exhibition_sculpture_01", "Contemporary sculpture modern art"),
    ("exhibition_painting_01", "Oil painting museum gallery"),
    ("exhibition_digital_01", "Digital light art installation"),
    ("exhibition_ceramic_01", "Ceramic museum exhibition"),
    ("exhibition_photo_01", "Photography exhibition gallery"),
    ("exhibition_design_01", "Modern architecture exhibition"),
    
    # 2. 南京同城活动 (Live Activities, Music, Drama, Outdoor)
    ("activity_concert_01", "Live music concert stage lights"),
    ("activity_rock_01", "Rock concert crowd festival"),
    ("activity_theater_01", "Theater drama performance stage"),
    ("activity_market_01", "Outdoor night market food stalls"),
    ("activity_camping_01", "Outdoor camping tent night"),
    ("activity_cosplay_01", "Anime convention cosplay"),
    ("activity_jazz_01", "Jazz performance live club"),
    ("activity_dance_01", "Street dance breakdance stage"),
    ("activity_cycling_01", "City bicycle urban night cycling"),

    # 3. 羊毛福利与探店生活 (Benefits, Cafes, Books, Bakery)
    ("benefit_coffee_01", "Latte art specialty coffee cup"),
    ("benefit_bookstore_01", "Independent bookstore library interior"),
    ("benefit_bakery_01", "Artisan bakery fresh bread pastries"),
    ("benefit_dessert_01", "Afternoon tea pastry cake"),
    ("benefit_beer_01", "Craft beer brewery taproom"),
    ("benefit_flower_01", "Flower market flower shop bouquet"),
    ("benefit_pottery_01", "Ceramic pottery wheel hands"),
    ("benefit_lifestyle_01", "Creative gift stationery craft"),

    # 4. 南京地标风貌 (Nanjing Iconic Landmarks)
    ("landmark_xinjiekou_01", "Xinjiekou Nanjing skyline"),
    ("landmark_xuanwu_01", "Xuanwu Lake Nanjing landscape"),
    ("landmark_qinhuai_01", "Qinhuai River Nanjing night lanterns"),
    ("landmark_theater_01", "Jiangsu Centre for the Performing Arts"),
    ("landmark_olympic_01", "Nanjing Olympic Sports Centre")
]

FALLBACK_URLS = [
    "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518998053901-5348d3961a04?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=800&q=80",
    "https://fastly.picsum.photos/id/1036/640/360.jpg?hmac=BaGywLhHWuvdE_Ggx1K8KE__TMVH0QyfML6W8_Ch9ag",
    "https://fastly.picsum.photos/id/42/640/360.jpg?hmac=9z8L1_qW1N4tP8qJvD3jK7w",
    "https://fastly.picsum.photos/id/24/640/360.jpg?hmac=1v4_qP2l3X8rT9s"
]

def search_wikimedia_image(query: str):
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
        print(f"  [Wikimedia Search Error] {query}: {e}")
    return None

def crop_and_optimize(image_bytes: bytes, out_path: Path):
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        w, h = img.size
        curr_aspect = w / h
        
        if curr_aspect > TARGET_ASPECT:
            # Too wide: crop left & right
            new_w = int(h * TARGET_ASPECT)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            # Too tall: crop top & bottom (favoring upper center)
            new_h = int(w / TARGET_ASPECT)
            top = max(0, int((h - new_h) * 0.35))
            img = img.crop((0, top, w, top + new_h))
            
        img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        img.save(out_path, "JPEG", quality=84, progressive=True, optimize=True)

def main():
    print(f"Starting harvest of {len(ASSET_TASKS)} image assets...")
    success_count = 0
    manifest = {}

    for idx, (asset_key, query) in enumerate(ASSET_TASKS):
        filename = f"{asset_key}.jpg"
        target_file = PUBLIC_COVERS_DIR / filename
        
        # If already downloaded and valid, skip
        if target_file.exists() and target_file.stat().st_size > 5000:
            print(f"[{idx+1}/{len(ASSET_TASKS)}] {filename} already exists ({target_file.stat().st_size} bytes).")
            # Sync to assets covers
            shutil.copy2(target_file, ASSETS_COVERS_DIR / filename)
            manifest[asset_key] = f"/covers/{filename}"
            success_count += 1
            continue

        print(f"[{idx+1}/{len(ASSET_TASKS)}] Harvesting '{asset_key}' via query: '{query}'...")
        image_url = search_wikimedia_image(query)
        image_bytes = None

        if image_url:
            try:
                req = urllib.request.Request(
                    image_url,
                    headers={"User-Agent": "NanjingLBS/1.0 (https://github.com/kuailedeya/nanjing-events-lbs)"}
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    image_bytes = r.read()
                    print(f"  -> Downloaded {len(image_bytes)} bytes from Wikimedia.")
            except Exception as e:
                print(f"  -> Failed downloading from Wikimedia: {e}")

        # Fallback if Wikimedia failed
        if not image_bytes or len(image_bytes) < 2000:
            fb_url = FALLBACK_URLS[idx % len(FALLBACK_URLS)]
            print(f"  -> Using fallback URL: {fb_url[:60]}...")
            try:
                req = urllib.request.Request(fb_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    image_bytes = r.read()
            except Exception as e:
                print(f"  -> Fallback download failed: {e}")

        if image_bytes:
            try:
                crop_and_optimize(image_bytes, target_file)
                # Copy to backend assets
                shutil.copy2(target_file, ASSETS_COVERS_DIR / filename)
                manifest[asset_key] = f"/covers/{filename}"
                print(f"  ✓ Processed and saved: {filename} ({target_file.stat().st_size // 1024} KB)")
                success_count += 1
            except Exception as e:
                print(f"  ✗ Pillow processing failed for {filename}: {e}")
        else:
            print(f"  ✗ Could not obtain image for {filename}")

    # Write manifest JSON
    manifest_path = BASE_DIR / "frontend" / "public" / "covers" / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    print(f"\nHarvest finished: {success_count}/{len(ASSET_TASKS)} assets successfully downloaded and optimized.")

if __name__ == "__main__":
    main()
