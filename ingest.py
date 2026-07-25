"""
Ingestion Pipeline: Markdown Files → Chunked Sections → Local Embeddings → ChromaDB
Uses sentence-transformers for fast local embedding generation.
"""

import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import re
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

import chromadb
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MARKDOWN_DIR = Path("markdown_data")
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "ucumberlands"
EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"
EMBEDDING_DIMENSIONS = 768
MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 50
BATCH_SIZE = 128


def parse_markdown_file(md_path):
    """Parse a markdown file into metadata + content."""
    text = md_path.read_text(encoding="utf-8")

    metadata = {}
    content = text

    # Parse YAML front matter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            front_matter = parts[1].strip()
            content = parts[2].strip()
            for line in front_matter.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().strip('"')
                    metadata[key.strip()] = val

    return metadata, content


def chunk_markdown(metadata, content):
    """Split markdown content into chunks by headings."""
    chunks = []
    url = metadata.get("url", "")
    title = metadata.get("title", "")
    category = metadata.get("category", "unknown")
    path_hierarchy = metadata.get("path", category)

    base_metadata = {
        "url": url,
        "title": title,
        "category": category,
        "path_hierarchy": path_hierarchy,
    }

    if not content.strip():
        return chunks

    # Split by markdown headings (## or ###)
    sections = split_by_md_headings(content)

    for section_heading, section_text in sections:
        section_text = section_text.strip()
        if len(section_text) < MIN_CHUNK_CHARS:
            continue

        sub_chunks = split_into_chunks(section_text, MAX_CHUNK_CHARS)

        for i, chunk_text in enumerate(sub_chunks):
            if len(chunk_text) < MIN_CHUNK_CHARS:
                continue

            chunk_metadata = {
                **base_metadata,
                "section": section_heading or title,
                "chunk_index": i,
            }

            # Context prefix for better retrieval
            context_prefix = f"# {title}"
            if section_heading and section_heading != title:
                context_prefix += f"\n## {section_heading}"
            enriched_text = f"{context_prefix}\n\n{chunk_text}"

            chunks.append({"text": enriched_text, "metadata": chunk_metadata})

    # Fallback: use meta description if no chunks
    if not chunks and metadata.get("description"):
        chunk_metadata = {**base_metadata, "section": title, "chunk_index": 0}
        chunks.append({"text": f"# {title}\n\n{metadata['description']}", "metadata": chunk_metadata})

    return chunks


def split_by_md_headings(content):
    """Split markdown content into (heading, text) pairs at ## boundaries."""
    sections = []
    lines = content.split("\n")

    current_heading = ""
    current_lines = []

    for line in lines:
        stripped = line.strip()
        # Match ## or ### headings
        match = re.match(r'^(#{1,4})\s+(.+)$', stripped)
        if match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines)))

    return sections if sections else [("", content)]


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
    """Main ingestion pipeline with local embeddings."""
    logger.info("Starting ingestion pipeline...")
    logger.info(f"Embedding model: {EMBEDDING_MODEL_NAME}")

    # Load embedding model
    logger.info("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info(f"Model loaded (dimensions: {EMBEDDING_DIMENSIONS})")

    # Connect to ChromaDB
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
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

    # Load all markdown files
    md_files = list(MARKDOWN_DIR.rglob("*.md"))
    logger.info(f"Found {len(md_files)} markdown files")

    # Chunk all pages
    all_chunks = []
    for f in tqdm(md_files, desc="Chunking pages"):
        metadata, content = parse_markdown_file(f)
        chunks = chunk_markdown(metadata, content)
        all_chunks.extend(chunks)

    logger.info(f"Total chunks created: {len(all_chunks)}")

    # Embed and store in batches
    total_ingested = 0
    all_texts = [c["text"] for c in all_chunks]

    logger.info(f"Generating embeddings in batches of {BATCH_SIZE}...")
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Embedding & storing"):
        batch = all_chunks[i: i + BATCH_SIZE]
        batch_texts = all_texts[i: i + BATCH_SIZE]
        metadatas = [c["metadata"] for c in batch]
        ids = [f"chunk_{i + j}" for j in range(len(batch))]

        try:
            embeddings = model.encode(batch_texts, normalize_embeddings=True).tolist()
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=metadatas,
            )
            total_ingested += len(batch)
        except Exception as e:
            logger.error(f"Batch {i // BATCH_SIZE} failed: {e}")

    logger.info(f"Ingestion complete: {total_ingested}/{len(all_chunks)} chunks stored")
    logger.info(f"Collection '{COLLECTION_NAME}' has {collection.count()} documents")

    # Save summary
    import json
    summary = {
        "total_pages": len(md_files),
        "total_chunks": len(all_chunks),
        "chunks_ingested": total_ingested,
        "collection_name": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "max_chunk_chars": MAX_CHUNK_CHARS,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open("scraped_data/ingestion_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    ingest()
