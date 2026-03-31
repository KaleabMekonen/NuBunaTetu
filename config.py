"""
NuBunaTetu – Configuration
ኑ ቡና ጠጡ · "Come and let's have coffee."
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")      # Required — script writing (FREE at aistudio.google.com)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")  # Optional — Telegram delivery
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")    # Optional — Telegram delivery
# Images: Pollinations.ai — completely free, no key needed!

# TikTok API (not needed yet — posting is done manually for now)
# TIKTOK_CLIENT_KEY    = os.getenv("TIKTOK_CLIENT_KEY", "")
# TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
# TIKTOK_ACCESS_TOKEN  = os.getenv("TIKTOK_ACCESS_TOKEN", "")

# ── Content Settings ───────────────────────────────────────────────────────────
# Target audience language preference
SCRIPT_LANGUAGE = "amharic-english-mixed"   # "amharic" | "english" | "amharic-english-mixed"

# Video duration in seconds (TikTok sweet spot: 30–60s)
VIDEO_DURATION_SEC = 45

# How many trend candidates to fetch before picking the best one
TREND_CANDIDATES = 5

# ── Video Output Settings ──────────────────────────────────────────────────────
OUTPUT_DIR     = "output"           # Where generated videos are saved
VIDEO_WIDTH    = 1080
VIDEO_HEIGHT   = 1920              # 9:16 portrait for TikTok
FONT_SIZE      = 52
CAPTION_COLOR  = "#FFFFFF"
CAPTION_BG     = "#000000"         # Semi-transparent caption background

# ── Entertainment Sources (Ethiopian) ─────────────────────────────────────────
# Focus: music, comedy, food, fashion, football, culture — NO politics or news
ENTERTAINMENT_SOURCES = [
    "https://www.youtube.com/results?search_query=ethiopian+music+2026",
    "https://www.youtube.com/results?search_query=ethiopian+comedy+2026",
    "https://ethiotube.net",          # Ethiopian video entertainment
    "https://www.habeshaview.com",    # Ethiopian showbiz & celebrity
]

# ── TikTok Trending Hashtags to Monitor ───────────────────────────────────────
ETHIOPIAN_HASHTAGS = [
    "EthiopianMusic",
    "HabeshaComedy",
    "EthiopianFood",
    "EthiopianFashion",
    "HabeshaVibes",
    "EthiopianDance",
    "AddisAbeba",
    "EthiopianTikTok",
    "HabeshaFood",
    "EthiopianFootball",
]

# ── Entertainment Categories to Rotate Through ────────────────────────────────
CONTENT_CATEGORIES = [
    "Ethiopian music & artists",
    "Ethiopian comedy & skits",
    "Ethiopian food & recipes",
    "Ethiopian fashion & style",
    "Ethiopian football & sports",
    "Ethiopian culture & traditions",
    "Ethiopian dance & performances",
    "Habesha celebrity news & gossip",
]

# ── TikTok Posting Schedule ────────────────────────────────────────────────────
POST_HOUR   = 19    # 7 PM Ethiopian time (UTC+3)
POST_MINUTE = 0
