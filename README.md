# CodeAtlas

**Turn any codebase into an interactive, queryable knowledge graph — no embeddings, no vector database.**

CodeAtlas combines deterministic AST parsing (tree‑sitter) with AI reasoning (Claude) to extract classes, functions, imports, call graphs, and cross‑document relationships. The result is a NetworkX graph clustered by topology alone (Leiden algorithm), exported as an interactive HTML visualisation, a plain‑language audit report, and queryable JSON.

## Features

- **5‑language AST extraction** – Python, JavaScript, TypeScript, Java, Go.
- **Confidence‑tagged edges** – EXTRACTED (found in source) vs INFERRED (Claude reasoning).
- **Topology‑only clustering** – Leiden community detection, no embeddings.
- **Interactive HTML graph** – Click, drag, zoom, explore.
- **Plain‑English audit report** – God nodes, surprising connections, knowledge gaps.
- **Web UI** – Paste a GitHub URL and watch the pipeline run live.
- **GitHub repo support** – Analyse any public repository in one command.

## Quick Start

`ash
# Clone and set up
git clone https://github.com/YOUR_USERNAME/CodeAtlas.git
cd CodeAtlas
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

# Add your Anthropic API key (optional, mock fallback works offline)
echo ANTHROPIC_API_KEY=your-key > .env

# Run the web UI
python webui.py
Or use the command line:
python main.py sample_repo          # local sample project
python main.py https://github.com/psf/requests   # any public repo
Output
FileDescription
output/graph.htmlInteractive visualisation
output/GRAPH_REPORT.mdPlain‑language audit
output/graph.jsonMachine‑queryable graph data
Architecture
LayerTechnologyCost
AST extractiontree‑sitter (5 languages)Free, local
Semantic reasoningClaude API (pluggable)~.01/run
Graph databaseNetworkX (in‑memory)Free
ClusteringLeiden / Louvain (graspologic)Free
VisualisationPyVis (interactive HTML)Free
Web UIFlask + SSE streamingFree
License
MIT
