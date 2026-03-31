"""
NuBunaTetu – Telegram Notifier
ኑ ቡና ጠጡ · "Come and let's have coffee."

Sends the generated video + caption to your Telegram so you can
download it and upload it manually to TikTok.
"""

import logging
import time
import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from agent.script_generator import VideoScript

logger = logging.getLogger(__name__)

POLL_INTERVAL  = 5     # seconds between checking for reply
APPROVAL_TIMEOUT = 3600  # 1 hour — if no reply, skip posting today


class TelegramReviewer:

    def __init__(self):
        self.token   = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base    = f"https://api.telegram.org/bot{self.token}"
        self._last_update_id = None

    # ── Sending ────────────────────────────────────────────────────────────────

    def send_video_ready(self, video_path: str, script: VideoScript) -> bool:
        """
        Sends the finished video to your Telegram with the ready-to-paste caption.
        Download the video from Telegram and upload it manually to TikTok.
        Returns True if sent successfully.
        """
        logger.info("📲 Sending video to Telegram...")

        caption = (
            f"🎬 *NuBunaTetu — Video Ready!*\n\n"
            f"📌 *Topic:* {script.topic}\n\n"
            f"🪝 *Hook:* {script.hook}\n\n"
            f"📋 *TikTok Caption (copy this when uploading):*\n"
            f"`{script.caption[:800]}`\n\n"
            f"📱 Download this video and upload it to TikTok manually."
        )

        try:
            # Send the video
            with open(video_path, "rb") as video_file:
                resp = requests.post(
                    f"{self.base}/sendVideo",
                    data={
                        "chat_id":    self.chat_id,
                        "caption":    caption,
                        "parse_mode": "Markdown",
                    },
                    files={"video": video_file},
                    timeout=120
                )
            resp.raise_for_status()

            # Send caption as a separate plain-text message for easy copy-paste
            self.send_message(
                f"📋 *Copy this caption into TikTok:*\n\n{script.caption}"
            )

            logger.info("✅ Video + caption sent to Telegram — download and upload to TikTok!")
            return True

        except Exception as e:
            logger.error(f"Failed to send video to Telegram: {e}")
            return False

    def send_message(self, text: str) -> None:
        """Send a plain text message to your Telegram chat."""
        try:
            requests.post(
                f"{self.base}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Failed to send Telegram message: {e}")

    # ── Receiving ──────────────────────────────────────────────────────────────

    def _get_updates(self) -> list[dict]:
        """Poll Telegram for new messages."""
        params = {"timeout": 10, "allowed_updates": ["message"]}
        if self._last_update_id is not None:
            params["offset"] = self._last_update_id + 1
        try:
            resp = requests.get(f"{self.base}/getUpdates", params=params, timeout=15)
            data = resp.json()
            return data.get("result", [])
        except Exception as e:
            logger.warning(f"Telegram poll error: {e}")
            return []

    def wait_for_approval(self, timeout_seconds: int = APPROVAL_TIMEOUT) -> bool:
        """
        Blocks and polls Telegram until you reply "approve" or "reject".
        Returns True if approved, False if rejected or timed out.
        """
        logger.info(f"⏳ Waiting for your Telegram approval (timeout: {timeout_seconds}s)...")
        self.send_message(
            "⏰ _Waiting for your reply..._\n\n"
            "Reply *approve* to post ✅\n"
            "Reply *reject* to skip ❌"
        )

        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            updates = self._get_updates()

            for update in updates:
                self._last_update_id = update["update_id"]
                msg = update.get("message", {})

                # Only accept messages from the configured chat
                if str(msg.get("chat", {}).get("id", "")) != str(self.chat_id):
                    continue

                text = msg.get("text", "").strip().lower()

                if text == "approve":
                    logger.info("✅ Video approved via Telegram!")
                    self.send_message("✅ *Approved!* Posting to TikTok now... 🚀")
                    return True

                elif text == "reject":
                    logger.info("❌ Video rejected via Telegram.")
                    self.send_message("❌ *Rejected.* Skipping today's post. Try again tomorrow!")
                    return False

                else:
                    self.send_message(
                        f"I didn't understand '{text}'.\n"
                        "Please reply *approve* ✅ or *reject* ❌"
                    )

            time.sleep(POLL_INTERVAL)

        # Timeout reached
        logger.warning("⏰ Approval timeout — skipping today's post.")
        self.send_message(
            "⏰ *Timeout reached.* No reply received — skipping today's post.\n"
            "The agent will try again tomorrow!"
        )
        return False


def get_telegram_chat_id(bot_token: str) -> str:
    """
    Helper: prints your Telegram chat ID so you can add it to .env.
    Run once after starting a conversation with your bot.
    """
    resp = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates")
    data = resp.json()
    updates = data.get("result", [])
    if updates:
        chat_id = updates[-1]["message"]["chat"]["id"]
        print(f"\n✅ Your TELEGRAM_CHAT_ID is: {chat_id}")
        print("Add this to your .env file.\n")
        return str(chat_id)
    else:
        print("\n⚠️  No messages found.")
        print("Send any message to your bot on Telegram first, then run this again.\n")
        return ""


if __name__ == "__main__":
    # Run this file directly to get your chat ID:
    # python -m agent.telegram_reviewer
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set in .env")
    else:
        get_telegram_chat_id(token)
