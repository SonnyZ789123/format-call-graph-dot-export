set -e

graphPath="$1"

if [ -z "$graphPath" ]; then
  echo "Usage: $0 <graph_path>"
  exit 1
fi

python3 main.py $graphPath

dot -Tsvg out/graph_clean_temp.dot -o out/graph_clean_temp.svg

open out/graph_clean_temp.svg