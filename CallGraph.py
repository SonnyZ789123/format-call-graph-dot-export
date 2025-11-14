import re
from typing import TypeAlias, Final


Node: TypeAlias = str
Edge: TypeAlias = tuple[str, str, str | None]
EdgeKey: TypeAlias = str


class CallGraph:
    # A node represents a full method signature
    nodes: Final[set[Node]]

    # An edge is a tuple of (source method signature, destination method signature, optional label)
    edges: Final[list[Edge]]

    # A mapping from method signature to its score
    node_coverage: Final[dict[Node, float]]

    # A mapping from edge (source, destination, label) to its score
    edge_coverage: Final[dict[EdgeKey, float]]

    # A mapping from method signature to its ranking score
    graph_ranking: Final[dict[Node, float]]

    # Example lines to match:
    # "<com.kuleuven.library.domain.Librarian: void <init>(java.lang.String)>"                       ->"<com.kuleuven.library.domain.User: void <init>(java.lang.String)>"[label="6"]
    # "<com.kuleuven.library.actions.Library: void addItem(com.kuleuven.library.domain.LibraryItem)>"->"<java.util.List: boolean add(java.lang.Object)>"[label="23"]
    # "<com.kuleuven.library.impl.LoggingListener: void <init>()>"                                   ->"<java.lang.Object: void <init>()>"[label="6"]
    EDGE_KEY_PATTERN: Final = re.compile(r'^\"<.*>\"\s*->\s*\"<.*>\"$')

    def __init__(self,
                 nodes: set[Node],
                 edges: list[Edge],
                 node_coverage: dict[Node, float] = None,
                 edge_coverage: dict[EdgeKey, float] = None,
                 graph_ranking: dict[Node, float] = None) -> None:
        self.nodes = nodes
        self.edges = edges
        self.node_coverage = node_coverage if node_coverage is not None else {}
        self.edge_coverage = edge_coverage if edge_coverage is not None else {}
        self.graph_ranking = graph_ranking if graph_ranking is not None else {}


    def get_clusters(self) -> dict[str, list[Node]]:
        # Group nodes by class name extracted from *simplified* label (for clustering only)
        clusters = {}
        for raw_node_signature in self.nodes:
            simplified = self.simplify_method_signature(raw_node_signature)
            cls = simplified.split(".", 1)[0]
            clusters.setdefault(cls, []).append(raw_node_signature)

        return clusters


    def export_to_dot(self) -> str:
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

        clusters = self.get_clusters()

        # Add the lines for the nodes, and cluster the nodes
        for cls, raw_nodes in sorted(clusters.items()):
            safe_cls = re.sub(r'[^A-Za-z0-9_]', '_', cls)  # graphviz errors on special chars like $
            all_green = all(self.node_coverage.get(raw, 0) > 0 for raw in raw_nodes)

            lines.append(f'    subgraph "cluster_{safe_cls}" {{')
            lines.append(f'        label = "{cls}"; {"color=green; fontcolor=green;" if all_green else ""}')
            lines.append(f'        style=rounded; {"color=green;" if all_green else ""}')

            for raw_node_signature in sorted(raw_nodes):
                simplified = self.simplify_method_signature(raw_node_signature)
                method_only = simplified.split(".", 1)[1]

                score = self.graph_ranking.get(raw_node_signature, None)
                label_text = f"{method_only}\\n({score:.4f})" if score is not None else method_only

                # color the node green if node covered
                cov_score = self.node_coverage.get(raw_node_signature, 0)
                color_attr = 'color="green", fontcolor="green"' if cov_score > 0 else ""

                lines.append(f'        "{raw_node_signature}" [label="{label_text}" {color_attr}];')
            lines.append('    }')

        # Add the lines for the edges
        for src_raw, dst_raw, label in self.edges:
            edge_key = self.get_edge_key(src_raw, dst_raw)
            cov_score = 0
            # keys in JSON look like "<src>"->"<dst>" (already quoted inside)
            if edge_key in self.edge_coverage:
                cov_score += self.edge_coverage[edge_key]

            color_attr = 'color="green", fontcolor="green"' if cov_score > 0 else ''
            if label:
                lines.append(f'    "{src_raw}"->"{dst_raw}"[label="{label}" {color_attr}];')
            else:
                lines.append(f'    "{src_raw}"->"{dst_raw}"[{color_attr}];')

        lines.append('}')
        return "\n".join(lines)


    @staticmethod
    def is_valid_edge_key(edge_key: str):
        return CallGraph.EDGE_KEY_PATTERN.match(edge_key)


    @staticmethod
    def simplify_method_signature(full_method_signature: str) -> str:
        """
        Convert a full signature like:
        <com.kuleuven.library.Book: void <init>(java.lang.String)>
        into a short clean label:
        Book.<init>
        """
        # extract inside "< >"
        inner = full_method_signature.strip("<>")
        if ":" not in inner:
            return inner

        # split "class: return method(params)"
        cls, rest = inner.split(":", 1)
        cls_short = cls.split(".")[-1]

        # extract method name before '(' and after space
        method = rest.strip().split("(")[0]  # "void <init>"
        method = method.split()[-1]  # "<init>"

        return f"{cls_short}.{method}"


    @staticmethod
    def get_edge_key(src_method: str, dst_method: str) -> str:
        """Return a formatted edge key like: "<src>"->"<dst>"

        Parameters:
            src_method: Full source method signature
            dst_method: Full destination method signature
        """
        return f'"{src_method}"->"{dst_method}"'


