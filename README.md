# Knowledge Graph Pipeline
### End-to-End Construction from Unstructured Documents using LLMs
*Masters Thesis Project*

---

## What This Does

This pipeline takes raw text documents (PDFs, `.txt`, `.html`) and automatically builds a **Knowledge Graph** stored in Neo4j. It uses an LLM (Claude or OpenAI) to extract entities and relationships from each chunk of text, resolves duplicates, and writes the final graph to a database you can query and visualise.

```
Raw Documents → Chunks → LLM Extraction → Entity Resolution → Neo4j Graph → Evaluation
```

---

## Project Structure

```
kg_pipeline/
├── config/
│   └── settings.py          # All configuration (API keys, model, chunking params)
├── src/
│   ├── ingestion.py         # Stage 1: Load & chunk documents
│   ├── extraction.py        # Stage 2: LLM entity/relation extraction
│   ├── resolution.py        # Stage 3: Entity deduplication & canonicalisation
│   ├── graph_builder.py     # Stage 4: Build & store Neo4j graph
│   ├── evaluation.py        # Stage 5: Evaluate graph quality
│   └── pipeline.py          # Orchestrator: runs all stages end-to-end
├── data/
│   ├── raw/                 # Put your input documents here
│   ├── processed/           # Intermediate outputs (chunks, extractions)
│   └── output/              # Final graph exports (JSON, CSV)
├── notebooks/
│   └── explore_graph.ipynb  # Jupyter notebook for visualisation
├── tests/
│   └── test_pipeline.py     # Unit tests for each stage
├── requirements.txt
└── run_pipeline.py          # Entry point — run this to start
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Set Your API Key

Open `config/settings.py` and add your Anthropic API key (or OpenAI key).

Get a free Anthropic API key at: https://console.anthropic.com

### 3. Install & Start Neo4j (Optional but recommended)

Download Neo4j Desktop (free): https://neo4j.com/download/

Or run with Docker:
```bash
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

If you skip Neo4j, the pipeline will still run and export results to JSON/CSV.

### 4. Add Your Documents

Drop `.txt`, `.pdf`, or `.html` files into `data/raw/`.

A sample document is included so you can run the pipeline immediately without any documents.

### 5. Run the Pipeline

```bash
python run_pipeline.py
```

That's it. Results are saved to `data/output/` and loaded into Neo4j.

---

## Configuration Options (`config/settings.py`)

| Setting | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `"anthropic"` | `"anthropic"` or `"openai"` |
| `MODEL_NAME` | `"claude-opus-4-6"` | Model to use for extraction |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `SIMILARITY_THRESHOLD` | `0.85` | Entity resolution threshold (0–1) |
| `NEO4J_ENABLED` | `True` | Set False to skip Neo4j |

---

## Understanding the Output

After running, check:

- **`data/output/triples.json`** — every extracted (subject, relation, object) triple
- **`data/output/entities.json`** — deduplicated entity list with types
- **`data/output/evaluation_report.txt`** — precision, recall, graph statistics
- **Neo4j Browser** at `http://localhost:7474` — visual graph explorer

### Sample Cypher Queries (in Neo4j Browser)

```cypher
// See all nodes
MATCH (n) RETURN n LIMIT 50

// Find all relations for an entity
MATCH (e:Entity {name: "Marie Curie"})-[r]->(o) RETURN e, r, o

// Count entity types
MATCH (n:Entity) RETURN n.type, count(n) ORDER BY count(n) DESC
```

---

## Thesis Evaluation Metrics

The evaluation module (`src/evaluation.py`) computes:

- **Triple precision/recall** against a gold standard (if provided)
- **Entity coverage** — how many unique entities extracted per document
- **Relation diversity** — number of distinct relation types
- **Graph density** — edges / possible edges
- **Extraction throughput** — tokens per second, cost per document

---

## Extending the Project

- **Add a domain**: drop new documents into `data/raw/` and re-run
- **Change LLM**: update `LLM_PROVIDER` and `MODEL_NAME` in settings
- **Custom entity types**: edit `ENTITY_TYPES` in `config/settings.py`
- **GraphRAG querying**: see `notebooks/explore_graph.ipynb` for natural language querying over the graph
