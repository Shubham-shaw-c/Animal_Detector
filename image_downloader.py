"""
image_downloader.py
High-speed, multi-threaded image downloader and validator for new animal classes.
Fetches, deduplicates, verifies with PIL, and saves images to animal_datasets/<animal>/.
"""

import hashlib
import html
from io import BytesIO
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

from animal_validator import validate_new_animal

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DATASET_ROOT = "animal_datasets"


class ImageDownloadTask:
    def __init__(self, animal_name: str, target_count: int = 100):
        self.animal_name = animal_name
        self.target_count = target_count
        self.downloaded_count = 0
        self.validated_count = 0
        self.status = "idle"  # idle, downloading, validating, completed, failed
        self.message = "Initializing download..."
        self.error = None
        self.lock = threading.Lock()
        self.folder_path = None
        self.seen_hashes = set()

    def get_progress(self):
        with self.lock:
            percent = 0
            if self.target_count > 0:
                percent = min(100, int((self.validated_count / self.target_count) * 100))
            return {
                "status": self.status,
                "animal": self.animal_name,
                "target": self.target_count,
                "downloaded": self.downloaded_count,
                "validated": self.validated_count,
                "percent": percent,
                "message": self.message,
                "error": self.error,
                "folder": self.folder_path
            }


# Global active download tracker
_active_download = None
_download_lock = threading.Lock()


def get_current_download_status():
    global _active_download
    with _download_lock:
        if _active_download is None:
            return {"status": "idle", "message": "No active download."}
        return _active_download.get_progress()


def validate_animal_name(name: str, existing_classes: list = None) -> tuple[bool, str, str]:
    """
    Validates animal name against zoological dictionary, path traversal, empty input, and duplicates.
    Returns: (is_valid, normalized_name, error_message)
    """
    is_valid, normalized, display_name, error_msg = validate_new_animal(name, existing_classes)
    return is_valid, normalized, error_msg


def fetch_bing_image_urls(query: str, max_links: int = 150) -> list[str]:
    """Scrapes direct image URLs from Bing Images Async."""
    urls = []
    seen = set()
    page = 1
    count_per_page = 35

    while len(urls) < max_links and page <= 5:
        first_index = (page - 1) * count_per_page + 1
        params = urllib.parse.urlencode({
            "q": query,
            "first": first_index,
            "count": count_per_page,
            "adlt": "off",
            "qft": "+filterui:photo-photo"
        })
        req_url = f"https://www.bing.com/images/async?{params}"
        
        try:
            req = urllib.request.Request(req_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                matches = re.findall(r'murl&quot;:&quot;(.*?)&quot;', content)
                if not matches:
                    break
                for m in matches:
                    u = html.unescape(m).replace(" ", "%20")
                    if u.startswith("http") and u not in seen:
                        seen.add(u)
                        urls.append(u)
                        if len(urls) >= max_links:
                            break
        except Exception:
            break
        
        page += 1

    return urls


def download_and_verify_single(url: str, headers: dict) -> tuple[bool, Image.Image or None, str or None]:
    """Downloads an image from URL and verifies with PIL."""
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            raw_bytes = response.read()

        if len(raw_bytes) < 3000:  # Ignore tiny/stub files (<3KB)
            return False, None, None

        # Hash for deduplication
        img_hash = hashlib.md5(raw_bytes).hexdigest()

        # PIL integrity verification
        bio = BytesIO(raw_bytes)
        img = Image.open(bio)
        img.verify()

        # Re-open after verify() closes it
        bio.seek(0)
        img = Image.open(bio)

        # Dimension filter: must be at least 120x120
        width, height = img.size
        if width < 120 or height < 120:
            return False, None, None

        # Convert to RGB
        rgb_img = img.convert("RGB")
        return True, rgb_img, img_hash
    except Exception:
        return False, None, None


def run_download_pipeline(task: ImageDownloadTask):
    """Executes the multi-threaded image gathering & validation pipeline."""
    # 0. Strict Zoological Animal Name Verification Guard
    is_valid, _, display_name, err = validate_new_animal(task.animal_name)
    if not is_valid:
        task.status = "failed"
        task.error = err or f"'{task.animal_name}' is not recognized as a valid animal species."
        task.message = f"Process aborted: {task.error}"
        print(f"[DOWNLOAD ABORTED] Refusing to create folder or download images: {task.message}")
        return

    task.status = "downloading"
    task.message = f"Creating dataset folder for {task.animal_name}..."

    # 1. Setup folder ONLY after successful animal validation
    folder = os.path.join(DATASET_ROOT, task.animal_name)
    os.makedirs(folder, exist_ok=True)
    task.folder_path = folder

    # Find highest existing image index
    existing_files = os.listdir(folder)
    highest_idx = 0
    for f in existing_files:
        match = re.match(r"Image_(\d+)\.", f, re.IGNORECASE)
        if match:
            highest_idx = max(highest_idx, int(match.group(1)))

    task.message = f"Searching high-resolution images for {task.animal_name}..."
    print(f"[DOWNLOAD] Fetching dataset images for '{task.animal_name.capitalize()}'...")

    # 2. Collect image URLs from multiple search query variations
    queries = [
        f"{task.animal_name} animal photo",
        f"{task.animal_name} wildlife high resolution",
        f"wild {task.animal_name} portrait"
    ]

    all_urls = []
    for q in queries:
        urls = fetch_bing_image_urls(q, max_links=80)
        for u in urls:
            if u not in all_urls:
                all_urls.append(u)
        if len(all_urls) >= task.target_count * 2:
            break

    if not all_urls:
        task.status = "failed"
        task.error = "No images found. Please verify animal name or internet connection."
        task.message = "Failed: No images found."
        return

    task.message = f"Found {len(all_urls)} candidate images. Downloading & verifying with PIL..."
    task.status = "validating"

    # 3. Download concurrently
    next_index = highest_idx + 1
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {
            executor.submit(download_and_verify_single, url, HEADERS): url
            for url in all_urls
        }

        for future in as_completed(future_to_url):
            if task.validated_count >= task.target_count:
                break

            with task.lock:
                task.downloaded_count += 1

            try:
                success, img, img_hash = future.result()
                if success and img and img_hash:
                    with task.lock:
                        if img_hash in task.seen_hashes:
                            continue
                        task.seen_hashes.add(img_hash)
                        
                        save_path = os.path.join(folder, f"Image_{next_index}.jpg")
                        img.save(save_path, "JPEG", quality=92)
                        next_index += 1
                        task.validated_count += 1
                        task.message = f"Validated {task.validated_count}/{task.target_count} images..."
            except Exception as e:
                pass

    if task.validated_count >= max(10, int(task.target_count * 0.2)):
        task.status = "completed"
        task.message = f"Successfully downloaded and verified {task.validated_count} images for {task.animal_name}!"
        print(f"[DOWNLOAD] Finished: {task.validated_count} verified images saved to {folder}")
    else:
        task.status = "failed"
        task.error = f"Only {task.validated_count} valid images could be obtained."
        task.message = task.error


def start_image_download(animal_name: str, target_count: int = 100) -> tuple[bool, str]:
    """Starts the download process in a background thread."""
    global _active_download
    with _download_lock:
        if _active_download and _active_download.status in ["downloading", "validating"]:
            return False, "Another download task is already in progress."

        task = ImageDownloadTask(animal_name=animal_name, target_count=target_count)
        _active_download = task

        thread = threading.Thread(target=run_download_pipeline, args=(task,), daemon=True)
        thread.start()
        return True, f"Started downloading images for '{animal_name}'."

