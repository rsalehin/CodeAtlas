# CodeAtlas — Interview Talking Points

## One-line pitch
CodeAtlas turns any codebase into an **interactive, queryable knowledge graph** — no embeddings, no vector database, just deterministic AST parsing + AI reasoning.

## Demo script (2 minutes)

### 1. Show the sample project (15s)
python demo.py sample_repo
Points to make:
- "This is a small Python calculator with utils — about what you'd see in a real project."
- "The pipeline runs in under 10 seconds including Claude API call."

### 2. Walk through the interactive graph (30s)
- "Every node is a **class, function, or file** — extracted deterministically by tree‑sitter."
- "**Teal edges** are EXTRACTED — found directly in source code."
- "**Orange edges** are INFERRED — Claude read the README and reasoned about relationships."
- "Click any node to see its connections. Drag to explore."

### 3. Show the communities (15s)
- "The graph self‑organises into **6 communities** purely from edge density — no embeddings."
- "Leiden algorithm found: calculator cluster, utils cluster, main bridge."
- "This is the architecture emerging from the code itself."

### 4. Walk through GRAPH_REPORT.md (15s)
- "**God nodes** — Logger, Config, main — the core abstractions."
- "**Surprising connections** — cross‑community edges Claude inferred."
- "**Confidence breakdown** — exactly 0 AMBIGUOUS edges, you know what's fact vs guess."

### 5. Run on a real GitHub repo (30s)
python demo.py https://github.com/psf/requests
- "Same pipeline, any public repo, any of 5 languages."
- "The `.graphifyignore` file skips venv, node_modules, .git — no noise."
- "Output: interactive HTML + JSON you can query programmatically."

## Architecture (if asked)

| Layer | Technology | Cost |
|-------|-----------|------|
| **AST extraction** | tree‑sitter (5 languages) | Free, local |
| **Semantic reasoning** | Claude API (pluggable) | ~$0.01/run |
| **Graph database** | NetworkX (in‑memory) | Free |
| **Clustering** | Leiden/Louvain (graspologic) | Free |
| **Visualisation** | PyVis (interactive HTML) | Free |

## Key differentiators

1. **No embeddings, no vector DB** — semantic similarity edges go directly into the graph
2. **Every edge is tagged** — EXTRACTED / INFERRED / AMBIGUOUS
3. **Deterministic + AI** — code structure is exact; AI handles only reasoning
4. **Works on any GitHub repo** — 5 languages, no config needed
5. **Interview‑ready output** — interactive HTML + plain‑English report

## Answering tough questions

**Q: "What if the LLM hallucinates?"**
A: "Every AI‑generated edge is tagged INFERRED with a confidence score. The user sees exactly what came from Claude vs what came from the AST. AMBIGUOUS edges are flagged for human review. Nothing is ever presented as fact if it's AI‑generated."

**Q: "Doesn't this get expensive at scale?"**
A: "AST extraction is free — it's just tree‑sitter. The Claude calls are only for README/docs files, not every line of code. On a typical repo, it's 1 Claude call for the documentation, which costs about $0.01. The mock fallback works offline with zero cost."

**Q: "Why not just use embeddings?"**
A: "Embeddings require maintaining a vector database and re‑embedding on every change. We let Claude extract `semantically_similar_to` edges directly, and Leiden finds communities by edge density. The graph *is* the similarity signal — one less moving part to break."