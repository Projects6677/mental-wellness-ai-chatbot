import json
import re

def get_suggestion(mood: str) -> str:
    tips = {
        "😊 Happy": "Celebrate! Jot down one thing that made you smile — savor it for 60 seconds.",
        "😔 Sad": "Try a 3-2-1 grounding: name 3 things you see, 2 things you can touch, 1 thing you can hear.",
        "😨 Anxious": "Try box breathing: inhale 4s, hold 4s, exhale 4s, hold 4s — repeat 4 times.",
        "😡 Angry": "Step away for 2 mins. Put your hands on your belly and take slow breaths to calm your body.",
        "😐 Neutral": "Take a 2-minute mindful break: notice your breath and your surroundings.",
        "😟 Stressed": "Break tasks into tiny steps — write one next tiny action you can finish in 5 minutes.",
    }
    return tips.get(mood, "Take a slow breath. You’re doing your best — that matters.")

def detect_crisis(text: str):
    """
    Very simple keyword-based crisis detector.
    Returns (bool, evidence) where evidence is matched keyword(s).
    NOTE: This is not clinical. For production, use a stronger classifier & human review.
    """
    lower = text.lower()
    # flagged phrases - expand as you need
    patterns = [
        r"suicid", r"kill myself", r"end my life", r"want to die", r"hurt myself",
        r"self[- ]harm", r"overdose", r"hang myself", r"i'll die", r"no reason to live"
    ]
    found = []
    for p in patterns:
        if re.search(p, lower):
            found.append(p)
    return (len(found) > 0, found)

def load_helplines(path: str = "resources/helplines.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # fallback default small list (user should replace with local helplines)
        return [
            {
                "country": "Global",
                "service": "Befrienders Worldwide (find local centers)",
                "number": "",
                "url": "https://www.befrienders.org/"
            },
            {
                "country": "US",
                "service": "National Suicide & Crisis Lifeline",
                "number": "988",
                "url": "https://988lifeline.org/"
            },
            {
                "country": "UK",
                "service": "Samaritans",
                "number": "116 123",
                "url": "https://www.samaritans.org/"
            }
        ]

def format_helplines(helplines):
    lines = []
    for h in helplines:
        s = f"**{h.get('country','')}** — {h.get('service','')}"
        if h.get("number"):
            s += f" — **{h.get('number')}**"
        if h.get("url"):
            s += f" — {h.get('url')}"
        lines.append(s)
    return "\n\n".join(lines)
