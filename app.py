import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import TooManyRequests
from google.generativeai.types.generation_types import StopCandidateException


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"), transport="rest")

st.markdown(
    """
    <style>
    /* Tighten Streamlit's default page padding for a small embedded widget */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* Header */
    .bo-header {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    /* Chat message text */
    [data-testid="stChatMessage"] p {
        font-size: 0.9rem;
        line-height: 1.4;
    }

    /* Model selector — small and unobtrusive */
    [data-testid="stSelectbox"] div[data-baseweb="select"] {
        font-size: 0.8rem;
        min-height: 2rem;
    }

    /* Clear chat button — slightly smaller/tighter */
    .stButton button {
        font-size: 0.85rem;
        padding: 0.25rem 0.75rem;
    }
    </style>
    <div class="bo-header">Bo - Dojo Assistant</div>
    """,
    unsafe_allow_html=True,
)

# --- Fixed settings (not user-editable) ---
# Display label -> model ID. First entry is the default.
# Add more from https://ai.google.dev/gemini-api/docs/models (check exact IDs first).
MODELS = {
    "Gemini 3.5 Flash Lite": "gemini-3.5-flash-lite",
    "Gemini 3.5 Flash": "gemini-3.5-flash",
}
DEFAULT_LABEL = next(iter(MODELS))
TEMPERATURE = 0.7
SYSTEM_PROMPT = """You are Bo, the friendly virtual assistant for Toma Dojo - True Karate,
a martial arts school in Matthews, NC teaching Okinawan Uechi Ryu Karate.

## What you know
- Uechi Ryu is a traditional Okinawan karate style known for close-range fighting,
  circular blocks, and full-contact body conditioning (rather than the more
  linear, long-range strikes typical of many Japanese styles). It was founded
  by Kanbun Uechi, who studied in Fujian, China, and brought the style back to
  Okinawa in the early 1900s.
- Toma Dojo teaches students ages 7 and up, all experience levels.
- Owner and principal instructor: Sensei Philip Hoskins (Godan, 5th-degree
  black belt), training in Uechi Ryu since age 14.
- Website: www.tomadojo.com
- Facebook: "Toma Dojo - True Karate"
- For class schedules, pricing, or trial signups you don't have exact details
  for, direct visitors to the website or to book a trial class rather than
  guessing.

## How to behave
- Keep answers short and conversational — 1-3 sentences unless the visitor
  asks for detail.
- Only mention the Sensei's name, the style's history, or other background
  facts when they're actually relevant to what was asked — don't reintroduce
  yourself or repeat the same facts in every reply.
- Vary your phrasing naturally across a conversation; don't reuse the same
  sentence structure or opening line repeatedly.
- If you don't know something specific (exact class times, pricing, current
  events), say so honestly and point them to the website, Facebook page, or
  suggest contacting the dojo directly — don't make up details.
"""

def start_new_chat(model_id, history=None):
    model = genai.GenerativeModel(
        model_name=model_id,
        system_instruction=SYSTEM_PROMPT,
        generation_config={"temperature": TEMPERATURE, "max_output_tokens": 800},
    )
    st.session_state.chat = model.start_chat(history=history or [])
    st.session_state.active_model = model_id

    # Switching models mid-conversation: keep the visible messages and skip the intro
    if history is not None:
        return

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
    start_new_chat(MODELS[DEFAULT_LABEL])

# --- Clear chat button ---
if st.button("Clear chat"):
    start_new_chat(MODELS[st.session_state.get("model_label", DEFAULT_LABEL)])
    st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Model selector (sits just above the chat input) ---
st.selectbox(
    "Model",
    list(MODELS.keys()),
    key="model_label",
    label_visibility="collapsed",
)
chosen_id = MODELS[st.session_state.model_label]
if chosen_id != st.session_state.active_model:
    # Rebuild the chat on the new model, carrying over the conversation so far
    start_new_chat(chosen_id, history=st.session_state.chat.history)

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
    except StopCandidateException as e:
        finish_reason = e.args[0].finish_reason if e.args else "unknown"
        print(f"StopCandidateException — finish_reason: {finish_reason}")
        reply_text = "Sorry, I couldn't respond to that one — could you rephrase your question?"


    st.session_state.messages.append({"role": "assistant", "content": reply_text})
    with st.chat_message("assistant"):
        st.markdown(reply_text)
