import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("RAG Chatbot for PDFs")

# File uploader
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file is not None:
    if st.button("Process PDF"):
        with st.spinner("Processing your PDF..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            response = requests.post(f"{BACKEND_URL}/uploadfile/", files=files)  # Added trailing slash for upload
            if response.status_code == 200:
                st.session_state.index_ready = True  # FIXED: Set ONLY on success
                st.success(f"✅ {response.json()['message']}")
            else:
                st.session_state.index_ready = False  # Explicitly unset on error
                st.error(f"❌ {response.json().get('detail', 'Error processing PDF')}")

# FIXED: Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "index_ready" not in st.session_state:
    st.session_state.index_ready = False

# Chat interface (only if ready)
if st.session_state.index_ready:
    st.info("Ready to chat! Ask questions about your PDF below.")

    # Show chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask a question about the PDF:"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching and answering..."):
                response = requests.post(f"{BACKEND_URL}/query", json={"question": prompt})  # Matches fixed backend
                if response.status_code == 200:
                    answer = response.json()["answer"]
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"❌ Query error: {response.json().get('detail', 'Unknown issue')}")
else:
    if uploaded_file is None:
        st.info("👆 Upload a PDF and process it to start chatting.")
    # Chat hidden until ready

# Optional: Clear chat button (for UX)
if st.session_state.index_ready:
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()