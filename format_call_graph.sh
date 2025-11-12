set -e

rawGraphPath="$1"
outputFileName="$2"
scoresPath="$3"

if [ -z "$rawGraphPath" ] || [ -z "$outputFileName" ]; then
  echo "Usage: $0 <raw_graph_path> <output_file_name> [graph_ranking_path]"
  exit 1
fi

python3 main.py $rawGraphPath $outputFileName $scoresPath

dot -Tsvg out/"$outputFileName".dot -o out/"$outputFileName".svg

open out/"$outputFileName".svg