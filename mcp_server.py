"""
Image Downloader MCP server
===========================
Exposes the Flask app's Bing search + download logic as MCP tools so Claude
(desktop app) can fetch topic images straight into a video project folder.

Run by the Claude desktop app over stdio (see MCP_SETUP.md). No Flask server needed.
"""
import time
import zipfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Reuse the scraper functions from app.py (app.py does not start Flask on import)
from app import scrape_image_urls, download_image, sanitize_folder_name, DOWNLOAD_DIR

# Only allow saving inside these roots (edit if you keep projects elsewhere)
ALLOWED_ROOTS = [
    DOWNLOAD_DIR.resolve(),
    (Path.home() / "Desktop" / "ContentSite").resolve(),
]

mcp = FastMCP("image-downloader")


def _resolve_dest(dest_folder: str | None, topic: str) -> Path:
    if not dest_folder:
        return DOWNLOAD_DIR / f"{sanitize_folder_name(topic)}_{int(time.time())}"
    p = Path(dest_folder).expanduser().resolve()
    if not any(p == r or r in p.parents for r in ALLOWED_ROOTS):
        raise ValueError(f"dest_folder must be inside one of: {[str(r) for r in ALLOWED_ROOTS]}")
    return p


@mcp.tool()
def download_images(topic: str, count: int = 5, dest_folder: str | None = None, prefix: str = "") -> dict:
    """Search the web for images about `topic` and download up to `count` (1-30) of them.

    dest_folder: absolute folder to save into (must be inside the app's downloads folder or
    ~/Desktop/ContentSite). Omit to save under the app's downloads folder.
    prefix: optional filename prefix, e.g. "court_" -> court_image_001.jpg.
    Returns the saved file paths and their source URLs.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("topic is required")
    count = max(1, min(int(count), 30))
    dest = _resolve_dest(dest_folder, topic)
    dest.mkdir(parents=True, exist_ok=True)

    urls = scrape_image_urls(topic, count)
    saved, idx = [], 1
    for url in urls:
        if len(saved) >= count:
            break
        name = download_image(url, dest, idx)
        if name:
            final = dest / f"{prefix}{name}" if prefix else dest / name
            if prefix:
                (dest / name).rename(final)
            saved.append({"path": str(final), "source_url": url})
            idx += 1

    # keep a simple source log for credits
    with open(dest / "sources.txt", "a", encoding="utf-8") as f:
        for s in saved:
            f.write(f"{Path(s['path']).name}\t{topic}\t{s['source_url']}\n")

    return {"topic": topic, "folder": str(dest), "downloaded": len(saved), "images": saved}


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


@mcp.tool()
def get_images_zip(topic: str, count: int = 10, dest_folder: str | None = None) -> dict:
    """Give a topic, get back a ZIP file of images about it.

    Searches the web for `topic`, downloads up to `count` (1-50) images, and packs them
    (plus sources.txt with each image's source URL) into a .zip.
    dest_folder: optional folder to put the zip in (must be inside the app's downloads
    folder or ~/Desktop/ContentSite). Omit to save under the app's downloads folder.
    Returns the absolute zip_path, image count, and the folder holding the loose images.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("topic is required")
    count = max(1, min(int(count), 50))

    stamp = f"{sanitize_folder_name(topic)}_{int(time.time())}"
    img_dir = DOWNLOAD_DIR / stamp
    img_dir.mkdir(parents=True, exist_ok=True)

    urls = scrape_image_urls(topic, count)
    saved, idx = [], 1
    for url in urls:
        if len(saved) >= count:
            break
        name = download_image(url, img_dir, idx)
        if name:
            saved.append((name, url))
            idx += 1

    if not saved:
        raise RuntimeError(f"No images could be downloaded for '{topic}'. Try a different wording.")

    with open(img_dir / "sources.txt", "w", encoding="utf-8") as f:
        for name, url in saved:
            f.write(f"{name}\t{topic}\t{url}\n")

    zip_dir = _resolve_dest(dest_folder, topic) if dest_folder else DOWNLOAD_DIR
    zip_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / f"{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(img_dir.iterdir()):
            if f.is_file():
                zf.write(f, f.name)

    return {
        "topic": topic,
        "zip_path": str(zip_path),
        "zip_size_kb": round(zip_path.stat().st_size / 1024, 1),
        "downloaded": len(saved),
        "images_folder": str(img_dir),
    }


@mcp.tool()
def list_image_folders() -> list[dict]:
    """List folders in the app's downloads directory with their image counts."""
    out = []
    for d in sorted(DOWNLOAD_DIR.iterdir()):
        if d.is_dir():
            n = sum(1 for f in d.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"})
            out.append({"folder": str(d), "images": n})
    return out


if __name__ == "__main__":
    mcp.run()
