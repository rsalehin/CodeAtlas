"""Graph analysis: god nodes, surprising connections, suggested questions."""
import networkx as nx
from collections import Counter
from typing import Dict, List

def god_nodes(G: nx.Graph, top_n: int = 10) -> List[dict]:
    """Highly-connected core abstractions, excluding file-level hubs."""
    # Exclude nodes that are just file paths or single-file hubs
    excluded_labels = set()
    for n, d in G.nodes(data=True):
        label = d.get("label", n)
        if label == d.get("source_file", ""):
            excluded_labels.add(n)
        if n.endswith((".py", ".js", ".ts", ".java", ".go")):
            excluded_labels.add(n)

    degrees = [(n, deg) for n, deg in G.degree() if n not in excluded_labels]
    degrees.sort(key=lambda x: x[1], reverse=True)
    return [
        {
            "id": n,
            "label": G.nodes[n].get("label", n),
            "degree": deg,
            "community": G.nodes[n].get("community", -1),
        }
        for n, deg in degrees[:top_n]
    ]

def surprising_connections(G: nx.Graph, communities: Dict[int, List[str]], top_n: int = 5) -> List[dict]:
    """Cross-community edges that reveal non-obvious couplings."""
    node_comm = {}
    for cid, members in communities.items():
        for n in members:
            node_comm[n] = cid

    cross_edges = []
    for u, v, d in G.edges(data=True):
        cu = node_comm.get(u, -1)
        cv = node_comm.get(v, -1)
        if cu != cv and cu >= 0 and cv >= 0:
            cross_edges.append({
                "source": G.nodes[u].get("label", u),
                "target": G.nodes[v].get("label", v),
                "source_community": cu,
                "target_community": cv,
                "relation": d.get("relation", "unknown"),
                "confidence": d.get("confidence", "EXTRACTED"),
                "evidence": d.get("evidence", ""),
            })

    # Sort by confidence: AMBIGUOUS first, then INFERRED, then EXTRACTED
    priority = {"AMBIGUOUS": 0, "INFERRED": 1, "EXTRACTED": 2}
    cross_edges.sort(key=lambda e: priority.get(e["confidence"], 99))
    return cross_edges[:top_n]

def suggest_questions(G: nx.Graph) -> List[str]:
    """Generate natural-language exploration questions."""
    questions = []
    degrees = dict(G.degree())
    # Isolated nodes
    isolated = [G.nodes[n].get("label", n) for n, deg in degrees.items() if deg == 0]
    if isolated:
        questions.append(f"Why are these entities isolated? {', '.join(isolated[:5])}")

    # High-degree hubs
    hubs = [G.nodes[n].get("label", n) for n, deg in sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:3]]
    if hubs:
        questions.append(f"What role do these core entities play in the architecture? {', '.join(hubs)}")

    # Cross-language connections (if present)
    langs = set()
    for n, d in G.nodes(data=True):
        sf = d.get("source_file", "")
        if sf.endswith(".py"): langs.add("Python")
        if sf.endswith(".js"): langs.add("JavaScript")
        if sf.endswith(".ts"): langs.add("TypeScript")
        if sf.endswith(".java"): langs.add("Java")
        if sf.endswith(".go"): langs.add("Go")
    if len(langs) > 1:
        questions.append(f"How do components across {', '.join(langs)} interact?")

    # Confidence mix
    conf_counter = Counter(d.get("confidence", "EXTRACTED") for _, _, d in G.edges(data=True))
    ambiguous = conf_counter.get("AMBIGUOUS", 0)
    if ambiguous > 0:
        questions.append(f"There are {ambiguous} ambiguous relationships — which ones need human review?")

    if not questions:
        questions.append("What is the overall purpose of this codebase?")
        questions.append("Which components are most critical to maintain?")

    return questions[:5]
