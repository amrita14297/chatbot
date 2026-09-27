import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"), transport="rest")

st.title("My Chatbot")

# --- Sidebar settings ---
with st.sidebar:
    st.header("Settings")
    model_choice = st.selectbox(
        "Model",
        ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-pro"],
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    system_prompt = st.text_area(
        "System prompt (personality)",
        value="You are a helpful, friendly assistant.",
        #You are a helpful, friendly assistant for Toma Dojo true karate Martial arts school. based of Matthews, NC. your school website in www.tomadojo.com
    )
    if st.button("Clear chat"):
        st.session_state.pop("chat", None)
        st.session_state.pop("messages", None)
        st.rerun()

# --- Init / rebuild chat session if settings changed ---
settings_key = (model_choice, temperature, system_prompt)
if "chat" not in st.session_state or st.session_state.get("settings_key") != settings_key:
    model = genai.GenerativeModel(
        model_name=model_choice,
        system_instruction=system_prompt,
        generation_config={"temperature": temperature},
    )
    st.session_state.chat = model.start_chat(history=[])
    st.session_state.messages = []
    st.session_state.settings_key = settings_key

# --- Display history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Input ---
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

    response = st.session_state.chat.send_message(user_input)

    st.session_state.messages.append({"role": "assistant", "content": response.text})
    with st.chat_message("assistant"):
        st.markdown(response.text)
