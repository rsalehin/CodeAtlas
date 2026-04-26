"""Merges extractions into a NetworkX graph with confidence priority and target resolution."""
import networkx as nx
from typing import List, Set, Dict, Tuple

STDLIB_BUILTINS: Set[str] = {
    "print","len","range","int","str","float","bool","list","dict",
    "set","tuple","type","isinstance","super","enumerate","zip","map",
    "filter","open","input","Exception","ValueError","TypeError",
    "KeyError","IndexError","BaseException","object",
    "os","sys","json","re","pathlib","Path","datetime","collections",
    "itertools","functools","typing","io","pathlib.Path",
    "System","String","Integer","List","ArrayList","Map","HashMap",
    "java.util","java.io","java.lang",
    "fmt","errors","strings","strconv","time","context",
    "console","Math","JSON","Array","Object","String","Number",
}

CONFIDENCE_RANK = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}

def build_graph(extractions: List[dict], directed: bool = False) -> nx.Graph:
    G = nx.DiGraph() if directed else nx.Graph()
    label_to_ids: Dict[str, List[str]] = {}
    edge_best_conf: Dict[Tuple[str, str], str] = {}

    # First pass: add all declared nodes
    for ext in extractions:
        for node in ext.get("nodes", []):
            nid = node["id"]
            label = node.get("label", "")
            G.add_node(nid,
                       label=label,
                       source_file=node.get("source_file", ""),
                       source_location=node.get("source_location", "L1"))
            label_to_ids.setdefault(label, []).append(nid)

    def resolve_target(raw_target: str, src: str) -> str:
        """If raw_target is a bare name, try to find a real node with that label
        (preferring cross-file candidates). Return the best match or the original."""
        candidates = label_to_ids.get(raw_target, [])
        if not candidates:
            return raw_target
        if raw_target in G.nodes:
            return raw_target   # already a real node ID
        src_file = G.nodes[src].get("source_file", src) if src in G.nodes else src
        cross = [c for c in candidates if G.nodes[c].get("source_file", c) != src_file]
        same = [c for c in candidates if G.nodes[c].get("source_file", c) == src_file]
        best = (cross or same or candidates)
        return best[0]

    # Second pass: add edges with target resolution
    for ext in extractions:
        for edge in ext.get("edges", []):
            src = edge["source"]
            tgt = edge["target"]
            rel = edge.get("relation", "unknown")
            conf = edge.get("confidence", "EXTRACTED")

            if tgt in STDLIB_BUILTINS and rel != "contains":
                continue

            # Ensure source exists (create file node if needed)
            if src not in G.nodes:
                lbl = src.rsplit("/",1)[-1] if "/" in src else src
                G.add_node(src, label=lbl, source_file=src, source_location="L0")
                label_to_ids.setdefault(lbl, []).append(src)

            # Resolve target to a real node if possible
            resolved = resolve_target(tgt, src)

            # Ensure resolved target exists
            if resolved not in G.nodes:
                lbl = resolved.rsplit("/",1)[-1] if "/" in resolved else resolved
                G.add_node(resolved, label=lbl,
                          source_file=resolved if "/" in resolved else "",
                          source_location="L0")
                label_to_ids.setdefault(lbl, []).append(resolved)

            # Symbol resolution for calls: try to redirect to actual function node
            final_targets = [resolved]
            if rel == "calls" and conf == "INFERRED":
                candidates = label_to_ids.get(tgt, [])
                if candidates:
                    src_file = G.nodes[src].get("source_file", src)
                    cross = [c for c in candidates if G.nodes[c].get("source_file", c) != src_file]
                    same = [c for c in candidates if G.nodes[c].get("source_file", c) == src_file]
                    better = cross or same
                    if better:
                        final_targets = better

            for rt in final_targets:
                key = (src, rt)
                current_best = edge_best_conf.get(key, "")
                current_rank = CONFIDENCE_RANK.get(current_best, 0)
                new_rank = CONFIDENCE_RANK.get(conf, 0)

                if new_rank > current_rank:
                    edge_best_conf[key] = conf
                    if G.has_edge(src, rt):
                        G.remove_edge(src, rt)
                    G.add_edge(src, rt,
                               relation=rel,
                               confidence=conf,
                               confidence_score=edge.get("confidence_score", 1.0),
                               evidence=edge.get("evidence", ""))

    return G
