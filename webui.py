"""CodeAtlas Web UI — paste a repo link, watch the pipeline, browse results."""
import sys
import json
import queue
import threading
import shutil
import tempfile
import webbrowser
import warnings
from pathlib import Path
from io import StringIO

warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from src.build import build_graph
from src.cluster import cluster as cluster_graph
from src.analyze import god_nodes, surprising_connections, suggest_questions
from src.export import to_html
from src.report import generate_report

app = Flask(__name__)

# Store running tasks
tasks: dict = {}
TASK_DIR = Path(tempfile.gettempdir()) / "codeatlas_webui"
TASK_DIR.mkdir(parents=True, exist_ok=True)

CODE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go"}


class StreamQueue:
    """A thread-safe queue that also captures for SSE streaming."""
    def __init__(self):
        self.q = queue.Queue()

    def write(self, msg: str):
        self.q.put(msg)

    def read(self, timeout: float = 30):
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None


def run_pipeline_in_thread(task_id: str, target: str, stream: StreamQueue):
    """Run the full pipeline in a background thread, capturing output."""
    from src.extract import extract_file
    from src.semantic import extract_from_directory

    # Override stdout
    original_stdout = sys.stdout
    sys.stdout = StringIO()

    class Tee:
        def write(self, text):
            if text.strip():
                stream.write(text.strip())
            original_stdout.write(text)
        def flush(self):
            original_stdout.flush()

    sys.stdout = Tee()

    try:
        is_github = target.startswith("https://github.com/") or target.startswith("git@github.com:")
        root: Path
        cleanup = None

        if is_github:
            stream.write("Cloning repository...")
            import subprocess
            root = TASK_DIR / task_id / "repo"
            root.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", target, str(root)], check=True, capture_output=True)
            cleanup = lambda: shutil.rmtree(root, ignore_errors=True)
        else:
            root = Path(target).resolve()

        output_dir = TASK_DIR / task_id / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        extractions = []
        ignore_patterns = {".git", ".venv", "venv", "node_modules", "__pycache__", "*.pyc", ".idea", ".vscode", "dist", "build", "output", "graphify-out"}

        # Pass 1: AST
        stream.write(f"Scanning {root} for code files...")
        code_files = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in CODE_EXTENSIONS:
                code_files.append(path)
        stream.write(f"Found {len(code_files)} code files")

        for path in code_files:
            result = extract_file(path, root)
            if result["nodes"] or result["edges"]:
                extractions.append(result)
                rel = str(path.relative_to(root)).replace("\\", "/")
                stream.write(f"AST: {rel} ({len(result['nodes'])} nodes, {len(result['edges'])} edges)")

        # Pass 2: Semantic
        stream.write("Semantic extraction (Claude)...")
        sem_result = extract_from_directory(root, CODE_EXTENSIONS)
        if sem_result["nodes"] or sem_result["edges"]:
            extractions.append(sem_result)
            stream.write(f"Semantic: {len(sem_result['nodes'])} nodes, {len(sem_result['edges'])} edges")

        # Build
        stream.write("Building graph...")
        G = build_graph(extractions)
        stream.write(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        # Cluster
        stream.write("Clustering (Leiden)...")
        communities = cluster_graph(G)
        stream.write(f"Found {len(communities)} communities")
        for cid, members in sorted(communities.items()):
            labels = [G.nodes[n].get("label", n) for n in members[:3]]
            stream.write(f"  Community {cid}: {', '.join(labels)} ({len(members)} nodes)")

        for cid, members in communities.items():
            for n in members:
                if n in G.nodes:
                    G.nodes[n]["community"] = cid

        # Analysis
        gods = god_nodes(G)
        surprises = surprising_connections(G, communities)
        questions = suggest_questions(G)
        stream.write(f"God nodes: {[g['label'] for g in gods[:5]]}")
        stream.write(f"Surprising connections: {len(surprises)}")

        # Save graph.json
        graph_path = output_dir / "graph.json"
        data = {
            "nodes": [{"id": n, **G.nodes[n]} for n in G.nodes],
            "edges": [
                {"source": u, "target": v, "relation": G.edges[u, v].get("relation", "unknown"),
                 "confidence": G.edges[u, v].get("confidence", "EXTRACTED"),
                 "confidence_score": G.edges[u, v].get("confidence_score", 1.0),
                 "evidence": G.edges[u, v].get("evidence", "")}
                for u, v in G.edges
            ],
            "communities": {str(k): v for k, v in communities.items()},
        }
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # HTML export
        html_path = output_dir / "graph.html"
        to_html(G, html_path, communities)

        # Report
        report_text = generate_report(G, communities, gods, surprises, questions)
        (output_dir / "GRAPH_REPORT.md").write_text(report_text, encoding="utf-8")

        if cleanup:
            cleanup()

        # Signal completion with output path
        stream.write(f"__DONE__:{output_dir}")

    except Exception as e:
        stream.write(f"__ERROR__:{str(e)}")
    finally:
        sys.stdout = original_stdout


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    target = request.json.get("target", "").strip()
    if not target:
        return jsonify({"error": "No target provided"}), 400

    import uuid
    task_id = str(uuid.uuid4())[:8]
    stream = StreamQueue()
    tasks[task_id] = stream

    thread = threading.Thread(target=run_pipeline_in_thread, args=(task_id, target, stream), daemon=True)
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/stream/<task_id>")
def stream(task_id):
    stream_q = tasks.get(task_id)
    if not stream_q:
        return Response("data: __ERROR__:Task not found\n\n", mimetype="text/event-stream")

    def generate():
        while True:
            msg = stream_q.read(timeout=120)
            if msg is None:
                yield "data: __KEEPALIVE__\n\n"
                continue
            if msg.startswith("__DONE__:"):
                yield f"data: {msg}\n\n"
                break
            if msg.startswith("__ERROR__:"):
                yield f"data: {msg}\n\n"
                break
            yield f"data: {msg}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/output/<path:filepath>")
def serve_output(filepath):
    """Serve files from output directories."""
    # filepath is like "task_id/output/filename"
    return send_from_directory(TASK_DIR, filepath)


@app.route("/graph/<task_id>")
def serve_graph(task_id):
    """Serve the graph HTML for a task."""
    html_file = TASK_DIR / task_id / "output" / "graph.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "Graph not found", 404


@app.route("/report/<task_id>")
def serve_report(task_id):
    """Serve the report for a task."""
    report_file = TASK_DIR / task_id / "output" / "GRAPH_REPORT.md"
    if report_file.exists():
        return report_file.read_text(encoding="utf-8")
    return "Report not found", 404


@app.route("/communities/<task_id>")
def serve_communities(task_id):
    """Return communities as JSON."""
    json_file = TASK_DIR / task_id / "output" / "graph.json"
    if json_file.exists():
        data = json.loads(json_file.read_text(encoding="utf-8"))
        return jsonify(data.get("communities", {}))
    return jsonify({})


if __name__ == "__main__":
    import sys
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    print(f"\n  CodeAtlas Web UI starting at http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
