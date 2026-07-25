"""
Generate a professional 6-slide PowerPoint presentation for the UC RAG Chatbot project.
Clean design matching UC Cumberlands website: white background, red accents, navy text.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR_TYPE

# UC Brand Colors
UC_NAVY = RGBColor(0x1B, 0x36, 0x5D)
UC_RED = RGBColor(0xC8, 0x10, 0x2E)
UC_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
UC_GRAY = RGBColor(0x6C, 0x75, 0x7D)
UC_DARK = RGBColor(0x2D, 0x37, 0x48)
UC_LIGHT_BG = RGBColor(0xF8, 0xF9, 0xFA)
UC_LIGHT_BORDER = RGBColor(0xE2, 0xE5, 0xEA)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


def add_slide_header(slide, title_text):
    """White header bar with red bottom border — matches UC website."""
    hdr = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.95))
    hdr.fill.solid()
    hdr.fill.fore_color.rgb = UC_WHITE
    hdr.line.fill.background()

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(0.93), prs.slide_width, Inches(0.04))
    line.fill.solid()
    line.fill.fore_color.rgb = UC_RED
    line.line.fill.background()

    txBox = slide.shapes.add_textbox(Inches(0.7), Inches(0.2), Inches(10), Inches(0.7))
    tf = txBox.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = UC_NAVY
    p.font.name = "Segoe UI"


def add_rounded_box(slide, left, top, width, height, fill_color, border_color=None, text="", font_size=11, font_color=UC_DARK, bold=False, align=PP_ALIGN.CENTER):
    """Add a rounded rectangle with centered text."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()

    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.font.name = "Segoe UI"
    p.alignment = align
    return shape


def add_arrow(slide, start_left, start_top, end_left, end_top):
    """Add a connector arrow between points."""
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR_TYPE.STRAIGHT, start_left, start_top, end_left, end_top
    )
    connector.line.color.rgb = UC_GRAY
    connector.line.width = Pt(2)
    return connector


def add_text(slide, left, top, width, height, text, font_size=14, color=UC_DARK, bold=False, align=PP_ALIGN.LEFT):
    """Simple text box."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = "Segoe UI"
    p.alignment = align
    return tf


# ============================================================
# SLIDE 1: Title Slide
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])

# Red top accent bar
accent_top = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.06))
accent_top.fill.solid()
accent_top.fill.fore_color.rgb = UC_RED
accent_top.line.fill.background()

# Left navy vertical bar
left_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.5), prs.slide_height)
left_bar.fill.solid()
left_bar.fill.fore_color.rgb = UC_NAVY
left_bar.line.fill.background()

# Title
add_text(slide, Inches(1.5), Inches(1.8), Inches(10), Inches(1.2),
         "RAG-Powered AI Chatbot", font_size=42, color=UC_NAVY, bold=True)
# Subtitle
add_text(slide, Inches(1.5), Inches(3.0), Inches(10), Inches(0.8),
         "University of the Cumberlands", font_size=28, color=UC_RED, bold=True)
# Tagline
add_text(slide, Inches(1.5), Inches(4.0), Inches(8), Inches(0.6),
         "Intelligent Q&A System  |  2,092 Web Pages  |  20,520 Knowledge Chunks", font_size=16, color=UC_GRAY)

# Bottom red line
bottom_accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(5.0), Inches(3), Inches(0.04))
bottom_accent.fill.solid()
bottom_accent.fill.fore_color.rgb = UC_RED
bottom_accent.line.fill.background()

# Info
add_text(slide, Inches(1.5), Inches(5.3), Inches(8), Inches(0.5),
         "MSIT Program  |  Enterprise RAG Architecture  |  July 2026", font_size=13, color=UC_GRAY)


# ============================================================
# SLIDE 2: Problem & Solution
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_slide_header(slide, "The Challenge & Our Solution")

# Left: Problem
add_rounded_box(slide, Inches(0.7), Inches(1.3), Inches(5.8), Inches(0.55),
                UC_NAVY, text="THE CHALLENGE", font_size=13, font_color=UC_WHITE, bold=True)

items = [
    "2,400+ pages of information spread across ucumberlands.edu",
    "Students struggle to find specific answers quickly",
    "Repetitive questions burden staff and admissions",
]
for i, item in enumerate(items):
    add_text(slide, Inches(1.0), Inches(2.1 + i * 0.55), Inches(5.5), Inches(0.5),
             f"•  {item}", font_size=13, color=UC_DARK)

# Right: Solution
add_rounded_box(slide, Inches(7.0), Inches(1.3), Inches(5.8), Inches(0.55),
                UC_RED, text="OUR SOLUTION", font_size=13, font_color=UC_WHITE, bold=True)

solutions = [
    "AI chatbot with natural language understanding",
    "Instant answers grounded in university data",
    "Source citations with direct links to UC pages",
]
for i, item in enumerate(solutions):
    add_text(slide, Inches(7.3), Inches(2.1 + i * 0.55), Inches(5.5), Inches(0.5),
             f"•  {item}", font_size=13, color=UC_DARK)

# Metrics row
metrics = [
    ("2,092", "Pages Scraped"),
    ("20,520", "Vector Chunks"),
    ("768-dim", "Embeddings"),
    ("< 3 sec", "Response Time"),
]

div = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(4.2), Inches(12), Inches(0.02))
div.fill.solid()
div.fill.fore_color.rgb = UC_LIGHT_BORDER
div.line.fill.background()

for i, (val, label) in enumerate(metrics):
    left = Inches(1.0 + i * 3.1)
    add_text(slide, left, Inches(4.5), Inches(2.5), Inches(0.6),
             val, font_size=28, color=UC_RED, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, left, Inches(5.1), Inches(2.5), Inches(0.4),
             label, font_size=12, color=UC_GRAY, align=PP_ALIGN.CENTER)


# ============================================================
# SLIDE 3: Architecture Diagram
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_slide_header(slide, "System Architecture")

# --- INGESTION PIPELINE (top) ---
add_text(slide, Inches(0.7), Inches(1.15), Inches(4), Inches(0.35),
         "DATA INGESTION PIPELINE", font_size=11, color=UC_RED, bold=True)

ing_y = Inches(1.6)
ing_h = Inches(1.15)
ing_w = Inches(2.2)

boxes_ingestion = [
    ("Web Scraper\n\n2,092 pages", Inches(0.7)),
    ("Markdown\nConverter\n\nJSON → .md", Inches(3.25)),
    ("Section-Aware\nChunking\n\n50–1500 chars", Inches(5.8)),
    ("Local\nEmbeddings\n\nBGE-base 768d", Inches(8.35)),
    ("ChromaDB\nVector Store\n\n20,520 chunks", Inches(10.9)),
]

for text, left in boxes_ingestion:
    add_rounded_box(slide, left, ing_y, ing_w, ing_h,
                    UC_LIGHT_BG, border_color=UC_NAVY,
                    text=text, font_size=10, font_color=UC_NAVY)

# Arrows between ingestion boxes
arrow_y = ing_y + Inches(0.575)
for i in range(len(boxes_ingestion) - 1):
    start_l = boxes_ingestion[i][1] + ing_w + Inches(0.05)
    end_l = boxes_ingestion[i+1][1] - Inches(0.05)
    cxn = slide.shapes.add_connector(MSO_CONNECTOR_TYPE.STRAIGHT, start_l, arrow_y, end_l, arrow_y)
    cxn.line.color.rgb = UC_NAVY
    cxn.line.width = Pt(1.5)

# --- QUERY PIPELINE (bottom) ---
add_text(slide, Inches(0.7), Inches(3.2), Inches(4), Inches(0.35),
         "QUERY & RESPONSE PIPELINE", font_size=11, color=UC_RED, bold=True)

query_y = Inches(3.6)
query_h = Inches(1.15)

boxes_query = [
    ("User\nQuestion\n\nChat Widget", Inches(0.7)),
    ("Query\nExpansion\n\nContext-aware", Inches(3.25)),
    ("Semantic\nSearch\n\nTop-15 → Top-10", Inches(5.8)),
    ("AWS Bedrock\nClaude Sonnet\n\nLLM Generation", Inches(8.35)),
    ("Formatted\nResponse\n\nLinks + Cite", Inches(10.9)),
]

for text, left in boxes_query:
    add_rounded_box(slide, left, query_y, ing_w, query_h,
                    UC_LIGHT_BG, border_color=UC_RED,
                    text=text, font_size=10, font_color=UC_DARK)

# Arrows between query boxes
arrow_y2 = query_y + Inches(0.575)
for i in range(len(boxes_query) - 1):
    start_l = boxes_query[i][1] + ing_w + Inches(0.05)
    end_l = boxes_query[i+1][1] - Inches(0.05)
    cxn = slide.shapes.add_connector(MSO_CONNECTOR_TYPE.STRAIGHT, start_l, arrow_y2, end_l, arrow_y2)
    cxn.line.color.rgb = UC_RED
    cxn.line.width = Pt(1.5)

# Vertical connector: ChromaDB down to Semantic Search
vert_x = Inches(6.9)
cxn_v = slide.shapes.add_connector(MSO_CONNECTOR_TYPE.STRAIGHT, vert_x, ing_y + ing_h, vert_x, query_y)
cxn_v.line.color.rgb = UC_GRAY
cxn_v.line.width = Pt(1.5)
cxn_v.line.dash_style = 2  # dashed

# Tech stack footer
add_text(slide, Inches(0.7), Inches(5.2), Inches(12), Inches(0.4),
         "Python  •  FastAPI  •  sentence-transformers  •  ChromaDB (HNSW)  •  AWS Bedrock  •  HTML/CSS/JS",
         font_size=12, color=UC_GRAY, align=PP_ALIGN.CENTER)


# ============================================================
# SLIDE 4: Tech Stack
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_slide_header(slide, "Technology Stack")

col_data = [
    ("Backend", UC_NAVY, [
        "FastAPI + Uvicorn",
        "ChromaDB (cosine HNSW)",
        "AWS Bedrock Claude Sonnet",
        "sentence-transformers",
        "BAAI/bge-base-en-v1.5",
    ]),
    ("Data Pipeline", UC_RED, [
        "Sitemap + link crawling",
        "JSON → Markdown converter",
        "Section-aware chunking",
        "Local GPU embeddings (MPS)",
        "4 min full ingestion",
    ]),
    ("Frontend", UC_NAVY, [
        "UC-branded responsive UI",
        "Floating chat widget",
        "Real-time typing indicators",
        "Clickable source links",
        "Context-aware follow-ups",
    ]),
]

for col_idx, (title, color, items) in enumerate(col_data):
    left = Inches(0.7 + col_idx * 4.2)
    add_rounded_box(slide, left, Inches(1.3), Inches(3.8), Inches(0.5),
                    color, text=title, font_size=13, font_color=UC_WHITE, bold=True)
    for i, item in enumerate(items):
        add_text(slide, left + Inches(0.2), Inches(2.0 + i * 0.48), Inches(3.6), Inches(0.45),
                 f"•  {item}", font_size=12, color=UC_DARK)

# Key decision highlight
add_rounded_box(slide, Inches(0.7), Inches(4.8), Inches(12), Inches(0.6),
                UC_LIGHT_BG, border_color=UC_LIGHT_BORDER,
                text="Key Decision: Local embeddings (4 min) vs API-based (50 min) — 12x faster with same quality",
                font_size=12, font_color=UC_NAVY)


# ============================================================
# SLIDE 5: RAG Pipeline Detail
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_slide_header(slide, "RAG Retrieval & Grounding")

# Left: Pipeline steps
steps = [
    ("1", "SCRAPE", "Sitemap + crawl → 2,092 JSON pages"),
    ("2", "CONVERT", "JSON → Markdown with YAML metadata"),
    ("3", "CHUNK", "Heading-based splits, 50–1500 chars"),
    ("4", "EMBED", "BGE-base local, 768d, MPS GPU"),
    ("5", "STORE", "ChromaDB, cosine HNSW index"),
]

for i, (num, title, desc) in enumerate(steps):
    y = Inches(1.3 + i * 0.88)
    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.8), y, Inches(0.42), Inches(0.42))
    circle.fill.solid()
    circle.fill.fore_color.rgb = UC_RED
    circle.line.fill.background()
    tf = circle.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = num
    p.font.size = Pt(11)
    p.font.color.rgb = UC_WHITE
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER

    add_text(slide, Inches(1.45), y + Inches(0.02), Inches(1.5), Inches(0.35),
             title, font_size=12, color=UC_NAVY, bold=True)
    add_text(slide, Inches(2.8), y + Inches(0.02), Inches(3.8), Inches(0.4),
             desc, font_size=11, color=UC_DARK)

# Right: Retrieval strategy
add_rounded_box(slide, Inches(7.3), Inches(1.3), Inches(5.4), Inches(0.5),
                UC_NAVY, text="RETRIEVAL STRATEGY", font_size=12, font_color=UC_WHITE, bold=True)

retrieval_items = [
    "Query expansion for pronouns & follow-ups",
    "Same model for indexing and querying",
    "Top-15 retrieved, top-10 to LLM",
    "Relevance threshold: 0.3 minimum",
    "Chat history (3 turns) for context",
    "Grounded: only answers from retrieved data",
]
for i, item in enumerate(retrieval_items):
    add_text(slide, Inches(7.5), Inches(2.0 + i * 0.48), Inches(5.2), Inches(0.45),
             f"•  {item}", font_size=11, color=UC_DARK)


# ============================================================
# SLIDE 6: Demo & Summary
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_slide_header(slide, "Demo & Summary")

# Left: UI
add_rounded_box(slide, Inches(0.7), Inches(1.3), Inches(5.5), Inches(0.5),
                UC_RED, text="USER INTERFACE", font_size=12, font_color=UC_WHITE, bold=True)

ui_items = [
    "White header + red accent (matching UC website)",
    "Red hero section with call-to-action",
    "Topic cards for quick questions",
    "Floating chat widget (480px panel)",
    "Professional tone, clickable source links",
]
for i, item in enumerate(ui_items):
    add_text(slide, Inches(0.9), Inches(2.0 + i * 0.45), Inches(5.3), Inches(0.42),
             f"•  {item}", font_size=12, color=UC_DARK)

# Right: Highlights
add_rounded_box(slide, Inches(6.8), Inches(1.3), Inches(5.8), Inches(0.5),
                UC_NAVY, text="PROJECT HIGHLIGHTS", font_size=12, font_color=UC_WHITE, bold=True)

highlights = [
    "End-to-end RAG: scrape → embed → answer",
    "Local + cloud AI (embeddings + LLM)",
    "Sub-3-second response time",
    "Extensible: streaming, analytics, Docker",
    "Production-ready architecture",
]
for i, item in enumerate(highlights):
    add_text(slide, Inches(7.0), Inches(2.0 + i * 0.45), Inches(5.5), Inches(0.42),
             f"•  {item}", font_size=12, color=UC_DARK)

# Bottom
div = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(4.6), Inches(12), Inches(0.02))
div.fill.solid()
div.fill.fore_color.rgb = UC_LIGHT_BORDER
div.line.fill.background()

add_text(slide, Inches(0.7), Inches(4.9), Inches(12), Inches(0.5),
         "GitHub: github.com/rmakala38838/uc-rag-chatbot", font_size=14, color=UC_NAVY, bold=True, align=PP_ALIGN.CENTER)

add_text(slide, Inches(0.7), Inches(5.5), Inches(12), Inches(0.5),
         "Thank You  —  Questions & Live Demo", font_size=22, color=UC_RED, bold=True, align=PP_ALIGN.CENTER)


# Save
output_path = "UC_RAG_Chatbot_Presentation.pptx"
prs.save(output_path)
print(f"Presentation saved: {output_path}")
print(f"Slides: {len(prs.slides)}")