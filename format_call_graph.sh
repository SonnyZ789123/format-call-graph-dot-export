python format_call_graph_dot_export.py ../../library-application/graph_raw.dot

dot -Tsvg graph_clean.dot -o graph_clean.svg

open graph_clean.svg