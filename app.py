"""
RAG Chatbot API for University of the Cumberlands
FastAPI backend with ChromaDB retrieval + Bedrock Claude generation.
"""

import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import json
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

import boto3
import chromadb
from sentence_transformers import SentenceTransformer

load_dotenv()

CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "ucumberlands"
EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"
EMBEDDING_DIMENSIONS = 768
LLM_MODEL = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
TOP_K = 15
RELEVANCE_THRESHOLD = 0.3

app = FastAPI(title="UC Cumberlands RAG Chatbot")

app.mount("/static", StaticFiles(directory="static"), name="static")

bedrock_client = None
chroma_collection = None
embedding_model = None


def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return embedding_model


def get_bedrock():
    global bedrock_client
    if bedrock_client is None:
        bedrock_client = boto3.client(
            "bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )
    return bedrock_client


def get_collection():
    global chroma_collection
    if chroma_collection is None:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        chroma_collection = client.get_collection(name=COLLECTION_NAME)
    return chroma_collection


def get_query_embedding(query: str):
    model = get_embedding_model()
    embedding = model.encode([query], normalize_embeddings=True)[0]
    return embedding.tolist()


def retrieve_context(query: str):
    collection = get_collection()
    query_embedding = get_query_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            similarity = 1 - distance
            chunks.append({"text": doc, "metadata": meta, "similarity": similarity})

    return chunks


def build_context_block(chunks):
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        source = f"[Source {i}: {meta.get('title', 'Unknown')} | {meta.get('section', '')} | {meta.get('url', '')}]"
        parts.append(f"{source}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


class ChatRequest(BaseModel):
    message: str
    history: list = []


class ChatResponse(BaseModel):
    response: str
    sources: list


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path("static/index.html")
    return HTMLResponse(content=html_path.read_text())


def expand_query(query: str, history: list) -> str:
    """Expand short/ambiguous queries by prepending the topic from recent chat."""
    if not history:
        return query

    query_lower = query.lower().strip().rstrip("?.,!")
    is_short = len(query.split()) <= 6

    # Check if query references something from context
    pronouns = {"this", "that", "it", "them", "the program", "this program",
                "here", "there", "those", "these"}
    has_reference = any(p in query_lower for p in pronouns)

    if not (is_short or has_reference):
        return query

    # Find the most recent user question that has substance (the topic)
    topic = ""
    for msg in reversed(history[-6:]):
        content = msg.get("content", "").strip()
        if msg.get("role") == "user" and len(content.split()) > 3:
            topic = content
            break

    if not topic:
        # Fallback: extract topic from assistant's first response line
        for msg in reversed(history[-6:]):
            if msg.get("role") == "assistant":
                first_line = msg["content"].split("\n")[0].strip()
                if len(first_line) > 10:
                    topic = first_line[:80]
                    break

    if topic:
        return f"{topic} — {query}"
    return query


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    query = request.message.strip()
    if not query:
        return ChatResponse(response="Please ask a question.", sources=[])

    # Expand short queries using conversation context
    search_query = expand_query(query, request.history)
    chunks = retrieve_context(search_query)

    if not chunks or chunks[0]["similarity"] < RELEVANCE_THRESHOLD:
        return ChatResponse(
            response="I don't have enough information from the University of the Cumberlands website to answer this question. Please contact the relevant department or visit ucumberlands.edu for more details.",
            sources=[],
        )

    context_block = build_context_block(chunks[:10])

    system_prompt = """You are a professional virtual assistant for the University of the Cumberlands. You answer questions from students, prospective students, parents, and staff based ONLY on the provided context from the university website.

RULES:
1. Only answer based on the provided context. Do not use external knowledge.
2. Keep responses SHORT — 2-4 brief paragraphs, 2-3 sentences each. Be direct and concise.
3. Use simple, clear sentences. Break information into small, digestible paragraphs.
4. When there are multiple items (requirements, steps, etc.), use a short bullet list with "- " prefix. Keep each bullet to one line.
5. Bold key terms sparingly with **bold**.
6. Always include clickable links using markdown format: [visible text](full URL). Use the actual URLs from the source context.
7. If context lacks information, say so briefly and provide a link or contact info.
8. No emojis. No markdown headings (## or ###). No tables.
9. For follow-up questions, use the conversation history to understand context.
10. NEVER use phrases like "Based on the available context", "The provided context doesn't include", "Based on the provided information", "According to the context", "The context doesn't contain", or any reference to "context" or "provided information". You are a university representative — answer directly. If information isn't available, simply say "I don't have that detail" or "That information isn't available here" and point them to the right page or contact."""

    messages = []
    for msg in request.history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_message = f"""Based on the following context from the University of the Cumberlands website, answer the user's question.

CONTEXT:
{context_block}

USER QUESTION: {query}

Keep your answer short (2-4 brief paragraphs). Include clickable [links](URL) to relevant pages. Use bullet points only for lists of requirements or steps."""

    messages.append({"role": "user", "content": user_message})

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "system": system_prompt,
        "messages": messages,
    })

    bedrock = get_bedrock()
    response = bedrock.invoke_model(modelId=LLM_MODEL, body=body)
    result = json.loads(response["body"].read())
    answer = result["content"][0]["text"]

    sources = [
        {
            "title": c["metadata"].get("title", ""),
            "section": c["metadata"].get("section", ""),
            "url": c["metadata"].get("url", ""),
            "category": c["metadata"].get("category", ""),
            "similarity": round(c["similarity"], 3),
        }
        for c in chunks[:10]
    ]

    return ChatResponse(response=answer, sources=sources)


@app.get("/api/health")
async def health():
    try:
        col = get_collection()
        count = col.count()
        return {"status": "ok", "chunks": count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
