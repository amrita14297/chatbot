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

    /* Clear chat button — slightly smaller/tighter */
    .stButton button {
        font-size: 0.85rem;
        padding: 0.25rem 0.75rem;
    }
    </style>
    <div class="bo-header">Chat Assistant</div>
    """,
    unsafe_allow_html=True,
)

# --- Fixed settings (not user-editable) ---
MODEL_NAME = "gemini-3.5-flash-lite"
TEMPERATURE = 0.7
SYSTEM_PROMPT = """You are a helpful, knowledgeable AI assistant. You can discuss a wide range of
topics including science, technology, history, culture, current events (via
search when available), everyday advice, writing help, coding, math, and
general problem-solving.

## How to behave
- Answer directly and concisely first; expand into more detail only if the
  question calls for it or the user asks for more.
- Match the user's tone and level of technical detail — simplify for a
  beginner, go deeper for an expert, without over-explaining either way.
- If a question is ambiguous, make a reasonable assumption and answer, rather
  than asking a clarifying question for every small uncertainty.
- If you don't know something or it requires current/real-time information
  you don't have access to, say so plainly rather than guessing or making up
  details.
- For subjective, opinion-based, or controversial questions, give a fair,
  balanced view of the different perspectives rather than pushing one as
  correct.
- Don't pad answers with unnecessary caveats, disclaimers, or repeated
  reminders of what you already said earlier in the conversation.
- Use formatting (lists, headers, code blocks) only when it genuinely helps
  readability — plain prose is fine for simple answers.
- Be honest and direct, including when correcting a mistake the user made or
  disagreeing with something they said — do this respectfully, not bluntly.
"""

def start_new_chat():
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config={"temperature": TEMPERATURE, "max_output_tokens": 800},
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
    except StopCandidateException as e:
        finish_reason = e.args[0].finish_reason if e.args else "unknown"
        print(f"StopCandidateException — finish_reason: {finish_reason}")
        reply_text = "Sorry, I couldn't respond to that one — could you rephrase your question?"


    st.session_state.messages.append({"role": "assistant", "content": reply_text})
    with st.chat_message("assistant"):
        st.markdown(reply_text)
