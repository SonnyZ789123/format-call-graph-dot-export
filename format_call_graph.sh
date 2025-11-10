set -e

graphPath="$1"
scoresPath="$2"

if [ -z "$graphPath" ] || [ -z "$scoresPath" ]; then
  echo "Usage: $0 <graph_path> <scores_path>"
  exit 1
fi

python3 main.py $graphPath $scoresPath

dot -Tsvg out/graph_clean_temp.dot -o out/graph_clean_temp.svg

open out/graph_clean_temp.svg