"""
Ingestion Pipeline: Scraped Data → Chunked Sections → Bedrock Embeddings → ChromaDB
Preserves page hierarchy and URLs for reference citations.
"""

import os
import json
import re
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

import boto3
import chromadb
from tqdm import tqdm

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRAPED_DIR = Path("scraped_data/pages")
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "ucumberlands"
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024
MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 50
BATCH_SIZE = 20


def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))


def get_embedding(client, text):
    response = client.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps({"inputText": text[:10000], "dimensions": EMBEDDING_DIMENSIONS}),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def get_embeddings_batch(client, texts):
    embeddings = []
    for text in texts:
        embeddings.append(get_embedding(client, text))
    return embeddings


def chunk_page(data):
    """Split a page into meaningful sections based on headings and content structure."""
    chunks = []
    url = data["url"]
    title = data.get("title", "")
    category = data.get("category", "unknown")
    path_hierarchy = data.get("path_hierarchy", [])
    meta_description = data.get("meta_description", "")

    base_metadata = {
        "url": url,
        "title": title,
        "category": category,
        "path_hierarchy": " > ".join(path_hierarchy) if path_hierarchy else category,
    }

    full_text = data.get("full_text", "")
    if not full_text.strip():
        return chunks

    headings = data.get("headings", [])
    heading_texts = [h["text"] for h in headings]

    # Strategy: split full_text by headings to create sections
    sections = split_by_headings(full_text, heading_texts)

    for section_heading, section_text in sections:
        section_text = section_text.strip()
        if len(section_text) < MIN_CHUNK_CHARS:
            continue

        # Further split large sections into smaller chunks
        sub_chunks = split_into_chunks(section_text, MAX_CHUNK_CHARS)

        for i, chunk_text in enumerate(sub_chunks):
            if len(chunk_text) < MIN_CHUNK_CHARS:
                continue

            chunk_metadata = {
                **base_metadata,
                "section": section_heading or title,
                "chunk_index": i,
            }

            # Prepend context to the chunk for better retrieval
            context_prefix = f"{title}"
            if section_heading and section_heading != title:
                context_prefix += f" - {section_heading}"
            enriched_text = f"{context_prefix}\n\n{chunk_text}"

            chunks.append({"text": enriched_text, "metadata": chunk_metadata})

    # If no sections were created, use meta description + full text chunks
    if not chunks and meta_description:
        chunk_metadata = {**base_metadata, "section": title, "chunk_index": 0}
        chunks.append({"text": f"{title}\n\n{meta_description}", "metadata": chunk_metadata})

    return chunks


def split_by_headings(full_text, heading_texts):
    """Split full_text into (heading, content) pairs using heading markers."""
    if not heading_texts:
        return [("", full_text)]

    # Build regex pattern to split on headings
    # Escape heading texts for regex and find them in the full text
    sections = []
    lines = full_text.split("\n")

    current_heading = ""
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped in heading_texts:
            # Save previous section
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = stripped
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines)))

    return sections if sections else [("", full_text)]


def split_into_chunks(text, max_chars):
    """Split text into chunks respecting sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += (" " if current_chunk else "") + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Handle sentences longer than max_chars
            if len(sentence) > max_chars:
                words = sentence.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= max_chars:
                        current_chunk += (" " if current_chunk else "") + word
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def ingest():
    """Main ingestion pipeline."""
    logger.info("Starting ingestion pipeline...")

    # Connect to ChromaDB
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    # Delete existing collection if re-running
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
        logger.info(f"Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(f"Created collection '{COLLECTION_NAME}'")

    # Initialize Bedrock client
    bedrock = get_bedrock_client()

    # Load all scraped pages
    json_files = list(SCRAPED_DIR.rglob("*.json"))
    logger.info(f"Found {len(json_files)} scraped pages")

    # Chunk all pages
    all_chunks = []
    for f in tqdm(json_files, desc="Chunking pages"):
        with open(f) as fh:
            data = json.load(fh)
        chunks = chunk_page(data)
        all_chunks.extend(chunks)

    logger.info(f"Total chunks created: {len(all_chunks)}")

    # Ingest in batches
    total_ingested = 0
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Embedding & storing"):
        batch = all_chunks[i : i + BATCH_SIZE]

        texts = [c["text"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        ids = [f"chunk_{i + j}" for j in range(len(batch))]

        try:
            embeddings = get_embeddings_batch(bedrock, texts)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            total_ingested += len(batch)
        except Exception as e:
            logger.error(f"Batch {i//BATCH_SIZE} failed: {e}")
            # Retry individually
            for j, (text, meta, doc_id) in enumerate(zip(texts, metadatas, ids)):
                try:
                    emb = get_embedding(bedrock, text)
                    collection.add(ids=[doc_id], embeddings=[emb], documents=[text], metadatas=[meta])
                    total_ingested += 1
                except Exception as e2:
                    logger.error(f"  Chunk {doc_id} failed: {e2}")

    logger.info(f"Ingestion complete: {total_ingested}/{len(all_chunks)} chunks stored")
    logger.info(f"Collection '{COLLECTION_NAME}' has {collection.count()} documents")

    # Save ingestion summary
    summary = {
        "total_pages": len(json_files),
        "total_chunks": len(all_chunks),
        "chunks_ingested": total_ingested,
        "collection_name": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "max_chunk_chars": MAX_CHUNK_CHARS,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open("scraped_data/ingestion_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    ingest()
