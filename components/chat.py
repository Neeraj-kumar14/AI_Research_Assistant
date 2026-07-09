import streamlit as st


def render_chat(messages):

    # -----------------------------
    # Show Chat History
    # -----------------------------

    for message in messages:

        with st.chat_message(message["role"]):

            if message.get("type") == "quiz":

                for i, q in enumerate(message["content"], start=1):

                    st.markdown(f"## Question {i}")

                    st.markdown(f"**Question:** {q['question']}")

                    st.markdown("**Options:**")

                    st.markdown(f"A. {q['options'][0]}")
                    st.markdown(f"B. {q['options'][1]}")
                    st.markdown(f"C. {q['options'][2]}")
                    st.markdown(f"D. {q['options'][3]}")

                    st.success(f"✅ Correct Answer: {q['answer']}")

                    st.info(q["explanation"])

                    st.divider()

            else:

                st.markdown(message["content"])