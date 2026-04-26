"""CodeAtlas pipeline: full end‑to‑end demo. Supports local paths and GitHub URLs."""
import json, sys, subprocess, tempfile, shutil, warnings
from pathlib import Path

# Suppress tree-sitter FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

from src.extract import extract_file
from src.semantic import extract_from_directory
from src.build import build_graph
from src.cluster import cluster
from src.analyze import god_nodes, surprising_connections, suggest_questions
from src.export import to_html
from src.report import generate_report, save_report

CODE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go"}

def load_ignore_patterns(root: Path) -> set:
    """Load .graphifyignore patterns (same syntax as .gitignore)."""
    ignore_path = root / ".graphifyignore"
    patterns = set()
    if ignore_path.exists():
        for line in ignore_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.add(line)
    # Default patterns
    patterns.update({".git", ".venv", "venv", "node_modules", "__pycache__", "*.pyc", ".idea", ".vscode", "*.egg-info", "dist", "build", "graphify-out", "output"})
    return patterns

def should_skip(path: Path, root: Path, patterns: set) -> bool:
    """Check if a path should be skipped based on ignore patterns."""
    try:
        rel = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return False
    parts = rel.split("/")
    for part in parts:
        if part in patterns:
            return True
        for pat in patterns:
            if pat.endswith("/") and part == pat.rstrip("/"):
                return True
            if "*" in pat:
                import fnmatch
                if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(path.name, pat):
                    return True
    return False

def pipeline(root: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    extractions = []
    ignore_patterns = load_ignore_patterns(root)

    # Pass 1: AST extraction
    print("=== Pass 1: AST extraction ===")
    code_files = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in CODE_EXTENSIONS:
            if not should_skip(path, root, ignore_patterns):
                code_files.append(path)
    print(f"  Found {len(code_files)} code files (after .graphifyignore)")
    for path in code_files:
        try:
            result = extract_file(path, root)
            if result["nodes"] or result["edges"]:
                extractions.append(result)
                rel = str(path.relative_to(root)).replace("\\", "/")
                print(f"  OK  {rel}  ({len(result['nodes'])} nodes, {len(result['edges'])} edges)")
        except Exception as e:
            rel = str(path.relative_to(root)).replace("\\", "/")
            print(f"  ERR {rel}: {e}")

    # Pass 2: Semantic extraction
    print("\n=== Pass 2: Semantic extraction ===")
    try:
        sem_result = extract_from_directory(root, CODE_EXTENSIONS)
        if sem_result["nodes"] or sem_result["edges"]:
            extractions.append(sem_result)
            print(f"  Semantic pass: {len(sem_result['nodes'])} nodes, {len(sem_result['edges'])} edges")
    except Exception as e:
        print(f"  Semantic pass failed: {e}")

    # Build graph
    print("\n=== Building graph ===")
    G = build_graph(extractions)
    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Clustering
    print("\n=== Clustering (Leiden) ===")
    communities = cluster(G)
    print(f"  Found {len(communities)} communities")
    for cid, members in sorted(communities.items()):
        labels = [G.nodes[n].get("label", n) for n in members[:5]]
        suffix = " ..." if len(members) > 5 else ""
        print(f"    Community {cid}: {', '.join(labels)}{suffix}  ({len(members)} nodes)")

    for cid, members in communities.items():
        for n in members:
            if n in G.nodes:
                G.nodes[n]["community"] = cid

    # Analysis
    print("\n=== Analysis ===")
    gods = god_nodes(G)
    print(f"  God nodes: {[g['label'] for g in gods[:5]]}")
    surprises = surprising_connections(G, communities)
    print(f"  Surprising connections: {len(surprises)}")
    questions = suggest_questions(G)
    print(f"  Suggested questions: {len(questions)}")

    # Exports
    print("\n=== Exports ===")
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
    print(f"  graph.json saved")

    html_path = output_dir / "graph.html"
    to_html(G, html_path, communities)

    report_text = generate_report(G, communities, gods, surprises, questions)
    report_path = output_dir / "GRAPH_REPORT.md"
    save_report(report_text, report_path)

    print(f"\n=== Done. Open {html_path} in your browser. ===")
    return G, communities

def clone_github(repo_url: str) -> Path:
    """Clone a GitHub repo to a temp directory and return the path."""
    tmp = Path(tempfile.mkdtemp(prefix="codeatlas_"))
    print(f"  Cloning {repo_url} ...")
    subprocess.run(["git", "clone", "--depth", "1", repo_url, str(tmp)], check=True, capture_output=True)
    return tmp

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path|github-url> [output-dir]")
        print("Examples:")
        print("  python main.py sample_repo")
        print("  python main.py https://github.com/user/repo")
        sys.exit(1)

    target = sys.argv[1]
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")
    is_github = target.startswith("https://github.com/") or target.startswith("git@github.com:")

    if is_github:
        # Normalize to HTTPS URL
        if target.startswith("git@github.com:"):
            target = target.replace("git@github.com:", "https://github.com/").replace(".git", "")
        try:
            repo_path = clone_github(target)
            pipeline(repo_path, output.resolve())
        finally:
            if repo_path.exists():
                shutil.rmtree(repo_path, ignore_errors=True)
    else:
        pipeline(Path(target).resolve(), output.resolve())
