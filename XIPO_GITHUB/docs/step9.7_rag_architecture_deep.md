# Step 9.7 -- RAG Architecture Deep Dive

## 1. What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that combines information
retrieval with language model generation. Instead of relying solely on a
language model's training data, RAG first retrieves relevant passages from a
knowledge base and then passes them as context to the model.

In XIPO, the knowledge base is a company's RHP document, indexed per-chunk
in FAISS. The language model is Ollama (`llama3:8b`), running locally.

---

## 2. Why RAG Instead of Direct LLM Prompting?

| Approach                  | Limitation                                        |
|---------------------------|---------------------------------------------------|
| Feed entire RHP to LLM    | RHP is 300--600 pages; exceeds any LLM context window |
| Fine-tune LLM on RHP data | Expensive, requires GPU, not feasible per-company |
| Summarise then prompt     | Lossy; important details may be discarded         |
| **RAG (retrieve + generate)** | **Selects only the most relevant chunks; LLM sees focused context** |

RAG allows XIPO to answer specific questions about a 400-page document by
retrieving only the 6 most relevant chunks (~6000 characters) and passing
them to the LLM. This keeps the prompt within the model's context window
while preserving the specific details needed to answer the question.

---

## 3. End-to-End Data Flow

```
User Question
    |
    v
[1] Embed question using SentenceTransformer (all-MiniLM-L6-v2)
    --> 384-dimensional float vector
    |
    v
[2] FAISS similarity search (IndexFlatL2)
    --> Returns indices of top_k nearest chunk vectors
    |
    v
[3] Retrieve chunk texts from metadata JSON using returned indices
    --> 6 text passages, each 800-1200 characters
    |
    v
[4] Construct prompt:
    System instruction + Retrieved context + User question
    |
    v
[5] Send prompt to Ollama (/api/generate, model=llama3:8b)
    --> Returns generated answer text
    |
    v
[6] Format response (answer only, or answer + debug metadata)
    --> Return to frontend
```

---

## 4. Component Breakdown

### 4.1 Embedding Model

**Model:** `all-MiniLM-L6-v2` from the SentenceTransformers library.

| Property        | Value                                    |
|-----------------|------------------------------------------|
| Output dimension| 384                                      |
| Model size      | ~80 MB                                   |
| Speed (CPU)     | ~500 chunks/second                       |
| Architecture    | 6-layer MiniLM (distilled from BERT)     |
| Training task   | Semantic textual similarity              |

The same model is used at both indexing time (embedding document chunks) and
query time (embedding the user's question). This ensures that the vector space
is consistent -- similar meanings produce nearby vectors.

### 4.2 FAISS Index

**Index type:** `IndexFlatL2` -- exact brute-force L2 (Euclidean) distance.

The index stores all chunk embeddings as a flat matrix. Search computes the L2
distance between the query vector and every stored vector, then returns the
`top_k` closest results.

**Why L2 and not cosine similarity?**
`all-MiniLM-L6-v2` produces normalised vectors by default. For normalised
vectors, L2 distance and cosine distance produce identical rankings:

```
||a - b||^2  =  2 - 2 * cos(a, b)    (when ||a|| = ||b|| = 1)
```

Therefore, L2 search on normalised vectors is equivalent to cosine similarity
search.

**Index file structure per company:**

```
data/faiss/
  <company_name>.index     -- FAISS binary index (chunk embeddings)
  <company_name>_meta.json -- Array of {chunk_id, section, text, char_count}
```

The metadata JSON stores the full chunk text alongside each chunk's ID and
section header. This allows the RAG engine to retrieve the actual text without
re-reading the original chunks file.

### 4.3 Chunking Strategy

The chunker (`backend/app/services/chunker.py`) splits the extracted text with
the following parameters:

| Parameter              | Value  | Rationale                              |
|------------------------|--------|----------------------------------------|
| `MIN_CHUNK_SIZE`       | 800    | Ensures chunks have enough context     |
| `MAX_CHUNK_SIZE`       | 1200   | Keeps chunks within embedding model limits |
| `SECTION_HEADER_MAX_LENGTH` | 80 | Prevents paragraph text from being misidentified as a header |

**Section header detection heuristic:** A line is treated as a section header
if it is shorter than 80 characters and at least 80% of its alphabetic
characters are uppercase (e.g., "RISK FACTORS", "OBJECTS OF THE ISSUE").

When a section header is encountered:
1. The current chunk is saved with the previous section label.
2. The section label is updated to the new header.
3. A new chunk begins.

This means chunks within the same section share a section label, which can
be used for filtering or provenance tracking.

### 4.4 Prompt Engineering

The RAG prompt has three parts:

```
[System instruction]
You are a professional IPO analyst. Answer the user's question...
NEVER mention "chunks", "context", "FAISS", "embeddings"...
Simply state the facts as if you have expert knowledge...

[Retrieved context]
IPO Prospectus Information:
<chunk_1>
---
<chunk_2>
---
...

[User question]
Question: <user's question>
Answer:
```

Key design decisions in the prompt:

1. **Persona.** The model is instructed to behave as a professional IPO
   analyst, not a generic assistant. This produces more authoritative and
   structured responses.

2. **Anti-technical-jargon rule.** The prompt explicitly forbids mentioning
   RAG internals ("chunks", "FAISS", "embeddings", "context"). Without this
   rule, the model often says "Based on the provided context..." which breaks
   the illusion of expertise.

3. **Missing information handling.** The prompt instructs the model to
   explicitly state when information is not available, rather than
   hallucinating an answer.

4. **Chunk separator.** Chunks are separated by `\n\n---\n\n` to provide
   clear visual boundaries for the model.

### 4.5 Answer Generation

The answer is generated by calling the Ollama REST API:

```
POST http://localhost:11434/api/generate
{
  "model": "llama3:8b",
  "prompt": "<full prompt>",
  "stream": false
}
```

**Timeout and retry configuration:**

| Parameter | Default (Q&A) | Default (Report) | Rationale                    |
|-----------|---------------|-------------------|------------------------------|
| `timeout` | 60s           | 300s              | Report sections are longer   |
| `retries` | 0             | 1                 | Report has 7 calls; at least one may timeout |

When a timeout occurs, the engine waits 2 seconds before retrying. If all
attempts fail, a `RuntimeError` is raised with a descriptive message.

---

## 5. Debug Mode

The `debug` parameter controls the response format:

**`debug=false` (production):**
```json
{
  "company_name": "Zomato",
  "question": "What is the issue size?",
  "answer": "The total issue size is up to Rs. 9,375 crores."
}
```

**`debug=true` (development):**
```json
{
  "company_name": "Zomato",
  "question": "What is the issue size?",
  "answer": "The total issue size is up to Rs. 9,375 crores.",
  "sources": [
    {"chunk_id": 14, "section": "DETAILS OF THE ISSUE"},
    {"chunk_id": 15, "section": "DETAILS OF THE ISSUE"}
  ],
  "retrieved_chunks_count": 6,
  "retrieved_context_preview": "Type Fresh Issue Offer for Sale Total..."
}
```

The same prompt and model call are used in both modes. Debug mode only adds
metadata to the response; it does not change the answer quality.

---

## 6. Report Generation via RAG

The report generator (`backend/app/services/report_generator.py`) uses the RAG
engine to produce a structured 7-section IPO analysis report. It does this by
asking 7 predefined questions, one per section:

| Section              | Question Asked                                           |
|----------------------|----------------------------------------------------------|
| `company_overview`   | What does this company do?                               |
| `business_model`     | Explain the business model and revenue generation.       |
| `objects_of_issue`   | What are the objects of the issue?                        |
| `strengths`          | What are the key strengths and competitive advantages?   |
| `key_risks`          | What are the major risks and challenges?                 |
| `financial_highlights`| Summarize the key financial metrics.                    |
| `final_verdict`      | Provide a brief investment perspective (not advice).     |

Each question triggers a full RAG cycle (embed, retrieve, generate). The
report generator uses `timeout=300` and `retries=1` because generating 7
consecutive answers is resource-intensive and any single call may timeout.

---

## 7. Performance Characteristics

| Metric                       | Typical Value                  |
|------------------------------|--------------------------------|
| FAISS index build time       | 3--10 seconds (200--800 chunks)|
| Single RAG query latency     | 10--30 seconds (CPU inference) |
| Full report generation       | 2--5 minutes (7 RAG calls)     |
| Embedding dimension          | 384                            |
| Index file size              | 100--300 KB per company        |

---

## 8. Limitations

1. **No re-ranking.** FAISS retrieves the top-k chunks by embedding similarity
   only. A cross-encoder re-ranker could improve precision but would add
   latency.

2. **No conversation memory.** Each RAG call is stateless. The chatbot does
   not carry context from previous questions. Conversation history is managed
   solely on the frontend via `st.session_state.chat_history`.

3. **Fixed chunk sizes.** The 800--1200 character window may split a
   table or paragraph mid-sentence. Semantic chunking (splitting at natural
   boundaries) would improve retrieval quality.

4. **Single embedding model.** The same model is used for both short questions
   and long document chunks. A query-optimised model for questions and a
   passage model for chunks (bi-encoder asymmetry) could improve retrieval.

---

## 9. Viva Preparation: Key Questions

**Q: What is the difference between RAG and fine-tuning?**
A: Fine-tuning modifies the model's weights using domain-specific data. RAG
leaves the model unchanged and instead provides relevant context at inference
time. RAG is cheaper, faster to update (just rebuild the index), and does not
require GPU resources for training.

**Q: Why retrieve 6 chunks (top_k=6)?**
A: This is a balance between context richness and prompt length. Too few chunks
may miss relevant information; too many may confuse the model or exceed its
context window. The value 6 was chosen empirically.

**Q: How does the system handle questions about topics not in the RHP?**
A: The prompt instructs the model to explicitly state "This information is not
available in the IPO prospectus" when the retrieved context does not contain
the answer. However, hallucination is still possible if the model overrides
this instruction.

**Q: Could you use a different vector database?**
A: Yes. The retrieval interface is simple (embed query, search, return chunks).
Any vector store that supports L2 or cosine search could replace FAISS with
minimal code changes. FAISS was chosen for its zero-setup, in-process nature.
