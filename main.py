import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel
from fastapi import File, UploadFile 
from uuid import uuid4
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client.models import Filter, FieldCondition, MatchValue
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

# 1. Load Environment Variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

# 2. Client & App Setup
client = genai.Client(api_key=api_key)

qdrant = QdrantClient(url="http://localhost:6333")

COLLECTION_NAME = "documents"
VECTOR_SIZE = 3072
 
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Pydantic Models
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GenerateRequest(BaseModel):
    messages: list[Message]


class GenerateResponse(BaseModel):
    answer: str
    confidence: str
    follow_up_question: str




# 4. Generate Endpoint (Chat + Structured JSON)
@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    if not request.messages:
            raise HTTPException(
                status_code=422,
                detail="Messages list cannot be empty.",
            )
    try:
        conversation = "\n".join(
            f"{message.role}: {message.content}" for message in request.messages
        )
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=conversation,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are a concise learning assistant. "
                    "Answer clearly and accurately."
                ),
                response_mime_type="application/json",
                response_schema=GenerateResponse,
            ),
        )
        return response.parsed

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini generation request failed: {error}",
        ) from error


# 5. Embed Endpoint (Vector Embeddings)
class EmbedRequest(BaseModel):
    text: str


@app.post("/embed")
def embed(request: EmbedRequest):
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=request.text,
    )

    vector = response.embeddings[0].values

    return {
        "dimensions": len(vector),
        "first_five_numbers": vector[:5],
    }

def create_collection_if_needed():
    if not qdrant.collection_exists(COLLECTION_NAME):
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
def search(request: SearchRequest):
    create_collection_if_needed()

    embedding_response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=request.query,
    )

    query_vector = embedding_response.embeddings[0].values

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=3,
    ).points

    return [
        {
            "score": result.score,
            "text": result.payload["text"],
            "filename": result.payload["filename"],
            "chunk_number": result.payload["chunk_number"],
        }
        for result in results
    ]    

class AskRequest(BaseModel):
    question: str

def chunk_text(
    text: str,
    chunk_size: int = 1_000,
    overlap: int = 200,
) -> list[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space

        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks

@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Only .txt files are allowed for now.",
        )

    content = (await file.read()).decode("utf-8").strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    chunks = chunk_text(content, chunk_size=300)
    create_collection_if_needed()

    points = []

    for chunk_number, chunk in enumerate(chunks):
        embedding_response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=chunk,
        )

        vector = embedding_response.embeddings[0].values

        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "text": chunk,
                    "filename": file.filename,
                    "chunk_number": chunk_number,
                },
            )
        )

    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    return {
        "filename": file.filename,
        "characters": len(content),
        "chunk_count": len(chunks),
        "stored_chunks": len(points),
    }

@app.post("/ask")
def ask(request: AskRequest):
    try:
        embedding_response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=request.question,
        )

        query_vector = embedding_response.embeddings[0].values

        results = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=3,
        ).points

        if not results:
            raise HTTPException(
                status_code=404,
                detail="No document chunks found.",
            )

        context = "\n\n".join(
            result.payload["text"]
            for result in results
        )

        prompt = f"""
Use only the document context below to answer the question.

If the answer is not in the context, say:
"I could not find that information in the uploaded documents."

Document context:
{context}

Question:
{request.question}
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )

        return {
            "answer": response.text,
            "sources": [
                {
                    "filename": result.payload["filename"],
                    "chunk_number": result.payload["chunk_number"],
                }
                for result in results
            ],
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"RAG request failed: {error}",
        ) from error

@app.get("/health")
def health():
    return{"status": "ok","service": "ai-doc-assistant"}

@app.get("/documents")
def list_documents():
    points, _ = qdrant.scroll(
        collection_name= COLLECTION_NAME,
        limit = 1000,
        with_payload=True,
        with_vectors=False,
    )

    summary = {}
    for point in points:
        name = point.payload["filename"]
        summary[name] = summary.get(name, 0) + 1

    return[
            {"filename": name, "chunk_count": count}
            for name, count in summary.items()
        ]

@app.delete("/documents/{filename}")
def delete_document(filename: str):
    qdrant.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="filename",
                    match=MatchValue(value=filename),
                )
            ]
        ),
    )
    return {"deleted": filename, "status": "ok"}

frontend_path = pathlib.Path(__file__).parent / "frontend" / "dist"

if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if not frontend_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not built")
    file_path = frontend_path / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(frontend_path / "index.html")