import re
import sys


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
    pattern = re.compile(r'"?<(.*?)>"?\s*->\s*"?<(.*?)>"?;')

    for line in input_str.splitlines():
        match = pattern.search(line)
        if not match:
            continue

        src = simplify_method_label(f"<{match.group(1)}>")
        dst = simplify_method_label(f"<{match.group(2)}>")
        edges.append((src, dst))
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

    # Add edges
    for src, dst in edges:
        lines.append(f'    "{src}" -> "{dst}";')

    lines.append('}')
    return "\n".join(lines)


def main(graph_raw_path: str) -> None:
    with open(graph_raw_path, "r") as f:
        raw = f.read()

    clean = convert_to_clean_graphviz(raw)

    with open("graph_clean.dot", "w") as f:
        f.write(clean)

    print("Wrote cleaned file: graph_clean.dot")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python format_call_graph_dot_export.py <graph_raw.dot>")
        sys.exit(1)

    main(sys.argv[1])
