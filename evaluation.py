
"""
RAG Chatbot Evaluation Suite
Tests 50 golden questions across 7 categories and computes retrieval + generation metrics.
Metrics: Retrieval Precision@5, Recall@10, Answer Accuracy, Faithfulness, Citation Accuracy, Refusal Appropriateness.
"""

import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import json
import time
import re
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

import boto3
import chromadb
from sentence_transformers import SentenceTransformer

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "ucumberlands"
EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"
LLM_MODEL = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
TOP_K = 15
RELEVANCE_THRESHOLD = 0.3

# ============================================================
# GOLDEN TEST SET — 50 Questions across 7 Categories
# ============================================================

GOLDEN_QUESTIONS = [
    # --- Category 1: Admission & Application (10 questions) ---
    {
        "id": "ADM-01",
        "category": "admission",
        "question": "What are the admission requirements for undergraduate students?",
        "expected_category": "admissions",
        "expected_keywords": ["gpa", "application", "transcript", "act", "sat"],
        "should_answer": True,
    },
    {
        "id": "ADM-02",
        "category": "admission",
        "question": "How do I apply for admission to UC?",
        "expected_category": "admissions",
        "expected_keywords": ["apply", "application", "online", "ucumberlands.edu"],
        "should_answer": True,
    },
    {
        "id": "ADM-03",
        "category": "admission",
        "question": "What is the application deadline for fall semester?",
        "expected_category": "admissions",
        "expected_keywords": ["deadline", "fall", "semester", "date"],
        "should_answer": True,
    },
    {
        "id": "ADM-04",
        "category": "admission",
        "question": "What documents are required for international student admission?",
        "expected_category": "admissions",
        "expected_keywords": ["international", "toefl", "ielts", "passport", "i-20", "transcript"],
        "should_answer": True,
    },
    {
        "id": "ADM-05",
        "category": "admission",
        "question": "Can I transfer credits from another university to UC?",
        "expected_category": "admissions",
        "expected_keywords": ["transfer", "credit", "hours", "accredited"],
        "should_answer": True,
    },
    {
        "id": "ADM-06",
        "category": "admission",
        "question": "What is the minimum GPA required for graduate admission?",
        "expected_category": "admissions",
        "expected_keywords": ["gpa", "graduate", "minimum", "2.5", "3.0"],
        "should_answer": True,
    },
    {
        "id": "ADM-07",
        "category": "admission",
        "question": "Does UC require standardized test scores for admission?",
        "expected_category": "admissions",
        "expected_keywords": ["test", "score", "act", "sat", "gre", "optional"],
        "should_answer": True,
    },
    {
        "id": "ADM-08",
        "category": "admission",
        "question": "How long does it take to receive an admission decision?",
        "expected_category": "admissions",
        "expected_keywords": ["decision", "weeks", "days", "notification"],
        "should_answer": True,
    },
    {
        "id": "ADM-09",
        "category": "admission",
        "question": "What is the process for readmission to UC after a break?",
        "expected_category": "admissions",
        "expected_keywords": ["readmission", "return", "re-enroll", "break"],
        "should_answer": True,
    },
    {
        "id": "ADM-10",
        "category": "admission",
        "question": "Are there any admission requirements specific to the doctoral programs?",
        "expected_category": "admissions",
        "expected_keywords": ["doctoral", "phd", "dissertation", "master", "experience"],
        "should_answer": True,
    },

    # --- Category 2: Academic Programs (10 questions) ---
    {
        "id": "ACAD-01",
        "category": "academic",
        "question": "What undergraduate programs does UC offer?",
        "expected_category": "academics",
        "expected_keywords": ["bachelor", "program", "major", "degree"],
        "should_answer": True,
    },
    {
        "id": "ACAD-02",
        "category": "academic",
        "question": "What are the course requirements for the MBA program?",
        "expected_category": "academics",
        "expected_keywords": ["mba", "course", "credit", "hours", "business"],
        "should_answer": True,
    },
    {
        "id": "ACAD-03",
        "category": "academic",
        "question": "Does UC offer an online computer science degree?",
        "expected_category": "academics",
        "expected_keywords": ["computer science", "online", "degree", "program"],
        "should_answer": True,
    },
    {
        "id": "ACAD-04",
        "category": "academic",
        "question": "What doctoral programs are available at UC?",
        "expected_category": "academics",
        "expected_keywords": ["doctoral", "phd", "edd", "program"],
        "should_answer": True,
    },
    {
        "id": "ACAD-05",
        "category": "academic",
        "question": "What certificate programs does UC have in technology?",
        "expected_category": "academics",
        "expected_keywords": ["certificate", "technology", "ai", "cyber", "data"],
        "should_answer": True,
    },
    {
        "id": "ACAD-06",
        "category": "academic",
        "question": "How many credit hours are required for a bachelor's degree?",
        "expected_category": "academics",
        "expected_keywords": ["credit", "hours", "120", "bachelor", "semester"],
        "should_answer": True,
    },
    {
        "id": "ACAD-07",
        "category": "academic",
        "question": "What is the MSIT program curriculum?",
        "expected_category": "academics",
        "expected_keywords": ["msit", "information", "technology", "course", "curriculum"],
        "should_answer": True,
    },
    {
        "id": "ACAD-08",
        "category": "academic",
        "question": "Does UC offer a nursing program?",
        "expected_category": "academics",
        "expected_keywords": ["nursing", "bsn", "rn", "health"],
        "should_answer": True,
    },
    {
        "id": "ACAD-09",
        "category": "academic",
        "question": "What are the general education requirements at UC?",
        "expected_category": "academics",
        "expected_keywords": ["general education", "core", "requirement", "liberal arts"],
        "should_answer": True,
    },
    {
        "id": "ACAD-10",
        "category": "academic",
        "question": "What accreditations does UC hold?",
        "expected_category": "academics",
        "expected_keywords": ["accredit", "sacscoc", "regional", "recognized"],
        "should_answer": True,
    },

    # --- Category 3: Tuition & Financial Aid (8 questions) ---
    {
        "id": "FIN-01",
        "category": "financial",
        "question": "What is the tuition cost for online graduate programs?",
        "expected_category": "tuition",
        "expected_keywords": ["tuition", "cost", "per credit", "online", "graduate"],
        "should_answer": True,
    },
    {
        "id": "FIN-02",
        "category": "financial",
        "question": "What scholarships are available at UC?",
        "expected_category": "tuition",
        "expected_keywords": ["scholarship", "award", "merit", "financial"],
        "should_answer": True,
    },
    {
        "id": "FIN-03",
        "category": "financial",
        "question": "How do I apply for financial aid at UC?",
        "expected_category": "tuition",
        "expected_keywords": ["fafsa", "financial aid", "apply", "form"],
        "should_answer": True,
    },
    {
        "id": "FIN-04",
        "category": "financial",
        "question": "Does UC offer payment plans for tuition?",
        "expected_category": "tuition",
        "expected_keywords": ["payment", "plan", "installment", "tuition"],
        "should_answer": True,
    },
    {
        "id": "FIN-05",
        "category": "financial",
        "question": "What is the cost of room and board at UC?",
        "expected_category": "tuition",
        "expected_keywords": ["room", "board", "housing", "cost", "semester"],
        "should_answer": True,
    },
    {
        "id": "FIN-06",
        "category": "financial",
        "question": "Are there any military or veteran tuition benefits?",
        "expected_category": "tuition",
        "expected_keywords": ["military", "veteran", "gi bill", "benefit", "discount"],
        "should_answer": True,
    },
    {
        "id": "FIN-07",
        "category": "financial",
        "question": "What is the tuition for undergraduate on-campus students?",
        "expected_category": "tuition",
        "expected_keywords": ["tuition", "undergraduate", "campus", "cost", "per semester"],
        "should_answer": True,
    },
    {
        "id": "FIN-08",
        "category": "financial",
        "question": "Does UC offer employer tuition reimbursement partnerships?",
        "expected_category": "tuition",
        "expected_keywords": ["employer", "reimbursement", "partnership", "corporate"],
        "should_answer": True,
    },

    # --- Category 4: Student Life (7 questions) ---
    {
        "id": "LIFE-01",
        "category": "student_life",
        "question": "What is campus life like at UC Cumberlands?",
        "expected_category": "student-life",
        "expected_keywords": ["campus", "activities", "student", "community"],
        "should_answer": True,
    },
    {
        "id": "LIFE-02",
        "category": "student_life",
        "question": "What student organizations and clubs are available?",
        "expected_category": "student-life",
        "expected_keywords": ["club", "organization", "student", "activities"],
        "should_answer": True,
    },
    {
        "id": "LIFE-03",
        "category": "student_life",
        "question": "What housing options are available for students?",
        "expected_category": "student-life",
        "expected_keywords": ["housing", "dorm", "residence", "hall", "room"],
        "should_answer": True,
    },
    {
        "id": "LIFE-04",
        "category": "student_life",
        "question": "What sports teams does UC have?",
        "expected_category": "student-life",
        "expected_keywords": ["sports", "athletic", "team", "ncaa", "basketball", "football"],
        "should_answer": True,
    },
    {
        "id": "LIFE-05",
        "category": "student_life",
        "question": "What dining options are available on campus?",
        "expected_category": "student-life",
        "expected_keywords": ["dining", "food", "cafeteria", "meal plan"],
        "should_answer": True,
    },
    {
        "id": "LIFE-06",
        "category": "student_life",
        "question": "Does UC offer career services for students?",
        "expected_category": "student-life",
        "expected_keywords": ["career", "service", "job", "internship", "placement"],
        "should_answer": True,
    },
    {
        "id": "LIFE-07",
        "category": "student_life",
        "question": "What mental health or counseling services are available?",
        "expected_category": "student-life",
        "expected_keywords": ["counseling", "mental health", "support", "wellness"],
        "should_answer": True,
    },

    # --- Category 5: Faculty & Staff (5 questions) ---
    {
        "id": "FAC-01",
        "category": "faculty",
        "question": "Who are the faculty in the Computer Science department?",
        "expected_category": "faculty",
        "expected_keywords": ["professor", "faculty", "computer science", "department"],
        "should_answer": True,
    },
    {
        "id": "FAC-02",
        "category": "faculty",
        "question": "How can I contact the admissions office?",
        "expected_category": "admissions",
        "expected_keywords": ["contact", "phone", "email", "admissions", "office"],
        "should_answer": True,
    },
    {
        "id": "FAC-03",
        "category": "faculty",
        "question": "Who is the president of University of the Cumberlands?",
        "expected_category": "about",
        "expected_keywords": ["president", "leadership", "dr."],
        "should_answer": True,
    },
    {
        "id": "FAC-04",
        "category": "faculty",
        "question": "What is the student-to-faculty ratio at UC?",
        "expected_category": "about",
        "expected_keywords": ["ratio", "student", "faculty", "class size"],
        "should_answer": True,
    },
    {
        "id": "FAC-05",
        "category": "faculty",
        "question": "How do I reach the financial aid office?",
        "expected_category": "tuition",
        "expected_keywords": ["financial aid", "contact", "phone", "email", "office"],
        "should_answer": True,
    },

    # --- Category 6: General/About (5 questions) ---
    {
        "id": "GEN-01",
        "category": "general",
        "question": "Where is University of the Cumberlands located?",
        "expected_category": "about",
        "expected_keywords": ["williamsburg", "kentucky", "location", "address"],
        "should_answer": True,
    },
    {
        "id": "GEN-02",
        "category": "general",
        "question": "What is the mission statement of UC?",
        "expected_category": "about",
        "expected_keywords": ["mission", "christian", "education", "values"],
        "should_answer": True,
    },
    {
        "id": "GEN-03",
        "category": "general",
        "question": "When was University of the Cumberlands founded?",
        "expected_category": "about",
        "expected_keywords": ["founded", "1888", "1889", "history", "established"],
        "should_answer": True,
    },
    {
        "id": "GEN-04",
        "category": "general",
        "question": "How many students are enrolled at UC?",
        "expected_category": "about",
        "expected_keywords": ["enrollment", "students", "total", "thousand"],
        "should_answer": True,
    },
    {
        "id": "GEN-05",
        "category": "general",
        "question": "What is the academic calendar for the current year?",
        "expected_category": "academics",
        "expected_keywords": ["calendar", "semester", "start", "end", "break"],
        "should_answer": True,
    },

    # --- Category 7: Out-of-Domain / Should Refuse (5 questions) ---
    {
        "id": "OOD-01",
        "category": "out_of_domain",
        "question": "What is the weather forecast for Tokyo this week?",
        "expected_category": None,
        "expected_keywords": [],
        "should_answer": False,
    },
    {
        "id": "OOD-02",
        "category": "out_of_domain",
        "question": "Can you write me a Python script to sort a list?",
        "expected_category": None,
        "expected_keywords": [],
        "should_answer": False,
    },
    {
        "id": "OOD-03",
        "category": "out_of_domain",
        "question": "What is the stock price of Apple today?",
        "expected_category": None,
        "expected_keywords": [],
        "should_answer": False,
    },
    {
        "id": "OOD-04",
        "category": "out_of_domain",
        "question": "Who won the Super Bowl last year?",
        "expected_category": None,
        "expected_keywords": [],
        "should_answer": False,
    },
    {
        "id": "OOD-05",
        "category": "out_of_domain",
        "question": "Explain quantum computing in simple terms.",
        "expected_category": None,
        "expected_keywords": [],
        "should_answer": False,
    },
]


# ============================================================
# EVALUATION ENGINE
# ============================================================

class RAGEvaluator:
    def __init__(self):
        logger.info("Initializing evaluator...")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        self.collection = self.chroma_client.get_collection(name=COLLECTION_NAME)
        self.bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        logger.info(f"Connected to ChromaDB collection: {self.collection.count()} chunks")

    def embed_query(self, query):
        embedding = self.embedding_model.encode([query], normalize_embeddings=True)[0]
        return embedding.tolist()

    def retrieve(self, query, top_k=TOP_K):
        query_embedding = self.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
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

    def generate_answer(self, query, chunks):
        if not chunks or chunks[0]["similarity"] < RELEVANCE_THRESHOLD:
            return {
                "answer": "I don't have enough information from the University of the Cumberlands website to answer this question.",
                "is_refusal": True,
            }

        context_parts = []
        for i, chunk in enumerate(chunks[:10], 1):
            meta = chunk["metadata"]
            source = f"[Source {i}: {meta.get('title', 'Unknown')} | {meta.get('section', '')} | {meta.get('url', '')}]"
            context_parts.append(f"{source}\n{chunk['text']}")
        context_block = "\n\n---\n\n".join(context_parts)

        system_prompt = """You are a professional virtual assistant for the University of the Cumberlands. Answer based ONLY on the provided context.
RULES:
1. Only answer from provided context. Do not use external knowledge.
2. Keep responses concise (2-4 paragraphs).
3. Include clickable links [text](URL) from the source context.
4. If context lacks information, say so briefly.
5. No emojis. No markdown headings.
6. NEVER reference "context" or "provided information"."""

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "system": system_prompt,
            "messages": [{"role": "user", "content": f"CONTEXT:\n{context_block}\n\nQUESTION: {query}"}],
        })

        response = self.bedrock.invoke_model(modelId=LLM_MODEL, body=body)
        result = json.loads(response["body"].read())
        answer = result["content"][0]["text"]

        return {"answer": answer, "is_refusal": False}

    def evaluate_single(self, test_case):
        """Run a single test case and compute per-question metrics."""
        question = test_case["question"]
        logger.info(f"  [{test_case['id']}] {question[:60]}...")

        # Retrieve
        start = time.time()
        chunks = self.retrieve(question)
        retrieval_time = time.time() - start

        # Generate
        start = time.time()
        result = self.generate_answer(question, chunks)
        generation_time = time.time() - start

        answer = result["answer"]
        is_refusal = result["is_refusal"]

        # --- Compute Metrics ---

        # 1. Retrieval Precision@5: fraction of top-5 chunks relevant to the expected category
        precision_at_5 = 0.0
        if test_case["should_answer"] and chunks:
            relevant_count = 0
            for chunk in chunks[:5]:
                cat = chunk["metadata"].get("category", "")
                title = chunk["metadata"].get("title", "").lower()
                text_lower = chunk["text"].lower()
                # A chunk is relevant if it matches expected category or contains expected keywords
                has_keyword = any(kw in text_lower for kw in test_case["expected_keywords"])
                if has_keyword:
                    relevant_count += 1
            precision_at_5 = relevant_count / 5.0

        # 2. Retrieval Recall@10: fraction of expected keywords found in top-10 chunks
        recall_at_10 = 0.0
        if test_case["should_answer"] and chunks and test_case["expected_keywords"]:
            top10_text = " ".join([c["text"].lower() for c in chunks[:10]])
            found = sum(1 for kw in test_case["expected_keywords"] if kw in top10_text)
            recall_at_10 = found / len(test_case["expected_keywords"])

        # 3. Answer Accuracy: does the answer contain expected keywords?
        answer_accuracy = 0.0
        if test_case["should_answer"] and not is_refusal:
            answer_lower = answer.lower()
            found = sum(1 for kw in test_case["expected_keywords"] if kw in answer_lower)
            answer_accuracy = found / max(len(test_case["expected_keywords"]), 1)
        elif not test_case["should_answer"] and is_refusal:
            answer_accuracy = 1.0  # Correctly refused

        # 4. Faithfulness: check answer doesn't contain hallucination markers
        faithfulness = 1.0
        if not is_refusal:
            hallucination_markers = [
                "I think", "I believe", "probably", "might be",
                "I'm not sure but", "as far as I know",
                "generally speaking", "in my opinion",
            ]
            answer_lower = answer.lower()
            hallucination_count = sum(1 for m in hallucination_markers if m in answer_lower)
            if hallucination_count > 0:
                faithfulness = max(0, 1.0 - (hallucination_count * 0.25))

        # 5. Citation Accuracy: do URLs in the answer match URLs in retrieved chunks?
        citation_accuracy = 1.0
        if not is_refusal:
            urls_in_answer = re.findall(r'https?://[^\s\)]+', answer)
            chunk_urls = [c["metadata"].get("url", "") for c in chunks[:10]]
            if urls_in_answer:
                valid = sum(1 for u in urls_in_answer if any(u.rstrip('/') in cu for cu in chunk_urls))
                citation_accuracy = valid / len(urls_in_answer)
            else:
                citation_accuracy = 0.5  # No citations provided (penalize slightly)

        # 6. Refusal Appropriateness
        refusal_correct = False
        if test_case["should_answer"] and not is_refusal:
            refusal_correct = True  # Correctly answered
        elif not test_case["should_answer"] and is_refusal:
            refusal_correct = True  # Correctly refused
        elif not test_case["should_answer"] and not is_refusal:
            refusal_correct = False  # Should have refused but didn't
        else:
            refusal_correct = False  # Refused when should have answered

        # 7. Response time
        total_time = retrieval_time + generation_time

        return {
            "id": test_case["id"],
            "category": test_case["category"],
            "question": question,
            "should_answer": test_case["should_answer"],
            "did_answer": not is_refusal,
            "answer_preview": answer[:200],
            "retrieval_time_sec": round(retrieval_time, 3),
            "generation_time_sec": round(generation_time, 3),
            "total_time_sec": round(total_time, 3),
            "top_similarity": round(chunks[0]["similarity"], 4) if chunks else 0,
            "metrics": {
                "precision_at_5": round(precision_at_5, 3),
                "recall_at_10": round(recall_at_10, 3),
                "answer_accuracy": round(answer_accuracy, 3),
                "faithfulness": round(faithfulness, 3),
                "citation_accuracy": round(citation_accuracy, 3),
                "refusal_appropriate": refusal_correct,
            },
        }

    def run_evaluation(self):
        """Run full evaluation suite."""
        logger.info(f"Running evaluation on {len(GOLDEN_QUESTIONS)} questions...")
        logger.info(f"Collection size: {self.collection.count()} chunks")
        logger.info("=" * 70)

        results = []
        for test_case in GOLDEN_QUESTIONS:
            try:
                result = self.evaluate_single(test_case)
                results.append(result)
            except Exception as e:
                logger.error(f"  [{test_case['id']}] FAILED: {e}")
                results.append({
                    "id": test_case["id"],
                    "category": test_case["category"],
                    "question": test_case["question"],
                    "error": str(e),
                    "metrics": {
                        "precision_at_5": 0, "recall_at_10": 0,
                        "answer_accuracy": 0, "faithfulness": 0,
                        "citation_accuracy": 0, "refusal_appropriate": False,
                    },
                })

        return results

    def compute_aggregate_metrics(self, results):
        """Compute overall and per-category metrics."""
        valid = [r for r in results if "error" not in r]
        answerable = [r for r in valid if r["should_answer"]]
        out_of_domain = [r for r in valid if not r["should_answer"]]

        def avg(values):
            return round(sum(values) / max(len(values), 1), 3)

        aggregate = {
            "total_questions": len(GOLDEN_QUESTIONS),
            "successful_evaluations": len(valid),
            "errors": len(results) - len(valid),
            "overall_metrics": {
                "retrieval_precision_at_5": avg([r["metrics"]["precision_at_5"] for r in answerable]),
                "retrieval_recall_at_10": avg([r["metrics"]["recall_at_10"] for r in answerable]),
                "answer_accuracy": avg([r["metrics"]["answer_accuracy"] for r in valid]),
                "faithfulness": avg([r["metrics"]["faithfulness"] for r in valid]),
                "citation_accuracy": avg([r["metrics"]["citation_accuracy"] for r in answerable]),
                "refusal_appropriateness": avg([1.0 if r["metrics"]["refusal_appropriate"] else 0.0 for r in valid]),
            },
            "performance": {
                "avg_retrieval_time_sec": avg([r.get("retrieval_time_sec", 0) for r in valid]),
                "avg_generation_time_sec": avg([r.get("generation_time_sec", 0) for r in valid]),
                "avg_total_time_sec": avg([r.get("total_time_sec", 0) for r in valid]),
                "avg_top_similarity": avg([r.get("top_similarity", 0) for r in valid]),
            },
            "refusal_stats": {
                "out_of_domain_correctly_refused": sum(1 for r in out_of_domain if r["metrics"]["refusal_appropriate"]),
                "out_of_domain_total": len(out_of_domain),
                "in_domain_incorrectly_refused": sum(1 for r in answerable if not r["did_answer"]),
                "in_domain_total": len(answerable),
            },
        }

        # Per-category breakdown
        categories = set(r["category"] for r in valid)
        category_metrics = {}
        for cat in sorted(categories):
            cat_results = [r for r in valid if r["category"] == cat]
            category_metrics[cat] = {
                "count": len(cat_results),
                "precision_at_5": avg([r["metrics"]["precision_at_5"] for r in cat_results]),
                "recall_at_10": avg([r["metrics"]["recall_at_10"] for r in cat_results]),
                "answer_accuracy": avg([r["metrics"]["answer_accuracy"] for r in cat_results]),
                "faithfulness": avg([r["metrics"]["faithfulness"] for r in cat_results]),
            }
        aggregate["per_category"] = category_metrics

        return aggregate


def print_report(results, aggregate):
    """Print a formatted evaluation report."""
    print("\n" + "=" * 70)
    print("  UC RAG CHATBOT — EVALUATION REPORT")
    print("=" * 70)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Questions: {aggregate['total_questions']} | Successful: {aggregate['successful_evaluations']} | Errors: {aggregate['errors']}")
    print("=" * 70)

    print("\n  OVERALL METRICS")
    print("  " + "-" * 50)
    m = aggregate["overall_metrics"]
    print(f"  Retrieval Precision@5:    {m['retrieval_precision_at_5']:.1%}")
    print(f"  Retrieval Recall@10:      {m['retrieval_recall_at_10']:.1%}")
    print(f"  Answer Accuracy:          {m['answer_accuracy']:.1%}")
    print(f"  Faithfulness:             {m['faithfulness']:.1%}")
    print(f"  Citation Accuracy:        {m['citation_accuracy']:.1%}")
    print(f"  Refusal Appropriateness:  {m['refusal_appropriateness']:.1%}")

    print("\n  PERFORMANCE")
    print("  " + "-" * 50)
    p = aggregate["performance"]
    print(f"  Avg Retrieval Time:  {p['avg_retrieval_time_sec']:.3f}s")
    print(f"  Avg Generation Time: {p['avg_generation_time_sec']:.3f}s")
    print(f"  Avg Total Time:      {p['avg_total_time_sec']:.3f}s")
    print(f"  Avg Top Similarity:  {p['avg_top_similarity']:.4f}")

    print("\n  REFUSAL ANALYSIS")
    print("  " + "-" * 50)
    r = aggregate["refusal_stats"]
    print(f"  Out-of-domain correctly refused: {r['out_of_domain_correctly_refused']}/{r['out_of_domain_total']}")
    print(f"  In-domain incorrectly refused:   {r['in_domain_incorrectly_refused']}/{r['in_domain_total']}")

    print("\n  PER-CATEGORY BREAKDOWN")
    print("  " + "-" * 50)
    print(f"  {'Category':<15} {'Count':<6} {'P@5':<8} {'R@10':<8} {'Accuracy':<10} {'Faithful':<10}")
    print("  " + "-" * 50)
    for cat, cm in aggregate["per_category"].items():
        print(f"  {cat:<15} {cm['count']:<6} {cm['precision_at_5']:<8.1%} {cm['recall_at_10']:<8.1%} {cm['answer_accuracy']:<10.1%} {cm['faithfulness']:<10.1%}")

    print("\n  INDIVIDUAL RESULTS")
    print("  " + "-" * 50)
    for r in results:
        if "error" in r:
            status = "ERROR"
        elif r["metrics"]["refusal_appropriate"]:
            status = "PASS"
        else:
            status = "FAIL"
        print(f"  [{status:5}] {r['id']:<8} acc={r['metrics'].get('answer_accuracy', 0):.2f}  {r['question'][:55]}")

    print("\n" + "=" * 70)


def main():
    evaluator = RAGEvaluator()
    results = evaluator.run_evaluation()
    aggregate = evaluator.compute_aggregate_metrics(results)

    print_report(results, aggregate)

    # Save results to JSON
    output = {
        "timestamp": datetime.now().isoformat(),
        "aggregate": aggregate,
        "results": results,
    }
    output_path = Path("evaluation_results.json")
    output_path.write_text(json.dumps(output, indent=2, default=str))
    logger.info(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()