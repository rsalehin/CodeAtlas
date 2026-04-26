"""Plain-language audit report generator."""
import networkx as nx
from pathlib import Path
from typing import Dict, List

def generate_report(G: nx.Graph, communities: Dict[int, List[str]],
                    god_nodes: List[dict], surprises: List[dict],
                    questions: List[str]) -> str:
    """Produce GRAPH_REPORT.md as a string."""
    lines = []
    lines.append("# CodeAtlas Graph Report\n")
    lines.append(f"**Nodes:** {G.number_of_nodes()}  |  **Edges:** {G.number_of_edges()}  |  **Communities:** {len(communities)}\n")

    # Confidence breakdown
    from collections import Counter
    conf_counter = Counter(d.get("confidence", "EXTRACTED") for _, _, d in G.edges(data=True))
    lines.append("## Confidence Breakdown\n")
    lines.append(f"| Confidence | Count |")
    lines.append(f"|------------|-------|")
    for conf in ["EXTRACTED", "INFERRED", "AMBIGUOUS"]:
        count = conf_counter.get(conf, 0)
        lines.append(f"| {conf} | {count} |")
    lines.append("")

    # God nodes
    lines.append("## Core Abstractions (God Nodes)\n")
    for item in god_nodes[:5]:
        lines.append(f"- **{item['label']}** — degree {item['degree']}, community {item['community']}")
    lines.append("")

    # Community overview
    lines.append("## Community Structure\n")
    for cid, members in sorted(communities.items()):
        labels = [G.nodes[n].get("label", n) for n in members[:3]]
        suffix = " ..." if len(members) > 3 else ""
        lines.append(f"- **Community {cid}** ({len(members)} nodes): {', '.join(labels)}{suffix}")
    lines.append("")

    # Surprising connections
    if surprises:
        lines.append("## Surprising Connections\n")
        for s in surprises:
            lines.append(
                f"- **{s['source']}** → **{s['target']}** "
                f"({s['relation']}, {s['confidence']}, communities {s['source_community']}↔{s['target_community']})"
            )
        lines.append("")

    # Knowledge gaps
    isolated = [G.nodes[n].get("label", n) for n, deg in G.degree() if deg == 0]
    if isolated:
        lines.append("## Knowledge Gaps\n")
        lines.append(f"Entities with no connections: {', '.join(isolated[:10])}")
        lines.append("")

    # Suggested questions
    lines.append("## Suggested Questions\n")
    for q in questions:
        lines.append(f"- {q}")
    lines.append("")

    return "\n".join(lines)

def save_report(report_text: str, out_path: Path):
    out_path.write_text(report_text, encoding="utf-8")
    print(f"  Report saved to {out_path}")
