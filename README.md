# 🖼️ Image & Video Scraper

A web app that scrapes images and videos from the internet based on a topic — lets you **preview**, **select/deselect** items, and **download** only what you want as a ZIP.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-green?logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **🔍 Topic-based search** — Enter any topic and specify how many images & videos you want
- **🖼️ Image scraping** — Scrapes high-quality images from Bing Image Search
- **🎬 Video search** — Finds related YouTube videos via yt-dlp
- **👁️ Preview grid** — Beautiful dark-themed preview of all scraped content
- **☑️ Select / Deselect** — Click any item to toggle selection; bulk select/deselect buttons
- **📦 ZIP download** — Downloads only selected items packaged as a single ZIP file
- **✅ Image validation** — Verifies each image with Pillow (skips broken/tiny files)
- **📱 Responsive** — Works on desktop and mobile

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/image-video-scraper.git
cd image-video-scraper
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
python app.py
```

Open **http://localhost:8080** in your browser.

## 📖 How It Works

```
┌─────────────┐      ┌──────────────┐      ┌────────────────┐      ┌──────────────┐
│  1. Search   │ ──▶  │  2. Preview   │ ──▶  │  3. Select     │ ──▶  │  4. Download  │
│  Enter topic │      │  See results  │      │  Pick items    │      │  Get ZIP      │
│  + counts    │      │  in a grid    │      │  you want      │      │  file         │
└─────────────┘      └──────────────┘      └────────────────┘      └──────────────┘
```

1. **Search** — Enter a topic (e.g., "mountain landscape"), set image count (up to 100) and video count (up to 20)
2. **Preview** — The app scrapes Bing Images and searches YouTube, then displays everything in a grid
3. **Select** — All items are selected by default. Click any card to deselect it. Use the toolbar buttons for bulk actions
4. **Download** — Hit "Download Selected" — the app downloads the chosen videos, packages everything into a ZIP, and gives you a download link

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, Flask |
| Image Scraping | Requests, BeautifulSoup4 |
| Image Validation | Pillow |
| Video Search & Download | yt-dlp (YouTube) |
| Frontend | Vanilla HTML/CSS/JS |
| Packaging | ZIP (built-in) |

## 📁 Project Structure

```
├── app.py                 # Flask backend — scraping, downloading, API routes
├── templates/
│   └── index.html         # Frontend — dark-themed UI with preview grid
├── requirements.txt       # Python dependencies
├── .gitignore
├── downloads/             # Auto-created — stores scraped files (git-ignored)
└── README.md
```

## ⚙️ Configuration

In `app.py` you can adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_IMAGES` | 100 | Maximum images per search |
| `MAX_VIDEOS` | 20 | Maximum videos per search |
| Port | 8080 | Server port (change in `app.run()`) |

## ⚠️ Disclaimer

This tool is for **personal/educational use only**. Please respect:
- Website terms of service
- Copyright and intellectual property rights
- Rate limits and robots.txt policies

The developers are not responsible for how this tool is used.

## 📄 License

MIT License — feel free to use, modify, and distribute.
