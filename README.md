# UC Cumberlands RAG Chatbot

Enterprise-level RAG (Retrieval-Augmented Generation) chatbot for the University of the Cumberlands. Built to answer questions from current students, prospective students, and anyone using the university website.

## Architecture

```
ucumberlands.edu ─→ Scraper ─→ Chunker ─→ Bedrock Embeddings ─→ ChromaDB ─→ Chatbot (Bedrock Claude)
```

## Components

| Component | Description |
|-----------|-------------|
| `scraper.py` | Sitemap-based web scraper (2,063 pages) |
| `ingest.py` | Chunking + embedding pipeline into ChromaDB |
| `chatbot.py` | RAG chatbot using AWS Bedrock (coming soon) |

## Tech Stack

- **LLM**: AWS Bedrock (Claude Sonnet)
- **Embeddings**: Amazon Titan Embed Text v2 (1024 dimensions)
- **Vector Store**: ChromaDB (persistent, local)
- **Scraping**: BeautifulSoup + requests
- **Language**: Python 3.11

## Setup

```bash
# 1. Clone and install dependencies
git clone git@github.com:rmakala38838/uc-rag-chatbot.git
cd uc-rag-chatbot
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your AWS credentials

# 3. Scrape the website
python scraper.py

# 4. Start ChromaDB and run ingestion
chroma run --path ./chroma_data --port 8000 &
python ingest.py

# 5. Run the chatbot (coming soon)
python chatbot.py
```

## Data Pipeline

1. **Scrape**: Fetches all 2,063 pages from ucumberlands.edu sitemap
2. **Chunk**: Splits pages into sections by headings (300-1500 chars each)
3. **Embed**: Generates 1024-dim vectors via Bedrock Titan
4. **Store**: Persists in ChromaDB with hierarchical metadata (category > path > title > section + URL)
5. **Query**: Semantic search + LLM synthesis with source citations

## Metadata Schema

Each chunk in the vector store carries:
```json
{
  "url": "https://www.ucumberlands.edu/academics/certificate/...",
  "title": "Page Title",
  "category": "academics",
  "path_hierarchy": "academics > certificate > artificial-intelligence-certificate",
  "section": "Course Requirements"
}
```

This enables filtered retrieval and source citations in chatbot responses.
