set -e

python3 main.py ../../library-application/graph_raw.dot

dot -Tsvg out/graph_clean_temp.dot -o out/graph_clean_temp.svg

open out/graph_clean_temp.svg