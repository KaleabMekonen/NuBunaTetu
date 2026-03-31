"""
NuBunaTetu – TikTok Poster
ኑ ቡና ጠጡ · "Come and let's have coffee."

Posts approved videos to TikTok using the Content Posting API.

⚠️  STATUS: Requires TikTok API approval.
    Until your TikTok developer app is approved and you have an access token,
    this module will run in DRY RUN mode — it logs what it would do without posting.

    Once approved:
    1. Complete the OAuth flow to get your access token
    2. Add TIKTOK_ACCESS_TOKEN to your .env file
    3. This module will automatically start posting for real
"""

import os
import logging
import requests
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from agent.script_generator import VideoScript

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"


class TikTokPoster:

    def __init__(self):
        self.access_token = config.TIKTOK_ACCESS_TOKEN
        self.is_ready     = bool(self.access_token)

        if not self.is_ready:
            logger.warning(
                "⚠️  TikTok access token not set — running in DRY RUN mode.\n"
                "   Complete the OAuth flow and add TIKTOK_ACCESS_TOKEN to .env to enable posting."
            )

    # ── OAuth Helper ───────────────────────────────────────────────────────────

    def get_auth_url(self) -> str:
        """
        Generates the TikTok OAuth URL.
        Visit this URL in your browser to authorise the app.
        """
        scopes = "video.upload,video.publish"
        auth_url = (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={config.TIKTOK_CLIENT_KEY}"
            f"&scope={scopes}"
            f"&response_type=code"
            f"&redirect_uri=https://kaleabmekonen.github.io/NuBunaTetu/"
            f"&state=nubunатету_auth"
        )
        return auth_url

    def exchange_code_for_token(self, auth_code: str) -> dict:
        """
        Exchange the OAuth authorization code for an access token.
        Call this after the user visits the auth URL and gets a code.
        """
        resp = requests.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key":    config.TIKTOK_CLIENT_KEY,
                "client_secret": config.TIKTOK_CLIENT_SECRET,
                "code":          auth_code,
                "grant_type":    "authorization_code",
                "redirect_uri":  "https://kaleabmekonen.github.io/NuBunaTetu/",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        data = resp.json()
        if "access_token" in data:
            logger.info("✅ Got TikTok access token! Add this to your .env:")
            logger.info(f"   TIKTOK_ACCESS_TOKEN={data['access_token']}")
        return data

    # ── Video Upload ───────────────────────────────────────────────────────────

    def _init_upload(self, file_size: int, caption: str) -> dict:
        """Step 1 of TikTok's direct-post flow: initialise the upload."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json; charset=UTF-8",
        }
        payload = {
            "post_info": {
                "title":         caption[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet":  False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source":          "FILE_UPLOAD",
                "video_size":      file_size,
                "chunk_size":      file_size,
                "total_chunk_count": 1,
            },
        }
        resp = requests.post(
            f"{TIKTOK_API_BASE}/post/publish/video/init/",
            json=payload,
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def _upload_chunk(self, upload_url: str, video_path: str, file_size: int) -> None:
        """Step 2: Upload the video file in a single chunk."""
        with open(video_path, "rb") as f:
            video_data = f.read()

        headers = {
            "Content-Range":  f"bytes 0-{file_size - 1}/{file_size}",
            "Content-Length": str(file_size),
            "Content-Type":   "video/mp4",
        }
        resp = requests.put(upload_url, data=video_data, headers=headers, timeout=300)
        resp.raise_for_status()

    def _check_status(self, publish_id: str) -> dict:
        """Step 3: Check publish status."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json; charset=UTF-8",
        }
        resp = requests.post(
            f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
            json={"publish_id": publish_id},
            headers=headers,
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()

    # ── Main Post Method ───────────────────────────────────────────────────────

    def post_video(self, video_path: str, script: VideoScript) -> bool:
        """
        Posts the video to TikTok.
        Returns True on success, False on failure.
        In DRY RUN mode, logs what would happen without actually posting.
        """
        file_size = os.path.getsize(video_path)
        caption   = script.caption

        # ── DRY RUN (no access token yet) ──
        if not self.is_ready:
            logger.info("🟡 DRY RUN — TikTok posting simulated (no access token)")
            logger.info(f"   Would post: {video_path}")
            logger.info(f"   Caption:    {caption[:100]}...")
            logger.info(f"   File size:  {file_size / 1024 / 1024:.1f} MB")
            logger.info("")
            logger.info("   To enable real posting:")
            logger.info("   1. Visit this URL to authorize the app:")
            logger.info(f"   {self.get_auth_url()}")
            logger.info("   2. Copy the 'code' parameter from the redirect URL")
            logger.info("   3. Run: python -m agent.tiktok_poster <code>")
            return False

        # ── REAL POSTING ──
        try:
            logger.info("🚀 Posting video to TikTok...")

            # Step 1: Init upload
            init_data   = self._init_upload(file_size, caption)
            publish_id  = init_data["data"]["publish_id"]
            upload_url  = init_data["data"]["upload_url"]
            logger.info(f"   Publish ID: {publish_id}")

            # Step 2: Upload video
            logger.info("   Uploading video...")
            self._upload_chunk(upload_url, video_path, file_size)

            # Step 3: Check status
            import time
            for attempt in range(10):
                time.sleep(6)
                status = self._check_status(publish_id)
                state  = status.get("data", {}).get("status", "UNKNOWN")
                logger.info(f"   Status check {attempt + 1}: {state}")

                if state == "PUBLISH_COMPLETE":
                    logger.info("✅ Video published to TikTok successfully!")
                    return True
                elif state in ("FAILED", "PUBLISH_FAILED"):
                    logger.error(f"❌ TikTok publish failed: {status}")
                    return False

            logger.warning("⚠️  Publish status unknown after 10 checks — may still be processing.")
            return True

        except Exception as e:
            logger.error(f"TikTok post failed: {e}")
            return False


if __name__ == "__main__":
    # Run this to complete OAuth:
    # python -m agent.tiktok_poster <auth_code>
    import sys
    poster = TikTokPoster()
    if len(sys.argv) > 1:
        auth_code = sys.argv[1]
        result = poster.exchange_code_for_token(auth_code)
        print(result)
    else:
        print("TikTok OAuth URL:")
        print(poster.get_auth_url())
        print("\nVisit the URL above, authorize the app, then run:")
        print("python -m agent.tiktok_poster <code_from_url>")
