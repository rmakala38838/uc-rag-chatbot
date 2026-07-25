"""
RAG Chatbot Evaluation Suite — LLM-as-Judge
50 golden question-answer pairs sourced directly from UC Cumberlands documents.
Uses Claude (via Bedrock) as an evaluator to score each response on multiple dimensions.
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
# 50 GOLDEN TEST CASES — Questions + Expected Answers from actual UC documents
# ============================================================

GOLDEN_TESTS = [
    # --- ADMISSION & APPLICATION (10) ---
    {
        "id": "ADM-01",
        "category": "Admissions",
        "question": "What GPA is required for undergraduate admission?",
        "expected_answer": "Students with 0-11 hours of college credit must submit an official high school transcript showing a cumulative GPA of at least 2.0 on a 4.0 scale.",
        "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements",
    },
    {
        "id": "ADM-02",
        "category": "Admissions",
        "question": "What is the minimum GPA for graduate program admission?",
        "expected_answer": "Master's degree admission requires a grade point average of at least 2.5 on a 4.0 scale from a bachelor's degree. Doctoral degree admission requires at least 3.0 on a 4.0 scale from the conferred master's degree.",
        "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements",
    },
    {
        "id": "ADM-03",
        "category": "Admissions",
        "question": "What English proficiency tests are accepted for international students?",
        "expected_answer": "UC accepts TOEFL (minimum 65 internet-based, updating to 4 on new scale in January 2026), IELTS (minimum 6), DuoLingo (minimum 95 for undergrad, 100 for graduate), ACT (minimum 17), and SAT (minimum 920).",
        "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements",
    },
    {
        "id": "ADM-04",
        "category": "Admissions",
        "question": "How many countries do international students come from at UC?",
        "expected_answer": "University of the Cumberlands welcomes international students from over 40 countries in both undergraduate and select graduate programs.",
        "source_url": "https://www.ucumberlands.edu/admissions/international-students",
    },
    {
        "id": "ADM-05",
        "category": "Admissions",
        "question": "What documents do international undergraduate students need for admission?",
        "expected_answer": "International undergraduates need to complete the Cumberlands application, prepare transcript evaluation and translation, provide English proficiency scores, pay enrollment deposit, complete I-20 request form through UC Global with bank statement showing sufficient funding, and pay the SEVIS I-901 fee.",
        "source_url": "https://www.ucumberlands.edu/admissions/international-students",
    },
    {
        "id": "ADM-06",
        "category": "Admissions",
        "question": "What transcript evaluation services does UC accept?",
        "expected_answer": "UC accepts evaluations from World Education Services (WES), International Education Research Foundation (IERF), Educational Perspectives (EP), Educational Credential Evaluators (ECE), PLAYNAIA InCRED for student-athletes, and TEC.",
        "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements",
    },
    {
        "id": "ADM-07",
        "category": "Admissions",
        "question": "What is the mailing address for graduate admissions at UC?",
        "expected_answer": "University of the Cumberlands, Graduate Admissions, 6178 College Station Drive, Williamsburg, KY 40769.",
        "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements",
    },
    {
        "id": "ADM-08",
        "category": "Admissions",
        "question": "Can a student who was suspended from a program apply to a new program at UC?",
        "expected_answer": "No. If a student has been on probation for more than one semester in an unfinished program or has been suspended from a program at UC or any other institution, the student cannot be admitted into a new program at University of the Cumberlands.",
        "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements",
    },
    {
        "id": "ADM-09",
        "category": "Admissions",
        "question": "Are high school transcripts required for transfer students with 12+ credits?",
        "expected_answer": "No. High school transcripts are not required for students who have obtained 12+ hours of college credit after graduating high school.",
        "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements",
    },
    {
        "id": "ADM-10",
        "category": "Admissions",
        "question": "What GPA is required for PhD in Counselor Education and Supervision (PhD CES)?",
        "expected_answer": "The PhD CES program requires a 3.5 GPA for admission, which is higher than the standard 3.0 requirement for other doctoral programs.",
        "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements",
    },

    # --- ACADEMIC PROGRAMS (10) ---
    {
        "id": "ACAD-01",
        "category": "Academics",
        "question": "How many credit hours is the MSIT program?",
        "expected_answer": "The online Master of Science in Information Technology requires 31 credit hours.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-02",
        "category": "Academics",
        "question": "What is the cost per credit hour for the MSIT program?",
        "expected_answer": "The MSIT program costs $355 per credit hour.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-03",
        "category": "Academics",
        "question": "What courses are included in the MSIT curriculum?",
        "expected_answer": "The MSIT curriculum includes ITS 530 - Analyzing and Visualizing Data, ITS 531 - Business Intelligence, ITS 532 - Cloud Computing, and ITS 535 - System Analysis and Design among other courses totaling 31 credit hours.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-04",
        "category": "Academics",
        "question": "How long is each course term in the online MSIT program?",
        "expected_answer": "Each course lasts eight weeks, called a bi-term. There are two bi-terms per semester, and three semesters per year (fall, spring, and summer). Many classes are asynchronous.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-05",
        "category": "Academics",
        "question": "What is the maximum class size for the MSIT program?",
        "expected_answer": "The maximum class size for the MSIT program is 30 students.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-06",
        "category": "Academics",
        "question": "Is the MSIT program ranked nationally?",
        "expected_answer": "Yes, the MSIT program is ranked #1 in the U.S. for Affordable Master's programs.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-07",
        "category": "Academics",
        "question": "What topics does the MSIT program cover?",
        "expected_answer": "The MSIT covers cybersecurity, data analytics, IT management and leadership, cloud computing, business intelligence, data mining, systems management, strategic IT planning, and enterprise technology integration.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-08",
        "category": "Academics",
        "question": "Does UC provide textbooks for online students?",
        "expected_answer": "Yes, Cumberlands provides free rental textbooks to online students as part of its One Price Promise.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-09",
        "category": "Academics",
        "question": "What format is the MSIT delivered in?",
        "expected_answer": "The MSIT is a 100% online program. Classes are asynchronous, meaning there is no set login time and students can work on schoolwork whenever they find time.",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },
    {
        "id": "ACAD-10",
        "category": "Academics",
        "question": "What is the average financial aid for the MSIT program?",
        "expected_answer": "The average financial aid for the MSIT program is $10,400 (reported as $10.4K).",
        "source_url": "https://www.ucumberlands.edu/academics/graduate/masters-information-technology",
    },

    # --- TUITION & FINANCIAL AID (8) ---
    {
        "id": "FIN-01",
        "category": "Tuition & Aid",
        "question": "What is the undergraduate on-campus tuition at UC?",
        "expected_answer": "The undergraduate on-campus One Price Promise is $19,175 or less. Without housing it is $9,875. This includes parking, fees, academic resources, dining, housing, laundry, counseling, student health, books, library access, and technology fees.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/tuition",
    },
    {
        "id": "FIN-02",
        "category": "Tuition & Aid",
        "question": "What is the tuition per credit hour for online undergraduate programs?",
        "expected_answer": "The online undergraduate tuition is $220 per credit hour under the One Price Promise, which includes technology fees, academic resources, library access, counseling services, fees, and books.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/tuition",
    },
    {
        "id": "FIN-03",
        "category": "Tuition & Aid",
        "question": "What is the graduate tuition per credit hour?",
        "expected_answer": "The graduate tuition is $355 per credit hour on average under the One Price Promise.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/tuition",
    },
    {
        "id": "FIN-04",
        "category": "Tuition & Aid",
        "question": "What is included in the One Price Promise?",
        "expected_answer": "The One Price Promise includes everything: tuition, books, parking, fees, academic resources, dining, housing, laundry, counseling services, student health, library access, and technology fees. No hidden fees or extra costs.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/tuition",
    },
    {
        "id": "FIN-05",
        "category": "Tuition & Aid",
        "question": "How do I apply for financial aid at UC?",
        "expected_answer": "Students should complete the FAFSA (Free Application for Federal Student Aid) at studentaid.gov. If circumstances change, students can complete the Financial Assistance Form to have their aid offer reevaluated.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/financial-resources",
    },
    {
        "id": "FIN-06",
        "category": "Tuition & Aid",
        "question": "When was UC founded and what is its mission regarding affordability?",
        "expected_answer": "Since its founding in 1888, it's been Cumberlands' mission to serve the underserved and provide the financial resources students need. They aim to make UC affordable for every situation.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/financial-resources",
    },
    {
        "id": "FIN-07",
        "category": "Tuition & Aid",
        "question": "What circumstances qualify for financial aid reevaluation?",
        "expected_answer": "Circumstances that may qualify include personal or family loss of income, change in employment status, or other situations that have impacted financial security. Students must provide documentation to support their appeal.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/financial-resources",
    },
    {
        "id": "FIN-08",
        "category": "Tuition & Aid",
        "question": "Does UC offer external scholarships?",
        "expected_answer": "Yes, UC facilitates external scholarships which are private funded scholarships given to students by private donors, organizations, foundations and other outside sources. Recipients are chosen by the external agency and funds are distributed through the university.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/financial-resources",
    },

    # --- STUDENT LIFE (7) ---
    {
        "id": "LIFE-01",
        "category": "Student Life",
        "question": "How many clubs and organizations does UC have?",
        "expected_answer": "UC offers 29 different clubs and organizations for students to find their community.",
        "source_url": "https://www.ucumberlands.edu/student-life",
    },
    {
        "id": "LIFE-02",
        "category": "Student Life",
        "question": "What intramural sports are available at UC?",
        "expected_answer": "Students can enjoy intramural sports like flag football and basketball, or try outdoor activities like hiking.",
        "source_url": "https://www.ucumberlands.edu/student-life",
    },
    {
        "id": "LIFE-03",
        "category": "Student Life",
        "question": "What ministries are available for students?",
        "expected_answer": "Students can engage with various ministries including Appalachian Ministries and Fellowship of Christian Athletes.",
        "source_url": "https://www.ucumberlands.edu/student-life",
    },
    {
        "id": "LIFE-04",
        "category": "Student Life",
        "question": "What sections does Student Life at UC include?",
        "expected_answer": "Student Life includes Campus Guide, Clubs & Organizations, Community Service, Student Ministries, Civic Responsibility, Online Experience, Career Development, and Student Services.",
        "source_url": "https://www.ucumberlands.edu/student-life",
    },
    {
        "id": "LIFE-05",
        "category": "Student Life",
        "question": "Does UC support online students with a campus experience?",
        "expected_answer": "Yes, UC provides a fully online experience with courses accessible anytime, anywhere, designed for busy schedules.",
        "source_url": "https://www.ucumberlands.edu/student-life",
    },
    {
        "id": "LIFE-06",
        "category": "Student Life",
        "question": "What is UC's approach to campus community?",
        "expected_answer": "UC describes itself as a campus where students can be themselves. Whether athletic, artistic, or original, they value the individuality of students and aim to make campus feel like home.",
        "source_url": "https://www.ucumberlands.edu/student-life",
    },
    {
        "id": "LIFE-07",
        "category": "Student Life",
        "question": "Does UC offer career development services?",
        "expected_answer": "Yes, UC offers Career Development as part of Student Life, including workforce training, job search resources, and work study programs.",
        "source_url": "https://www.ucumberlands.edu/student-life",
    },

    # --- GENERAL / ABOUT (10) ---
    {
        "id": "GEN-01",
        "category": "General",
        "question": "Who is the president of University of the Cumberlands?",
        "expected_answer": "Dr. Quentin Young is the University President of the University of the Cumberlands.",
        "source_url": "https://www.ucumberlands.edu/about",
    },
    {
        "id": "GEN-02",
        "category": "General",
        "question": "What is UC's mission statement?",
        "expected_answer": "UC's mission is to provide a quality, affordable education to students from all backgrounds through broad-based academics. The institution is grounded in Christian principles and leadership through service.",
        "source_url": "https://www.ucumberlands.edu/about",
    },
    {
        "id": "GEN-03",
        "category": "General",
        "question": "What year was UC founded?",
        "expected_answer": "University of the Cumberlands was founded in 1888.",
        "source_url": "https://www.ucumberlands.edu/tuition-aid/financial-resources",
    },
    {
        "id": "GEN-04",
        "category": "General",
        "question": "What does UC mean by 'putting students first'?",
        "expected_answer": "UC provides every student with their own success coordinator for a personalized experience. They foster leadership through service, innovate constantly, cut tuition by 57% for accessibility, and have no hidden fees.",
        "source_url": "https://www.ucumberlands.edu/about",
    },
    {
        "id": "GEN-05",
        "category": "General",
        "question": "What are the three pillars of the Cumberlands Commitment?",
        "expected_answer": "The Cumberlands Commitment has three pillars: Affordable (One Price Promise with no hidden fees), Supported (investing in student success), and Distinctive (preparing students for next steps after graduation).",
        "source_url": "https://www.ucumberlands.edu/about",
    },
    {
        "id": "GEN-06",
        "category": "General",
        "question": "What is UC's campus size and location?",
        "expected_answer": "The University of the Cumberlands is located in Williamsburg, Kentucky, in the heart of Appalachia.",
        "source_url": "https://www.ucumberlands.edu/about",
    },
    {
        "id": "GEN-07",
        "category": "General",
        "question": "Does UC have a religious affiliation?",
        "expected_answer": "Yes, UC is grounded in Christian principles and values. The institution emphasizes leadership through service and fosters a community of faith.",
        "source_url": "https://www.ucumberlands.edu/about",
    },
    {
        "id": "GEN-08",
        "category": "General",
        "question": "How has UC addressed tuition affordability?",
        "expected_answer": "UC cut tuition by 57% and introduced the One Price Promise to make education accessible. The One Price Promise eliminates hidden fees and includes books, parking, technology fees, and other services.",
        "source_url": "https://www.ucumberlands.edu/about",
    },
    {
        "id": "GEN-09",
        "category": "General",
        "question": "What support does UC provide each student?",
        "expected_answer": "Every student at UC gets their own success coordinator who provides personalized guidance and support throughout their academic journey.",
        "source_url": "https://www.ucumberlands.edu/about",
    },
    {
        "id": "GEN-10",
        "category": "General",
        "question": "What does UC's 'Distinctive' commitment mean?",
        "expected_answer": "The Distinctive commitment means UC prepares students for the next step after graduation — whether that's a career, graduate school, or other goals. They focus on real-world readiness.",
        "source_url": "https://www.ucumberlands.edu/about",
    },

    # --- OUT-OF-DOMAIN / SHOULD REFUSE (5) ---
    {
        "id": "OOD-01",
        "category": "Out-of-Domain",
        "question": "What is the weather forecast for Tokyo this week?",
        "expected_answer": "REFUSE - This question is unrelated to UC Cumberlands.",
        "source_url": None,
    },
    {
        "id": "OOD-02",
        "category": "Out-of-Domain",
        "question": "Can you help me write a cover letter for a job at Google?",
        "expected_answer": "REFUSE - This question is unrelated to UC Cumberlands.",
        "source_url": None,
    },
    {
        "id": "OOD-03",
        "category": "Out-of-Domain",
        "question": "What is the capital of France?",
        "expected_answer": "REFUSE - This question is unrelated to UC Cumberlands.",
        "source_url": None,
    },
    {
        "id": "OOD-04",
        "category": "Out-of-Domain",
        "question": "Explain the theory of relativity.",
        "expected_answer": "REFUSE - This question is unrelated to UC Cumberlands.",
        "source_url": None,
    },
    {
        "id": "OOD-05",
        "category": "Out-of-Domain",
        "question": "What are the best restaurants near Harvard University?",
        "expected_answer": "REFUSE - This question is unrelated to UC Cumberlands.",
        "source_url": None,
    },
]


# ============================================================
# LLM-AS-JUDGE PROMPT
# ============================================================

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator for a university chatbot. You will be given:
1. A QUESTION asked by a user
2. The EXPECTED ANSWER (ground truth from official documents)
3. The ACTUAL ANSWER produced by the chatbot

Score the actual answer on these dimensions (each 1-5):

1. **Correctness** (1-5): Does the actual answer contain the same factual information as the expected answer? Are key facts, numbers, and details accurate?
2. **Completeness** (1-5): Does the actual answer cover the key points from the expected answer? Missing important details = lower score.
3. **Faithfulness** (1-5): Does the actual answer ONLY contain information that could be found on the UC website? Any hallucinated or made-up information = 1.
4. **Relevance** (1-5): Is the actual answer directly relevant to the question asked? Off-topic information = lower score.
5. **Citation Quality** (1-5): Does the answer include source URLs or links? Are they from ucumberlands.edu?

For OUT-OF-DOMAIN questions (expected = REFUSE), score:
- If chatbot refused/deflected appropriately: all scores = 5
- If chatbot answered anyway with UC-unrelated content: all scores = 1
- If chatbot answered with UC content tangentially related: Correctness=2, others=3

Respond ONLY with valid JSON in this exact format:
{"correctness": N, "completeness": N, "faithfulness": N, "relevance": N, "citation_quality": N, "reasoning": "one sentence explanation"}"""


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
        logger.info(f"Connected: {self.collection.count()} chunks in ChromaDB")

    def embed_query(self, query):
        return self.embedding_model.encode([query], normalize_embeddings=True)[0].tolist()

    def retrieve(self, query):
        results = self.collection.query(
            query_embeddings=[self.embed_query(query)],
            n_results=TOP_K,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        if results and results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
                chunks.append({"text": doc, "metadata": meta, "similarity": 1 - dist})
        return chunks

    def generate_answer(self, query, chunks):
        if not chunks or chunks[0]["similarity"] < RELEVANCE_THRESHOLD:
            return "I don't have enough information from the University of the Cumberlands website to answer this question. Please contact the relevant department or visit ucumberlands.edu for more details."

        context_parts = []
        for i, chunk in enumerate(chunks[:10], 1):
            meta = chunk["metadata"]
            source = f"[Source {i}: {meta.get('title', '')} | {meta.get('url', '')}]"
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
        return result["content"][0]["text"]

    def judge_answer(self, question, expected_answer, actual_answer):
        """Use LLM as judge to score the actual answer against expected."""
        prompt = f"""QUESTION: {question}

EXPECTED ANSWER (ground truth): {expected_answer}

ACTUAL ANSWER (from chatbot): {actual_answer}

Score the actual answer. Respond ONLY with JSON."""

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "system": JUDGE_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        })
        response = self.bedrock.invoke_model(modelId=LLM_MODEL, body=body)
        result = json.loads(response["body"].read())
        judge_text = result["content"][0]["text"].strip()

        try:
            if "```" in judge_text:
                judge_text = judge_text.split("```")[1]
                if judge_text.startswith("json"):
                    judge_text = judge_text[4:]
            scores = json.loads(judge_text)
        except json.JSONDecodeError:
            match = re.search(r'\{[^}]+\}', judge_text)
            if match:
                scores = json.loads(match.group())
            else:
                scores = {"correctness": 0, "completeness": 0, "faithfulness": 0, "relevance": 0, "citation_quality": 0, "reasoning": "Failed to parse judge response"}

        return scores

    def evaluate_single(self, test):
        """Evaluate a single test case end-to-end."""
        question = test["question"]
        expected = test["expected_answer"]
        logger.info(f"  [{test['id']}] {question[:55]}...")

        # Step 1: Retrieve
        t0 = time.time()
        chunks = self.retrieve(question)
        retrieval_time = time.time() - t0

        # Step 2: Generate
        t0 = time.time()
        actual_answer = self.generate_answer(question, chunks)
        generation_time = time.time() - t0

        # Step 3: Judge
        t0 = time.time()
        scores = self.judge_answer(question, expected, actual_answer)
        judge_time = time.time() - t0

        # Check if source URL was found in retrieved chunks
        source_found = False
        if test["source_url"] and chunks:
            for c in chunks[:10]:
                if test["source_url"] in c["metadata"].get("url", ""):
                    source_found = True
                    break

        return {
            "id": test["id"],
            "category": test["category"],
            "question": question,
            "expected_answer": expected,
            "actual_answer": actual_answer,
            "source_url": test["source_url"],
            "source_retrieved": source_found,
            "top_similarity": round(chunks[0]["similarity"], 4) if chunks else 0,
            "scores": scores,
            "timing": {
                "retrieval_sec": round(retrieval_time, 3),
                "generation_sec": round(generation_time, 3),
                "judge_sec": round(judge_time, 3),
                "total_sec": round(retrieval_time + generation_time + judge_time, 3),
            },
        }

    def run_evaluation(self):
        """Run full 50-question evaluation."""
        logger.info(f"Starting evaluation: {len(GOLDEN_TESTS)} questions")
        logger.info(f"ChromaDB: {self.collection.count()} chunks")
        logger.info(f"Judge model: {LLM_MODEL}")
        logger.info("=" * 70)

        results = []
        for test in GOLDEN_TESTS:
            try:
                result = self.evaluate_single(test)
                results.append(result)
                s = result["scores"]
                logger.info(f"    -> C={s.get('correctness',0)} F={s.get('faithfulness',0)} R={s.get('relevance',0)}")
            except Exception as e:
                logger.error(f"  [{test['id']}] ERROR: {e}")
                results.append({
                    "id": test["id"],
                    "category": test["category"],
                    "question": test["question"],
                    "error": str(e),
                    "scores": {"correctness": 0, "completeness": 0, "faithfulness": 0, "relevance": 0, "citation_quality": 0},
                })
        return results

    def compute_aggregate(self, results):
        """Compute aggregate metrics from judge scores."""
        valid = [r for r in results if "error" not in r]

        def avg_score(key):
            vals = [r["scores"].get(key, 0) for r in valid]
            return round(sum(vals) / max(len(vals), 1), 2)

        aggregate = {
            "total_questions": len(GOLDEN_TESTS),
            "evaluated": len(valid),
            "errors": len(results) - len(valid),
            "overall_scores": {
                "correctness": avg_score("correctness"),
                "completeness": avg_score("completeness"),
                "faithfulness": avg_score("faithfulness"),
                "relevance": avg_score("relevance"),
                "citation_quality": avg_score("citation_quality"),
                "average": round((avg_score("correctness") + avg_score("completeness") + avg_score("faithfulness") + avg_score("relevance") + avg_score("citation_quality")) / 5, 2),
            },
            "retrieval": {
                "source_retrieval_rate": round(sum(1 for r in valid if r.get("source_retrieved")) / max(sum(1 for r in valid if r.get("source_url")), 1), 3),
                "avg_top_similarity": round(sum(r.get("top_similarity", 0) for r in valid) / max(len(valid), 1), 4),
            },
            "timing": {
                "avg_retrieval_sec": round(sum(r["timing"]["retrieval_sec"] for r in valid) / max(len(valid), 1), 3),
                "avg_generation_sec": round(sum(r["timing"]["generation_sec"] for r in valid) / max(len(valid), 1), 3),
                "avg_total_sec": round(sum(r["timing"]["total_sec"] for r in valid) / max(len(valid), 1), 3),
            },
        }

        # Per-category breakdown
        categories = sorted(set(r["category"] for r in valid))
        per_cat = {}
        for cat in categories:
            cat_results = [r for r in valid if r["category"] == cat]
            per_cat[cat] = {
                "count": len(cat_results),
                "correctness": round(sum(r["scores"].get("correctness", 0) for r in cat_results) / len(cat_results), 2),
                "completeness": round(sum(r["scores"].get("completeness", 0) for r in cat_results) / len(cat_results), 2),
                "faithfulness": round(sum(r["scores"].get("faithfulness", 0) for r in cat_results) / len(cat_results), 2),
                "relevance": round(sum(r["scores"].get("relevance", 0) for r in cat_results) / len(cat_results), 2),
                "citation_quality": round(sum(r["scores"].get("citation_quality", 0) for r in cat_results) / len(cat_results), 2),
            }
        aggregate["per_category"] = per_cat

        return aggregate


def print_report(results, aggregate):
    """Print formatted evaluation report."""
    print("\n" + "=" * 75)
    print("  UC RAG CHATBOT — LLM-AS-JUDGE EVALUATION REPORT")
    print("=" * 75)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Questions: {aggregate['total_questions']} | Evaluated: {aggregate['evaluated']} | Errors: {aggregate['errors']}")
    print(f"  Judge Model: {LLM_MODEL}")
    print("=" * 75)

    print("\n  OVERALL SCORES (1-5 scale, LLM-judged)")
    print("  " + "-" * 55)
    s = aggregate["overall_scores"]
    print(f"  Correctness:      {s['correctness']}/5  {'|' * int(s['correctness'] * 4)}")
    print(f"  Completeness:     {s['completeness']}/5  {'|' * int(s['completeness'] * 4)}")
    print(f"  Faithfulness:     {s['faithfulness']}/5  {'|' * int(s['faithfulness'] * 4)}")
    print(f"  Relevance:        {s['relevance']}/5  {'|' * int(s['relevance'] * 4)}")
    print(f"  Citation Quality: {s['citation_quality']}/5  {'|' * int(s['citation_quality'] * 4)}")
    print(f"  ----------------------------")
    print(f"  OVERALL AVERAGE:  {s['average']}/5")

    print("\n  RETRIEVAL PERFORMANCE")
    print("  " + "-" * 55)
    r = aggregate["retrieval"]
    print(f"  Source Document Retrieved: {r['source_retrieval_rate']:.1%}")
    print(f"  Avg Top Similarity:        {r['avg_top_similarity']:.4f}")
    t = aggregate["timing"]
    print(f"  Avg Retrieval Time:        {t['avg_retrieval_sec']:.3f}s")
    print(f"  Avg Generation Time:       {t['avg_generation_sec']:.3f}s")
    print(f"  Avg Total Time:            {t['avg_total_sec']:.3f}s")

    print("\n  PER-CATEGORY SCORES")
    print("  " + "-" * 55)
    print(f"  {'Category':<16} {'#':<4} {'Correct':<9} {'Complete':<10} {'Faithful':<10} {'Relevant':<10} {'Citation'}")
    print("  " + "-" * 55)
    for cat, cm in aggregate["per_category"].items():
        print(f"  {cat:<16} {cm['count']:<4} {cm['correctness']:<9} {cm['completeness']:<10} {cm['faithfulness']:<10} {cm['relevance']:<10} {cm['citation_quality']}")

    print("\n  INDIVIDUAL RESULTS (avg score)")
    print("  " + "-" * 55)
    for r in results:
        if "error" in r:
            print(f"  [ERROR] {r['id']:<8} {r['question'][:50]}")
        else:
            s = r["scores"]
            avg = (s.get("correctness", 0) + s.get("completeness", 0) + s.get("faithfulness", 0) + s.get("relevance", 0) + s.get("citation_quality", 0)) / 5
            src = "Y" if r.get("source_retrieved") else "N"
            print(f"  [{avg:.1f}/5] {r['id']:<8} src={src}  {r['question'][:48]}")

    print("\n" + "=" * 75)


def main():
    evaluator = RAGEvaluator()
    results = evaluator.run_evaluation()
    aggregate = evaluator.compute_aggregate(results)

    print_report(results, aggregate)

    # Save full results
    output = {
        "timestamp": datetime.now().isoformat(),
        "model": LLM_MODEL,
        "judge_model": LLM_MODEL,
        "aggregate": aggregate,
        "results": results,
    }
    Path("evaluation_results.json").write_text(json.dumps(output, indent=2, default=str))
    logger.info("Results saved to evaluation_results.json")


if __name__ == "__main__":
    main()