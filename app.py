import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import TooManyRequests

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"), transport="rest")

st.markdown(
    """
    <style>
    .bo-header {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    </style>
    <div class="bo-header">Bo — Dojo Assistant</div>
    """,
    unsafe_allow_html=True,
)

# --- Fixed settings (not user-editable) ---
MODEL_NAME = "gemini-3.5-flash-lite"
TEMPERATURE = 0.7
SYSTEM_PROMPT = """You are the friendly virtual assistant for Toma Dojo - True Karate,
a martial arts school teaching Okinawan Uechi Ryu Karate in Matthews, NC. Your school website is www.tomadojo.com.
Help visitors with questions about classes, schedules, trials, and the dojo. The Owner of the Dojo is Sensei Philip Hoskins. Their fb page handle is Toma Dojo -true karate
Keep answers concise and welcoming."""

def start_new_chat():
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config={"temperature": TEMPERATURE},
    )
    st.session_state.chat = model.start_chat(history=[])
    st.session_state.messages = []

    # Hidden kickoff message — generates the intro, never shown to the user
    try:
        intro = st.session_state.chat.send_message(
            "Introduce yourself to a visitor who just opened the chat window. "
            "Keep it to one short, friendly sentence."
        )
        intro_text = intro.text
    except TooManyRequests:
        intro_text = "Hi, I'm Bo! How can I help you today?"  # fallback if rate-limited

    st.session_state.messages.append({"role": "assistant", "content": intro_text})

# --- Init chat session once ---
if "chat" not in st.session_state:
    start_new_chat()

# --- Clear chat button ---
if st.button("Clear chat"):
    start_new_chat()
    st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Say something...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        response = st.session_state.chat.send_message(user_input)
        reply_text = response.text
    except TooManyRequests:
        reply_text = "I'm getting a lot of requests right now — please try again in a moment."

    st.session_state.messages.append({"role": "assistant", "content": reply_text})
    with st.chat_message("assistant"):
        st.markdown(reply_text)
