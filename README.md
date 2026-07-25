# UC Cumberlands RAG Chatbot

An enterprise-grade **Retrieval-Augmented Generation (RAG)** chatbot built for the University of the Cumberlands. It scrapes the entire university website, processes the content into searchable chunks, and provides instant, accurate answers to student questions using AI — all grounded in real university data.

---

## Table of Contents

- [What is RAG?](#what-is-rag)
- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [How Each Component Works](#how-each-component-works)
  - [1. Web Scraper](#1-web-scraper-scraperpy)
  - [2. Markdown Converter](#2-markdown-converter-convert_to_mdpy)
  - [3. Ingestion Pipeline](#3-ingestion-pipeline-ingestpy)
  - [4. RAG Chatbot API](#4-rag-chatbot-api-apppy)
  - [5. Frontend UI](#5-frontend-ui-static)
- [Data Flow: End to End](#data-flow-end-to-end)
- [Configuration](#configuration)
- [Key Design Decisions](#key-design-decisions)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)

---

## What is RAG?

**RAG (Retrieval-Augmented Generation)** is an AI architecture that combines two steps:

1. **Retrieval** — When a user asks a question, the system searches a database of pre-processed documents to find the most relevant passages.
2. **Generation** — Those relevant passages are sent to a large language model (LLM), which uses them as context to generate a factual, grounded answer.

**Why RAG instead of just asking an LLM directly?**

| Problem with plain LLM | How RAG solves it |
|---|---|
| LLMs can hallucinate (make up facts) | RAG only answers from real university data |
| LLMs don't know private/recent information | RAG searches the latest scraped content |
| No source citations | RAG provides links back to the original web pages |
| Generic answers | RAG gives specific UC Cumberlands information |

---

## Project Overview

This chatbot can answer questions like:
- "What are the admission requirements for the MBA program?"
- "How much is tuition for online students?"
- "Who are the faculty in the Computer Science department?"
- "What financial aid options are available?"
- "What clubs and activities are on campus?"

**Key Numbers:**
| Metric | Value |
|--------|-------|
| Pages scraped | 2,092 |
| Total chunks in vector store | 20,520 |
| Embedding dimensions | 768 |
| Average response time | < 3 seconds |
| Ingestion time (full rebuild) | ~4 minutes |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION PIPELINE                              │
│                         (Run once, then periodically)                        │
├─────────────┬──────────────┬────────────────┬─────────────┬────────────────┤
│             │              │                │             │                │
│  Web        │  Markdown    │  Section-Aware │  Local      │  ChromaDB      │
│  Scraper    │  Converter   │  Chunking      │  Embeddings │  Vector Store  │
│             │              │                │             │                │
│  Fetches    │  Cleans &    │  Splits by     │  Converts   │  Stores 20,520 │
│  2,092      │  structures  │  headings      │  text to    │  chunks with   │
│  pages      │  into .md    │  (50-1500      │  768-dim    │  cosine search │
│             │  files       │   chars)       │  vectors    │                │
└─────┬───────┴──────┬───────┴────────┬───────┴──────┬──────┴────────────────┘
      │              │                │              │
      ▼              ▼                ▼              ▼
  scraped_data/   markdown_data/   (in memory)   chroma_data/
  (JSON files)    (.md files)                    (persistent DB)


┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUERY & RESPONSE PIPELINE                            │
│                         (Every time a user asks a question)                  │
├─────────────┬──────────────┬────────────────┬─────────────┬────────────────┤
│             │              │                │             │                │
│  User       │  Query       │  Semantic      │  Context    │  AWS Bedrock   │
│  Question   │  Expansion   │  Search        │  Assembly   │  Claude LLM    │
│             │              │                │             │                │
│  "What MBA  │  Resolves    │  Finds top 15  │  Builds     │  Generates     │
│   programs  │  pronouns &  │  most similar  │  prompt     │  grounded      │
│   exist?"   │  follow-ups  │  chunks        │  with top   │  answer with   │
│             │              │                │  10 chunks  │  citations     │
└─────────────┴──────────────┴────────────────┴─────────────┴────────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Scraping** | BeautifulSoup + requests | Extracts content from ucumberlands.edu |
| **Data Processing** | Custom Python scripts | Converts HTML → JSON → Markdown → Chunks |
| **Embeddings** | sentence-transformers (BAAI/bge-base-en-v1.5) | Converts text to 768-dimensional vectors locally |
| **Vector Database** | ChromaDB | Stores and searches embeddings using cosine similarity (HNSW index) |
| **LLM** | AWS Bedrock Claude Sonnet | Generates natural language answers from retrieved context |
| **Backend API** | FastAPI + Uvicorn | REST API serving the chat endpoint |
| **Frontend** | HTML5 + CSS3 + Vanilla JavaScript | Professional UC-branded chat interface |
| **GPU Acceleration** | Apple Silicon MPS | Speeds up local embedding generation |

---

## Project Structure

```
uc-rag-chatbot/
│
├── scraper.py               # Step 1: Scrapes ucumberlands.edu (2,092 pages)
├── convert_to_md.py         # Step 2: Converts JSON → clean Markdown files
├── ingest.py                # Step 3: Chunks + embeds → stores in ChromaDB
├── app.py                   # Step 4: FastAPI backend (RAG query engine)
├── chatbot.py               # Alternative: Streamlit-based chatbot UI
│
├── static/                  # Frontend assets
│   ├── index.html           # Main page (UC-branded landing + chat widget)
│   ├── styles.css           # Styling (UC colors: crimson, navy, white)
│   └── chat.js              # Chat widget logic (send/receive messages)
│
├── create_presentation.py   # Generates project PowerPoint presentation
├── UC_RAG_Chatbot_Presentation.pptx  # 6-slide project presentation
│
├── requirements.txt         # Python dependencies
├── .env.example             # Template for environment variables
├── .env                     # Your AWS credentials (NOT in git)
├── .gitignore               # Files excluded from version control
│
├── scraped_data/            # (Generated) Raw scraped JSON files
│   └── pages/               # One .json file per scraped page
│
├── markdown_data/           # (Generated) Clean markdown files
│   └── [mirrors scraped_data structure]
│
└── chroma_data/             # (Generated) ChromaDB persistent storage
```

---

## Prerequisites

Before you begin, you need:

1. **Python 3.10 or higher** — [Download Python](https://www.python.org/downloads/)
2. **pip** — Python package manager (comes with Python)
3. **AWS Account** with Bedrock access — For the Claude LLM
   - You need: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - Claude Sonnet model must be enabled in your AWS Bedrock console
4. **8GB+ RAM** — The embedding model uses ~1.5GB of memory
5. **10GB disk space** — For scraped data, markdown files, and vector store

**Optional but recommended:**
- Apple Silicon Mac (M1/M2/M3) — Embeddings run 3-5x faster on MPS GPU
- Stable internet connection — For scraping and AWS Bedrock API calls

---

## Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/rmakala38838/uc-rag-chatbot.git
cd uc-rag-chatbot
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
python -m venv venv

# Activate it:
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
| Package | Version | Purpose |
|---------|---------|---------|
| requests | >= 2.31 | HTTP requests for scraping |
| beautifulsoup4 | >= 4.12 | HTML parsing |
| lxml | >= 4.9 | Fast HTML/XML parser |
| tqdm | >= 4.65 | Progress bars |
| boto3 | >= 1.28 | AWS SDK (for Bedrock) |
| chromadb | >= 1.0 | Vector database |
| python-dotenv | >= 1.0 | Load .env files |
| fastapi | >= 0.110 | Web API framework |
| uvicorn | >= 0.27 | ASGI server for FastAPI |
| sentence-transformers | >= 2.6 | Local embedding model |
| streamlit | >= 1.30 | Alternative chat UI |

### Step 4: Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your AWS credentials:

```env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
```

**Where to get AWS credentials:**
1. Go to [AWS Console](https://console.aws.amazon.com) → IAM → Users
2. Create or select a user with `BedrockFullAccess` policy
3. Go to Security Credentials → Create Access Key
4. Copy the Access Key ID and Secret Access Key into your `.env`

### Step 5: Download the Embedding Model (First Time Only)

The embedding model (`BAAI/bge-base-en-v1.5`) is approximately 440MB. It will auto-download the first time you run `ingest.py` or `app.py`. After the first download, it runs fully offline.

If you're on a restricted network, you can pre-download it:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5')"
```

---

## Running the Application

### Full Pipeline (First Time)

Run these steps in order:

```bash
# 1. Scrape the website (~30 minutes, 2,092 pages)
python scraper.py

# 2. Convert JSON to Markdown (~1 minute)
python convert_to_md.py

# 3. Start ChromaDB server (keep this running in a separate terminal)
chroma run --path ./chroma_data --port 8000

# 4. Run ingestion pipeline (~4 minutes)
python ingest.py

# 5. Start the chatbot (in another terminal)
python app.py
```

Then open your browser to: **http://localhost:8080**

### Quick Start (If Data Already Exists)

If you've already run the scraper and ingestion:

```bash
# Terminal 1: Start ChromaDB
chroma run --path ./chroma_data --port 8000

# Terminal 2: Start the chatbot
python app.py
```

### Alternative: Streamlit UI

```bash
streamlit run chatbot.py --server.headless true
```
Opens at http://localhost:8501

---

## How Each Component Works

### 1. Web Scraper (`scraper.py`)

**What it does:** Crawls every page on ucumberlands.edu and saves the content as structured JSON files.

**How it works:**
1. Fetches the sitemap XML from ucumberlands.edu/sitemap.xml
2. Extracts all URLs listed in the sitemap (2,062 pages)
3. Visits each URL and also discovers additional links within pages (383 extra pages)
4. For each page, extracts:
   - Page title
   - All headings (h1-h6) with their hierarchy level
   - Full text content (cleaned of HTML)
   - All links (text + URL)
   - Tables (if any)
   - Meta description
   - URL path hierarchy (e.g., `academics > graduate > mba`)
5. Saves each page as a JSON file in `scraped_data/pages/`

**Key settings:**
- `DELAY_BETWEEN_REQUESTS = 0.1` — 100ms between requests to be respectful
- `MAX_PAGES = 5000` — Safety limit
- `REQUEST_TIMEOUT = 30` — 30 seconds per page max
- Skips binary files (PDFs, images, videos)
- SSL verification disabled (UC site has certificate issues)
- Automatic retry (3 attempts per page)

**Output example** (`scraped_data/pages/academics_graduate_mba.json`):
```json
{
  "url": "https://www.ucumberlands.edu/academics/graduate/mba",
  "title": "Master of Business Administration",
  "full_text": "The MBA program at UC...",
  "headings": [
    {"level": 1, "text": "Master of Business Administration"},
    {"level": 2, "text": "Program Overview"},
    {"level": 2, "text": "Admission Requirements"}
  ],
  "links": [
    {"text": "Apply Now", "url": "https://www.ucumberlands.edu/apply"}
  ],
  "meta_description": "Earn your MBA online at UC...",
  "category": "academics",
  "path_hierarchy": ["academics", "graduate", "mba"]
}
```

---

### 2. Markdown Converter (`convert_to_md.py`)

**What it does:** Transforms raw JSON into clean, structured Markdown files that are easier to chunk and embed.

**Why Markdown?**
- Headings (`##`) provide natural section boundaries for chunking
- Links `[text](url)` are preserved for citations
- Lists are structured clearly
- Removes HTML noise and navigation elements

**How it works:**
1. Reads each JSON file from `scraped_data/pages/`
2. Creates a YAML front matter header with metadata
3. Reconstructs the page content using headings as structure
4. Cleans up noise (navigation buttons like "Move Left", "Skip to main content")
5. De-obfuscates emails (converts `[at]` back to `@`)
6. Converts link text to proper Markdown links using the link data
7. Saves as `.md` file in `markdown_data/`

**Output example** (`markdown_data/academics_graduate_mba.md`):
```markdown
---
title: "Master of Business Administration"
url: "https://www.ucumberlands.edu/academics/graduate/mba"
description: "Earn your MBA online at UC..."
category: "academics"
path: "academics > graduate > mba"
---

# Master of Business Administration

## Program Overview

The MBA program at University of the Cumberlands prepares students
for leadership roles in today's business environment...

## Admission Requirements

- Bachelor's degree from an accredited institution
- Minimum 2.5 GPA
- [Apply online](https://www.ucumberlands.edu/apply)
```

---

### 3. Ingestion Pipeline (`ingest.py`)

**What it does:** Reads all Markdown files, splits them into searchable chunks, generates vector embeddings, and stores everything in ChromaDB.

**How it works:**

1. **Parse**: Reads each `.md` file, separates YAML front matter (metadata) from content
2. **Chunk**: Splits content by heading boundaries
   - Each `##` or `###` heading starts a new section
   - Large sections are further split at sentence boundaries
   - Min chunk: 50 characters / Max chunk: 1,500 characters
   - Each chunk gets a context prefix: `# Page Title\n## Section Heading`
3. **Embed**: Converts each chunk to a 768-dimensional vector
   - Model: `BAAI/bge-base-en-v1.5` (runs locally, no API calls)
   - Batch size: 128 chunks at a time
   - Uses Apple Silicon MPS GPU if available
   - Vectors are normalized for cosine similarity
4. **Store**: Saves to ChromaDB with metadata
   - Each chunk stored with: text, embedding vector, and metadata
   - Metadata includes: URL, title, category, section name, path hierarchy

**Key settings:**
```python
EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"  # 768 dimensions
MAX_CHUNK_CHARS = 1500  # Maximum characters per chunk
MIN_CHUNK_CHARS = 50    # Skip tiny chunks
BATCH_SIZE = 128        # Chunks per embedding batch
```

**What is an embedding?**
An embedding is a list of 768 numbers that represents the "meaning" of a piece of text. Similar texts have similar embeddings. This allows us to find relevant content by comparing the user's question embedding against all stored chunk embeddings.

---

### 4. RAG Chatbot API (`app.py`)

**What it does:** The brain of the chatbot. Receives user questions, retrieves relevant content, and generates answers using Claude.

**API Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serves the main HTML page |
| `/api/chat` | POST | Receives a question, returns an answer |
| `/api/health` | GET | Health check (shows chunk count) |

**How `/api/chat` works:**

1. **Receive** the user's message and chat history
2. **Expand** the query if it's a follow-up:
   - "tell me more" → "MBA program — tell me more"
   - "what about tuition?" → "MBA program — what about tuition?"
3. **Embed** the query using the same BGE model
4. **Search** ChromaDB for the top 15 most similar chunks
5. **Filter** by relevance threshold (similarity > 0.3)
6. **Build** a context block from the top 10 chunks with source attribution
7. **Send** to AWS Bedrock Claude with:
   - System prompt (rules for response format)
   - Last 3 conversation turns (for context)
   - Retrieved chunks as context
   - The user's question
8. **Return** the answer + source metadata

**Query Expansion (Smart Follow-ups):**

The system detects when a user asks a short or ambiguous follow-up question:
```
User: "What programs does the CS department offer?"
Bot: [answers about CS programs]
User: "tell me more"  ← This is ambiguous alone!
```
The system automatically expands "tell me more" to "What programs does the CS department offer? — tell me more" so the vector search finds relevant content.

**Triggers:** Questions with < 6 words, or containing pronouns like "this", "it", "the program", "those".

**System Prompt Rules:**
- Answer only from retrieved context (no hallucination)
- Keep responses to 2-4 short paragraphs
- Include clickable links to source pages
- No emojis, no markdown headings in responses
- Never say "Based on the context" or reference internal workings
- Professional university representative tone

---

### 5. Frontend UI (`static/`)

**What it does:** A professional, UC-branded web interface with a floating chat widget.

**Design:**
- Matches the real ucumberlands.edu website's color scheme
- White background with red accent borders (like the UC header)
- UC crimson red (`#C8102E`) for hero section and accents
- UC navy blue (`#1B365D`) for headings and user messages
- Merriweather font for headings, Open Sans for body text

**Components:**

| File | Purpose |
|------|---------|
| `index.html` | Page structure: header, hero, info cards, chat widget |
| `styles.css` | All styling (596 lines), responsive design, animations |
| `chat.js` | Chat logic: send messages, show typing indicator, format responses |

**Chat Widget Features:**
- Floating red button (bottom-right corner) — click to open
- 480px wide panel with message history
- Typing indicator (3-dot bounce animation)
- User messages in navy bubbles (right-aligned)
- Bot messages in white cards with border (left-aligned)
- Clickable links rendered in red
- Topic cards on the landing page pre-fill questions

**Response Formatting (`chat.js`):**
The browser converts markdown in bot responses to HTML:
- `[text](url)` → clickable links
- `**bold**` → bold text
- `- items` → bullet lists
- Plain URLs → clickable links
- Double newlines → paragraph breaks

---

## Data Flow: End to End

Here's what happens when a user asks "What are the admission requirements for the MBA?":

```
1. User types question in chat widget
      │
      ▼
2. JavaScript sends POST to /api/chat with message + history
      │
      ▼
3. FastAPI receives request
      │
      ▼
4. Query expansion checks if it's a follow-up (no, it's a full question)
      │
      ▼
5. Embedding model converts question to 768-dim vector
      │
      ▼
6. ChromaDB searches 20,520 chunks using cosine similarity
      │
      ▼
7. Top 15 chunks returned (e.g., MBA page sections, admissions page, etc.)
      │
      ▼
8. Top 10 chunks assembled into a context block with source labels
      │
      ▼
9. Context + question + system prompt + chat history → AWS Bedrock Claude
      │
      ▼
10. Claude generates a grounded answer (2-3 paragraphs + links)
      │
      ▼
11. Response returned as JSON to the browser
      │
      ▼
12. JavaScript formats markdown → HTML and displays in chat bubble
```

---

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Yes | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS IAM secret key |
| `AWS_DEFAULT_REGION` | Yes | AWS region (default: `us-east-1`) |
| `BEDROCK_MODEL_ID` | No | Claude model ID (default: `us.anthropic.claude-sonnet-4-6`) |

### Application Settings (`app.py`)

| Setting | Value | What it controls |
|---------|-------|------------------|
| `TOP_K` | 15 | How many chunks to retrieve from ChromaDB |
| `RELEVANCE_THRESHOLD` | 0.3 | Minimum similarity score to consider a chunk relevant |
| `EMBEDDING_MODEL_NAME` | BAAI/bge-base-en-v1.5 | Which embedding model to use |
| Chunks sent to LLM | 10 | How many of the top-15 are included in the prompt |
| Max tokens | 1500 | Maximum length of Claude's response |

### ChromaDB

| Setting | Value |
|---------|-------|
| Host | localhost |
| Port | 8000 |
| Collection name | ucumberlands |
| Distance metric | Cosine similarity |
| Index type | HNSW (Hierarchical Navigable Small World) |

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| **Local embeddings** instead of API | 12x faster (4 min vs 50 min), no per-call cost, works offline |
| **Markdown intermediate step** | Headings provide natural chunk boundaries, cleaner text |
| **Section-aware chunking** | Preserves context within a topic (vs arbitrary character splits) |
| **Context prefix on chunks** | "# Page Title\n## Section" helps retrieval match the right page |
| **Query expansion** | Without it, "tell me more" returns random results |
| **Top-15 retrieve, top-10 to LLM** | Retrieves broadly, sends the best context to reduce noise |
| **Relevance threshold (0.3)** | Prevents the bot from answering with irrelevant content |
| **No streaming** | Simpler architecture; response times are already fast (~2-3s) |
| **Vanilla JS (no React/Vue)** | Simple widget, no build step, fast load times |

---

## Troubleshooting

### ChromaDB connection refused
```
Error: Connection refused on localhost:8000
```
**Fix:** Start ChromaDB first: `chroma run --path ./chroma_data --port 8000`

### Embedding model download fails
```
Error: SSL certificate verify failed
```
**Fix:** The model may need to be downloaded manually. Run:
```bash
pip install --upgrade certifi
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5')"
```

### AWS Bedrock access denied
```
Error: AccessDeniedException
```
**Fix:**
1. Ensure your AWS credentials are correct in `.env`
2. Ensure Claude Sonnet is enabled in the Bedrock console (Model Access page)
3. Check your IAM user has `BedrockFullAccess` or `bedrock:InvokeModel` permission

### "I don't have enough information" for every question
**Fix:** Verify ingestion completed:
```bash
curl http://localhost:8000/api/v1/collections
```
Should show a collection with ~20,520 documents. If 0, re-run `python ingest.py`.

### Slow embedding/ingestion
**Expected:** ~4 minutes on Apple Silicon, ~8-12 minutes on CPU-only.
If much slower, ensure you're not running other heavy processes.

### Port 8080 already in use
```bash
# Find what's using it:
lsof -i :8080
# Kill it, or use a different port:
python -c "import uvicorn; uvicorn.run('app:app', host='0.0.0.0', port=9090)"
```

---

## Future Enhancements

- **Streaming responses** — Show tokens as they generate (real-time feel)
- **Scheduled re-scraping** — Automatically update content weekly
- **User feedback** — Thumbs up/down to improve retrieval quality
- **Analytics dashboard** — Track popular questions and coverage gaps
- **Docker deployment** — Containerize for AWS ECS/EKS
- **Fine-tuned embeddings** — Train on UC-specific terminology
- **Multi-language support** — For international students

---

## License

This project is for academic purposes as part of the MSIT program at the University of the Cumberlands.

---

## Author

Built as a capstone project demonstrating enterprise RAG architecture with modern AI technologies.