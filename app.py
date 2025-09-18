import os
import json
import streamlit as st
import openai
from datetime import datetime
import random

from config.prompts import SYSTEM_PROMPT, build_messages
from utils.helpers import (
    get_suggestion,
    detect_crisis,
    load_helplines,
    format_helplines,
)

# --- CONFIG / API KEY ---
# Streamlit Cloud: put your key in Secrets (OPENAI_API_KEY)
# Local: export OPENAI_API_KEY or use .streamlit/secrets.toml for local dev
OPENAI_API_KEY = (
    st.secrets.get("OPENAI_API_KEY", None)
    if hasattr(st, "secrets")
    else os.environ.get("OPENAI_API_KEY")
)

if not OPENAI_API_KEY:
    st.warning(
        "OPENAI_API_KEY not found. Locally set env var or set Streamlit Secret OPENAI_API_KEY."
    )
openai.api_key = OPENAI_API_KEY

# --- Helper functions for new features ---
def get_sentiment(text):
    """Analyzes sentiment of the user's input using the AI."""
    sentiment_prompt = f"Analyze the sentiment of the following text. Respond with only a single word: 'positive', 'negative', or 'neutral'.\n\nText: '{text}'"
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": sentiment_prompt}],
            temperature=0.0
        )
        sentiment = response.choices[0].message.content.strip().lower()
        return sentiment
    except Exception as e:
        st.warning(f"Sentiment analysis failed: {e}")
        return "neutral"

def update_streak():
    """Updates the user's check-in streak based on daily interactions."""
    today = datetime.now().date()
    
    # Initialize streak if it doesn't exist
    if "streak_count" not in st.session_state:
        st.session_state.streak_count = 0
        st.session_state.last_checkin_date = None

    # Check if a new day has started
    if st.session_state.last_checkin_date is None or st.session_state.last_checkin_date < today:
        if st.session_state.last_checkin_date and (today - st.session_state.last_checkin_date).days == 1:
            # Continue streak
            st.session_state.streak_count += 1
        else:
            # New streak or reset
            st.session_state.streak_count = 1
        
        st.session_state.last_checkin_date = today

# --- UI ---
st.set_page_config(page_title="AI Buddy — Youth Mental Wellness", layout="centered")
st.title("🤝 AI Buddy — Youth Mental Wellness")
st.markdown(
    """
An **anonymous** and **empathetic** AI listener for quick check-ins, mood tracking and self-help suggestions.
**Note:** This tool is not a replacement for professional care. If you are in immediate danger, call your local emergency number.
"""
)

# Display Streak Counter
update_streak()
st.markdown(f"🔥 **Current Streak:** {st.session_state.streak_count} day(s)")

# Sidebar
with st.sidebar:
    st.header("About")
    st.write(
        "AI Buddy is a demo chatbot for youth mental wellness. It's anonymous and stores nothing permanently (session only)."
    )
    if st.button("Clear session"):
        st.session_state.clear()

# Session state for chat history
if "history" not in st.session_state:
    st.session_state.history = [{"role": "assistant", "text": "Hi there. I'm AI Buddy. How can I support you today?"}]

# Load helplines (resources/helplines.json)
helplines = load_helplines("resources/helplines.json")

# Mood selector
mood = st.radio(
    "How are you feeling right now?",
    ("😊 Happy", "😔 Sad", "😨 Anxious", "😡 Angry", "😐 Neutral", "😟 Stressed"),
)

user_input = st.text_area("Write to your AI Buddy (be honest):", height=120)

col1, col2 = st.columns([1, 1])
with col1:
    send = st.button("Send")
with col2:
    quick_tip = st.button("Get a suggestion for this mood")

# Quick suggestion only (no LLM call)
if quick_tip:
    st.info(get_suggestion(mood))

# When user sends message
if send and user_input.strip():
    # Update streak since a new message signifies a check-in
    update_streak()
    
    # Analyze sentiment
    sentiment = get_sentiment(user_input)
    
    # show user's message
    st.session_state.history.append({"role": "user", "text": user_input})

    # Crisis detection (simple keyword-based). If crisis -> show helplines prominently
    crisis_flag, evidence = detect_crisis(user_input)
    if crisis_flag:
        st.error(
            "⚠️ I detect language that suggests you may be in severe distress or crisis. "
            "If you are in immediate danger, please call your local emergency number now."
        )
        st.markdown(format_helplines(helplines))
        # still let the AI reply with supportive non-clinical wording, but emphasize help
        system_prompt = (
            SYSTEM_PROMPT
            + "\nNOTE: The user may be in crisis. Prioritize calm, supportive language and encourage seeking immediate help. "
            "Do NOT provide instructions for self-harm. Give crisis resources and encourage contacting professionals."
        )
    else:
        system_prompt = SYSTEM_PROMPT + f"\n\nUser's detected sentiment is '{sentiment}'. Respond with an appropriate tone based on this emotion."

    # Build messages for ChatCompletion
    messages = build_messages(system_prompt, mood, user_input)

    # Call OpenAI (chat completion)
    try:
        with st.spinner("AI Buddy is thinking..."):
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=350,
                temperature=0.8,
            )
            ai_text = response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"OpenAI API error: {e}")
        ai_text = (
            "Sorry — I'm having trouble connecting to my brain. Try again in a moment."
        )

    # Append assistant reply to history
    st.session_state.history.append({"role": "assistant", "text": ai_text})

# Display conversation history
if st.session_state.history:
    st.markdown("---")
    for msg in st.session_state.history[::-1]:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['text']}")
        else:
            st.markdown(f"**AI Buddy:** {msg['text']}")

# Footer suggestions + resources
st.markdown("---")
st.subheader("Quick Resources")
st.write("If you want a fast coping technique for this mood:")
st.info(get_suggestion(mood))
st.markdown("**Helplines & support**")
st.markdown(format_helplines(helplines))

# Option to download transcript (session only)
if st.session_state.history:
    transcript = "\n\n".join(
        [f"{h['role'].upper()}: {h['text']}" for h in st.session_state.history]
    )
    st.download_button("Download transcript (txt)", data=transcript, file_name="transcript.txt")
