import re
import sys
import os
from datetime import datetime

def get_page_rank_scores_as_map(path_to_scores: str) -> dict[str, float]:
    """
    Reads a PageRank score file where each line has the format:
        <signature> | score

    Example line:
        <java.util.List: java.util.Iterator iterator()> | 0.01638346390050937

    Returns:
        A dictionary mapping the FULL RAW method signature string to its score.
        Keys remain in the angle bracket format so they can match the call graph.
    """
    scores = {}

    with open(path_to_scores, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue

            raw_sig, score_str = line.split("|", 1)
            raw_sig = raw_sig.strip()        # keep the "<...>" form as-is
            score = float(score_str.strip())  # convert score to float

            scores[raw_sig] = score

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

    # split "class: return method(params)"
    cls, rest = inner.split(":", 1)
    cls_short = cls.split(".")[-1]

    # extract method name before '(' and after space
    method = rest.strip().split("(")[0]  # "void <init>"
    method = method.split()[-1]          # "<init>"

    return f"{cls_short}.{method}"


def convert_to_clean_graphviz(input_str: str, scores_map: dict[str, float]) -> str:
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
        lines.append(f'    subgraph "cluster_{safe_cls}" {{')
        lines.append(f'        label = "{cls}";')
        lines.append('        style=rounded;')

        for raw in sorted(raw_nodes):
            simplified = simplify_method_label(raw)
            method_only = simplified.split(".", 1)[1]

            score = scores_map.get(raw, None)
            if score is not None:
                label = f"{method_only}\\n({score:.4f})"
            else:
                label = method_only

            lines.append(f'        "{raw}" [label="{label}"];')

        lines.append('    }')

    # ✅ Add edges, node IDs remain RAW
    for src_raw, dst_raw, label in edges:
        if label:
            lines.append(f'    "{src_raw}" -> "{dst_raw}" [label="{label}"];')
        else:
            lines.append(f'    "{src_raw}" -> "{dst_raw}";')

    lines.append('}')
    return "\n".join(lines)


def main(graph_raw_path: str, scores_path: str) -> None:
    # Read raw DOT
    with open(graph_raw_path, "r") as f:
        raw = f.read()

    scores = get_page_rank_scores_as_map(scores_path)

    clean = convert_to_clean_graphviz(raw, scores)

    os.makedirs("out", exist_ok=True)

    # ✅ Create timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = f"out/graph_clean_{timestamp}.dot"

    with open(output_path, "w") as f:
        f.write(clean)

    with open("out/graph_clean_temp.dot", "w") as f:
        f.write(clean)

    print(f"✅ Wrote cleaned file: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python format_call_graph_dot_export.py <graphPath> <scoresPath>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
