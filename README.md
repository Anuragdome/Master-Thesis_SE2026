# Consensus-Based Knowledge Graph Construction from Unstructured Documents using Multiple Large Language Models for Hallucination Reduction

### Multi-LLM Consensus Knowledge Graph Pipeline
*MSc Thesis Project*

---

## What This Does

This pipeline takes raw documents (`.txt`, `.pdf`, `.html`) and builds a **Knowledge
Graph** stored in Neo4j — but instead of trusting a single LLM's extraction with a
self-reported confidence score, it uses **three independent LLMs** (Gemini, Llama
3.1 8B, Qwen 3 8B) that each build their own graph from the same text, then
**cross-verify each other's triples against the source text**. A fact only enters
the final graph if enough of the *other* models agree it is explicitly supported —
this **Agreement Score** completely replaces the old single-model confidence score
as the project's central, fully-explainable trust metric.

```
Input PDF
   │
   ▼
Text Extraction → Chunking
   │
   ├──────────────┬──────────────┐
   ▼              ▼              ▼
Gemini         Llama 3.1      Qwen 3
Extraction     Extraction     Extraction
   │              │              │
   ▼              ▼              ▼
Graph A        Graph B        Graph C     (three independent graphs — NOT merged)
   │              │              │
   └──────────────┴──────────────┘
                  ▼
          Triple Alignment
      (normalise paraphrased relations,
       reuse Entity Resolution logic)
                  ▼
          Cross Verification
   (every triple checked by the OTHER
    two models against the source text)
                  ▼
          Agreement Calculation
     agreement = supporting_models / verifying_models
                  ▼
        Consensus Triple Selection
      (agreement_score >= MIN_AGREEMENT_SCORE)
                  ▼
            Entity Resolution
                  ▼
                Neo4j
                  ▼
        Consensus Knowledge Graph
                  ▼
              Evaluation
```

If you have API-key / local-model trouble, the pipeline automatically **falls back
to a legacy single-model mode** (or a mock demo with no LLM at all) so the
Streamlit app and CLI always work out of the box — see [Troubleshooting](#troubleshooting).

---

## Architecture Diagram (Class Level)

```
config/settings.py ── read by everything below

src/providers.py
  BaseLLM (ABC)
   ├── GeminiProvider        (hosted Gemini API)
   └── OllamaProvider        (local models via http://localhost:11434)
        ├── LlamaProvider    (llama3.1:8b)
        └── QwenProvider     (qwen3:8b)

src/extraction.py
  Triple                     (dataclass — now carries generator_model,
                              verification_results, agreement_score, timestamp)
  LLMExtractor               (legacy, single-model — kept for backward compat)
  MultiLLMExtractor          (Step 1: independent extraction, all 3 models, async)

src/resolution.py
  EntityResolver             (unchanged — shared by legacy AND consensus modes)

src/consensus.py
  TripleAligner              (Step 2: entity + relation alignment)
  ConsensusManager           (Step 6-7: threshold + de-duplication)

src/verification.py
  HallucinationFilter        (legacy, lexical/single-LLM — kept for backward compat)
  VerificationManager        (Step 3-5: cross verification + Agreement Score, async)

src/graph_builder.py
  GraphBuilder               (unchanged API; now writes full consensus metadata)

src/evaluation.py
  Evaluator                  (legacy — kept for backward compat)
  EvaluationManager          (Step 9: per-model / consensus / gold-standard /
                              single-vs-consensus comparison, extends Evaluator)

src/pipeline.py
  Pipeline.run() / run_async()
    ├── _run_consensus()     (used when >= 2 providers are available)
    └── _run_legacy()        (automatic fallback: 1 provider, or mock demo)
```

---

## Project Structure

```
kg_pipeline/
├── config/
│   └── settings.py           # All configuration — API keys, models, thresholds
├── src/
│   ├── ingestion.py           # Stage 1: Load & chunk documents
│   ├── providers.py           # BaseLLM / GeminiProvider / OllamaProvider / LlamaProvider / QwenProvider
│   ├── extraction.py          # Stage 2: Triple dataclass, LLMExtractor (legacy), MultiLLMExtractor
│   ├── consensus.py           # TripleAligner (Step 2), ConsensusManager (Step 6-7)
│   ├── verification.py        # HallucinationFilter (legacy), VerificationManager (Step 3-5)
│   ├── resolution.py          # Stage 3: Entity deduplication & canonicalisation
│   ├── graph_builder.py       # Stage 4: Build & store Neo4j / NetworkX graph + exports
│   ├── evaluation.py          # Stage 5: Evaluator (legacy), EvaluationManager (consensus)
│   └── pipeline.py            # Orchestrator — consensus mode + legacy fallback, asyncio
├── data/
│   ├── raw/                   # Put your input documents here
│   ├── processed/             # Intermediate outputs (chunks, per-model & verified triples)
│   ├── output/                # Final graph exports (JSON, CSV, Cypher, evaluation report)
│   └── gold_standard.txt      # Reference triples for precision/recall
├── notebooks/
│   └── explore_graph.ipynb    # Jupyter notebook for visualisation
├── tests/
│   └── test_pipeline.py       # Unit tests for each stage
├── app.py                     # Streamlit UI
├── run_pipeline.py            # CLI entry point
├── setup.bat                  # Windows one-click setup (Python deps + Ollama check)
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Windows users can instead just double-click / run **`setup.bat`**, which installs
the dependencies and checks your Ollama installation and models automatically
(see [Automatic Setup](#automatic-setup-windows) below).

### 2. Ollama Installation (for Llama 3.1 & Qwen 3, local)

Two of the three consensus models run **locally** via [Ollama](https://ollama.com) —
no code changes or API keys needed for them.

1. Download and install Ollama: **https://ollama.com/download**
2. Start the server (usually starts automatically after install; if not):
   ```bash
   ollama serve
   ```
   By default it listens on `http://localhost:11434` — matches
   `config.settings.OLLAMA_URL` out of the box.

### 3. Model Download

```bash
ollama pull llama3.1:8b
ollama pull qwen3:8b
```

Each is roughly a 5 GB download. You need enough free RAM/VRAM to run an 8B model
(16 GB system RAM is comfortable for CPU inference; a GPU with 8 GB+ VRAM speeds
things up considerably).

### 4. Gemini API Key

Get a free key at **https://aistudio.google.com/apikey**, then either:

```bash
set GEMINI_API_KEY=your-key-here        # Windows (cmd)
$env:GEMINI_API_KEY="your-key-here"     # Windows (PowerShell)
export GEMINI_API_KEY=your-key-here     # macOS/Linux
```

or paste it directly into `config/settings.py` (`GEMINI_API_KEY`), or into the
Streamlit sidebar at runtime.

### Automatic Setup (Windows)

Run:

```bat
setup.bat
```

This will:
- Install everything in `requirements.txt`
- Check whether Ollama is installed (and tell you where to get it if not)
- Check whether `llama3.1:8b` and `qwen3:8b` are already pulled, and print the
  exact `ollama pull ...` commands for anything missing

---

## Project Setup

### Add Your Documents

Drop `.txt`, `.pdf`, or `.html` files into `data/raw/`. Sample documents
(Marie Curie, Albert Einstein, OpenAI) are included so the pipeline runs
immediately with no setup — it uses a small built-in mock extractor if no LLM
provider is configured yet, so you can sanity-check the rest of the pipeline
before wiring up real models.

### Neo4j (optional but recommended)

Download Neo4j Desktop (free): https://neo4j.com/download/, or run with Docker:

```bash
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
```

If you skip Neo4j (`NEO4J_ENABLED = False`), the pipeline still runs and exports
results to JSON/CSV/Cypher — the Cypher file at `data/output/import_graph.cypher`
can be pasted into Neo4j Browser later.

---

## Running

### Running Streamlit

```bash
streamlit run app.py
```

Upload documents, toggle which models to use (Gemini / Llama / Qwen), set the
minimum Agreement Score, and click **Run Pipeline**. Results appear in tabs
including a dedicated **Consensus** tab with per-model statistics, the
agreement-score distribution, and the single-model-vs-consensus F1 comparison.

### Running from the command line

```bash
python run_pipeline.py
```

Options:
```bash
python run_pipeline.py --input path/to/docs
python run_pipeline.py --no-neo4j
python run_pipeline.py --log-level DEBUG
```

### Running Neo4j Browser

Once the pipeline has written to Neo4j: open **http://localhost:7474** and run:

```cypher
// See all nodes
MATCH (n) RETURN n LIMIT 50

// Explore an entity and its consensus metadata
MATCH (e:Entity {name: "Marie Curie"})-[r]->(o)
RETURN e, r.agreement_score, r.generated_by, r.verified_by, r.evidence, o

// Only very high-confidence (unanimous) consensus facts
MATCH ()-[r]->() WHERE r.agreement_score = 1.0 RETURN r LIMIT 50
```

---

## Consensus Workflow (Steps 1-8)

1. **Independent Extraction** — Gemini, Llama, and Qwen each extract triples from
   every chunk independently, with the *same* prompt and schema
   (`src/providers.py::EXTRACTION_SYSTEM_PROMPT`). Their outputs are kept as
   three separate graphs (`src/extraction.py::MultiLLMExtractor`) — not merged.
2. **Triple Alignment** — different models phrase the same fact differently
   ("acquired" / "purchased" / "bought"). `src/consensus.py::TripleAligner`
   canonicalises entity names via the *same* `EntityResolver` used everywhere
   else, and clusters near-duplicate relation strings the same way
   (`rapidfuzz.token_sort_ratio`), so equivalent triples compare equal.
3. **Cross Verification** — every triple generated by one model is sent, along
   with its exact source chunk, to each of the *other* models with a strict
   evidence-only prompt (`src/providers.py::VERIFICATION_SYSTEM_PROMPT`):
   > "Determine whether this triple is explicitly supported by the provided
   > source text. Return JSON only. `{supported:true/false, evidence:'exact
   > supporting sentence'}`"
4. **Evidence-Based Verification** — a verifier must return `SUPPORTED` /
   `NOT_SUPPORTED` *and*, if supported, the exact sentence. A `NOT_SUPPORTED`
   verdict is never allowed to carry invented evidence
   (`src/verification.py::VerificationManager._verify_one`).
5. **Agreement Score** (see formula below) is computed and stored on every
   triple, replacing the old single-model confidence score.
6. **Consensus Rule** — only triples with `agreement_score >= MIN_AGREEMENT_SCORE`
   (configurable) survive.
7. **Consensus Knowledge Graph** — accepted triples are de-duplicated (the same
   fact independently proposed by 2-3 models becomes ONE edge, with the other
   generators recorded, not discarded) and only this final set is written to
   Neo4j (`src/consensus.py::ConsensusManager`).
8. **Metadata** — every stored relationship carries: Subject, Predicate, Object,
   Generator Model, per-verifier Verification Results, Evidence Sentences,
   Agreement Score, and a Timestamp (see example below).

## Verification Algorithm

```
for generator_model in {gemini, llama, qwen}:
    for triple in generator_model.extracted_triples:
        verifiers = {gemini, llama, qwen} - {generator_model}
        results = []
        for verifier in verifiers:                      # run concurrently (asyncio)
            response = verifier.check(source_text, triple)
            results.append(response)                     # {supported, evidence}
        triple.verification_results = results
        triple.agreement_score = count(supported) / len(verifiers)
```

## Agreement Formula

```
Agreement Score = (number of verifying models that returned supported = true)
                   / (number of verifying models)
```

| Verifiers agreeing | Verifying models | Agreement Score |
|---|---|---|
| 2 | 2 | 1.00 |
| 1 | 2 | 0.50 |
| 0 | 2 | 0.00 |

`MIN_AGREEMENT_SCORE` (in `config/settings.py`) sets the acceptance threshold:

- `1.0` — unanimous agreement required (strictest, highest precision)
- `0.5` — at least one of two verifiers must agree (default)
- `0.0` — accept everything (disables consensus filtering, useful for ablation)

### Example stored triple

```
Subject:              Apple
Predicate:             acquired
Object:                Beats
Generated By:          Gemini
Verified By Llama:     SUPPORTED — "Apple acquired Beats in 2014."
Verified By Qwen:      SUPPORTED — "Apple acquired Beats in 2014."
Agreement Score:       1.00
Consensus Status:      accepted
Timestamp:             2026-08-06T10:15:32+00:00
```

---

## Configuration Options (`config/settings.py`)

### Multi-LLM Consensus (primary framework)

| Setting | Default | Description |
|---|---|---|
| `USE_GEMINI` | `True` | Enable the hosted Gemini API |
| `USE_LLAMA` | `True` | Enable local Llama 3.1 8B via Ollama |
| `USE_QWEN` | `True` | Enable local Qwen 3 8B via Ollama |
| `GEMINI_API_KEY` | env `GEMINI_API_KEY` | Gemini API key |
| `MODEL_NAME` | `"gemini-2.5-flash"` | Gemini model id |
| `OLLAMA_URL` | `http://localhost:11434` | Local Ollama server |
| `LLAMA_MODEL_NAME` | `"llama3.1:8b"` | Ollama tag for Llama |
| `QWEN_MODEL_NAME` | `"qwen3:8b"` | Ollama tag for Qwen |
| `MIN_AGREEMENT_SCORE` | `0.5` | Consensus acceptance threshold (0-1) |
| `ENABLE_EVIDENCE_STORAGE` | `True` | Store per-verifier evidence sentences |
| `ENABLE_ASYNC` | `True` | Run extraction/verification concurrently |
| `CONSENSUS_MAX_CONCURRENCY` | `4` | Max in-flight calls per provider |

### Document processing / entity resolution / Neo4j (unchanged)

| Setting | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `SIMILARITY_THRESHOLD` | `0.85` | Entity resolution threshold (0-1) |
| `USE_SEMANTIC_SIMILARITY` | `True` | Use sentence-transformer embeddings for entity resolution |
| `NEO4J_ENABLED` | `True` | Set `False` to skip Neo4j (still exports files) |

### Gold standard evaluation

| Setting | Default | Description |
|---|---|---|
| `GOLD_STANDARD_PATH` | `data/gold_standard.txt` | Reference triples for precision/recall |
| `GOLD_STANDARD_FUZZY_MATCH` | `True` | Also score with fuzzy (not just exact) matching |
| `GOLD_STANDARD_FUZZY_THRESHOLD` | `85.0` | rapidfuzz threshold (0-100) |

### Legacy (single-model fallback only)

| Setting | Default | Description |
|---|---|---|
| `GROUNDING_THRESHOLD` | `60.0` | Lexical grounding threshold used only in legacy mode |
| `HALLUCINATION_FILTER_MODE` | `"flag"` | `"flag"` \| `"downweight"` \| `"drop"` (legacy mode only) |
| `USE_LLM_VERIFICATION` | `False` | Legacy single-model LLM verification pass |

---

## Understanding the Output

- **`data/output/triples.json` / `triples.csv`** — the final Consensus Knowledge
  Graph, one row per accepted triple, with full metadata (generator, agreement
  score, verification results, evidence, timestamp).
- **`data/output/import_graph.cypher`** — paste into Neo4j Browser to (re)build
  the graph, including all consensus metadata as edge properties.
- **`data/processed/raw_triples_by_model.json`** — the three independent, pre-consensus
  graphs (one array per model) — useful for the per-model ablation section of a thesis.
- **`data/processed/verified_triples.json`** — every candidate triple after cross
  verification, before the consensus threshold is applied.
- **`data/processed/consensus_triples.json`** — the accepted, de-duplicated
  Consensus Knowledge Graph before it's written to Neo4j.
- **`data/output/evaluation_report.txt` / `evaluation_results.json`** — full
  Step 9 evaluation (see below).

---

## Evaluation (Step 9)

`src/evaluation.py::EvaluationManager` (used automatically whenever the
consensus pipeline runs) reports:

- **Per-model statistics** — triples generated / accepted / rejected and
  average agreement score, for each of Gemini/Llama/Qwen.
- **Consensus graph statistics** — nodes, edges, density, entity-type
  diversity, relation-type diversity.
- **Hallucination statistics** — accepted / rejected counts, acceptance rate,
  and the full agreement-score distribution.
- **Gold-standard precision/recall/F1** (if `GOLD_STANDARD_PATH` is set) —
  both exact-match and fuzzy-match, exactly as in the legacy pipeline.
- **Single model vs. Consensus graph** — precision/recall/F1 for each
  individual model's raw graph compared against the final consensus graph,
  with the absolute and relative F1 improvement the consensus framework
  provides over using any one model alone — the core empirical result for
  the thesis.

The legacy `Evaluator` class (single-model gold-standard eval, hallucination/
grounding stats, entity coverage, etc.) is preserved unchanged and is used
automatically if the pipeline falls back to legacy mode.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Pipeline logs "Falling back to the legacy single-model pipeline" | Fewer than 2 of `USE_GEMINI/USE_LLAMA/USE_QWEN` resolved to a usable provider. Check your `GEMINI_API_KEY`, and confirm `ollama serve` is running (`ollama list` should succeed). |
| `[llama] Ollama request ... failed` / `[qwen] Ollama request ... failed` | Ollama isn't running, or the model isn't pulled. Run `ollama serve` in one terminal and `ollama pull llama3.1:8b` / `ollama pull qwen3:8b` in another. |
| Gemini calls fail with an auth error | Check `GEMINI_API_KEY` is set (env var or `config/settings.py`) and valid at https://aistudio.google.com/apikey |
| Pipeline is slow | Local 8B models on CPU are the bottleneck, not the orchestration (extraction and verification already run concurrently via asyncio). Use a GPU-backed Ollama install, or lower `CONSENSUS_MAX_CONCURRENCY` if you're hitting memory limits with concurrent local calls. |
| Neo4j write fails / is skipped | The pipeline logs a warning and continues — check Neo4j is running and `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` are correct. Results are still exported to JSON/CSV/Cypher regardless. |
| No documents in `data/raw/` | The pipeline auto-generates 3 sample documents (Marie Curie, Einstein, OpenAI) so it always has something to run on. |
| Want to see the pipeline run without any LLM at all | Leave `USE_GEMINI/USE_LLAMA/USE_QWEN` off / unreachable — it uses a small built-in mock extractor (`Pipeline._mock_extraction`) so the rest of the stages (resolution, graph, evaluation) are still exercised. |

---

## Extending the Project

- **Add a domain**: drop new documents into `data/raw/` and re-run.
- **Ablation runs**: toggle `USE_GEMINI` / `USE_LLAMA` / `USE_QWEN` to see how
  2-model vs 3-model consensus affects the agreement distribution and F1.
- **Change the threshold**: sweep `MIN_AGREEMENT_SCORE` (0.0 / 0.5 / 1.0) and
  compare `data/output/evaluation_report.txt` across runs for the
  precision/recall trade-off write-up.
- **Custom entity types**: edit `ENTITY_TYPES` in `config/settings.py`.
- **GraphRAG querying**: see `notebooks/explore_graph.ipynb`.
