"""
NuBunaTetu – Trend Discovery
ኑ ቡና ጠጡ · "Come and let's have coffee."

Discovers trending Ethiopian ENTERTAINMENT topics from:
  1. YouTube trending Ethiopian music & comedy searches
  2. TikTok entertainment hashtags
  3. Google Trends (Ethiopia) — filtered for entertainment
  4. Category rotation fallback — ensures variety

No politics. No news. Only vibes. 🎶
"""

import re
import random
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional
from pytrends.request import TrendReq

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# Keywords that signal news/politics — we skip any topic containing these
BLOCKED_KEYWORDS = [
    "war", "conflict", "attack", "killed", "protest", "government",
    "minister", "parliament", "election", "military", "airstrike",
    "displaced", "crisis", "shooting", "bomb", "death toll",
    "tigray", "amhara", "oromia",  # skip when used in political context
    "famine", "drought", "flood",  # skip disaster news
]


@dataclass
class TrendingTopic:
    title: str
    description: str
    source: str
    category: str = "Entertainment"
    url: Optional[str] = None
    score: int = 0


def _is_entertainment(text: str) -> bool:
    """Returns True if the topic is clearly entertainment (not politics/news)."""
    lower = text.lower()
    return not any(kw in lower for kw in BLOCKED_KEYWORDS)


# ── YouTube Ethiopian Entertainment ───────────────────────────────────────────

def _scrape_youtube_ethiopian_music() -> list[TrendingTopic]:
    """Scrapes YouTube search results for trending Ethiopian music."""
    topics = []
    queries = [
        "ethiopian music 2026",
        "ethiopian comedy 2026",
        "habesha funny video",
        "new ethiopian song",
    ]
    for query in queries:
        try:
            url  = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            # YouTube embeds video titles in <script> tags as JSON-like text
            # Pull any title patterns we can find
            for script in soup.find_all("script"):
                text = script.string or ""
                matches = re.findall(r'"title":\{"runs":\[{"text":"([^"]{10,80})"', text)
                for title in matches[:3]:
                    if _is_entertainment(title):
                        topics.append(TrendingTopic(
                            title=title,
                            description=f"Trending on YouTube: {title}",
                            source="YouTube",
                            category="Music & Entertainment",
                            url=url,
                            score=random.randint(65, 92)
                        ))
        except Exception as e:
            logger.warning(f"YouTube scrape failed for '{query}': {e}")

    return topics


def _scrape_habeshaview() -> list[TrendingTopic]:
    """Scrapes HabeshaView for Ethiopian showbiz & celebrity content."""
    topics = []
    try:
        resp = requests.get("https://www.habeshaview.com", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for article in soup.select("h2 a, h3 a, .post-title a")[:10]:
            title = article.get_text(strip=True)
            url   = article.get("href", "")
            if len(title) > 10 and _is_entertainment(title):
                topics.append(TrendingTopic(
                    title=title,
                    description=f"Ethiopian showbiz: {title}",
                    source="HabeshaView",
                    category="Celebrity & Showbiz",
                    url=url,
                    score=random.randint(60, 88)
                ))
    except Exception as e:
        logger.warning(f"HabeshaView scrape failed: {e}")
    return topics


# ── Google Trends (Ethiopia — Entertainment Keywords) ─────────────────────────

def _google_trends_ethiopia() -> list[TrendingTopic]:
    """
    Pulls what Ethiopians are searching on Google right now,
    then filters to keep only entertainment-related topics.
    """
    topics = []
    try:
        pytrends = TrendReq(hl="am-ET", tz=180)
        trending  = pytrends.trending_searches(pn="ethiopia")
        for term in trending[0].tolist()[:10]:
            if _is_entertainment(term):
                topics.append(TrendingTopic(
                    title=term,
                    description=f"Trending on Google in Ethiopia right now: {term}",
                    source="Google Trends",
                    category="Trending",
                    score=random.randint(72, 100)
                ))
    except Exception as e:
        logger.warning(f"Google Trends fetch failed: {e}")
    return topics


# ── TikTok Entertainment Hashtags ─────────────────────────────────────────────

def _tiktok_hashtag_topics() -> list[TrendingTopic]:
    """Tries TikTok search API; falls back to category seed topics."""
    topics = []
    for hashtag in config.ETHIOPIAN_HASHTAGS[:5]:
        try:
            url  = f"https://www.tiktok.com/api/search/general/full/?keyword=%23{hashtag}&offset=0&count=5"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                data  = resp.json()
                items = data.get("data", [])
                for item in items[:2]:
                    desc = item.get("desc", "") or item.get("title", "")
                    if desc and _is_entertainment(desc):
                        topics.append(TrendingTopic(
                            title=f"#{hashtag}: {desc[:80]}",
                            description=desc,
                            source=f"TikTok #{hashtag}",
                            category="TikTok Trending",
                            score=random.randint(68, 96)
                        ))
        except Exception as e:
            logger.warning(f"TikTok #{hashtag} fetch failed: {e}")

        # Always add a hashtag seed as fallback
        topics.append(TrendingTopic(
            title=f"#{hashtag}",
            description=f"Create fun content around #{hashtag} for the Ethiopian TikTok community",
            source=f"TikTok #{hashtag}",
            category="TikTok Trending",
            score=random.randint(50, 72)
        ))

    return topics


# ── Category Rotation Fallback ─────────────────────────────────────────────────

def _category_rotation_topics() -> list[TrendingTopic]:
    """
    Generates topic ideas from the content categories in config.
    Used as a reliable fallback when scrapers return nothing.
    Each run picks a different category to keep content varied.
    """
    topics = []
    for category in config.CONTENT_CATEGORIES:
        topics.append(TrendingTopic(
            title=category,
            description=f"Create an engaging TikTok video about: {category}",
            source="Category Rotation",
            category=category,
            score=random.randint(55, 78)
        ))
    random.shuffle(topics)
    return topics


# ── Main Entry Point ───────────────────────────────────────────────────────────

def get_trending_topics(n: int = None) -> list[TrendingTopic]:
    """
    Returns the top-N trending Ethiopian entertainment topics, sorted by score.
    All political and news topics are filtered out automatically.
    """
    n = n or config.TREND_CANDIDATES
    logger.info("🔍 Discovering trending Ethiopian entertainment topics...")

    all_topics: list[TrendingTopic] = []
    all_topics += _google_trends_ethiopia()
    all_topics += _scrape_youtube_ethiopian_music()
    all_topics += _scrape_habeshaview()
    all_topics += _tiktok_hashtag_topics()
    all_topics += _category_rotation_topics()   # always has something

    # Deduplicate by title similarity
    seen: set[str] = set()
    unique: list[TrendingTopic] = []
    for t in all_topics:
        key = re.sub(r"\W+", "", t.title.lower())[:30]
        if key not in seen:
            seen.add(key)
            unique.append(t)

    # Sort by score descending
    unique.sort(key=lambda t: t.score, reverse=True)
    top = unique[:n]

    logger.info(f"✅ Found {len(top)} entertainment topics (politics filtered out)")
    for i, t in enumerate(top, 1):
        logger.info(f"  {i}. [{t.score}] {t.title} [{t.category}]")

    return top


def pick_best_topic(topics: list[TrendingTopic]) -> TrendingTopic:
    """Pick the highest-scoring topic."""
    if not topics:
        return TrendingTopic(
            title="Ethiopian Coffee Ceremony",
            description="Ethiopia gave coffee to the world — share the beauty of the coffee ceremony with a fun twist.",
            source="Default",
            category="Culture",
            score=50
        )
    return topics[0]
