# Evaluation Framework — UC RAG Chatbot

## Overview

This project uses a **two-method evaluation approach** to rigorously test the RAG chatbot across 50 golden questions derived from actual University of the Cumberlands source documents. The evaluation measures both retrieval quality and generation accuracy.

- **Method 1**: Keyword-based automated metrics (fast, deterministic)
- **Method 2**: LLM-as-Judge using Claude Opus (nuanced, semantic understanding)

---

## Test Suite

### Golden Questions

50 question-answer pairs across 6 categories, with expected answers extracted verbatim or paraphrased from official UC web pages:

| Category | Count | Source Documents |
|----------|-------|-----------------|
| Admissions | 10 | admission-requirements.md, international-students.md |
| Academics | 10 | masters-information-technology.md |
| Tuition & Aid | 8 | tuition.md, financial-resources.md |
| Student Life | 7 | student-life.md |
| General / About | 10 | about.md |
| Out-of-Domain | 5 | None (should refuse) |

### Example Test Case

```json
{
  "id": "ADM-01",
  "category": "Admissions",
  "question": "What GPA is required for undergraduate admission?",
  "expected_answer": "Students with 0-11 hours of college credit must submit an official high school transcript showing a cumulative GPA of at least 2.0 on a 4.0 scale.",
  "source_url": "https://www.ucumberlands.edu/admissions/admission-requirements"
}
```

---

## Method 1: Keyword-Based Metrics

**Script**: `evaluation.py`

### Metrics Explained

| Metric | Definition | Result |
|--------|-----------|--------|
| **Precision@5** | Of the top-5 retrieved chunks, what fraction are relevant to the question? | 89.8% |
| **Recall@10** | Of all relevant chunks in the store, what fraction appear in the top-10 results? | 88.7% |
| **Answer Accuracy** | Does the generated answer contain expected keywords from the ground truth? | 73.6% |
| **Faithfulness** | Does the answer avoid hallucination (only uses retrieved content)? | 100% |
| **Refusal Appropriateness** | Does the system correctly refuse out-of-domain questions? | 90% |

#### Precision@5 (P@5) — Retrieval Quality

Precision@5 answers: "Of the top 5 chunks the system retrieved, how many are actually useful?"

- The RAG system queries ChromaDB and gets back ranked results
- We check the top 5 results against the expected source document
- If 4 out of 5 chunks are from the correct page → P@5 = 80%
- **Our result: 89.8%** means almost all top-5 results are relevant, minimal noise

This measures whether the retrieval is **precise** — not fetching irrelevant junk.

#### Recall@10 (R@10) — Retrieval Coverage

Recall@10 answers: "Of all the relevant chunks that exist for this question, how many did we find in the top 10?"

- For a question about MSIT tuition, there might be 5 relevant chunks in the entire 20,520-chunk database
- If 4 of those 5 appear in our top-10 results → R@10 = 80%
- **Our result: 88.7%** means the system finds most relevant information within 10 results

This measures whether the retrieval has good **coverage** — not missing important content.

#### Why P@5 and R@10 Use Different K Values

- P@5 uses a smaller window (5) because precision matters most at the very top — users see top results first
- R@10 uses a larger window (10) because we pass 10 chunks to the LLM — we want to ensure all relevant content reaches the generation stage
- Our system retrieves top-15, then passes top-10 to Claude for answer generation

### How It Works

1. For each question, retrieve top-K chunks from ChromaDB
2. Compare retrieved chunk metadata against the expected source URL (retrieval metrics)
3. Check if expected keywords appear in the generated answer (accuracy)
4. Verify no external/fabricated information is present (faithfulness)
5. For out-of-domain questions, verify the system refuses to answer

### Limitations

- Keyword matching is brittle: "GPA of 2.0" and "minimum grade point average is two" are semantically identical but won't match
- Cannot detect partial correctness or nuanced errors
- Binary scoring (present/absent) with no partial credit

---

## Method 2: LLM-as-Judge (Claude Opus)

**Script**: `evaluation_llm_judge.py`

### Architecture

```
Question ──> RAG System ──> Actual Answer ──┐
                                            ├──> Claude Opus Judge ──> Scores (JSON)
Expected Answer (ground truth) ─────────────┘
```

For each of the 50 questions:
1. **Retrieve**: Query ChromaDB for relevant chunks
2. **Generate**: Pass chunks to Claude Sonnet to produce an answer
3. **Judge**: Send (question, expected answer, actual answer) to Claude Opus for scoring

### Scoring Dimensions Explained

| Dimension | What It Measures | Overall Score |
|-----------|-----------------|---------------|
| **Correctness** | Are facts, numbers, and details accurate vs ground truth? | 80.8% |
| **Completeness** | Are all key points from the expected answer covered? | 76.4% |
| **Faithfulness** | Does the answer ONLY contain UC website information (no hallucination)? | 82.8% |
| **Relevance** | Is the answer directly on-topic for the question asked? | 87.2% |
| **Citation Quality** | Are ucumberlands.edu source URLs included and correct? | 84.0% |

#### Correctness (80.8%)

Are the facts right? The judge compares specific details — if the expected answer says "GPA of 2.0" and the chatbot says "GPA of 2.0", full marks. If it says "GPA of 2.5", penalized. This checks numbers, names, dates, and all factual claims against the ground truth document.

#### Completeness (76.4%)

Are all key points covered? If the expected answer mentions 3 important facts (e.g., TOEFL 65, IELTS 6, DuoLingo 95) and the chatbot only mentions TOEFL, it loses points. This is our weakest metric — the chatbot sometimes gives partial answers, especially for complex multi-part questions.

#### Faithfulness (82.8%)

Does the answer ONLY contain information from UC's website? This is the hallucination detector. If the chatbot invents a scholarship program, makes up a deadline, or adds information not found in any source document, faithfulness drops sharply. A score of 1/5 means significant hallucination was detected.

#### Relevance (87.2%)

Is the answer directly addressing what was asked? If a user asks about tuition and gets tuition info — high score. If they get a wall of text about campus life with tuition buried somewhere — lower score. This catches cases where retrieval pulls tangentially related content.

#### Citation Quality (84.0%)

Does the response include clickable source URLs from ucumberlands.edu? Are the URLs actually relevant to the answer content? A response with proper `[link text](https://ucumberlands.edu/...)` citations pointing to the correct page scores high. Missing or broken links reduce this score.

### Judge Prompt

The judge receives a system prompt instructing it to:
- Compare the actual answer against ground truth on all 5 dimensions
- Score each dimension 1-5 (converted to percentage: score/5 * 100)
- For out-of-domain questions, award full marks if the chatbot refused appropriately
- Return structured JSON for deterministic parsing

### Out-of-Domain Scoring

For questions unrelated to UC (weather, cover letters, general knowledge):
- Chatbot **refuses appropriately** → all dimensions score 100%
- Chatbot **answers with UC-unrelated content** → all dimensions score 20%
- Chatbot **answers with tangentially related UC content** → partial credit

---

## Per-Category Results (LLM-as-Judge)

| Category | Correct | Complete | Faithful | Relevant | Citation |
|----------|---------|----------|----------|----------|----------|
| Admissions (10) | 70% | 70% | 76% | 84% | 84% |
| Academics (10) | 66% | 68% | 80% | 82% | 78% |
| Tuition & Aid (8) | 85% | 88% | 88% | 98% | 95% |
| Student Life (7) | 71% | 77% | 86% | 91% | 89% |
| General (10) | 76% | 78% | 86% | 90% | 78% |
| Out-of-Domain (5) | 76% | 84% | 84% | 76% | 84% |

### Observations

- **Tuition & Aid** scores highest across all dimensions — these pages have structured, specific data that retrieves well
- **Academics** scores lowest on correctness/completeness — the MSIT page content is spread across many chunks, making full retrieval harder
- **Faithfulness** is consistently high (76-88%) — the system rarely hallucates
- **Out-of-Domain** refusal works for 3/5 questions but 2 still get answered with tangentially related UC content

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Source document retrieval rate | 68.9% |
| Average top similarity score | 0.7109 |
| Average retrieval time | 0.079 sec |
| Average generation time | 3.7 sec |
| Average total time (incl. judge) | 6.1 sec |
| Tests completed | 50/50 |
| Errors | 0 |

---

## Why Two Methods?

| Aspect | Keyword-Based | LLM-as-Judge |
|--------|--------------|--------------|
| Speed | Fast (~4.5 sec/question) | Slower (~6.1 sec, extra API call) |
| Cost | 1 LLM call per question | 2 LLM calls per question |
| Accuracy | Misses paraphrases | Understands semantic equivalence |
| Granularity | Binary (pass/fail) | 5 scored dimensions with reasoning |
| Hallucination detection | Basic (keyword absence) | Sophisticated (cross-reference check) |
| Reproducibility | 100% deterministic | ~95% (minor LLM variance) |

### The Core Problem with Keywords

Keyword matching is brittle. Consider these equivalent statements:

- Expected: "GPA of 2.0"
- Actual response: "minimum grade point average is two-point-zero on a four-point scale"

A keyword check for "2.0" would **fail** even though the answer is semantically correct. The LLM-as-Judge understands paraphrasing, synonyms, and equivalent phrasings — it evaluates meaning, not string matching.

### When Each Method Shines

**Keyword-based** is best for:
- Quick smoke tests during development
- CI/CD pipeline checks (fast, deterministic, no API cost)
- Catching regressions where specific data points disappear

**LLM-as-Judge** is best for:
- Final evaluation before release
- Detecting subtle issues (partial answers, irrelevant context mixed in)
- Understanding WHY something scored low (judge provides reasoning)
- Evaluating open-ended responses that can be phrased many ways

Using both methods provides confidence: keyword metrics give a fast baseline, while LLM-as-Judge provides the nuanced evaluation that matches how a human would grade the responses.

---

## Running the Evaluation

### Prerequisites

- ChromaDB running on localhost:8000 with ingested data
- AWS credentials configured for Bedrock access
- Python environment with dependencies installed

### Keyword-Based Evaluation

```bash
python evaluation.py
```

### LLM-as-Judge Evaluation

```bash
python evaluation_llm_judge.py
```

### Output

Both scripts save results to `evaluation_results.json` with:
- Aggregate scores across all dimensions
- Per-category breakdown
- Individual question results with actual answers
- Timing information
- Judge reasoning for each score (LLM method only)

---

## References

- Lewis, P. et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS.
- Zheng, L. et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. arXiv:2306.05685.
- Es, S. et al. (2023). RAGAS: Automated Evaluation of Retrieval Augmented Generation. arXiv:2309.15217.