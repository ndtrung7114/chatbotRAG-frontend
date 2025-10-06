import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("RAG Chatbot for PDFs")

# Display a prominent warning about the 6MB limit
st.warning("⚠️ **Maximum PDF size: 6MB** due to CPU limitations on our free Hugging Face deployment. Files larger than 6MB will not be processed, even though the upload area may indicate a 200MB limit.")

# File uploader with help message
uploaded_file = st.file_uploader(
    "Upload a PDF",
    type="pdf",
    help="Upload a PDF file (maximum size: 6MB). Larger files cannot be processed due to CPU limitations."
)

if uploaded_file is not None:
    # Validate file size (6MB = 6 * 1024 * 1024 bytes)
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if file_size_mb > 6:
        st.error("❌ The uploaded PDF exceeds the 6MB size limit. Please upload a smaller file.")
    elif st.button("Process PDF"):
        with st.spinner("Processing your PDF..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            response = requests.post(f"{BACKEND_URL}/uploadfile/", files=files)
            if response.status_code == 200:
                st.session_state.index_ready = True
                st.success(f"✅ {response.json()['message']}")
            else:
                st.session_state.index_ready = False
                st.error(f"❌ {response.json().get('detail', 'Error processing PDF')}")

# Initialize session state
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
                response = requests.post(f"{BACKEND_URL}/query", json={"question": prompt})
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