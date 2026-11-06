# Image Downloader MCP

Claude gives a topic → this app searches, downloads images, and returns a ZIP file path.

## Already set up (6 Nov 2026)

- Python env: `.venv/` in this folder (deps from requirements.txt; `mcp` pinned below 2.x)
- Claude Code: registered at user scope as `image-downloader` (works in every project)
- Claude desktop chat app: added to `~/Library/Application Support/Claude/claude_desktop_config.json`
  (backup saved next to it as `claude_desktop_config.json.bak`). Quit and reopen the app to load it.

The Flask web app (`python app.py`, http://localhost:8080) is not needed for MCP — the
MCP server calls the same search/download code directly.

## Tools

- `get_images_zip(topic, count=10, dest_folder=None)` → `{zip_path, downloaded, images_folder, ...}`
  The zip holds the images plus `sources.txt` (source URL for each image).
- `download_images(topic, count, dest_folder, prefix)` → loose images + sources.txt
- `list_image_folders()`

Example prompt to Claude: "Get me a zip of 10 images of Dhaka old town."

## Re-setup from scratch

    cd "/Users/sazzadhossain/Desktop/Building/Download from the internet"
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    claude mcp add -s user image-downloader -- "$PWD/.venv/bin/python" "$PWD/mcp_server.py"

Note: images found this way are owned by whoever published them. Check rights before posting.
