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

    # ✅ Convert "<init>" into a cleaner label
    method = method.replace("<init>", "constructor")

    return f"{cls_short}.{method}"


def convert_to_clean_graphviz(input_str: str) -> str:
    edges = []
    nodes = set()
    pattern = re.compile(
        r'"?<([^>]+)>"?\s*->\s*"?<([^>]+)>"?\s*(?:\[\s*label\s*=\s*"([^"]+)"\s*\])?'
    )

    for line in input_str.splitlines():
        match = pattern.search(line)
        if not match:
            continue

        src_raw, dst_raw, label = match.groups()

        src = simplify_method_label(f"<{src_raw}>")
        dst = simplify_method_label(f"<{dst_raw}>")

        edges.append((src, dst, label))
        nodes.add(src)
        nodes.add(dst)

    # Group nodes by class = text before the first "."
    clusters = {}
    for node in nodes:
        cls = node.split(".", 1)[0]
        clusters.setdefault(cls, []).append(node)

    lines = [
        'digraph ObjectGraph {',
        '    rankdir=LR;',
        '    graph [',
        '        ranksep=1.8,',  # Keep vertical spacing tight
        '        nodesep=0.1,',  # Increase horizontal spacing
        '        overlap=false,',
        '        splines=true',
        '    ];',
        '    node [shape=box, fontsize=10];'
    ]

    # Create subgraph clusters
    for cls, class_nodes in sorted(clusters.items()):
        lines.append(f'    subgraph cluster_{cls} {{')
        lines.append(f'        label = "{cls}";')
        lines.append('        style=rounded;')
        for n in sorted(class_nodes):
            method_only = n.split(".", 1)[1]  # ✅ remove class name
            lines.append(f'        "{n}" [label="{method_only}"];')
        lines.append('    }')

    # ✅ Add edges with labels preserved
    for src, dst, label in edges:
        if label:
            lines.append(f'    "{src}" -> "{dst}" [label="{label}"];')
        else:
            lines.append(f'    "{src}" -> "{dst}";')

    lines.append('}')
    return "\n".join(lines)


def main(graph_raw_path: str) -> None:
    # Read raw DOT
    with open(graph_raw_path, "r") as f:
        raw = f.read()

    clean = convert_to_clean_graphviz(raw)

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
        print("Usage: python format_call_graph_dot_export.py <graphPath>")
        sys.exit(1)

    main(sys.argv[1])
