import streamlit as st

st.set_page_config(
    page_title="Knowledge Retrieval Platform",
    page_icon="🤖"
)

st.title("AI Knowledge Retrieval Platform")

st.write(
    "Ask questions and get answers from the available knowledge base."
)

query = st.text_input("Enter your question:")

if st.button("Ask"):
    if query:
        st.write("Query received:", query)
    else:
        st.warning("Please enter a question.")
