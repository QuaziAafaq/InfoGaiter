# -----------------------------
# File: main.py
# -----------------------------
# Entry point for Streamlit app (glass-style UI)

import os
import random
import streamlit as st
from config import PDF_FOLDER
from functions import (
    discover_pdfs,
    summarize_on_prompt,
    answer_question_auto,
    generate_pdf,
)
from ui import render_header

st.set_page_config(page_title="InfoGaiter", layout="wide", page_icon="🐊")


def main():
    render_header()

    # Side-by-side layout
    left, right = st.columns([1, 1], gap="large")

    # LEFT: Q&A — auto-detect best PDF
    with left:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### Ask a Question")
        st.caption("We automatically pick the most relevant information from BU Academic Calendar.")
        question = st.text_area("Your question", height=140, placeholder="e.g., What are the add/drop deadlines?")

        if st.button("Get Answer", key="ask_btn"):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                spinner_messages = [
                    "Snapping up the best answer for you…",
                    "Gliding towards your question…",
                    "Surfacing with fresh campus wisdom…",
                    "Keeping our jaws locked on your question…",
                    "Splashing through the archives…",
                    "Patrolling the river of resources…"
                ]

                with st.spinner(random.choice(spinner_messages)):
                    answer, used_pdf, score = answer_question_auto(question)

                st.markdown(f"<div class='glass-card'>{answer}</div>", unsafe_allow_html=True)
                st.download_button("Download Answer", data=generate_pdf("Answer", answer), file_name="answer.pdf")
        st.markdown("</div>", unsafe_allow_html=True)

    # RIGHT: Summarization — user types a topic; app selects PDF automatically
    with right:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### Summarize by Topic")
        st.caption("Type something like: ‘Music department’, ‘Internships’, ‘Financial aid overview’…")
        prompt = st.text_area("What should we summarize?", height=140, placeholder="e.g., Summarize the Internships policies")

        if st.button("Generate Summary", key="sum_btn"):
            if not prompt.strip():
                st.warning("Please enter a topic or instruction to summarize.")
            else:
                spinner_messages = [
                    "Swimming through the swamp of facts…",
                    "Crunching the numbers and the knowledge…",
                    "Surfacing with fresh campus wisdom…",
                    "Splashing through the archives…",
                    "Patrolling the river of resources…"
                ]
                with st.spinner(random.choice(spinner_messages)):
                    summary, used_pdf, score = summarize_on_prompt(prompt)

                st.markdown(f"<div class='glass-card'>{summary}</div>", unsafe_allow_html=True)
                st.download_button(
                    "Download Summary",
                    data=generate_pdf(f"Summary - {used_pdf or 'document'}", summary),
                    file_name=f"{(used_pdf or 'summary').replace('/', '_')}.pdf"
                )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='small' style='text-align:center;margin-top:16px'>Copyright © BU | Version 0.1 | Last update August 2025</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
