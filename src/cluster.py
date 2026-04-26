"""Topology-only community detection — Leiden / Louvain, no embeddings."""
import networkx as nx
from typing import Dict, List, Any

def cluster(G: nx.Graph) -> Dict[int, List[str]]:
    if G.number_of_nodes() == 0:
        return {}

    H = G.to_undirected() if G.is_directed() else G.copy()

    raw: Any = None

    # 1. Try Louvain (built-in, reliable)
    try:
        from networkx.algorithms.community import louvain_communities
        raw = louvain_communities(H, seed=42)
    except Exception:
        pass

    # 2. Fall back to connected components
    if raw is None:
        raw = [list(comp) for comp in nx.connected_components(H)]

    # Normalise
    partitions: Dict[int, List[str]] = {}
    for i, comm in enumerate(raw):
        if isinstance(comm, (list, set)):
            partitions[i] = [str(n) for n in comm]
        else:
            partitions[i] = [str(comm)]

    # If every community is size 1, use connected components instead
    if all(len(v) == 1 for v in partitions.values()):
        comps = [list(c) for c in nx.connected_components(H)]
        partitions = {i: [str(n) for n in c] for i, c in enumerate(comps)}
        print("  (Leiden gave singletons → using connected components)")

    # Add isolates
    all_assigned = set()
    for nodes in partitions.values():
        all_assigned.update(nodes)
    isolates = [str(n) for n in H.nodes() if str(n) not in all_assigned]
    next_id = max(partitions.keys()) + 1 if partitions else 0
    for n in isolates:
        partitions[next_id] = [n]
        next_id += 1

    # Split oversized communities (> 25% of graph, min 10 nodes)
    threshold = max(10, int(H.number_of_nodes() * 0.25))
    split_again: Dict[int, List[str]] = {}
    remove_keys = []
    next_id = max(partitions.keys()) + 1 if partitions else 0
    for cid, members in list(partitions.items()):
        if len(members) > threshold:
            sub = H.subgraph(members)
            try:
                from networkx.algorithms.community import louvain_communities
                sub_raw = louvain_communities(sub, seed=42)
                for sub_comm in sub_raw:
                    split_again[next_id] = [str(n) for n in sub_comm]
                    next_id += 1
                remove_keys.append(cid)
            except Exception:
                pass
    for k in remove_keys:
        del partitions[k]
    partitions.update(split_again)

    # Re-number so community 0 is the largest
    sorted_comms = sorted(partitions.values(), key=len, reverse=True)
    return {i: sorted_comms[i] for i in range(len(sorted_comms))}
