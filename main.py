import os
import uuid

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "20"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "600"))

st.set_page_config(page_title="Scientific Paper RAG", page_icon="🔬", layout="wide")


def api_error(response: requests.Response) -> str:
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text or f"HTTP {response.status_code}"


def render_sources(sources: list[dict]) -> None:
    for source in sources:
        scores = f"vector={source['retrieval_score']}"
        if source.get("rerank_score") is not None:
            scores += f", reranker={source['rerank_score']}"
        heading = f"[{source['rank']}] {source['source']}"
        if source.get("section"):
            heading += f" — {source['section']}"
        st.markdown(f"**{heading}**  \n`{scores}`")
        st.write(source["content"])


if "collection_id" not in st.session_state:
    st.session_state.collection_id = f"session-{uuid.uuid4().hex}"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "index_ready" not in st.session_state:
    st.session_state.index_ready = False
if "ingestion" not in st.session_state:
    st.session_state.ingestion = None

st.title("🔬 Scientific Paper RAG")
st.caption(
    "Ask cited questions across scientific PDFs containing text, tables, "
    "figures, and LaTeX formulas."
)

with st.sidebar:
    st.header("Retrieval settings")
    use_reranker = st.toggle(
        "Cross-encoder reranking",
        value=True,
        help="Reranks the top vector-search candidates before answer generation.",
    )
    top_k = st.slider("Context chunks", min_value=1, max_value=10, value=5)
    candidate_k = st.slider(
        "Vector candidates",
        min_value=top_k,
        max_value=50,
        value=max(20, top_k),
    )
    st.caption(f"Collection: `{st.session_state.collection_id[:24]}…`")

    if st.button("Reset documents and chat", use_container_width=True):
        try:
            requests.delete(
                f"{BACKEND_URL}/collections/{st.session_state.collection_id}",
                timeout=30,
            )
        except requests.RequestException:
            pass
        st.session_state.collection_id = f"session-{uuid.uuid4().hex}"
        st.session_state.messages = []
        st.session_state.index_ready = False
        st.session_state.ingestion = None
        st.rerun()

uploaded_files = st.file_uploader(
    "Upload one or more scientific PDFs",
    type="pdf",
    accept_multiple_files=True,
    help=f"Each file can be up to {MAX_FILE_MB} MB.",
)

if uploaded_files:
    oversized = [
        file.name
        for file in uploaded_files
        if len(file.getvalue()) > MAX_FILE_MB * 1024 * 1024
    ]
    if oversized:
        st.error(
            f"These files exceed {MAX_FILE_MB} MB: " + ", ".join(oversized)
        )
    elif st.button("Process papers", type="primary"):
        payload = [
            ("files", (file.name, file.getvalue(), "application/pdf"))
            for file in uploaded_files
        ]
        with st.spinner(
            "Extracting text, tables, formulas, and figures, then building the index…"
        ):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/documents",
                    files=payload,
                    data={"collection_id": st.session_state.collection_id},
                    timeout=REQUEST_TIMEOUT,
                )
                if response.ok:
                    st.session_state.ingestion = response.json()
                    st.session_state.index_ready = True
                    st.session_state.messages = []
                    st.success(response.json()["message"])
                else:
                    st.session_state.index_ready = False
                    st.error(api_error(response))
            except requests.RequestException as exc:
                st.session_state.index_ready = False
                st.error(f"Could not reach the backend: {exc}")

if st.session_state.ingestion:
    ingestion = st.session_state.ingestion
    with st.expander("Indexed-paper summary", expanded=False):
        col1, col2, col3 = st.columns(3)
        col1.metric("Papers", len(ingestion["files"]))
        col2.metric("Chunks", ingestion["total_chunks"])
        col3.metric("Processing time", f"{ingestion['timings']['total_seconds']:.1f}s")
        for file in ingestion["files"]:
            st.write(
                f"**{file['name']}** — {file['chunks']} chunks, "
                f"{file['processing_seconds']:.1f}s"
            )

if st.session_state.index_ready:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("metadata"):
                metadata = message["metadata"]
                st.caption(
                    f"Total {metadata['timings']['total_seconds']:.2f}s · "
                    f"{len(metadata['sources'])} cited chunks · "
                    f"reranker {'on' if metadata['reranker_used'] else 'off'}"
                )
                with st.expander("Sources"):
                    render_sources(metadata["sources"])

    if prompt := st.chat_input("Ask a question about the uploaded papers"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving evidence and generating a cited answer…"):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/query",
                        json={
                            "question": prompt,
                            "collection_id": st.session_state.collection_id,
                            "top_k": top_k,
                            "candidate_k": candidate_k,
                            "use_reranker": use_reranker,
                            "generate_answer": True,
                        },
                        timeout=REQUEST_TIMEOUT,
                    )
                    if response.ok:
                        result = response.json()
                        st.markdown(result["answer"])
                        st.caption(
                            f"Total {result['timings']['total_seconds']:.2f}s · "
                            f"{len(result['sources'])} cited chunks"
                        )
                        with st.expander("Sources"):
                            render_sources(result["sources"])
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": result["answer"],
                                "metadata": result,
                            }
                        )
                    else:
                        st.error(api_error(response))
                except requests.RequestException as exc:
                    st.error(f"Query failed: {exc}")
else:
    st.info("Upload and process at least one PDF to begin.")
