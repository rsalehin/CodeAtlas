"""Semantic extraction: uses Claude to find inferred relationships, plus demo JSON fallback."""
from pathlib import Path
from typing import List, Dict, Set
import json
from src.llm import extract_semantic_relationships

def extract_from_directory(root: Path, code_extensions: set) -> dict:
    nodes = []
    edges = []
    seen_ids: Set[str] = set()
    file_contents: Dict[str, str] = {}
    root_id = str(root.resolve()).replace("\\", "/")

    readable_exts = {".md", ".txt", ".rst", ".cfg", ".toml", ".yaml", ".yml", ".json"}

    # Load hard-coded demo relationships if present
    relationships_path = root / "relationships.json"
    if relationships_path.exists():
        try:
            demo_data = json.loads(relationships_path.read_text(encoding="utf-8"))
            for node in demo_data.get("nodes", []):
                nid = node["id"]
                if nid not in seen_ids:
                    seen_ids.add(nid)
                    nodes.append(node)
            for edge in demo_data.get("edges", []):
                edges.append(edge)
            print(f"  Loaded {len(demo_data.get('nodes', []))} nodes and {len(demo_data.get('edges', []))} edges from relationships.json")
        except Exception as e:
            print(f"  relationships.json error: {e}")

    # Collect readable non-code files
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in readable_exts and path.name != "relationships.json":
            try:
                content = path.read_text(encoding="utf-8", errors="replace")[:3000]
                rel = str(path.relative_to(root)).replace("\\", "/")
                file_id = f"{root_id}/{rel}"
                file_contents[file_id] = content
                if file_id not in seen_ids:
                    seen_ids.add(file_id)
                    nodes.append({
                        "id": file_id,
                        "label": rel,
                        "source_file": file_id,
                        "source_location": "L1",
                    })
            except Exception:
                continue

    # Call Claude for additional edges
    if file_contents:
        print(f"  Asking Claude to analyze {len(file_contents)} documents...")
        try:
            relationships = extract_semantic_relationships(file_contents)
            for rel in relationships:
                src = rel.get("source", "")
                tgt = rel.get("target", "")
                relation = rel.get("relation", "semantically_similar_to")
                confidence = rel.get("confidence", 0.5)
                evidence = rel.get("evidence", "")

                def resolve_id(partial: str) -> str:
                    if "/" in partial and partial.startswith(root_id.split("/")[0]):
                        return partial
                    for fid in file_contents:
                        if partial in fid or fid.endswith(partial):
                            return fid
                    return partial

                src_full = resolve_id(src)
                tgt_full = resolve_id(tgt)

                edges.append({
                    "source": src_full,
                    "target": tgt_full,
                    "relation": relation,
                    "confidence": "INFERRED",
                    "confidence_score": confidence,
                    "evidence": evidence,
                })
        except Exception as e:
            print(f"  Claude call skipped: {e}")

    return {"nodes": nodes, "edges": edges}
