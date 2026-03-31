"""
NuBunaTetu – Video Creator (Illustrated Edition)
ኑ ቡና ጠጡ · "Come and let's have coffee."

Builds a TikTok-ready 9:16 video using:
  1. DALL-E 3 — generates Ethiopian-themed illustrated scenes for each part of the script
  2. Ken Burns effect — slow zoom & pan to bring still images to life
  3. edge-tts — Amharic/English voiceover narrates the script
  4. Captions — animated text overlaid at the bottom of each scene
  5. NuBunaTetu branding watermark

The result looks like an animated illustrated storybook — unique on Ethiopian TikTok.
"""

import os
import asyncio
import textwrap
import logging
import requests
import tempfile
import math
from pathlib import Path
from io import BytesIO

import openai
import edge_tts
from moviepy import (
    AudioFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from agent.script_generator import VideoScript

logger = logging.getLogger(__name__)

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT   # 1080 × 1920 (TikTok portrait)

# Amharic-capable TTS voice
AMHARIC_VOICE  = "am-ET-MekdesNeural"
FALLBACK_VOICE = "en-US-AriaNeural"


# ── DALL-E 3 Illustrated Image Generation ─────────────────────────────────────

# Prompt template that steers DALL-E toward Ethiopian illustrated art style
IMAGE_STYLE = (
    "digital illustration, vibrant Ethiopian art style, "
    "warm earthy tones with pops of red green and gold, "
    "Habesha cultural motifs and traditional patterns, "
    "detailed and expressive characters, no text, no words, "
    "9:16 portrait orientation, cinematic composition"
)

# Scene prompts matched to each part of the video
SCENE_PROMPTS = {
    "hook": (
        "an illustrated Ethiopian scene that grabs attention — "
        "an expressive young Habesha person reacting with surprise or laughter, "
        "vibrant Addis Abeba background, "
    ),
    "body": (
        "an illustrated Ethiopian story scene — "
        "lively community, cultural setting, coffee ceremony, music, or sports, "
        "warm and joyful atmosphere, "
    ),
    "cta": (
        "a beautiful illustrated Ethiopian closing scene — "
        "traditional coffee ceremony, Ethiopian flag colors, "
        "warm invitation feeling, "
    ),
}


def _build_dalle_prompt(scene: str, topic: str, category: str) -> str:
    """Builds a DALL-E 3 prompt for a specific scene and topic."""
    base = SCENE_PROMPTS.get(scene, SCENE_PROMPTS["body"])
    topic_hint = f"themed around '{topic}', "
    return base + topic_hint + IMAGE_STYLE


def generate_illustrated_scene(scene: str, topic: str, category: str, output_path: str) -> str:
    """
    Calls DALL-E 3 to generate one illustrated scene.
    Saves to output_path and returns the path.
    Falls back to a stylised solid colour if generation fails.
    """
    if not config.OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY — using fallback gradient background.")
        return _make_gradient_bg(output_path)

    prompt = _build_dalle_prompt(scene, topic, category)
    logger.info(f"   🎨 Generating '{scene}' illustration via DALL-E 3...")

    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1792",     # Closest to 9:16 that DALL-E 3 supports
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        img_data  = requests.get(image_url, timeout=30).content

        # Resize to exact 1080×1920
        img = Image.open(BytesIO(img_data)).convert("RGB")
        img = img.resize((W, H), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=92)
        logger.info(f"   ✅ Illustration saved: {output_path}")
        return output_path

    except Exception as e:
        logger.warning(f"   DALL-E generation failed for '{scene}': {e}")
        return _make_gradient_bg(output_path)


def _make_gradient_bg(output_path: str) -> str:
    """
    Fallback: creates a warm Ethiopian-coloured gradient background.
    Uses the Ethiopian flag palette — green, yellow, red.
    """
    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Vertical gradient: deep green → dark gold → dark red
    colours = [(34, 85, 34), (180, 130, 20), (140, 20, 20)]
    seg_h   = H // len(colours)

    for i, colour in enumerate(colours):
        y0 = i * seg_h
        y1 = (i + 1) * seg_h if i < len(colours) - 1 else H
        draw.rectangle([0, y0, W, y1], fill=colour)

    # Soften with blur for a smooth look
    img = img.filter(ImageFilter.GaussianBlur(radius=60))
    img.save(output_path, "JPEG", quality=90)
    return output_path


# ── Ken Burns Motion Effect ────────────────────────────────────────────────────

def apply_ken_burns(image_path: str, duration: float, effect: str = "zoom_in") -> ImageClip:
    """
    Applies a slow Ken Burns motion effect to a still image.

    What is Ken Burns?
    It's a filmmaking technique where a still photo slowly zooms or pans,
    making it feel like a live camera shot. Named after documentary filmmaker
    Ken Burns who used it extensively. It makes illustrated images feel alive.

    Effects available:
      zoom_in   — camera slowly moves closer (pulls viewer in)
      zoom_out  — camera pulls back (reveals the scene)
      pan_right — camera drifts right across the image
      pan_left  — camera drifts left across the image
    """
    img     = Image.open(image_path).convert("RGB")
    img_arr = np.array(img)

    # We create an image slightly larger than the frame so we have room to move
    SCALE = 1.15   # 15% larger gives smooth motion without cropping weirdly

    def make_frame(t: float) -> np.ndarray:
        """
        For each moment in time (t), return what the "camera" sees.
        t goes from 0 (start) to duration (end).
        """
        progress = t / duration   # 0.0 → 1.0

        if effect == "zoom_in":
            # Scale smoothly from SCALE → 1.0 (getting closer)
            scale  = SCALE - (SCALE - 1.0) * progress
            crop_w = int(W * scale)
            crop_h = int(H * scale)
            x0     = (W - crop_w) // 2
            y0     = (H - crop_h) // 2

        elif effect == "zoom_out":
            # Scale smoothly from 1.0 → SCALE (pulling back)
            scale  = 1.0 + (SCALE - 1.0) * progress
            crop_w = int(W * scale)
            crop_h = int(H * scale)
            x0     = (W - crop_w) // 2
            y0     = (H - crop_h) // 2

        elif effect == "pan_right":
            # Pan from left side to right side
            crop_w = int(W * SCALE)
            crop_h = H
            max_x  = W - crop_w  # negative — image is wider than frame
            x0     = int(max_x * (1 - progress))   # moves right over time
            y0     = 0

        elif effect == "pan_left":
            crop_w = int(W * SCALE)
            crop_h = H
            max_x  = W - crop_w
            x0     = int(max_x * progress)
            y0     = 0

        else:
            # Fallback: static
            return img_arr

        # Resize image to make it slightly larger than frame
        resized = img.resize((int(W * SCALE), int(H * SCALE)), Image.LANCZOS)
        # Crop the exact frame area
        frame   = resized.crop((abs(x0), abs(y0), abs(x0) + W, abs(y0) + H))
        return np.array(frame)

    clip = ImageClip(make_frame, duration=duration, ismask=False)
    return clip


# ── Text-to-Speech ─────────────────────────────────────────────────────────────

async def _tts_async(text: str, output_path: str, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_voiceover(script: VideoScript, output_dir: str) -> str:
    """Generates MP3 voiceover from the full script. Returns audio file path."""
    audio_path = os.path.join(output_dir, "voiceover.mp3")
    logger.info("🎙️  Generating voiceover...")

    for voice in [AMHARIC_VOICE, FALLBACK_VOICE]:
        try:
            asyncio.run(_tts_async(script.full_text, audio_path, voice))
            logger.info(f"   ✅ Voiceover ready (voice: {voice})")
            return audio_path
        except Exception as e:
            logger.warning(f"   Voice {voice} failed: {e}")

    raise RuntimeError("All TTS voices failed.")


# ── Caption Rendering ──────────────────────────────────────────────────────────

def _render_caption(text: str) -> np.ndarray:
    """
    Renders caption text onto a transparent RGBA image the same size as the video.
    Appears at the bottom of the frame with a semi-transparent dark background pill.
    """
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            config.FONT_SIZE
        )
    except Exception:
        font = ImageFont.load_default()

    # Wrap to fit frame width
    wrapped = textwrap.fill(text, width=20)
    lines   = wrapped.split("\n")
    line_h  = config.FONT_SIZE + 10
    total_h = line_h * len(lines)
    y       = H - total_h - 140   # bottom padding

    for line in lines:
        bbox   = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x      = (W - text_w) // 2

        # Dark pill behind each line for readability
        pad = 14
        draw.rounded_rectangle(
            [x - pad, y - pad // 2, x + text_w + pad, y + config.FONT_SIZE + pad // 2],
            radius=10,
            fill=(0, 0, 0, 185)
        )
        # White text
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h

    return np.array(img)


def _render_watermark() -> np.ndarray:
    """NuBunaTetu brand watermark in TikTok red, top-right corner."""
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30
        )
    except Exception:
        font = ImageFont.load_default()

    text  = "NuBunaTetu 🇪🇹"
    bbox  = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = W - text_w - 28

    # Subtle dark pill behind watermark
    draw.rounded_rectangle([x - 10, 52, x + text_w + 10, 100], radius=8, fill=(0, 0, 0, 130))
    draw.text((x, 56), text, font=font, fill=(254, 44, 85, 230))   # TikTok red
    return np.array(img)


# ── Main Video Builder ─────────────────────────────────────────────────────────

# Ken Burns effects cycle — each scene gets a different movement
KEN_BURNS_CYCLE = ["zoom_in", "pan_right", "zoom_out", "pan_left"]


def create_video(script: VideoScript, output_dir: str) -> str:
    """
    Builds the full illustrated TikTok video.

    Pipeline:
      1. Generate 3 Ethiopian illustrated scenes via DALL-E 3
         (one for hook, one for body, one for CTA)
      2. Apply Ken Burns motion effect to each scene
      3. Generate Amharic/English voiceover via edge-tts
      4. Overlay animated captions on each scene
      5. Add NuBunaTetu watermark
      6. Composite all layers and export MP4

    Returns path to the final video file.
    """
    os.makedirs(output_dir, exist_ok=True)
    category = getattr(script, "category", "Entertainment")

    # ── Step 1: Generate voiceover ─────────────────────────────────────────────
    logger.info("🎙️  Step 1/5 — Generating voiceover...")
    audio_path = generate_voiceover(script, output_dir)
    audio_clip = AudioFileClip(audio_path)
    total_dur  = audio_clip.duration

    # ── Step 2: Define scenes (hook / body / cta) ──────────────────────────────
    logger.info("🎨 Step 2/5 — Generating illustrated scenes via DALL-E 3...")

    # Each scene gets a share of the total video duration
    scenes = [
        ("hook", script.hook,  0.20),   # 20% of video
        ("body", script.body,  0.60),   # 60% of video
        ("cta",  script.cta,   0.20),   # 20% of video
    ]

    # ── Step 3: Build scene clips ──────────────────────────────────────────────
    logger.info("🎬 Step 3/5 — Building video scenes...")
    scene_clips = []

    for i, (scene_name, caption_text, duration_ratio) in enumerate(scenes):
        scene_dur  = total_dur * duration_ratio
        img_path   = os.path.join(output_dir, f"scene_{scene_name}.jpg")

        # Generate illustrated image for this scene
        generate_illustrated_scene(
            scene=scene_name,
            topic=script.topic,
            category=category,
            output_path=img_path
        )

        # Apply Ken Burns motion effect
        effect     = KEN_BURNS_CYCLE[i % len(KEN_BURNS_CYCLE)]
        bg_clip    = apply_ken_burns(img_path, scene_dur, effect)

        # Render caption overlay for this scene
        cap_arr    = _render_caption(caption_text[:120])
        cap_clip   = ImageClip(cap_arr, duration=scene_dur)

        # Composite: background + caption
        scene_clip = CompositeVideoClip([bg_clip, cap_clip], size=(W, H))
        scene_clips.append(scene_clip)

        logger.info(f"   ✅ Scene '{scene_name}' ready ({scene_dur:.1f}s, effect: {effect})")

    # ── Step 4: Concatenate scenes ─────────────────────────────────────────────
    logger.info("🔗 Step 4/5 — Joining scenes...")
    full_video = concatenate_videoclips(scene_clips, method="compose")

    # Add watermark on top of everything
    watermark  = ImageClip(_render_watermark(), duration=total_dur)
    final      = CompositeVideoClip([full_video, watermark], size=(W, H))
    final      = final.with_audio(audio_clip)

    # ── Step 5: Export ─────────────────────────────────────────────────────────
    logger.info("💾 Step 5/5 — Exporting MP4...")
    output_path = os.path.join(output_dir, "nubunатету_video.mp4")
    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=os.path.join(output_dir, "temp_audio.m4a"),
        remove_temp=True,
        logger=None
    )

    logger.info(f"✅ Video ready: {output_path}")
    return output_path
