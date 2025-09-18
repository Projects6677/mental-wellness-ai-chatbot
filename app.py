import os
import json
import streamlit as st
import openai
from datetime import datetime
import random
import time

from config.prompts import SYSTEM_PROMPT
from utils.helpers import (
    get_suggestion,
    detect_crisis,
    load_helplines,
    format_helplines,
    MOOD_SUGGESTIONS,
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
    st.session_state.history = []

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# Load helplines (resources/helplines.json)
helplines = load_helplines("resources/helplines.json")

# Mood selector
mood = st.radio(
    "How are you feeling right now?",
    ("😊 Happy", "😔 Sad", "😨 Anxious", "😡 Angry", "😐 Neutral", "😟 Stressed"),
)

user_input = st.text_input(
    "Write to your AI Buddy (be honest):",
    placeholder=f"Tell me about what's on your mind. You can say something like, 'I'm feeling {mood.split()[1].lower()} because...'"
)

col1, col2 = st.columns([1, 1])
with col1:
    send = st.button("Send")
with col2:
    quick_tip = st.button("Get a suggestion for this mood")

# Display conversation history using chat elements
for message in st.session_state.history:
    # Use .get() to safely access 'content' or fallback to 'text' for old messages
    content = message.get("content", message.get("text", ""))
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            st.markdown(content)

# Quick suggestion only (no LLM call)
if quick_tip:
    with st.chat_message("assistant"):
        st.info(random.choice(MOOD_SUGGESTIONS.get(mood, ["Take a deep breath. You're doing your best and that matters."])))

# When user sends message
if send and user_input.strip():
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.history.append({"role": "user", "content": user_input})
    
    # Update streak
    update_streak()
    
    # Analyze sentiment
    sentiment = get_sentiment(user_input)
    
    # Crisis detection (simple keyword-based). If crisis -> show helplines prominently
    crisis_flag, evidence = detect_crisis(user_input)
    if crisis_flag:
        with st.chat_message("assistant"):
            st.error(
                "⚠️ I detect language that suggests you may be in severe distress or crisis. "
                "If you are in immediate danger, please call your local emergency number now."
            )
            st.markdown(format_helplines(helplines))
        
        system_prompt = (
            SYSTEM_PROMPT
            + "\nNOTE: The user may be in crisis. Prioritize calm, supportive language and encourage seeking immediate help. "
            "Do NOT provide instructions for self-harm. Give crisis resources and encourage contacting professionals."
        )
        st.session_state.messages.append({"role": "system", "content": system_prompt})
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})

    # Call OpenAI (chat completion)
    try:
        with st.chat_message("assistant"):
            with st.spinner("AI Buddy is thinking..."):
                full_response = ""
                message_placeholder = st.empty()

                for chunk in openai.ChatCompletion.create(
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
            ai_text = (
                "Sorry — I'm having trouble connecting to my brain. Try again in a moment."
            )
    
    st.session_state.history.append({"role": "assistant", "content": ai_text})

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
        [f"{h['role'].upper()}: {h['content']}" for h in st.session_state.history]
    )
    st.download_button("Download transcript (txt)", data=transcript, file_name="transcript.txt")
