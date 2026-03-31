"""
NuBunaTetu – Script Generator
ኑ ቡና ጠጡ · "Come and let's have coffee."

Uses Claude AI to write punchy Amharic/English mixed TikTok scripts
based on a trending topic.
"""

import logging
import anthropic
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from agent.trend_discovery import TrendingTopic

logger = logging.getLogger(__name__)


@dataclass
class VideoScript:
    topic: str
    hook: str           # First 3 seconds — must grab attention
    body: str           # Main content (30–45 seconds)
    cta: str            # Call to action (last 5 seconds)
    hashtags: list[str]
    full_text: str      # Hook + body + CTA combined for TTS
    caption: str        # TikTok post caption (max 2200 chars)


SYSTEM_PROMPT = """You are NuBunaTetu, a fun and energetic Ethiopian TikTok entertainment creator.
You write short, punchy, viral video scripts that make people laugh, feel proud, and want to share.

🚫 STRICT RULE: NEVER write about politics, government, war, conflict, elections, or any serious news.
✅ ONLY write about: music, comedy, food, fashion, football, dance, culture, relationships, celebrity gossip, funny observations about Ethiopian life.

Your scripts must:
- Mix Amharic and English naturally (code-switching like young Ethiopians do)
- Be funny, warm, relatable, or surprising — something that makes people laugh or say "ትክክል ነው!"
- Have a powerful HOOK in the first 3 seconds that stops the scroll — shock, humor, or curiosity
- Be conversational and authentic, like you're talking to a friend over coffee (ቡና)
- Be 30–45 seconds when spoken aloud at a natural pace
- End with a fun call to action (follow ያድርጉ, comment ያድርጉ, share ያድርጉ)

Tone: Think less news anchor, more funny cousin who always has tea ☕

Ethiopian TikTok entertainment audience profile:
- Age 16–35, urban Ethiopians & diaspora
- Love: Teddy Afro, Dawit Tsige, Seifu on EBS, Ethiopian Premier League, injera debates, diaspora vs. back-home comparisons
- Respond to: relatable humor, cultural pride, "Ethiopia vs. the world" content, food content, music reactions
- Popular phrases: ወዳጄ, ዘጠኝ ዘጠኝ, ማን ቆሞ ነው, ኧረ ይቅርታ, ቤተሰብ ነው, ፍቅር ነው, yebet lijoch

Output strictly as JSON with these keys:
{
  "hook": "...",
  "body": "...",
  "cta": "...",
  "hashtags": ["tag1", "tag2", ...],
  "caption": "..."
}"""


def generate_script(topic: TrendingTopic) -> VideoScript:
    """
    Calls Claude to generate a TikTok script for the given trending topic.
    Returns a VideoScript dataclass.
    """
    logger.info(f"✍️  Generating script for: {topic.title}")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    user_prompt = f"""Write a fun, entertaining TikTok video script about this topic:

Topic: {topic.title}
Details: {topic.description}
Category: {getattr(topic, 'category', 'Entertainment')}

Remember:
- ENTERTAINMENT ONLY — no politics, no news, no serious topics
- Mix Amharic and English naturally (code-switch like young Ethiopians do)
- Hook must be under 15 words — funny, shocking, or relatable
- Body should be 30–40 seconds when spoken at a natural pace
- End with a fun CTA in Amharic/English mix
- Include 6–10 hashtags (entertainment-focused, mix Amharic and English themes)
- Caption should be punchy and fun — something people want to share"""

    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        import json
        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)

        full_text = f"{data['hook']} {data['body']} {data['cta']}"

        script = VideoScript(
            topic=topic.title,
            hook=data["hook"],
            body=data["body"],
            cta=data["cta"],
            hashtags=data.get("hashtags", []),
            full_text=full_text,
            caption=data.get("caption", full_text[:500])
        )

        logger.info(f"✅ Script generated ({len(full_text)} chars)")
        logger.info(f"   Hook: {script.hook[:60]}...")
        return script

    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        # Return a fallback script
        fallback_hook = "ወዳጄ! This you need to know about Ethiopia 🇪🇹"
        fallback_body = (
            f"Let's talk about {topic.title}. "
            "Ethiopia has so much going on — and this is one story you shouldn't miss. "
            "ትክክለኛ information, no drama, just facts. "
            "የEthiopia ታሪክ is deeper than most people think, "
            "and today we're breaking it down for you."
        )
        fallback_cta = "Like ያድርጉ, follow ያድርጉ — more Ethiopian content is coming! 🔥"
        full_text = f"{fallback_hook} {fallback_body} {fallback_cta}"

        return VideoScript(
            topic=topic.title,
            hook=fallback_hook,
            body=fallback_body,
            cta=fallback_cta,
            hashtags=["Ethiopia", "Habesha", "Ethiopian", "AddisAbaba", "EthiopianTikTok"],
            full_text=full_text,
            caption=f"{fallback_hook}\n\n#Ethiopia #Habesha #Ethiopian #EthiopianTikTok"
        )
