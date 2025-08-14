# -----------------------------
# File: ui.py
# -----------------------------
# Glassmorphism + sticky header

import streamlit as st
from PIL import Image
import os

# Glass UI / modern styling
_CSS = """
/* Fonts */
body, div, h1, h2, h3, p, span {
    font-family: 'Helvetica', 'Arial', sans-serif;
}

/* General background */
body {
    background-color: #f7f6fb;
}

/* Sticky header with gradient and glass effect */
.header {
    position: sticky;
    top: 0;
    z-index: 999;
    backdrop-filter: blur(10px);
    background: rgba(255, 255, 255, 0.2);
    border-radius: 16px;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
}

/* Header texts */
.header-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #2b2b2b;
    margin: 0;
}
.header-sub {
    font-size: 1rem;
    color: rgba(43,43,43,0.8);
    margin: 0;
}

/* Glass cards for Q&A and Summary */
.glass-card {
    background: rgba(255,255,255,0.15);
    border-radius: 18px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.2);
    max-height: 650px;
    overflow-y: auto;
    animation: fadeIn 0.7s;
}

/* Inputs */
textarea, input, select {
    border-radius: 12px !important;
    padding: 12px !important;
    border: 1px solid rgba(200,200,200,0.4) !important;
    background: rgba(255,255,255,0.25) !important;
    color: #1b1b1b !important;
}

/* Placeholder text */
::placeholder {
    color: rgba(0,0,0,0.4);
    font-style: italic;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg, #6c5ce7, #4e36b8);
    color: white;
    border-radius: 14px;
    padding: 12px 24px;
    font-weight: 600;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.25);
}

/* Footer */
.footer {
    text-align: center;
    color: rgba(0,0,0,0.5);
    font-size: 0.85rem;
    padding-top: 10px;
}

/* Fade-in animation */
@keyframes fadeIn {
    0% {opacity:0;}
    100% {opacity:1;}
}
"""

def inject_styles():
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

# Header rendering
def render_header(logo_path='logo.png'):
    inject_styles()
    st.divider()
    cols = st.columns([1,4])
    with cols[0]:
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                st.image(img, width=500)
            except Exception:
                st.markdown("<h2 class='header-title'>InfoGaiter</h2>", unsafe_allow_html=True)
        else:
            st.markdown("<h2 class='header-title'>InfoGaiter</h2>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(
            "<div style='padding-top:18px'>"
            "<h3 class='header-title' style='font-size:1.4rem'>InfoGaiter</h3>"
            "<p class='header-sub'>Have a question about the university? Ask away or know more in summaries</p>"
            "</div>", unsafe_allow_html=True
        )
    st.divider()