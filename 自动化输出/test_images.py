#!/usr/bin/env python3
"""
Test image downloader and validator.
Downloads images from various sources (Unsplash, Pexels, direct URLs)
and verifies they are valid image files with size > 50KB.
"""

import os
import sys
import time
import requests
from pathlib import Path
from urllib.parse import urlparse

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

# Configuration
SAVE_DIR = Path(r"C:\Users\apple\Desktop\成功\img_test")
MIN_SIZE_KB = 50
TIMEOUT = 30
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Test URLs from various sources
TEST_URLS = {
    "Unsplash (random 800x600)": "https://source.unsplash.com/800x600/?nature",
    "Unsplash (random landscape)": "https://source.unsplash.com/1024x768/?landscape",
    "Unsplash (random cat)": "https://source.unsplash.com/640x480/?cat",
    "Pexels (direct photo 1)": "https://images.pexels.com/photos/459225/pexels-photo-459225.jpeg?auto=compress&cs=tinysrgb&w=800",
    "Pexels (direct photo 2)": "https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg?auto=compress&cs=tinysrgb&w=800",
    "Pexels (direct photo 3)": "https://images.pexels.com/photos/326055/pexels-photo-326055.jpeg?auto=compress&cs=tinysrgb&w=800",
    "Picsum (random image 1)": "https://picsum.photos/800/600.jpg",
    "Picsum (random image 2)": "https://picsum.photos/1024/768.jpg",
    "Lorem Flickr (nature)": "https://loremflickr.com/800/600/nature",
    "Lorem Flickr (city)": "https://loremflickr.com/800/600/city",
    "Placeholder (1920x1080)": "https://placehold.co/1920x1080.png",
    "Placeholder (800x600)": "https://placehold.co/800x600.jpg",
}


def download_image(url, save_path):
    """Download an image from URL to save_path. Returns (success, info_dict)."""
    info = {
        "url": url,
        "save_path": str(save_path),
        "file_size_bytes": 0,
        "file_size_kb": 0,
        "status_code": None,
        "content_type": None,
        "width": None,
        "height": None,
        "format": None,
        "valid_image": False,
        "meets_min_size": False,
        "error": None,
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True,
                                allow_redirects=True)
        info["status_code"] = response.status_code
        info["content_type"] = response.headers.get("Content-Type", "unknown")
        info["final_url"] = response.url

        if response.status_code != 200:
            info["error"] = f"HTTP {response.status_code}"
            return False, info

        # Write to file
        total_bytes = 0
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                total_bytes += len(chunk)

        info["file_size_bytes"] = total_bytes
        info["file_size_kb"] = round(total_bytes / 1024, 2)
        info["meets_min_size"] = total_bytes >= MIN_SIZE_KB * 1024

        # Validate with PIL
        try:
            with Image.open(save_path) as img:
                img.verify()  # Verify it's a valid image

            # Re-open to get dimensions (verify() closes the image)
            with Image.open(save_path) as img:
                info["width"], info["height"] = img.size
                info["format"] = img.format
                info["valid_image"] = True

        except Exception as e:
            info["error"] = f"Invalid image: {e}"
            # Clean up invalid file
            try:
                os.remove(save_path)
            except OSError:
                pass
            return False, info

        return True, info

    except requests.exceptions.Timeout:
        info["error"] = "Request timed out"
        return False, info
    except requests.exceptions.ConnectionError as e:
        info["error"] = f"Connection error: {e}"
        return False, info
    except requests.exceptions.RequestException as e:
        info["error"] = f"Request error: {e}"
        return False, info
    except Exception as e:
        info["error"] = f"Unexpected error: {e}"
        return False, info


def sanitize_filename(name):
    """Create a safe filename from a label."""
    safe = "".join(c if c.isalnum() or c in ("-", "_", " ") else "_" for c in name)
    return safe.strip().replace(" ", "_")[:60]


def get_extension(url, content_type):
    """Guess file extension from URL or content type."""
    # Try from content type first
    ct_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/svg+xml": ".svg",
    }
    for ct, ext in ct_map.items():
        if ct in (content_type or ""):
            return ext

    # Try from URL path
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
        if path.endswith(ext):
            return ext

    return ".jpg"  # Default


def main():
    print("=" * 70)
    print("  IMAGE DOWNLOAD & VALIDATION TEST")
    print("=" * 70)

    # Create output directory
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {SAVE_DIR}")
    print(f"Minimum size threshold: {MIN_SIZE_KB} KB")
    print(f"Testing {len(TEST_URLS)} image URLs...\n")

    results = []
    valid_images = []

    for label, url in TEST_URLS.items():
        print(f"[{len(results)+1}/{len(TEST_URLS)}] {label}")
        print(f"  URL: {url}")

        # Determine filename
        ext = get_extension(url, "")  # content type unknown until we download
        filename = sanitize_filename(label) + ext
        save_path = SAVE_DIR / filename

        # Avoid overwrites
        counter = 1
        while save_path.exists():
            save_path = SAVE_DIR / f"{sanitize_filename(label)}_{counter}{ext}"
            counter += 1

        success, info = download_image(url, save_path)

        # If we got a different format, rename
        if info["format"] and info["valid_image"]:
            correct_ext = f".{info['format'].lower()}"
            if correct_ext == ".jpeg":
                correct_ext = ".jpg"
            if save_path.suffix.lower() != correct_ext:
                new_path = save_path.with_suffix(correct_ext)
                if not new_path.exists():
                    save_path.rename(new_path)
                    info["save_path"] = str(new_path)
                    save_path = new_path

        if success:
            status = "VALID"
            if info["meets_min_size"]:
                status += " (>50KB)"
                valid_images.append(info)
            else:
                status += f" (TOO SMALL: {info['file_size_kb']}KB)"

            print(f"  Status: {status}")
            print(f"  Size: {info['file_size_kb']} KB | "
                  f"Dimensions: {info['width']}x{info['height']} | "
                  f"Format: {info['format']}")
        else:
            print(f"  Status: FAILED - {info['error']}")

        results.append(info)
        print()

        # Small delay between requests to be polite
        time.sleep(0.5)

    # Summary report
    print("=" * 70)
    print("  SUMMARY REPORT")
    print("=" * 70)

    total = len(results)
    downloaded = sum(1 for r in results if r["valid_image"])
    valid_count = len(valid_images)
    failed = total - downloaded

    print(f"\nTotal URLs tested:    {total}")
    print(f"Successful downloads: {downloaded}")
    print(f"Valid images >50KB:   {valid_count}")
    print(f"Failed:               {failed}")

    if valid_images:
        print(f"\n--- Valid Images (> {MIN_SIZE_KB} KB) ---")
        for info in valid_images:
            print(f"  [{info['format']}] {info['width']}x{info['height']} "
                  f"| {info['file_size_kb']} KB | {Path(info['save_path']).name}")

    if failed > 0:
        print(f"\n--- Failed Downloads ---")
        for info in results:
            if not info["valid_image"]:
                print(f"  {info['error']} | {info['url'][:80]}")

    print(f"\nAll images saved to: {SAVE_DIR}")
    print("=" * 70)

    return 0 if valid_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
