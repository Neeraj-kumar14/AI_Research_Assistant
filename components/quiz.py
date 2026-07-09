import streamlit as st


def render_quiz():
    if st.session_state.quiz:

        st.header("📝 Interactive Quiz")

        current = st.session_state.current_question

        q = st.session_state.quiz[current]

        st.subheader(
            f"Question {current + 1} / {len(st.session_state.quiz)}"
        )

        progress = (current + 1) / len(st.session_state.quiz)

        st.progress(progress)

        st.write(q["question"])

        selected = st.radio(
            "Choose your answer:",
            q["options"],
            key=f"quiz_{current}",
            disabled=st.session_state.quiz_submitted
            )

        st.session_state.quiz_answers[current] = selected
        col1, col2 = st.columns(2)

        with col1:

            if current > 0:

                if st.button(
                    "⬅ Previous",
                    key="quiz_prev"
                ):
                    st.session_state.current_question -= 1
                    st.rerun()

        with col2:
            # st.write("Inside Col2")
            # st.write(current)
            # st.write(len(st.session_state.quiz))
            if current < len(st.session_state.quiz) - 1:

                if st.button(
                    "Next ➡",
                    key="quiz_next"
                ):

                    st.session_state.current_question += 1
                    st.rerun()

            else:

                if st.button(
                    "✅ Submit Quiz",
                    key="quiz_submit"
                ):

                    score = 0

                    option_letters = ["A", "B", "C", "D"]

                    for i, q in enumerate(st.session_state.quiz):

                        selected = st.session_state.quiz_answers.get(i)

                        if selected:

                            selected_letter = option_letters[
                                q["options"].index(selected)
                            ]

                            if selected_letter == q["answer"]:

                                score += 1

                    st.session_state.quiz_score = score

                    st.session_state.quiz_submitted = True

                    st.rerun()


    if st.session_state.quiz_submitted:

        total = len(st.session_state.quiz)

        score = st.session_state.quiz_score

        percentage = (score / total) * 100

        st.balloons()

        st.success(f"🏆 Quiz Completed!")

        st.markdown(f"## 🎯 Score: {score}/{total}")

        st.markdown(f"### 📊 Percentage: {percentage:.1f}%")

        if percentage >= 90:

            st.success("🥇 Excellent!")

        elif percentage >= 75:

            st.success("🥈 Very Good!")

        elif percentage >= 60:

            st.warning("🥉 Good Job!")

        else:

            st.error("📚 Needs More Practice!")

        st.progress(percentage / 100)

        if st.button(
            "📖 Review Answers",
            key="review_answers"
        ):

            st.session_state.review_mode = True

            st.rerun()

    if st.session_state.review_mode:

        st.header("📖 Review Answers")

        option_letters = ["A", "B", "C", "D"]

        for i, q in enumerate(st.session_state.quiz):

            st.subheader(f"Question {i+1}")

            st.write(q["question"])

            selected = st.session_state.quiz_answers.get(i)

            if selected:

                selected_letter = option_letters[
                    q["options"].index(selected)
                ]

                st.write(f"**Your Answer:** {selected_letter}")

                st.write(f"**Correct Answer:** {q['answer']}")

                if selected_letter == q["answer"]:

                    st.success("✅ Correct")

                else:

                    st.error("❌ Wrong")

            st.info(q["explanation"])

            st.divider()

# import streamlit as st


# def render_quiz():

#     if not st.session_state.quiz:
#         return

#     st.header("📝 Interactive Quiz")

#     current = st.session_state.current_question

#     q = st.session_state.quiz[current]

#     st.subheader(
#         f"Question {current + 1} / {len(st.session_state.quiz)}"
#     )

#     progress = (current + 1) / len(st.session_state.quiz)

#     st.progress(progress)

#     st.write(q["question"])

#     selected = st.radio(
#         "Choose your answer:",
#         q["options"],
#         key=f"quiz_{current}",
#         disabled=st.session_state.quiz_submitted
#     )

#     st.session_state.quiz_answers[current] = selected