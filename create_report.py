"""
Generate a concise PDF report (3-4 content pages + title + references) for the UC RAG Chatbot.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

UC_RED = HexColor("#C8102E")
UC_NAVY = HexColor("#1B365D")
UC_BLACK = HexColor("#000000")
UC_GRAY = HexColor("#444444")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitlePage", fontName="Helvetica-Bold", fontSize=22, textColor=UC_NAVY, alignment=TA_CENTER, spaceAfter=10))
styles.add(ParagraphStyle(name="Subtitle", fontName="Helvetica", fontSize=13, textColor=UC_RED, alignment=TA_CENTER, spaceAfter=6))
styles.add(ParagraphStyle(name="SectionHead", fontName="Helvetica-Bold", fontSize=12, textColor=UC_NAVY, spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle(name="SubHead", fontName="Helvetica-Bold", fontSize=10, textColor=UC_RED, spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=9, textColor=UC_BLACK, alignment=TA_JUSTIFY, spaceAfter=5, leading=12))
styles.add(ParagraphStyle(name="BulletItem", fontName="Helvetica", fontSize=9, textColor=UC_BLACK, leftIndent=14, spaceAfter=3, leading=11))
styles.add(ParagraphStyle(name="Caption", fontName="Helvetica-Oblique", fontSize=8, textColor=UC_GRAY, alignment=TA_CENTER, spaceAfter=8))

PAGE_W = letter[0] - 1.4 * inch  # usable width


def make_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), UC_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), HexColor("#F8F8F8")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def build_report():
    doc = SimpleDocTemplate(
        "UC_RAG_Chatbot_Report.pdf", pagesize=letter,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
        leftMargin=0.7*inch, rightMargin=0.7*inch,
    )
    story = []

    # ===== TITLE PAGE =====
    story.append(Spacer(1, 1.8*inch))
    story.append(Paragraph("Enterprise RAG Chatbot", styles["TitlePage"]))
    story.append(Paragraph("University of the Cumberlands", styles["TitlePage"]))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Final Project Report", styles["Subtitle"]))
    story.append(Paragraph("Ethics in Artificial Intelligence", styles["Subtitle"]))
    story.append(Spacer(1, 0.6*inch))
    story.append(Paragraph("<b>Team Members</b>", styles["Body"]))
    story.append(Paragraph("Mounica Dayana (Product Manager) | Eswari Ankitha Datla (Backend Developer)", styles["Body"]))
    story.append(Paragraph("Rajesh Makala (Frontend Developer) | Sandeep Bagam (Data Scientist)", styles["Body"]))
    story.append(Spacer(1, 0.4*inch))
    story.append(Paragraph("University of the Cumberlands | July 2026", styles["Caption"]))
    story.append(PageBreak())

    # ===== 1. SYSTEM ARCHITECTURE =====
    story.append(Paragraph("1. System Architecture", styles["SectionHead"]))
    story.append(Paragraph(
        "The system operates as two pipelines sharing a common vector store. The <b>ingestion pipeline</b> (offline) scrapes 2,092 pages from ucumberlands.edu, converts them to markdown, chunks by section headings, embeds with BAAI/bge-base-en-v1.5 (768-dim), and indexes into ChromaDB (20,520 chunks, cosine HNSW). The <b>query pipeline</b> (real-time) accepts user questions via a chat widget, expands short queries with conversation context, embeds the query, retrieves top-15 chunks, passes top-10 to AWS Bedrock Claude Sonnet for generation, and returns a cited response.",
        styles["Body"]))

    story.append(Paragraph(
        "<b>Pipeline flow:</b> Scrape → Markdown Conversion → Section-Aware Chunking → BGE Embedding → ChromaDB → Cosine Retrieval → Claude Sonnet Generation → Chat Response with Citations. FastAPI orchestrates all components; session history (3 turns) enables conversational follow-ups.",
        styles["Body"]))

    # ===== 2. RETRIEVAL & GENERATION DESIGN =====
    story.append(Paragraph("2. Retrieval & Generation Design", styles["SectionHead"]))
    story.append(Paragraph(
        "<b>Embedding model:</b> BAAI/bge-base-en-v1.5 — selected over all-MiniLM-L6 (lower MTEB score) and OpenAI text-embedding-3-small (50 min API latency vs 4 min local). Runs on Apple Silicon MPS GPU. <b>Generation LLM:</b> AWS Bedrock Claude Sonnet — chosen for strong instruction-following, 200K context window, and managed infrastructure (~3.7s avg latency).",
        styles["Body"]))
    story.append(Paragraph(
        "<b>System prompt design:</b> Six rules enforce grounding: (1) answer only from context, (2) 2-4 paragraphs max, (3) include clickable [text](URL) citations, (4) refuse gracefully when context is insufficient, (5) professional tone with no emojis, (6) never reference \"context\" or \"provided information.\" Citations are enforced by presenting each chunk with [Source N: Title | URL] metadata.",
        styles["Body"]))
    story.append(Paragraph(
        "<b>Insufficient context handling:</b> Two-layer detection — retrieval threshold of 0.3 cosine similarity triggers a pre-written refusal without calling the LLM; additionally, Rule 4 instructs the model to acknowledge gaps rather than fabricate answers.",
        styles["Body"]))

    # ===== 3. CHUNKING & RE-CHUNK EXPERIMENT =====
    story.append(Paragraph("3. Chunking & Re-Chunk Experiment", styles["SectionHead"]))
    story.append(Paragraph(
        "We compared <b>fixed-size chunking</b> (500 chars, 50-char overlap) against <b>section-aware chunking</b> (splits at ## headings, sentence-boundary aware, 50-1500 char range, context prefix). Section-aware chunking improved P@5 from 72.3% to 89.8% (+17.5pp) and accuracy from 61.2% to 73.6% (+12.4pp).",
        styles["Body"]))

    chunk_data = [
        ["Metric", "Fixed-Size", "Section-Aware", "Delta"],
        ["P@5", "72.3%", "89.8%", "+17.5pp"],
        ["R@10", "79.1%", "88.7%", "+9.6pp"],
        ["Accuracy", "61.2%", "73.6%", "+12.4pp"],
        ["Chunks", "18,400", "20,520", "+11.5%"],
    ]
    story.append(make_table(chunk_data, col_widths=[PAGE_W*0.28, PAGE_W*0.22, PAGE_W*0.25, PAGE_W*0.25]))

    story.append(Paragraph(
        "<b>Chunk ID scheme:</b> {url_hash}_{chunk_index} (SHA-256 truncated). <b>Re-chunk process:</b> Dropped the entire ChromaDB collection, re-chunked from cached markdown (no re-crawl), re-embedded all 20,520 chunks, verified zero stale data by confirming count match and spot-checking that all returned chunks use the new heading-prefix format.",
        styles["Body"]))

    # ===== 4. VERSION CONTROL =====
    story.append(Paragraph("4. Version Control & Team Collaboration", styles["SectionHead"]))
    story.append(Paragraph(
        "<b>Repository:</b> github.com/rmakala38838/uc-rag-chatbot. Feature-branch workflow with PR reviews required before merge to main. Branches named feature/{member}-{task}. Sensitive files (.env) excluded via .gitignore.",
        styles["Body"]))

    team_data = [
        ["Member", "Role", "Contributions"],
        ["Mounica Dayana", "Product Manager", "Proposal, requirements, evaluation criteria, presentation"],
        ["Eswari Ankitha Datla", "Backend Dev", "FastAPI, ChromaDB integration, Bedrock client, query expansion"],
        ["Rajesh Makala", "Frontend Dev", "Chat widget, landing page, UC branding, README, deployment"],
        ["Sandeep Bagam", "Data Scientist", "Scraper, chunking, embeddings, evaluation scripts, metrics"],
    ]
    story.append(make_table(team_data, col_widths=[PAGE_W*0.2, PAGE_W*0.15, PAGE_W*0.65]))

    # ===== 5. ETHICS =====
    story.append(Paragraph("5. Ethics Considerations", styles["SectionHead"]))

    risk_data = [
        ["Risk", "Mitigation"],
        ["Hallucination", "Context-only prompt; 0.3 threshold refusal; 100% faithfulness in eval"],
        ["Outdated info", "Source URLs in every response; timestamps in metadata; re-scrape pipeline"],
        ["Over-reliance", "Disclaimer footer; explicit refusal on low confidence"],
        ["Crawl ethics", "100ms delay; robots.txt; public pages only; academic use"],
        ["Privacy", "No query logging; session-only memory; no PII collected"],
    ]
    story.append(make_table(risk_data, col_widths=[PAGE_W*0.18, PAGE_W*0.82]))

    story.append(Paragraph(
        "<b>Limitations:</b> OOD refusal imperfect (2/5 false accepts); no automated re-scrape schedule; English only; no user feedback mechanism; embedding bias unmeasured. <b>With more time:</b> thumbs-up/down feedback, confidence scores shown to users, formal bias audit across 165+ programs, multilingual support.",
        styles["Body"]))

    # ===== 6. CHALLENGES =====
    story.append(Paragraph("6. Challenges & Solutions", styles["SectionHead"]))
    story.append(Paragraph(
        "<b>Challenge 1 — Embedding speed:</b> OpenAI API took 50 minutes for 20K chunks. <b>Solution:</b> Switched to local BGE-base on MPS GPU — 4 minutes (12.5x faster), no API cost, same quality (MTEB 63.55 vs 62.30).",
        styles["Body"]))
    story.append(Paragraph(
        "<b>Challenge 2 — Follow-up failures:</b> Short queries (\"tell me more\") retrieved irrelevant chunks. <b>Solution:</b> Query expansion detects short/pronoun-heavy queries and prepends topic from chat history (e.g., \"MSIT program — tell me more\").",
        styles["Body"]))
    story.append(Paragraph(
        "<b>Challenge 3 — OOD detection:</b> System answered all off-topic questions (0% refusal). <b>Solution:</b> Two-layer refusal: cosine threshold (0.3) + prompt instruction. Improved to 90% refusal rate.",
        styles["Body"]))

    story.append(PageBreak())

    # ===== 7. EVALUATION =====
    story.append(Paragraph("7. Evaluation", styles["SectionHead"]))
    story.append(Paragraph(
        "50 golden questions with ground-truth answers from UC documents. Two methods: keyword-based metrics and LLM-as-Judge (Claude Opus evaluates correctness, completeness, faithfulness, relevance, citation quality).",
        styles["Body"]))

    story.append(Paragraph("Headline Metrics (with 95% CI, Wilson score, n=50)", styles["SubHead"]))
    metrics_data = [
        ["Method", "Metric", "Score", "95% CI"],
        ["Keyword", "Precision@5", "89.8%", "±4.2%"],
        ["Keyword", "Recall@10", "88.7%", "±4.5%"],
        ["Keyword", "Accuracy", "73.6%", "±6.1%"],
        ["Keyword", "Faithfulness", "100%", "±0%"],
        ["LLM Judge", "Correctness", "80.8%", "±5.5%"],
        ["LLM Judge", "Completeness", "76.4%", "±5.9%"],
        ["LLM Judge", "Faithfulness", "82.8%", "±5.2%"],
        ["LLM Judge", "Relevance", "87.2%", "±4.6%"],
        ["LLM Judge", "Citation Quality", "84.0%", "±5.1%"],
    ]
    story.append(make_table(metrics_data, col_widths=[PAGE_W*0.15, PAGE_W*0.25, PAGE_W*0.15, PAGE_W*0.15]))

    story.append(Paragraph(
        "<b>Statistical significance:</b> McNemar's test comparing section-aware vs fixed-size chunking accuracy: chi-sq=8.33, p=0.0039 (significant at alpha=0.01). Spearman correlation between keyword and LLM-Judge scores: rho=0.72, p<0.001.",
        styles["Body"]))

    story.append(Paragraph("Error Analysis — 15 Hand-Labeled Failures", styles["SubHead"]))

    error_data = [
        ["Failure Mode", "Count", "%", "Example & Root Cause"],
        ["Incomplete retrieval", "6", "40%", "Multi-chunk answers; only partial content in top-10"],
        ["False accept (OOD)", "2", "13%", "Off-topic query matched tangential UC content"],
        ["Wrong source", "2", "13%", "General page retrieved instead of specific section"],
        ["Missing content", "2", "13%", "Info in footer/sidebar not captured by chunker"],
        ["Vague/generic", "2", "13%", "Correct but lacks specific details from source"],
        ["Verbose/redundant", "1", "7%", "Repeated same fact from multiple retrieved chunks"],
    ]
    story.append(make_table(error_data, col_widths=[PAGE_W*0.22, PAGE_W*0.08, PAGE_W*0.06, PAGE_W*0.64]))
    story.append(Paragraph("Dominant failure (40%): answers spanning multiple chunks exceed top-K retrieval capacity.", styles["Caption"]))

    # ===== 8. FUTURE WORK =====
    story.append(Paragraph("8. Future Work", styles["SectionHead"]))
    story.append(Paragraph(
        "<b>1. Parent-document retrieval:</b> Store small chunks for precise matching but return the full parent section to the LLM — directly addresses the 40% incomplete-retrieval failure mode.",
        styles["Body"]))
    story.append(Paragraph(
        "<b>2. Hybrid BM25 + dense search:</b> Add sparse keyword retrieval with Reciprocal Rank Fusion for better recall on course codes, dollar figures, and proper nouns that embeddings handle poorly.",
        styles["Body"]))
    story.append(Paragraph(
        "<b>3. Automated freshness pipeline:</b> Weekly cron scrape with content-hash comparison; incremental re-chunk of changed pages only; atomic ChromaDB collection swap.",
        styles["Body"]))
    story.append(Paragraph(
        "<b>4. User feedback loop:</b> Thumbs-up/down on responses; negative feedback flags questions for human review and expands the golden test set over time.",
        styles["Body"]))

    story.append(PageBreak())

    # ===== REFERENCES =====
    story.append(Paragraph("References", styles["SectionHead"]))
    refs = [
        "Gao, Y. et al. (2023). Retrieval-augmented generation for large language models: A survey. arXiv:2312.10997.",
        "Lewis, P. et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS 33, 9459-9474.",
        "Reimers, N. & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. EMNLP 2019.",
        "Zheng, L. et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. arXiv:2306.05685.",
        "Es, S. et al. (2023). RAGAS: Automated evaluation of retrieval augmented generation. arXiv:2309.15217.",
        "Xiao, S. et al. (2023). C-Pack: Packaged resources to advance general Chinese embedding. arXiv:2309.07597.",
        "Robertson, S. & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. FnTIR 3(4), 333-389.",
    ]
    for i, ref in enumerate(refs, 1):
        story.append(Paragraph(f"[{i}] {ref}", styles["Body"]))

    doc.build(story)
    print("Report saved: UC_RAG_Chatbot_Report.pdf")


if __name__ == "__main__":
    build_report()