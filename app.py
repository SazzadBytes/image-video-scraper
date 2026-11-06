"""
Image & Video Scraper + Downloader
====================================
A Flask web app that scrapes images and videos from the internet
based on a user-provided topic, lets you preview and select/deselect
items, then downloads only the selected ones as a ZIP.

Images: scraped from Bing Image Search
Videos: searched on YouTube via yt-dlp
"""

import os
import re
import sys
import json
import time
import shutil
import zipfile
import logging
import subprocess
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from flask import (
    Flask, render_template, request, jsonify,
    send_file, send_from_directory, Response
)
from PIL import Image

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────
DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

MAX_IMAGES = 100
MAX_VIDEOS = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ─── Helpers ─────────────────────────────────────────────────────

def sanitize_folder_name(name: str) -> str:
    """Create a safe folder name from the topic string."""
    safe = re.sub(r'[^\w\s-]', '', name).strip()
    safe = re.sub(r'[\s]+', '_', safe)
    return safe[:60] or "download"


def format_duration(seconds):
    """Convert seconds to M:SS or H:MM:SS string."""
    if not seconds or not isinstance(seconds, (int, float)):
        return ""
    seconds = int(seconds)
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


# ─── Image Scraping ─────────────────────────────────────────────

def scrape_image_urls(topic: str, count: int) -> list[dict]:
    """Scrape image items from Bing Image Search (both high-res murl and reliable turl fallback)."""
    items = []
    seen = set()

    for offset in range(0, max(count * 3, 35), 35):
        if len(items) >= count * 2:
            break

        search_url = (
            f"https://www.bing.com/images/search"
            f"?q={urllib.parse.quote(topic)}"
            f"&first={offset}&count=35"
        )

        try:
            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract strictly from 'iusc' search result anchors
        for a_tag in soup.find_all("a", {"class": "iusc"}):
            m_attr = a_tag.get("m")
            if not m_attr:
                continue
            murl_match = re.search(r'"murl"\s*:\s*"([^"]+)"', m_attr)
            turl_match = re.search(r'"turl"\s*:\s*"([^"]+)"', m_attr)

            murl = murl_match.group(1) if murl_match else None
            turl = turl_match.group(1) if turl_match else None

            # Skip if already seen or invalid
            key = murl or turl
            if not key or key in seen:
                continue

            seen.add(key)
            items.append({"murl": murl, "turl": turl})

        time.sleep(0.2)

    return items


def download_image(item: dict, save_path: Path, index: int) -> str | None:
    """
    Download a single image. Tries the full-res 'murl' first;
    if blocked or failed, falls back to the reliable Microsoft CDN 'turl'.
    """
    candidates = []
    if item.get("murl"):
        candidates.append(item["murl"])
    if item.get("turl") and item["turl"] not in candidates:
        candidates.append(item["turl"])

    for url in candidates:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8, stream=True)
            if resp.status_code != 200:
                continue

            content_type = resp.headers.get("Content-Type", "").lower()
            img_data = resp.content
            if len(img_data) < 1000:
                continue

            # Determine extension
            ext = ".jpg"
            if "png" in content_type or ".png" in url.lower():
                ext = ".png"
            elif "webp" in content_type or ".webp" in url.lower():
                ext = ".webp"
            elif "gif" in content_type or ".gif" in url.lower():
                ext = ".gif"

            # Validate image integrity
            img = Image.open(BytesIO(img_data))
            img.verify()

            filename = f"image_{index:03d}{ext}"
            with open(save_path / filename, "wb") as f:
                f.write(img_data)

            return filename

        except Exception:
            continue

    return None


# ─── Video Search (yt-dlp) ──────────────────────────────────────

def check_ytdlp():
    """Check if yt-dlp is available."""
    try:
        subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, timeout=10
        )
        return True
    except Exception:
        return False


def search_videos(topic: str, count: int) -> list[dict]:
    """Search YouTube for videos matching the topic using yt-dlp."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        f"ytsearch{count}:{topic}",
        "--dump-single-json",
        "--flat-playlist",
        "--no-warnings",
        "--quiet",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.error(f"yt-dlp search failed: {result.stderr}")
            return []

        data = json.loads(result.stdout)
        videos = []

        for entry in data.get("entries", []):
            vid_id = entry.get("id", "")
            if not vid_id:
                continue
            videos.append({
                "id": vid_id,
                "title": entry.get("title", "Untitled"),
                "url": entry.get("url", f"https://www.youtube.com/watch?v={vid_id}"),
                "thumbnail": f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg",
                "duration": format_duration(entry.get("duration")),
                "channel": entry.get("channel", entry.get("uploader", "")),
            })

        return videos

    except subprocess.TimeoutExpired:
        logger.error("yt-dlp search timed out")
        return []
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"yt-dlp search error: {e}")
        return []


def download_video(url: str, save_path: Path, index: int) -> str | None:
    """Download a video using yt-dlp. Returns the filename on success."""
    output_template = str(save_path / f"video_{index:03d}.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-o", output_template,
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--socket-timeout", "30",
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            # Find the downloaded file
            for f in save_path.iterdir():
                if f.name.startswith(f"video_{index:03d}.") and f.is_file():
                    return f.name

    except subprocess.TimeoutExpired:
        logger.error(f"Video download timed out: {url}")
    except Exception as e:
        logger.error(f"Video download error: {e}")

    return None


# ─── Routes ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scrape", methods=["POST"])
def scrape():
    """
    Phase 1: Scrape images (download for preview) and search videos (metadata only).
    Returns all items for the user to select/deselect before final download.
    """
    data = request.get_json()
    topic = data.get("topic", "").strip()
    image_count = min(int(data.get("imageCount", 0)), MAX_IMAGES)
    video_count = min(int(data.get("videoCount", 0)), MAX_VIDEOS)

    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    if image_count < 0 or video_count < 0:
        return jsonify({"error": "Counts must be non-negative"}), 400
    if image_count == 0 and video_count == 0:
        return jsonify({"error": "Request at least 1 image or 1 video"}), 400

    # Create session folder
    session_id = f"{sanitize_folder_name(topic)}_{int(time.time())}"
    save_path = DOWNLOAD_DIR / session_id
    save_path.mkdir(parents=True, exist_ok=True)

    # ── Scrape & download images ──
    images = []
    if image_count > 0:
        image_items = scrape_image_urls(topic, image_count)
        idx = 1
        for item in image_items:
            if len(images) >= image_count:
                break
            filename = download_image(item, save_path, idx)
            if filename:
                images.append({"filename": filename, "index": idx})
                idx += 1

    # ── Search videos ──
    videos = []
    if video_count > 0:
        if not check_ytdlp():
            logger.warning("yt-dlp not available, skipping video search")
        else:
            videos = search_videos(topic, video_count)

    return jsonify({
        "sessionId": session_id,
        "topic": topic,
        "images": images,
        "videos": videos,
    })


@app.route("/download-selected", methods=["POST"])
def download_selected():
    """
    Phase 2: Download only the selected videos, keep only selected images,
    package everything into a ZIP.
    """
    data = request.get_json()
    session_id = data.get("sessionId", "")
    selected_images = set(data.get("selectedImages", []))
    selected_videos = data.get("selectedVideos", [])

    save_path = DOWNLOAD_DIR / session_id
    if not save_path.exists():
        return jsonify({"error": "Session not found"}), 404

    # ── Remove unselected images ──
    for f in list(save_path.iterdir()):
        if f.is_file() and f.name.startswith("image_") and f.name not in selected_images:
            f.unlink()

    # ── Download selected videos ──
    video_results = []
    for i, video in enumerate(selected_videos, 1):
        url = video.get("url", "")
        if not url:
            continue
        filename = download_video(url, save_path, i)
        video_results.append({
            "title": video.get("title", ""),
            "success": filename is not None,
            "filename": filename,
        })

    # ── Create ZIP ──
    zip_path = DOWNLOAD_DIR / f"{session_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in save_path.iterdir():
            if f.is_file():
                zf.write(f, f.name)

    successful_videos = sum(1 for v in video_results if v["success"])
    total_items = len(selected_images) + successful_videos

    return jsonify({
        "success": True,
        "downloadUrl": f"/download-zip/{session_id}",
        "totalItems": total_items,
        "imageCount": len(selected_images),
        "videoCount": successful_videos,
        "videoResults": video_results,
    })


@app.route("/image/<folder>/<filename>")
def serve_image(folder, filename):
    """Serve a downloaded image for preview."""
    folder_path = DOWNLOAD_DIR / folder
    if not folder_path.exists():
        return "Not found", 404
    return send_from_directory(str(folder_path), filename)


@app.route("/download-zip/<folder>")
def download_zip(folder):
    """Send the final ZIP file."""
    zip_path = DOWNLOAD_DIR / f"{folder}.zip"
    if not zip_path.exists():
        return "Not found", 404

    return send_file(
        str(zip_path),
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{folder}.zip",
    )


# ─── Main ────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("\n" + "=" * 58)
    print(f"  🖼️  Image & Video Scraper running on port {port}")
    print("=" * 58 + "\n")
    app.run(debug=False, host="0.0.0.0", port=port)
