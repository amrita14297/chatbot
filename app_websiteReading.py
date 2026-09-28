import os
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
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

    /* Disclaimer shown under the chat input */
    [data-testid="stBottom"] > div::after {
        content: "AI can make mistakes. Please double-check important information.";
        display: block;
        text-align: center;
        font-size: 0.7rem;
        color: #808495;
        padding: 0.25rem 0 0.4rem;
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
MODEL_NAME = "gemini-3.5-flash-lite"
TEMPERATURE = 0.7
BASE_PROMPT = """You are Bo, the friendly virtual assistant for Toma Dojo - True Karate,
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

# --- Website knowledge (read from the live site, refreshed hourly) ---
SITE_URL = "https://www.tomadojo.com"
# Pages to try even if the homepage doesn't link to them (missing pages are skipped)
EXTRA_PAGES = ["schedule", "instructors", "events", "gallery", "start-trial", "uechi-ryu"]
MAX_PAGES = 15
MAX_SITE_CHARS = 40000
SKIP_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".ico", ".css", ".js")


def _clean_page(html, keep_footer=False):
    """Turn a page's HTML into plain text (drops scripts, nav menus and repeated footers)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "nav"]):
        tag.decompose()
    if not keep_footer:
        for tag in soup.find_all("footer"):
            tag.decompose()
    # Keep the address of outside links (Facebook, Instagram, ...) so Bo can share them
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and "tomadojo.com" not in href:
            a.append(f" ({href})")
    text = soup.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


@st.cache_data(ttl=3600, show_spinner=False)
def load_site_content():
    """Fetch the site's pages as plain text. Returns '' if the site can't be reached."""
    try:
        home = requests.get(SITE_URL, timeout=10)
        home.raise_for_status()
    except requests.RequestException:
        return ""

    def norm(u):
        return u.split("#")[0].split("?")[0].rstrip("/")

    def is_home(u):
        return u in (SITE_URL, SITE_URL + "/home")

    host = urlparse(SITE_URL).netloc.replace("www.", "")
    soup = BeautifulSoup(home.text, "html.parser")
    candidates = [urljoin(SITE_URL + "/", a["href"]) for a in soup.find_all("a", href=True)]
    candidates += [f"{SITE_URL}/{p}" for p in EXTRA_PAGES]

    urls = []
    for u in map(norm, candidates):
        same_site = urlparse(u).netloc.replace("www.", "") == host
        if same_site and not is_home(u) and not u.lower().endswith(SKIP_EXT) and u not in urls:
            urls.append(u)

    home_text = _clean_page(home.text, keep_footer=True)
    seen = {home_text}
    blocks = [f"### PAGE: {SITE_URL}/home\n{home_text}"]
    for u in urls[:MAX_PAGES]:
        try:
            r = requests.get(u, timeout=10)
        except requests.RequestException:
            continue
        if r.status_code != 200 or "text/html" not in r.headers.get("Content-Type", ""):
            continue
        text = _clean_page(r.text)
        if text and text not in seen:  # skips "not found" pages that return the homepage
            seen.add(text)
            blocks.append(f"### PAGE: {u}\n{text}")
    return "\n\n".join(blocks)[:MAX_SITE_CHARS]


SITE_CONTENT = load_site_content()
SYSTEM_PROMPT = BASE_PROMPT
if SITE_CONTENT:
    SYSTEM_PROMPT += f"""
## Website content
Below is the current text of the Toma Dojo website. Treat it as your main source
of truth for anything about the dojo (classes, schedule, instructors, events,
pricing, contact details, policies). Answer specific questions from it accurately,
and mention the relevant page (for example www.tomadojo.com/schedule) when helpful.
If something isn't covered here, say you don't have that detail and point them to
the website, Facebook page, or suggest contacting the dojo directly - never guess.

{SITE_CONTENT}
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

# --- Model in use (sits just above the chat input) ---
st.caption(f"Model: {MODEL_NAME}")

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
