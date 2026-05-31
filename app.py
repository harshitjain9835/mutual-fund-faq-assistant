import sys
from pathlib import Path
import streamlit as st

# Add the src directory to the Python path to access backend modules
root_dir = Path(__file__).resolve().parent.parent
src_dir = root_dir / "src"
sys.path.append(str(src_dir))

from retrieval import retrieve_passages
from generate import generate_answer

# Page Configuration
st.set_page_config(page_title="Mutual Fund FAQ Assistant", page_icon="📈", layout="centered")

# UI Header & Disclaimer
st.title("📈 Mutual Fund FAQ Assistant")
st.markdown("Welcome! Ask objective, verifiable questions about mutual funds.")
st.warning("⚠️ **DISCLAIMER: Facts-only. No investment advice.**")

with st.expander("💡 Example questions you can ask"):
    st.markdown("""
    * What is the exit load for HDFC Mid Cap?
    * Who is the fund manager for HDFC Defence Fund?
    * What is the expense ratio for HDFC Small Cap Fund?
    """)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("e.g., What is the exit load for HDFC Mid Cap?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Process user query and generate response
    with st.chat_message("assistant"):
        with st.spinner("Searching official sources..."):
            passages = retrieve_passages(prompt)
            response = generate_answer(prompt, passages)
            st.markdown(response)
            
    st.session_state.messages.append({"role": "assistant", "content": response})