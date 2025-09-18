import streamlit as st
import os
import openai
import random
import json

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

# --- Streamlit UI ---
st.set_page_config(page_title="AI Buddy", layout="centered", initial_sidebar_state="collapsed")
st.title("AI Buddy: Your Mental Wellness Companion")
st.markdown("A confidential and empathetic space to check in with yourself.")

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
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI Buddy is thinking..."):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
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
