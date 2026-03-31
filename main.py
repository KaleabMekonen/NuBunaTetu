"""
NuBunaTetu – Main Orchestrator
ኑ ቡና ጠጡ · "Come and let's have coffee."

Runs the full pipeline:
  1. Discover trending Ethiopian topics
  2. Generate Amharic/English mixed script
  3. Create TikTok video
  4. Send video + caption to your Telegram
  5. Save video to output/ folder — ready for manual TikTok upload

Usage:
  python main.py                                       # Run full pipeline
  python main.py --topic "Ethiopian coffee ceremony"   # Use a custom topic
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("nubunатету.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# ── Imports ────────────────────────────────────────────────────────────────────
import config
from agent.trend_discovery  import get_trending_topics, pick_best_topic, TrendingTopic
from agent.script_generator import generate_script
from agent.video_creator    import create_video
from agent.telegram_reviewer import TelegramReviewer


def run_pipeline(custom_topic: str = None) -> None:
    """
    Executes the full NuBunaTetu pipeline for one video.
    Saves video to output/ and sends it to Telegram for manual upload.
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("  NuBunaTetu — ኑ ቡና ጠጡ · 'Come and let's have coffee.'")
    logger.info(f"  Starting pipeline at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # ── Step 1: Discover trends ────────────────────────────────────────────────
    logger.info("\n📌 STEP 1: Trend Discovery")

    if custom_topic:
        logger.info(f"   Using custom topic: {custom_topic}")
        topic = TrendingTopic(
            title=custom_topic,
            description=f"User-specified topic: {custom_topic}",
            source="Manual",
            score=100
        )
    else:
        topics = get_trending_topics(n=config.TREND_CANDIDATES)
        topic  = pick_best_topic(topics)
        logger.info(f"   Selected: {topic.title} (score: {topic.score})")

    # ── Step 2: Generate script ────────────────────────────────────────────────
    logger.info("\n✍️  STEP 2: Script Generation")
    script = generate_script(topic)
    logger.info(f"   Hook: {script.hook[:70]}...")

    # ── Step 3: Create video ───────────────────────────────────────────────────
    logger.info("\n🎬 STEP 3: Video Creation")
    output_dir = os.path.join(
        config.OUTPUT_DIR,
        datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    )
    video_path = create_video(script, output_dir)

    # Save caption to a text file alongside the video for easy copy-paste
    caption_path = os.path.join(output_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(script.caption)
    logger.info(f"   Video saved:   {video_path}")
    logger.info(f"   Caption saved: {caption_path}")

    # ── Step 4: Send to Telegram ───────────────────────────────────────────────
    logger.info("\n📲 STEP 4: Sending to Telegram")

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("   Telegram not configured — video saved locally only.")
    else:
        reviewer = TelegramReviewer()
        reviewer.send_video_ready(video_path, script)

    # ── Summary ────────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start_time).seconds
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ PIPELINE COMPLETE — Video ready to upload!")
    logger.info(f"  Topic:   {topic.title}")
    logger.info(f"  Video:   {video_path}")
    logger.info(f"  Caption: {caption_path}")
    logger.info(f"  Time:    {elapsed}s")
    logger.info("")
    logger.info("  📱 Next step: Open TikTok, tap + and upload the video.")
    logger.info("  📋 Paste the caption from caption.txt when posting.")
    logger.info("=" * 60)


def check_env() -> bool:
    """Validates that required environment variables are set."""
    if not config.ANTHROPIC_API_KEY:
        logger.error("❌ ANTHROPIC_API_KEY is required. Add it to your .env file.")
        return False

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — video will be saved locally only.")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NuBunaTetu TikTok Agent")
    parser.add_argument("--topic", type=str, default=None, help="Override the trending topic")
    args = parser.parse_args()

    if check_env():
        run_pipeline(custom_topic=args.topic)
    else:
        logger.error("Fix the above issues and try again.")
        sys.exit(1)
