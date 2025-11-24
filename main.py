import re
import sys
import os
import json
from datetime import datetime

from CallGraph import CallGraph


def load_json_key_float_dictionary(path: str | None) -> dict[str, float]:
    """Load JSON as a dict of keys and floats. Returns empty dict if path missing or invalid."""
    if not path or not os.path.exists(path):
        print(f"⚠️  JSON file not found or not provided: {path}")
        return {}
    with open(path, "r") as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} entries from {path}")
    return data


def extract_nodes_and_edges_from_raw_dot_file(raw_dot_str: str) -> tuple[set[str], list[tuple[str, str, str | None]]]:
    edges = []
    nodes = set()

    pattern = re.compile(r'^\"<.*>\"\s*->\s*\"<.*>\"\[label=".*"]$')

    for line in raw_dot_str.splitlines():
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

    return nodes, edges


def main(graph_raw_path: str,
         output_file_name: str,
         graph_ranking_path: str | None = None,
         node_cov_path: str | None = None,
         edge_cov_path: str | None = None) -> None:
    with open(graph_raw_path, "r") as f:
        raw = f.read()

    scores = load_json_key_float_dictionary(graph_ranking_path)
    node_cov = load_json_key_float_dictionary(node_cov_path)
    edge_cov = load_json_key_float_dictionary(edge_cov_path)

    nodes, edges = extract_nodes_and_edges_from_raw_dot_file(raw)

    call_graph = CallGraph(nodes, edges, node_coverage=node_cov, edge_coverage=edge_cov, graph_ranking=scores)

    dot_export = call_graph.export_to_dot()

    os.makedirs("out", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = f"out/{output_file_name}.dot"

    with open(f"out/{output_file_name}_{timestamp}.dot", "w") as f:
        f.write(dot_export)
    with open(output_path, "w") as f:
        f.write(dot_export)
    print(f"✅ Wrote cleaned file: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python format_call_graph_dot_export.py <rawGraphPath> <outputFileName> [nodeCoverage.json] [edgeCoverage.json] [rankingPath]")
        sys.exit(1)

    graph_path = sys.argv[1]
    output_file_name = sys.argv[2]
    ranking_path = sys.argv[3] if len(sys.argv) >= 4 else None
    node_cov_path = sys.argv[4] if len(sys.argv) >= 5 else None
    edge_cov_path = sys.argv[5] if len(sys.argv) >= 6 else None

    main(graph_path, output_file_name, graph_ranking_path=ranking_path, node_cov_path=node_cov_path, edge_cov_path=edge_cov_path)
