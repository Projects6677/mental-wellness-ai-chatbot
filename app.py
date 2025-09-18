import os
import json
import streamlit as st
import openai
from datetime import datetime
import random
import time
import re

from config.prompts import SYSTEM_PROMPT, build_messages
from utils.helpers import (
    get_suggestion,
    detect_crisis,
    load_helplines,
    format_helplines,
    MOOD_SUGGESTIONS,
)

# --- CONFIG / API KEY ---
# Attempt to get the key from Streamlit Cloud Secrets or local environment variables.
OPENAI_API_KEY = (
    st.secrets.get("OPENAI_API_KEY", None)
    if hasattr(st, "secrets")
    else os.environ.get("OPENAI_API_KEY")
)

if not OPENAI_API_KEY:
    st.warning("OPENAI_API_KEY not found. Please check your secrets.toml or environment variables.")
    st.stop()

# Initialize OpenAI client with the new syntax
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Helper functions for new features ---
def get_sentiment(text):
    """Analyzes sentiment of the user's input using the AI."""
    sentiment_prompt = f"Analyze the sentiment of the following text. Respond with only a single word: 'positive', 'negative', or 'neutral'.\n\nText: '{text}'"
    
    try:
        response = client.chat.completions.create(
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
    
    if "streak_count" not in st.session_state:
        st.session_state.streak_count = 0
        st.session_state.last_checkin_date = None

    if st.session_state.last_checkin_date is None or st.session_state.last_checkin_date < today:
        if st.session_state.last_checkin_date and (today - st.session_state.last_checkin_date).days == 1:
            st.session_state.streak_count += 1
        else:
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
        st.rerun()

# Session state for chat history
if "history" not in st.session_state:
    st.session_state.history = []

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

helplines = load_helplines("resources/helplines.json")

# Mood selector
mood = st.radio(
    "How are you feeling right now?",
    ("😊 Happy", "😔 Sad", "😨 Anxious", "😡 Angry", "😐 Neutral", "😟 Stressed"),
)

# Display chat history
for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input from a new chat input box at the bottom
if user_input := st.chat_input(placeholder=f"Tell me about what's on your mind. You can say something like, 'I'm feeling {mood.split()[1].lower()} because...'"):
    with st.chat_message("user"):
        st.markdown(user_input)
    
    st.session_state.history.append({"role": "user", "content": user_input})
    update_streak()
    
    sentiment = get_sentiment(user_input)
    
    crisis_flag, evidence = detect_crisis(user_input)
    
    if crisis_flag:
        with st.chat_message("assistant"):
            st.error(
                "⚠️ I detect language that suggests you may be in severe distress or crisis. "
                "If you are in immediate danger, please call your local emergency number now."
            )
            for helpline in helplines:
                s = f"**{helpline.get('country','')}** — {helpline.get('service','')}"
                if helpline.get("number"):
                    s += f" — **{helpline.get('number')}**"
                if helpline.get("url"):
                    s += f" — {helpline.get('url')}"
                st.markdown(s)
        
        system_prompt = (
            SYSTEM_PROMPT
            + "\nNOTE: The user may be in crisis. Prioritize calm, supportive language and encourage seeking immediate help. "
            "Do NOT provide instructions for self-harm. Give crisis resources and encourage contacting professionals."
        )
        st.session_state.messages.append({"role": "system", "content": system_prompt})
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_input})
    
    try:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            for chunk in client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                temperature=0.8,
                stream=True
            ):
                full_response += chunk.choices[0].delta.get("content", "")
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            ai_text = full_response
    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"OpenAI API error: {e}")
            ai_text = "Sorry — I'm having trouble connecting to my brain. Try again in a moment."
    
    st.session_state.history.append({"role": "assistant", "content": ai_text})
    st.experimental_rerun()

st.markdown("---")
st.subheader("Quick Resources")
st.write("If you want a fast coping technique for this mood:")
st.info(get_suggestion(mood))
st.markdown("**Helplines & support**")
if helplines:
    for helpline in helplines:
        s = f"**{helpline.get('country','')}** — {helpline.get('service','')}"
        if helpline.get("number"):
            s += f" — **{helpline.get('number')}**"
        if helpline.get("url"):
            s += f" — {helpline.get('url')}"
        st.markdown(s)

if st.session_state.history:
    transcript = "\n\n".join(
        [f"{h['role'].upper()}: {h['content']}" for h in st.session_state.history]
    )
    st.download_button("Download transcript (txt)", data=transcript, file_name="transcript.txt")
