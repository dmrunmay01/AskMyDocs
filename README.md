# ⚡ AskMyDocs — RAG-Powered Document Q&A

> Ask questions about your documents using a local LLM, retrieve relevant context with Chroma, and receive grounded answers with source citations.

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.2-orange.svg)](https://langchain.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

---

## 📸 Demo

AskMyDocs provides a browser-based interface for uploading documents, indexing their content, and asking natural-language questions against the indexed knowledge base.

### Interface

- Upload documents through the web interface
- Index uploaded documents into a searchable vector store
- Ask natural-language questions
- Filter queries by document
- View retrieved source information
- Continue multi-turn conversations
- Monitor application services through Prometheus and Grafana

> **Try it locally:** start the Docker stack and open `http://localhost:3000`.

---

## 🏗 Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                   Frontend (Nginx)                      │
│            Upload + Document Q&A Chat UI                │
└──────────────────────┬──────────────────────────────────┘
                       │ REST / SSE
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Application                    │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │  Documents  │  │    Query     │  │    Sessions    │ │
│  │   Router    │  │    Router    │  │    Router      │ │
│  └──────┬──────┘  └──────┬───────┘  └────────────────┘ │
│         │                │                              │
│  ┌──────▼──────┐  ┌──────▼──────────────────────────┐ │
│  │  Document   │  │          RAG Pipeline            │ │
│  │  Processor  │  │ Retrieve → MMR → Generate        │ │
│  │  (chunking) │  └──────┬──────────────┬────────────┘ │
│  └──────┬──────┘         │              │              │
│         │         ┌──────▼──────┐  ┌───▼───────────┐ │
│  ┌──────▼──────┐  │    Chroma    │  │  LLM Service  │ │
│  │ HuggingFace │  │ Vector Store│  │    Ollama     │ │
│  │  Embeddings │  │   + MMR     │  │ / HF fallback │ │
│  └─────────────┘  └─────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. File upload → `DocumentProcessor` parses and splits the document into chunks.
2. Chunks are embedded using `sentence-transformers/all-MiniLM-L6-v2`.
3. Embeddings and metadata are stored in a Chroma index.
4. A user query is embedded and relevant chunks are retrieved using similarity search, with optional MMR diversity.
5. Retrieved context and conversation history are passed to the local Ollama LLM.
6. The generated answer and retrieved source information are returned to the frontend.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Document Formats** | PDF, DOCX, TXT, Markdown, CSV, HTML |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector Store** | Chroma |
| **Retrieval** | Similarity search with optional MMR diversity |
| **LLM** | Ollama local models with configurable model name |
| **Chunking** | Recursive character splitting |
| **Sessions** | In-memory conversation history with TTL cleanup |
| **Source Citations** | Retrieved document chunks are shown with answers |
| **Document Filtering** | Query all indexed documents or selected documents |
| **Monitoring** | Prometheus metrics + Grafana dashboards |
| **API Docs** | Interactive Swagger UI at `/docs` |
| **Deployment** | Docker Compose |

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop with Docker Compose
- Sufficient disk space for the application and local LLM model
- NVIDIA GPU support is optional
- CPU execution can also be used depending on the Ollama configuration

### Start the Application

```bash
docker compose up -d --build
```

Then open:

```text
http://localhost:3000
```

### Services

| Service | Local URL |
|---|---|
| AskMyDocs frontend | `http://localhost:3000` |
| FastAPI | `http://localhost:8000` |
| Swagger API docs | `http://localhost:8000/docs` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3001` |
| Ollama | `http://localhost:11434` |

Docker Compose uses persistent volumes for uploaded documents, vector data, model data, and monitoring data.

---

## 🛠 Local Development

### Prerequisites

- Python 3.11+
- Ollama installed locally

### Setup

```bash
# Clone the repository
git clone https://github.com/dmrunmay01/AskMyDocs.git
cd AskMyDocs

# Create a virtual environment
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Copy `.env.example` to `.env` and configure the required environment variables.

### Pull the LLM Model

```bash
ollama pull mistral
```

### Start the API

```bash
uvicorn app.main:app --reload --port 8000
```

### Serve the Frontend

```bash
python -m http.server 3000 --directory frontend
```

Then open:

```text
http://localhost:3000
```

The LLM is configurable through `OLLAMA_MODEL`.

---

## 📡 API Reference

### Upload Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@yourfile.pdf"
```

### Ask a Question

```bash
curl -X POST http://localhost:8000/api/v1/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main topics covered?",
    "top_k": 5,
    "use_mmr": true,
    "include_sources": true
  }'
```

### Example Response

```json
{
  "answer": "The document covers ...",
  "session_id": "abc-123",
  "sources": [
    {
      "content": "...",
      "score": 0.87,
      "filename": "report.pdf",
      "page_number": 3
    }
  ],
  "model_used": "mistral",
  "processing_time_ms": 1423.5
}
```

### Multi-turn Conversation

First turn:

```bash
curl -X POST http://localhost:8000/api/v1/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize the document"}'
```

Follow-up using the returned `session_id`:

```bash
curl -X POST http://localhost:8000/api/v1/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me more about the second point",
    "session_id": "abc-123"
  }'
```

### Semantic Search

```bash
curl -X POST http://localhost:8000/api/v1/query/search \
  -H "Content-Type: application/json" \
  -d '{"query": "neural networks", "top_k": 5}'
```

### Filter by Document

```bash
curl -X POST http://localhost:8000/api/v1/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What does this say about risks?",
    "doc_ids": ["your-doc-id-here"]
  }'
```

### Interactive API Documentation

```text
http://localhost:8000/docs
```

---

## ⚙️ Configuration

Key environment variables:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `mistral` | Local LLM model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer embedding model |
| `CHUNK_SIZE` | `512` | Characters per chunk |
| `CHUNK_OVERLAP` | `64` | Chunk overlap |
| `TOP_K_RESULTS` | `5` | Number of retrieved chunks |
| `SIMILARITY_THRESHOLD` | `0.3` | Minimum relevance threshold |
| `MMR_LAMBDA` | `0.5` | MMR diversity/relevance parameter |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum upload size |

### LLM Model Configuration

Set the model in `.env`:

```bash
OLLAMA_MODEL=phi3
```

or:

```bash
OLLAMA_MODEL=mistral
```

Make sure the selected model is available in Ollama.

For example:

```bash
docker compose exec ollama ollama pull phi3
```

Then restart the API:

```bash
docker compose restart api
```

---

## 🧪 Testing

Run the automated test suite:

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ -v --cov=app --cov-report=html
```

The test suite covers areas including:

- Health and root endpoints
- Document upload validation
- Document CRUD and index statistics
- Session lifecycle
- Document processing
- Schema validation
- Configuration
- Custom exceptions

### Manual RAG Validation

The application can be validated using dedicated documents and question sets.

Functional validation includes:

- Retrieving information from uploaded documents
- Selecting a specific document before querying
- Returning source citations
- Testing out-of-context questions
- Verifying grounded responses
- End-to-end document question answering

---

## 📈 Evaluation

AskMyDocs can be evaluated across retrieval quality, response grounding, and system performance.

### Functional Evaluation

- Document retrieval
- Document-specific filtering
- Source attribution
- Out-of-context question handling
- End-to-end RAG generation

### Performance Metrics

The following metrics can be measured for system benchmarking:

- Retrieval latency
- LLM generation latency
- End-to-end query latency
- Retrieval precision and recall
- Answer faithfulness
- Embedding throughput
- Index build time
- Indexing time

Performance measurements depend on the hardware, LLM model, document corpus, question set, and configuration used during evaluation.

---

## 📊 Monitoring

| Service | URL |
|---|---|
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3001` |

The monitoring stack provides access to application and retrieval-related metrics exposed by the project.

---

## 🐳 Docker Commands

### Start Everything

```bash
docker compose up -d
```

### View API Logs

```bash
docker compose logs -f api
```

### View Ollama Logs

```bash
docker compose logs -f ollama
```

### Stop the Stack

```bash
docker compose down
```

### Full Reset

```bash
docker compose down -v
```

> `docker compose down -v` removes persistent volumes and should only be used when a full data reset is intended.

### Rebuild the API

```bash
docker compose build api
docker compose up -d api
```

### Rebuild the Frontend

```bash
docker compose build frontend
docker compose up -d frontend
```

---

## 🗂 Project Structure

```text
AskMyDocs/
│
├── app/
│   ├── main.py                    # FastAPI application
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── documents.py       # Document endpoints
│   │       ├── query.py           # Q&A and search endpoints
│   │       ├── sessions.py        # Session management
│   │       └── health.py          # Health check
│   │
│   ├── core/
│   │   ├── config.py              # Application settings
│   │   ├── exceptions.py          # Custom exceptions
│   │   └── logging.py             # Application logging
│   │
│   ├── models/
│   │   └── schemas.py             # Request/response models
│   │
│   ├── services/
│   │   ├── document_processor.py  # Document parsing + chunking
│   │   ├── vector_store.py        # Chroma operations + MMR
│   │   ├── llm_service.py         # Ollama / HuggingFace LLM
│   │   ├── rag_pipeline.py        # RAG orchestration
│   │   └── session_service.py     # Conversation history + TTL
│   │
│   └── utils/
│
├── frontend/
│   ├── index.html                 # Web interface
│   ├── Dockerfile                 # Nginx container
│   └── nginx.conf                 # Nginx configuration
│
├── tests/
│   ├── __init__.py
│   └── test_api.py                # API and integration tests
│
├── monitoring/
│   └── prometheus.yml             # Prometheus configuration
│
├── scripts/
│   ├── setup.sh                   # Setup helper
│   └── push_to_github.sh          # GitHub helper
│
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions workflow
│
├── EVALUATION.md                  # Evaluation methodology
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## 🔧 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript, Nginx |
| Backend | FastAPI, Python |
| RAG Framework | LangChain |
| Embeddings | Hugging Face Sentence Transformers |
| Vector Search | Chroma |
| LLM Runtime | Ollama |
| Model Support | Local Ollama models / Hugging Face fallback |
| Containerization | Docker, Docker Compose |
| Monitoring | Prometheus, Grafana |
| Testing | Pytest |
| API Documentation | Swagger / OpenAPI |

---

**Built with:** FastAPI · LangChain · Chroma · HuggingFace · Ollama · Docker · Prometheus · Grafana
