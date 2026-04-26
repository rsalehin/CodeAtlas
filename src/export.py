"""Interactive HTML export using PyVis."""
import networkx as nx
from pathlib import Path

def to_html(G: nx.Graph, out_path: Path, communities: dict = None):
    """Generate an interactive graph.html with community colors."""
    from pyvis.network import Network

    net = Network(height="750px", width="100%", bgcolor="#1a1a2e", font_color="white", directed=G.is_directed())
    net.set_options("""
    {
      "physics": {
        "barnesHut": { "gravitationalConstant": -3000, "centralGravity": 0.3, "springLength": 150 },
        "minVelocity": 0.75
      },
      "interaction": { "hover": true, "tooltipDelay": 100 }
    }
    """)

    # Community colours (12 distinct hues)
    colours = [
        "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4",
        "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990", "#dcbeff"
    ]

    for n, d in G.nodes(data=True):
        cid = d.get("community", -1)
        color = colours[cid % len(colours)] if cid >= 0 else "#888888"
        label = d.get("label", n)
        # Truncate long labels for display
        display_label = label if len(label) < 40 else label[:37] + "..."
        title = f"{label}<br>File: {d.get('source_file', 'N/A')}<br>Community: {cid}"
        net.add_node(n, label=display_label, title=title, color=color)

    for u, v, d in G.edges(data=True):
        relation = d.get("relation", "unknown")
        confidence = d.get("confidence", "EXTRACTED")
        title = f"{relation}<br>{confidence}"
        width = 2 if confidence == "EXTRACTED" else 1.5
        color = "#00ff88" if confidence == "EXTRACTED" else "#ffaa00"
        net.add_edge(u, v, title=title, width=width, color=color, arrows="to" if G.is_directed() else "")

    net.write_html(str(out_path))
    print(f"  Interactive graph saved to {out_path}")
