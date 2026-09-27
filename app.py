import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import TooManyRequests

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"), transport="rest")

st.title("My Chatbot")

# --- Fixed settings (not user-editable) ---
MODEL_NAME = "gemini-3.5-flash-lite"
TEMPERATURE = 0.7
SYSTEM_PROMPT = """You are the friendly virtual assistant for Toma Dojo,
a martial arts school teaching Okinawan Uechi Ryu Karate in Matthews, NC.
Help visitors with questions about classes, schedules, trials, and the dojo.
Keep answers concise and welcoming."""

# --- Init chat session once ---
if "chat" not in st.session_state:
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config={"temperature": TEMPERATURE},
    )
    st.session_state.chat = model.start_chat(history=[])
    st.session_state.messages = []

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
