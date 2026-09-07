# RAG Document Assistant

Ask questions about your documents and get AI-powered answers with source citations.

## What It Does

1. Upload a text document
2. Document is chunked, embedded with Gemini, and stored in Qdrant
3. Ask a question about the document
4. Get an answer grounded in the document content with citations

## Tech Stack

- **Backend:** FastAPI, Python
- **LLM:** Google Gemini API (generation + embeddings)
- **Vector Database:** Qdrant
- **Frontend:** React
- **Containerization:** Docker, Docker Compose

## How It Works

```
User Question
    |
    v
Gemini Embedding (convert text to vector)
    |
    v
Qdrant Search (find relevant document chunks)
    |
    v
Gemini Generation (answer using retrieved context)
    |
    v
Response with answer + source citations
```

## Features

- Document upload and indexing
- Semantic search using vector embeddings
- RAG-based question answering
- Source citations with text snippets
- Markdown rendering of AI responses
- Document list with delete functionality
- Structured JSON responses with validation
- Health check endpoint
- Docker Compose deployment

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker Desktop
- Google Gemini API key

### Local Development

1. Clone the repo:

```bash
git clone https://github.com/abdullahniazi56/rag-document-assistant.git
cd rag-document-assistant
```

2. Create `.env`:

```
GEMINI_API_KEY=your_key_here
```

3. Start with Docker:

```bash
docker compose up --build
```

4. Open:

- Swagger: http://localhost:8000/docs
- Qdrant: http://localhost:6333/dashboard

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /generate | Chat with Gemini |
| POST | /embed | Create text embeddings |
| POST | /search | Semantic search in Qdrant |
| POST | /documents | Upload and index document |
| GET | /documents | List uploaded documents |
| DELETE | /documents/{filename} | Delete a document |
| POST | /ask | RAG question answering |

## Tests

```bash
python -m pytest test_main.py -v
```
