import re
from typing import TypeAlias, Final
from pprint import pprint

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


        node_color_map = self.get_color_map(self.node_coverage)
        print("\n🟩 Node Color Map:")
        pprint(node_color_map, sort_dicts=False)

        edge_color_map = self.get_color_map(self.edge_coverage)
        print("\n🟩 Edge Color Map:")
        pprint(edge_color_map, sort_dicts=False)

        clusters = self.get_clusters()

        # Add the lines for the nodes, and cluster the nodes
        for cls, raw_nodes in sorted(clusters.items()):
            safe_cls = re.sub(r'[^A-Za-z0-9_]', '_', cls)  # graphviz errors on special chars like $
            all_green = all(raw in node_color_map for raw in raw_nodes)

            lines.append(f'    subgraph "cluster_{safe_cls}" {{')
            lines.append(f'        label = "{cls}"; {"color=green; fontcolor=green;" if all_green else ""}')
            lines.append(f'        style=rounded; {"color=green;" if all_green else ""}')

            for raw_node_signature in sorted(raw_nodes):
                simplified = self.simplify_method_signature(raw_node_signature)
                method_only = simplified.split(".", 1)[1]

                score = self.graph_ranking.get(raw_node_signature, None)
                label_text = f"{method_only}\\n({score:.4f})" if score is not None else method_only

                # color the node green if node covered
                color = node_color_map.get(raw_node_signature, (0.0, None))[1]
                color_attr = f'color="{color}", fontcolor="{color}"' if color is not None else ""

                lines.append(f'        "{raw_node_signature}" [label="{label_text}" {color_attr}];')
            lines.append('    }')

        # Add the lines for the edges
        for src_raw, dst_raw, label in self.edges:
            edge_key = self.get_edge_key(src_raw, dst_raw)

            color = edge_color_map.get(edge_key, (0.0, None))[1]
            color_attr = f'color="{color}", fontcolor="{color}"' if color is not None else ""
            if label:
                lines.append(f'    "{src_raw}"->"{dst_raw}"[label="{label}" {color_attr}];')
            else:
                lines.append(f'    "{src_raw}"->"{dst_raw}"[{color_attr}];')

        lines.append('}')
        return "\n".join(lines)


    def get_color_map(self, coverage: dict[str, float]) -> dict[str, tuple[float, str]]:
        """
        Generalized function to create a color map for a given coverage dictionary.
        - Filters uncovered items
        - Normalizes covered values
        - Maps to green intensity via _get_green_intensity(score)

        Returns:
            A dictionary mapping each key -> (normalized_score, color_hex)
        """
        filtered = self._filter_covered(coverage)
        normalized = self._normalize_coverage(filtered)

        color_map: Final[dict[str, tuple[float, str]]] = {
            k: (v, self._get_green_intensity(v)) for k, v in normalized.items()
        }
        return color_map


    @staticmethod
    def _filter_covered(coverage: dict[str, float]) -> dict[str, float]:
        """
        Filter a coverage dictionary so only entries with coverage > 0 remain.
        """
        return {k: v for k, v in coverage.items() if v > 0}


    @staticmethod
    def _normalize_coverage(coverage: dict[str, float]) -> dict[str, float]:
        """
        Normalize a single coverage dictionary to [0, 1] using (score - min) / (max - min).
        If all values are equal, returns all 1.0.
        """
        if not coverage:
            return {}
        min_v = min(coverage.values())
        max_v = max(coverage.values())
        if max_v == min_v:
            return {k: 1.0 for k in coverage}
        return {k: (v - min_v) / (max_v - min_v) for k, v in coverage.items()}


    @staticmethod
    def _get_green_intensity(score: float) -> str:
        """
        Given a float between 0 and 1, return a hex color string representing
        a green intensity. Includes a baseline so score=0 is still visibly green.

        Returns: e.g., '#66FF66' (bright) or '#339933' (medium green)
        """

        # Clamp score to [0, 1]
        clamped_score = max(0.0, min(1.0, score))

        # Baseline intensity (0 → visible medium green)
        baseline = 0.35  # try between 0.3–0.5 for desired brightness

        # Linear interpolation between baseline and full brightness
        intensity = baseline + (1.0 - baseline) * clamped_score

        # Convert to RGB hex (keep R & B slightly above 0 for warmth if desired)
        green_value = int(255 * intensity)
        red_value = int(30 * (1 - clamped_score))  # subtle tint, optional
        blue_value = int(30 * (1 - clamped_score))  # subtle tint, optional

        return f"#{red_value:02X}{green_value:02X}{blue_value:02X}"


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


