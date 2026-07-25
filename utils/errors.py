"""Shared error-display helper.

Every LLM-call site in this app used to do `st.error(f"Groq Error:\n\n{e}")`
— which puts the raw exception string (stack traces, provider-internal
error bodies, sometimes key-adjacent details) directly in front of the
user. That's fine for local debugging but not great for a public
deployment, and it's duplicated in five different files.

show_llm_error() logs the full exception server-side (so you still
have everything you need to debug) and shows a short, friendly,
non-leaky message to the user instead. Rate-limit errors get a
slightly different message since "wait a moment and try again" is
genuinely actionable advice for that specific case.
"""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def show_llm_error(e: Exception, action: str = "complete that request") -> None:
    """Log `e` with full detail, then render a friendly st.error().

    action: a short lowercase phrase describing what was being
    attempted, e.g. "generate the quiz" or "answer your question" —
    used to make the user-facing message specific.
    """
    logger.exception("LLM call failed while trying to %s", action)

    msg = str(e).lower()
    if "rate-limited" in msg or "rate_limit" in msg or "rate limit" in msg:
        st.error(
            "⏳ All configured models are currently rate-limited. "
            "Please wait a moment and try again."
        )
    else:
        st.error(
            f"⚠️ Something went wrong trying to {action}. Please try again "
            "in a moment. If this keeps happening, double-check your API "
            "keys are set correctly."
        )
