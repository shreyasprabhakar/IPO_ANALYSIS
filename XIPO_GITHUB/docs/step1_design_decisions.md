# Step 1 -- Design Decisions and Trade-offs

This document explains the reasoning behind each major technical decision in
the XIPO project. For each decision, the chosen approach is stated, the
alternatives that were considered are listed, and the trade-offs are discussed.

---

## 1. Why FastAPI Over Flask or Django?

**Chosen:** FastAPI with uvicorn.

**Reasoning:**

- FastAPI auto-generates an OpenAPI (Swagger) UI at `/docs`. This was critical
  during development because every new endpoint could be tested immediately
  from a browser without writing a separate client or cURL commands.
- Pydantic request models provide automatic validation and clear error messages
  when a required field is missing or has the wrong type.
- FastAPI supports both sync and async handlers. All XIPO handlers are
  synchronous (blocking I/O to Ollama, file system, SEBI), which FastAPI
  handles correctly by running them in a thread pool.

**Alternatives considered:**

| Alternative | Why rejected                                                 |
|-------------|--------------------------------------------------------------|
| Flask       | No built-in request validation, no auto-generated docs       |
| Django      | Too heavyweight for a REST API; ORM not needed (no database) |
| Express.js  | Would require rewriting all Python ML/NLP logic              |

**Trade-off:** FastAPI's main limitation is that it is Python-only, which can
be slower than compiled alternatives for CPU-bound tasks. In XIPO, the
bottleneck is always the LLM inference (Ollama), not the framework itself.

---

## 2. Why Streamlit Over React or Next.js?

**Chosen:** Streamlit single-file frontend.

**Reasoning:**

- Streamlit produces a functional UI from pure Python with no HTML, CSS, or
  JavaScript required. This kept the frontend as a single file (`app.py`,
  ~400 lines).
- Built-in widgets (`st.text_input`, `st.button`, `st.expander`,
  `st.spinner`) match exactly the interaction patterns XIPO needs.
- Hot-reload on save accelerated iteration during development.

**Alternatives considered:**

| Alternative | Why rejected                                                     |
|-------------|------------------------------------------------------------------|
| React       | Requires a build toolchain (webpack/vite), state management library, and HTTP client setup |
| Next.js     | Server-side rendering adds complexity not needed for a local tool |
| Gradio      | Better for ML demos, less flexible for multi-section dashboards  |

**Trade-off:** Streamlit reruns the entire script on every interaction. This
means network calls to the backend can be re-triggered unintentionally. XIPO
mitigates this with `st.session_state` guards and an `is_analyzing` flag.

---

## 3. Why FAISS Over ChromaDB, Pinecone, or Elasticsearch?

**Chosen:** FAISS with `IndexFlatL2` (exact L2 brute-force search).

**Reasoning:**

- FAISS runs entirely in-process with no server to install or manage. A single
  `pip install faiss-cpu` is sufficient.
- For the typical RHP document (300--600 pages, 200--800 chunks), brute-force
  L2 search over 384-dimensional vectors completes in under 10 milliseconds.
  Approximate nearest neighbour (ANN) indices are unnecessary at this scale.
- FAISS indices serialise to a single binary file, making per-company storage
  trivial.

**Alternatives considered:**

| Alternative     | Why rejected                                                  |
|-----------------|---------------------------------------------------------------|
| ChromaDB        | Adds a separate server process and dependency                 |
| Pinecone        | Cloud-hosted, requires API key, adds latency and cost         |
| Elasticsearch   | Requires JVM, heavy setup, overkill for <1000 vectors         |
| Weaviate        | Docker dependency, complex for a local-only tool              |

**Trade-off:** `IndexFlatL2` does not support filtering, metadata queries, or
incremental updates. XIPO compensates by storing metadata in a parallel JSON
file and rebuilding the index from scratch when needed (which takes only a few
seconds for typical document sizes).

---

## 4. Why Ollama (Local LLM) Over Cloud APIs?

**Chosen:** Ollama running `llama3:8b` locally.

**Reasoning:**

- No API keys, no per-token billing, no usage limits. XIPO can run fully
  offline after initial model download.
- IPO prospectuses contain sensitive financial data. Local inference ensures
  nothing leaves the user's machine.
- Ollama provides a simple REST API (`/api/generate`) that mirrors the
  interface of cloud LLM APIs, making it easy to swap later if needed.

**Alternatives considered:**

| Alternative    | Why rejected                                               |
|----------------|------------------------------------------------------------|
| OpenAI GPT-4   | Costs money per token, requires internet, data leaves machine |
| Cerebras API   | Free but rate-limited, external dependency                 |
| Hugging Face   | Requires manual model loading, GPU management, no REST API |

**Trade-off:** Local inference on CPU is significantly slower than cloud APIs.
A single report generation (7 LLM calls) can take 3--5 minutes on a typical
laptop. XIPO addresses this with 300-second timeouts and automatic retries.

---

## 5. Why difflib Over Dedicated Fuzzy Matching Libraries?

**Chosen:** `difflib.SequenceMatcher` with custom boosts.

**Reasoning:**

- `difflib` is part of the Python standard library. No additional dependency
  is needed.
- Company name matching is a relatively simple task: the candidate pool per
  SEBI page is 25 entries, and the total pool is at most 250 (10 pages).
  `SequenceMatcher` handles this efficiently.
- Custom boosts (substring matching, token overlap) were added to handle edge
  cases like partial queries ("Zomato" matching "Zomato Limited - RHP").

**Alternatives considered:**

| Alternative      | Why rejected                                              |
|------------------|-----------------------------------------------------------|
| FuzzyWuzzy       | External dependency; wraps `difflib` anyway               |
| RapidFuzz        | C extension, harder to install on some platforms          |
| Elasticsearch    | Would require a full search engine for a simple task      |

**Trade-off:** `SequenceMatcher` can produce false positives when company names
are very short (2--3 characters). XIPO mitigates this by requiring a minimum
score of 0.65 and only considering RHP/DRHP document types.

---

## 6. Why Regex Over NLP for Financial Extraction?

**Chosen:** Pattern-based regex extraction with `_first_number_after()`.

**Reasoning:**

- Financial metrics in RHP documents follow predictable textual patterns
  ("Revenue from Operations", "Profit After Tax", "Total Assets").
- Regex extraction is deterministic, auditable, and requires zero model
  inference. Each extracted value can be traced back to the exact pattern
  that matched.
- No dependency on spaCy, Transformers, or other NLP libraries.

**Alternatives considered:**

| Alternative         | Why rejected                                            |
|---------------------|---------------------------------------------------------|
| Named Entity Recognition (NER) | Requires training data specific to Indian financial docs |
| LLM-based extraction | Slow, non-deterministic, expensive for structured data  |
| Table extraction    | RHP tables vary widely in format; brittle to parse      |

**Trade-off:** Regex patterns are brittle. If a prospectus uses an unusual
phrasing ("Income from Business Operations" instead of "Revenue from
Operations"), the pattern will miss it and the metric will be `null`. XIPO
handles missing metrics gracefully by returning `null` and noting the gap in
`extraction_notes`.

---

## 7. Why Percentile Ranking Over a Trained ML Model for Health Score?

**Chosen:** Percentile rank against a training dataset, averaged across
available features.

**Reasoning:**

- Percentile ranking is fully transparent. A score of 75 means "this company's
  metrics are better than 75% of companies in the same sector." There is no
  black-box model to explain.
- The training dataset (`ipo_training_data_scored.json`, ~68 companies)
  provides real sector benchmarks.
- When a sector match is not found, the system falls back to a GLOBAL
  comparison without failing.

**Alternatives considered:**

| Alternative          | Why rejected                                            |
|----------------------|---------------------------------------------------------|
| Random Forest        | Requires labelled training data (good/bad IPOs); subjective |
| Neural network       | Overkill; hard to interpret; requires GPU for training   |
| Simple threshold     | Does not account for sector-specific norms               |

**Trade-off:** The health score depends entirely on the quality and
representativeness of the training dataset. If the dataset skews toward a
particular sector, scores for underrepresented sectors will rely on the GLOBAL
fallback, which is less precise.

---

## 8. Why SentenceTransformers (`all-MiniLM-L6-v2`) Over Other Embedding Models?

**Chosen:** `all-MiniLM-L6-v2` from the SentenceTransformers library.

**Reasoning:**

- 384-dimensional output keeps FAISS index files small (~150 KB per company).
- The model size is approximately 80 MB, making it fast to download and load.
- The model is optimised for semantic similarity, which is the exact use case
  for RAG retrieval.
- Inference is fast on CPU (sub-second for a batch of 500 chunks).

**Alternatives considered:**

| Alternative            | Why rejected                                          |
|------------------------|-------------------------------------------------------|
| OpenAI `text-embedding-ada-002` | Requires API key, costs money, 1536-dim vectors |
| `all-mpnet-base-v2`    | Better quality but 2x slower, 768-dim (larger indices) |
| BGE-small              | Comparable quality but less community adoption        |

**Trade-off:** `MiniLM-L6-v2` sacrifices some embedding quality for speed.
In practice, retrieval quality is sufficient because RHP text is domain-specific
and queries are short, focused questions about concrete topics.

---

## 9. Why Flat Files Over a Database?

**Chosen:** JSON and TXT files on the local file system.

**Reasoning:**

- XIPO is a single-user, local-first tool. There is no concurrent access
  pattern that requires transactional guarantees.
- JSON files are human-readable and can be inspected directly for debugging.
- No database setup, migration, or connection management is needed.

**Alternatives considered:**

| Alternative  | Why rejected                                                 |
|--------------|--------------------------------------------------------------|
| SQLite       | Adds schema management; JSON blob storage is less ergonomic  |
| PostgreSQL   | Requires a separate server; overkill for single-user         |
| MongoDB      | External dependency; no clear benefit over flat JSON files   |

**Trade-off:** Flat files do not support concurrent writes safely. If two
instances of the backend run simultaneously and write to the same file, data
could be corrupted. For a single-user tool, this risk is acceptable.

---

## 10. Summary of Key Trade-offs

| Decision         | Gained                         | Sacrificed                         |
|------------------|--------------------------------|------------------------------------|
| Local LLM        | Privacy, no cost, offline use  | Speed (3--5 min per report)        |
| FAISS brute-force| Simplicity, no server          | No metadata filtering              |
| Regex extraction | Transparency, speed            | Recall on unusual document formats |
| Percentile score | Interpretability               | Accuracy without broad training data |
| Flat files       | Zero setup, human-readable     | No concurrent write safety         |
| Streamlit        | Rapid development              | Limited UI customisation           |
