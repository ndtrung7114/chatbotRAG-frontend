# Scientific Paper RAG UI

Streamlit interface for the Scientific Paper RAG API.

It supports multi-PDF collections, configurable cross-encoder reranking,
source-level citations, retrieval scores, and end-to-end latency reporting.

```bash
pip install -r requirements.txt
streamlit run main.py
```

Set `BACKEND_URL` when the FastAPI service is not running at
`http://localhost:8000`.
