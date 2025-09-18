import streamlit as st
import os
import openai
import random
import json
from datetime import datetime

# Set the completions model
COMPLETIONS_MODEL = "gpt-3.5-turbo"

# --- Load API Key (Handles both local .env and Streamlit Cloud secrets) ---
try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
except KeyError:
    st.error("OpenAI API key not found. Please set it as an environment variable or a Streamlit secret.")
    st.stop()

# --- Load Crisis Resources from JSON file ---
try:
    with open("resources/helplines.json", "r") as f:
        RESOURCES = json.load(f)
except FileNotFoundError:
    st.error("Helplines JSON file not found. Please ensure it exists in the 'resources' directory.")
    st.stop()

# --- Import and Configuration ---
# Assuming 'config/prompts.py' contains SYSTEM_PROMPT
# Assuming 'utils/helpers.py' contains SUGGESTIONS
try:
    from config.prompts import SYSTEM_PROMPT
    from utils.helpers import SUGGESTIONS
except ImportError as e:
    st.error(f"Error importing modules: {e}. Please ensure 'config/prompts.py' and 'utils/helpers.py' exist.")
    st.stop()

# --- Helper function for sentiment analysis ---
def get_sentiment(text):
    """Analyzes sentiment of the user's input using the AI."""
    sentiment_prompt = f"Analyze the sentiment of the following text. Respond with only a single word: 'positive', 'negative', or 'neutral'.\n\nText: '{text}'"
    
    try:
        response = openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL,
            messages=[{"role": "user", "content": sentiment_prompt}],
            temperature=0.0
        )
        sentiment = response.choices[0].message.content.strip().lower()
        return sentiment
    except Exception as e:
        st.warning(f"Sentiment analysis failed: {e}")
        return "neutral"

# --- Streak Tracker Functions ---
def update_streak():
    """Updates the user's check-in streak."""
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

# --- Streamlit UI ---
st.set_page_config(page_title="AI Buddy", layout="centered", initial_sidebar_state="collapsed")
st.title("AI Buddy: Your Mental Wellness Companion")
st.markdown("A confidential and empathetic space to check in with yourself.")

# Display Streak Counter
update_streak()
st.subheader(f"Current Streak: 🔥 {st.session_state.streak_count} day(s)")

# --- Mood Tracker Buttons ---
st.markdown("### How are you feeling right now?")
cols = st.columns(len(SUGGESTIONS))
for col, emoji in zip(cols, SUGGESTIONS.keys()):
    if col.button(emoji, use_container_width=True):
        st.session_state.current_mood = emoji
        st.session_state.chat_history.append({"role": "assistant", "content": random.choice(SUGGESTIONS[emoji])})
        st.session_state.mood_selected = True

# --- Chat History Management ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "Hi there. I'm AI Buddy. How are you feeling today?"}]
if "mood_selected" not in st.session_state:
    st.session_state.mood_selected = False
if "current_mood" not in st.session_state:
    st.session_state.current_mood = ""

# Display chat messages from history on app rerun
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- User Input & AI Response Generation ---
if prompt := st.chat_input("What's on your mind?"):
    # This is where the streak is updated, as it signifies a check-in
    update_streak()
    
    sentiment = get_sentiment(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(f"({sentiment.capitalize()} sentiment detected) {prompt}")

    with st.chat_message("assistant"):
        with st.spinner("AI Buddy is thinking..."):
            # Add a message with sentiment information to guide the AI's response
            messages = [{"role": "system", "content": SYSTEM_PROMPT + f"\n\nUser's current emotional state is: {sentiment}. Adjust your tone and response accordingly."}] + [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.chat_history
            ]
            
            response = openai.ChatCompletion.create(
                model=COMPLETIONS_MODEL,
                messages=messages,
                temperature=0.7,
                stream=True
            )
            
            # Stream response for a better user experience
            full_response = ""
            message_placeholder = st.empty()
            for chunk in response:
                delta_content = chunk["choices"][0]["delta"].get("content", "")
                full_response += delta_content
                message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.chat_history.append({"role": "assistant", "content": full_response})

# --- Display Suggestions & Resources after mood selection ---
if st.session_state.mood_selected:
    st.divider()
    st.markdown("### Some resources and ideas for you")
    st.markdown(f"**Based on your mood: {st.session_state.current_mood}**")
    st.markdown(random.choice(SUGGESTIONS[st.session_state.current_mood]))

    st.subheader("Crisis Resources")
    for resource in RESOURCES:
        st.info(f"**{resource['name']}:** {resource['link']}")

    st.session_state.mood_selected = False
