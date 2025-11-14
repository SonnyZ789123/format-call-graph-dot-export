import re
import sys
import os
import json
from datetime import datetime


def load_json_coverage(path: str | None) -> dict[str, float]:
    """Load coverage JSON as a dict. Returns empty dict if path missing or invalid."""
    if not path or not os.path.exists(path):
        print(f"⚠️  Coverage file not found or not provided: {path}")
        return {}
    with open(path, "r") as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} coverage entries from {path}")
    return data


def get_graph_ranking_as_map(path_to_scores: str | None) -> dict[str, float]:
    """
    Reads a PageRank score file where each line has the format:
        <signature> | score

    If the path is None or doesn't exist, returns an empty dictionary.
    """
    scores = {}

    if not path_to_scores:
        print("ℹ️  No scores file provided — continuing without graph ranking.")
        return scores

    if not os.path.exists(path_to_scores):
        print(f"⚠️  Provided scores file not found: {path_to_scores} — ignoring.")
        return scores

    with open(path_to_scores, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue

            raw_sig, score_str = line.split("|", 1)
            raw_sig = raw_sig.strip()
            try:
                scores[raw_sig] = float(score_str.strip())
            except ValueError:
                continue

    print(f"✅ Loaded {len(scores)} graph ranking scores.")
    return scores


def simplify_method_label(raw_label: str) -> str:
    """
    Convert a full signature like:
    <com.kuleuven.library.Book: void <init>(java.lang.String)>
    into a short clean label:
    Book.constructor
    """
    # extract inside "< >"
    inner = raw_label.strip("<>")
    if ":" not in inner:
        return inner

    # split "class: return method(params)"
    cls, rest = inner.split(":", 1)
    cls_short = cls.split(".")[-1]

    # extract method name before '(' and after space
    method = rest.strip().split("(")[0]  # "void <init>"
    method = method.split()[-1]          # "<init>"

    return f"{cls_short}.{method}"


def convert_to_clean_graphviz(input_str: str, scores_map: dict[str, float],
                              node_cov: dict[str, float], edge_cov: dict[str, float]) -> str:
    edges = []
    nodes = set()

    # Example lines to match:
    # "<com.kuleuven.library.domain.Librarian: void <init>(java.lang.String)>"                       ->"<com.kuleuven.library.domain.User: void <init>(java.lang.String)>"[label="6"]
    # "<com.kuleuven.library.actions.Library: void addItem(com.kuleuven.library.domain.LibraryItem)>"->"<java.util.List: boolean add(java.lang.Object)>"[label="23"]
    # "<com.kuleuven.library.impl.LoggingListener: void <init>()>"                                   ->"<java.lang.Object: void <init>()>"[label="6"]
    pattern = re.compile(r'^\"<.*>\"\s*->\s*\"<.*>\"\[label=".*"]$')

    for line in input_str.splitlines():
        line = line.strip()
        if not pattern.match(line):
            continue

        # 1) Split source and rest
        if "->" not in line:
            continue
        left, right = line.split("->", 1)

        # 2) Extract label
        label = None
        if "[label" in right:
            right, label_part = right.split("[label", 1)
            label = label_part.split("\"")[1]  # extract between quotes

        # 3) Clean up identifiers
        src_raw_full = left.strip().strip("\"")
        dst_raw_full = right.strip().strip("\"").rstrip(";")

        edges.append((src_raw_full, dst_raw_full, label))
        nodes.add(src_raw_full)
        nodes.add(dst_raw_full)

    # Group nodes by class name extracted from *simplified* label (for clustering only)
    clusters = {}
    for raw in nodes:
        simplified = simplify_method_label(raw)
        cls = simplified.split(".", 1)[0]
        clusters.setdefault(cls, []).append(raw)

    lines = [
        'digraph ObjectGraph {',
        '    rankdir=LR;',
        '    graph [',
        '        ranksep=1.8,',  # vertical spacing
        '        nodesep=0.1,',  # horizontal spacing
        '        overlap=false,',
        '        splines=true',
        '    ];',
        '    node [shape=box, fontsize=10];'
    ]

    # ✅ Create clusters, display simplified method name with score if available
    for cls, raw_nodes in sorted(clusters.items()):
        safe_cls = re.sub(r'[^A-Za-z0-9_]', '_', cls) # graphviz errors on special chars like $
        all_green = all(node_cov.get(raw, 0) > 0 for raw in raw_nodes)

        lines.append(f'    subgraph "cluster_{safe_cls}" {{')
        lines.append(f'        label = "{cls}"; {"color=green; fontcolor=green;" if all_green else ""}')
        lines.append(f'        style=rounded; {"color=green;" if all_green else ""}')


        for raw in sorted(raw_nodes):
            simplified = simplify_method_label(raw)
            method_only = simplified.split(".", 1)[1]

            score = scores_map.get(raw, None)
            label_text = f"{method_only}\\n({score:.4f})" if score is not None else method_only

            # color the node green if node covered
            cov_score = node_cov.get(raw, 0)
            if cov_score > 0:
                color_attr = 'color="green", fontcolor="green"'
            else:
                color_attr = ''

            lines.append(f'        "{raw}" [label="{label_text}" {color_attr}];')
        lines.append('    }')

    # ✅ Add edges, node IDs remain RAW
    for src_raw, dst_raw, label in edges:
        edge_key = f'"{src_raw}"->"{dst_raw}"'
        cov_score = 0
        # keys in JSON look like "<src>"->"<dst>" (already quoted inside)
        if edge_key in edge_cov:
            cov_score += edge_cov[edge_key]

        color_attr = 'color="green", fontcolor="green"' if cov_score > 0 else ''
        if label:
            lines.append(f'    "{src_raw}"->"{dst_raw}"[label="{label}" {color_attr}];')
        else:
            lines.append(f'    "{src_raw}"->"{dst_raw}"[{color_attr}];')

    lines.append('}')
    return "\n".join(lines)


def main(graph_raw_path: str, output_file_name: str,
         graph_ranking_path: str | None = None,
         node_cov_path: str | None = None,
         edge_cov_path: str | None = None) -> None:
    with open(graph_raw_path, "r") as f:
        raw = f.read()

    scores = get_graph_ranking_as_map(graph_ranking_path)
    node_cov = load_json_coverage(node_cov_path)
    edge_cov = load_json_coverage(edge_cov_path)

    clean = convert_to_clean_graphviz(raw, scores, node_cov, edge_cov)

    os.makedirs("out", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = f"out/{output_file_name}.dot"

    with open(f"out/{output_file_name}_{timestamp}.dot", "w") as f:
        f.write(clean)
    with open(output_path, "w") as f:
        f.write(clean)
    print(f"✅ Wrote cleaned file: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python format_call_graph_dot_export.py <rawGraphPath> <outputFileName> [nodeCoverage.json] [edgeCoverage.json] [rankingPath]")
        sys.exit(1)

    graph_path = sys.argv[1]
    output_file_name = sys.argv[2]
    node_cov_path = sys.argv[3] if len(sys.argv) >= 4 else None
    edge_cov_path = sys.argv[4] if len(sys.argv) >= 5 else None
    ranking_path = sys.argv[5] if len(sys.argv) >= 6 else None

    main(graph_path, output_file_name, ranking_path, node_cov_path, edge_cov_path)
