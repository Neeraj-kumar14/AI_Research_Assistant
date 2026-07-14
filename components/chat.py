import streamlit as st

from components.flashcards import render_flashcards


def render_source_cards(sources=None, web_sources=None):
    """Render retrieved chunks / web results as small index-card citations."""
    cards_html = ""

    if sources:
        shown = set()
        for chunk in sources:
            label = f"{chunk['source']} · p.{chunk['page']}"
            if label in shown:
                continue
            shown.add(label)
            cards_html += f'<div class="index-card">📄 {label}</div>'

    if web_sources:
        for url in web_sources:
            display = url if len(url) <= 40 else url[:37] + "..."
            cards_html += f'<div class="index-card web">🌐 <a href="{url}" target="_blank">{display}</a></div>'

    if cards_html:
        st.markdown(f'<div class="source-row">{cards_html}</div>', unsafe_allow_html=True)


def render_chat(messages):
    for idx, message in enumerate(messages):
        with st.chat_message(message["role"]):
            if message.get("type") == "quiz":
                for i, q in enumerate(message["content"], start=1):
                    st.markdown(f"**Question {i}.** {q['question']}")
                    for letter, opt in zip("ABCD", q["options"]):
                        st.markdown(f"&nbsp;&nbsp;**{letter}.** {opt}")
                    st.success(f"Correct answer: {q['answer']}")
                    st.info(q["explanation"])
                    st.divider()
            elif message.get("type") == "flashcards":
                cards = message.get("content")
                if cards:
                    render_flashcards(cards, key_prefix=f"fc-{idx}")
                else:
                    st.markdown(message.get("raw", "No flashcards generated."))
            else:
                st.markdown(message["content"])

                sources = message.get("sources")
                web_sources = message.get("web_sources")
                if sources or web_sources:
                    render_source_cards(sources, web_sources)
