# -----------------------------
# File: functions.py
# -----------------------------
import os
import re
import time
from io import BytesIO
from typing import List, Tuple, Dict

import pymupdf  # PyMuPDF
import numpy as np
import requests
import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import (
    get_groq_api_key,
    get_api_ninjas_key,
    MODEL_PRIORITY,
    PDF_FOLDER,
    MAX_WORDS_PER_CHUNK,
    TOP_K_CHUNKS_FOR_QA,
)

# Optional metrics
def compute_metrics_rouge_bleu(reference: str, candidate: str) -> Dict[str, float]:
    """Return ROUGE-1/2/L and BLEU scores. Heavy deps are imported lazily.
    NOTE: This function is defined for completeness but never called in the app.
    """
    try:
        import evaluate  # lazy import
        rouge = evaluate.load("rouge")
        bleu = evaluate.load("bleu")
        rouge_result = rouge.compute(predictions=[candidate], references=[reference])
        bleu_result = bleu.compute(predictions=[candidate], references=[[reference]])
        return {
            "rouge1": float(rouge_result.get("rouge1", 0.0)),
            "rouge2": float(rouge_result.get("rouge2", 0.0)),
            "rougeL": float(rouge_result.get("rougeL", 0.0)),
            "bleu": float(bleu_result.get("bleu", 0.0)),
        }
    except Exception:
        return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0, "bleu": 0.0}

# Register a Unicode font for PDF export (best-effort)
try:
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
except Exception:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# PDF utilities
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def discover_pdfs(folder: str = PDF_FOLDER) -> List[str]:
    if not os.path.exists(folder):
        return []
    files = [f for f in os.listdir(folder) if f.lower().endswith('.pdf')]
    files.sort()
    return files


@st.cache_data(show_spinner=False)
def extract_text_from_pdf_path(path: str) -> str:
    if not os.path.exists(path):
        return ""
    try:
        doc = pymupdf.open(path)
    except Exception:
        return ""
    texts: List[str] = []
    for p in doc:
        try:
            texts.append(p.get_text())
        except Exception:
            continue
    doc.close()
    return "\n".join(texts)


def _split_into_sentences(text: str) -> List[str]:
    return re.split(r"(?<=[\.!?])\s+", text.strip())


@st.cache_data(show_spinner=False)
def chunk_text(text: str, max_words: int = MAX_WORDS_PER_CHUNK) -> List[str]:
    sentences = _split_into_sentences(text)
    chunks, current, wc = [], [], 0
    for s in sentences:
        words = s.split()
        if not words:
            continue
        if wc + len(words) > max_words:
            if current:
                chunks.append(" ".join(current))
            current, wc = words.copy(), len(words)
        else:
            current.extend(words)
            wc += len(words)
    if current:
        chunks.append(" ".join(current))
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# LLM client + calls (Groq)
# ─────────────────────────────────────────────────────────────────────────────

_groq_client = None


def _get_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    key = get_groq_api_key()
    if not key or key == "your_groq_api_key_here":
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=key)
        return _groq_client
    except Exception:
        return None


def _chat_complete(messages: List[Dict[str, str]]):
    client = _get_client()
    if client is None:
        # Fallback so UI still works without a key
        for m in reversed(messages):
            if m["role"] == "user":
                txt = m["content"]
                return {"text": (txt[:800] + ("..." if len(txt) > 800 else ""))}
        return {"text": "[No Groq API key configured]"}

    last_error = None
    for model in MODEL_PRIORITY:
        try:
            resp = client.chat.completions.create(model=model, messages=messages)
            if hasattr(resp, "choices") and resp.choices:
                return {"text": resp.choices[0].message.content}
        except Exception as e:
            last_error = e
            time.sleep(0.4)
            continue
    return {"text": f"[LLM error: {last_error}]"}


def summarize_text_long(text: str) -> str:
    """Summarize long text by chunking, then refining a combined draft."""
    chunks = chunk_text(text)
    if not chunks:
        return ""
    partials: List[str] = []
    for c in chunks:
        out = _chat_complete([
            {"role": "system", "content": "You are a concise academic summarizer."},
            {"role": "user", "content": f"Summarize this section in 3–6 bullet points.\n\n{c}"},
        ])["text"]
        partials.append(out)
    combined = "\n\n".join(partials)
    final = _chat_complete([
        {"role": "system", "content": "You write clean, faithful, non-redundant summaries."},
        {"role": "user", "content": f"Unify and deduplicate the notes below into a single coherent summary with short headings if useful.\n\n{combined}"},
    ])["text"]
    return final


# ─────────────────────────────────────────────────────────────────────────────
# Auto-detect best PDF for a question/summary prompt
# ─────────────────────────────────────────────────────────────────────────────

def _tfidf_best_pdf_and_chunks(query: str, pdf_names: List[str]) -> Tuple[str, List[str], float]:
    """Return best matching PDF name, its top-K chunks, and an average relevance score."""
    best_pdf, best_score, best_chunks = None, -1.0, []
    for pdf in pdf_names:
        text = extract_text_from_pdf_path(os.path.join(PDF_FOLDER, pdf))
        chunks = chunk_text(text)
        if not chunks:
            continue
        vec = TfidfVectorizer().fit([query] + chunks)
        sims = cosine_similarity(vec.transform([query]), vec.transform(chunks)).flatten()
        top_idx = np.argsort(sims)[::-1][:TOP_K_CHUNKS_FOR_QA]
        top_scores = [sims[i] for i in top_idx]
        avg_score = float(np.mean(top_scores)) if top_scores else 0.0
        if avg_score > best_score:
            best_pdf, best_score, best_chunks = pdf, avg_score, [chunks[i] for i in top_idx]
    return best_pdf or "", best_chunks, max(best_score, 0.0)


def _api_ninjas_refine(query: str, chunks: List[str]) -> List[str]:
    """Optionally re-rank chunks using API Ninjas if key is present."""
    key = get_api_ninjas_key()
    if not key or key == "your_api_ninjas_key_here":
        return chunks
    url = "https://api.api-ninjas.com/v1/textsimilarity"
    headers = {"X-Api-Key": key}
    scored = []
    for c in chunks:
        try:
            r = requests.post(url, headers=headers, json={"text_1": query, "text_2": c}, timeout=8)
            sim = r.json().get("similarity", 0.0) if r.ok else 0.0
        except Exception:
            sim = 0.0
        scored.append((sim, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def answer_question_auto(question: str) -> Tuple[str, str, float]:
    """Auto-detect relevant PDF and answer using its top chunks. Returns (answer, pdf_name, score)."""
    pdfs = discover_pdfs()
    if not pdfs:
        return ("[No PDFs found in the 'pdfs' folder.]", "", 0.0)

    best_pdf, top_chunks, score = _tfidf_best_pdf_and_chunks(question, pdfs)
    if not best_pdf:
        return ("[Could not determine a relevant PDF for this question]", "", 0.0)

    top_chunks = _api_ninjas_refine(question, top_chunks)
    context = "\n\n".join(top_chunks)
    prompt = (
        f"You are answering a question about the PDF titled '{best_pdf}'.\n"
        f"Use ONLY the context below. If the answer is not present, say so clearly.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\n"
        f"Answer concisely and, when helpful, quote short snippets in parentheses."
    )
    out = _chat_complete([
        {"role": "system", "content": "You are a precise academic assistant."},
        {"role": "user", "content": prompt},
    ])["text"]
    return out, best_pdf, score


def summarize_on_prompt(prompt_text: str) -> Tuple[str, str, float]:
    """Auto-detect the best PDF for the user's summary prompt and summarize it. Returns (summary, pdf_name, score)."""
    pdfs = discover_pdfs()
    if not pdfs:
        return ("[No PDFs found in the 'pdfs' folder.]", "", 0.0)
    best_pdf, top_chunks, score = _tfidf_best_pdf_and_chunks(prompt_text, pdfs)
    if not best_pdf:
        return ("[Could not find relevant information to summarize. Please try again or refer the website]", "", 0.0)
    # Build a condensed context from top chunks and ask the model for a summary of that document
    context = "\n\n".join(top_chunks)
    final = _chat_complete([
        {"role": "system", "content": "You create faithful, high-level summaries of academic/policy PDFs."},
        {"role": "user", "content": f"Based on the context snippets from the PDF '{best_pdf}', write a clean summary with short headings, covering the most relevant points to this request: '{prompt_text}'.\n\nContext:\n{context}"},
    ])["text"]
    return final, best_pdf, score


# ─────────────────────────────────────────────────────────────────────────────
# Download helper
# ─────────────────────────────────────────────────────────────────────────────

def generate_pdf(title: str, content: str):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"<b>{title}</b>", styles['Title']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(content.replace('\n', '<br/>'), styles['BodyText']))
    doc.build(story)
    buffer.seek(0)
    return buffer

