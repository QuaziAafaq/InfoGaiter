# -----------------------------
# File: config.py
# -----------------------------
"""Configuration for API keys, model choice, file locations, and routing.
- Keys can be set here (placeholders) or via env vars / st.secrets. Env/st.secrets override.
- No model names are ever shown in the UI.
- PDFs live in ./pdfs (bundled with the app).
"""
import os

# ── ▼▼ OPTIONAL INLINE KEYS (env/st.secrets override) ▼▼ ─────────────────────
DEFAULT_GROQ_API_KEY = "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"
DEFAULT_API_NINJAS_KEY = "1GQ7si67cmFs1UXq4mC5jA==Ynh3UwXH1SGb616G"  # optional, for similarity refinement
# ── ▲▲ OPTIONAL INLINE KEYS ▲▲ ───────────────────────────────────────────────

# Preferred models (hidden). First that works will be used.
MODEL_PRIORITY = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

# Where your bundled PDFs live
PDF_FOLDER = "pdfs"

# Chunking / retrieval params
MAX_WORDS_PER_CHUNK = 500
TOP_K_CHUNKS_FOR_QA = 3  # how many top chunks from the best PDF to feed the LLM

# ---------------------------------------------------------------------------
# Helpers to read from environment or fall back to placeholders above
# ---------------------------------------------------------------------------

def get_groq_api_key() -> str:
    key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_API_KEY
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY", key)
    except Exception:
        pass
    return key


def get_api_ninjas_key() -> str:
    key = os.getenv("API_NINJAS_KEY") or DEFAULT_API_NINJAS_KEY
    try:
        import streamlit as st
        key = st.secrets.get("API_NINJAS_KEY", key)
    except Exception:
        pass
    return key