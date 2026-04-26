import tree_sitter_languages
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple

QUERIES = {
    "python": {
        "function": "(function_definition name: (identifier) @name) @def",
        "class": "(class_definition name: (identifier) @name) @def",
        "import": "(import_statement) @import",
        "import_from": "(import_from_statement) @import",
        "call": "(call function: (identifier) @callee) @call",
    },
    "javascript": {
        "function": "(function_declaration name: (identifier) @name) @def",
        "class": "(class_declaration name: (identifier) @name) @def",
        "import": "(import_statement) @import",
        "call": "(call_expression function: (identifier) @callee) @call",
    },
    "typescript": {
        "function": "(function_declaration name: (identifier) @name) @def",
        "class": "(class_declaration name: (identifier) @name) @def",
        "import": "(import_statement) @import",
        "call": "(call_expression function: (identifier) @callee) @call",
    },
    "java": {
        "function": "(method_declaration name: (identifier) @name) @def",
        "class": "(class_declaration name: (identifier) @name) @def",
        "import": "(import_declaration) @import",
        "call": "(method_invocation name: (identifier) @callee) @call",
    },
    "go": {
        "function": "(function_declaration name: (identifier) @name) @def",
        "struct": "(type_declaration (type_spec name: (type_identifier) @name type: (struct_type)) @def)",
        "interface": "(type_declaration (type_spec name: (type_identifier) @name type: (interface_type)) @def)",
        "import": "(import_declaration) @import",
        "call": "(call_expression function: (identifier) @callee) @call",
    },
}

EXT_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".go": "go",
}

def get_language(file_path: Path) -> Optional[str]:
    return EXT_MAP.get(file_path.suffix)

def node_text(code: bytes, node) -> str:
    return code[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

def is_descendant(parent, node):
    while node is not None:
        if node == parent:
            return True
        node = node.parent
    return False

def _extract_module_name(text: str) -> Optional[str]:
    """Heuristic to extract the module name from an import statement.
    Returns the module (e.g., 'os', 'mcp.server') or None.
    """
    # Remove line continuations and extra spaces
    text = ' '.join(text.split())
    # Handle 'from X import Y'
    if text.startswith('from ') and ' import ' in text:
        # text like "from mcp.server import Server"
        prefix = text[5:]                 # remove "from "
        module = prefix.split(' import ')[0].strip()
        return module
    # Handle 'import X' or 'import X, Y'
    if text.startswith('import '):
        rest = text[7:]                   # remove "import "
        # Take the first module name, stripping any trailing comma/semicolon
        module = rest.split()[0].rstrip(',;')
        return module
    return None

def extract_file(file_path: Path, root: Path = None) -> dict:
    lang_name = get_language(file_path)
    if lang_name is None:
        return {"nodes": [], "edges": []}

    language = tree_sitter_languages.get_language(lang_name)
    parser = tree_sitter_languages.get_parser(lang_name)
    code = file_path.read_bytes()
    tree = parser.parse(code)
    queries = QUERIES.get(lang_name)
    if not queries:
        return {"nodes": [], "edges": []}

    nodes: List[dict] = []
    edges: List[dict] = []
    node_ids: Set[str] = set()
    edge_keys: Set[Tuple] = set()
    if root:
        file_id = str(file_path.relative_to(root)).replace("\\", "/")
    else:
        file_id = str(file_path).replace("\\", "/")

    def add_node(kind: str, label: str, row: int) -> str:
        node_id = f"{file_id}::{kind}:{label}"
        if node_id in node_ids:
            return node_id
        node_ids.add(node_id)
        nodes.append({
            "id": node_id,
            "label": label,
            "source_file": file_id,
            "source_location": f"L{row}",
        })
        return node_id

    def add_edge(src: str, tgt: str, rel: str, conf: str):
        key = (src, tgt, rel)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append({
            "source": src,
            "target": tgt,
            "relation": rel,
            "confidence": conf,
        })

    def run_pattern(pattern: str) -> Dict[str, List]:
        query = language.query(pattern)
        raw = query.captures(tree.root_node)
        result: Dict[str, List] = {}
        for node, name in raw:
            result.setdefault(name, []).append(node)
        return result

    # 1. Definitions
    for kind, qkey in [("class", "class"), ("function", "function"),
                       ("struct", "struct"), ("interface", "interface")]:
        pattern = queries.get(qkey)
        if not pattern:
            continue
        patterns = [pattern] if not isinstance(pattern, list) else pattern
        for pat in patterns:
            captures = run_pattern(pat)
            def_nodes = captures.get("def", [])
            name_nodes = captures.get("name", [])
            for def_node in def_nodes:
                name_str = None
                for n in name_nodes:
                    if is_descendant(def_node, n):
                        name_str = node_text(code, n)
                        break
                if name_str:
                    add_node(kind, name_str, def_node.start_point[0] + 1)

    # 2. Contains edges
    for kind, qkey in [("class", "class"), ("struct", "struct"), ("interface", "interface")]:
        pattern = queries.get(qkey)
        if not pattern:
            continue
        patterns = [pattern] if not isinstance(pattern, list) else pattern
        for pat in patterns:
            captures = run_pattern(pat)
            class_defs = captures.get("def", [])
            class_names = captures.get("name", [])
            for class_def in class_defs:
                class_name = None
                for n in class_names:
                    if is_descendant(class_def, n):
                        class_name = node_text(code, n)
                        break
                if not class_name:
                    continue
                class_id = f"{file_id}::{kind}:{class_name}"
                for method_kind, mqkey in [("function", "function"), ("struct", "struct"), ("interface", "interface")]:
                    mp = queries.get(mqkey)
                    if not mp:
                        continue
                    mpats = [mp] if not isinstance(mp, list) else mp
                    for mpat in mpats:
                        mcaptures = run_pattern(mpat)
                        mdefs = mcaptures.get("def", [])
                        mnames = mcaptures.get("name", [])
                        for mdef in mdefs:
                            if is_descendant(class_def, mdef):
                                mname = None
                                for mn in mnames:
                                    if is_descendant(mdef, mn):
                                        mname = node_text(code, mn)
                                        break
                                if mname:
                                    method_id = f"{file_id}::{method_kind}:{mname}"
                                    add_edge(class_id, method_id, "contains", "EXTRACTED")

    # 3. Imports (FIXED)
    import_patterns = []
    if "import" in queries:
        import_patterns.append(queries["import"])
    if "import_from" in queries:
        import_patterns.append(queries["import_from"])
    for pat in import_patterns:
        captures = run_pattern(pat)
        for import_node in captures.get("import", []):
            text = node_text(code, import_node)
            module = _extract_module_name(text)
            if not module:
                continue
            # Try to resolve to a known file in the project
            target_file = None
            for nid in list(node_ids):
                nid_file = nid.split("::")[0]
                suffixes = [".py", ".js", ".ts", ".java", ".go"]
                for sfx in suffixes:
                    if nid_file.endswith(f"/{module}{sfx}"):
                        target_file = nid_file
                        break
                if target_file:
                    break
                if module in nid_file:
                    target_file = nid_file
                    break
            if target_file:
                add_edge(file_id, target_file, "imports_from", "EXTRACTED")
            else:
                add_edge(file_id, module, "imports", "EXTRACTED")

    # 4. Call edges
    call_pattern = queries.get("call")
    if call_pattern:
        captures = run_pattern(call_pattern)
        call_nodes = captures.get("call", [])
        callee_nodes = captures.get("callee", [])
        for call_node in call_nodes:
            callee_name = None
            for callee_node in callee_nodes:
                if is_descendant(call_node, callee_node):
                    callee_name = node_text(code, callee_node)
                    break
            if callee_name:
                caller_id = file_id
                parent = call_node.parent
                while parent is not None:
                    found = False
                    for kind, qkey in [("function", "function"), ("class", "class"), ("struct", "struct"), ("interface", "interface")]:
                        pk = queries.get(qkey)
                        if not pk:
                            continue
                        pk_list = [pk] if not isinstance(pk, list) else pk
                        for p in pk_list:
                            pc = run_pattern(p)
                            pdefs = pc.get("def", [])
                            if parent in pdefs:
                                pnames = pc.get("name", [])
                                enc_name = None
                                for n in pnames:
                                    if is_descendant(parent, n):
                                        enc_name = node_text(code, n)
                                        break
                                if enc_name:
                                    caller_id = f"{file_id}::{kind}:{enc_name}"
                                    found = True
                                    break
                        if found:
                            break
                    if found:
                        break
                    parent = parent.parent
                add_edge(caller_id, callee_name, "calls", "INFERRED")

    return {"nodes": nodes, "edges": edges}
